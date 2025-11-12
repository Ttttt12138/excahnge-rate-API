# 汇率分析 ETL 项目实现计划

## 项目目标与范围

* 目标：按需求文档实现从 FRED 与 Yahoo Finance 自动获取 8 个数据系列，统一转换频率与缺失值处理，生成无缺失、可用于 BI 的主数据集 `master_data.csv`。

* 范围：只做 ETL/转换与可运行脚本，不做 EDA 与仪表盘设计。

## 技术栈与依赖

* Python 3.x（建议 3.13+）

* 依赖：`pandas`、`fredapi`、`yfinance`

* 环境变量：`FRED_API_KEY`（用于 FRED 认证）

## 项目结构

* `src/etl_script.py`：主脚本，包含提取、清理、合并、频率处理、输出与校验。

* `output/master_data.csv`：脚本运行后生成的主数据文件（路径可通过参数覆盖）。

* `requirements.txt`：依赖列表（可选）。

## 数据提取（Extract）

* FRED（使用 `fredapi`）：

  * 系列：`DEXCHUS`（USD/CNY）、`FEDFUNDS`（美国联邦基金利率）、`CPIAUCSL`（美国 CPI）、`CHNCPIALLMINMEI`（中国 CPI）、`DPRCMLTLPR1Y`（中国 1Y LPR）

  * 从环境变量读取 `FRED_API_KEY`，使用 `Fred(api_key=...)` 与 `get_series(series_id, observation_start=..., observation_end=...)`。

* Yahoo Finance（使用 `yfinance`）：

  * 代码：`GC=F`（黄金期货）、`^GSPC`（标普 500）、`000001.SS`（上证指数）

  * 只保留 `Close` 列：`yf.Ticker(symbol).history(start=..., end=...).loc[:, ['Close']]`

* 统一日期范围参数：`--start`（默认 `2000-01-01`）、`--end`（默认今天）。

## 数据清理与重命名（Clean）

* 重命名为业务字段：

  * `USD_CNY_Rate`、`US_Interest_Rate`、`Gold_Price`、`US_CPI`、`CN_CPI`、`CN_LPR`、`SP500_Close`、`SSE_Close`

* 统一索引为 `DatetimeIndex`（UTC 忽略时区），并按日期排序去重。

## 合并与缺失值（Merge & Missing Values）

* 使用日期索引横向合并：`pd.concat([...], axis=1)`。

* 每日数据（汇率/利率/价格/指数）：统一采用前向填充 `ffill` 以覆盖周末与假期空档。

* 合并后进行一次全表 `ffill` 与必要的 `bfill` 以消除首段缺口。

## 频率处理（Mixed Frequencies）

* 默认模式：`monthly`（推荐）。

  * 使用 `df.resample('M').last()` 生成月末值（也可选择 `mean`，通过参数控制）。

  * 对重采样后残余空值执行 `ffill`，确保最终无 `NaN`。

* 备用模式：`daily`。

  * 对月度数据（`US_CPI`、`CN_CPI`、`CN_LPR`）做 `ffill` 展开到日频，再与已 `ffill` 的日频数据合并。

* 通过参数 `--mode {monthly|daily}` 与（仅限 monthly）`--monthly-agg {last|mean}` 控制策略。

## 输出与校验（Load & Validate）

* 将索引转 `Date` 列后输出 CSV：`df.reset_index().to_csv(path, index=False)`。

* 校验：

  * 列完整性：必须包含 8 个业务列与 `Date`。

  * 缺失值检查：`df.isna().sum().sum() == 0`。

  * 行数与日期范围合理性（开始/结束日期覆盖）。

## 可运行性与参数化

* 命令行参数：

  * `--start`、`--end` 日期；`--mode` 频率；`--monthly-agg`；`--out` 输出路径。

* 环境读取：从系统环境读取 `FRED_API_KEY`；如不存在则报错提示设置。

* 日志：使用 `logging` 输出关键步骤与耗时；对网络调用做简易重试（不引入额外依赖）。

## 错误处理与鲁棒性

* 网络/速率限制：捕获 `HTTPError`/连接超时，重试后降级或退出并给出明确提示。

* 数据对齐：在合并前统一索引类型与时区；避免重复索引；对异常日期做过滤。

## 交付与验收

* 准备：创建虚拟环境，安装依赖；设置 `FRED_API_KEY`。

* 运行示例：

  * `python src/etl_script.py --mode monthly --monthly-agg last --out output/master_data.csv`

* 验收：脚本无错误，成功生成 `master_data.csv`；打开文件列齐全且无缺失值。

## 后续工作（非本阶段）

* 进行 EDA 与特征分析（相关性、滞后、滚动统计）。

* 基于 `master_data.csv` 构建可视化仪表盘（如 Tableau/Power BI/Streamlit）。

