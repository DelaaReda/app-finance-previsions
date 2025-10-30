from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

try:
    from hub.logging_setup import get_logger  # type: ignore
    from hub import profiler as _prof  # type: ignore
    _log = get_logger("api")  # type: ignore
except Exception:
    class _P:
        def log_event(self,*a,**k): pass
    class _L:
        def info(self,*a,**k): pass
        def debug(self,*a,**k): pass
        def warning(self,*a,**k): pass
        def exception(self,*a,**k): pass
    _prof = _P()  # type: ignore
    _log = _L()   # type: ignore


def _ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}


def _err(msg: str) -> Dict[str, Any]:
    return {"ok": False, "error": msg}


# ----------------------------- Forecasts ---------------------------------- #

def _load_equity_final() -> pd.DataFrame:
    try:
        parts = sorted(Path('data/forecast').glob('dt=*'))
        if not parts:
            return pd.DataFrame()
        p = parts[-1] / 'final.parquet'
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _load_commodity() -> pd.DataFrame:
    try:
        parts = sorted(Path('data/forecast').glob('dt=*'))
        if not parts:
            return pd.DataFrame()
        p = parts[-1] / 'commodities.parquet'
        return pd.read_parquet(p) if p.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def forecasts(asset_type: str = 'all', horizon: str = 'all', search: str | None = None, sort_by: str = 'score') -> Dict[str, Any]:
    """Return forecasts as JSON rows for React UI."""
    _prof.log_event("http", {"path": "/api/forecasts", "asset_type": asset_type, "horizon": horizon, "sort_by": sort_by, "search": search})
    _log.debug("api.forecasts", extra={"ctx": {"asset_type": asset_type, "horizon": horizon, "sort_by": sort_by, "search": search}})

    if asset_type == 'equity':
        df = _load_equity_final()
        tag = 'equity'
    elif asset_type == 'commodity':
        df = _load_commodity()
        tag = 'commodity'
    else:
        e = _load_equity_final()
        c = _load_commodity()
        if not e.empty:
            e['asset_type'] = 'equity'
        if not c.empty:
            c['asset_type'] = 'commodity'
        df = pd.concat([d for d in [e, c] if not d.empty], ignore_index=True) if (not e.empty or not c.empty) else pd.DataFrame()
        tag = 'all'

    if df.empty:
        return _ok({"rows": [], "count": 0, "asset_type": tag})

    if horizon != 'all' and 'horizon' in df.columns:
        df = df[df['horizon'] == horizon]

    if search:
        terms = [t.strip().lower() for t in search.split(',') if t.strip()]
        mask = pd.Series(False, index=df.index)
        for t in terms:
            for col in [c for c in ['ticker','commodity_name','category'] if c in df.columns]:
                mask |= df[col].astype(str).str.lower().str.contains(t, na=False)
        df = df[mask]

    if df.empty:
        return _ok({"rows": [], "count": 0, "asset_type": tag})

    # Sorting
    if tag == 'commodity' or ('confidence' in df.columns and sort_by in ['score','confidence']):
        col = 'confidence' if 'confidence' in df.columns else 'expected_return'
        df = df.sort_values(col, ascending=False)
    elif 'final_score' in df.columns:
        df = df.sort_values('final_score', ascending=False)
    else:
        if 'expected_return' in df.columns:
            df = df.sort_values('expected_return', ascending=False)

    # Keep a compact set of columns for API
    wanted = [c for c in ['asset_type','ticker','commodity_name','category','horizon','final_score','direction','confidence','expected_return'] if c in df.columns]
    out = df[wanted].reset_index(drop=True).to_dict('records')
    return _ok({"rows": out, "count": len(out), "asset_type": tag})


# -------------------------------- News ------------------------------------ #

def news(sector: str = 'all', search: str | None = None) -> Dict[str, Any]:
    _prof.log_event("http", {"path": "/api/news", "sector": sector, "search": search})
    try:
        parts = sorted(Path('data/news').glob('dt=*'))
        df = pd.DataFrame()
        if parts:
            latest = parts[-1]
            files = sorted(latest.glob('news_*.parquet'))
            if files:
                df = pd.read_parquet(files[-1])
        if df.empty and Path('data/news.jsonl').exists():
            df = pd.read_json('data/news.jsonl', lines=True)
        if df.empty:
            return _ok({"rows": [], "count": 0})
        if search:
            s = search.lower()
            df = df[df.get('title','').str.lower().str.contains(s, na=False) | df.get('summary','').str.lower().str.contains(s, na=False)]
        # simple sector filter placeholder using tickers
        if sector != 'all' and 'tickers' in df.columns:
            sector_tickers = {
                'tech': ['AAPL','MSFT','GOOGL','AMZN'],
                'finance': ['JPM','BAC','WFC','GS'],
                'energy': ['XOM','CVX','COP','SLB']
            }
            if sector in sector_tickers:
                df = df[df['tickers'].apply(lambda x: any(t in sector_tickers[sector] for t in (x or [])) if isinstance(x, list) else False)]
        rows = df[['title','summary','source','sentiment']].head(200).fillna('').to_dict('records')
        return _ok({"rows": rows, "count": len(rows)})
    except Exception as e:
        _log.exception("api.news.fail", extra={"ctx": {"error": str(e)}})
        return _err(str(e))


# ------------------------------ Watchlist --------------------------------- #

def watchlist_get() -> Dict[str, Any]:
    try:
        fp = Path('data/watchlist.json')
        if fp.exists():
            js = json.loads(fp.read_text(encoding='utf-8'))
            return _ok({"watchlist": js.get('watchlist', [])})
        return _ok({"watchlist": []})
    except Exception as e:
        return _err(str(e))


def watchlist_set(tickers: List[str]) -> Dict[str, Any]:
    try:
        Path('data').mkdir(parents=True, exist_ok=True)
        Path('data/watchlist.json').write_text(json.dumps({"watchlist": tickers}, ensure_ascii=False, indent=2), encoding='utf-8')
        return _ok({"saved": len(tickers)})
    except Exception as e:
        return _err(str(e))


# ------------------------------- Settings --------------------------------- #

def settings_get() -> Dict[str, Any]:
    try:
        fp = Path('data/config/alerts.json')
        if fp.exists():
            js = json.loads(fp.read_text(encoding='utf-8'))
            return _ok(js)
        return _ok({"move_abs_pct": 1.0, "tilt": "balanced"})
    except Exception as e:
        return _err(str(e))


def settings_set(move_abs_pct: float, tilt: str) -> Dict[str, Any]:
    try:
        cfg = Path('data/config')
        cfg.mkdir(parents=True, exist_ok=True)
        data = {"move_abs_pct": float(move_abs_pct), "tilt": tilt}
        (cfg / 'alerts.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return _ok({"saved": True})
    except Exception as e:
        return _err(str(e))


# ------------------------------ LLM Judge --------------------------------- #

def llm_judge_run(model: str, max_er: float = 0.08, min_conf: float = 0.6, tickers: str | None = None) -> Dict[str, Any]:
    """Fire context build then LLM forecast agent; return summarized info."""
    try:
        _prof.log_event("http", {"path": "/api/llm/judge/run", "model": model, "max_er": max_er, "min_conf": min_conf, "tickers": tickers})
        _log.info("api.llm_judge.start", extra={"ctx": {"model": model, "max_er": max_er, "min_conf": min_conf, "tickers": tickers}})
        cmd_ctx = ["python3", "-m", "src.agents.llm_context_builder_agent"]
        if tickers and tickers.strip():
            cmd_ctx += ["--tickers", tickers.strip()]
        out1 = subprocess.run(cmd_ctx, capture_output=True, text=True, timeout=180)
        env = {
            'LLM_USE_G4F': '1',
            'LLM_MODEL': model,
            'LLM_MAX_ER': str(max_er),
        }
        out2 = subprocess.run(["python3", "scripts/llm_forecast_agent.py"], capture_output=True, text=True, timeout=300, env={**dict(Path), **env} if False else None)
        # Read latest llm_agents.json
        base = Path('data/forecast')
        parts = sorted(base.glob('dt=*/llm_agents.json'))
        rows: List[Dict[str, Any]] = []
        if parts:
            try:
                js = json.loads(parts[-1].read_text(encoding='utf-8'))
                for t in js.get('tickers', []):
                    m = (t.get('models') or [{}])[0]
                    rows.append({
                        'ticker': t.get('ticker'),
                        'direction': m.get('direction'),
                        'expected_return': m.get('expected_return'),
                        'confidence': m.get('confidence'),
                        'provider': m.get('name') or m.get('source'),
                    })
            except Exception:
                pass
        _log.info("api.llm_judge.done", extra={"ctx": {"rows": len(rows)}})
        return _ok({
            "stdout": {
                "context": (out1.stdout or '').strip(),
                "forecast": (out2.stdout or '').strip(),
            },
            "rows": rows,
        })
    except Exception as e:
        _log.exception("api.llm_judge.fail", extra={"ctx": {"error": str(e)}})
        return _err(str(e))

