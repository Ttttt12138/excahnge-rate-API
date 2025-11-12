## 前置
- 设置当前目录：`Set-Location "D:\Trae-project\excahnge-rate API"`
- 确认 `.env` 内容为：`FRED_API_KEY=8cedcfd0830d67703744b6f5da3c786c`

## 安装依赖
- `pip install -r requirements.txt`
- 如报缺：`pip install certifi cffi frozendict platformdirs`
- 如需升级证书：`pip install --upgrade certifi`

## 证书环境变量
- 获取证书路径：`$cert = (python -c "import certifi; print(certifi.where())").Trim()`
- 设置会话变量：
  - `$env:CURL_CA_BUNDLE = $cert`
  - `$env:REQUESTS_CA_BUNDLE = $cert`
  - `$env:YF_USE_CURL_CFFI = "0"`

## 运行脚本
- 月度（月末聚合）：`python src/etl_script.py --mode monthly --monthly-agg last --out output/master_data.csv`
- 日度（月度数据前向填充到日频）：`python src/etl_script.py --mode daily --out output/master_data.csv`

## 验证输出
- 行数与缺失检查：`python -c "import pandas as pd; df=pd.read_csv('output/master_data.csv'); print('rows=',len(df),'na=',df.isna().sum().sum())"`

## 常见问题
- 若仍出现 curl/证书错误：
  - 重新执行“证书环境变量”步骤并确保 `$cert` 指向有效路径
  - 再次运行：`python src/etl_script.py --mode monthly --monthly-agg last --out output/master_data.csv`
- 使用特定解释器（Conda 环境）：
  - `& C:/ProgramData/miniconda3/envs/exchange_rate/python.exe "D:/Trae-project/excahnge-rate API/src/etl_script.py" --mode monthly --monthly-agg last --out output/master_data.csv`