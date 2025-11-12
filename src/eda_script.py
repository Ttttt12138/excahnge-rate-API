import os
import argparse
import logging
import json
import pandas as pd

def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", default=os.path.join("output", "master_data.csv"))
    p.add_argument("--out-dir", default=os.path.join("output", "eda"))
    return p.parse_args()

def _init_logger():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def _load_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"]) 
    df = df.sort_values("Date").set_index("Date")
    return df

def _save_csv(df: pd.DataFrame, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path)

def _save_json(obj: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _describe(df: pd.DataFrame) -> pd.DataFrame:
    return df.describe()

def _corr(df: pd.DataFrame) -> pd.DataFrame:
    return df.corr(numeric_only=True)

def _metrics(df: pd.DataFrame) -> dict:
    interest_spread = df["US_Interest_Rate"] - df["CN_LPR"]
    inflation_spread = df["US_CPI"] - df["CN_CPI"]
    m = {}
    m["volatility_usd_cny"] = float(df["USD_CNY_Rate"].std())
    m["interest_spread_mean"] = float(interest_spread.mean())
    m["inflation_spread_mean"] = float(inflation_spread.mean())
    m["corr_usd_cny_gold"] = float(df["USD_CNY_Rate"].corr(df["Gold_Price"]))
    m["corr_usd_cny_interest_spread"] = float(df["USD_CNY_Rate"].corr(interest_spread))
    m["corr_usd_cny_sp500"] = float(df["USD_CNY_Rate"].corr(df["SP500_Close"]))
    m["corr_usd_cny_cn_stock"] = float(df["USD_CNY_Rate"].corr(df["CN_Stock_Price"]))
    m["skew_usd_cny"] = float(df["USD_CNY_Rate"].skew())
    return m

def _kpis(df: pd.DataFrame) -> dict:
    fields = [
        "USD_CNY_Rate",
        "US_Interest_Rate",
        "CN_LPR",
        "Gold_Price",
        "SP500_Close",
        "CN_M2",
        "US_CPI",
        "CN_CPI",
        "CN_Stock_Price",
    ]
    last_date = df.index.max()
    mom = df[fields].pct_change(periods=1)
    qoq = df[fields].pct_change(periods=3)
    out = {"date": last_date.strftime("%Y-%m-%d"), "items": {}}
    for f in fields:
        last_val = df[f].iloc[-1] if len(df[f]) > 0 else None
        mom_val = mom[f].iloc[-1] if len(mom[f]) > 0 else None
        qoq_val = qoq[f].iloc[-1] if len(qoq[f]) > 0 else None
        out["items"][f] = {
            "value": None if pd.isna(last_val) else float(last_val),
            "mom_pct": None if pd.isna(mom_val) else float(mom_val),
            "qoq_pct": None if pd.isna(qoq_val) else float(qoq_val),
        }
    return out

def main():
    args = _parse_args()
    _init_logger()
    logging.info("loading %s", args.inp)
    df = _load_df(args.inp)
    logging.info("computing describe")
    desc = _describe(df)
    _save_csv(desc, os.path.join(args.out_dir, "describe.csv"))
    logging.info("computing correlation")
    corr = _corr(df)
    _save_csv(corr, os.path.join(args.out_dir, "correlation.csv"))
    logging.info("computing metrics")
    metrics = _metrics(df)
    _save_json(metrics, os.path.join(args.out_dir, "metrics.json"))
    logging.info("computing kpis")
    kpis = _kpis(df)
    _save_json(kpis, os.path.join(args.out_dir, "kpis.json"))
    logging.info("saved outputs to %s", args.out_dir)

if __name__ == "__main__":
    main()

