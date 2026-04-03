from dagster import (
    asset_sensor,
    AssetKey,
    RunRequest,
    op,
    Config,
    SkipReason,
    job
)
from ..utils.email_helper import send_silver_alert_email


class EmailAlertConfig(Config):
    """
    Configuration schema for the email alert operation.
    Provides default values for testing purposes.
    """
    asset_name: str = "test_asset_from_ui"
    error_count: int = 1
    clean_count: int = 0


@op
def send_email_op(config: EmailAlertConfig):
    """
    Dagster operation that extracts configuration values and executes
    the external email helper function to send an alert.
    """
    send_silver_alert_email(
        asset_name=config.asset_name,
        error_count=config.error_count,
        clean_count=config.clean_count
    )


@job
def email_alert_job():
    """
    Dagster job encapsulating the email alert operation.
    """
    send_email_op()


@asset_sensor(
    asset_key=AssetKey(["silver", "library", "silver_cleaned_books"]),
    job=email_alert_job
)
def silver_books_error_sensor(context, asset_event):
    """
    Sensor that monitors materialization events for the 'silver_cleaned_books' asset.
    Evaluates metadata and triggers the email alert job if data quality errors are found.
    """
    metadata = asset_event.asset_materialization.metadata

    # Safely extract metrics from the asset's materialization metadata
    err_count = metadata.get("error_count").value if "error_count" in metadata else 0
    clean_count = metadata.get("final_clean_count").value if "final_clean_count" in metadata else 0

    # Trigger a run request if bad records were detected
    if err_count > 0:
        return RunRequest(
            run_key=f"error_alert_{asset_event.run_id}",
            run_config={
                "ops": {
                    "send_email_op": {
                        "config": {
                            "asset_name": "silver_cleaned_books",
                            "error_count": err_count,
                            "clean_count": clean_count
                        }
                    }
                }
            }
        )

    return SkipReason("No errors detected in silver_cleaned_books.")