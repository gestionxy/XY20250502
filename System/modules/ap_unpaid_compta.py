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

    df = load_supplier_data()

    # 因为会计做账，本次进处理采购类 purchase 的项目，因此仅筛选保留如下 部门项目
    # 【如需仅保留 采购类项目，请取消注释】
    #selected_departments = ['冻部', '厨房', '杂货', '牛奶生鲜', '肉部', '菜部', '运输', '酒水', '鱼部']
    #df = df[df['部门'].isin(selected_departments)].reset_index(drop=True)
        
    # 1.1 首先排除出 直接用信用卡VISA-1826 进行支付的，信用卡支付的不是公司支票账户
    df = df[~df['公司名称'].isin(['SLEEMAN', 'Arc-en-ciel','Ferme vallee verte*'])]

    # -------------------------------
    # 2. 日期字段转换为 datetime 类型（一次性）
    # -------------------------------
    df['开支票日期'] = pd.to_datetime(df['开支票日期'], errors='coerce')
    df['发票日期'] = pd.to_datetime(df['发票日期'], errors='coerce')
    df['银行对账日期'] = pd.to_datetime(df['银行对账日期'], errors='coerce')



    # -------------------------------
    # 3. 定义银行对账日期计算函数（通用）
    # -------------------------------
    # 2024-03-15	15号 < 25号 → 本月对账	2024-03-01
    # 2024-03-25	25号 ≥ 25 → 下月对账	2024-04-01
    # 2024-12-30	30号 ≥ 25 → 跨年 → 次年1月	2025-01-01 
    # 2024-06-01	1号 < 25 → 本月对账	2024-06-01

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




    # ——————————————— 目的说明 ———————————————
    # 1) 条件1（mask_star）：
    #    仅在「银行对账日期为空」时，才对「公司名称以 * 结尾」的记录进行自动规则处理；
    #    若该行已有银行对账日期，则视为已对账/已确定，不做改动。
    # 2) 条件2（mask_no_star_and_letter_cheque）：
    #    仅在「开支票日期为空」时，才对「公司名不含 * 且 付款支票号以字母开头」的记录处理；
    #    若该行已有开支票日期，尊重原始数据，不覆盖。
    # 3) 合并条件（mask_target = 条件1 or 条件2），对命中的行：
    #    - 若开支票日期为空：设置 开支票日期 = 发票日期
    #    - 设置 银行假定过账日期 = 开支票日期 + 7 天
    #    - 用 calculate_reconcile_date(银行假定过账日期) 推导 银行对账日期
    #    注：全部用 df.loc[...] 进行就地赋值，避免 SettingWithCopyWarning。

    # ===================== 条件 1 =====================
    # 银行对账日期为空 & 公司名称以 * 结尾
    # - .isna()：仅挑出“银行对账日期为空”的行（为空才需要我们推导）。
    # - .astype(str).str.endswith('*')：对公司名按字面检查是否以星号结尾。
    mask_star = (
        df['银行对账日期'].isna()
        & df['公司名称'].astype(str).str.endswith('*')
    )

    # ===================== 条件 2 =====================
    # 公司名不含 *、付款支票号非空/非'nan'类占位、且“以字母开头”、并且“开支票日期为空”
    # - str.contains(r'\*', na=False)：正则匹配星号，需转义 \*；na=False 让 NaN 当作不含 *（返回 False），防止 NaN 传播。
    # - ~ ... .isin(['', 'nan', 'none', 'null'])：把空串与常见“空值字符串”排除（如 'nan','none','null' 等）。
    # - str.match(r'^[A-Za-z]', na=False)：支票号首字符为字母；na=False 让空值返回 False。
    # - df['开支票日期'].isna()：若已有开支票日期，尊重原始数据，不重复/不覆盖。
    mask_no_star_and_letter_cheque = (
        ~df['公司名称'].astype(str).str.contains(r'\*', na=False)
        & ~df['付款支票号'].astype(str).str.strip().str.lower().isin(['', 'nan', 'none', 'null'])
        & df['付款支票号'].astype(str).str.match(r'^[A-Za-z]', na=False)
        & df['开支票日期'].isna()
    )

    # ===================== 合并目标行 =====================
    # 逻辑“或”合并：满足 条件1 或 条件2 的任意一条即可进入后续处理。
    mask_target = mask_star | mask_no_star_and_letter_cheque

    # ===================== 设置开支票日期（仅空值时） =====================
    # 仅对【目标行】且【开支票日期为空】的行赋值：开支票日期 = 发票日期
    # 说明：
    # - 与 mask_target 联合，保证只处理需要的行；
    # - 再与 df['开支票日期'].isna() 联合，避免覆盖已有的开支票日期（尊重原始数据）。
    df.loc[mask_target & df['开支票日期'].isna(), '开支票日期'] = df.loc[
        mask_target & df['开支票日期'].isna(), '发票日期'
    ]

    # ===================== 计算“银行假定过账日期” =====================
    # 对【目标行】：银行假定过账日期 = 开支票日期 + 7 天
    # 说明：
    # - 若开支票日期不是 datetime 类型，先用 pd.to_datetime(...) 做容错转换，
    #   再加 Timedelta，避免类型不匹配错误（如字符串与 Timedelta 相加）。
    df.loc[mask_target, '银行假定过账日期'] = (
        pd.to_datetime(df.loc[mask_target, '开支票日期'], errors='coerce') + pd.Timedelta(days=7)
    )

    # ===================== 计算“银行对账日期” =====================
    # 对【目标行】：根据“银行假定过账日期”计算“银行对账日期”。
    # 说明：
    # - calculate_reconcile_date(日期) 通常用于把 +7 天后的日期“对齐”为银行实际过账日，
    #   比如跳过周末/法定假日等（具体取决于你自定义的函数逻辑）。
    df.loc[mask_target, '银行对账日期'] = df.loc[mask_target, '银行假定过账日期'].apply(
        calculate_reconcile_date
    )



    # ✅ 条件3：开支票日期 <= 2025-04-20 且 银行对账日期为空
    # 为什么这样设置呢？ 主要是处理之前很多的数据，因为之前没有对账日期，所以需要处理
    extra_mask = (
        (df['开支票日期'].notna()) &
        (df['开支票日期'] <= pd.Timestamp("2025-04-20")) &
        (df['银行对账日期'].isna())
    )

    # ✅ 设定：银行假定过账日期 = 开支票日期 + 7天
    df.loc[extra_mask, '银行假定过账日期'] = df.loc[extra_mask, '开支票日期'] + pd.Timedelta(days=7)

    # ✅ 重新计算：银行对账日期 = calculate_reconcile_date(银行假定过账日期)
    df.loc[extra_mask, '银行对账日期'] = df.loc[extra_mask, '银行假定过账日期'].apply(calculate_reconcile_date)



    # # 安全检查
    # min_date = df['发票日期'].min()
    # max_date = df['发票日期'].max()
    # if pd.isna(min_date) or pd.isna(max_date):
    #     st.warning("⚠️ 发票日期无效，无法生成筛选日期。")
    #     st.stop()

    # # ✅ 构建每月1号作为起始日期选项
    # start_dates = pd.date_range(
    #     start=min_date.replace(day=1),
    #     end=(max_date + pd.DateOffset(months=1)).replace(day=1),
    #     freq='MS'
    # ).to_list()

    # # ✅ 构建每月25号作为结束日期选项（从下月起）
    # first_end_date = (min_date + pd.DateOffset(months=1)).replace(day=25)
    # last_end_date = (max_date + pd.DateOffset(months=1)).replace(day=25)
    # end_dates = pd.date_range(
    #     start=first_end_date,
    #     end=last_end_date,
    #     freq='M'
    # ).to_list()
    # end_dates = [d.replace(day=25) for d in end_dates]

    # 安全检查
    min_date = df['发票日期'].min()
    max_date = df['发票日期'].max()
    if pd.isna(min_date) or pd.isna(max_date):
        st.warning("⚠️ 发票日期无效，无法生成筛选日期。")
        st.stop()

    # 统一转成 datetime，防止类型不稳
    min_date = pd.to_datetime(min_date)
    max_date = pd.to_datetime(max_date)

    # ✅ 构建每月1号作为起始日期选项
    start_dates = pd.date_range(
        start=min_date.replace(day=1),
        end=(max_date + pd.DateOffset(months=1)).replace(day=1),
        freq='MS'
    ).to_list()

    # ✅ 构建每月25号作为结束日期选项（稳定版：不再用 freq='M'）
    first_end_date = (min_date + pd.DateOffset(months=1)).replace(day=25)
    last_end_date = (max_date + pd.DateOffset(months=1)).replace(day=25)

    end_dates = []
    current = first_end_date

    while current <= last_end_date:
        end_dates.append(current)
        current = (current + pd.DateOffset(months=1)).replace(day=25)

    # ✅ Streamlit UI 美化 - 两栏并排显示
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.selectbox(
            "🟢 起始日期（每月1号）",
            options=start_dates,
            format_func=lambda x: x.strftime('%Y-%m-%d'),
            index=0
        )

    with col2:
        selected_option = st.selectbox(
            "🔴 结束日期（每月25号 或 自定义）",
            options= ["自定义日期"] + end_dates,
            format_func=lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else str(x),
            index=len(end_dates) - 1
        )

        if selected_option == "自定义日期":
            end_date = st.date_input("📅 请选择自定义结束日期")
            end_date = pd.to_datetime(end_date)  # ✅ 统一为 Timestamp
        else:
            end_date = selected_option



    # ✅ 初步筛选日期范围
    if start_date > end_date:
        st.error("❌ 起始日期不能晚于结束日期，请重新选择。")
        st.stop()

    filtered_df = df[(df['发票日期'] >= start_date) & (df['发票日期'] <= end_date)]



    # ✅ 部门选择下拉框
    purchase_departments = ['冻部', '厨房', '杂货', '肉部', '菜部', '美妆', '酒水', '面包', '鱼部', '牛奶生鲜']
    dept_choice = st.selectbox("🏷️ 请选择部门类型", ['全部', '采购类: 冻部 / 厨房 / 杂货 / 肉部 / 菜部 / 美妆 / 酒水 / 面包 / 鱼部 / 牛奶生鲜'])

    # ✅ 根据部门类型进一步筛选
    if dept_choice == '采购类: 冻部 / 厨房 / 杂货 / 肉部 / 菜部 / 美妆 / 酒水 / 面包 / 鱼部 / 牛奶生鲜':
        filtered_df = filtered_df[filtered_df['部门'].isin(purchase_departments)]


    # ✅ 同步原始金额
    filtered_df['银行实际支付金额'] = df['实际支付金额']

    # ✅ 1. 条件判断：银行对账日期为空或晚于用户选定的结束日期，则记为未支付,标记为0
    filtered_df['银行实际支付金额'] = filtered_df.apply(
        lambda row: 0 if pd.isna(row['银行对账日期']) or row['银行对账日期'] > end_date else row['实际支付金额'],
        axis=1
    )

    # ✅ 2. 新增字段：应付未付额AP
    filtered_df['应付未付额AP'] = filtered_df['发票金额'] - filtered_df['银行实际支付金额']






    # 仅保留并按顺序展示这些列
    cols = [
        '公司名称','部门','发票号','发票日期','发票金额','TPS','TVQ',
        '付款支票号','实际支付金额','付款支票总额','开支票日期',
        '银行对账日期','银行假定过账日期','银行实际支付金额','应付未付额AP'
    ]
    existing_cols = [c for c in cols if c in filtered_df.columns]
    df_show = filtered_df.loc[:, existing_cols].copy()

    # 定义日期列和数值列
    date_cols = ['发票日期','开支票日期','银行对账日期','银行假定过账日期']
    num_cols  = ['发票金额','TPS','TVQ','实际支付金额','付款支票总额','银行实际支付金额','应付未付额AP']

    # 统一为 datetime（显示时用 YYYY-MM-DD）
    for c in [x for x in date_cols if x in df_show.columns]:
        try:
            df_show[c] = pd.to_datetime(df_show[c], errors='coerce').dt.tz_localize(None)
        except TypeError:
            df_show[c] = pd.to_datetime(df_show[c], errors='coerce')

    # 数值列转数值并保留两位小数
    for c in [x for x in num_cols if x in df_show.columns]:
        df_show[c] = pd.to_numeric(df_show[c], errors='coerce').round(2)

    st.info("数据 银行对账 处理完成，请查看结果。")

    # 去除 应付未付额AP 为空的数据以及等于0的数据
    # 转成数值并保留两位小数
    df_show1 = df_show.copy() 
    df_show1['应付未付额AP'] = pd.to_numeric(df_show1['应付未付额AP'], errors='coerce').round(2)
    # 去除为空和等于 0 的行
    df_show1 = df_show1[df_show1['应付未付额AP'].notna() & (df_show1['应付未付额AP'] != 0)]


    st.success(
        f"📋 共筛选出 {len(df_show1)} 条记录，"
        f"发票总金额：{filtered_df['发票金额'].sum():,.2f}，"
        f"银行实际支付金额：{filtered_df['银行实际支付金额'].sum():,.2f}，"
        f"应付未付额AP：{filtered_df['应付未付额AP'].sum():,.2f}"
    )


    st.info("仅包含 应付未付额AP ")
    # 用 column_config 控制显示格式（日期 yyyy-mm-dd，数值保留两位）
    st.dataframe(
        df_show1,
        use_container_width=True,
        column_config={
            **{c: st.column_config.DateColumn(format="YYYY-MM-DD") for c in date_cols if c in df_show1.columns},
            **{c: st.column_config.NumberColumn(format="%.2f") for c in num_cols if c in df_show1.columns},
        }
    )



    st.info("完整数据")
    # 用 column_config 控制显示格式（日期 yyyy-mm-dd，数值保留两位）
    st.dataframe(
        df_show,
        use_container_width=True,
        column_config={
            **{c: st.column_config.DateColumn(format="YYYY-MM-DD") for c in date_cols if c in df_show.columns},
            **{c: st.column_config.NumberColumn(format="%.2f") for c in num_cols if c in df_show.columns},
        }
    )









    # ✅ 3. 汇总（按部门）
    grouped_df = filtered_df.groupby('部门', as_index=False)[
        ['发票金额', 'TPS', 'TVQ', '银行实际支付金额', '应付未付额AP']
    ].sum().round(2)

    # ✅ 4. 添加总计行
    total_row = grouped_df[['发票金额', 'TPS', 'TVQ', '银行实际支付金额', '应付未付额AP']].sum().round(2)
    total_row['部门'] = '总计'
    grouped_df = pd.concat([grouped_df, pd.DataFrame([total_row])], ignore_index=True)

    # ✅ 5. 样式：总计行淡红色
    def highlight_total_row(row):
        return ['background-color: #ffe6e6'] * len(row) if row['部门'] == '总计' else [''] * len(row)

    styled_summary_df = (
        grouped_df
        .style
        .apply(highlight_total_row, axis=1)
        .format({
            '发票金额': '{:,.2f}',
            'TPS': '{:,.2f}',
            'TVQ': '{:,.2f}',
            '银行实际支付金额': '{:,.2f}',
            '应付未付额AP': '{:,.2f}',
        })
    )

    # ✅ 6. 显示汇总表
    st.success(
        f"📋 共筛选出 {len(filtered_df)} 条记录，"
        f"发票总金额：{filtered_df['发票金额'].sum():,.2f}，"
        f"银行实际支付金额：{filtered_df['银行实际支付金额'].sum():,.2f}，"
        f"应付未付额AP：{filtered_df['应付未付额AP'].sum():,.2f}"
    )

    st.subheader("📊 按部门汇总应付未付情况")
    st.dataframe(styled_summary_df, use_container_width=True)


    # ✅ 展示提示
    st.info("📂 发票明细已折叠，如需查看请展开下方模块并选择部门查看。")

    # ✅ 保留需要展示的列
    display_columns = [
        '公司名称', '部门', '发票号', '发票金额','实际支付金额', '银行实际支付金额',
        '应付未付额AP',  'TPS', 'TVQ',
        '付款支票号', '付款支票总额', '发票日期', '开支票日期', '银行对账日期'
    ]

    # ✅ 格式化日期列
    filtered_display_df = filtered_df[display_columns].copy()
    date_cols = ['发票日期', '开支票日期', '银行对账日期']
    for col in date_cols:
        filtered_display_df[col] = pd.to_datetime(filtered_display_df[col], errors='coerce').dt.strftime('%Y-%m-%d')

    # ✅ 获取部门列表
    department_options = ['全部'] + sorted(filtered_display_df['部门'].dropna().unique().tolist())

    # ✅ 折叠框组件
    with st.expander("📋 点击展开查看【发票明细列表（按部门）】", expanded=False):
        
        # 选择部门
        selected_dept = st.selectbox("🏷️ 请选择要查看的部门：", department_options)

        # 筛选数据
        if selected_dept == '全部':
            df_to_display = filtered_display_df.copy()
        else:
            df_to_display = filtered_display_df[filtered_display_df['部门'] == selected_dept].copy()

        # ✅ 按公司名称 + 发票日期排序
        df_to_display = df_to_display.sort_values(by=['公司名称', '发票日期'])

        # ✅ 金额列
        amount_cols = ['发票金额', 'TPS', 'TVQ', '实际支付金额', '银行实际支付金额', '应付未付额AP']

        # ✅ 按部门分块（或仅一个）
        grouped = df_to_display.groupby('部门') if selected_dept == '全部' else [(selected_dept, df_to_display)]

        for dept, df_grp in grouped:
            st.markdown(f"#### 🏷️ 部门：{dept}（共 {len(df_grp)} 条）")

            # 添加汇总行
            total_row = df_grp[amount_cols].sum().round(2)
            total_row['公司名称'] = '总计'
            total_row['部门'] = dept
            total_row['发票号'] = ''
            total_row['付款支票号'] = ''
            total_row['发票日期'] = ''
            total_row['开支票日期'] = ''
            total_row['银行对账日期'] = ''

            df_display = pd.concat([df_grp, pd.DataFrame([total_row])], ignore_index=True)

            # 样式函数：总计行为淡蓝色
            def highlight_total(row):
                return ['background-color: #e6f0ff'] * len(row) if row['公司名称'] == '总计' else [''] * len(row)

            styled_detail = (
                df_display
                .style
                .apply(highlight_total, axis=1)
                .format({col: '{:,.2f}' for col in amount_cols})
            )

            # 显示表格
            st.dataframe(styled_detail, use_container_width=True)







    

















































#     # -------------------------------
#    # -------------------------------
#     # 第二部分：处理“银行过账日期为空 且 支票号为字母开头”的记录（排除 NaN 和空字符串）
#     # -------------------------------

#     # 条件 1：【银行过账】日期为空
#     mask_null_posting = df['银行过账日期'].isna()

#     # 条件 2：【付款支票号】非空、非'nan'文本、非空格，并以英文字母开头
#     #      公司名称	        部门	 发票号	  发票日期	  发票金额	TPS	    TVQ	   税后净值	付款支票号	实际支付金额	付款支票总额	开支票日期	  支票寄出日期	银行对账日期
#     # Beaudry & Cadrin Inc	酒水	6031806	2024-10-07	4143.49	180.01	359.06	3604.42	PPA-Beaudry	4143.49	        4143.49	      2024-10-30		          ??????
#     # 对于这样的情况，PPA-Beaudry 但没有具有的银行过账日期，我们要计算 银行对账日期， 因此我们设置条件 发票日期 + 10 天

#     mask_letter_cheque = (
#         df['付款支票号'].notna() &  # 不是实际 NaN（np.nan）
#         df['付款支票号'].astype(str).str.strip().str.lower().ne('nan') &  # 排除 'nan' 字符串
#         df['付款支票号'].astype(str).str.strip().ne('') &  # 排除空字符串
#         df['付款支票号'].astype(str).str.match(r'^[A-Za-z]')  # 确保以英文字母开头
#     )

#     # 综合条件
#     mask_letter_cheque_null_posting = mask_null_posting & mask_letter_cheque

#     # 银行过账日期填补：优先使用开支票日期，否则为发票日期 + 10 天
#     df.loc[mask_letter_cheque_null_posting, '银行过账日期'] = np.where(
#         df.loc[mask_letter_cheque_null_posting, '开支票日期'].notna(),
#         df.loc[mask_letter_cheque_null_posting, '开支票日期'],
#         df.loc[mask_letter_cheque_null_posting, '发票日期'] + pd.to_timedelta(10, unit='d')
#     )

#     # 银行对账日期生成：根据银行过账日期，应用周期归整逻辑
#     df.loc[mask_letter_cheque_null_posting, '银行对账日期'] = (
#         df.loc[mask_letter_cheque_null_posting, '银行过账日期']
#         .apply(calculate_reconcile_date)
#     )
    
#     #st.info("##### 💡 xxxx（会计版）")
#     #st.dataframe(style_dataframe(df), use_container_width=True)



#     # 在此处进行数据数据赋值，因为是 会计做账使用，因此 我们按照 发票日期 和 银行对账日期 进行操作
#     # 首先规范 df 银行对账日期 的时间格式，方便之后进行操作
#     #df['银行对账日期'] = pd.to_datetime(df['银行对账日期'], errors='coerce')  # 保持为 datetime 类型以便后续提取年月


#     # 假设 df 是原始发票数据，包括以下列：
#     # 发票日期、发票金额、实际支付金额、银行对账日期、部门等

#     # ========= [1] 侧边栏选择条件 =========
#     st.sidebar.subheader("筛选条件")

#     # 自动获取发票日期范围，便于用户选择
#     min_date, max_date = df['发票日期'].min(), df['发票日期'].max()
#     start_date = st.sidebar.date_input("开始日期", value=min_date)
#     end_date = st.sidebar.date_input("结束日期", value=max_date)

#     # 用户筛选部门（例如 ["肉部", "蔬菜", "酒水"]）
#     departments = get_selected_departments(df)

#     # ========= [2] 筛选发票日期在范围内的记录 =========
#     # 例如：只保留发票日期在 2024-03-01 至 2024-04-30 之间的记录
#     mask_invoice_range = (
#         df['发票日期'] >= pd.to_datetime(start_date)
#     ) & (
#         df['发票日期'] <= pd.to_datetime(end_date)
#     )

#     # 生成筛选结果子集
#     df_filtered = df[mask_invoice_range].copy()

#     # 示例：
#     # 发票号 A001 | 发票日期: 2024-03-10 | 发票金额: 1000 | 实际支付金额: 1000 | 银行对账日期: 2024-03-15  ✅
#     # 发票号 A002 | 发票日期: 2024-02-15 → ❌（不在范围内被排除）

#     # ========= [3] 构造屏蔽条件，删除“对账完成”的记录 =========
#     # 规则：
#     # - 银行对账日期不为空，且也在时间范围内
#     # - 发票金额 == 实际支付金额（对账完成）

#     mask_to_exclude = (
#         df_filtered['银行对账日期'].notna() &  # 非空说明已过账
#         (df_filtered['银行对账日期'] >= pd.to_datetime(start_date)) &
#         (df_filtered['银行对账日期'] <= pd.to_datetime(end_date)) &
#         ((df_filtered['发票金额'] - df_filtered['实际支付金额'].fillna(0)) == 0)
#     )

#     # 示例（将被排除）：
#     # 发票号 A003 | 发票金额: 1500 | 实际支付金额: 1500 | 银行对账日期: 2024-03-25 ✅（完全对账 → 排除）

#     # 示例（将保留）：
#     # 发票号 A004 | 发票金额: 2000 | 实际支付金额: 1500 → 差额 ≠ 0 → 保留
#     # 发票号 A005 | 银行对账日期为空 → 尚未过账 → 保留

#     # ========= [4] 去除被屏蔽的记录，得到最终保留的结果 =========
#     df = df_filtered[~mask_to_exclude].reset_index(drop=True)

#     # ========= [5] 对“尚未过账”的记录，将其实际支付金额清零 =========
#     # 原因：这些发票虽然在范围内，但还未处理，所以视为“尚未支付”

#     mask_no_posting_date = df['银行对账日期'].isna()
#     df.loc[mask_no_posting_date, '实际支付金额'] = 0

#     # 示例：
#     # 发票号 A006 | 发票金额: 1800 | 实际支付金额: 1800 | 银行对账日期: None → 实际支付金额清零为 0

#     # ========= [可选：按部门进一步过滤] =========
#     # 如果用户选择了特定部门，也可继续按部门筛选
#     # df = df[df['部门'].isin(departments)]

    
#     #st.info("##### 💡 应付未付（会计版）")
#     #st.dataframe(style_dataframe(df), use_container_width=True)


#     # ✅ 只过滤时间，不筛选部门
#     filtered_time_only = df[
#         (df['发票日期'] >= pd.to_datetime(start_date)) &
#         (df['发票日期'] <= pd.to_datetime(end_date))
#     ].copy()
    
#     filtered_time_only['实际支付金额'] = filtered_time_only['实际支付金额'].fillna(0)
#     filtered_time_only['发票金额'] = filtered_time_only['发票金额'].fillna(0)
#     filtered_time_only['应付未付差额'] = filtered_time_only['发票金额'] - filtered_time_only['实际支付金额']

#     # ✅ 筛选部门
#     filtered = filtered_time_only[filtered_time_only['部门'].isin(departments)].copy()

#     # ✅ 部门汇总表
#     summary_table = (
#         filtered.groupby('部门')[['发票金额', '实际支付金额', '应付未付差额','TPS', 'TVQ',]]
#         .sum()
#         .reset_index()
#     )
#     total_row = pd.DataFrame([{
#         '部门': '总计',
#         '发票金额': summary_table['发票金额'].sum(),
#         '实际支付金额': summary_table['实际支付金额'].sum(),
#         '应付未付差额': summary_table['应付未付差额'].sum(),
#         'TPS': summary_table['TPS'].sum(),
#         'TVQ': summary_table['TVQ'].sum(),
#     }])
#     summary_table = pd.concat([summary_table, total_row], ignore_index=True)

#     summary_table['Hors Taxes'] = summary_table['发票金额'] - summary_table['TPS'] - summary_table['TVQ']


#     st.markdown("""
#     <h4 >
#     🧾 <strong>各部门应付未付账单（会计版）金额汇总</strong>
#     </h4>
#     """, unsafe_allow_html=True)
#     st.info("##### 💡 应付未付（会计版）账单是按照🧾发票日期进行筛选设置的，并且按照 银行对账单日期 作为实际付款日期")
#     #st.markdown("<h4 style='color:#196F3D;'>📋 各部门<span style='color:red;'>应付未付</span>账单金额汇总 </h4>", unsafe_allow_html=True)
#     st.dataframe(style_dataframe(summary_table), use_container_width=True)


#     # ✅ 明细表
#     # 步骤 1：将“发票日期”列转换为标准日期类型（datetime.date）
#     # 使用 pd.to_datetime 可自动识别多种格式；errors='coerce' 表示遇到非法值将转换为 NaT（空日期）
#     # 再用 .dt.date 去除时间信息，只保留日期部分（如 2025-05-05）
#     df['发票日期'] = pd.to_datetime(df['发票日期'], errors='coerce').dt.date

#     # 步骤 2：构建最终展示用的 DataFrame（明细 + 小计 + 总计）
#     final = pd.DataFrame()  # 初始化空表格用于后续拼接

#     # 遍历每个部门，分组处理
#     for dept, df_dept in filtered.groupby('部门'):
#         # 对每个部门内的公司分组
#         for company, df_comp in df_dept.groupby('公司名称'):
#             # 拼接当前公司所有明细数据，只保留指定列
#             final = pd.concat([final, df_comp[['部门', '公司名称', '发票号', '发票日期','银行对账日期', '发票金额', '付款支票号','实际支付金额', '应付未付差额','TPS','TVQ']]])
        
#         # 部门小计：对当前部门的金额字段求和（总额、小计）
#         subtotal = df_dept[['发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']].sum().to_frame().T  # 转置成一行 DataFrame
#         subtotal['部门'] = f"{dept} 汇总"   # 特殊标识该行为“XX部门 汇总”
#         subtotal['公司名称'] = ''           # 小计行无公司
#         subtotal['发票号'] = ''
#         subtotal['付款支票号'] = ''             # 小计行无发票号
#         subtotal['发票日期'] = pd.NaT       # 小计行不设日期，用 pd.NaT 保持类型一致
#         subtotal['银行对账日期'] = pd.NaT
#         final = pd.concat([final, subtotal], ignore_index=True)  # 拼接至 final 表格

#     # 所有部门总计：汇总所有金额字段
#     total = filtered[['发票金额', '实际支付金额', '应付未付差额','TPS','TVQ']].sum().to_frame().T
#     total['部门'] = '总计'            # 标记“总计”行
#     total['公司名称'] = ''
#     total['发票号'] = ''
#     total['付款支票号'] = ''
#     total['发票日期'] = pd.NaT        # 同样用 NaT 表示“无日期”
#     subtotal['银行对账日期'] = pd.NaT
#     final = pd.concat([final, total], ignore_index=True)

#     # 步骤 3：格式化“发票日期”为字符串（yyyy-mm-dd）
#     # 必须使用 pd.notnull(d) 来过滤掉 NaT，否则调用 d.strftime 会报错
#     # 这里确保：只有有效日期对象才格式化，否则返回空字符串
#     final['发票日期'] = final['发票日期'].apply(
#         lambda d: d.strftime('%Y-%m-%d') if pd.notnull(d) else ''
#     )

#     # 步骤 4：按指定字段顺序重新排列列，确保前端显示或导出一致
#     final = final[['部门', '公司名称', '发票号', '发票日期','银行对账日期', '发票金额','付款支票号', '实际支付金额', '应付未付差额','TPS','TVQ']]

#     final['Hors Taxes'] = final['发票金额'] - final['TPS'].fillna(0) - final['TVQ'].fillna(0)

#     # 规范日期格式的显示 强制格式化为字符串
#     final['银行对账日期'] = pd.to_datetime(final['银行对账日期'], errors='coerce').dt.strftime('%Y-%m-%d')




#     st.markdown("""
#     <h4 >
#     🧾 <strong>新亚超市应付未付（会计版）账单明细</strong>
#     </h4>
#     """, unsafe_allow_html=True)
#     #st.markdown("<h3 style='color:#1A5276;'>📋 新亚超市<span style='color:red;'>应付未付</span>账单 明细</h3>", unsafe_allow_html=True)
#     st.dataframe(style_dataframe(final), use_container_width=True)

   