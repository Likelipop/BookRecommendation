import os
import pandas as pd
import streamlit as st
from databricks import sql
from dotenv import load_dotenv

# Load các biến môi trường từ file .env
load_dotenv()


def get_databricks_connection():
    """Khởi tạo kết nối an toàn đến Databricks SQL Warehouse/Serverless."""
    try:
        connection = sql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        return connection
    except Exception as e:
        st.error(f"⚠️ Lỗi kết nối đến Databricks: {e}")
        return None


# ttl=3600: Cache dữ liệu trong 1 giờ để tiết kiệm chi phí tính toán (compute) trên Databricks
@st.cache_data(ttl=3600)
def load_data(query: str):
    """Thực thi câu SQL trên Databricks và trả về Pandas DataFrame"""
    conn = get_databricks_connection()

    if conn is None:
        return None

    try:
        # Sử dụng pd.read_sql để lấy trực tiếp kết quả từ kết nối DB vào DataFrame
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"⚠️ Lỗi khi truy vấn dữ liệu từ Databricks: {e}")
        return None
    finally:
        # Luôn đảm bảo đóng kết nối để giải phóng tài nguyên
        conn.close()