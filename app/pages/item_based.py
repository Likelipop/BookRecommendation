import streamlit as st
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix
from utils import load_data

st.set_page_config(page_title="Item-Based CF", page_icon="🤖")
st.title("🤖 Item-Based Collaborative Filtering")
st.markdown("Hệ thống sẽ tìm những cuốn sách tương đồng dựa trên hành vi đánh giá của cộng đồng người dùng.")

# 1. Load dữ liệu ma trận đã được chuẩn bị từ lớp Gold
ml_df = load_data("gold_user_item_interactions.csv")
if ml_df is None:
    st.error("Chưa có file dữ liệu Machine Learning. Vui lòng chạy cập nhật file `gold.py` trên Dagster.")
    st.stop()


# 2. Xây dựng mô hình (Chạy ngầm mỗi khi bật trang)
@st.cache_resource  # Cache model lại để không phải train lại mỗi lần bấm nút
def train_knn_model(df):
    # Tạo Pivot Table: Dòng là Sách, Cột là User, Giá trị là Rating
    book_pivot = df.pivot_table(index='title', columns='user_id', values='book_rating').fillna(0)

    # Chuyển thành dạng Sparse Matrix để tối ưu RAM (việc xử lý ma trận thưa sẽ nhanh hơn)
    book_sparse = csr_matrix(book_pivot.values)

    # Khởi tạo mô hình KNN dùng khoảng cách Cosine
    model = NearestNeighbors(metric='cosine', algorithm='brute')
    model.fit(book_sparse)

    return model, book_pivot


with st.spinner('Đang khởi tạo ma trận Machine Learning...'):
    knn_model, book_pivot_table = train_knn_model(ml_df)

# 3. Giao diện người dùng
book_list = book_pivot_table.index.tolist()
selected_book = st.selectbox("🔍 Chọn một cuốn sách bạn đã đọc và yêu thích:", ["-- Chọn sách --"] + book_list)
num_recs = st.slider("Số lượng gợi ý:", min_value=1, max_value=10, value=5)

if st.button("Tạo Gợi Ý 🚀") and selected_book != "-- Chọn sách --":
    # Lấy vector điểm rating của cuốn sách được chọn
    book_vector = book_pivot_table.loc[selected_book, :].values.reshape(1, -1)

    # Tìm K hàng xóm gần nhất (cộng thêm 1 vì hàng xóm gần nhất chính là bản thân cuốn sách đó)
    distances, indices = knn_model.kneighbors(book_vector, n_neighbors=num_recs + 1)

    st.subheader(f"💡 Vì bạn thích '{selected_book}', có thể bạn sẽ thích:")

    # Hiển thị kết quả
    recs = []
    for i in range(1, len(distances.flatten())):
        similar_book_title = book_pivot_table.index[indices.flatten()[i]]
        # Cosine distance: 0 là giống hệt, 1 là khác biệt hoàn toàn. (1 - distance) = Độ tương đồng %
        similarity_score = (1 - distances.flatten()[i]) * 100
        recs.append({"Tên Sách": similar_book_title, "Độ Tương Đồng": f"{similarity_score:.1f}%"})

    st.table(pd.DataFrame(recs))