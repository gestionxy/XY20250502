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

    if filtered_time_only.empty or filtered_time_only['发票金额'].sum() == 0:
        st.info("没有可用于图表的数据（请确认已选择有效时间段和有金额的部门）。")
        return

    pie_df = filtered_time_only.groupby("部门")[['应付未付差额']].sum().reset_index()
    bar_df = pie_df[pie_df['部门'].isin(departments)].copy()

    unique_departments = pie_df['部门'].tolist()
    cmap_colors = plt.get_cmap("tab20").colors
    color_cycle = cycle(cmap_colors)
    color_map = {dept: color for dept, color in zip(unique_departments, color_cycle)}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.bar(
        bar_df['部门'],
        bar_df['应付未付差额'],
        color=[color_map.get(d, '#CCCCCC') for d in bar_df['部门']]
    )

    # ✅ 添加数据标签（整数格式）
    # 遍历 bar_df 中每一行数据，用于在柱子顶部显示对应的应付未付差额
    for idx, row in bar_df.iterrows():
        ax1.text(
            x=idx,  # 横坐标：柱子的索引位置（第几根柱子）
            y=row['应付未付差额'],  # 纵坐标：柱子高度，即应付未付差额的值
            s=f"{int(row['应付未付差额'])}",  # 文本内容：只保留整数，显示在柱子上方
            ha='center',  # 水平对齐方式：居中显示（horizontal alignment）
            va='bottom',  # 垂直对齐方式：紧贴柱子顶部（vertical alignment）
            fontsize=10,  # 字体大小
            fontproperties=my_font  # 使用预设的中文字体，防止中文乱码
        )


    ax1.set_title("选中部门应付未付差额", fontsize=12, fontproperties=my_font)
    ax1.set_ylabel("金额（$ CAD）", fontproperties=my_font)
    ax1.tick_params(axis='x', labelrotation=30)
    ax1.set_xticklabels(bar_df['部门'], fontproperties=my_font)
    ax1.set_yticklabels(ax1.get_yticks(), fontproperties=my_font)
    ax1.grid(True, axis='y', linestyle='--', alpha=0.4)

    wedges, _, autotexts = ax2.pie(
        pie_df['应付未付差额'],
        labels=None,
        autopct=lambda pct: f'{pct:.1f}%' if pct > 0 else '',
        startangle=140,
        colors=[color_map.get(d, '#CCCCCC') for d in pie_df['部门']]
    )
    ax2.set_title("所有部门占总应付差额比例", fontsize=12, fontproperties=my_font)
    ax2.legend(
        wedges,
        pie_df['部门'],
        title="部门",
        loc="center left",
        bbox_to_anchor=(1.0, 0.5),
        fontsize=9,
        prop=my_font
    )
    for autotext in autotexts:
        autotext.set_fontproperties(my_font)

    plt.tight_layout()
    st.pyplot(fig)



