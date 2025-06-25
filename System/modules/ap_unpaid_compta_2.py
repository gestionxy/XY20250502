import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta
import numpy as np

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


    # 0. 加载应付账款数据
    # 1. 标准化关键日期列为 datetime 格式（如开支票日期、发票日期等）
    # 2. 定义通用的“银行对账日期”计算逻辑：
    #  - 每月25日～次月24日 → 对账日期统一设为次月1日（如：2024-08-25～09-24 → 2024-09-01）   
    
    # 阶段一：目标公司处理逻辑
    #3. 识别属于目标公司列表的所有行（如 SERVICELAB, Wah Teng 等）
    #4. 对于这些行：
            #- 如果存在“开支票日期” → 设为“银行过账日期”
            # - 否则 → “银行过账日期” = 发票日期 + 10 天

    #5. 根据银行过账日期动态生成银行对账日期：
            #- 使用前面定义的周期逻辑函数


    # 阶段二：异常记录（字母开头支票号 + 无银行过账日期）
    # 6. 筛选所有满足以下两个条件的行：
            # - 银行过账日期为空
            #- 付款支票号是字母开头（如：ETF-Alex、VISA-ciel）

    # 7. 对于这些行：
            #- 如果存在“开支票日期” → 设为银行过账日期
            #- 否则 → 银行过账日期 = 发票日期 + 10天

    # 8. 再次套用通用对账日期函数，生成规范的银行对账日期


    # -------------------------------
    # 1. 载入数据
    # -------------------------------
    df = load_supplier_data()
        
    # 1.1 首先排除出 直接用信用卡VISA-1826 进行支付的
    df = df[~df['公司名称'].isin(['SLEEMAN', 'Arc-en-ciel','Ferme vallee verte'])]

    # -------------------------------
    # 2. 日期字段转换为 datetime 类型（一次性）
    # -------------------------------
    df['开支票日期'] = pd.to_datetime(df['开支票日期'], errors='coerce')
    df['发票日期'] = pd.to_datetime(df['发票日期'], errors='coerce')
    df['银行对账日期'] = pd.to_datetime(df['银行对账日期'], errors='coerce')

    # -------------------------------
    # 3. 定义银行对账日期计算函数（通用）
    # -------------------------------
    def calculate_reconcile_date(posting_date: pd.Timestamp) -> pd.Timestamp:
        if pd.isna(posting_date):
            return pd.NaT
        if posting_date.day >= 25:
            month = (posting_date.month % 12) + 1
            year = posting_date.year if posting_date.month < 12 else posting_date.year + 1
        else:
            month = posting_date.month
            year = posting_date.year
        return pd.Timestamp(f"{year}-{month:02d}-01")

    # -------------------------------
    # 第一部分：处理目标公司列表
    # -------------------------------
    target_companies = [
        'SERVICELAB',
        'Wah Teng',
        'Saputo',
        'Monco',
        'ALEX COULOMBE',
        'Canada Bread',
        'CANADAWIDE FRUIT',
        'Beaudry & Cadrin Inc',
        'Bimbo',
        'IMPERIAL TOBACCO CANADA',
        'BOULANGERIE BLOUIN',
        'korsmet'
    ]

    mask_target = df['公司名称'].isin(target_companies)

    # 银行过账日期填补（目标公司）
    df.loc[mask_target, '银行过账日期'] = np.where(
        df.loc[mask_target, '开支票日期'].notna(),
        df.loc[mask_target, '开支票日期'],
        df.loc[mask_target, '发票日期'] + pd.to_timedelta(10, unit='d')
    )

    # 银行对账日期更新（目标公司）
    df.loc[mask_target, '银行对账日期'] = df.loc[mask_target, '银行过账日期'].apply(calculate_reconcile_date)

    # -------------------------------
   # -------------------------------
    # 第二部分：处理“银行过账日期为空 且 支票号为字母开头”的记录（排除 NaN 和空字符串）
    # -------------------------------

    # 条件 1：银行过账日期为空
    mask_null_posting = df['银行过账日期'].isna()

    # 条件 2：付款支票号非空、非'nan'文本、非空格，并以英文字母开头
    mask_letter_cheque = (
        df['付款支票号'].notna() &  # 不是实际 NaN（np.nan）
        df['付款支票号'].astype(str).str.strip().str.lower().ne('nan') &  # 排除 'nan' 字符串
        df['付款支票号'].astype(str).str.strip().ne('') &  # 排除空字符串
        df['付款支票号'].astype(str).str.match(r'^[A-Za-z]')  # 确保以英文字母开头
    )

    # 综合条件
    mask_letter_cheque_null_posting = mask_null_posting & mask_letter_cheque

    # 银行过账日期填补：优先使用开支票日期，否则为发票日期 + 10 天
    df.loc[mask_letter_cheque_null_posting, '银行过账日期'] = np.where(
        df.loc[mask_letter_cheque_null_posting, '开支票日期'].notna(),
        df.loc[mask_letter_cheque_null_posting, '开支票日期'],
        df.loc[mask_letter_cheque_null_posting, '发票日期'] + pd.to_timedelta(10, unit='d')
    )

    # 银行对账日期生成：根据银行过账日期，应用周期归整逻辑
    df.loc[mask_letter_cheque_null_posting, '银行对账日期'] = (
        df.loc[mask_letter_cheque_null_posting, '银行过账日期']
        .apply(calculate_reconcile_date)
    )
    
    st.info("##### 💡 xxxx（会计版）")
    st.dataframe(style_dataframe(df), use_container_width=True)



    # 在此处进行数据数据赋值，因为是 会计做账使用，因此 我们按照 发票日期 和 银行对账日期 进行操作
    # 首先规范 df 银行对账日期 的时间格式，方便之后进行操作
    #df['银行对账日期'] = pd.to_datetime(df['银行对账日期'], errors='coerce')  # 保持为 datetime 类型以便后续提取年月


    st.sidebar.subheader("筛选条件")
    min_date, max_date = df['发票日期'].min(), df['发票日期'].max()
    start_date = st.sidebar.date_input("开始日期", value=min_date)
    end_date = st.sidebar.date_input("结束日期", value=max_date)
    departments = get_selected_departments(df)



    # 第一步：筛选出“发票日期”落在 [start_date, end_date] 范围内的所有记录
    mask_invoice_range = (
        df['发票日期'] >= pd.to_datetime(start_date)
    ) & (
        df['发票日期'] <= pd.to_datetime(end_date)
    )

    # 提取满足条件的子集，命名为 df_filtered
    df_filtered = df[mask_invoice_range].copy()


    # 在发票日期范围内的目标公司记录中，如果银行对账日期也在范围内 → 视为已支付完成
    mask_target_paid_in_range = (
        df_filtered['公司名称'].isin(target_companies) &
        df_filtered['银行对账日期'].notna() &
        (df_filtered['银行对账日期'] >= pd.to_datetime(start_date)) &
        (df_filtered['银行对账日期'] <= pd.to_datetime(end_date))
    )

    # 设置 实际支付金额 = 发票金额（即默认视为已对账）
    df_filtered.loc[mask_target_paid_in_range, '实际支付金额'] = df_filtered.loc[mask_target_paid_in_range, '发票金额']


    # 第二步：构造一个“要屏蔽的条件”，即这些记录会被删除（不进入最终 df）：
    # 满足以下所有条件的行将被屏蔽：
    #   - 存在“银行对账日期”（非空）
    #   - 银行对账日期也落在 [start_date, end_date] 范围内
    #   - 发票金额 - 实际支付金额 == 0（即已完全对账）
    mask_to_exclude = (
        df_filtered['银行对账日期'].notna() &  # 银行对账日期必须有值
        (df_filtered['银行对账日期'] >= pd.to_datetime(start_date)) &
        (df_filtered['银行对账日期'] <= pd.to_datetime(end_date)) &
        ((df_filtered['发票金额'] - df_filtered['实际支付金额'].fillna(0)) == 0)  # 差额为0，表示对账完成
    )

    # 第三步：将不在屏蔽条件内的记录（即需保留的记录）取出，作为最终结果 df
    df = df_filtered[~mask_to_exclude].reset_index(drop=True)

    # 第四步：将这些保留下来的记录中，符合以下条件的行，其“实际支付金额”清零：
    #   - 银行过账日期为空（即尚未处理）
    # 说明：这些行虽然还没有过账，但发票已进入当前时间范围，所以先清零，等待后续匹配
    mask_no_posting_date = df['银行对账日期'].isna()
    df.loc[mask_no_posting_date, '实际支付金额'] = 0

    
    st.info("##### 💡 应付未付（会计版）")
    st.dataframe(style_dataframe(df), use_container_width=True)


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
            final = pd.concat([final, df_comp[['部门', '公司名称', '发票号', '发票日期','银行对账日期', '发票金额', '付款支票号','实际支付金额', '应付未付差额','TPS','TVQ']]])
        
        # 部门小计：对当前部门的金额字段求和（总额、小计）
        subtotal = df_dept[['发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']].sum().to_frame().T  # 转置成一行 DataFrame
        subtotal['部门'] = f"{dept} 汇总"   # 特殊标识该行为“XX部门 汇总”
        subtotal['公司名称'] = ''           # 小计行无公司
        subtotal['发票号'] = ''
        subtotal['付款支票号'] = ''             # 小计行无发票号
        subtotal['发票日期'] = pd.NaT       # 小计行不设日期，用 pd.NaT 保持类型一致
        subtotal['银行对账日期'] = pd.NaT
        final = pd.concat([final, subtotal], ignore_index=True)  # 拼接至 final 表格

    # 所有部门总计：汇总所有金额字段
    total = filtered[['发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']].sum().to_frame().T
    total['部门'] = '总计'            # 标记“总计”行
    total['公司名称'] = ''
    total['发票号'] = ''
    total['付款支票号'] = ''
    total['发票日期'] = pd.NaT        # 同样用 NaT 表示“无日期”
    subtotal['银行对账日期'] = pd.NaT
    final = pd.concat([final, total], ignore_index=True)

    # 步骤 3：格式化“发票日期”为字符串（yyyy-mm-dd）
    # 必须使用 pd.notnull(d) 来过滤掉 NaT，否则调用 d.strftime 会报错
    # 这里确保：只有有效日期对象才格式化，否则返回空字符串
    final['发票日期'] = final['发票日期'].apply(
        lambda d: d.strftime('%Y-%m-%d') if pd.notnull(d) else ''
    )

    # 步骤 4：按指定字段顺序重新排列列，确保前端显示或导出一致
    final = final[['部门', '公司名称', '发票号', '发票日期','银行对账日期', '发票金额','付款支票号', '实际支付金额', '应付未付差额','TPS','TVQ']]

    final['Hors Taxes'] = final['发票金额'] - final['TPS'].fillna(0) - final['TVQ'].fillna(0)




    st.markdown("""
    <h4 >
    🧾 <strong>新亚超市应付未付（会计版）账单明细</strong>
    </h4>
    """, unsafe_allow_html=True)
    #st.markdown("<h3 style='color:#1A5276;'>📋 新亚超市<span style='color:red;'>应付未付</span>账单 明细</h3>", unsafe_allow_html=True)
    st.dataframe(style_dataframe(final), use_container_width=True)

   