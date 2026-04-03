from dagster import asset, AssetKey, MaterializeResult
from databricks.connect import DatabricksSession
from ..databrick_resource import DatabricksServerlessResource
import pyspark.sql.functions as F
import os


def get_serverless_session():
    """
    Initializes and returns a Databricks Serverless Spark session.
    """
    return DatabricksSession.builder.serverless().getOrCreate()


@asset(
    deps=[
        AssetKey(["silver", "library", "silver_cleaned_books"]),
        AssetKey(["silver", "library", "silver_cleaned_ratings"])
    ],
    key_prefix=["gold", "library"],
    group_name="gold_layer",
    description="Aggregated book metrics for analytics and recommendations. Saves to Databricks and Local CSV."
)
def gold_book_metrics(context, db_resource: DatabricksServerlessResource):
    """
    Aggregates book ratings from the silver layer, calculates average ratings and total reviews,
    filters out books with fewer than 5 ratings, and saves the final analytical dataset
    to both Databricks Delta Lake and a local CSV file.
    """
    spark = db_resource.get_session()

    spark.sql("CREATE SCHEMA IF NOT EXISTS book_project.gold_library")

    books_df = spark.table("book_project.cleaned_library.silver_cleaned_books")
    ratings_df = spark.table("book_project.cleaned_library.silver_cleaned_ratings")

    # Aggregate ratings per book and filter out books with fewer than 5 ratings
    agg_ratings_df = ratings_df.groupBy("ISBN").agg(
        F.count("book_rating").alias("total_ratings"),
        F.round(F.avg("book_rating"), 2).alias("average_rating")
    )

    filtered_ratings_df = agg_ratings_df.filter(F.col("total_ratings") >= 5)

    # Join with book metadata and sort by rating and popularity
    gold_df = filtered_ratings_df.join(books_df, "ISBN", "left")

    final_gold_df = gold_df.select(
        "ISBN",
        F.col("book_title").alias("title"),
        F.col("book_author").alias("author"),
        F.col("year_of_publication").alias("year"),
        "total_ratings",
        "average_rating"
    ).orderBy(F.col("average_rating").desc(), F.col("total_ratings").desc())

    dest_table = "book_project.gold_library.gold_book_metrics"
    final_gold_df.write.format("delta").mode("overwrite").saveAsTable(dest_table)

    context.log.info(f"Successfully wrote Delta table to {dest_table}")

    # Convert to Pandas to save locally (safe due to reduced aggregated size)
    pandas_df = final_gold_df.toPandas()

    # Resolve path to project root and define local export directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))
    local_dir = os.path.join(project_root, "data", "gold")

    os.makedirs(local_dir, exist_ok=True)
    local_csv_path = os.path.join(local_dir, "gold_book_metrics.csv")

    pandas_df.to_csv(local_csv_path, index=False, encoding='utf-8')
    context.log.info(f"Successfully saved local CSV to {local_csv_path}")

    yield MaterializeResult(
        metadata={
            "total_analytical_books": int(final_gold_df.count()),
            "local_file_path": local_csv_path
        }
    )


@asset(
    deps=[
        AssetKey(["silver", "library", "silver_cleaned_books"]),
        AssetKey(["silver", "library", "silver_cleaned_ratings"])
    ],
    key_prefix=["gold", "library"],
    group_name="gold_layer",
    description="Filtered User-Item interactions for Collaborative Filtering"
)
def gold_user_item_interactions(context, db_resource: DatabricksServerlessResource):
    """
    Filters user-item interactions to reduce sparsity for Machine Learning models.
    Keeps only users with at least 5 ratings and books with at least 10 ratings.
    Saves the resulting dataset to Databricks Delta Lake and a local CSV.
    """
    spark = db_resource.get_session()

    ratings_df = spark.table("book_project.cleaned_library.silver_cleaned_ratings")
    books_df = spark.table("book_project.cleaned_library.silver_cleaned_books")

    # Reduce sparsity: Filter for active users (>= 5 ratings) and popular books (>= 10 ratings)
    active_users = ratings_df.groupBy("user_id").count().filter(F.col("count") >= 5).select("user_id")
    popular_books = ratings_df.groupBy("ISBN").count().filter(F.col("count") >= 10).select("ISBN")

    ml_ratings_df = ratings_df \
        .join(active_users, "user_id", "inner") \
        .join(popular_books, "ISBN", "inner")

    final_ml_df = ml_ratings_df.join(
        books_df.select("ISBN", F.col("book_title").alias("title")),
        "ISBN",
        "left"
    ).select("user_id", "ISBN", "title", "book_rating")

    dest_table = "book_project.gold_library.gold_user_item_interactions"
    final_ml_df.write.format("delta").mode("overwrite").saveAsTable(dest_table)

    context.log.info(f"Successfully wrote Delta table to {dest_table}")

    # Convert to Pandas and save to local directory for Streamlit consumption
    pandas_df = final_ml_df.toPandas()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))
    local_dir = os.path.join(project_root, "data", "gold")

    os.makedirs(local_dir, exist_ok=True)
    local_csv_path = os.path.join(local_dir, "gold_user_item_interactions.csv")

    pandas_df.to_csv(local_csv_path, index=False, encoding='utf-8')
    context.log.info(f"Successfully saved local CSV to {local_csv_path}")

    yield MaterializeResult(
        metadata={
            "total_ml_interactions": int(final_ml_df.count()),
            "unique_users": int(pandas_df['user_id'].nunique()),
            "unique_books": int(pandas_df['ISBN'].nunique()),
            "local_file_path": local_csv_path
        }
    )