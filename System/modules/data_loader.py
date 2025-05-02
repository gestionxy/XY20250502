import pandas as pd
import streamlit as st

# 加载数据函数，设置缓存时间为 10 秒
@st.cache_data(ttl=3600)

def load_supplier_data():
    # Google Sheet 文件的 ID（你提供的链接）
    file_id = "1qH_odKEPlDrLTM8B8UfsMzW6Uu9ciDUW"

    # Google Sheet 的 CSV 导出地址
    csv_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"

    # 读取 CSV 数据（从 Google Sheets）
    df = pd.read_csv(csv_url)

    # 自动转换常用日期字段为 datetime 类型（可按需扩展）
    date_columns = ['开支票日期', '发票日期']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # 强制转换为字符串以避免 Streamlit 警告
    string_columns = ['付款支票号', '发票号', '公司名称']
    for col in string_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df
