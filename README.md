# 📚 Simple Book Recommendation System

Dự án này là một hệ thống gợi ý sách đơn giản, giúp người dùng tìm kiếm những cuốn sách tương tự dựa trên nội dung hoặc sở thích cá nhân. Phù hợp cho những ai đang bắt đầu tìm hiểu về **Recommender Systems** và **Machine Learning**.
This project's purpose is to create a simple pipeline for creating a book recommendation model, tranditional one.
The whole pipeline especially makes use of serverless Databrick platform for delegating hard work using PySpark, and Dagster for the ease of orchestration.

## 🚀 Features

* **Content-bassed recommendation:**
* **Items-based recommendation:**
* **Users-based recommendation:**

## 🛠️ Tech stach

This project was crafted mainly by **Python** and makes use of:

* **PySpark:** for ingestion and Transformations.
* **Dagster:** Pipeline orchestrations.
* **Streamlit (under implementation):** graphical interfaces for deployment. 

## ⚙️ Installation

This project uses **[uv](https://github.com/astral-sh/uv)**, an extremely fast Python package installer and resolver.

1. **Clone the repository:**
```bash
git clone https://github.com/username/simple-book-recommendation.git
cd simple-book-recommendation

```


2. **Create a virtual environment and install dependencies:**
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

```



## 🔐 Databricks Authentication

To interact with your Databricks workspace, you need to configure authentication. It is recommended to use environment variables or the Databricks CLI.

1. **Install Databricks CLI:**
```bash
uv pip install databricks-cli

```


2. **Configure your credentials:**
```bash
export DATABRICKS_HOST="https://adb-xxxx.x.azuredatabricks.net"
export DATABRICKS_TOKEN="your-personal-access-token"

```


*Alternatively, run `databricks configure --token` and follow the prompts.*

## 📥 Data Ingestion (Bronze Layer)

The ingestion process is handled by `src/ingestion/bronze.py`. This script uploads raw book data to the Databricks Unity Catalog.

**Catalog Destination:** `workspace.book_datas`

The `bronze.py` script performs the following:

* Connects to the Databricks workspace using the configured credentials.
* Reads raw local datasets (CSV/JSON).
* Writes the data to the Delta table at `workspace.book_datas.raw_books`.

**Run ingestion:**

```bash
python src/ingestion/bronze.py

```


## 🤝 Contributing

Feel free to open an issue or submit a pull request if you want to extend the project to Silver/Gold layers or add new recommendation algorithms.
