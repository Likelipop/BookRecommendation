from dagster import asset, AssetKey, MaterializeResult
from databricks.connect import DatabricksSession
from ..databrick_resource import DatabricksServerlessResource
import pyspark.sql.functions as F

import os


def get_serverless_session():
    """Initialize Databricks Serverless Session"""
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
    spark = db_resource.get_session()

    # Tạo schema cho lớp gold nếu chưa có
    spark.sql("CREATE SCHEMA IF NOT EXISTS book_project.gold_library")

    # Đọc dữ liệu từ lớp Silver
    books_df = spark.table("book_project.cleaned_library.silver_cleaned_books")
    ratings_df = spark.table("book_project.cleaned_library.silver_cleaned_ratings")

    # 1. Aggregation: Tính toán các metrics cho sách
    # Nhóm theo ISBN, đếm số lượng rating và tính điểm trung bình
    agg_ratings_df = ratings_df.groupBy("ISBN").agg(
        F.count("book_rating").alias("total_ratings"),
        F.round(F.avg("book_rating"), 2).alias("average_rating")
    )

    # Lọc nhiễu: Chỉ lấy những sách có từ 5 lượt đánh giá trở lên (Business Rule)
    filtered_ratings_df = agg_ratings_df.filter(F.col("total_ratings") >= 5)

    # 2. Join: Kết nối với thông tin sách để tạo bảng hoàn chỉnh
    gold_df = filtered_ratings_df.join(books_df, "ISBN", "left")

    # 3. Select & Order: Chọn các cột cần thiết và sắp xếp thứ hạng
    final_gold_df = gold_df.select(
        "ISBN",
        F.col("book_title").alias("title"),
        F.col("book_author").alias("author"),
        F.col("year_of_publication").alias("year"),
        "total_ratings",
        "average_rating"
    ).orderBy(F.col("average_rating").desc(), F.col("total_ratings").desc())

    # --- LƯU XUỐNG DATABRICKS TIER ---
    dest_table = "book_project.gold_library.gold_book_metrics"
    final_gold_df.write.format("delta").mode("overwrite").saveAsTable(dest_table)

    context.log.info(f"Successfully wrote Delta table to {dest_table}")

    # --- THỬ NGHIỆM: LƯU KẾT QUẢ XUỐNG LOCAL DESKTOP ---
    # Chuyển đổi Spark DataFrame thành Pandas DataFrame để lưu ở local
    # Lưu ý: Lớp Gold đã được aggregate nên dung lượng thường đủ nhỏ để fit vào RAM (toPandas)
    pandas_df = final_gold_df.toPandas()

    # 1. Lấy đường dẫn tuyệt đối của thư mục chứa file gold.py hiện tại (thư mục 'defs')
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Lùi 4 cấp thư mục để trở về thư mục gốc 'BookRecommendation'
    # Cấu trúc: defs (1) -> etl_pipeline (2) -> src (3) -> etl_pipeline (4) -> BookRecommendation
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))

    # 3. Trỏ chính xác vào thư mục data/gold nằm ở thư mục gốc
    local_dir = os.path.join(project_root, "data", "gold")

    # 4. Tạo thư mục và định nghĩa đường dẫn file CSV
    os.makedirs(local_dir, exist_ok=True)
    local_csv_path = os.path.join(local_dir, "gold_book_metrics.csv")

    # Lưu thành file CSV
    pandas_df.to_csv(local_csv_path, index=False, encoding='utf-8')
    context.log.info(f"Successfully saved local CSV to {local_csv_path}")

    # Trả về metadata cho Dagster UI
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
    spark = db_resource.get_session()

    # 1. Đọc dữ liệu từ lớp Silver
    ratings_df = spark.table("book_project.cleaned_library.silver_cleaned_ratings")
    books_df = spark.table("book_project.cleaned_library.silver_cleaned_books")

    # 2. LỌC NHIỄU (GIẢM SPARSITY) CHO MACHINE LEARNING
    # Chỉ lấy những người dùng đã đánh giá ít nhất 5 cuốn sách (Active Users)
    active_users = ratings_df.groupBy("user_id").count().filter(F.col("count") >= 5).select("user_id")

    # Chỉ lấy những cuốn sách có ít nhất 10 lượt đánh giá (Popular Books)
    popular_books = ratings_df.groupBy("ISBN").count().filter(F.col("count") >= 10).select("ISBN")

    # Áp dụng bộ lọc vào bảng ratings ban đầu
    ml_ratings_df = ratings_df \
        .join(active_users, "user_id", "inner") \
        .join(popular_books, "ISBN", "inner")

    # Lấy thêm tên sách để tiện hiển thị trên Streamlit
    final_ml_df = ml_ratings_df.join(
        books_df.select("ISBN", F.col("book_title").alias("title")),
        "ISBN",
        "left"
    ).select("user_id", "ISBN", "title", "book_rating")

    # --- LƯU XUỐNG DATABRICKS ---
    dest_table = "book_project.gold_library.gold_user_item_interactions"
    final_ml_df.write.format("delta").mode("overwrite").saveAsTable(dest_table)

    # --- LƯU XUỐNG LOCAL CSV CHO STREAMLIT ---
    pandas_df = final_ml_df.toPandas()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))
    local_dir = os.path.join(project_root, "data", "gold")

    os.makedirs(local_dir, exist_ok=True)
    local_csv_path = os.path.join(local_dir, "gold_user_item_interactions.csv")

    pandas_df.to_csv(local_csv_path, index=False, encoding='utf-8')

    yield MaterializeResult(
        metadata={
            "total_ml_interactions": int(final_ml_df.count()),
            "unique_users": int(pandas_df['user_id'].nunique()),
            "unique_books": int(pandas_df['ISBN'].nunique()),
            "local_file_path": local_csv_path
        }
    )