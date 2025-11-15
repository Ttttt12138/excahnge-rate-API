import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass
import json
import hashlib
import datetime as dt
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import socket

st.set_page_config(layout="wide", page_title="汇率 (USD/CNY) 深度分析仪表盘")

def load_csv(pth: str) -> pd.DataFrame:
    @st.cache_data(show_spinner=False)
    def _load(path: str):
        try:
            if path.startswith("http://") or path.startswith("https://"):
                import urllib.request
                import io
                req = urllib.request.Request(path, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as resp:
                    data = resp.read().decode("utf-8")
                df = pd.read_csv(io.StringIO(data))
            else:
                df = pd.read_csv(path)
        except Exception as e:
            st.error(f"数据加载失败: {e}")
            return pd.DataFrame()
        df["Date"] = pd.to_datetime(df["Date"]) 
        df = df.sort_values("Date").set_index("Date")
        return df
    return _load(pth)

def load_json(pth: str):
    @st.cache_data(show_spinner=False)
    def _load(path: str):
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return _load(pth)

def filter_by_date(df: pd.DataFrame, start: dt.date, end: dt.date) -> pd.DataFrame:
    if df.empty:
        return df
    s = pd.to_datetime(start)
    e = pd.to_datetime(end) + pd.Timedelta(days=1)
    return df.loc[(df.index >= s) & (df.index < e)]

def render_kpis(kpis: dict):
    cols = st.columns(4)
    items = kpis.get("items", {})
    keys = ["USD_CNY_Rate", "US_Interest_Rate", "CN_LPR", "Gold_Price"]
    for i, k in enumerate(keys):
        it = items.get(k, {})
        val = it.get("value")
        mom = it.get("mom_pct")
        delta = None if mom is None else f"{mom*100:.2f}%"
        cols[i].metric(label=k, value=None if val is None else f"{val:.4f}", delta=delta)

def render_dual_axis(df: pd.DataFrame, y1: str, y2: str, title: str):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df.index, y=df[y1], name=y1, mode="lines"), secondary_y=False)
    fig.add_trace(go.Scatter(x=df.index, y=df[y2], name=y2, mode="lines"), secondary_y=True)
    fig.update_layout(title=title, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

def render_line(df: pd.DataFrame, col: str, title: str):
    fig = px.line(df.reset_index(), x="Date", y=col, title=title)
    st.plotly_chart(fig, use_container_width=True)

def render_scatter(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    trend = None
    try:
        import statsmodels.api as _sm
        trend = "ols"
    except ModuleNotFoundError:
        trend = None
    fig = px.scatter(df.reset_index(), x=x_col, y=y_col, trendline=trend, title=title)
    st.plotly_chart(fig, use_container_width=True)

def render_hist(df: pd.DataFrame, col: str, title: str):
    fig = px.histogram(df.reset_index(), x=col, nbins=30, title=title)
    st.plotly_chart(fig, use_container_width=True)

def render_heatmap(corr_df: pd.DataFrame, title: str, info_text: str):
    if corr_df is None or corr_df.empty:
        st.info(info_text)
        return
    fig = px.imshow(corr_df.values, x=corr_df.columns, y=corr_df.columns, color_continuous_scale="RdBu", zmin=-1, zmax=1, title=title)
    st.plotly_chart(fig, use_container_width=True)

def compute_corr(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    use_cols = [c for c in cols if c in df.columns]
    if not use_cols:
        return pd.DataFrame()
    df_num = df[use_cols].apply(pd.to_numeric, errors="coerce")
    return df_num.corr()

def _range_str(s: dt.date, e: dt.date) -> str:
    return f"{s} ~ {e}"

def _fp(chart_id: str, lang: str, s: dt.date, e: dt.date, params: dict) -> str:
    payload = {"chart_id": chart_id, "lang": lang, "start": str(s), "end": str(e), "params": params or {}}
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def _ai_cache_load() -> dict:
    if "ai_chart_cache" in st.session_state:
        return st.session_state["ai_chart_cache"]
    p = os.path.join("output", "eda", "ai_chart_cache.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                st.session_state["ai_chart_cache"] = json.load(f)
        except Exception:
            st.session_state["ai_chart_cache"] = {}
    else:
        st.session_state["ai_chart_cache"] = {}
    return st.session_state["ai_chart_cache"]

def _ai_cache_save():
    p = os.path.join("output", "eda", "ai_chart_cache.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(st.session_state.get("ai_chart_cache", {}), f, ensure_ascii=False, indent=2)

def _ai_cache_key(chart_id: str, lang: str) -> str:
    return f"{chart_id}:{lang}"

def _ai_cache_show(chart_id: str, start_date: dt.date, end_date: dt.date, params: dict, TEXT: dict):
    cache = _ai_cache_load()
    rng = _range_str(start_date, end_date)
    for lg in ["zh", "en"]:
        k = _ai_cache_key(chart_id, lg)
        entry = cache.get(k)
        if not entry:
            continue
        fp_new = _fp(chart_id, lg, start_date, end_date, params)
        if entry.get("fingerprint") != fp_new:
            cache.pop(k, None)
            continue
        ttl = "AI · 中文" if lg == "zh" else "AI · English"
        with st.expander(f"{ttl} | {TEXT[lg].get('ai_based_on_range','Based on range')}: {rng}"):
            st.write(entry.get("detail", ""))

@st.cache_data(show_spinner=False)
def compute_summary_stats(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    use_cols = [c for c in cols if c in df.columns]
    if not use_cols:
        return pd.DataFrame()
    df_num = df[use_cols].apply(pd.to_numeric, errors="coerce")
    res = {}
    for c in use_cols:
        s = df_num[c].dropna()
        if s.empty:
            continue
        res[c] = {
            "count": float(s.count()),
            "mean": float(s.mean()),
            "median": float(s.median()),
            "std": float(s.std()),
            "min": float(s.min()),
            "max": float(s.max()),
            "q25": float(s.quantile(0.25)),
            "q75": float(s.quantile(0.75)),
            "skew": float(s.skew()),
            "kurt": float(s.kurt()),
        }
    if not res:
        return pd.DataFrame()
    out = pd.DataFrame(res)
    return out.round(4)

def render_summary_stats(stats_df: pd.DataFrame, info_text: str):
    if stats_df is None or stats_df.empty:
        st.info(info_text)
        return
    st.dataframe(stats_df, use_container_width=True)

def compute_kpis(df: pd.DataFrame, keys: list[str]) -> dict:
    items: dict[str, dict] = {}
    if df is None or df.empty:
        return {"items": items}
    for k in keys:
        if k not in df.columns:
            continue
        s = df[k].dropna()
        if s.empty:
            continue
        val = float(s.iloc[-1])
        mom_pct = None
        if len(s) >= 2 and s.iloc[-2] != 0:
            mom_pct = (val - float(s.iloc[-2])) / abs(float(s.iloc[-2]))
        items[k] = {"value": val, "mom_pct": mom_pct}
    return {"items": items}

def run_gemini(query: str, df_context: pd.DataFrame, api_key: str, lang: str = "zh") -> str:
    if not api_key:
        return (
            "未检测到 Gemini API Key。请在 .env 或 Secrets 设置 GEMINI_API_KEY 或 Gemini_API_KEY。"
            if lang == "zh"
            else "Gemini API Key not found. Please set GEMINI_API_KEY or Gemini_API_KEY in .env or Secrets."
        )
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
        head = df_context.tail(50).to_string()
        if lang == "zh":
            prompt = f"以专业宏观分析师视角，根据以下数据片段进行分析并回答：\n\n数据: \n{head}\n\n问题: {query}"
        else:
            prompt = f"As a professional macro analyst, analyze the following data snippet and answer the question.\n\nData:\n{head}\n\nQuestion: {query}"
        resp = model.generate_content(prompt)
        return getattr(resp, "text", "生成成功，但未返回文本内容") if lang == "zh" else getattr(resp, "text", "Generated successfully, but no text returned")
    except ModuleNotFoundError:
        return "未安装 google-generativeai，请运行: pip install google-generativeai" if lang == "zh" else "google-generativeai not installed. Run: pip install google-generativeai"
    except Exception as e:
        return f"调用失败: {e}" if lang == "zh" else f"Call failed: {e}"

def main():
    TEXT = {
        "zh": {
            "title": "💹 汇率 (USD/CNY) 深度分析仪表盘",
            "filters": "🎛️ 过滤器 (Filters)",
            "date_range": "日期范围",
            "api_key": "Gemini API Key",
            "tab_dashboard": "仪表盘",
            "tab_ai": "AI 分析",
            "core_trends": "核心趋势",
            "macro_contrast": "宏观对比",
            "fx_gold": "汇率与黄金/股市",
            "market_switch": "市场切换",
            "m2_trend": "中国 M2 趋势",
            "corr_heat": "相关性热图",
            "corr_unavail": "相关性数据不可用",
            "summary_stats": "总结统计",
            "stats_unavail": "统计数据不可用",
            "stats_select_cols": "选择统计字段",
            "spread_fx": "利差与汇率关系",
            "fx_hist": "汇率分布直方图",
            "ai_title": "AI 智能分析",
            "example_label": "问题示例",
            "fill_example": "填入示例",
            "enter_question": "请输入你的问题...",
            "gen_analysis": "生成分析",
            "history": "历史记录（最多保留三条）",
            "clear_history": "清空历史",
            "delete_last": "删除最近一条",
            "question_prefix": "问题：",
            "chart_fx_trend": "USD/CNY 汇率长期趋势",
            "chart_rate_comp": "美中利率对比",
            "chart_infl_comp": "美中通胀对比",
            "chart_fx_gold": "汇率 vs 黄金价格",
            "chart_fx_market": "汇率 vs 市场信心",
            "chart_m2": "中国 M2 供应量趋势",
            "chart_spread_fx": "利差与汇率散点图",
            "chart_fx_hist": "汇率分布直方图",
            "btn_fx_trend": "🤖 分析 [汇率趋势]",
            "btn_gold_trend": "🤖 分析 [黄金趋势]",
            "btn_rate_comp": "🤖 分析 [利率对比]",
            "btn_cpi_comp": "🤖 分析 [通胀对比]",
            "btn_spread_fx": "🤖 分析 [利差与汇率]",
            "btn_corr_matrix": "🤖 分析 [相关性矩阵]",
            "btn_fx_hist": "🤖 分析 [汇率分布]",
            "ai_need_key": "未检测到 Key，请在侧边栏输入或设置 .env/Secrets",
            "ai_cached": "已缓存（与当前筛选一致）",
            "ai_based_on_range": "基于区间",
        },
        "en": {
            "title": "💹 USD/CNY Deep Analysis Dashboard",
            "filters": "🎛️ Filters",
            "date_range": "Date Range",
            "api_key": "Gemini API Key",
            "tab_dashboard": "Dashboard",
            "tab_ai": "AI Analysis",
            "core_trends": "Core Trends",
            "macro_contrast": "Macro Comparison",
            "fx_gold": "FX & Gold / Equities",
            "market_switch": "Market Toggle",
            "m2_trend": "China M2 Trend",
            "corr_heat": "Correlation Heatmap",
            "corr_unavail": "Correlation data unavailable",
            "summary_stats": "Summary Stats",
            "stats_unavail": "Summary data unavailable",
            "stats_select_cols": "Select fields",
            "spread_fx": "Spread vs FX",
            "fx_hist": "FX Histogram",
            "ai_title": "AI Analysis",
            "example_label": "Example Questions",
            "fill_example": "Fill Example",
            "enter_question": "Enter your question...",
            "gen_analysis": "Generate Analysis",
            "history": "History (max 3)",
            "clear_history": "Clear History",
            "delete_last": "Delete Latest",
            "question_prefix": "Question:",
            "chart_fx_trend": "USD/CNY Long-term Trend",
            "chart_rate_comp": "US-CN Interest Rate Comparison",
            "chart_infl_comp": "US-CN Inflation Comparison",
            "chart_fx_gold": "FX vs Gold Price",
            "chart_fx_market": "FX vs Market Confidence",
            "chart_m2": "China M2 Supply Trend",
            "chart_spread_fx": "Spread vs FX Scatter",
            "chart_fx_hist": "FX Distribution Histogram",
            "btn_fx_trend": "🤖 Analyze [FX Trend]",
            "btn_gold_trend": "🤖 Analyze [Gold Trend]",
            "btn_rate_comp": "🤖 Analyze [Rate Comparison]",
            "btn_cpi_comp": "🤖 Analyze [CPI Comparison]",
            "btn_spread_fx": "🤖 Analyze [Spread vs FX]",
            "btn_corr_matrix": "🤖 Analyze [Correlation Matrix]",
            "btn_fx_hist": "🤖 Analyze [FX Distribution]",
            "ai_need_key": "API Key missing. Enter in sidebar or set .env/Secrets",
            "ai_cached": "Cached (matches current filter)",
            "ai_based_on_range": "Based on range",
        },
    }
    KPI_LABELS = {
        "zh": {
            "USD_CNY_Rate": "USD/CNY 汇率",
            "US_Interest_Rate": "美国利率",
            "CN_LPR": "中国LPR",
            "Gold_Price": "黄金价格",
            "SP500_Close": "标普500收盘",
            "CN_M2": "中国M2",
            "US_CPI": "美国CPI",
            "CN_CPI": "中国CPI",
            "CN_Stock_Price": "中国股市指数",
        },
        "en": {
            "USD_CNY_Rate": "USD/CNY Rate",
            "US_Interest_Rate": "US Interest Rate",
            "CN_LPR": "CN LPR",
            "Gold_Price": "Gold Price",
            "SP500_Close": "S&P 500 Close",
            "CN_M2": "China M2",
            "US_CPI": "US CPI",
            "CN_CPI": "China CPI",
            "CN_Stock_Price": "China Stock Index",
        },
    }
    if "lang" not in st.session_state:
        st.session_state["lang"] = "中文"
    lang_choice = st.sidebar.selectbox("Language / 语言", ["中文", "English"], index=0 if st.session_state["lang"] == "中文" else 1)
    st.session_state["lang"] = lang_choice
    lang = "zh" if lang_choice == "中文" else "en"
    st.title(TEXT[lang]["title"])
    default_url = os.environ.get("DATA_URL", "")
    try:
        default_url = st.secrets.get("DATA_URL", default_url)
    except Exception:
        pass
    data_url = st.sidebar.text_input("数据源 URL (Gist Raw)", value=default_url)
    src_path = data_url if data_url else os.path.join("output", "master_data.csv")
    if not (data_url.startswith("http://") or data_url.startswith("https://")) and not os.path.exists(src_path):
        st.error("未找到数据文件。请在侧边栏输入 Gist Raw URL 或在 Secrets 设置 DATA_URL。")
        st.stop()
    df = load_csv(src_path)
    if df.empty:
        st.stop()
    df["Interest_Spread"] = df["US_Interest_Rate"] - df["CN_LPR"]
    kpis = load_json(os.path.join("output", "eda", "kpis.json"))
    corr_df = None
    corr_path = os.path.join("output", "eda", "correlation.csv")
    if os.path.exists(corr_path):
        corr_df = pd.read_csv(corr_path, index_col=0)
    st.sidebar.title(TEXT[lang]["filters"])
    date_min = df.index.min().date() if not df.empty else dt.date(2000, 1, 1)
    date_max = df.index.max().date() if not df.empty else dt.date.today()
    date_range = st.sidebar.date_input(TEXT[lang]["date_range"], (date_min, date_max))
    api_key_default = os.environ.get("GEMINI_API_KEY", os.environ.get("Gemini_API_KEY", ""))
    try:
        v = st.secrets.get("GEMINI_API_KEY", None)
        if v:
            api_key_default = v
    except Exception:
        pass
    if api_key_default:
        api_key = api_key_default
        st.sidebar.caption("✅ 已检测到 API Key")
    else:
        st.sidebar.caption("⚠️ 未检测到 API Key")
        api_key = st.sidebar.text_input(TEXT[lang]["api_key"], type="password")
    selectable_cols = [
        "USD_CNY_Rate",
        "US_Interest_Rate",
        "CN_LPR",
        "US_CPI",
        "CN_CPI",
        "Gold_Price",
        "SP500_Close",
        "CN_M2",
        "CN_Stock_Price",
        "Interest_Spread",
    ]
    available_cols = [c for c in selectable_cols if c in df.columns]
    selected_stats_cols = st.sidebar.multiselect(TEXT[lang]["stats_select_cols"], options=available_cols, default=available_cols[:4])
    start_date, end_date = date_range if isinstance(date_range, tuple) else (date_min, date_max)
    df_f = filter_by_date(df, start_date, end_date)
    if corr_df is None or corr_df.empty:
        corr_cols = [
            "USD_CNY_Rate",
            "US_Interest_Rate",
            "CN_LPR",
            "US_CPI",
            "CN_CPI",
            "Gold_Price",
            "SP500_Close",
            "CN_M2",
            "CN_Stock_Price",
            "Interest_Spread",
        ]
        corr_df = compute_corr(df_f, corr_cols)
    tab1, tab2 = st.tabs([TEXT[lang]["tab_dashboard"], TEXT[lang]["tab_ai"]])
    with tab1:
        kpi_keys = list(KPI_LABELS[lang].keys())
        computed = compute_kpis(df_f, kpi_keys)
        items = {}
        for k in kpi_keys:
            src = kpis.get("items", {}).get(k, {}) if kpis else {}
            comp = computed.get("items", {}).get(k, {})
            items[k] = {
                "value": src.get("value", comp.get("value")),
                "mom_pct": src.get("mom_pct", comp.get("mom_pct")),
                "qoq_pct": src.get("qoq_pct"),
            }
        render_kpis({"items": items})
        st.subheader(TEXT[lang]["core_trends"])
        render_line(df_f, "USD_CNY_Rate", TEXT[lang]["chart_fx_trend"])
        _ai_cache_show("fx_trend", start_date, end_date, {}, TEXT)
        if st.button(TEXT[lang]["btn_fx_trend"]):
            s = df_f["USD_CNY_Rate"].dropna()
            if s.empty:
                st.info(TEXT[lang]["stats_unavail"])
            elif not api_key:
                st.info(TEXT[lang]["ai_need_key"])
            else:
                desc = s.describe().to_string()
                head = df_f[["USD_CNY_Rate"]].head().to_string()
                if lang == "zh":
                    prompt = f"你是一个金融分析师。基于以下统计数据与数据摘要，分析 USD/CNY 汇率在所选时间范围内的趋势、波动性和关键转折点。\n\n统计:\n{desc}\n\n数据摘要:\n{head}"
                else:
                    prompt = f"You are a financial analyst. Analyze USD/CNY trend, volatility and turning points based on stats and snippet.\n\nStats:\n{desc}\n\nSnippet:\n{head}"
                resp = run_gemini(prompt, df_f, api_key, lang)
                with st.expander(TEXT[lang]["ai_cached"] + f" | {TEXT[lang]['ai_based_on_range']}: " + _range_str(start_date, end_date)):
                    st.write(resp)
                if "ai_history" not in st.session_state:
                    st.session_state["ai_history"] = []
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                summ = resp.strip()
                if len(summ) > 160:
                    summ = summ[:160] + "..."
                entry = {"time": ts, "question": "FX Trend", "summary": summ, "detail": resp}
                st.session_state["ai_history"].append(entry)
                st.session_state["ai_history"] = st.session_state["ai_history"][-7:]
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
                cache = _ai_cache_load()
                key = _ai_cache_key("fx_trend", lang)
                fpv = _fp("fx_trend", lang, start_date, end_date, {})
                cache[key] = {"fingerprint": fpv, "detail": resp, "summary": summ, "time": ts}
                _ai_cache_save()
        st.subheader(TEXT[lang]["macro_contrast"])
        render_dual_axis(df_f, "US_Interest_Rate", "CN_LPR", TEXT[lang]["chart_rate_comp"])
        _ai_cache_show("rate_comp", start_date, end_date, {}, TEXT)
        if st.button(TEXT[lang]["btn_rate_comp"]):
            if df_f.empty:
                st.info(TEXT[lang]["stats_unavail"])
            elif not api_key:
                st.info(TEXT[lang]["ai_need_key"])
            else:
                c = df_f["US_Interest_Rate"].corr(df_f["CN_LPR"]) if "US_Interest_Rate" in df_f.columns and "CN_LPR" in df_f.columns else None
                sp = None
                if "US_Interest_Rate" in df_f.columns and "CN_LPR" in df_f.columns and not df_f[["US_Interest_Rate","CN_LPR"]].dropna().empty:
                    sp = (df_f["US_Interest_Rate"].iloc[-1] - df_f["CN_LPR"].iloc[-1]) * 100
                if lang == "zh":
                    prompt = f"你是一个经济学家。美中利率的相关系数为 {c if c is not None else 'N/A'}，最新利差为 {sp if sp is not None else 'N/A'} 基点。请分析两国利率在所选时间内的走势是趋同还是分化，并解释这种相关性。"
                else:
                    prompt = f"You are an economist. US vs CN rates correlation is {c if c is not None else 'N/A'}, latest spread {sp if sp is not None else 'N/A'} bps. Analyze convergence/divergence and explain correlation."
                resp = run_gemini(prompt, df_f, api_key, lang)
                with st.expander(TEXT[lang]["ai_cached"] + f" | {TEXT[lang]['ai_based_on_range']}: " + _range_str(start_date, end_date)):
                    st.write(resp)
                if "ai_history" not in st.session_state:
                    st.session_state["ai_history"] = []
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                summ = resp.strip()
                if len(summ) > 160:
                    summ = summ[:160] + "..."
                entry = {"time": ts, "question": "Rate Comparison", "summary": summ, "detail": resp}
                st.session_state["ai_history"].append(entry)
                st.session_state["ai_history"] = st.session_state["ai_history"][-7:]
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
                cache = _ai_cache_load()
                key = _ai_cache_key("rate_comp", lang)
                fpv = _fp("rate_comp", lang, start_date, end_date, {})
                cache[key] = {"fingerprint": fpv, "detail": resp, "summary": summ, "time": ts}
                _ai_cache_save()
        render_dual_axis(df_f, "US_CPI", "CN_CPI", TEXT[lang]["chart_infl_comp"])
        _ai_cache_show("cpi_comp", start_date, end_date, {}, TEXT)
        if st.button(TEXT[lang]["btn_cpi_comp"]):
            if df_f.empty:
                st.info(TEXT[lang]["stats_unavail"])
            elif not api_key:
                st.info(TEXT[lang]["ai_need_key"])
            else:
                c = df_f["US_CPI"].corr(df_f["CN_CPI"]) if "US_CPI" in df_f.columns and "CN_CPI" in df_f.columns else None
                if lang == "zh":
                    prompt = f"分析美国和中国的 CPI 走势。相关系数为 {c if c is not None else 'N/A'}。这说明了什么？"
                else:
                    prompt = f"Analyze US and CN CPI trends. Correlation is {c if c is not None else 'N/A'}. What does it imply?"
                resp = run_gemini(prompt, df_f, api_key, lang)
                with st.expander(TEXT[lang]["ai_cached"] + f" | {TEXT[lang]['ai_based_on_range']}: " + _range_str(start_date, end_date)):
                    st.write(resp)
                if "ai_history" not in st.session_state:
                    st.session_state["ai_history"] = []
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                summ = resp.strip()
                if len(summ) > 160:
                    summ = summ[:160] + "..."
                entry = {"time": ts, "question": "CPI Comparison", "summary": summ, "detail": resp}
                st.session_state["ai_history"].append(entry)
                st.session_state["ai_history"] = st.session_state["ai_history"][-7:]
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
        st.subheader(TEXT[lang]["fx_gold"])
        market_choice = st.radio(TEXT[lang]["market_switch"], ["SP500_Close", "CN_Stock_Price"], horizontal=True, format_func=lambda x: KPI_LABELS[lang].get(x, x))
        render_dual_axis(df_f, "USD_CNY_Rate", "Gold_Price", TEXT[lang]["chart_fx_gold"])
        _ai_cache_show("gold_trend", start_date, end_date, {}, TEXT)
        if st.button(TEXT[lang]["btn_gold_trend"]):
            s = df_f["Gold_Price"].dropna()
            if s.empty:
                st.info(TEXT[lang]["stats_unavail"])
            elif not api_key:
                st.info(TEXT[lang]["ai_need_key"])
            else:
                desc = s.describe().to_string()
                head = df_f[["Gold_Price"]].head().to_string()
                if lang == "zh":
                    prompt = f"你是一个金融分析师。基于以下统计与数据摘要，分析黄金价格在所选时间范围内的趋势与波动性。\n\n统计:\n{desc}\n\n数据摘要:\n{head}"
                else:
                    prompt = f"You are a financial analyst. Analyze gold price trend and volatility based on stats and snippet.\n\nStats:\n{desc}\n\nSnippet:\n{head}"
                resp = run_gemini(prompt, df_f, api_key, lang)
                with st.expander(TEXT[lang]["ai_cached"] + f" | {TEXT[lang]['ai_based_on_range']}: " + _range_str(start_date, end_date)):
                    st.write(resp)
                if "ai_history" not in st.session_state:
                    st.session_state["ai_history"] = []
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                summ = resp.strip()
                if len(summ) > 160:
                    summ = summ[:160] + "..."
                entry = {"time": ts, "question": "Gold Trend", "summary": summ, "detail": resp}
                st.session_state["ai_history"].append(entry)
                st.session_state["ai_history"] = st.session_state["ai_history"][-7:]
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
        render_dual_axis(df_f, "USD_CNY_Rate", market_choice, TEXT[lang]["chart_fx_market"])
        st.subheader(TEXT[lang]["m2_trend"])
        render_line(df_f, "CN_M2", TEXT[lang]["chart_m2"])
        st.subheader(TEXT[lang]["corr_heat"])
        render_heatmap(corr_df if corr_df is not None else pd.DataFrame(), TEXT[lang]["corr_heat"], TEXT[lang]["corr_unavail"])
        _ai_cache_show("corr_matrix", start_date, end_date, {}, TEXT)
        if st.button(TEXT[lang]["btn_corr_matrix"]):
            cols = ["USD_CNY_Rate","US_Interest_Rate","CN_LPR","US_CPI","CN_CPI","Gold_Price","SP500_Close","CN_M2","CN_Stock_Price","Interest_Spread"]
            use = [c for c in cols if c in df_f.columns]
            if not use:
                st.info(TEXT[lang]["corr_unavail"])
            elif not api_key:
                st.info(TEXT[lang]["ai_need_key"])
            else:
                js = df_f[use].corr().to_json()
                if lang == "zh":
                    prompt = f"这是相关性矩阵(JSON): {js}。请找出与 USD/CNY_Rate 相关性最强(正或负)的三个变量，并解释含义。"
                else:
                    prompt = f"This is the correlation matrix (JSON): {js}. Find the top 3 variables most correlated (pos/neg) with USD_CNY_Rate and explain."
                resp = run_gemini(prompt, df_f, api_key, lang)
                with st.expander(TEXT[lang]["ai_cached"] + f" | {TEXT[lang]['ai_based_on_range']}: " + _range_str(start_date, end_date)):
                    st.write(resp)
                if "ai_history" not in st.session_state:
                    st.session_state["ai_history"] = []
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                summ = resp.strip()
                if len(summ) > 160:
                    summ = summ[:160] + "..."
                entry = {"time": ts, "question": "Correlation Matrix", "summary": summ, "detail": resp}
                st.session_state["ai_history"].append(entry)
                st.session_state["ai_history"] = st.session_state["ai_history"][-7:]
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
        st.subheader(TEXT[lang]["summary_stats"]) 
        stats_df = compute_summary_stats(df_f, selected_stats_cols)
        render_summary_stats(stats_df, TEXT[lang]["stats_unavail"]) 
        st.subheader(TEXT[lang]["spread_fx"])
        render_scatter(df_f, "Interest_Spread", "USD_CNY_Rate", TEXT[lang]["chart_spread_fx"])
        _ai_cache_show("spread_fx", start_date, end_date, {}, TEXT)
        if st.button(TEXT[lang]["btn_spread_fx"]):
            if df_f.empty:
                st.info(TEXT[lang]["stats_unavail"])
            elif not api_key:
                st.info(TEXT[lang]["ai_need_key"])
            else:
                c = df_f["Interest_Spread"].corr(df_f["USD_CNY_Rate"]) if "Interest_Spread" in df_f.columns and "USD_CNY_Rate" in df_f.columns else None
                if lang == "zh":
                    prompt = f"你是一个外汇策略师。美中利差与 USD/CNY 汇率的相关系数为 {c if c is not None else 'N/A'}。请定量分析利差是否是汇率的强驱动因素？该相关性方向与经济含义是什么？"
                else:
                    prompt = f"You are an FX strategist. Correlation between spread and USD/CNY is {c if c is not None else 'N/A'}. Assess strength as driver, sign, and economic meaning."
                resp = run_gemini(prompt, df_f, api_key, lang)
                with st.expander(TEXT[lang]["ai_cached"] + f" | {TEXT[lang]['ai_based_on_range']}: " + _range_str(start_date, end_date)):
                    st.write(resp)
                if "ai_history" not in st.session_state:
                    st.session_state["ai_history"] = []
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                summ = resp.strip()
                if len(summ) > 160:
                    summ = summ[:160] + "..."
                entry = {"time": ts, "question": "Spread vs FX", "summary": summ, "detail": resp}
                st.session_state["ai_history"].append(entry)
                st.session_state["ai_history"] = st.session_state["ai_history"][-7:]
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
        st.subheader(TEXT[lang]["fx_hist"])
        render_hist(df_f, "USD_CNY_Rate", TEXT[lang]["chart_fx_hist"])
        _ai_cache_show("fx_hist", start_date, end_date, {}, TEXT)
        if st.button(TEXT[lang]["btn_fx_hist"]):
            s = df_f["USD_CNY_Rate"].dropna()
            if s.empty:
                st.info(TEXT[lang]["stats_unavail"])
            elif not api_key:
                st.info(TEXT[lang]["ai_need_key"])
            else:
                skew = s.skew()
                kurt = s.kurt()
                if lang == "zh":
                    prompt = f"分析 USD/CNY 汇率的统计分布。其偏度为 {skew:.4f}，峰度为 {kurt:.4f}。解释该分布的偏态与峰度以及对外汇风险的含义。"
                else:
                    prompt = f"Analyze USD/CNY distribution. Skewness {skew:.4f}, kurtosis {kurt:.4f}. Explain skew/peakedness and FX risk implications."
                resp = run_gemini(prompt, df_f, api_key, lang)
                with st.expander(TEXT[lang]["ai_cached"] + f" | {TEXT[lang]['ai_based_on_range']}: " + _range_str(start_date, end_date)):
                    st.write(resp)
                if "ai_history" not in st.session_state:
                    st.session_state["ai_history"] = []
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                summ = resp.strip()
                if len(summ) > 160:
                    summ = summ[:160] + "..."
                entry = {"time": ts, "question": "FX Histogram", "summary": summ, "detail": resp}
                st.session_state["ai_history"].append(entry)
                st.session_state["ai_history"] = st.session_state["ai_history"][-7:]
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
    if "ai_query" not in st.session_state:
        st.session_state["ai_query"] = ""
    if "ai_history" not in st.session_state:
        hist_path = os.path.join("output", "eda", "ai_history.json")
        h = load_json(hist_path)
        if isinstance(h, list):
            st.session_state["ai_history"] = h[-3:]
        else:
            st.session_state["ai_history"] = []
    with tab2:
        st.subheader(TEXT[lang]["ai_title"])
        examples_zh = [
            "请分析最近三个月 USD/CNY 的主要驱动因素，并引用利差与通胀差。",
            "黄金价格与汇率的关系在本区间内是否显著？请给出结论与依据。",
            "当前利差与汇率的线性相关性强度如何？是否有结构性变化迹象？",
            "美国与中国股市对汇率的关联度对比，哪个更强？",
            "请根据相关性热图总结三条最重要的宏观关联。",
            "从 M2 与通胀角度，推断未来一个季度汇率可能的风险方向。",
        ]
        examples_en = [
            "Analyze the main drivers of USD/CNY over the last three months, referencing spread and inflation.",
            "Is the relationship between gold price and USD/CNY significant in this range? Provide conclusion and evidence.",
            "How strong is the linear correlation between interest spread and USD/CNY? Any structural shifts?",
            "Compare correlations of US vs China equities with USD/CNY. Which is stronger?",
            "Summarize three key macro correlations based on the heatmap.",
            "From M2 and inflation perspectives, infer potential FX risk direction for next quarter.",
        ]
        sel = st.selectbox(TEXT[lang]["example_label"], examples_zh if lang == "zh" else examples_en)
        c1, c2 = st.columns([1, 1])
        if c1.button(TEXT[lang]["fill_example"]):
            st.session_state["ai_query"] = sel
        q = st.text_area(TEXT[lang]["enter_question"], key="ai_query")
        if c2.button(TEXT[lang]["gen_analysis"]):
            resp = run_gemini(q, df_f, api_key, lang)
            st.write(resp)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            summ = resp.strip()
            if len(summ) > 160:
                summ = summ[:160] + "..."
            entry = {"time": ts, "question": q, "summary": summ, "detail": resp}
            st.session_state["ai_history"].append(entry)
            st.session_state["ai_history"] = st.session_state["ai_history"][-3:]
            save_path = os.path.join("output", "eda", "ai_history.json")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                import json as _json
                _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
        st.divider()
        st.caption(TEXT[lang]["history"])
        c_del_all, c_del_last = st.columns([1,1])
        if c_del_all.button(TEXT[lang]["clear_history"]):
            st.session_state["ai_history"] = []
            save_path = os.path.join("output", "eda", "ai_history.json")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                import json as _json
                _json.dump([], f, ensure_ascii=False, indent=2)
            st.rerun()
        if c_del_last.button(TEXT[lang]["delete_last"]):
            if st.session_state.get("ai_history"):
                st.session_state["ai_history"].pop()
                save_path = os.path.join("output", "eda", "ai_history.json")
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w", encoding="utf-8") as f:
                    import json as _json
                    _json.dump(st.session_state["ai_history"], f, ensure_ascii=False, indent=2)
                st.rerun()
        for idx, item in enumerate(reversed(st.session_state["ai_history"])):
            label = f"{item.get('time','')} | {item.get('summary','')}"
            with st.expander(label):
                st.markdown(f"{TEXT[lang]['question_prefix']}{item.get('question','')}")
                st.markdown(item.get("detail", ""))

if __name__ == "__main__":
    main()
                cache = _ai_cache_load()
                key = _ai_cache_key("cpi_comp", lang)
                fpv = _fp("cpi_comp", lang, start_date, end_date, {})
                cache[key] = {"fingerprint": fpv, "detail": resp, "summary": summ, "time": ts}
                _ai_cache_save()
                cache = _ai_cache_load()
                key = _ai_cache_key("gold_trend", lang)
                fpv = _fp("gold_trend", lang, start_date, end_date, {})
                cache[key] = {"fingerprint": fpv, "detail": resp, "summary": summ, "time": ts}
                _ai_cache_save()
                cache = _ai_cache_load()
                key = _ai_cache_key("corr_matrix", lang)
                fpv = _fp("corr_matrix", lang, start_date, end_date, {})
                cache[key] = {"fingerprint": fpv, "detail": resp, "summary": summ, "time": ts}
                _ai_cache_save()
                cache = _ai_cache_load()
                key = _ai_cache_key("spread_fx", lang)
                fpv = _fp("spread_fx", lang, start_date, end_date, {})
                cache[key] = {"fingerprint": fpv, "detail": resp, "summary": summ, "time": ts}
                _ai_cache_save()
                cache = _ai_cache_load()
                key = _ai_cache_key("fx_hist", lang)
                fpv = _fp("fx_hist", lang, start_date, end_date, {})
                cache[key] = {"fingerprint": fpv, "detail": resp, "summary": summ, "time": ts}
                _ai_cache_save()
