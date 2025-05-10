import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from modules.data_loader import load_supplier_data

# ✅ 加载中文字体以防止图表中出现乱码
from fonts.fonts import load_chinese_font
my_font = load_chinese_font()

# ✅ 导入统一的数据加载函数


def paid_cheques_query():
    df = load_supplier_data()

    # --- 侧边栏筛选条件 ---
    st.sidebar.subheader("筛选条件")
    min_date = df['开支票日期'].min()
    max_date = df['开支票日期'].max()
    start_date = st.sidebar.date_input("开始日期", value=min_date)
    end_date = st.sidebar.date_input("结束日期", value=max_date)

    # --- 筛选部门 ---
    all_departments = sorted(df['部门'].dropna().unique().tolist())
    department_options = ["全部"] + all_departments
    selected_raw = st.sidebar.multiselect("选择部门", department_options, default=["全部"])
    selected_departments = all_departments if "全部" in selected_raw or not selected_raw else selected_raw

    # --- 根据选择筛选数据 ---
    filtered = df[
        (df['开支票日期'].notna()) &
        (df['开支票日期'] >= pd.to_datetime(start_date)) &
        (df['开支票日期'] <= pd.to_datetime(end_date)) &
        (df['部门'].isin(selected_departments))
    ].copy()

    # --- 构建“各部门付款汇总”表格 ---
    summary_table = (
        filtered.groupby('部门')[['实际支付金额', 'TPS', 'TVQ']]
        .sum()
        .reset_index()
    )

    # 添加总计行
    total_row = pd.DataFrame([{
        '部门': '总计',
        '实际支付金额': summary_table['实际支付金额'].sum(),
        'TPS': summary_table['TPS'].sum(),
        'TVQ': summary_table['TVQ'].sum()
    }])
    summary_table = pd.concat([summary_table, total_row], ignore_index=True)

    # 设置颜色：总计行为淡红色
    def highlight_total(row):
        if row['部门'] == '总计':
            return ['background-color: #FADBD8'] * len(row)
        else:
            return [''] * len(row)

    st.info("##### 💡 付款支票信息查询的搜索时间是按照 *📆开支票日期* 进行设置的，方便用户查询某段时间内所开支票的信息")
    
    # --- 展示“各部门付款汇总”表格 ---
    st.markdown("### 🧾 各部门付款金额汇总")
    st.dataframe(
        summary_table.style
        .apply(highlight_total, axis=1)
        .format({
            '实际支付金额': '{:,.2f}',
            'TPS': '{:,.2f}',
            'TVQ': '{:,.2f}'
        }),
        use_container_width=True
    )

    # --- 构建“付款支票信息”详情表格 ---
    def sort_cheques(df_sub):
        df_sub = df_sub.copy()
        df_sub['支票分类'] = df_sub['付款支票号'].apply(lambda x: 0 if x.isnumeric() else 1)
        df_sub['支票排序值'] = df_sub['付款支票号'].apply(lambda x: int(x) if x.isnumeric() else float('inf'))
        return df_sub.sort_values(by=['支票分类', '支票排序值'])

    summary_raw = (
        filtered.groupby(['部门', '付款支票号', '公司名称'])
        .agg({
            '发票号': lambda x: ",".join(x.dropna().unique()),
            '开支票日期': 'first',
            '实际支付金额': 'sum',
            'TPS': 'sum',
            'TVQ': 'sum'
        })
        .reset_index()
    )

    summary = sort_cheques(summary_raw)

    final = pd.DataFrame()
    for dept, df_dept in summary.groupby('部门'):
        final = pd.concat([final, df_dept])
        subtotal = df_dept[['实际支付金额', 'TPS', 'TVQ']].sum().to_frame().T
        subtotal['部门'] = f"{dept} 汇总"
        subtotal['付款支票号'] = ''
        subtotal['公司名称'] = ''
        subtotal['发票号'] = ''
        subtotal['开支票日期'] = ''
        final = pd.concat([final, subtotal], ignore_index=True)

    total = summary[['实际支付金额', 'TPS', 'TVQ']].sum().to_frame().T
    total['部门'] = '总计'
    total['付款支票号'] = ''
    total['公司名称'] = ''
    total['发票号'] = ''
    total['开支票日期'] = ''
    final = pd.concat([final, total], ignore_index=True)

    final = final[['部门', '付款支票号', '公司名称', '发票号','开支票日期', '实际支付金额', 'TPS', 'TVQ']]

    # 着色：小计和总计行
    def highlight_summary(row):
        if isinstance(row['部门'], str):
            if row['部门'].endswith("汇总"):
                return ['background-color: #E8F6F3'] * len(row)
            elif row['部门'] == '总计':
                return ['background-color: #FADBD8'] * len(row)
        return [''] * len(row)

    # --- 展示“付款支票信息”详细表格 ---
    st.markdown("### 📝 XINYA超市 *付款支票* 信息明细")
    #st.info("##### 📝 XINYA超市 *付款支票* 信息明细")
    #st.markdown("<h3 style='color:#117A65;'>XINYA超市 <span style='color:purple;'>付款支票信息明细</span></h3>", unsafe_allow_html=True)
    
    # 先转换一次就好
    final['开支票日期'] = pd.to_datetime(final['开支票日期'], errors='coerce').dt.date
    
    st.dataframe(
        final.style
        .apply(highlight_summary, axis=1)
        .format({
            '实际支付金额': "{:,.2f}",
            'TPS': "{:,.2f}",
            'TVQ': "{:,.2f}"
            
        }),
        use_container_width=True
    )

    import plotly.express as px
    from datetime import timedelta

    import plotly.express as px

    from datetime import timedelta


    # 1. 读取数据
    df_paid_cheques = load_supplier_data()

    # 2. 数据清理
    df_paid_cheques['实际支付金额'] = pd.to_numeric(df_paid_cheques['实际支付金额'], errors='coerce')
    df_paid_cheques['开支票日期'] = pd.to_datetime(df_paid_cheques['开支票日期'], errors='coerce')
    df_paid_cheques = df_paid_cheques.dropna(subset=['开支票日期', '实际支付金额'])

    # 3. 去重
    #df_paid_cheques = df_paid_cheques.drop_duplicates(subset=['付款支票号', '实际支付金额', '开支票日期'])

    # 4. 过滤有效数据
    paid_df = df_paid_cheques[df_paid_cheques['实际支付金额'].notna()]

    # 5. 按开支票日期的月份汇总
    paid_df['月份'] = pd.to_datetime(paid_df['开支票日期']).dt.to_period('M').astype(str)
    paid_summary = paid_df.groupby(['部门', '月份'])['实际支付金额'].sum().reset_index()
    monthly_totals = paid_df.groupby('月份')['实际支付金额'].sum().reset_index()
    monthly_totals_dict = monthly_totals.set_index('月份')['实际支付金额'].to_dict()

    # 7. 生成部门颜色映射
    unique_departments_paid = sorted(paid_summary['部门'].unique())
    colors_paid = px.colors.qualitative.Dark24
    color_map_paid = {dept: colors_paid[i % len(colors_paid)] for i, dept in enumerate(unique_departments_paid)}

    # 8. 添加提示信息
    paid_summary['总支付金额'] = paid_summary['月份'].map(monthly_totals_dict)
    paid_summary['提示信息'] = paid_summary.apply(
        lambda row: f"所选月份总支付金额：{monthly_totals_dict[row['月份']]:,.0f}<br>部门：{row['部门']}<br>实际付款金额：{row['实际支付金额']:,.0f}",
        axis=1
    )

    # 9. 绘制月度折线图
    fig_paid_month = px.line(
        paid_summary,
        x="月份",
        y="实际支付金额",
        color="部门",
        title="各部门每月实际付款金额",
        markers=True,
        labels={"实际支付金额": "实际付款金额", "月份": "月份"},
        line_shape="linear",
        color_discrete_map=color_map_paid,
        hover_data={'提示信息': True}
    )

    fig_paid_month.update_traces(
        text=paid_summary["实际支付金额"].round(0).astype(int),
        textposition="top center",
        hovertemplate="%{customdata[0]}"
    )

    # 10. 显示图表
    st.title("📊 各部门每月实际付款金额分析")
    st.plotly_chart(fig_paid_month, key="monthly_paid_chart001")

    # 11. 周度分析（可选）
    valid_months = sorted(paid_df['月份'].unique())
    selected_month = st.selectbox("🔎选择查看具体周数据的月份", valid_months)

    # 12. 按周统计
    paid_df['周开始'] = paid_df['开支票日期'] - pd.to_timedelta(paid_df['开支票日期'].dt.weekday, unit='D')
    paid_df['周结束'] = paid_df['周开始'] + timedelta(days=6)
    paid_df['周范围'] = paid_df['周开始'].dt.strftime('%Y-%m-%d') + ' ~ ' + paid_df['周结束'].dt.strftime('%Y-%m-%d')

    weekly_summary_filtered = paid_df[paid_df['月份'] == selected_month].groupby(
        ['部门', '周范围', '周开始', '周结束']
    )['实际支付金额'].sum().reset_index()

    weekly_summary_filtered['周开始'] = pd.to_datetime(weekly_summary_filtered['周开始'])
    weekly_summary_filtered = weekly_summary_filtered.sort_values(by='周开始').reset_index(drop=True)

    weekly_totals = weekly_summary_filtered.groupby('周范围')['实际支付金额'].sum().reset_index()
    weekly_totals_dict = weekly_totals.set_index('周范围')['实际支付金额'].to_dict()

    weekly_summary_filtered['提示信息'] = weekly_summary_filtered.apply(
        lambda row: f"所选周总支付金额：{weekly_totals_dict[row['周范围']]:,.0f}<br>部门：{row['部门']}<br>实际付款金额：{row['实际支付金额']:,.0f}",
        axis=1
    )

    fig_paid_week = px.line(
        weekly_summary_filtered,
        x="周范围",
        y="实际支付金额",
        color="部门",
        title=f"{selected_month} 每周各部门实际付款金额",
        markers=True,
        labels={"实际支付金额": "实际付款金额", "周范围": "周"},
        line_shape="linear",
        color_discrete_map=color_map_paid,
        hover_data={'提示信息': True}
    )

    fig_paid_week.update_traces(
        text=weekly_summary_filtered["实际支付金额"].round(0).astype(int),
        textposition="top center",
        hovertemplate="%{customdata[0]}"
    )

    st.plotly_chart(fig_paid_week, key="weekly_paid_chart001")

