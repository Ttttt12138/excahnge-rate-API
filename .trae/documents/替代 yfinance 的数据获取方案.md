## 目标
- 去除 `yfinance`，用 FRED 与 Tushare 获取黄金、标普与上证数据，满足 8 指标 ETL 输出。

## 变更概览
- 依赖：移除 `yfinance`，新增 `tushare`
- 数据源替换：
  - 黄金价格 → FRED `GOLDAMGBD228NLBM` → `Gold_Price`
  - 标普500 → FRED `SP500` → `SP500_Close`
  - 上证指数 → Tushare `index_daily(ts_code='000001.SH')` → `SSE_Close`
- 频率与缺失：保持既有 `ffill`；月度模式使用 `resample('ME').last()` 或 `mean`

## 技术实现
- 修改 `src/etl_script.py`：
  - 删除 `yfinance` 相关导入与 `_yf_close`
  - 新增 `import tushare as ts` 与 `_ts_pro()`（从 `.env`/环境读取 `TUSHARE_TOKEN`，初始化 `ts.set_token`，返回 `pro_api()`）
  - 新增 `_ts_sse_close(start, end)`：调用 `pro.index_daily(ts_code='000001.SH', start_date='YYYYMMDD', end_date='YYYYMMDD')`，取 `close` 重命名为 `SSE_Close`，索引为日期
  - 在 `_extract()` 中用 FRED 获取 `SP500` 与 `GOLDAMGBD228NLBM`，用 `_ts_sse_close` 获取上证收盘价
  - 其余 FRED 指标与清理/合并/重采样/校验逻辑保持不变
- 修改 `requirements.txt`：移除 `yfinance`，添加 `tushare`
- `.env` 读取：沿用现有 `.env` 解析方式，新增对 `TUSHARE_TOKEN` 的读取（若未设置则报错）

## 运行方式
- 设置 `.env`：
  - `FRED_API_KEY=你的FRED密钥`
  - `TUSHARE_TOKEN=你的Tushare令牌`
- 运行：
  - `python src/etl_script.py --mode monthly --monthly-agg last --out output/master_data.csv`

## 验证与验收
- 检查 `output/master_data.csv` 包含 `Date` 与 8 列且无缺失
- 随机抽查黄金/标普/上证行值与来源一致性

## 风险与回退
- 若 Tushare 网络受限：保留 FRED 与 Tushare调用的错误处理与重试；如需回退，可暂时将上证列置为缺失后在月度模式 `ffill`，但验收需无缺失则不建议

## 下一步
- 我将按此方案更新脚本与依赖，接着安装 `tushare` 并运行验证