## 项目目标
- 构建一个基于 Streamlit 的交互式仪表盘，满足 DDRD 文档的布局与组件要求，并与现有 EDA 产出无缝集成。
- 展示 10 个核心图表与顶部 KPI 卡，支持日期范围过滤与 AI 智能分析模块（Gemini）。
- 支持本地运行（localhost:8501）与演示期的临时公网链接（ngrok）。

## 技术选型
- 框架: Streamlit（layout="wide"，侧边栏过滤 + 主区展示）
- 可视化: Plotly Express（交互式折线、散点、直方图、热图）
- 数据处理: Pandas（与既有 ETL/EDA一致）
- AI: Google Gemini（仅在用户提供 API Key 时启用；不持久化密钥）

## 数据与集成
- 原始数据: `output/master_data.csv`（ETL生成，月频/日频）
- EDA产出: `output/eda/describe.csv`、`correlation.csv`、`metrics.json`、`kpis.json`（由 `src/eda_script.py` 生成；参考函数 `_kpis` 于 src/eda_script.py:55）
- 加载策略: 使用 `st.cache_data` 缓存 CSV/JSON 读入；以侧边栏日期范围过滤生成 `df_filtered`。

## 顶部 KPI 卡
- 来源: `output/eda/kpis.json` 的 `items[field].value`、`mom_pct`、`qoq_pct`
- 展示: 4列 `st.metric`，优先显示 `USD_CNY_Rate`、`US_Interest_Rate`、`CN_LPR`、`Gold_Price`；`delta` 使用 `mom_pct` 百分比格式（次要信息可在 tooltip 或次行显示 `qoq_pct`）。

## 图表实现（10项）
- 汇率长期趋势：`USD_CNY_Rate` 折线
- 美中利差：双线（`US_Interest_Rate` vs `CN_LPR`），并在副图展示利差（`US_Interest_Rate - CN_LPR`）
- 通胀对比：双线（`US_CPI` vs `CN_CPI`）
- 汇率 vs 黄金：双轴折线（`USD_CNY_Rate` vs `Gold_Price`）
- 汇率 vs 市场信心：双轴折线（`USD_CNY_Rate` vs `SP500_Close` 与/或 `CN_Stock_Price`，可用切换）
- 中国 M2 趋势：`CN_M2` 折线
- 相关性热图：基于 `output/eda/correlation.csv`
- 利差与汇率散点：X=`US_Interest_Rate - CN_LPR`，Y=`USD_CNY_Rate`
- 汇率直方图：`USD_CNY_Rate` 分布
- 附加细分：在图表上支持 hover、缩放，并可导出为静态PNG（可选）

## 交互与筛选
- 侧边栏：日期范围、图表切换（美股/中股）、频率提示（依据 ETL 输出模式）
- 过滤逻辑：对 `master_data.csv` 执行区间过滤并驱动所有图表与 KPI 更新

## AI 智能分析（Gemini）
- 侧边栏密钥输入：仅内存持有，调用前做校验；无密钥不显示或禁用按钮
- Prompt构建：将 `df_filtered` 的关键统计（选取若干行和摘要）嵌入到提示中，附用户问题
- 输出：`st.expander` 内 `st.markdown` 展示；错误处理与超时提示

## 代码结构
- 新增 `src/streamlit_app.py`（主入口）
- 模块划分（单文件起步，后续可拆分）：
  - 数据加载：`load_master()`, `load_eda_*()`（带缓存）
  - 过滤与派生：`filter_by_date()`、利差列派生
  - KPI渲染：`render_kpis()`
  - 图表渲染：`render_*()`系列（对应 10 个图）
  - AI模块：`run_gemini(query, df_context, api_key)`（占位；实际调用在用户提供密钥后执行）

## 依赖与配置
- 在 `requirements.txt` 增加：`streamlit`, `plotly`
- 可选：`numpy`（百分比与数值处理）、`pydantic`（数据校验）
- 不写入任何 API Key 到代码或配置；支持通过环境变量或侧边栏输入

## 运行与演示
- 安装：`pip install -r requirements.txt`
- 启动：`streamlit run src/streamlit_app.py`（浏览器自动打开 `http://localhost:8501`）
- 临时公网：`ngrok http 8501`，复制生成的公网URL用于演示（符合 DDRD 的“方案B”）

## 安全与性能
- 缓存：`st.cache_data` 避免重复加载；控制缓存失效策略
- 隐私：不记录密钥；错误信息不泄露参数
- 性能：限制热图维度；图表按需渲染（分页或 expander）

## 迭代与验收
- 验收标准：
  - 所有 10 个图表与 4列 KPI 正确渲染并随日期过滤联动
  - AI分析在提供密钥后可获得文本结果
  - ngrok 公网链接在演示期可访问
- 迭代计划：先实现核心数据/图表与 KPI；随后接入 Gemini；最后完善样式与导出能力