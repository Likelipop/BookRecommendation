from dagster import asset, RetryPolicy
from databricks.connect import DatabricksSession
from delta.tables import DeltaTable
import pyspark.sql.types as T
from ..databrick_resource import DatabricksServerlessResource

def get_serverless_session():
    """Initialize Databricks Serverless Session"""
    return DatabricksSession.builder.serverless().getOrCreate()


def execute_delta_merge(spark, source_df, dest_table, merge_condition):
    """
    Thực thi Upsert dựa trên tài liệu chuẩn của Databricks Delta Lake.
    """
    if spark.catalog.tableExists(dest_table):
        # Bảng đã tồn tại -> Khởi tạo đối tượng DeltaTable và gọi lệnh merge
        target_delta = DeltaTable.forName(spark, dest_table)

        target_delta.alias("target").merge(
            source_df.alias("source"),
            merge_condition
        ).whenMatchedUpdateAll() \
            .whenNotMatchedInsertAll() \
            .execute()
    else:
        # Bảng chưa tồn tại -> Khởi tạo lần đầu
        source_df.write.format("delta").mode("overwrite").saveAsTable(dest_table)


@asset(
    key_prefix=["bronze", "library"],
    retry_policy=RetryPolicy(max_retries=3, delay=300),
    group_name="bronze_layer",
    description="Upsert daily book data to bronze layer safely"
)
def bronze_raw_book(db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()

    book_schema = T.StructType([
        T.StructField("ISBN", T.StringType(), True),
        T.StructField("Book-Title", T.StringType(), True),
        T.StructField("Book-Author", T.StringType(), True),
        T.StructField("Year-Of-Publication", T.StringType(), True),
        T.StructField("Publisher", T.StringType(), True),
        T.StructField("Image-URL-S", T.StringType(), True),
        T.StructField("Image-URL-M", T.StringType(), True),
        T.StructField("Image-URL-L", T.StringType(), True)
    ])

    df = spark.table("book_project.landing_zone.books").select([field.name for field in book_schema])

    for field in book_schema:
        df = df.withColumn(field.name, df[field.name].cast(field.dataType))

    # BƯỚC QUAN TRỌNG: Xóa trùng lặp theo khóa chính trước khi Merge
    df_deduped = df.dropDuplicates(["ISBN"])

    dest_catalog = "book_project"
    dest_schema = "staged_library"
    dest_table = f"{dest_catalog}.{dest_schema}.bronze_raw_book"

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {dest_catalog}.{dest_schema}")

    merge_condition = "target.ISBN = source.ISBN"
    execute_delta_merge(spark, df_deduped, dest_table, merge_condition)

    return dest_table


@asset(
    key_prefix=["bronze", "library"],
    group_name="bronze_layer",
    description="Upsert daily ratings data to bronze layer safely"
)
def bronze_raw_ratings(db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()

    rating_schema = T.StructType([
        T.StructField("User-ID", T.LongType(), True),
        T.StructField("ISBN", T.StringType(), True),
        T.StructField("Book-Rating", T.LongType(), True)
    ])

    df = spark.table("book_project.landing_zone.ratings")

    for field in rating_schema:
        df = df.withColumn(field.name, df[field.name].cast(field.dataType))

    # Xóa trùng lặp theo cặp User-ID và ISBN (một user chỉ có 1 rating cuối cùng cho 1 sách)
    df_deduped = df.dropDuplicates(["User-ID", "ISBN"])

    dest_table = "book_project.staged_library.bronze_raw_ratings"
    merge_condition = "target.`User-ID` = source.`User-ID` AND target.ISBN = source.ISBN"

    execute_delta_merge(spark, df_deduped, dest_table, merge_condition)

    return dest_table


@asset(
    key_prefix=["bronze", "library"],
    group_name="bronze_layer",
    description="Upsert daily users data to bronze layer safely"
)
def bronze_raw_users(db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()

    user_schema = T.StructType([
        T.StructField("User-ID", T.LongType(), True),
        T.StructField("Location", T.StringType(), True),
        T.StructField("Age", T.DoubleType(), True)
    ])

    df = spark.table("book_project.landing_zone.users")

    for field in user_schema:
        df = df.withColumn(field.name, df[field.name].cast(field.dataType))

    # Xóa trùng lặp theo User-ID
    df_deduped = df.dropDuplicates(["User-ID"])

    dest_table = "book_project.staged_library.bronze_raw_users"
    merge_condition = "target.`User-ID` = source.`User-ID`"

    execute_delta_merge(spark, df_deduped, dest_table, merge_condition)

    return dest_table