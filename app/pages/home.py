import streamlit as st

st.title("📚 Book Recommendation Engine")
st.markdown("""
Chào mừng bạn đến với Hệ thống Gợi ý Sách! Hệ thống này được vận hành bởi Data Pipeline: **Bronze ➡️ Silver ➡️ Gold**.

👈 **Hãy chọn các tính năng ở thanh công cụ bên trái:**
* **🔥 Gợi ý Phổ Biến:** Phù hợp cho người dùng mới (Cold Start), gợi ý các sách có lượt đánh giá cao nhất.
* **🤖 Gợi ý Tương Đồng:** Ứng dụng Machine Learning để tìm các cuốn sách có hành vi đánh giá giống nhau.
""")