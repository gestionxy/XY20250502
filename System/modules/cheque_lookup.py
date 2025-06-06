import streamlit as st
import pandas as pd
from modules.data_loader import load_supplier_data


def cheque_lookup_query():
    """支票号查询功能，支持数字和文本支票号排序，模糊查询，以及部门汇总和详细发票信息显示。"""
    # 1. 读取供应商数据
    df = load_supplier_data()

    # 2. 显示查询页面标题
    st.subheader("🔍 支票号查询")

    # 3. 提取所有非空支票号
    # - dropna()：移除缺失值，确保没有 NaN 支票号
    # - str.strip()：去掉前后空格，避免因空格导致的查询失败
    # - unique()：获取唯一支票号列表，避免重复
    all_cheques = df['付款支票号'].dropna()
    all_cheques = all_cheques[all_cheques.astype(str).str.strip() != ''].astype(str).unique()

    # 4. 支票号排序：数字在前，文本在后
    # - 使用 isnumeric() 判断是否为纯数字
    # - 数字按数值排序，文本按字母排序
    # - c 是 all_cheques 列表中的每一个元素（即一个支票号），isnumeric() 检查字符串是否只包含数字（不包含负号、小数点或其他字符）
    # - key 是一个可选参数，用于定义排序的规则
    # - key=lambda x: int(x)：将字符串类型的支票号先转换为整数 (int(x))，然后再排序，确保按照数值大小排序，而不是按照字符串的字典顺序
    # - sorted(iterable, key=None, reverse=False) 
    numeric_cheques = sorted([c for c in all_cheques if c.isnumeric()], key=lambda x: int(x))
    text_cheques = sorted([c for c in all_cheques if not c.isnumeric()])
    sorted_cheques = numeric_cheques + text_cheques

    # 5. 创建下拉输入框
    # - options：支持空选项（即没有输入支票号）
    # - placeholder：提示用户输入支票号或选择下拉选项
    cheque_input = st.selectbox(
        "请输入或选择支票号（支持模糊匹配）:",
        # 如果不设置 [""]，selectbox 会默认选中 sorted_cheques 列表中的第一个支票号，这可能会导致误查询
        # 大多数用户在搜索时会希望先清空输入框，然后手动输入关键字。
        #设置 [""] 可以模拟这种自然的输入流程，提高用户体验。
        options=[""] + sorted_cheques,  # 包含空选项
        # index 是 st.selectbox() 的一个可选参数，指定在下拉列表中默认选中的选项索引
        # 因为我们之前已经设置了options=[""]， 因此 index=0 则默认选中空选项 ""，让用户可以从空状态开始进行支票号选择或手动输入
        index=0,
        # placeholder 是一个可选提示文本，在用户没有进行选择或输入之前显示在输入框中的灰色提示信息。
        placeholder="输入支票号或选择下拉选项"
    )

    # 6. 如果用户选择了支票号或输入了有效支票号
    if cheque_input:
        import re  # 引入正则表达式库，处理复杂字符串匹配
        # **6.1 去掉前后空格并处理正则特殊字符**
        cheque_input = cheque_input.strip()  # 去掉前后空格
        pattern = re.escape(cheque_input)   # 转义正则特殊字符，确保特殊符号不会被误解释

        # **6.2 执行精确匹配**
        # - contains() 进行模糊查询，忽略大小写
        # - na=False 确保 NaN 不会参与匹配
        filtered = df[df['付款支票号'].astype(str).str.strip() == cheque_input]

        # 7. 检查是否找到匹配结果
        if filtered.empty:
            # 如果没有匹配结果，显示警告信息
            st.warning("❌ 支票号不存在或输入错误，请检查后重试。")
        else:
            # 8. 差额计算
            # - 转换金额列为数值类型，非数值（如空值）用 0 填充
            filtered['发票金额'] = pd.to_numeric(filtered['发票金额'], errors='coerce').fillna(0)
            filtered['实际支付金额'] = pd.to_numeric(filtered['实际支付金额'], errors='coerce').fillna(0)
            filtered['差额'] = filtered['发票金额'] - filtered['实际支付金额']

            # 9. 格式化日期列
            # - 转换日期列为统一格式，避免日期显示错误
            filtered['发票日期'] = pd.to_datetime(filtered['发票日期'], errors='coerce').dt.strftime('%Y-%m-%d')
            # errors='coerce'： 强制转换：如果某个值无法转换为有效日期（例如空字符串或格式错误），则自动填充为 NaT（Not a Time），而不会抛出错误。
            # .dt.strftime('%Y-%m-%d') - 格式化日期， 转换后的数据类型会变为 object（字符串），而不是 datetime64
            filtered['开支票日期'] = pd.to_datetime(filtered['开支票日期'], errors='coerce').dt.strftime('%Y-%m-%d')

            # 10. 生成部门汇总表
            # - 按部门汇总实际支付金额、TPS 和 TVQ
            # groupby().sum() 在 Pandas 中的默认行为，它会自动忽略列中的空值（NaN），而不是将结果直接设为 NaN
            # .reset_index() 将分组列（部门）从索引转换为普通列，使得结果可以作为一个独立的 DataFrame 返回，便于后续处理和展示
            # 此时 summary 已经变成了一个 DataFrame，包含部门、实际支付金额、TPS 和 TVQ 的总和
            summary = filtered.groupby('部门')[['实际支付金额', 'TPS', 'TVQ']].sum().reset_index()
            
            # - 添加总计行
            total_row = pd.DataFrame([{
                # 部门 列 下面放一个 总计
                '部门': '总计',
                '实际支付金额': summary['实际支付金额'].sum(),
                'TPS': summary['TPS'].sum(),
                'TVQ': summary['TVQ'].sum()
            }])
            
            # axis=0（默认）：纵向合并（行方向）, axis=1：横向合并（列方向）
            # ignore_index=True 会重新设置索引，而不是保留原有索引
            summary = pd.concat([summary, total_row], axis = 0, ignore_index=True)

            # **10.1 定义总计行高亮函数**
            def highlight_total(row):
                # 当前行是否是“总计”行，设置背景颜色
                if row['部门'] == '总计':
                    # len(row)：获取当前行的列数
                    return ['background-color: #FADBD8'] * len(row)
                # 如果不是“总计”行，则返回一个空样式列表，不做任何样式设置。
                return [''] * len(row)

            # 11. 显示部门汇总结果
            st.markdown("### 💰 查询结果：部门汇总")
            st.dataframe(
                summary.style
                # 在 Pandas 的 DataFrame.apply() 方法中，函数**highlight_total的调用方式与普通 Python 函数有所不同,不需要()显式传递参数,
                # 主要原因是在 apply() 传递函数时，Pandas 会自动将每一行（axis=1）或每一列（axis=0）作为**Series传递给函数，因此highlight_total**不需要显式传递参数。
                # highlight_total(row) 只接受一个参数，即**row**
                .apply(highlight_total, axis=1) # axis=1 按行应用样式
                .format({
                    # ：格式说明符开始   , 启用千分位    .2f 保留两位小数
                    '实际支付金额': '{:,.2f}',
                    'TPS': '{:,.2f}',
                    'TVQ': '{:,.2f}'
                }),
                use_container_width=True
            )

            # 12. 显示详细发票信息
            st.markdown("### 🧾 查询结果：详细发票信息")
            st.dataframe(
                filtered[['部门', '公司名称', '发票号', '发票金额', '实际支付金额', 'TPS', 'TVQ', '差额', '发票日期', '开支票日期']]
                .style.format({
                    '发票金额': '{:,.2f}',
                    '实际支付金额': '{:,.2f}',
                    'TPS': '{:,.2f}',
                    'TVQ': '{:,.2f}',
                    '差额': '{:,.2f}'
                }),
                use_container_width=True
            )
