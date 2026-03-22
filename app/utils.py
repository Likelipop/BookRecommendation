import os
import pandas as pd
import streamlit as st

@st.cache_data
def load_data(file_name):
    """Hàm dùng chung để load file CSV từ thư mục data/gold"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    csv_path = os.path.join(project_root, "data", "gold", file_name)

    try:
        df = pd.read_csv(csv_path)
        return df
    except FileNotFoundError:
        st.error(f"⚠️ Không tìm thấy file: {csv_path}")
        return None