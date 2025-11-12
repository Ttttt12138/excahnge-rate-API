汇率分析项目 - 自动化ETL需求文档

属性

详情

项目名称

汇率分析仪表盘 (Exchange Rate Analysis Dashboard)

文档版本

v2.0 (已扩展)

文档ID

ETL-REQ-001

日期

2025年11月12日

文档作者

(你的名字)

项目主题

汇率 (Exchange Rate)

1. 项目背景与目标

本项目（代号：Project-Based Learning 3）旨在围绕“汇率”主题，构建一个在线数据分析仪表盘。根据项目指南要求，必须结合至少三个不同的数据源，并执行完整的 ETL (Extract, Transform, Load) 和 EDA (Exploratory Data Analysis) 流程。

本需求文档专注于定义 ETL 流程中的“提取 (Extract)”和“转换 (Transform)”阶段，采用自动化的 API 调用方式，以取代手动下载 CSV 文件，并已根据实现更新数据源为 FRED 主导的数据集。

业务目标：

自动化： 建立一个可重复运行的流程，自动从公共数据源获取最新的汇率、利率和商品数据。

集成： 将多个独立的数据源（包括宏观经济指标）整合为一个干净、统一、可供分析的数据集。

效率： 消除手动下载和清理数据所带来的时间消耗和潜在错误。

2. 需求范围

2.1. 范围内 (In-Scope)

通过 API 自动从 FRED 数据库提取数据。

使用 Python (Pandas) 对提取的多个数据集进行转换。

转换操作应包括：数据清理、日期格式统一、处理混合频率（日/月）、缺失值处理、数据合并。

输出一个单一的、干净的、可用于 BI 工具（如 Tableau）加载的 CSV 文件。

2.2. 范围外 (Out-of-Scope)

本需求的产出不包括：

EDA (探索性数据分析) 的统计和可视化（这是下一步）。

BI 仪表盘的设计和开发（这是“加载”后的步骤）。

最终项目报告的撰写。

3. 数据源需求 (Extract)

系统必须从以下 API 端点提取数据：

编号

数据源

数据内容

标识符/代码

频率

提取方式

备注

DS-01

FRED

美元兑人民币汇率

DEXCHUS

每日

fredapi

核心指标。1 美元可兑换的人民币。

DS-02

FRED

美国联邦基金利率

FEDFUNDS

每日

fredapi

美国利率。

DS-03

FRED（替代黄金相关序列）

黄金价格（替代）

优先：Credit Suisse NASDAQ Gold FLOWS103 Price Index；回退：Export/Import Price Index (End Use): Nonmonetary Gold

月度或每日（随所用序列而定，统一按月频处理）

fredapi

全球市场避险情绪。

DS-04

FRED

美国 CPI (通胀)

CPIAUCSL

每月

fredapi

美国通胀率。

DS-05

FRED

中国 CPI (通胀)

CHNCPIALLMINMEI

每月

fredapi

中国通胀率 (月度)。

DS-06

FRED

中国 LPR 利率

DPRCMLTLPR1Y

每月

fredapi

中国1年期贷款市场报价利率。

DS-07

FRED

美国 S&P 500 指数

SP500

每日

fredapi

美国市场信心。

DS-08（更新）

FRED

中国 M2（货币供应量）

通过关键词检索 Money Supply M2 for China

每月

fredapi

中国货币供应。

DS-09（新增）

FRED

中国股票价格（金融市场）

通过关键词检索 Stock Price Index for China / Share Prices: Total for China（取其一）

每月

fredapi

中国股票价格指数（总量）。

4. 技术实现与转换逻辑 (Transform)

4.1. 技术栈

语言： Python 3.x

核心库：

pandas (用于数据转换和处理)

fredapi (用于连接 FRED API，需要 API 密钥)

4.2. 转换 (Transform) 逻辑

提取 (Extract)：

fredapi 库将使用 API 密钥初始化。

调用 get_series()/搜索获取 DS-01, 02, 03(替代黄金), 04, 05, 06, 07, 08(M2), 09(中国股票价格)。

清理 (Clean)：

重命名： 将所有列重命名为清晰的业务名称 (例如：USD_CNY_Rate, US_Interest_Rate, Gold_Price, US_CPI, CN_CPI, CN_LPR, SP500_Close, CN_M2, CN_Stock_Price)。

合并 (Merge)：

将所有 Pandas 对象合并为一个新的主 DataFrame。

合并键： 所有数据都必须基于日期索引进行合并 (使用 pd.concat(..., axis=1))。

处理缺失值 (Handle Missing Values)：

问题： 日频数据（汇率、利率、标普）在周末和节假日可能不存在。

解决方案： 针对所有每日数据（DS-01, 02, 07），使用前向填充 (Forward-fill / fillna(method='ffill')) 策略。这假设周末或假日的值与前一个工作日相同。

(关键) 4.2.5. 处理混合频率 (Handle Mixed Frequencies)

问题： 合并后，你的 DataFrame 中同时存在每日数据（已填充）和每月数据（例如 US_CPI 在该月的1号有值，其他日期为 NaN）。

解决方案： 你必须选择一种策略来统一频率：

方案 A (推荐 - 月度分析)：

将整个 DataFrame 重采样 (Resample) 为月度。

df_monthly = df.resample('ME').mean() (使用月均值) 或 df_monthly = df.resample('ME').last() (使用月末值)。

优点： 这是最统计上最严谨的比较方式。

方案 B (每日分析)：

如果你希望保留每日视图，则必须前向填充 (Forward-fill) 所有的每月数据（DS-03(替代黄金), 04, 05, 06, 08(M2), 09(中国股票价格)）。

优点： 保持了数据的粒度，但必须在报告中注明“本月CPI在全月内保持不变”的假设。

5. 最终交付物 (Load)

此 ETL 流程的最终产出（即“加载”到 BI 工具的源文件）必须满足以下标准：

一个 Python 脚本 (etl_script.py)： 该脚本包含上述所有提取和转换逻辑。

一个干净的 CSV 文件 (master_data.csv)：

该文件由 etl_script.py 自动生成（注意：根据上述 4.2.5，这可能是月度数据或每日数据）。

必须包含所有 9 个指标的列以及 Date 列（USD_CNY_Rate, US_Interest_Rate, US_CPI, CN_CPI, CN_LPR, Gold_Price, SP500_Close, CN_M2, CN_Stock_Price）。

文件中不得包含任何 NaN 或空值。

6. 验收标准

✅ etl_script.py 脚本可以成功运行，不抛出错误。

✅ 脚本成功从 FRED 获取所有 9 个数据系列（包含替代黄金序列与中国 M2、股票价格）。

✅ 脚本成功处理了混合频率问题（无论是重采样还是填充）。

✅ 脚本成功生成 master_data.csv 文件。

✅ 打开 master_data.csv 文件，数据已正确对齐，且无缺失值。
