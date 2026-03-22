import streamlit as st

# 1. Cấu hình chung cho toàn bộ App (Phải gọi đầu tiên)
st.set_page_config(
    page_title="Book Recommender System",
    page_icon="📚",
    layout="wide"
)

# 2. Định nghĩa các trang (Kết nối file vật lý với Tên hiển thị & Icon)
home_page = st.Page(
    "pages/home.py",
    title="Trang Chủ",
    icon="🏠",
    default=True  # Trang này sẽ hiện lên đầu tiên khi vào app
)

popularity_page = st.Page(
    "pages/popularity_based.py",
    title="Gợi ý Phổ Biến (Popularity)",
    icon="🔥"
)

item_based_page = st.Page(
    "pages/item_based.py",
    title="Gợi ý Tương Đồng (Item-Based CF)",
    icon="🤖"
)

# 3. Gom các trang vào Navigation và chạy
pg = st.navigation({
    "Hệ Thống Gợi Ý": [home_page, popularity_page, item_based_page]
})

pg.run()