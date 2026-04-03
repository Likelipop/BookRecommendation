from dagster import (
    asset_sensor,
    AssetKey,
    RunRequest,
    op,
    Config,       # Đảm bảo đã import Config
    SkipReason,
    job
)
from ..utils.email_helper import send_silver_alert_email

class EmailAlertConfig(Config):
    # Thêm giá trị mặc định cho các biến
    asset_name: str = "test_asset_from_ui"
    error_count: int = 1  # Giả sử có 1 lỗi để test
    clean_count: int = 0


# 2. SỬA LẠI OP
@op
def send_email_op(config: EmailAlertConfig): # Dùng class vừa tạo thay vì dict
    send_silver_alert_email(
        # 3. DÙNG DẤU CHẤM (.) ĐỂ TRUY CẬP BIẾN
        asset_name=config.asset_name,
        error_count=config.error_count,
        clean_count=config.clean_count
    )


# --- PHẦN DƯỚI NÀY CỦA BẠN GIỮ NGUYÊN HOÀN TOÀN ---

@job
def email_alert_job():
    send_email_op()


@asset_sensor(
    asset_key=AssetKey(["silver", "library", "silver_cleaned_books"]),
    job=email_alert_job
)
def silver_books_error_sensor(context, asset_event):
    metadata = asset_event.asset_materialization.metadata

    err_count = metadata.get("error_count").value if "error_count" in metadata else 0
    clean_count = metadata.get("final_clean_count").value if "final_clean_count" in metadata else 0

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