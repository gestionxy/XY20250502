import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from itertools import cycle

from ui.sidebar import get_selected_departments
from fonts.fonts import load_chinese_font
from modules.data_loader import load_supplier_data

my_font = load_chinese_font()

def style_dataframe(df):
    def highlight_rows(row):
        if isinstance(row['部门'], str):
            if row['部门'].endswith("汇总"):
                return ['background-color: #E8F6F3'] * len(row)
            elif row['部门'] == '总计':
                return ['background-color: #FADBD8'] * len(row)
        return [''] * len(row)
    return df.style.apply(highlight_rows, axis=1).format({
        '发票金额': "{:,.2f}",
        '实际支付金额': "{:,.2f}",
        '应付未付差额': "{:,.2f}"
    })

def ap_unpaid_query():
    df = load_supplier_data()

    st.sidebar.subheader("筛选条件")
    min_date, max_date = df['发票日期'].min(), df['发票日期'].max()
    start_date = st.sidebar.date_input("开始日期", value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("结束日期", value=max_date, min_value=min_date, max_value=max_date)
    departments = get_selected_departments(df)

    # ✅ 饼图：只过滤时间，不筛选部门
    filtered_time_only = df[
        (df['发票日期'] >= pd.to_datetime(start_date)) &
        (df['发票日期'] <= pd.to_datetime(end_date))
    ].copy()
    filtered_time_only['实际支付金额'] = filtered_time_only['实际支付金额'].fillna(0)
    filtered_time_only['发票金额'] = filtered_time_only['发票金额'].fillna(0)
    filtered_time_only['应付未付差额'] = filtered_time_only['发票金额'] - filtered_time_only['实际支付金额']

    # ✅ 柱状图：筛选部门
    filtered = filtered_time_only[filtered_time_only['部门'].isin(departments)].copy()

    # ✅ 部门汇总表
    summary_table = (
        filtered.groupby('部门')[['发票金额', '实际支付金额', '应付未付差额']]
        .sum()
        .reset_index()
    )
    total_row = pd.DataFrame([{
        '部门': '总计',
        '发票金额': summary_table['发票金额'].sum(),
        '实际支付金额': summary_table['实际支付金额'].sum(),
        '应付未付差额': summary_table['应付未付差额'].sum()
    }])
    summary_table = pd.concat([summary_table, total_row], ignore_index=True)


    st.markdown("""
    <h4 >
    🧾 <strong>各部门应付未付账单金额汇总</strong>
    </h4>
    """, unsafe_allow_html=True)
    st.info("##### 💡 应付未付账单是按照🧾发票日期进行筛选设置的")
    #st.markdown("<h4 style='color:#196F3D;'>📋 各部门<span style='color:red;'>应付未付</span>账单金额汇总 </h4>", unsafe_allow_html=True)
    st.dataframe(style_dataframe(summary_table), use_container_width=True)


    # ✅ 明细表
    # 步骤 1：将“发票日期”列转换为标准日期类型（datetime.date）
    # 使用 pd.to_datetime 可自动识别多种格式；errors='coerce' 表示遇到非法值将转换为 NaT（空日期）
    # 再用 .dt.date 去除时间信息，只保留日期部分（如 2025-05-05）
    df['发票日期'] = pd.to_datetime(df['发票日期'], errors='coerce').dt.date

    # 步骤 2：构建最终展示用的 DataFrame（明细 + 小计 + 总计）
    final = pd.DataFrame()  # 初始化空表格用于后续拼接

    # 遍历每个部门，分组处理
    for dept, df_dept in filtered.groupby('部门'):
        # 对每个部门内的公司分组
        for company, df_comp in df_dept.groupby('公司名称'):
            # 拼接当前公司所有明细数据，只保留指定列
            final = pd.concat([final, df_comp[['部门', '公司名称', '发票号', '发票日期', '发票金额', '实际支付金额', '应付未付差额']]])
        
        # 部门小计：对当前部门的金额字段求和（总额、小计）
        subtotal = df_dept[['发票金额', '实际支付金额', '应付未付差额']].sum().to_frame().T  # 转置成一行 DataFrame
        subtotal['部门'] = f"{dept} 汇总"   # 特殊标识该行为“XX部门 汇总”
        subtotal['公司名称'] = ''           # 小计行无公司
        subtotal['发票号'] = ''             # 小计行无发票号
        subtotal['发票日期'] = pd.NaT       # 小计行不设日期，用 pd.NaT 保持类型一致
        final = pd.concat([final, subtotal], ignore_index=True)  # 拼接至 final 表格

    # 所有部门总计：汇总所有金额字段
    total = filtered[['发票金额', '实际支付金额', '应付未付差额']].sum().to_frame().T
    total['部门'] = '总计'            # 标记“总计”行
    total['公司名称'] = ''
    total['发票号'] = ''
    total['发票日期'] = pd.NaT        # 同样用 NaT 表示“无日期”
    final = pd.concat([final, total], ignore_index=True)

    # 步骤 3：格式化“发票日期”为字符串（yyyy-mm-dd）
    # 必须使用 pd.notnull(d) 来过滤掉 NaT，否则调用 d.strftime 会报错
    # 这里确保：只有有效日期对象才格式化，否则返回空字符串
    final['发票日期'] = final['发票日期'].apply(
        lambda d: d.strftime('%Y-%m-%d') if pd.notnull(d) else ''
    )

    # 步骤 4：按指定字段顺序重新排列列，确保前端显示或导出一致
    final = final[['部门', '公司名称', '发票号', '发票日期', '发票金额', '实际支付金额', '应付未付差额']]




    st.markdown("""
    <h4 >
    🧾 <strong>新亚超市应付未付账单明细</strong>
    </h4>
    """, unsafe_allow_html=True)
    #st.markdown("<h3 style='color:#1A5276;'>📋 新亚超市<span style='color:red;'>应付未付</span>账单 明细</h3>", unsafe_allow_html=True)
    st.dataframe(style_dataframe(final), use_container_width=True)

    st.subheader("📊 各部门应付未付差额图表分析")


    import plotly.express as px
    
    df_unpaid_zhexiantu = load_supplier_data()

    # 2. 筛选未付账数据（付款支票号为空）
    df_unpaid_zhexiantu = df_unpaid_zhexiantu[df_unpaid_zhexiantu['付款支票号'].apply(lambda x: str(x).strip().lower() in ['', 'nan', 'none'])]

    # 3. 处理发票日期，转换为 "YYYY-MM" 格式
    df_unpaid_zhexiantu['月份'] = pd.to_datetime(df_unpaid_zhexiantu['发票日期']).dt.to_period('M').astype(str)

    # 4. 按部门和月份汇总发票金额
    unpaid_summary = df_unpaid_zhexiantu.groupby(['部门', '月份'])['发票金额'].sum().reset_index()

    # 5. 生成部门颜色映射，确保三张图颜色一致
    unique_departments = sorted(unpaid_summary['部门'].unique())
    colors = px.colors.qualitative.Dark24
    color_map = {dept: colors[i % len(colors)] for i, dept in enumerate(unique_departments)}

    # 6. 生成交互式折线图
    fig1 = px.line(
        unpaid_summary,
        x="月份",
        y="发票金额",
        color="部门",
        title="各部门每月未付账金额",
        markers=True,
        labels={"发票金额": "未付账金额", "月份": "月份"},
        line_shape="linear",
        color_discrete_map=color_map
    )

    fig1.update_traces(text=unpaid_summary["发票金额"].round(0).astype(int), textposition="top center")

    # 7. 显示折线图
    #st.title("📊 各部门每月未付账金额分析")
    st.plotly_chart(fig1)

    # 8. 生成交互式柱状图
    bar_df = filtered_time_only.groupby("部门")[['应付未付差额']].sum().reset_index()
    bar_df['应付未付差额'] = bar_df['应付未付差额'].round(0).astype(int)
    fig_bar = px.bar(
        bar_df,
        x="部门",
        y="应付未付差额",
        color="部门",
        title="选中部门应付未付差额",
        text="应付未付差额",
        labels={"应付未付差额": "金额（$ CAD）"},
        color_discrete_map=color_map
    )
    fig_bar.update_traces(textposition="outside")

    # 9. 生成交互式饼状图
    fig_pie = px.pie(
        bar_df,
        names="部门",
        values="应付未付差额",
        title="所有部门占总应付差额比例",
        labels={"应付未付差额": "金额（$ CAD）"},
        hole=0.4,
        color_discrete_map=color_map
    )

    fig_pie.update_traces(marker=dict(colors=[color_map.get(dept, '#CCCCCC') for dept in bar_df['部门']]))

    # 10. 显示柱状图和饼状图
    st.plotly_chart(fig_bar)
    st.plotly_chart(fig_pie)


