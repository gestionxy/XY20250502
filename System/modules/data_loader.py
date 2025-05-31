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
    df = df.dropna(how='all')

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


def load_cash_data():
    # Google Sheet 文件的 ID（你提供的链接）
    file_id = "1G26AeXPjZmAOCDSiGMirBxCGCi_Li-B-"

    # Google Sheet 的 CSV 导出地址
    csv_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"

    # 读取 CSV 数据（从 Google Sheets）
    df_data = pd.read_csv(csv_url)


    # ✅ 步骤 1：读取 Excel 文件
    df_data = df_data.dropna(how='all')  # 删除完全为空的行

    # ✅ 步骤 2：统一日期和金额格式
    df_data['小票日期'] = pd.to_datetime(df_data['小票日期'], errors='coerce').dt.strftime('%Y-%m-%d')  # 格式化为 yyyy-mm-dd 字符串
    df_data['开票日期'] = pd.to_datetime(df_data['开票日期'], errors='coerce')  # 保持为 datetime 类型以便后续提取年月

    # ✅ 保留“开票日期”非空的数据
    df_data = df_data[df_data['开票日期'].notna()]

    # ✅ 金额字段转换为浮点并保留两位小数
    for col in ['总金额', 'TPS', 'TVQ', '支票金额']:
        df_data[col] = pd.to_numeric(df_data[col], errors='coerce').round(2)

    # ✅ 步骤 3：添加“年月”列（格式：2025-02）
    df_data['年月'] = df_data['开票日期'].dt.to_period('M').astype(str)

    # ✅ 步骤 4 : 添加 净值 列
    # 只要其中任意一个值为 NaN，该行计算出的 '净值' 也会是 NaN。 这是因为在 Pandas 中，任何数值与 NaN 参与运算，结果都将是 NaN。
    # .fillna(0) 在这里只是返回一个临时替换了空值的新 Series，并没有写回原来的 DataFrame， 即不改变原数据库内容。
    df_data['净值'] = df_data['总金额'] - df_data['TPS'].fillna(0) - df_data['TVQ'].fillna(0)



    # 强制转换为字符串以避免 Streamlit 警告
    string_columns = ['支票号', '公司名称']
    for col in string_columns:
        if col in df_data.columns:
            df_data[col] = df_data[col].astype(str)

    return df_data
