import streamlit as st
import pandas as pd

from ui.sidebar import get_selected_departments
from modules.data_loader import load_supplier_data



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
        '应付未付差额': "{:,.2f}",
        'TPS': "{:,.2f}",
        'TVQ': "{:,.2f}",
        'Hors Taxes': "{:,.2f}",
   
    })

# 此版本专用于会计做账使用，以发票日期为准，截止日期以银行对账日期为准，由此计算是在这段时间内完成付款，未完成的按 应付未付进行处理
def ap_unpaid_query_compta():
    
    df = load_supplier_data()

    # 在此处进行数据数据赋值，因为是 会计做账使用，因此 我们按照 发票日期 和 银行对账日期 进行操作
    # 首先规范 df 银行对账日期 的时间格式，方便之后进行操作
    df['银行对账日期'] = pd.to_datetime(df['银行对账日期'], errors='coerce')  # 保持为 datetime 类型以便后续提取年月


    st.sidebar.subheader("筛选条件")
    min_date, max_date = df['发票日期'].min(), df['发票日期'].max()
    start_date = st.sidebar.date_input("开始日期", value=min_date)
    end_date = st.sidebar.date_input("结束日期", value=max_date)
    departments = get_selected_departments(df)



    # 第一步：先按发票日期范围过滤
    mask_invoice_range = (df['发票日期'] >= pd.to_datetime(start_date)) & \
                        (df['发票日期'] <= pd.to_datetime(end_date))
    df_filtered = df[mask_invoice_range].copy()

    # 第二步：在这个范围内，去掉银行对账日期非空（有数值的删除），且也在这个范围内的行
    mask_bank_match = df_filtered['银行对账日期'].notna() & \
                    (df_filtered['银行对账日期'] >= pd.to_datetime(start_date)) & \
                    (df_filtered['银行对账日期'] <= pd.to_datetime(end_date))

    df = df_filtered[~mask_bank_match].reset_index(drop=True)
    df['实际支付金额'] = 0



    # ✅ 只过滤时间，不筛选部门
    filtered_time_only = df[
        (df['发票日期'] >= pd.to_datetime(start_date)) &
        (df['发票日期'] <= pd.to_datetime(end_date))
    ].copy()
    
    filtered_time_only['实际支付金额'] = filtered_time_only['实际支付金额'].fillna(0)
    filtered_time_only['发票金额'] = filtered_time_only['发票金额'].fillna(0)
    filtered_time_only['应付未付差额'] = filtered_time_only['发票金额'] - filtered_time_only['实际支付金额']

    # ✅ 筛选部门
    filtered = filtered_time_only[filtered_time_only['部门'].isin(departments)].copy()

    # ✅ 部门汇总表
    summary_table = (
        filtered.groupby('部门')[['发票金额', '实际支付金额', '应付未付差额','TPS', 'TVQ',]]
        .sum()
        .reset_index()
    )
    total_row = pd.DataFrame([{
        '部门': '总计',
        '发票金额': summary_table['发票金额'].sum(),
        '实际支付金额': summary_table['实际支付金额'].sum(),
        '应付未付差额': summary_table['应付未付差额'].sum(),
        'TPS': summary_table['TPS'].sum(),
        'TVQ': summary_table['TVQ'].sum(),
    }])
    summary_table = pd.concat([summary_table, total_row], ignore_index=True)

    summary_table['Hors Taxes'] = summary_table['发票金额'] - summary_table['TPS'] - summary_table['TVQ']


    st.markdown("""
    <h4 >
    🧾 <strong>各部门应付未付账单（会计版）金额汇总</strong>
    </h4>
    """, unsafe_allow_html=True)
    st.info("##### 💡 应付未付（会计版）账单是按照🧾发票日期进行筛选设置的，并且按照 银行对账单日期 作为实际付款日期")
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
            final = pd.concat([final, df_comp[['部门', '公司名称', '发票号', '发票日期', '发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']]])
        
        # 部门小计：对当前部门的金额字段求和（总额、小计）
        subtotal = df_dept[['发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']].sum().to_frame().T  # 转置成一行 DataFrame
        subtotal['部门'] = f"{dept} 汇总"   # 特殊标识该行为“XX部门 汇总”
        subtotal['公司名称'] = ''           # 小计行无公司
        subtotal['发票号'] = ''             # 小计行无发票号
        subtotal['发票日期'] = pd.NaT       # 小计行不设日期，用 pd.NaT 保持类型一致
        final = pd.concat([final, subtotal], ignore_index=True)  # 拼接至 final 表格

    # 所有部门总计：汇总所有金额字段
    total = filtered[['发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']].sum().to_frame().T
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
    final = final[['部门', '公司名称', '发票号', '发票日期', '发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']]

    final['Hors Taxes'] = final['发票金额'] - final['TPS'].fillna(0) - final['TVQ'].fillna(0)




    st.markdown("""
    <h4 >
    🧾 <strong>新亚超市应付未付（会计版）账单明细</strong>
    </h4>
    """, unsafe_allow_html=True)
    #st.markdown("<h3 style='color:#1A5276;'>📋 新亚超市<span style='color:red;'>应付未付</span>账单 明细</h3>", unsafe_allow_html=True)
    st.dataframe(style_dataframe(final), use_container_width=True)

   