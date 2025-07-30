import streamlit as st
from ui.sidebar import render_sidebar

from ui.sidebar import render_sidebar, render_refresh_button
from modules.data_loader import load_supplier_data  # 你需要创建这个模块

from modules.ap_unpaid import ap_unpaid_query
from modules.ap_unpaid_compta import ap_unpaid_query_compta

from modules.paid_cheques import paid_cheques_query
from modules.cheque_lookup import cheque_lookup_query
from modules.invoice_lookup import invoice_lookup_query
from modules.company_invoice_query import company_invoice_query
from modules.cheque_ledger_query import cheque_ledger_query
from modules.cash_refund import cash_refund




st.set_page_config(page_title="新亚超市智能管理系统", layout="wide")

# 页面标题
st.markdown("""
    <h2 style='color:#1A5276;'>新亚超市智能管理系统</h2>
""", unsafe_allow_html=True)


# ✅ 手动刷新数据按钮，显示在左侧最上方
refresh_triggered = render_refresh_button(load_supplier_data)


# 左侧导航
selected = render_sidebar()

# 根据选项运行对应功能
#if selected == "应付未付账单查询(管理版)":
    #ap_unpaid_query()


if selected == "应付未付账单查询(会计版)":
    ap_unpaid_query_compta()

if selected == "付款支票信息查询":
    paid_cheques_query()

if selected == "支票号查询":
    cheque_lookup_query()

if selected == "发票号查询":
    invoice_lookup_query()

if selected == "按公司查询":
    company_invoice_query()

if selected == "当前支票总账":
    cheque_ledger_query()

if selected == "查询Cash_Refund信息":
    cash_refund()

