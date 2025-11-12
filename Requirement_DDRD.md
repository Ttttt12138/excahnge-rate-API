汇率分析仪表盘 - 设计与需求文档 (DDRD)

属性

详情

项目名称

汇率分析仪表盘 (Exchange Rate Analysis Dashboard)

文档版本

v2.0 (集成 AI)

文档ID

DASH-REQ-002

日期

2025年11月12日

项目主题

汇率 (Exchange Rate)

构建工具

Streamlit

1. 仪表盘概述

目标 (Goal): 本仪表盘旨在为管理层和分析师提供一个动态、可交互的视图，用于理解 USD/CNY（美元/人民币）汇率的关键驱动因素。

核心目的 (Purpose):

[描述] 通过对比中美宏观指标和市场情绪，分析汇率 “为什么” 变动。

[智能] (新增) 提供一个由 Gemini 驱动的 AI 接口，允许用户基于当前数据进行自然语言提问和分析。

技术栈 (Technology Stack):

Web 框架: Streamlit

数据处理: Pandas

数据可视化: Plotly Express

AI 大模型: Google Gemini (通过 API 调用)

2. 目标受众与分析问题 (项目要求 5.1)

目标受众: 经济分析师、投资经理、企业管理层（需要评估汇率风险）。

核心分析问题 (10):

(此部分与 v1.0 相同，包含10个静态分析问题)

3. 仪表盘布局与组件设计 (项目要求 6.5)

本仪表盘将采用“侧边栏过滤 + 主体内容区展示”的经典布局 (layout="wide")。

3.1. 侧边栏 (Sidebar - st.sidebar)

组件 1: 标题

st.sidebar.title("🎛️ 过滤器 (Filters)")

组件 2: 日期范围选择器 (Date Range Selector)

st.sidebar.date_input()

目的: 允许用户选择他们关心的分析时间区间。这是仪表盘的核心交互功能。

组件 3: (新增) Gemini API 密钥输入

st.sidebar.text_input("Gemini API Key", type="password")

目的: 安全地输入 API 密钥以激活 AI 分析功能。

3.2. 主页面 (Main Page)

A. 标题区 (Title)

st.title("💹 汇率 (USD/CNY) 深度分析仪表盘")

B. 关键指标卡 (KPIs) (st.metric)

(与 v1.0 相同: 4列KPIs)

C. 核心趋势图 (Core Trends) (st.plotly_chart)

(与 v1.0 相同: 汇率 & 黄金价格)

D. 宏观经济对比 (Macro-Economic Comparison)

(与 v1.0 相同: 利率对比 & 通胀对比)

E. 深度驱动分析 (Key Driver Analysis)

(与 v1.0 相同: 利差散点图 & 相关性热图)

F. 市场信心与货币 (Market & Monetary)

(与 v1.0 相同: S&P 500, 中国股市, 中国 M2)

G. 附加分析 (Additional Analysis)

(与 v1.0 相同: 汇率直方图)

H. (新增) 🤖 AI 智能分析 (Gemini)

布局: st.expander("展开 AI 智能分析")

组件 1: 文本输入框

st.text_area("请输入你的问题...")

目的: 允许用户用自然语言提问。

组件 2: 分析按钮

st.button("生成分析")

组件 3: 响应区

st.markdown(response_text)

目的: 显示 Gemini 返回的分析结果。

工作流: 1.  用户点击“生成分析”。
2.  应用获取用户问题和侧边栏的 API 密钥。
3.  应用提取当前已筛选的数据 (df_filtered) 并将其（或其摘要）转换为字符串。
4.  应用构建一个 Prompt，包含数据上下文和用户问题。
5.  应用调用 Gemini API (gemini-2.5-flash-preview-09-2025)。
6.  在“响应区”显示结果。

4. 部署与交付 (项目要求 5.4, 6.6) - (已更新)

部署平台: 本地网络 (Local Network)

本地运行流程:

确保已安装 Python 环境。

将 streamlit_app.py, requirements.txt, 和 master_data.csv 放置在同一文件夹中。

打开终端 (Terminal / 命令行)。

安装所有依赖库: pip install -r requirements.txt

运行 Streamlit 应用: streamlit run streamlit_app.py

应用将在默认浏览器中自动打开 (地址: http://localhost:8501)。

⚠️ 关于项目 6.6 (公开链接) 的重要提示:

挑战: localhost 地址不是一个公开链接；它只能在你自己的电脑上访问。这不满足你项目指南中 (5.4) "以在线格式发布" 和 (6.6) "公开可访问的仪表盘链接" 的要求。

解决方案 B (演示用): 如果你只是想在演示 (11月25日) 时临时公开，可以使用 ngrok 等工具为你的 localhost:8501 创建一个临时的公共 URL 隧道。（选用B方案解决）