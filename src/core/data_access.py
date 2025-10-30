# src/core/data_access.py
"""
Unified data access layer with priority: features → legacy
Provides clean abstractions for reading prices, macro, news from optimized formats
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd

# DuckDB optional (faster queries)
try:
    import duckdb
    _HAS_DUCK = True
except ImportError:
    _HAS_DUCK = False

def _latest_glob(pattern: str) -> Optional[Path]:
    """Find latest partition matching glob pattern."""
    parts = sorted(Path(".").glob(pattern))
    return parts[-1] if parts else None

# ============================= PRICES / FEATURES =============================

def get_close_series_from_features(ticker: str) -> Optional[pd.Series]:
    """
    Read close prices from optimized features Parquet.
    Uses DuckDB if available for fast cross-partition queries.
    """
    pat = "data/features/table=prices_features_daily/dt=*/final.parquet"
    
    if _HAS_DUCK:
        try:
            con = duckdb.connect()
            df = con.execute(f"""
                SELECT date, close
                FROM read_parquet('{pat}')
                WHERE symbol = ?
                ORDER BY date
            """, [ticker]).df()
            con.close()
            
            if df.empty:
                return None
                
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            return pd.Series(df["close"].values, index=df["date"], name="Close")
        except Exception:
            pass
    
    # Fallback: pandas scan
    files = sorted(Path("data/features/table=prices_features_daily").glob("dt=*/final.parquet"))
    if not files:
        return None
        
    dfs = []
    for f in files[-7:]:  # Last 7 partitions to limit I/O
        try:
            d = pd.read_parquet(f)
            d = d[d["symbol"] == ticker]
            if not d.empty:
                dfs.append(d[["date", "close"]])
        except Exception:
            continue
            
    if not dfs:
        return None
        
    df = pd.concat(dfs, ignore_index=True).dropna()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date")
    return pd.Series(df["close"].values, index=df["date"], name="Close")

def get_close_series_legacy(ticker: str) -> Optional[pd.Series]:
    """Read prices from legacy data/prices/ticker=.../prices.parquet format."""
    p = Path("data/prices") / f"ticker={ticker}" / "prices.parquet"
    if not p.exists():
        return None
        
    try:
        df = pd.read_parquet(p)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.set_index("date").sort_index()
        elif "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.set_index("Date").sort_index()
            
        # Find Close column (case-insensitive)
        col = None
        for c in ["Close", "close", "CLOSE"]:
            if c in df.columns:
                col = c
                break
                
        if not col:
            return None
            
        return df[col].rename("Close")
    except Exception:
        return None

def get_close_series(ticker: str) -> Optional[pd.Series]:
    """
    Get close price series for ticker.
    Priority: features → legacy
    """
    s = get_close_series_from_features(ticker)
    if s is not None and not s.empty:
        return s
    return get_close_series_legacy(ticker)

def coverage_days_from_features(ticker: str) -> Optional[int]:
    """Calculate data coverage in days from features."""
    s = get_close_series_from_features(ticker)
    if s is None or s.empty:
        return None
    return int((s.index.max() - s.index.min()).days)

# ================================== MACRO ====================================

def load_macro_forecast_rows(limit: int = 200) -> Dict[str, Any]:
    """
    Load macro forecast data.
    Priority: macro_forecast parquet → macro_snapshot_daily features
    """
    # Try macro forecast
    p = _latest_glob("data/macro/forecast/dt=*/macro_forecast.parquet")
    if p and p.exists():
        try:
            df = pd.read_parquet(p).head(limit)
            return {
                "ok": True,
                "path": str(p),
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records")
            }
        except Exception:
            pass
    
    # Fallback: features
    pf = _latest_glob("data/features/table=macro_snapshot_daily/dt=*/final.parquet")
    if pf and pf.exists():
        try:
            df = pd.read_parquet(pf).head(limit)
            return {
                "ok": True,
                "path": str(pf),
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records"),
                "fallback": "features_macro_snapshot_daily"
            }
        except Exception:
            pass
    
    return {"ok": False, "reason": "no_macro"}

# =================================== NEWS ====================================

def load_news_features(limit: int = 100) -> Dict[str, Any]:
    """
    Load aggregated news features.
    Priority: news_features_daily → raw news parquets
    """
    # Try features
    p = _latest_glob("data/features/table=news_features_daily/dt=*/final.parquet")
    if p and p.exists():
        try:
            df = pd.read_parquet(p).head(limit)
            return {
                "ok": True,
                "path": str(p),
                "columns": list(df.columns),
                "rows": df.to_dict(orient="records")
            }
        except Exception:
            pass
    
    # Fallback: raw news
    ps = sorted(Path("data/news").glob("dt=*/news_*.parquet"))
    if ps:
        try:
            dfs = [pd.read_parquet(x).head(50) for x in ps[-4:]]
            df = pd.concat(dfs, ignore_index=True)
            return {
                "ok": True,
                "path": "data/news",
                "columns": list(df.columns),
                "rows": df.head(limit).to_dict(orient="records"),
                "fallback": "raw_news"
            }
        except Exception:
            pass
    
    return {"ok": False, "reason": "no_news"}

# ============================ UTILITY FUNCTIONS ==============================

def get_latest_partition(base: str) -> Optional[str]:
    """Get latest dt=YYYYMMDD partition name."""
    parts = sorted(Path(base).glob("dt=*"))
    if not parts:
        return None
    return parts[-1].name.split("=")[-1]

def check_data_freshness() -> Dict[str, Any]:
    """Check freshness of all data sources."""
    return {
        "prices_features": get_latest_partition("data/features/table=prices_features_daily"),
        "macro_features": get_latest_partition("data/features/table=macro_snapshot_daily"),
        "news_features": get_latest_partition("data/features/table=news_features_daily"),
        "forecasts": get_latest_partition("data/forecast"),
        "macro_forecast": get_latest_partition("data/macro/forecast"),
        "news_raw": get_latest_partition("data/news"),
    }
