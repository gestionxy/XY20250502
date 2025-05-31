
import streamlit as st
import pandas as pd
from modules.data_loader import load_cash_data
import pandas as pd
from datetime import datetime
from io import BytesIO



def style_dataframe(df):
    def highlight_rows(row):
        value = ""

        # 优先使用 '年月'，否则尝试使用 '供应商'
        if '年月' in row:
            value = row['年月']
        elif '供应商' in row:
            value = row['供应商']

        if isinstance(value, str):
            if value.endswith("汇总"):
                return ['background-color: #D1ECE8'] * len(row)  # 蓝绿色
            elif value == "总计":
                return ['background-color: #FADBD8'] * len(row)  # 粉红色

        return [''] * len(row)

    return df.style.apply(highlight_rows, axis=1).format(precision=2, na_rep="")



def cash_refund():
    
    df_data = load_cash_data()

    # ✅ 步骤 4：将“分类号码”映射为分类名称
    category_mapping = {
        1: '1_PURCHASE', 2: '2_OFFICE', 3: '3_R/M', 4: '4_BANK', 5: '5_BOOKKEEPING',
        6: '6_Auto', 7: '7_EQUIPMENT RENTAL', 8: '8_TEL', 9: '9_Tax & License',
        10: '10_Equip.', 11: '11_LHP', 12: '12_Leasehold Improvement',
        13: '13_Brokerage', 14: '14_Advertisement', 15: '15_Computer',
        16: '16_Hino Truck', 17: '17_Transport', 18: '18_MEALS'
    }
    df_data['分类号码'] = pd.to_numeric(df_data['分类号码'], errors='coerce')
    df_data['分类名称'] = pd.Categorical(df_data['分类号码'].map(category_mapping), categories=category_mapping.values())

    # ✅ 步骤 5：创建分类金额透视表（按“年月” + 分类统计“总金额”）
    category_pivot_nan = df_data.pivot_table(
        index='年月',
        columns='分类名称',
        values='净值',
        aggfunc='sum'
    ).round(2).reset_index()

    # ✅ 步骤 6：创建基础汇总（每月的总金额 / TPS / TVQ）
    core_summary = df_data.groupby('年月')[['总金额', 'TPS', 'TVQ']].sum().round(2).reset_index()

    # ✅ 步骤 7：合并两张表
    merged_summary_nan = pd.merge(core_summary, category_pivot_nan, on='年月', how='outer')
    merged_summary_nan = merged_summary_nan.sort_values(by='年月').reset_index(drop=True)

    # ✅ 步骤 8：将分类金额中为 0.00 的值设为 NaN（只做在分类列上）
    non_category_cols = ['年月', '总金额', 'TPS', 'TVQ']
    category_cols = [col for col in merged_summary_nan.columns if col not in non_category_cols]
    import numpy as np
    for col in category_cols:
        merged_summary_nan[col] = merged_summary_nan[col].apply(lambda x: np.nan if x == 0.00 else x)

    # ✅ 步骤 9：添加汇总行（合计所有数值列）
    # 获取所有非文本列（数值列）并求和
    numeric_cols = merged_summary_nan.select_dtypes(include='number').columns
    summary_values = merged_summary_nan[numeric_cols].sum().round(2)

    # 构造完整的汇总行字典，确保每个列都存在（包括“年月”）
    summary_dict = {col: summary_values.get(col, "") for col in merged_summary_nan.columns}
    summary_dict['年月'] = '总计'  # 或替换为 '供应商'、'月份' 等主标识列

    # 构造 DataFrame 汇总行
    summary_row_df = pd.DataFrame([summary_dict])

    # 拼接到首尾
    merged_summary_nan = pd.concat(
        [summary_row_df, merged_summary_nan, summary_row_df],
        ignore_index=True
    )

    st.markdown("""
        <h4 >
        💸 <strong>Xinya现金账Cash_Refund信息汇总</strong>
        </h4>
        """, unsafe_allow_html=True)
    
    st.info("##### 💡 Cash_Refund信息是按照🧾开支票日期进行统计汇总")
    
    st.dataframe(style_dataframe(merged_summary_nan), use_container_width=True)



    # 假设 df_data 是你已经读取和处理过的数据
    df_cash_detail_by_month = df_data.copy()
    valid_months = sorted(df_cash_detail_by_month['年月'].dropna().unique().tolist())

    # 🎛️ 顶部：标题和下载按钮放同一行
    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown("<h4>💰 <strong>按月份查看付款详情</strong></h4>", unsafe_allow_html=True)

    with col2:
        # 占位：按钮只在数据准备好后启用（留一个占位，避免页面跳动）
        download_placeholder = st.empty()

    # 🔽 下拉框选择月份
    selected_month = st.selectbox("请选择月份：", valid_months)

    # 🔍 根据选定月份筛选数据
    df_filtered = df_cash_detail_by_month[df_cash_detail_by_month['年月'] == selected_month].copy()

    # 按照支票号分组
    cheque_groups = df_filtered.groupby('支票号')

    # 合并导出列表
    all_groups_with_totals = []

    # 展示每个支票号的表格
    for cheque_id, group in cheque_groups:
        group_display = group[['供应商', '小票日期', '分类', '分类号码', '总金额', 'TPS', 'TVQ', '支票号', '支票金额','开票日期']].sort_values(by='小票日期')

        subtotal_row = pd.DataFrame([{
            '供应商': '汇总',
            '小票日期': '',
            '分类': '',
            '分类号码': '',
            '总金额': group_display['总金额'].sum().round(2),
            'TPS': group_display['TPS'].sum().round(2),
            'TVQ': group_display['TVQ'].sum().round(2),
            '支票号': '',
            '支票金额': '',
            '开票日期': ''
        }])

        #group_with_total = pd.concat([subtotal_row, group_display, subtotal_row], ignore_index=True)
        group_with_total = pd.concat([subtotal_row, group_display], ignore_index=True)

        st.markdown(f"### 💳 支票号：{cheque_id}")
        st.dataframe(style_dataframe(group_with_total), use_container_width=True)

        all_groups_with_totals.append(group_with_total)

    # 📥 更新下载按钮内容（此处才触发）
    if all_groups_with_totals:
        export_df = pd.concat(all_groups_with_totals, ignore_index=True)
        output = BytesIO()
        export_df.to_excel(output, index=False)
        output.seek(0)
        filename = f"{selected_month}_Cash_refund支票详情_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # 在上方右侧区域更新下载按钮
        with col2:
            download_placeholder.download_button(
                label="📥 下载报表",
                data=output,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
