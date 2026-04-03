from dagster import asset, AssetIn, MaterializeResult, AssetKey
from databricks.connect import DatabricksSession
from ..databrick_resource import DatabricksServerlessResource
import pyspark.sql.functions as F


def separate_errors(df, condition, error_reason):
    """
    Separates the DataFrame into valid rows and error rows based on a condition.
    Adds an 'error_reason' column to the error rows for tracking.

    Returns:
        tuple: (valid_df, error_df)
    """
    error_df = df.filter(condition).withColumn("error_reason", F.lit(error_reason))
    valid_df = df.filter(~condition)
    return valid_df, error_df


@asset(
    ins={"bronze_raw_book": AssetIn(key_prefix=["bronze", "library"])},
    key_prefix=["silver", "library"],
    group_name="silver_layer",
    description="Clean book data with year validation and error logging"
)
def silver_cleaned_books(context, bronze_raw_book, db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()
    raw_df = spark.table("book_project.staged_library.bronze_raw_book")
    error_table = "book_project.cleaned_library.silver_error_books"

    spark.sql("CREATE SCHEMA IF NOT EXISTS book_project.cleaned_library")

    # 1. Check if year is a valid integer
    df_with_cast = raw_df.withColumn("year_parsed", F.expr("try_cast(`Year-Of-Publication` AS INT)"))
    not_int_cond = F.col("Year-Of-Publication").isNotNull() & F.col("year_parsed").isNull()

    valid_df_step1, err_not_int = separate_errors(df_with_cast, not_int_cond, "Year is not an integer")

    # 2. Check year range (1900-2020)
    abnormality_cond = (F.col("year_parsed") < 1900) | (F.col("year_parsed") > 2020)
    valid_df_step2, err_out_of_range = separate_errors(valid_df_step1, abnormality_cond,
                                                       "Year out of range (1900-2020)")

    # 3. Union all errors and save ONCE (Overwrite ensures idempotency)
    all_errors = err_not_int.unionByName(err_out_of_range, allowMissingColumns=True)
    all_errors.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(error_table)

    # 4. Format final valid DataFrame
    final_df = valid_df_step2.select(
        F.col("ISBN").cast("string"),
        F.col("Book-Title").cast("string").alias("book_title"),
        F.col("Book-Author").cast("string").alias("book_author"),
        F.col("year_parsed").alias("year_of_publication"),  # keep as int
        F.col("Publisher").cast("string").alias("publisher"),
        F.col("Image-URL-S").cast("string"),
        F.col("Image-URL-M").cast("string"),
        F.col("Image-URL-L").cast("string")
    )

    dest_table = "book_project.cleaned_library.silver_cleaned_books"
    final_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(dest_table)

    # Trigger action only once at the end for metadata
    yield MaterializeResult(
        metadata={
            "error_count": all_errors.count(),
            "final_clean_count": final_df.count()
        }
    )


@asset(
    ins={"bronze_raw_users": AssetIn(key_prefix=["bronze", "library"])},
    key_prefix=["silver", "library"],
    group_name="silver_layer",
    description="Clean user data with age validation"
)
def silver_cleaned_users(context, bronze_raw_users, db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()
    raw_df = spark.table("book_project.staged_library.bronze_raw_users")
    error_table = "book_project.cleaned_library.silver_error_users"

    spark.sql("CREATE SCHEMA IF NOT EXISTS book_project.cleaned_library")

    # 1. Check if Age is an integer
    df_cast = raw_df.withColumn("age_parsed", F.expr("try_cast(Age AS INT)"))
    not_int_cond = F.col("Age").isNotNull() & F.col("age_parsed").isNull()

    valid_df_step1, err_not_int = separate_errors(df_cast, not_int_cond, "Age is not an integer")

    # 2. Check Age range (5-80)
    abnormality_cond = (F.col("age_parsed") < 5) | (F.col("age_parsed") > 80)
    valid_df_step2, err_out_of_range = separate_errors(valid_df_step1, abnormality_cond, "Age out of range (5-80)")

    # 3. Union errors and write
    all_errors = err_not_int.unionByName(err_out_of_range, allowMissingColumns=True)
    all_errors.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(error_table)

    # 4. Format final valid DataFrame
    final_df = valid_df_step2.select(
        F.col("User-ID").cast("string").alias("user_id"),
        F.col("Location").cast("string").alias("location"),
        F.col("age_parsed").alias("age")  # keep as int
    ).dropDuplicates(["user_id"])

    dest_table = "book_project.cleaned_library.silver_cleaned_users"
    final_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(dest_table)

    yield MaterializeResult(
        metadata={
            "error_count": all_errors.count(),
            "final_clean_count": final_df.count()
        }
    )


@asset(
    deps=[
        AssetKey(["silver", "library", "silver_cleaned_users"]),
        AssetKey(["silver", "library", "silver_cleaned_books"]),
        AssetKey(["bronze", "library", "bronze_raw_ratings"])
    ],
    key_prefix=["silver", "library"],
    group_name="silver_layer",
    description="Clean ratings data using validated users and books"
)
def silver_cleaned_ratings(context, db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()

    raw_df = spark.table("book_project.staged_library.bronze_raw_ratings")
    users_df = spark.table("book_project.cleaned_library.silver_cleaned_users")
    books_df = spark.table("book_project.cleaned_library.silver_cleaned_books")
    error_table = "book_project.cleaned_library.silver_error_ratings"

    # 1. Verify UserID exists in users table
    valid_users_df = raw_df.join(users_df, raw_df["User-ID"] == users_df["user_id"], "left_semi")
    fake_users_df = raw_df.join(users_df, raw_df["User-ID"] == users_df["user_id"], "left_anti") \
        .withColumn("error_reason", F.lit("User-ID does not exist in users table"))

    # 2. Verify ISBN exists in books table
    valid_books_df = valid_users_df.join(books_df, "ISBN", "left_semi")
    fake_books_df = valid_users_df.join(books_df, "ISBN", "left_anti") \
        .withColumn("error_reason", F.lit("ISBN does not exist in books table"))

    # 3. Check if BookRating is an integer
    df_cast = valid_books_df.withColumn("rating_parsed", F.expr("try_cast(`Book-Rating` AS INT)"))
    not_int_cond = F.col("Book-Rating").isNotNull() & F.col("rating_parsed").isNull()

    valid_df_step3, err_not_int = separate_errors(df_cast, not_int_cond, "Rating is not an integer")

    # 4. Check Rating range (1-10)
    abnormality_cond = (F.col("rating_parsed") < 1) | (F.col("rating_parsed") > 10)
    valid_df_step4, err_out_of_range = separate_errors(valid_df_step3, abnormality_cond, "Rating out of range (1-10)")

    # 5. Union all 4 types of errors together and write ONCE
    # allowMissingColumns=True is crucial here because fake_users/books don't have 'rating_parsed'
    all_errors = fake_users_df.unionByName(fake_books_df, allowMissingColumns=True) \
        .unionByName(err_not_int, allowMissingColumns=True) \
        .unionByName(err_out_of_range, allowMissingColumns=True)

    all_errors.write.format("delta").mode("overwrite").option("mergeSchema", "true").saveAsTable(error_table)

    # 6. Format final valid DataFrame
    final_df = valid_df_step4.select(
        F.col("User-ID").alias("user_id"),
        F.col("ISBN"),
        F.col("rating_parsed").alias("book_rating")
    ).dropDuplicates(["user_id", "ISBN"])

    dest_table = "book_project.cleaned_library.silver_cleaned_ratings"
    final_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(dest_table)

    yield MaterializeResult(
        metadata={
            "total_errors_caught": all_errors.count(),
            "final_clean_count": final_df.count()
        }
    )
