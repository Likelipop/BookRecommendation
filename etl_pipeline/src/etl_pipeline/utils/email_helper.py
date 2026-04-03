import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv, find_dotenv


def send_silver_alert_email(asset_name, error_count, clean_count):
    """
    Sends an email alert regarding data quality issues detected during the Silver layer processing.

    Args:
        asset_name (str): The name of the Dagster asset that triggered the alert.
        error_count (int): The number of error/invalid records found.
        clean_count (int): The number of clean/valid records processed.
    """
    # Load SMTP credentials from environment variables
    load_dotenv(find_dotenv())
    EMAIL_ADDRESS = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    RECEIVER_EMAIL = "verylikelipop@gmail.com"

    msg = EmailMessage()
    msg['Subject'] = f"⚠️ [Dagster Alert] Data Quality Issue: {asset_name}"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECEIVER_EMAIL

    # Construct the email body
    content = f"""
    The system detected invalid records during the Silver Layer processing.

    - Asset: {asset_name}
    - Error Count: {error_count}
    - Clean Count: {clean_count}
    - Status: Action required. Please review the 'silver_error_{asset_name.split('_')[-1]}' table in Databricks.
    """
    msg.set_content(content)

    # Attempt to send the email via Gmail SMTP
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")