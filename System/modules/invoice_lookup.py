import streamlit as st
import pandas as pd
from fonts.fonts import load_chinese_font
from modules.data_loader import load_supplier_data

my_font = load_chinese_font()

def invoice_lookup_query():
    df = load_supplier_data()

    st.subheader("🧾 发票号查询（支持模糊匹配和下拉选择）")

    # ✅ 预处理发票号列表
    all_invoice_ids = df['发票号'].dropna().astype(str).unique().tolist()

    numeric_ids = sorted([x for x in all_invoice_ids if x.isdigit()], key=lambda x: int(x))
    text_ids = sorted([x for x in all_invoice_ids if not x.isdigit()])

    all_sorted_invoice_ids = numeric_ids + text_ids

    # ✅ 合并输入框：可输入，也可下拉选择
    invoice_input = st.selectbox(
        "请输入或选择发票号关键词（自动提示，模糊包含）",
        options=all_sorted_invoice_ids,
        index=None,
        placeholder="请输入发票号关键词，例如145 或 IN145"
    )


    if invoice_input:
        filtered = df[df['发票号'].astype(str).str.contains(invoice_input.strip(), case=False, na=False)]
        # 后续逻辑...


        if filtered.empty:
            st.warning("❌ 未找到相关发票号，请检查输入或选择内容。")
        else:
            # ✅ 差额列
            filtered['差额'] = filtered['发票金额'].fillna(0) - filtered['实际支付金额'].fillna(0)

            # ✅ 格式化日期列
            for col in ['发票日期', '开支票日期']:
                filtered[col] = pd.to_datetime(filtered[col], errors='coerce').dt.strftime('%Y-%m-%d')

            # ✅ 显示结果
            st.markdown("### 📋 查询结果：发票明细")
            display_cols = [
                '发票号', '公司名称', '部门', '付款支票号',
                '发票日期', '开支票日期',
                '发票金额', '实际支付金额', 'TPS', 'TVQ', '差额'
            ]
            st.dataframe(
                filtered[display_cols].style.format({
                    '发票金额': '{:,.2f}',
                    '实际支付金额': '{:,.2f}',
                    'TPS': '{:,.2f}',
                    'TVQ': '{:,.2f}',
                    '差额': '{:,.2f}'
                }),
                use_container_width=True
            )
