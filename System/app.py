import streamlit as st
from ui.sidebar import render_sidebar
from modules.ap_unpaid import ap_unpaid_query
from modules.paid_cheques import paid_cheques_query
from modules.cheque_lookup import cheque_lookup_query
from modules.invoice_lookup import invoice_lookup_query
from modules.company_invoice_query import company_invoice_query



st.set_page_config(page_title="新亚超市智能管理系统", layout="wide")

# 页面标题
st.markdown("""
    <h2 style='color:#1A5276;'>新亚超市智能管理系统</h2>
""", unsafe_allow_html=True)

# 左侧导航
selected = render_sidebar()

# 根据选项运行对应功能
if selected == "应付未付账单查询":
    ap_unpaid_query()

if selected == "付款支票信息查询":
    paid_cheques_query()

if selected == "支票号查询":
    cheque_lookup_query()

if selected == "发票号查询":
    invoice_lookup_query()

if selected == "按公司查询":
    company_invoice_query()


