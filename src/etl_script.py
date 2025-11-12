import os
import re
import argparse
import logging
import time
from datetime import datetime
import pandas as pd
from fredapi import Fred
os.environ["YF_USE_CURL_CFFI"] = "0"
import tushare as ts

def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2000-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--mode", choices=["monthly", "daily"], default="monthly")
    p.add_argument("--monthly-agg", choices=["last", "mean"], default="last")
    p.add_argument("--out", default=os.path.join("output", "master_data.csv"))
    p.add_argument("--fred-key", default=None)
    p.add_argument("--fred-key-file", default=None)
    return p.parse_args()

def _init_logger():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def _get_env_value(name: str) -> str:
    v = os.getenv(name)
    if v:
        return v.strip().strip("'\"")
    env_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, ".env")),
    ]
    for pth in env_paths:
        if os.path.exists(pth):
            with open(pth, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    if "=" in s:
                        k, val = s.split("=", 1)
                        k_norm = re.sub(r"[^A-Za-z_]", "", k).upper()
                        if k_norm == name.upper():
                            return val.strip().strip("'\"")
    return ""

def _fred_client():
    key = os.getenv("FRED_API_KEY")
    if not key:
        env_paths = [
            os.path.join(os.getcwd(), ".env"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, ".env")),
        ]
        for pth in env_paths:
            if not key and os.path.exists(pth):
                logging.info("reading .env %s", pth)
                with open(pth, "r", encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith("#"):
                            continue
                        s_raw = line
                        if not key and "fred_api_key" in s_raw.lower():
                            part = s_raw
                            if "=" in part:
                                part = part.split("=", 1)[1]
                            v_norm2 = "".join(re.findall(r"[a-z0-9]", part.lower()))
                            if len(v_norm2) >= 32:
                                key = v_norm2[:32]
                                logging.info("loaded key from .env direct")
                                break
                        if "=" in s:
                            k, v = s.split("=", 1)
                            k_norm = re.sub(r"[^a-z]", "", k.lower())
                            v_norm = "".join(re.findall(r"[a-z0-9]", v.lower()))
                            logging.info("env key line k=%s len(v)=%d", k_norm, len(v_norm))
                            if k_norm == "fredapikey" and len(v_norm) >= 32:
                                key = v_norm[:32]
                                logging.info("loaded key from .env")
                                break
        candidates = []
        env_path = os.getenv("FRED_API_KEY_FILE")
        if env_path:
            candidates.append(env_path)
        candidates.append(os.path.join("secrets", "fred_api_key.txt"))
        candidates.append(os.path.join(os.getcwd(), "fred_api_key.txt"))
        script_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        candidates.append(os.path.join(script_root, "fred_api_key.txt"))
        for key_file in candidates:
            if not key and os.path.exists(key_file):
                logging.info("reading key file %s", key_file)
                with open(key_file, "r", encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if not s:
                            continue
                        if "=" in s:
                            s = s.split("=", 1)[1].strip()
                        s = s.strip("'\"")
                        s_norm = "".join(re.findall(r"[a-z0-9]", s.lower()))
                        if len(s_norm) >= 32:
                            key = s_norm[:32]
                            logging.info("loaded key from file")
                            break
    if not key:
        raise RuntimeError("FRED_API_KEY not set")
    return Fred(api_key=key)

def _fred_series(fred: Fred, series_id: str, start: str, end: str) -> pd.DataFrame:
    s = fred.get_series(series_id, observation_start=start, observation_end=end)
    df = s.to_frame(name=series_id)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df

def _fred_series_by_query(fred: Fred, query: str, start: str, end: str, out_col: str) -> pd.DataFrame:
    res = fred.search(query)
    chosen = None
    if isinstance(res, pd.DataFrame) and len(res) > 0:
        chosen = res.iloc[0].get("id")
    if not chosen:
        raise RuntimeError("fred search no match")
    df = _fred_series(fred, chosen, start, end)
    return df.rename(columns={df.columns[0]: out_col})

def _fred_series_try_list(fred: Fred, ids: list, start: str, end: str, out_col: str) -> pd.DataFrame:
    for sid in ids:
        try:
            df = _fred_series(fred, sid, start, end)
            return df.rename(columns={sid: out_col})
        except Exception:
            pass
    raise RuntimeError("fred series list no match")

def _ts_pro():
    token = _get_env_value("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN not set")
    ts.set_token(token)
    return ts.pro_api()

def _ts_gold_price(start: str, end: str) -> pd.DataFrame:
    pro = _ts_pro()
    start_s = pd.to_datetime(start).strftime("%Y%m%d")
    end_s = pd.to_datetime(end).strftime("%Y%m%d")
    try:
        df = pro.index_daily(ts_code="AU9999.SGE", start_date=start_s, end_date=end_s)
        if df is not None and len(df) > 0:
            df["trade_date"] = pd.to_datetime(df["trade_date"]) 
            df = df.sort_values("trade_date").set_index("trade_date")
            return df.loc[:, ["close"]].rename(columns={"close": "Gold_Price"})
    except Exception:
        pass
    try:
        df = pro.fut_daily(ts_code="AU", start_date=start_s, end_date=end_s)
        if df is not None and len(df) > 0:
            df["trade_date"] = pd.to_datetime(df["trade_date"]) 
            df = df.sort_values("trade_date").set_index("trade_date")
            return df.loc[:, ["close"]].rename(columns={"close": "Gold_Price"})
    except Exception:
        pass
    raise RuntimeError("tushare gold series no match")

 

def _ts_sse_close(start: str, end: str) -> pd.DataFrame:
    pro = _ts_pro()
    start_s = pd.to_datetime(start).strftime("%Y%m%d")
    end_s = pd.to_datetime(end).strftime("%Y%m%d")
    df = pro.index_daily(ts_code="000001.SH", start_date=start_s, end_date=end_s)
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["SSE_Close"])  
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date")
    df = df.set_index("trade_date")
    df = df.loc[:, ["close"]].rename(columns={"close": "SSE_Close"})
    return df

def _extract(start: str, end: str) -> dict:
    fred = _fred_client()
    usd_cny = _fred_series(fred, "DEXCHUS", start, end).rename(columns={"DEXCHUS": "USD_CNY_Rate"})
    fedfunds = _fred_series(fred, "FEDFUNDS", start, end).rename(columns={"FEDFUNDS": "US_Interest_Rate"})
    us_cpi = _fred_series(fred, "CPIAUCSL", start, end).rename(columns={"CPIAUCSL": "US_CPI"})
    cn_cpi = _fred_series(fred, "CHNCPIALLMINMEI", start, end).rename(columns={"CHNCPIALLMINMEI": "CN_CPI"})
    cn_lpr = None
    try:
        cn_lpr = _fred_series(fred, "DPRCMLTLPR1Y", start, end).rename(columns={"DPRCMLTLPR1Y": "CN_LPR"})
    except Exception:
        cn_lpr = _fred_series_by_query(
            fred,
            "Immediate Rates (< 24 Hours): Central Bank Rates: Total for China",
            start,
            end,
            "CN_LPR",
        )
    try:
        gold = _fred_series_by_query(
            fred,
            "Credit Suisse NASDAQ Gold FLOWS103 Price Index",
            start,
            end,
            "Gold_Price",
        )
    except Exception:
        try:
            gold = _fred_series_by_query(
                fred,
                "Export Price Index (End Use): Nonmonetary Gold",
                start,
                end,
                "Gold_Price",
            )
        except Exception:
            gold = _fred_series_by_query(
                fred,
                "Import Price Index (End Use): Nonmonetary Gold",
                start,
                end,
                "Gold_Price",
            )
    sp500 = _fred_series_try_list(
        fred,
        ["SP500"],
        start,
        end,
        "SP500_Close",
    )
    cn_stock = None
    try:
        cn_stock = _fred_series_by_query(
            fred,
            "Stock Price Index for China",
            start,
            end,
            "CN_Stock_Price",
        )
    except Exception:
        try:
            cn_stock = _fred_series_by_query(
                fred,
                "Share Prices: Total for China",
                start,
                end,
                "CN_Stock_Price",
            )
        except Exception:
            cn_stock = _fred_series_by_query(
                fred,
                "Stock Prices: Total for China",
                start,
                end,
                "CN_Stock_Price",
            )
    cn_m2 = _fred_series_by_query(
        fred,
        "Money Supply M2 for China",
        start,
        end,
        "CN_M2",
    )
    return {
        "USD_CNY_Rate": usd_cny,
        "US_Interest_Rate": fedfunds,
        "US_CPI": us_cpi,
        "CN_CPI": cn_cpi,
        "CN_LPR": cn_lpr,
        "Gold_Price": gold,
        "SP500_Close": sp500,
        "CN_M2": cn_m2,
        "CN_Stock_Price": cn_stock,
    }

def _transform(dfs: dict, mode: str, monthly_agg: str) -> pd.DataFrame:
    df = pd.concat(list(dfs.values()), axis=1)
    df = df.sort_index()
    daily_cols = ["USD_CNY_Rate", "US_Interest_Rate", "SP500_Close"]
    monthly_cols = ["US_CPI", "CN_CPI", "CN_LPR", "Gold_Price", "CN_M2", "CN_Stock_Price"]
    df[daily_cols] = df[daily_cols].ffill()
    if mode == "daily":
        df[monthly_cols] = df[monthly_cols].ffill()
    else:
        if monthly_agg == "last":
            df = df.resample("ME").last()
        else:
            df = df.resample("ME").mean()
        df = df.ffill()
    df = df.dropna()
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"
    return df

def _validate(df: pd.DataFrame):
    expected = ["USD_CNY_Rate", "US_Interest_Rate", "Gold_Price", "US_CPI", "CN_CPI", "CN_LPR", "SP500_Close", "CN_M2", "CN_Stock_Price"]
    cols = ["Date"] + expected
    if any(c not in df.columns for c in expected):
        raise RuntimeError("columns missing")
    if df.isna().sum().sum() != 0:
        raise RuntimeError("nan present")

def _save(df: pd.DataFrame, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.reset_index().to_csv(out_path, index=False)

def main():
    args = _parse_args()
    _init_logger()
    if args.fred_key:
        os.environ["FRED_API_KEY"] = "".join(re.findall(r"[a-z0-9]", args.fred_key.lower()))[:32]
    elif args.fred_key_file and os.path.exists(args.fred_key_file):
        with open(args.fred_key_file, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if "=" in s:
                    s = s.split("=", 1)[1].strip()
                s = s.strip("'\"")
                s_norm = "".join(re.findall(r"[a-z0-9]", s.lower()))
                if len(s_norm) >= 32:
                    os.environ["FRED_API_KEY"] = s_norm[:32]
                    break
    start = args.start
    end = args.end or datetime.today().strftime("%Y-%m-%d")
    logging.info("extract start=%s end=%s", start, end)
    dfs = _extract(start, end)
    logging.info("transform mode=%s", args.mode)
    df = _transform(dfs, args.mode, args.monthly_agg)
    _validate(df)
    _save(df, args.out)
    logging.info("saved %s rows=%d", args.out, len(df))

if __name__ == "__main__":
    main()
