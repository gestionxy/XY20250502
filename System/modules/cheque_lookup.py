import streamlit as st
import pandas as pd
from fonts.fonts import load_chinese_font
from modules.data_loader import load_supplier_data

my_font = load_chinese_font()

def cheque_lookup_query():
    df = load_supplier_data()

    st.subheader("🔍 支票号查询")

    # 提取所有非空支票号
    all_cheques = df['付款支票号'].dropna()
    all_cheques = all_cheques[all_cheques.astype(str).str.strip() != ''].astype(str).unique()

    # 支票号排序：数字在前，文本在后
    numeric_cheques = sorted([c for c in all_cheques if c.isnumeric()], key=lambda x: int(x))
    text_cheques = sorted([c for c in all_cheques if not c.isnumeric()])
    sorted_cheques = numeric_cheques + text_cheques

    # 创建下拉输入框，支持提示匹配和空默认
    cheque_input = st.selectbox(
        "请输入或选择支票号（支持模糊匹配）:",
        options=[""] + sorted_cheques,
        index=0,
        placeholder="输入支票号或选择下拉选项"
    )

    if cheque_input:
        # 模糊匹配：包含关键词
        filtered = df[df['付款支票号'].astype(str).str.contains(cheque_input.strip(), case=False, na=False)]

        if filtered.empty:
            st.warning("❌ 支票号不存在或输入错误，请检查后重试。")
        else:
            # 差额计算
            filtered['发票金额'] = pd.to_numeric(filtered['发票金额'], errors='coerce').fillna(0)
            filtered['实际支付金额'] = pd.to_numeric(filtered['实际支付金额'], errors='coerce').fillna(0)
            filtered['差额'] = filtered['发票金额'] - filtered['实际支付金额']

            # 格式化日期
            filtered['发票日期'] = pd.to_datetime(filtered['发票日期'], errors='coerce').dt.strftime('%Y-%m-%d')
            filtered['开支票日期'] = pd.to_datetime(filtered['开支票日期'], errors='coerce').dt.strftime('%Y-%m-%d')

            # 部门汇总
            summary = filtered.groupby('部门')[['实际支付金额', 'TPS', 'TVQ']].sum().reset_index()
            total_row = pd.DataFrame([{
                '部门': '总计',
                '实际支付金额': summary['实际支付金额'].sum(),
                'TPS': summary['TPS'].sum(),
                'TVQ': summary['TVQ'].sum()
            }])
            summary = pd.concat([summary, total_row], ignore_index=True)

            def highlight_total(row):
                if row['部门'] == '总计':
                    return ['background-color: #FADBD8'] * len(row)
                return [''] * len(row)

            st.markdown("### 💰 查询结果：部门汇总")
            st.dataframe(
                summary.style
                .apply(highlight_total, axis=1)
                .format({
                    '实际支付金额': '{:,.2f}',
                    'TPS': '{:,.2f}',
                    'TVQ': '{:,.2f}'
                }),
                use_container_width=True
            )

            st.markdown("### 🧾 查询结果：详细发票信息")
            st.dataframe(
                filtered[['部门', '公司名称', '发票号', '发票金额', '实际支付金额', 'TPS', 'TVQ', '差额', '发票日期', '开支票日期']]
                .style.format({
                    '发票金额': '{:,.2f}',
                    '实际支付金额': '{:,.2f}',
                    'TPS': '{:,.2f}',
                    'TVQ': '{:,.2f}',
                    '差额': '{:,.2f}'
                }),
                use_container_width=True
            )
