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
    st.info("##### 📝 XINYA超市 *付款支票* 信息明细")
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

    
    # 图表部分
    chart_df = summary.groupby('部门')[['实际支付金额']].sum().reset_index()
    
    if not chart_df.empty:
        st.markdown("### <span style='font-size:18px;'>📊 各部门实际支付金额柱状图</span>", unsafe_allow_html=True)
    
        fig, ax = plt.subplots(figsize=(7, 4))
        cmap = plt.get_cmap("Set3")
        colors = [cmap(i % 12) for i in range(len(chart_df))]
        bars = ax.bar(chart_df['部门'], chart_df['实际支付金额'], color=colors)
    
        # 添加金额标签
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + max(chart_df['实际支付金额']) * 0.01,
                f"{int(height):,}",
                ha='center',
                va='bottom',
                fontsize=10,
                fontproperties=my_font  # ✅ 显式指定中文字体
            )
    
        ax.set_title("按部门分布", fontsize=12, fontproperties=my_font)
        ax.set_ylabel("金额（元）", fontsize=10, fontproperties=my_font)
        ax.set_xlabel("部门", fontsize=10, fontproperties=my_font)
        ax.tick_params(axis='x', labelrotation=30, labelsize=9)
        ax.tick_params(axis='y', labelsize=9)
        ax.set_xticklabels(chart_df['部门'], fontproperties=my_font)
        ax.set_yticklabels(ax.get_yticks(), fontproperties=my_font)
    
        ax.grid(True, axis='y', linestyle='--', alpha=0.4)
        plt.tight_layout()
    
        # 渲染高清图像
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=300)
        st.image(buf.getvalue(), width=600)


