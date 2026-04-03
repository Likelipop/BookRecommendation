import smtplib
from email.message import EmailMessage  # Sửa lại ở đây
import os
from dotenv import load_dotenv, find_dotenv

def send_silver_alert_email(asset_name, error_count, clean_count):

    load_dotenv(find_dotenv())
    EMAIL_ADDRESS = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    RECEIVER_EMAIL = "verylikelipop@gmail.com" # Thay bằng email thật của bạn

    msg = EmailMessage()
    msg['Subject'] = f"⚠️ [Dagster Alert] Data Quality Issue: {asset_name}"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECEIVER_EMAIL

    content = f"""
    Hệ thống phát hiện bản ghi lỗi trong quá trình xử lý Silver Layer.

    - Asset: {asset_name}
    - Số dòng lỗi (Errors): {error_count}
    - Số dòng sạch (Clean): {clean_count}
    - Trạng thái: Cần kiểm tra lại table silver_error_{asset_name.split('_')[-1]} trên Databricks.
    """
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")