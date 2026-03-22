import streamlit as st
from utils import load_data

st.set_page_config(page_title="Popularity Based", page_icon="🔥")
st.title("🔥 Popularity-Based Recommendations")

df = load_data("gold_book_metrics.csv")
if df is None:
    st.stop()

st.sidebar.header("⚙️ Bộ lọc")
min_ratings = st.sidebar.slider("Số lượt đánh giá tối thiểu:", 5, 200, 20, 5)
top_n = st.sidebar.slider("Top N sách:", 5, 50, 10, 5)

tab1, tab2 = st.tabs(["🏆 Top Sách Nổi Bật", "🔍 Khám phá theo Tác giả"])

with tab1:
    filtered_df = df[df['total_ratings'] >= min_ratings]
    top_books = filtered_df.sort_values(by=['average_rating', 'total_ratings'], ascending=[False, False]).head(top_n)
    st.dataframe(top_books[['title', 'author', 'year', 'average_rating', 'total_ratings']], use_container_width=True, hide_index=True)

with tab2:
    authors = df['author'].dropna().unique()
    selected_author = st.selectbox("Chọn tác giả:", ["-- Hãy chọn tác giả --"] + sorted(list(authors)))
    if selected_author != "-- Hãy chọn tác giả --":
        author_books = df[df['author'] == selected_author].sort_values(by=['average_rating', 'total_ratings'], ascending=[False, False])
        st.dataframe(author_books[['title', 'year', 'average_rating', 'total_ratings']], use_container_width=True, hide_index=True)