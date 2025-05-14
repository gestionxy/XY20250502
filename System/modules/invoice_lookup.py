import streamlit as st
import pandas as pd
from modules.data_loader import load_supplier_data


def invoice_lookup_query():
    # 🔄 加载供应商数据
    df = load_supplier_data()

    # 📝 设置页面标题
    st.subheader("🧾 发票号查询（支持精确匹配和下拉选择）")

    # ✅ 预处理发票号列表，去除空值并转换为字符串类型
    # 将所有发票号转换为字符串，去除空值，并获取唯一值
    all_invoice_ids = df['发票号'].dropna().astype(str).unique().tolist()

    # ✅ 将发票号分为数字和非数字两类，并分别排序
    # 数字发票号按数值排序
    numeric_ids = sorted([x for x in all_invoice_ids if x.isdigit()], key=lambda x: int(x))
    # 非数字发票号按字母顺序排序
    text_ids = sorted([x for x in all_invoice_ids if not x.isdigit()])

    # ✅ 合并数字和文本发票号，确保数字在前
    all_sorted_invoice_ids = numeric_ids + text_ids

    # ✅ 选择框（支持精确匹配）
    # 提供一个带有下拉选项和输入框的组合控件
    invoice_input = st.selectbox(
        "请输入或选择发票号（仅精确匹配）",  # 输入提示
        options=all_sorted_invoice_ids,  # 选项列表
        index=None,  # 默认不选中任何值
        placeholder="请输入完整的发票号，例如145 或 IN145"  # 输入框占位符
    )

    # ✅ 检查用户是否输入了发票号
    if invoice_input:
        # 🔎 过滤数据，仅保留完全匹配的发票号
        filtered = df[df['发票号'].astype(str).str.strip() == invoice_input.strip()]

        # ❌ 如果没有找到匹配结果，提示用户
        if filtered.empty:
            st.warning("❌ 未找到相关发票号，请检查输入或选择内容。")
        else:
            # 💰 差额列计算
            # 计算差额 = 发票金额 - 实际支付金额，缺失值视为0
            filtered['差额'] = filtered['发票金额'].fillna(0) - filtered['实际支付金额'].fillna(0)

            # 📅 格式化日期列
            # 将 '发票日期' 和 '开支票日期' 转换为 'YYYY-MM-DD' 格式
            for col in ['发票日期', '开支票日期']:
                filtered[col] = pd.to_datetime(filtered[col], errors='coerce').dt.strftime('%Y-%m-%d')

            # ✅ 设置要显示的列
            display_cols = [
                '发票号', '公司名称', '部门', '付款支票号',
                '发票日期', '开支票日期',
                '发票金额', '实际支付金额', 'TPS', 'TVQ', '差额'
            ]

            # ✅ 统计汇总行（仅当结果行数 >= 2）
            has_summary_row = False
            if len(filtered) >= 2:
                # 📊 创建汇总行，只统计数值列
                has_summary_row = True
                summary_row = pd.DataFrame({
                    '发票号': ['汇总'],
                    '公司名称': ['-'],
                    '部门': ['-'],
                    '付款支票号': ['-'],
                    '发票日期': ['-'],
                    '开支票日期': ['-'],
                    '发票金额': [filtered['发票金额'].sum()],
                    '实际支付金额': [filtered['实际支付金额'].sum()],
                    'TPS': [filtered['TPS'].sum()],
                    'TVQ': [filtered['TVQ'].sum()],
                    '差额': [filtered['差额'].sum()]
                })

                # 🔗 将汇总行添加到结果表格中
                filtered = pd.concat([filtered, summary_row], ignore_index=True)

            # 🎨 自定义样式函数（设置汇总行背景颜色）
            def highlight_summary(row):
                # 如果该行是汇总行，则设置淡红色背景
                if has_summary_row and row['发票号'] == '汇总':
                    return ['background-color: #f8d7da'] * len(row)
                # 否则不设置背景颜色
                return [''] * len(row)

            # 📋 显示结果表格
            # 使用 Pandas Styler 设置表格格式和样式
            st.dataframe(
                filtered[display_cols].style.apply(highlight_summary, axis=1).format({
                    '发票金额': '{:,.2f}',
                    '实际支付金额': '{:,.2f}',
                    'TPS': '{:,.2f}',
                    'TVQ': '{:,.2f}',
                    '差额': '{:,.2f}'
                }),
                use_container_width=True  # 使表格自适应容器宽度
            )
