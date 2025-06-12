import streamlit as st


def render_sidebar():
    # st.sidebar：Streamlit 提供的侧边栏组件，可以在页面的左侧创建一个固定的菜单区域
    # markdown()：用于显示Markdown 或 HTML 格式的文本
    st.sidebar.markdown("<h3 style='color:red;'>新亚超市管理系统</h3>", unsafe_allow_html=True)
    
    # st.sidebar.radio()：在侧边栏添加一个单选按钮组
    menu = st.sidebar.radio("🚀数据更新截止至：2025-06-11 17:57", 
        # 每个选项代表一个功能模块，可以根据选择执行不同的业务逻辑
        [
        "应付未付账单查询",
        "付款支票信息查询",
        "当前支票总账",
        "支票号查询",
        "发票号查询",
        "按公司查询",
        "查询Cash_Refund信息",
        # "进货明细统计",
    ])
    # # 返回用户选择的菜单项
    return menu

# ✅ 添加这个函数用于统一返回用户选中的部门
#  提供一个部门选择的多选框，允许用户选择一个或多个部门，并支持全部选择
def get_selected_departments(df):
    # 从**df** 中提取**“部门”列，去除空值**，获取唯一值并排序
    # tolist()：将结果转换为Python 列表，便于后续处理
    all_departments = sorted(df['部门'].dropna().unique().tolist())
    
    # 在部门列表前添加**“全部”选项，便于用户快速选择所有部门**
    department_options = ["全部"] + all_departments

    # st.sidebar.multiselect()： 创建一个多选框，允许用户选择一个或多个部门
    # st.sidebar.multiselect() 返回的是一个Python 列表，包含用户当前选中的所有选项
    # "选择部门"：标签，用于提示用户选择部门
    # options=department_options： 选项列表，包括**“全部”和各个部门**
    # default=["全部"]：默认选择“全部”，确保用户首次加载时不遗漏数据
    selected_raw = st.sidebar.multiselect("选择部门", options=department_options, default=["全部"])


    # "全部" in selected_raw： 如果用户选择了**“全部”，返回所有部门**
    # not selected_raw：如果用户未选择任何部门，也返回所有部门（避免返回空列表）   
    if "全部" in selected_raw or not selected_raw:
        return all_departments
    else:
        # 否则，返回用户实际选择的部门列表
        return selected_raw


# 在侧边栏创建一个手动刷新数据的按钮，并在用户点击按钮后清除缓存，重新加载数据
# load_func： 一个数据加载函数，通常是**@st.cache_data** 缓存的数据函数
def render_refresh_button(load_func):
    # 在侧边栏显示数据刷新标题，###：设置三级标题（较大字体）
    st.sidebar.markdown("### 🔄 数据刷新")
    # st.sidebar.button()： 在侧边栏创建一个按钮。
    # 触发机制：st.sidebar.button() 是一个交互组件，在用户点击后返回**True，否则返回False**
    if st.sidebar.button("👉 手动刷新数据"):
        # 清除**load_func** 关联的数据缓存
        # 通常用于**@st.cache_data** 缓存的数据加载函数
        
        # 例如 
        #@st.cache_data
        #def load_supplier_data():
            # 加载数据的复杂逻辑
        #return data

        load_func.clear()
        
        # st.sidebar.success() 会在侧边栏显示绿色背景的消息框，增强用户反馈
        st.sidebar.success("✅ 已清除缓存，数据将重新加载")
        # 返回**True，表明用户点击了**刷新按钮
        return True
    
    # 如果用户没有点击按钮，返回**False，保持数据状态不变**
    return False

    # 在Streamlit 中，很多组件（例如按钮、单选框、多选框）都是事件驱动的，
    # 即用户的点击、选择或输入会触发相应的状态改变。
    # 这种状态变化通常需要通过布尔值进行判断，以确保正确地处理用户的交互行为