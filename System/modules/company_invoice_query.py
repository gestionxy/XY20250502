import streamlit as st
import pandas as pd
from fonts.fonts import load_chinese_font
from modules.data_loader import load_supplier_data

my_font = load_chinese_font()

def company_invoice_query():
    df = load_supplier_data()

    st.subheader("🏢 公司查询（支持不区分大小写模糊匹配+下拉选择）")

    # ✅ 公司名选项（去重、排除空值）
    all_companies = df['公司名称'].dropna().astype(str).unique().tolist()
    sorted_companies = sorted([c for c in all_companies if c.strip()], key=lambda x: x.lower())

    # ✅ 用户输入或选择公司名称（自动提示 + 下拉）
    keyword = st.selectbox("请输入或选择公司名称（支持模糊匹配和不区分大小写）:", options=[""] + sorted_companies, index=0)

    # ✅ 日期选择（发票日期）
    min_date, max_date = df['发票日期'].min(), df['发票日期'].max()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", min_value=min_date, max_value=max_date, value=min_date)
    with col2:
        end_date = st.date_input("结束日期", min_value=min_date, max_value=max_date, value=max_date)

    if keyword:
        # ✅ 过滤公司名（模糊匹配 + 忽略大小写）
        df_filtered = df[
            df['公司名称'].astype(str).str.lower().str.contains(keyword.strip().lower()) &
            (df['发票日期'] >= pd.to_datetime(start_date)) &
            (df['发票日期'] <= pd.to_datetime(end_date))
        ].copy()

        if df_filtered.empty:
            st.warning("未找到符合条件的发票数据，请检查公司名或日期范围。")
            return

        # ✅ 计算差额
        df_filtered['差额'] = df_filtered['发票金额'].fillna(0) - df_filtered['实际支付金额'].fillna(0)

        # ✅ 日期格式统一
        df_filtered['发票日期'] = pd.to_datetime(df_filtered['发票日期']).dt.strftime('%Y-%m-%d')
        df_filtered['开支票日期'] = pd.to_datetime(df_filtered['开支票日期']).dt.strftime('%Y-%m-%d')

        # ✅ 排序（部门，发票日期）
        df_filtered = df_filtered.sort_values(by=['部门', '发票日期'])

        # ✅ 生成带有汇总行的表格
        final_df = pd.DataFrame()
        for dept, group in df_filtered.groupby('部门'):
            final_df = pd.concat([final_df, group])
            subtotal = group[['发票金额', '实际支付金额','TPS','TVQ', '差额']].sum().to_frame().T
            subtotal['公司名称'] = keyword
            subtotal['部门'] = f"{dept} 汇总"
            subtotal['发票号'] = ''
            subtotal['付款支票号'] = ''
            subtotal['发票日期'] = ''
            subtotal['开支票日期'] = ''
            final_df = pd.concat([final_df, subtotal], ignore_index=True)

        # ✅ 添加总计行
        total = df_filtered[['发票金额', '实际支付金额', 'TPS','TVQ','差额']].sum().to_frame().T
        total['公司名称'] = keyword
        total['部门'] = '总计'
        total['发票号'] = ''
        total['付款支票号'] = ''
        total['发票日期'] = ''
        total['开支票日期'] = ''
        final_df = pd.concat([final_df, total], ignore_index=True)

        final_df = final_df[['公司名称', '部门', '发票号', '发票日期', '开支票日期', '付款支票号', '发票金额', '实际支付金额', 'TPS','TVQ','差额']]

        # ✅ 着色
        def highlight_summary(row):
            if isinstance(row['部门'], str):
                if row['部门'].endswith('汇总'):
                    return ['background-color: #D6EAF8'] * len(row)
                elif row['部门'] == '总计':
                    return ['background-color: #FADBD8'] * len(row)
            return [''] * len(row)

        st.markdown("### 📋 查询结果：按部门分类显示")

        st.info("💡 如果“差额”为正数，表示我们**尚未支付的金额**（即欠款）；如果“差额”为负数，表示我们**多付了金额**。")
        st.info("💡 支票号nan 代表 尚未使用支票付款")

        
        #final_df['付款支票号'] = final_df['付款支票号'].fillna('').astype(str)


        st.dataframe(
            final_df.style
            .apply(highlight_summary, axis=1)
            .format({
                '发票金额': '{:,.2f}',
                '实际支付金额': '{:,.2f}',
                '差额': '{:,.2f}',
                'TPS': '{:,.2f}',
                'TVQ': '{:,.2f}',
            }),
            use_container_width=True
        )
