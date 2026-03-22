from dagster import asset_check, AssetCheckResult, AssetKey
from .databrick_resource import DatabricksServerlessResource

def evaluate_error_rate(spark, clean_table: str, error_table: str, threshold: float = 0.05):
    """
    Helper function to calculate the error rate between a clean table and an error table.
    """
    if not spark.catalog.tableExists(clean_table) or not spark.catalog.tableExists(error_table):
        return True, 0.0, 0, 0

    clean_count = spark.table(clean_table).count()
    error_count = spark.table(error_table).count()

    total_count = clean_count + error_count

    if total_count == 0:
        return True, 0.0, 0, 0

    error_rate = error_count / total_count
    is_passed = error_rate <= threshold

    return is_passed, error_rate, clean_count, error_count


# ---------------------------------------------------------
# 1. ERROR RATE CHECKS
# ---------------------------------------------------------

@asset_check(
    asset=AssetKey(["silver", "library", "silver_cleaned_books"]),
    description="Ensure the error rate of cleaned books does not exceed 5%"
)
def check_books_error_rate(context, db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()
    clean_table = "book_project.cleaned_library.silver_cleaned_books"
    error_table = "book_project.cleaned_library.silver_error_books"

    is_passed, error_rate, clean_count, error_count = evaluate_error_rate(
        spark, clean_table, error_table, threshold=0.05
    )

    return AssetCheckResult(
        passed=is_passed,
        metadata={"error_rate": f"{error_rate:.2%}", "clean_rows": clean_count, "error_rows": error_count},
        description=f"Book Error Rate is {error_rate:.2%}. Passed: {is_passed}"
    )


@asset_check(
    asset=AssetKey(["silver", "library", "silver_cleaned_users"]),
    description="Ensure the error rate of cleaned users does not exceed 5%"
)
def check_users_error_rate(context, db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()
    clean_table = "book_project.cleaned_library.silver_cleaned_users"
    error_table = "book_project.cleaned_library.silver_error_users"

    is_passed, error_rate, clean_count, error_count = evaluate_error_rate(
        spark, clean_table, error_table, threshold=0.05
    )

    return AssetCheckResult(
        passed=is_passed,
        metadata={"error_rate": f"{error_rate:.2%}", "clean_rows": clean_count, "error_rows": error_count},
        description=f"User Error Rate is {error_rate:.2%}. Passed: {is_passed}"
    )


@asset_check(
    asset=AssetKey(["silver", "library", "silver_cleaned_ratings"]),
    description="Ensure the error rate of cleaned ratings does not exceed 10%"
)
def check_ratings_error_rate(context, db_resource: DatabricksServerlessResource):
    spark = db_resource.get_session()
    clean_table = "book_project.cleaned_library.silver_cleaned_ratings"
    error_table = "book_project.cleaned_library.silver_error_ratings"

    is_passed, error_rate, clean_count, error_count = evaluate_error_rate(
        spark, clean_table, error_table, threshold=0.10
    )

    return AssetCheckResult(
        passed=is_passed,
        metadata={"error_rate": f"{error_rate:.2%}", "clean_rows": clean_count, "error_rows": error_count},
        description=f"Ratings Error Rate is {error_rate:.2%}. Passed: {is_passed}"
    )


# ---------------------------------------------------------
# 2. BUSINESS LOGIC CHECKS
# ---------------------------------------------------------

@asset_check(
    asset=AssetKey(["silver", "library", "silver_cleaned_ratings"]),
    description="Critical constraint: Cleaned ratings must not contain NULL user_id or ISBN"
)
def check_ratings_no_null_keys(context, db_resource):
    spark = db_resource.get_session()
    clean_table = "book_project.cleaned_library.silver_cleaned_ratings"

    if not spark.catalog.tableExists(clean_table):
        return AssetCheckResult(passed=True, description="Table not created yet.")

    df = spark.table(clean_table)

    # Count rows where essential keys are null
    null_keys_count = df.filter(df["user_id"].isNull() | df["ISBN"].isNull()).count()

    is_passed = (null_keys_count == 0)

    return AssetCheckResult(
        passed=is_passed,
        metadata={"null_keys_count": null_keys_count},
        description="Passed" if is_passed else f"Failed: Found {null_keys_count} rows with NULL keys."
    )