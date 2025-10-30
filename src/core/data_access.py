# src/core/data_access.py
from __future__ import annotations
from pathlib import Path
from typing import Optional, Iterable, Dict, Any, List
import glob
import pandas as pd

# DuckDB optionnel (plus rapide)
try:
    import duckdb
    _HAS_DUCK = True
except Exception:
    _HAS_DUCK = False

def _latest_glob(pattern: str) -> Optional[Path]:
    parts = sorted(Path(".").glob(pattern))
    return parts[-1] if parts else None

# ---------- PRICES / FEATURES ----------

def get_close_series_from_features(ticker: str) -> Optional[pd.Series]:
    """Lit close depuis features/prices_features_daily (plus rapide/compact)."""
    pat = "data/features/table=prices_features_daily/dt=*/final.parquet"
    if _HAS_DUCK:
        con = duckdb.connect()
        try:
            df = con.execute(f"""
              SELECT date, close
              FROM read_parquet('{pat}')
              WHERE symbol = ?
              ORDER BY date
            """, [ticker]).df()
            if df.empty: return None
            s = pd.to_datetime(df["date"], errors="coerce")
            out = pd.Series(df["close"].values, index=s, name="Close")
            return out
        finally:
            con.close()
    # Fallback pandas
    files = sorted(Path("data/features/table=prices_features_daily").glob("dt=*/final.parquet"))
    if not files: return None
    dfs = []
    for f in files[-7:]:  # dernières partitions pour limiter les IO
        try:
            d = pd.read_parquet(f)
            d = d[d["symbol"] == ticker]
            if not d.empty:
                dfs.append(d[["date","close"]])
        except Exception:
            pass
    if not dfs: return None
    df = pd.concat(dfs, ignore_index=True).dropna()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date")
    return pd.Series(df["close"].values, index=df["date"], name="Close")

def get_close_series_legacy(ticker: str) -> Optional[pd.Series]:
    """Lit data/prices/ticker=.../prices.parquet si présent."""
    p = Path("data/prices")/f"ticker={ticker}"/"prices.parquet"
    if not p.exists(): return None
    df = pd.read_parquet(p)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.set_index("date").sort_index()
    col = "Close" if "Close" in df.columns else ("close" if "close" in df.columns else None)
    if not col: return None
    return df[col].rename("Close")

def get_close_series(ticker: str) -> Optional[pd.Series]:
    """Priorité features → fallback legacy."""
    s = get_close_series_from_features(ticker)
    return s if s is not None and not s.empty else get_close_series_legacy(ticker)

def coverage_days_from_features(ticker: str) -> Optional[int]:
    s = get_close_series_from_features(ticker)
    if s is None or s.empty: return None
    return int((s.index.max() - s.index.min()).days)

# ---------- MACRO ----------

def load_macro_forecast_rows(limit: int = 200) -> Dict[str, Any]:
    """Préférence macro_forecast parquet; fallback macro_snapshot_daily features."""
    p = _latest_glob("data/macro/forecast/dt=*/macro_forecast.parquet")
    if p and p.exists():
        df = pd.read_parquet(p).head(limit)
        return {"ok": True, "path": str(p), "columns": list(df.columns), "rows": df.to_dict(orient="records")}
    # fallback features
    pf = _latest_glob("data/features/table=macro_snapshot_daily/dt=*/final.parquet")
    if pf and pf.exists():
        df = pd.read_parquet(pf).head(limit)
        return {"ok": True, "path": str(pf), "columns": list(df.columns), "rows": df.to_dict(orient="records"), "fallback": "features_macro_snapshot_daily"}
    return {"ok": False, "reason": "no_macro"}

# ---------- NEWS (agrégées) ----------

def load_news_features(limit: int = 100) -> Dict[str, Any]:
    p = _latest_glob("data/features/table=news_features_daily/dt=*/final.parquet")
    if p and p.exists():
        df = pd.read_parquet(p).head(limit)
        return {"ok": True, "path": str(p), "columns": list(df.columns), "rows": df.to_dict(orient="records")}
    # fallback brut (parquets news)
    ps = sorted(Path("data/news").glob("dt=*/news_*.parquet"))
    if ps:
        try:
            df = pd.concat([pd.read_parquet(x).head(50) for x in ps[-4:]], ignore_index=True)
            return {"ok": True, "path": "data/news", "columns": list(df.columns), "rows": df.head(limit).to_dict(orient="records"), "fallback": "raw_news"}
        except Exception:
            pass
    return {"ok": False, "reason": "no_news"}