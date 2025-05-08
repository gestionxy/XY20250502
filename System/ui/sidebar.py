import streamlit as st

def render_sidebar():
    st.sidebar.markdown("<h3 style='color:red;'>新亚超市管理系统</h3>", unsafe_allow_html=True)
    menu = st.sidebar.radio("数据更新截止2025-05-07", [
        "应付未付账单查询",
        "付款支票信息查询",
        "当前支票总账",
        "支票号查询",
        "发票号查询",
        "按公司查询",
        # "进货明细统计",
    ])
    return menu

# ✅ 添加这个函数用于统一返回用户选中的部门
def get_selected_departments(df):
    all_departments = sorted(df['部门'].dropna().unique().tolist())
    department_options = ["全部"] + all_departments

    selected_raw = st.sidebar.multiselect("选择部门", options=department_options, default=["全部"])

    if "全部" in selected_raw or not selected_raw:
        return all_departments
    else:
        return selected_raw


def render_refresh_button(load_func):
    st.sidebar.markdown("### 🔄 数据刷新")
    if st.sidebar.button("👉 手动刷新数据"):
        load_func.clear()
        st.sidebar.success("✅ 已清除缓存，数据将重新加载")
        return True
    return False
