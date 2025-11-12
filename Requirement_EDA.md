汇率分析项目 - EDA 开发计划 (EDA Development Plan)

本文档基于 master_data.csv (包含9个核心字段)，旨在规划 EDA 阶段，以满足项目指南 (WPS扫描件) 中关于 4.1 (10个摘要统计) 和 4.2 (10-15个可视化) 的要求。

第 1 部分：摘要统计 (Summary Statistics)

项目要求 (6.3): 解释定义、源代码和输出解读。
执行工具: eda_script.py (Python, Pandas)

以下是必须生成的10个关键统计数据：

描述性统计全表 (.describe()):

定义: 对所有9个数值型字段计算计数、均值、标准差、最小值、最大值和四分位数。

目的: 快速了解每个变量的数据分布、中心趋势和离散程度。

源代码: df.describe() (已在 eda_script.py 中实现)。

相关性矩阵 (.corr()):

定义: 计算所有变量对 (Pair-wise) 之间的皮尔逊相关系数（值在 -1 到 1 之间）。

目的: (最关键的统计) 快速识别哪些变量与 USD_CNY_Rate（汇率）高度正相关（同向移动）或负相关（反向移动）。

源代码: df.corr() (已在 eda_script.py 中实现)。

汇率波动率 (Volatility):

定义: USD_CNY_Rate 的标准差 (Standard Deviation)。

目的: 量化汇率在整个周期内的风险或不确定性。高标准差意味着高波动。

美中利差 (Interest Rate Spread) - 均值:

定义: (US_Interest_Rate - CN_LPR) 的平均值。

目的: 这是分析汇率的核心驱动因素之一。一个正的利差（美国利率更高）通常会吸引资本流入美国，使美元升值（USD_CNY_Rate 上升）。

美中通胀差 (Inflation Spread) - 均值:

定义: (US_CPI - CN_CPI) 的平均值。

目的: 根据购买力平价理论，通胀更高的一方（例如美国）的货币长期来看应会贬值。

相关性：汇率 vs 黄金:

定义: USD_CNY_Rate 与 Gold_Price 之间的相关系数。

目的: 检验黄金作为避险资产时，是否与人民币/美元汇率呈特定关系（通常黄金涨，美元（相对于一揽子货币）跌，但对特定汇率对的关系需要检验）。

相关性：汇率 vs 美中利差:

定义: USD_CNY_Rate 与 (US_Interest_Rate - CN_LPR) 之间的相关系数。

目的: 用一个具体数字来证明利差对汇率的影响强度。

相关性：汇率 vs 美国股市:

定义: USD_CNY_Rate 与 SP500_Close 之间的相关系数。

目的: 观察美国市场信心（股市）与汇率的关系。

相关性：汇率 vs 中国股市:

定义: USD_CNY_Rate 与 CN_Stock_Price 之间的相关系数。

目的: 观察中国市场信心（股市）与汇率的关系（例如，股市上涨是否吸引外资流入，使人民币升值）。

汇率偏度 (Skewness):

定义: USD_CNY_Rate 的偏度值。

目的: 检查汇率的分布是否对称。正偏度意味着历史上“大涨”的幅度/频率大于“大跌”。

第 2 部分：可视化 (Visualisations)

项目要求 (6.4): 解释图表的定义和目的。
执行工具: Tableau, Power BI, 或 Python (Plotly/Seaborn)

以下是10个核心的可视化建议，它们将构成你仪表盘的主体：

图表 1：USD/CNY 汇率长期趋势

图表类型: 折线图 (Line Chart)

目的: 展示分析周期内汇率的主要走势（人民币升值/贬值）。这是仪表盘的核心图表。

图表 2：美中利差 (Interest Rate Spread)

图表类型: 双线图 (Dual-Line Chart) 或 面积图 (Area Chart)

Y1轴: US_Interest_Rate

Y2轴 (或同轴): CN_LPR

目的: 直观展示两国利率政策的分歧或趋同。利差的扩大和缩小是关键观察点。

图表 3：美中通胀对比 (Inflation Contrast)

图表类型: 双线图 (Dual-Line Chart)

Y1轴: US_CPI (例如同比)

Y2轴: CN_CPI (例如同比)

目的: 对比两国通胀压力，这是影响长期汇率的根本因素之一。

图表 4：汇率 vs 黄金价格

图表类型: 双轴图 (Dual-Axis Chart)

Y1轴: USD_CNY_Rate (折线图)

Y2轴: Gold_Price (折线图)

目的: 观察全球避险情绪（黄金）与汇率变动的关系。

图表 5：汇率 vs 股市信心

图表类型: 双轴图 (Dual-Axis Chart)

Y1轴: USD_CNY_Rate (折线图)

Y2轴: SP500_Close 或 CN_Stock_Price (折线图) - 可能需要制作两个图表或使用筛选器切换

目的: 观察资本市场表现是否领先或伴随汇率变动。

图表 6：中国 M2 供应量趋势

图表类型: 折线图 (Line Chart)

Y轴: CN_M2

目的: 展示中国的货币供应量。M2 增速的快慢反映了货币政策的松紧，会间接影响利率和汇率。

图表 7：【关键】相关性热图 (Correlation Heatmap)

图表类型: 热图 (Heatmap)

目的: (最关键的可视化) 一目了然地展示所有9个变量之间的相关性（即第1部分的统计2）。红色代表强正相关，蓝色代表强负相关。

图表 8：【关键】利差与汇率关系

图表类型: 散点图 (Scatter Plot)

X轴: (US_Interest_Rate - CN_LPR) (利差)

Y轴: USD_CNY_Rate (汇率)

目的: 验证利差和汇率之间的线性关系。如果点呈趋势线（例如左下到右上），则证明了强相关性。

图表 9：汇率分布直方图 (Histogram)

图表类型: 直方图 (Histogram)

X轴: USD_CNY_Rate

Y轴: 频数 (Count)

目的: 查看汇率最常出现的区间，并（结合统计10）观察分布的偏度。

图表 10：关键指标卡 (KPI Cards)

图表类型: 文本卡片 (Text / KPI Card)

目的: 在仪表盘最上方显示最新的汇率、利率、黄金价格等数值，并显示月度/季度环比变化（例如 +0.5% 📈）。