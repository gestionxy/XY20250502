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
    start_date = st.sidebar.date_input("开始日期", value=min_date)
    end_date = st.sidebar.date_input("结束日期", value=max_date)
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

    from datetime import timedelta

    # 1. 读取数据
    df_unpaid_zhexiantu = load_supplier_data()

    # 2. 数据清理
    # !!!XXX筛选未付款记录（付款支票号为空）
    # 筛选未付款记录（付款支票号为空），不能直接使用 支票号 作为 排除选项， 以为有的公司是直接 支票先行转账，所以发票是0，而实际支付金额是10000， 存在支票号982/989，直接使用 支票号进行筛选是错误的
    # 正确的做法是新建一列 【实际差额】列，进行计算实际上没有付款的金额
    #df_unpaid_zhexiantu = df_unpaid_zhexiantu[
        #df_unpaid_zhexiantu['付款支票号'].apply(lambda x: str(x).strip().lower() in ['', 'nan', 'none'])
    #]

    # 将发票金额和实际支付金额转换为数值，处理非数值和空值
    df_unpaid_zhexiantu['发票金额'] = pd.to_numeric(df_unpaid_zhexiantu['发票金额'], errors='coerce').fillna(0)
    df_unpaid_zhexiantu['实际支付金额'] = pd.to_numeric(df_unpaid_zhexiantu['实际支付金额'], errors='coerce').fillna(0)

    # 计算实际差额（未付款金额）
    df_unpaid_zhexiantu['实际差额'] = df_unpaid_zhexiantu['发票金额'] - df_unpaid_zhexiantu['实际支付金额']

    # 处理发票日期，转换为 datetime 格式
    df_unpaid_zhexiantu['发票日期'] = pd.to_datetime(df_unpaid_zhexiantu['发票日期'], errors='coerce')
    #df_unpaid_zhexiantu = df_unpaid_zhexiantu.dropna(subset=['发票日期', '实际差额'])

    # 3. 去重（基于发票号、发票日期、实际差额）
    #df_unpaid_zhexiantu = df_unpaid_zhexiantu.drop_duplicates(subset=['发票号', '发票日期', '实际差额'])

    # 4. 按月份分配（用于月度分析和周度过滤）
    df_unpaid_zhexiantu['月份'] = df_unpaid_zhexiantu['发票日期'].dt.to_period('M').astype(str)

    # 5. 按部门和月份汇总未付款金额
    unpaid_summary = df_unpaid_zhexiantu.groupby(['部门', '月份'])['实际差额'].sum().reset_index()

    # 6. 计算月度总未付款金额
    monthly_totals = df_unpaid_zhexiantu.groupby('月份')['实际差额'].sum().reset_index()
    monthly_totals_dict = monthly_totals.set_index('月份')['实际差额'].to_dict()

    # 7. 生成部门颜色映射
    unique_departments = sorted(unpaid_summary['部门'].unique())
    colors = px.colors.qualitative.Dark24
    color_map = {dept: colors[i % len(colors)] for i, dept in enumerate(unique_departments)}

    # 8. 添加月度提示信息
    unpaid_summary['总未付金额'] = unpaid_summary['月份'].map(monthly_totals_dict)
    unpaid_summary['提示信息'] = unpaid_summary.apply(
        lambda row: f"所选月份总未付金额：{monthly_totals_dict[row['月份']]:,.0f}<br>部门：{row['部门']}<br>未付金额：{row['实际差额']:,.0f}",
        axis=1
    )

    # 9. 绘制月度折线图
    fig_month = px.line(
        unpaid_summary,
        x="月份",
        y="实际差额",
        color="部门",
        title="各部门每月未付账金额",
        markers=True,
        labels={"实际差额": "未付账金额", "月份": "月份"},
        line_shape="linear",
        color_discrete_map=color_map,
        hover_data={'提示信息': True}
    )

    fig_month.update_traces(
        text=unpaid_summary["实际差额"].round(0).astype(int),
        textposition="top center",
        hovertemplate="%{customdata[0]}"
    )

    # 10. 显示月度图表
    #st.title("📊 各部门每月未付账金额分析")
    st.plotly_chart(fig_month, key="monthly_unpaid_chart001")

    # 11. 周度分析
    # 添加周范围（周一到周日）
    df_unpaid_zhexiantu['周开始'] = df_unpaid_zhexiantu['发票日期'] - pd.to_timedelta(df_unpaid_zhexiantu['发票日期'].dt.weekday, unit='D')
    df_unpaid_zhexiantu['周结束'] = df_unpaid_zhexiantu['周开始'] + timedelta(days=6)
    df_unpaid_zhexiantu['周范围'] = df_unpaid_zhexiantu['周开始'].dt.strftime('%Y-%m-%d') + ' ~ ' + df_unpaid_zhexiantu['周结束'].dt.strftime('%Y-%m-%d')

    # 12. 提供月份选择
    valid_months = sorted(df_unpaid_zhexiantu['月份'].unique())
    selected_month = st.selectbox("🔎选择查看具体周数据的月份", valid_months)

    # 13. 按周汇总（包含跨月周的完整记录）
    # 选择所选月份的记录
    month_data = df_unpaid_zhexiantu[df_unpaid_zhexiantu['月份'] == selected_month]

    # 获取该月份涉及的所有周范围
    week_ranges = df_unpaid_zhexiantu[
        (df_unpaid_zhexiantu['发票日期'].dt.to_period('M').astype(str) == selected_month) |
        (df_unpaid_zhexiantu['周开始'].dt.to_period('M').astype(str) == selected_month) |
        (df_unpaid_zhexiantu['周结束'].dt.to_period('M').astype(str) == selected_month)
    ]['周范围'].unique()

    # 按周汇总（基于发票日期在周范围内的记录）
    weekly_summary_filtered = df_unpaid_zhexiantu[
        (df_unpaid_zhexiantu['周范围'].isin(week_ranges)) &
        (df_unpaid_zhexiantu['发票日期'] >= df_unpaid_zhexiantu['周开始']) &
        (df_unpaid_zhexiantu['发票日期'] <= df_unpaid_zhexiantu['周结束'])
    ].groupby(
        ['部门', '周范围', '周开始', '周结束']
    )['实际差额'].sum().reset_index()

    # 确保按周开始日期排序
    weekly_summary_filtered['周开始'] = pd.to_datetime(weekly_summary_filtered['周开始'])
    weekly_summary_filtered = weekly_summary_filtered.sort_values(by='周开始').reset_index(drop=True)

    # 14. 计算周度总未付款金额
    weekly_totals = weekly_summary_filtered.groupby('周范围')['实际差额'].sum().reset_index()
    weekly_totals_dict = weekly_totals.set_index('周范围')['实际差额'].to_dict()

    # 15. 验证 2025-04-28 ~ 2025-05-04 周的金额
    if '2025-04-28 ~ 2025-05-04' in weekly_totals_dict:
        week_total = weekly_totals_dict['2025-04-28 ~ 2025-05-04']
        print(f"2025-04-28 ~ 2025-05-04 周未付总金额：{week_total}")
        week_data = df_unpaid_zhexiantu[
            (df_unpaid_zhexiantu['发票日期'] >= '2025-04-28') &
            (df_unpaid_zhexiantu['发票日期'] <= '2025-05-04')
        ]
        print("2025-04-28 ~ 2025-05-04 周记录数：", len(week_data))
        print("2025-04-28 ~ 2025-05-04 周记录明细：", week_data[['部门', '发票日期', '发票号', '实际差额']])

    # 16. 添加周度提示信息
    weekly_summary_filtered['提示信息'] = weekly_summary_filtered.apply(
        lambda row: f"所选周总未付金额：{weekly_totals_dict[row['周范围']]:,.0f}<br>部门：{row['部门']}<br>未付金额：{row['实际差额']:,.0f}",
        axis=1
    )

    # 17. 绘制周度折线图
    # 确保 X 轴按时间顺序排列
    fig_week = px.line(
        weekly_summary_filtered,
        x="周范围",
        y="实际差额",
        color="部门",
        title=f"{selected_month} 每周各部门未付账金额",
        markers=True,
        labels={"实际差额": "未付账金额", "周范围": "周"},
        line_shape="linear",
        color_discrete_map=color_map,
        hover_data={'提示信息': True},
        category_orders={"周范围": weekly_summary_filtered['周范围'].tolist()}  # 明确指定 X 轴顺序
    )

    fig_week.update_traces(
        text=weekly_summary_filtered["实际差额"].round(0).astype(int),
        textposition="top center",
        hovertemplate="%{customdata[0]}"
    )

    # 18. 显示周度图表
    st.plotly_chart(fig_week, key="weekly_unpaid_chart001")



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



