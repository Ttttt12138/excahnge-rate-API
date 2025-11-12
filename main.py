import os
import sys
import argparse
from datetime import datetime
import subprocess
import time
import json
import urllib.request
import urllib.error
import socket
from src import etl_script, eda_script

def _etl(args):
    if args.fred_key:
        import re
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
                import re
                s_norm = "".join(re.findall(r"[a-z0-9]", s.lower()))
                if len(s_norm) >= 32:
                    os.environ["FRED_API_KEY"] = s_norm[:32]
                    break
    start = args.start
    end = args.end or datetime.today().strftime("%Y-%m-%d")
    dfs = etl_script._extract(start, end)
    df = etl_script._transform(dfs, args.mode, args.monthly_agg)
    etl_script._validate(df)
    etl_script._save(df, args.out)

def _eda(args):
    df = eda_script._load_df(args.inp)
    desc = eda_script._describe(df)
    eda_script._save_csv(desc, os.path.join(args.out_dir, "describe.csv"))
    corr = eda_script._corr(df)
    eda_script._save_csv(corr, os.path.join(args.out_dir, "correlation.csv"))
    metrics = eda_script._metrics(df)
    eda_script._save_json(metrics, os.path.join(args.out_dir, "metrics.json"))
    kpis = eda_script._kpis(df)
    eda_script._save_json(kpis, os.path.join(args.out_dir, "kpis.json"))

def _dash(args):
    cmd = [sys.executable, "-m", "streamlit", "run", os.path.join("src", "streamlit_app.py")]
    if args.port:
        cmd.extend(["--server.port", str(args.port)])
    subprocess.Popen(cmd)

def _start_ngrok(port: int):
    print("尝试建立临时公网隧道 …")
    try:
        subprocess.Popen(["ngrok", "http", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("未检测到 ngrok，请安装并确保在 PATH。示例: ngrok config add-authtoken <你的令牌>")
        return None
    public_url = None
    for _ in range(20):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for t in data.get("tunnels", []):
                    url = t.get("public_url")
                    if url and (url.startswith("http://") or url.startswith("https://")):
                        public_url = url
                        break
                if public_url:
                    break
        except Exception:
            pass
    if public_url:
        print(f"临时公网 URL: {public_url}")
    else:
        print(f"未能获取 ngrok 公网地址，请手动运行: ngrok http {port}")
    return public_url

def _pick_available_port(start_port: int) -> int:
    for p in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start_port

def _host_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def _run_all(args):
    print("开始执行 ETL …")
    try:
        _etl(args)
        print(f"ETL 完成，输出: {args.out}")
    except Exception as e:
        print(f"ETL 失败，将使用现有数据。原因: {e}")
    inp = args.out if os.path.exists(args.out) else os.path.join("output", "master_data.csv")
    print(f"开始执行 EDA … 读取: {inp}")
    try:
        df = eda_script._load_df(inp)
        print(f"数据加载完成，行数: {len(df)}")
        desc = eda_script._describe(df)
        eda_script._save_csv(desc, os.path.join(args.eda_out_dir, "describe.csv"))
        print("已生成: describe.csv")
        corr = eda_script._corr(df)
        eda_script._save_csv(corr, os.path.join(args.eda_out_dir, "correlation.csv"))
        print("已生成: correlation.csv")
        metrics = eda_script._metrics(df)
        eda_script._save_json(metrics, os.path.join(args.eda_out_dir, "metrics.json"))
        print("已生成: metrics.json")
        kpis = eda_script._kpis(df)
        eda_script._save_json(kpis, os.path.join(args.eda_out_dir, "kpis.json"))
        print("已生成: kpis.json")
        print(f"EDA 完成，输出目录: {args.eda_out_dir}")
    except Exception as e:
        print(f"EDA 失败，原因: {e}")
    chosen_port = _pick_available_port(args.port)
    if chosen_port != args.port:
        print(f"端口 {args.port} 已占用，改用 {chosen_port}")
        args.port = chosen_port
    print(f"启动仪表盘 … 端口: {args.port}")
    _dash(args)
    local_url = f"http://localhost:{args.port}"
    net_url = f"http://{_host_ip()}:{args.port}"
    print("\n  You can now view your Streamlit app in your browser.\n")
    print(f"  Local URL: {local_url}")
    print(f"  Network URL: {net_url}")
    _start_ngrok(args.port)

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    p_etl = sub.add_parser("etl")
    p_etl.add_argument("--start", default="2000-01-01")
    p_etl.add_argument("--end", default=None)
    p_etl.add_argument("--mode", choices=["monthly", "daily"], default="monthly")
    p_etl.add_argument("--monthly-agg", choices=["last", "mean"], default="last")
    p_etl.add_argument("--out", default=os.path.join("output", "master_data.csv"))
    p_etl.add_argument("--fred-key", default=None)
    p_etl.add_argument("--fred-key-file", default=None)
    p_etl.set_defaults(func=_etl)
    p_eda = sub.add_parser("eda")
    p_eda.add_argument("--in", dest="inp", default=os.path.join("output", "master_data.csv"))
    p_eda.add_argument("--out-dir", default=os.path.join("output", "eda"))
    p_eda.set_defaults(func=_eda)
    p_dash = sub.add_parser("dash")
    p_dash.add_argument("--port", type=int, default=8501)
    p_dash.set_defaults(func=_dash)
    p_run = sub.add_parser("run-all")
    p_run.add_argument("--start", default="2000-01-01")
    p_run.add_argument("--end", default=None)
    p_run.add_argument("--mode", choices=["monthly", "daily"], default="monthly")
    p_run.add_argument("--monthly-agg", choices=["last", "mean"], default="last")
    p_run.add_argument("--out", default=os.path.join("output", "master_data.csv"))
    p_run.add_argument("--fred-key", default=None)
    p_run.add_argument("--fred-key-file", default=None)
    p_run.add_argument("--eda-out-dir", dest="eda_out_dir", default=os.path.join("output", "eda"))
    p_run.add_argument("--port", type=int, default=8501)
    p_run.set_defaults(func=_run_all)
    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
