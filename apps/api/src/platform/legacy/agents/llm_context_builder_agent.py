from __future__ import annotations

"""
Build compact LLM contexts per ticker from existing data (prices, macro, news, peers).
Writes: data/llm/context/dt=YYYYMMDD/{ticker}.json

Usage:
  PYTHONPATH=src python -m src.agents.llm_context_builder_agent --tickers NGD.TO,AAPL,MSFT
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


DT_FMT = "%Y%m%d"


def today_dt() -> str:
    # Use timezone-aware UTC to avoid deprecation warnings and ambiguity
    return datetime.now(timezone.utc).strftime(DT_FMT)


def _read_watchlist() -> List[str]:
    wl = []
    try:
        obj = json.loads(Path('data/watchlist.json').read_text(encoding='utf-8'))
        wl = [str(x).strip().upper() for x in (obj.get('watchlist') or []) if str(x).strip()]
    except Exception:
        pass
    return wl or ["NGD.TO", "AAPL", "MSFT", "SPY", "GDX"]


def _latest_macro_parquet() -> Optional[Path]:
    parts = sorted(Path('data/macro/forecast').glob('dt=*/macro_forecast.parquet'))
    return parts[-1] if parts else None


def _latest_news_parquet() -> Optional[Path]:
    parts = sorted(Path('data/news').glob('dt=*/news_*.parquet'))
    return parts[-1] if parts else None


def _price_summary(ticker: str) -> Dict:
    p = Path(f'data/prices/ticker={ticker}/prices.parquet')
    if not p.exists():
        return {"available": False}
    try:
        df = pd.read_parquet(p)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.set_index('date').sort_index()
        col = 'Close' if 'Close' in df.columns else ('close' if 'close' in df.columns else None)
        if not col or df.empty:
            return {"available": False}
        s = pd.to_numeric(df[col], errors='coerce').dropna()
        if s.empty:
            return {"available": False}
        def ret(days):
            i = max(0, len(s) - days)
            return float(s.iloc[-1] / s.iloc[i] - 1)
        r_1m = ret(21)
        r_3m = ret(63)
        r_1y = ret(252)
        vol_1m = float(s.pct_change().dropna().tail(21).std()) if len(s) > 21 else None
        dd = float(1 - s / s.cummax()).max()
        return {
            "available": True,
            "last": float(s.iloc[-1]),
            "ret_1m": r_1m, "ret_3m": r_3m, "ret_1y": r_1y,
            "vol_1m": vol_1m, "max_drawdown": dd
        }
    except Exception:
        return {"available": False}


def _macro_kpis() -> Dict:
    p = _latest_macro_parquet()
    if not p or not p.exists():
        return {}
    try:
        df = pd.read_parquet(p)
        def last(*cols):
            for c in cols:
                if c in df.columns:
                    v = df[c].dropna()
                    if not v.empty:
                        return float(v.iloc[-1])
            return None
        return {
            "cpi_yoy": last('cpi_yoy','CPI_YoY','cpi_yoy_pct','inflation_yoy'),
            "yield_curve_slope": last('slope_10y_2y','yc_10y_2y','yield_curve_slope'),
            "recession_prob": last('recession_prob','recession_probability','recession_12m')
        }
    except Exception:
        return {}


def _news_digest(limit: int = 10) -> List[Dict]:
    p = _latest_news_parquet()
    out: List[Dict] = []
    try:
        if p and p.exists():
            df = pd.read_parquet(p)
            df = df.head(limit)
            for _, row in df.iterrows():
                out.append({
                    "title": str(row.get('title','')),
                    "summary": str(row.get('summary',''))[:240],
                    "source": str(row.get('source','')),
                    "sent": str(row.get('sentiment','')),
                })
        else:
            try:
                # fallback news.jsonl
                if Path('data/news.jsonl').exists():
                    import itertools
                    for i, line in zip(range(limit), Path('data/news.jsonl').open('r', encoding='utf-8')):
                        obj = json.loads(line)
                        out.append({
                            "title": obj.get('title',''),
                            "summary": (obj.get('summary','') or '')[:240],
                            "source": obj.get('source',''),
                            "sent": obj.get('sentiment',''),
                        })
            except Exception:
                pass
    except Exception:
        return out
    return out


def _peers_perf(ticker: str, peers: List[str]) -> List[Dict]:
    out: List[Dict] = []
    for t in peers:
        if t.upper() == ticker.upper():
            continue
        ps = _price_summary(t)
        if ps.get('available'):
            out.append({"ticker": t, "ret_1m": ps.get('ret_1m'), "ret_3m": ps.get('ret_3m'), "ret_1y": ps.get('ret_1y')})
    return out[:10]


def build_context_for(ticker: str) -> Dict:
    prices = _price_summary(ticker)
    macro = _macro_kpis()
    news = _news_digest(limit=10)
    peers = _peers_perf(ticker, _read_watchlist())
    ctx = {
        "ticker": ticker,
        "dt": today_dt(),
        "prices": prices,
        "macro": macro,
        "news": news,
        "peers": peers,
        "meta": {"sources": [s for s,_ in [("prices", prices.get('available')), ("macro", bool(macro)), ("news", bool(news)), ("peers", bool(peers))] if _]}
    }
    return ctx


def write_context(ctx: Dict) -> Path:
    outdir = Path('data/llm/context') / f"dt={today_dt()}"
    outdir.mkdir(parents=True, exist_ok=True)
    fp = outdir / f"{ctx['ticker']}.json"
    fp.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding='utf-8')
    return fp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tickers', default=','.join(_read_watchlist()))
    args = ap.parse_args()
    tickers = [t.strip().upper() for t in str(args.tickers).split(',') if t.strip()]
    written = []
    for t in tickers:
        ctx = build_context_for(t)
        written.append(str(write_context(ctx)))
    print(json.dumps({"ok": True, "written": len(written), "files": written}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
