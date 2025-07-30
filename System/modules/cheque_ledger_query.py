# 📁 modules/cheque_ledger_query.py
import io
import pandas as pd
import streamlit as st
from datetime import datetime
from modules.data_loader import load_supplier_data

def cheque_ledger_query():
    
    df = load_supplier_data()

    # ✅ 过滤无效支票号
    df = df[df['付款支票号'].apply(lambda x: str(x).strip().lower() not in ['', 'nan', 'none'])]
    df['付款支票号'] = df['付款支票号'].astype(str)

    st.subheader("📒 当前支票总账查询")
    #st.info("##### 💡 支票信息总账的搜索时间是按照 *🧾发票日期* 进行设置的，查询某个会计日期内的支票信息")


    # ✅ 日期标准化
    df['发票日期'] = pd.to_datetime(df['发票日期'], errors='coerce')



    agg_funcs = {
        '公司名称': 'first',
        #'部门': lambda x: ','.join(sorted(x.astype(str))),
        '部门': 'first',
        '发票号': lambda x: ','.join(sorted(x.astype(str))),
        '发票金额': lambda x: '+'.join(sorted(x.astype(str))),
        '银行对账日期': 'first',
        '开支票日期': 'first',
        '实际支付金额': 'sum',
        'TPS': 'sum',
        'TVQ': 'sum',
    }

    grouped = df.groupby('付款支票号').agg(agg_funcs).reset_index()

    grouped['银行对账日期'] = pd.to_datetime(grouped['银行对账日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    grouped['开支票日期'] = pd.to_datetime(grouped['开支票日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    grouped['税后金额'] = grouped['实际支付金额'] - grouped['TPS'] - grouped['TVQ']



    # 仅保留 数字编号的 支票号码
    # 只保留以数字开头的付款支票号（用正则表达式）
    grouped = grouped[grouped['付款支票号'].astype(str).str.match(r'^\d')]

    # 新增一列提取支票号中的数字部分（用于排序）
    # 我只要这个提取结果的“第 0 列”（也就是唯一那一列），并把它变成一个 Series。
    # 如果你不写 [0]，提取结果就是个 DataFrame，不能直接赋值到某个 Series 列里，也没法 .astype(int)，程序会报错或行为不对。
    grouped['支票号数字'] = grouped['付款支票号'].astype(str).str.extract(r'^(\d+)')[0].astype(int)

    # 按照提取的数字部分进行排序
    grouped = grouped.sort_values(by='支票号数字').drop(columns='支票号数字').reset_index(drop=True)

    desired_order = [
        '付款支票号', '公司名称', '实际支付金额',
        'TPS', 'TVQ', '税后金额',
        '开支票日期', '银行对账日期',
        '部门', '发票号', '发票金额'
    ]

    # 重新排列列顺序，保留你指定的列
    grouped = grouped.reindex(columns=desired_order)


    # ✅ 选择筛选方式：radio 控件
    filter_mode = st.radio("🧭 请选择筛选方式：", ["显示所有已开支票", "按银行对账日期显示已开支票", "PPA / EFT / DEBIT 等自动过账"], index=0)

    # ✅ 分支 1：按财会年度筛选
    if filter_mode == "显示所有已开支票":

        if df['发票日期'].notna().any():
            min_date = df['发票日期'].min().strftime('%Y-%m-%d')
            max_date = df['发票日期'].max().strftime('%Y-%m-%d')
            st.info(f"📌 当前发票日期范围 {min_date} ~ {max_date}")
        else:
            st.warning("⚠️ 没有有效的发票日期")
        #st.dataframe(grouped)


    # ✅ 分支 2：按银行对账日期显示已开支票
    elif filter_mode == "按银行对账日期显示已开支票":
        col_a, col_b = st.columns([2, 1])
        with col_a:
            valid_dates = sorted(grouped['银行对账日期'].dropna().unique())
            selected_reconcile_date = st.selectbox("📆 按银行对账日期筛选（可选）", options=["全部"] + valid_dates)

        if selected_reconcile_date != "全部":
            grouped = grouped[grouped['银行对账日期'] == selected_reconcile_date]

        #st.dataframe(grouped)


        if not grouped.empty:
            def convert_df_to_excel(df_export):
                export_df = df_export.copy()

                # 格式化日期
                export_df['银行对账日期'] = pd.to_datetime(export_df['银行对账日期'], errors='coerce').dt.strftime('%Y-%m-%d')
                export_df['开支票日期'] = pd.to_datetime(export_df['开支票日期'], errors='coerce').dt.strftime('%Y-%m-%d')

                # 保留两位小数的金额列
                for col in ['实际支付金额', 'TPS', 'TVQ', '税后金额']:
                    export_df[col] = pd.to_numeric(export_df[col], errors='coerce').round(2)

                # ✅ 新增辅助匹配列：支票号数字部分 + 金额
                # 提取数字部分：例如 CK889 → 889
                export_df['辅助匹配列'] = export_df.apply(
                    lambda row: f"{''.join(filter(str.isdigit, str(row['付款支票号'])))}-{format(row['实际支付金额'], '.2f')}",
                    axis=1
                )

                # 导出 Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='支票总账')
                    writer.close()
                return buffer.getvalue()


            excel_data = convert_df_to_excel(grouped)

            # ✅ 当前时间戳用于命名文件：如 20250606151515
            timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
            file_name = f"支票总账_{timestamp_str}.xlsx"

            with col_b:
                st.download_button(
                    label="📥 下载当前支票数据",
                    data=excel_data,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )




    # 增加PPA / ETF / DEBIT 账单查询窗口
    # 满足 sui姐 关于自动转账的数据查询
    elif filter_mode == "PPA / EFT / DEBIT 等自动过账":

        # 加载数据
        df_ppa_eft_debit = load_supplier_data()
        df_ppa_eft_debit_1 = load_supplier_data()

        # 转换日期字段
        df_ppa_eft_debit_1['发票日期'] = pd.to_datetime(df_ppa_eft_debit_1['发票日期'], errors='coerce')

        # 条件1：公司名称以 * 结尾
        cond_company_star = df_ppa_eft_debit_1['公司名称'].str.endswith('*', na=False)


        # 条件2：公司名称不以 * 结尾 且 付款支票号以字母开头

        # 确保字段为字符串
        df_ppa_eft_debit['公司名称'] = df_ppa_eft_debit['公司名称'].astype(str)
        df_ppa_eft_debit['付款支票号'] = df_ppa_eft_debit['付款支票号'].astype(str)

        # 去除付款支票号中逻辑无效的值（空、nan、none等）
        invalid_values = ['', 'nan', 'none']
        df_ppa_eft_debit = df_ppa_eft_debit[
            ~df_ppa_eft_debit['付款支票号'].str.strip().str.lower().isin(invalid_values)
        ]


        cond_company_nonstar_and_cheque_alpha = (
            ~df_ppa_eft_debit['公司名称'].str.endswith('*', na=False) &
            df_ppa_eft_debit['付款支票号'].str.match(r'^[A-Za-z]', na=False)
        )

        # 合并条件（取并集）
        combined_condition = cond_company_star | cond_company_nonstar_and_cheque_alpha

        # 最终筛选后的数据集
        df_filtered_PPA = df_ppa_eft_debit[combined_condition]

        # 如果筛选结果为空，给予提示
        if df_filtered_PPA.empty:
            st.warning("没有找到公司名称以 * 结尾的数据。")
        else:
            # 获取发票日期的最小值和最大值
            min_date = df_filtered_PPA['发票日期'].min()
            max_date = df_filtered_PPA['发票日期'].max()

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("开始日期", value=min_date, min_value=min_date, max_value=max_date)
            with col2:
                end_date = st.date_input("结束日期", value=max_date, min_value=min_date, max_value=max_date)

            # 日期过滤
            date_mask = (df_filtered_PPA['发票日期'] >= pd.to_datetime(start_date)) & \
                        (df_filtered_PPA['发票日期'] <= pd.to_datetime(end_date))
            df_filtered_PPA = df_filtered_PPA.loc[date_mask]

            # 提取并格式化要显示的字段
            df_display = df_filtered_PPA[['公司名称', '部门', '发票号', '发票日期', '发票金额', 'TPS', 'TVQ', '付款支票号']].copy()
            df_display['发票日期'] = df_display['发票日期'].dt.strftime('%Y-%m-%d')
            for col in ['发票金额', 'TPS', 'TVQ']:
                df_display[col] = df_display[col].astype(float).map("{:.2f}".format)

            # 显示结果
            st.dataframe(df_display, use_container_width=True)
    


    # 为了让 自动过账PPA / EFT / DEBIT 的数据内容不显示 如下信息，我们设置一个if条件进行限制
    # 如果不是 PPA / EFT / DEBIT 等自动过账，则显示下面的数据统计部分
    if filter_mode != "PPA / EFT / DEBIT 等自动过账":

        # ✅ 添加总计行
        total_row = pd.DataFrame([{
            '付款支票号': '总计',
            '公司名称': '',
            '部门': '',
            '发票号': '',
            '发票金额': '',
            '实际支付金额': grouped['实际支付金额'].sum(),
            'TPS': grouped['TPS'].sum(),
            'TVQ': grouped['TVQ'].sum(),
            '税后金额': grouped['税后金额'].sum(),
            '银行对账日期': '',
            '开支票日期': '',
        }])

        grouped_table = pd.concat([grouped, total_row], ignore_index=True)


            # 先构造总计数据字典
        total_data = {
            #"实际支付金额": round(grouped.loc[grouped['付款支票号'] == '总计', '实际支付金额'].sum(), 2),
            #"TPS": round(grouped.loc[grouped['付款支票号'] == '总计', 'TPS'].sum(), 2),
            #"TVQ": round(grouped.loc[grouped['付款支票号'] == '总计', 'TVQ'].sum(), 2),
            #"税后金额": round(grouped.loc[grouped['付款支票号'] == '总计', '税后金额'].sum(), 2),
            "实际支付金额": round(grouped['实际支付金额'].sum(), 2),
            "TPS": round(grouped['TPS'].sum(), 2),
            "TVQ": round(grouped['TVQ'].sum(), 2),
            "税后金额": round(grouped['税后金额'].sum(), 2),
        }




        # 构造 HTML + CSS 表格（卡片浮动样式）
        html = f"""
        <style>
            .card {{
                background-color: #ffffff;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                width: 420px;
                margin: 30px auto;
                font-family: "Segoe UI", sans-serif;
            }}
            .summary-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 15px;
                background-color: #EAF2F8;
                border-radius: 8px;
                overflow: hidden;
            }}
            .summary-table th {{
                background-color: #D6EAF8;
                text-align: left;
                padding: 10px;
            }}
            .summary-table td {{
                padding: 10px;
                border-top: 1px solid #D4E6F1;
                text-align: right;
            }}
            .summary-table td:first-child {{
                text-align: left;
            }}
        </style>

        <div class="card">
            <h3>💰 总计</h3>
            <table class="summary-table">
                <tr><th>项目</th><th>金额（元）</th></tr>
                <tr><td>实际支付金额</td><td>{total_data['实际支付金额']:,.2f}</td></tr>
                <tr><td>TPS</td><td>{total_data['TPS']:,.2f}</td></tr>
                <tr><td>TVQ</td><td>{total_data['TVQ']:,.2f}</td></tr>
                <tr><td>税后金额</td><td>{total_data['税后金额']:,.2f}</td></tr>
            </table>
        </div>
        """

        # 渲染 HTML 内容
        st.markdown(html, unsafe_allow_html=True)
        
        


        # ✅ 设置样式
        def highlight_total(row):
            if row['付款支票号'] == '总计':
                return ['background-color: #FADBD8'] * len(row)
            return [''] * len(row)

        st.dataframe(
            grouped_table.style
            .apply(highlight_total, axis=1)
            .format({
                #'发票金额': '{:,.2f}',
                '实际支付金额': '{:,.2f}',
                'TPS': '{:,.2f}',
                'TVQ': '{:,.2f}',
                '税后金额': '{:,.2f}'
            }),
            use_container_width=True
        )



