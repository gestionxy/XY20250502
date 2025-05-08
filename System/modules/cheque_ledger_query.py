# 📁 modules/cheque_ledger_query.py
import streamlit as st
import pandas as pd
from modules.data_loader import load_supplier_data
from fonts.fonts import load_chinese_font

my_font = load_chinese_font()


def cheque_ledger_query():
    df = load_supplier_data()
    
    # 强力过滤 “空值”、"nan" 字符串、空字符串、只含空格的值
    df = df[df['付款支票号'].apply(lambda x: str(x).strip().lower() not in ['', 'nan', 'none'])]

    # 再转为字符串（如果需要进一步分组）
    df['付款支票号'] = df['付款支票号'].astype(str)




    st.subheader("📒 当前支票总账查询")
    st.info("##### 💡 支票信息总账的搜索时间是按照 *🧾发票日期* 进行设置的，查询某个会计日期内的支票信息")

    # ✅ 时间筛选：默认使用全部数据范围
    min_date, max_date = pd.to_datetime(df['发票日期'], errors='coerce').min(), pd.to_datetime(df['发票日期'], errors='coerce').max()
    col1, col2 = st.columns(2)
    start_date = col1.date_input("开始发票日期", value=min_date)
    end_date = col2.date_input("结束发票日期", value=max_date)

    # ✅ 筛选出有付款支票号的数据，并且发票日期在指定范围
    df = df[df['付款支票号'].notna()]
    df['发票日期'] = pd.to_datetime(df['发票日期'], errors='coerce')
    df = df[(df['发票日期'] >= pd.to_datetime(start_date)) & (df['发票日期'] <= pd.to_datetime(end_date))]

    # ✅ 聚合数据：按支票号、部门、公司汇总
    agg_funcs = {
        '公司名称': 'first',
        '部门': lambda x: ','.join(sorted(x.astype(str))),
        '发票号': lambda x: ','.join(sorted(x.astype(str))),
        '发票金额': lambda x: '+'.join(sorted(x.astype(str))),
        '实际支付金额': 'sum',
        'TPS': 'sum',
        'TVQ': 'sum'
    }

    grouped = df.groupby('付款支票号').agg(agg_funcs).reset_index()
    grouped['税后金额'] = grouped['实际支付金额'] - grouped['TPS'] - grouped['TVQ']

    # ✅ 数值支票号在前、文本支票号在后排序
    def sort_key(val):
        try:
            return (0, int(val))
        except:
            return (1, str(val))

    grouped = grouped.sort_values(by='付款支票号', key=lambda x: x.map(sort_key)).reset_index(drop=True)

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
        '税后金额': grouped['税后金额'].sum()
    }])

    grouped = pd.concat([grouped, total_row], ignore_index=True)

    # ✅ 设置样式
    def highlight_total(row):
        if row['付款支票号'] == '总计':
            return ['background-color: #FADBD8'] * len(row)
        return [''] * len(row)

    st.dataframe(
        grouped.style
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
