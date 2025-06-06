# 📁 modules/cheque_ledger_query.py
import io
import pandas as pd
import streamlit as st
from datetime import datetime
from modules.data_loader import load_supplier_data

def cheque_ledger_query():
    df = load_supplier_data()

    # ✅ 过滤无效支票号
    df = df[df['付款支票号'].apply(lambda x: str(x).strip().lower() not in ['', 'nan', 'none'])]
    df['付款支票号'] = df['付款支票号'].astype(str)

    st.subheader("📒 当前支票总账查询")
    st.info("##### 💡 支票信息总账的搜索时间是按照 *🧾发票日期* 进行设置的，查询某个会计日期内的支票信息")

    # ✅ 财会年度选择器
    fiscal_options = {
        "全部": None,
        "2024年度（2023-08-01 ~ 2024-07-31）": ("2023-08-01", "2024-07-31"),
        "2025年度（2024-08-01 ~ 2025-07-31）": ("2024-08-01", "2025-07-31"),
        "2026年度（2025-08-01 ~ 2026-07-31）": ("2025-08-01", "2026-07-31"),
    }
    selected_fiscal_year = st.selectbox("📅 选择财会年度（可选）", options=list(fiscal_options.keys()))

    # ✅ 发票日期格式化
    df['发票日期'] = pd.to_datetime(df['发票日期'], errors='coerce')

    if fiscal_options[selected_fiscal_year]:
        fiscal_start, fiscal_end = fiscal_options[selected_fiscal_year]
        df = df[
            (df['发票日期'] >= pd.to_datetime(fiscal_start)) &
            (df['发票日期'] <= pd.to_datetime(fiscal_end))
        ]

    min_date = df['发票日期'].min()
    max_date = df['发票日期'].max()

    if pd.isna(min_date) or pd.isna(max_date):
        st.warning("⚠️ 没有符合条件的发票数据，无法进行日期筛选。")
        return

    col1, col2 = st.columns(2)
    start_date = col1.date_input("开始发票日期", value=min_date.date())
    end_date = col2.date_input("结束发票日期", value=max_date.date())

    df = df[df['付款支票号'].notna()]
    df = df[
        (df['发票日期'] >= pd.to_datetime(start_date)) &
        (df['发票日期'] <= pd.to_datetime(end_date))
    ]

    agg_funcs = {
        '公司名称': 'first',
        '部门': lambda x: ','.join(sorted(x.astype(str))),
        '发票号': lambda x: ','.join(sorted(x.astype(str))),
        '发票金额': lambda x: '+'.join(sorted(x.astype(str))),
        '银行对账日期': 'first',
        '实际支付金额': 'sum',
        'TPS': 'sum',
        'TVQ': 'sum',
    }

    grouped = df.groupby('付款支票号').agg(agg_funcs).reset_index()

    grouped['银行对账日期'] = pd.to_datetime(grouped['银行对账日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    grouped['税后金额'] = grouped['实际支付金额'] - grouped['TPS'] - grouped['TVQ']

    # ✅ 日期筛选 + 下载按钮并排显示
    col_a, col_b = st.columns([2, 1])
    with col_a:
        valid_dates = sorted(grouped['银行对账日期'].dropna().unique())
        selected_reconcile_date = st.selectbox("📆 按银行对账日期筛选（可选）", options=["全部"] + valid_dates)

    if selected_reconcile_date != "全部":
        grouped = grouped[grouped['银行对账日期'] == selected_reconcile_date]


    if not grouped.empty:
        def convert_df_to_excel(df_export):
            export_df = df_export.copy()

            # 格式化日期
            export_df['银行对账日期'] = pd.to_datetime(export_df['银行对账日期'], errors='coerce').dt.strftime('%Y-%m-%d')

            # 保留两位小数的金额列
            for col in ['实际支付金额', 'TPS', 'TVQ', '税后金额']:
                export_df[col] = pd.to_numeric(export_df[col], errors='coerce').round(2)

            # ✅ 新增辅助匹配列：支票号数字部分 + 金额
            # 提取数字部分：例如 CK889 → 889
            export_df['辅助匹配列'] = export_df.apply(
                lambda row: f"{''.join(filter(str.isdigit, str(row['付款支票号'])))}-{format(row['实际支付金额'], '.2f')}",
                axis=1
            )

            # 导出 Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                export_df.to_excel(writer, index=False, sheet_name='支票总账')
                writer.close()
            return buffer.getvalue()


        excel_data = convert_df_to_excel(grouped)

        # ✅ 当前时间戳用于命名文件：如 20250606151515
        timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = f"支票总账_{timestamp_str}.xlsx"

        with col_b:
            st.download_button(
                label="📥 下载当前支票数据",
                data=excel_data,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    # ✅ 数值支票号在前、文本支票号在后排序
    def sort_key(val):
        try:
            return (0, int(val))
        except:
            return (1, str(val))

    grouped = grouped.sort_values(by='付款支票号', key=lambda x: x.map(sort_key)).reset_index(drop=True)

    # ✅ 添加总计行
    total_row = pd.DataFrame([{
        '付款支票号': '总计',
        '公司名称': '',
        '部门': '',
        '发票号': '',
        '发票金额': '',
        '实际支付金额': grouped['实际支付金额'].sum(),
        'TPS': grouped['TPS'].sum(),
        'TVQ': grouped['TVQ'].sum(),
        '税后金额': grouped['税后金额'].sum(),
        '银行对账日期': ''
    }])

    grouped_table = pd.concat([grouped, total_row], ignore_index=True)


        # 先构造总计数据字典
    total_data = {
        #"实际支付金额": round(grouped.loc[grouped['付款支票号'] == '总计', '实际支付金额'].sum(), 2),
        #"TPS": round(grouped.loc[grouped['付款支票号'] == '总计', 'TPS'].sum(), 2),
        #"TVQ": round(grouped.loc[grouped['付款支票号'] == '总计', 'TVQ'].sum(), 2),
        #"税后金额": round(grouped.loc[grouped['付款支票号'] == '总计', '税后金额'].sum(), 2),
        "实际支付金额": round(grouped['实际支付金额'].sum(), 2),
        "TPS": round(grouped['TPS'].sum(), 2),
        "TVQ": round(grouped['TVQ'].sum(), 2),
        "税后金额": round(grouped['税后金额'].sum(), 2),
    }

    # 转换为 DataFrame（转置以便更好地展示）
    #total_df = pd.DataFrame.from_dict(total_data, orient='index', columns=['金额'])
    #total_df.index.name = '项目'

    # 渲染为表格
    #st.markdown("#### 💰 总计")
    #st.table(total_df.style.format({'金额': '{:,.2f}'}))



    # 构造 HTML + CSS 表格（卡片浮动样式）
    html = f"""
    <style>
        .card {{
            background-color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            width: 420px;
            margin: 30px auto;
            font-family: "Segoe UI", sans-serif;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 15px;
            background-color: #EAF2F8;
            border-radius: 8px;
            overflow: hidden;
        }}
        .summary-table th {{
            background-color: #D6EAF8;
            text-align: left;
            padding: 10px;
        }}
        .summary-table td {{
            padding: 10px;
            border-top: 1px solid #D4E6F1;
            text-align: right;
        }}
        .summary-table td:first-child {{
            text-align: left;
        }}
    </style>

    <div class="card">
        <h3>💰 总计</h3>
        <table class="summary-table">
            <tr><th>项目</th><th>金额（元）</th></tr>
            <tr><td>实际支付金额</td><td>{total_data['实际支付金额']:,.2f}</td></tr>
            <tr><td>TPS</td><td>{total_data['TPS']:,.2f}</td></tr>
            <tr><td>TVQ</td><td>{total_data['TVQ']:,.2f}</td></tr>
            <tr><td>税后金额</td><td>{total_data['税后金额']:,.2f}</td></tr>
        </table>
    </div>
    """

    # 渲染 HTML 内容
    st.markdown(html, unsafe_allow_html=True)
    
    


    # ✅ 设置样式
    def highlight_total(row):
        if row['付款支票号'] == '总计':
            return ['background-color: #FADBD8'] * len(row)
        return [''] * len(row)

    st.dataframe(
        grouped_table.style
        .apply(highlight_total, axis=1)
        .format({
            #'发票金额': '{:,.2f}',
            '实际支付金额': '{:,.2f}',
            'TPS': '{:,.2f}',
            'TVQ': '{:,.2f}',
            '税后金额': '{:,.2f}'
        }),
        use_container_width=True
    )
