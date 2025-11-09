# src/api/main.py
"""
FastAPI backend for React frontend.
Serves all 5 pillars according to VISION.md
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
from dataclasses import asdict
import logging
import math

from fastapi import FastAPI, Query, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import pandas as pd
from starlette.concurrency import run_in_threadpool

DEBUG_MODE = str(os.getenv("FINANCE_COPILOT_DEBUG", os.getenv("COPILOT_DEBUG", "1"))).lower() in {
    "1",
    "true",
    "yes",
    "on",
    "debug",
}

# Ensure project backend paths are on sys.path so `import core.*` works
import sys
from pathlib import Path as _Path
_backend_root = _Path(__file__).resolve().parents[2]
_src_path = str(_backend_root / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))


def _configure_debug_logging():
    """Ensure backend logs everything when DEBUG_MODE is enabled."""
    if getattr(_configure_debug_logging, "_configured", False):
        return
    logging.basicConfig(level=logging.DEBUG)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "api.debug"):
        logging.getLogger(name).setLevel(logging.DEBUG)
    _configure_debug_logging._configured = True  # type: ignore[attr-defined]

logger = logging.getLogger("api.routes")

# ------------------------------ Constants ---------------------------------- #
MACRO_SERIES_META: Dict[str, Dict[str, Optional[str]]] = {
    "CPIAUCSL": {"name": "US CPI (All Items)", "unit": "index", "frequency": "monthly"},
    "UNRATE": {"name": "Unemployment Rate", "unit": "%", "frequency": "monthly"},
    "DGS10": {"name": "10Y Treasury Yield", "unit": "%", "frequency": "daily"},
    "DGS2": {"name": "2Y Treasury Yield", "unit": "%", "frequency": "daily"},
    "FEDFUNDS": {"name": "Federal Funds Rate", "unit": "%", "frequency": "monthly"},
    "MICH": {"name": "Michigan Sentiment", "unit": "index", "frequency": "monthly"},
}
DEFAULT_MACRO_SERIES = list(MACRO_SERIES_META.keys())

DEFAULT_STOCKS_UNIVERSE = [
    t.strip().upper()
    for t in os.getenv("STOCKS_UNIVERSE", "SPY,QQQ,AAPL,NVDA,MSFT,GOOGL,AMZN,TSLA,META,IBM")
    .split(",")
    if t.strip()
]
if not DEFAULT_STOCKS_UNIVERSE:
    DEFAULT_STOCKS_UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT"]

STOCKS_CACHE_TTL_MINUTES = int(os.getenv("STOCKS_CACHE_TTL_MINUTES", "15") or "15")
STOCKS_CACHE_TTL = timedelta(minutes=max(5, STOCKS_CACHE_TTL_MINUTES))
_STOCKS_METRICS_CACHE: Dict[str, Dict[str, Any]] = {}


# Import data access layer
try:
    from core.data_access import (
        get_close_series,
        load_macro_forecast_rows
    )
    from core.market_data import get_price_history, get_fundamentals, get_fred_series
    from core.downsample import lttb
    from core.duck import query_parquet, parquet_glob
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    # Fallback stubs
    def get_close_series(ticker): return None
    def load_macro_forecast_rows(limit=200): return {"ok": False}
    def get_price_history(ticker, **kw): return None
    def get_fundamentals(ticker): return {}
    def get_fred_series(series_id, start=None): return pd.DataFrame(columns=[series_id])
    def lttb(points, threshold=1000): return points
    def query_parquet(sql, params=None): return []
    def parquet_glob(*parts): return str(Path(*parts))

from api.services.news_service import (
    get_news_events as lakehouse_news_events,
    get_sentiment as lakehouse_news_sentiment,
)
from services.intelligence_service import (
    get_market_context_snapshot,
    get_market_intelligence_snapshot,
)


def _parse_csv_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _infer_frequency(index: pd.Index) -> Optional[str]:
    if not isinstance(index, pd.DatetimeIndex) or index.empty:
        return None
    freq = pd.infer_freq(index)
    if not freq:
        return None
    freq = freq.lower()
    if "m" in freq:
        return "monthly"
    if "q" in freq:
        return "quarterly"


def _fallback_intelligence_snapshot(message: str) -> Dict[str, Any]:
    now_iso = datetime.utcnow().isoformat() + "Z"
    return {
        "insights": {
            "summary": message,
            "market_regime": {
                "current": "NORMAL",
                "explanation": "Fallback snapshot (pipeline unavailable).",
            },
            "opportunities": [],
            "risks": [],
        },
        "data_freshness": {
            "forecasts_age": "unknown",
            "macro_age": "unknown",
            "news_age": "unknown",
        },
        "timestamp": now_iso,
        "drivers": [],
        "sources": {
            "forecasts": False,
            "brief": False,
            "news": False,
        },
    }


def _fallback_market_context(message: str) -> Dict[str, Any]:
    return {
        "regime": "NORMAL",
        "confidence": 0.0,
        "key_drivers": [],
        "characteristics": {
            "volatility": "medium",
            "sentiment": "neutral",
            "trend": "sideways",
            "momentum": "weak",
            "risk_level": "medium",
        },
        "recommended_layout": {
            "primary_widgets": ["intelligence", "forecasts", "news"],
            "emphasis": "opportunities",
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "note": message,
    }
    if "w" in freq:
        return "weekly"
    return "daily"


def _format_points(df: pd.DataFrame, column: str, limit: int, start: Optional[pd.Timestamp], end: Optional[pd.Timestamp]) -> List[Dict[str, Any]]:
    if column not in df.columns or df.empty:
        return []
    series = df[column].dropna()
    if start is not None:
        series = series[series.index >= start]
    if end is not None:
        series = series[series.index <= end]
    if limit:
        series = series.tail(limit)
    points = []
    for ts, value in series.items():
        if pd.isna(value):
            points.append({"date": ts.strftime("%Y-%m-%d"), "value": None})
        else:
            points.append({"date": ts.strftime("%Y-%m-%d"), "value": float(value)})
    return points


def _normalize_percent(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if math.isnan(value):
        return None
    return float(round(value, 4))


def _compute_stock_metrics(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper()
    cached = _STOCKS_METRICS_CACHE.get(ticker)
    now = datetime.utcnow()
    if cached and (now - cached["fetched_at"]) < STOCKS_CACHE_TTL:
        return cached["data"]

    lookback_start = (now - timedelta(days=120)).strftime("%Y-%m-%d")
    df_prices = get_price_history(ticker, start=lookback_start, interval="1d")
    last_price = change_1d = momentum_30d = risk = None
    if df_prices is not None and not df_prices.empty and "Close" in df_prices.columns:
        close = df_prices["Close"].dropna()
        if not close.empty:
            last_price = float(close.iloc[-1])
            if len(close) > 1:
                prev_close = float(close.iloc[-2])
                if prev_close:
                    change_1d = ((last_price - prev_close) / prev_close) * 100
            if len(close) > 30:
                base = float(close.iloc[-31])
                if base:
                    momentum_30d = ((last_price - base) / base) * 100
            returns = close.pct_change().dropna()
            if len(returns) >= 20:
                daily_vol = float(returns.rolling(20).std().iloc[-1])
                if not math.isnan(daily_vol):
                    risk = daily_vol * math.sqrt(252) * 100

    fundamentals = get_fundamentals(ticker) or {}
    name = fundamentals.get("name") or ticker
    sector = fundamentals.get("sector")
    industry = fundamentals.get("industry")
    mcap = fundamentals.get("market_cap")
    pe = fundamentals.get("pe")
    div_yield = fundamentals.get("dividend_yield")
    if div_yield is not None and div_yield < 1:
        div_yield = div_yield * 100

    # Quality score (simple heuristic)
    quality = None
    if pe and pe > 0:
        quality = max(0.0, min(100.0, 100 - min(pe, 80)))
    # Composite score
    composite = 50.0
    if momentum_30d is not None:
        composite += max(-25.0, min(25.0, momentum_30d / 2))
    if risk is not None:
        composite += max(-20.0, min(20.0, 20 - risk))
    if div_yield is not None:
        composite += max(-10.0, min(10.0, div_yield / 2))
    score = max(0.0, min(100.0, composite))

    data = {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "industry": industry,
        "price": float(round(last_price, 4)) if last_price is not None else None,
        "change_1d": _normalize_percent(change_1d),
        "momentum_30d": _normalize_percent(momentum_30d),
        "risk": _normalize_percent(risk),
        "score": float(round(score, 2)),
        "quality": float(round(quality, 2)) if quality is not None else None,
        "mcap": float(mcap) if isinstance(mcap, (int, float)) else None,
        "pe": float(pe) if isinstance(pe, (int, float)) else None,
        "div_yield": _normalize_percent(div_yield),
        "fetched_at": now.isoformat(),
    }

    _STOCKS_METRICS_CACHE[ticker] = {"data": data, "fetched_at": now}
    return data

# ================================= APP SETUP =================================

def create_app() -> FastAPI:
    """Create and configure FastAPI app."""
    debug_enabled = DEBUG_MODE
    app = FastAPI(
        title="Finance Copilot API",
        description="Backend API for React frontend - 5 Pillars: Macro, Stocks, News, Copilot, Brief",
        version="0.1.0",
        debug=debug_enabled,
    )

    if debug_enabled:
        _configure_debug_logging()
        debug_logger = logging.getLogger("api.debug")

        @app.middleware("http")
        async def debug_request_logger(request: Request, call_next):
            start = datetime.now()
            response = await call_next(request)
            duration = (datetime.now() - start).total_seconds() * 1000.0
            try:
                debug_logger.debug(
                    "HTTP %s %s -> %s in %.1f ms",
                    request.method,
                    request.url.path,
                    getattr(response, "status_code", "unknown"),
                    duration,
                )
            except Exception:
                pass
            return response

    # CORS middleware (allow React dev server and production origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://0.0.0.0:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Routes
    register_routes(app)

    # Include brief routes
    try:
        from api.routes.brief_routes import router as brief_router
        app.include_router(brief_router)
    except ImportError as e:
        print(f"⚠️  Failed to include brief routes: {e}")

    # Include cache management routes
    try:
        from api.routes.cache_routes import router as cache_router
        app.include_router(cache_router)
    except ImportError as e:
        print(f"⚠️  Failed to include cache routes: {e}")

    # Include portfolios/watchlists routes
    try:
        from api.routes.portfolios import router as portfolios_router
        app.include_router(portfolios_router)
    except ImportError as e:
        print(f"⚠️  Failed to include portfolios routes: {e}")

    # Include analytics routes
    try:
        from api.routes.analytics import router as analytics_router
        app.include_router(analytics_router)
    except ImportError as e:
        print(f"⚠️  Failed to include analytics routes: {e}")

    # =================== STARTUP EVENT HANDLER ===================
    @app.on_event("startup")
    async def startup_event():
        """
        Initialize application data at startup
        Task: FC-STARTUP-INIT-001 (+60 pts)
        Author: CLAUDE-STABILITY-ARCHITECT-IRONMAN-42
        """
        import logging
        logger = logging.getLogger(__name__)
        try:
            logger.setLevel(logging.INFO)
        except Exception:
            pass

        logger.info("="*70)
        logger.info("🚀 Finance Copilot Starting Up...")
        logger.info("="*70)

        # Import necessary functions
        try:
            from storage.io import load_json
            from jobs.forecasts import run_forecasts_job
            from jobs.news_ingest import run_news_ingest
            from jobs.weekly_brief import run_and_persist_weekly_brief
            from jobs.alerts import run_alerts_job
            from scheduler.app import start_scheduler

            logger.info("📦 Checking data availability...")

            # Check and generate forecasts if missing
            if not load_json("forecasts.json"):
                logger.info("⚠️  No forecasts found, generating initial set...")
                try:
                    run_forecasts_job()
                    logger.info("✅ Initial forecasts generated")
                except Exception as e:
                    logger.error(f"❌ Failed to generate forecasts: {e}")
            else:
                logger.info("✅ Forecasts data found")

            # Check and generate news feed if missing
            if not load_json("news_feed.json"):
                logger.info("⚠️  No news feed found, fetching initial data...")
                try:
                    run_news_ingest()
                    logger.info("✅ Initial news feed generated")
                except Exception as e:
                    logger.error(f"❌ Failed to fetch news: {e}")
            else:
                logger.info("✅ News feed data found")

            # Check and generate weekly brief if missing
            if not load_json("brief_weekly.json"):
                logger.info("⚠️  No weekly brief found, generating...")
                try:
                    run_and_persist_weekly_brief()
                    logger.info("✅ Initial weekly brief generated")
                except Exception as e:
                    logger.error(f"❌ Failed to generate weekly brief: {e}")
            else:
                logger.info("✅ Weekly brief data found")

            # Check and generate alerts if missing
            if not load_json("alerts.json"):
                logger.info("⚠️  No alerts found, generating...")
                try:
                    run_alerts_job()
                    logger.info("✅ Initial alerts generated")
                except Exception as e:
                    logger.error(f"❌ Failed to generate alerts: {e}")
            else:
                logger.info("✅ Alerts data found")

            # Start background scheduler
            logger.info("⏰ Starting background scheduler...")
            try:
                start_scheduler()
                logger.info("✅ Scheduler started successfully")
            except Exception as e:
                logger.error(f"❌ Failed to start scheduler: {e}")

            logger.info("="*70)
            logger.info("✅ Finance Copilot Ready!")
            logger.info("="*70)

        except Exception as e:
            logger.error(f"❌ Startup initialization failed: {e}")
            logger.warning("⚠️  Application will continue but some features may not work")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info("🛑 Shutting down Finance Copilot...")

        try:
            from scheduler.app import stop_scheduler
            stop_scheduler()
            logger.info("✅ Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {e}")

        logger.info("👋 Goodbye!")

    return app

# ================================= MODELS ====================================

class ApiResponse(BaseModel):
    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None

class CopilotAskRequest(BaseModel):
    question: str
    context_years: int = 5
    max_sources: int = 10
    scope: Optional[Dict[str, Any]] = None
    tickers: Optional[List[str]] = None


class LLMJudgeRequest(BaseModel):
    """Request payload for the LLM judge endpoint."""
    model: str = "deepseek-ai/DeepSeek-V3-0324-Turbo"
    max_er: float = 0.08
    min_conf: float = 0.6
    tickers: Optional[str] = None

# ================================= HELPERS ===================================

def _ok(data: Any) -> Dict:
    return {"ok": True, "data": data}

def _err(msg: str) -> Dict:
    return {"ok": False, "error": msg}

def _latest_partition(base: str) -> Optional[str]:
    """Get latest dt=YYYYMMDD partition."""
    parts = sorted(Path(base).glob("dt=*"))
    return parts[-1].name.split("=")[-1] if parts else None

DEFAULT_JUDGE_TICKERS = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"]
# ================================= ROUTES ====================================

def register_routes(app: FastAPI):
    """Register all API routes."""

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint with enriched status information."""
        # Use relative import based on the project structure
        # Since this is in src/api, and storage is in backend/storage (outside src), 
        # we need to use a different approach
        try:
            # First try the direct import (relative to project root)
            backend_root = Path(__file__).resolve().parents[2]  # Go from src/api/main.py to backend/
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))
            
            from storage.base import load_json
        except ImportError:
            try:
                from storage.io import load_json  # Alternative storage module
            except ImportError:
                # Ultimate fallback - create a mock load_json function
                def load_json(key):
                    return None
        
        # Get last updates by domain from stored files
        last_updates = {}
        
        # Check forecasts last update
        forecasts_data = load_json("forecasts.json")
        if forecasts_data:
            last_updates["forecasts"] = forecasts_data.get("last_update")
        
        # Check news feed last update
        news_data = load_json("news_feed.json")
        if news_data:
            last_updates["news"] = news_data.get("last_update")
        
        # Check weekly brief last update
        brief_data = load_json("brief_weekly.json")
        if brief_data:
            last_updates["brief_weekly"] = brief_data.get("last_update")
        
        # Check backtests last update
        try:
            from backend.storage.base import load_json
            backtests_data = load_json("backtests.json")
            if backtests_data:
                last_updates["backtests"] = backtests_data.get("last_update")
        except ImportError:
            # If storage module isn't available, skip backtests update
            pass
        
        return _ok({
            "status": "up",
            "backend_up": True,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.1.0",
            "last_updates": last_updates,
            "data_paths": {
                "forecasts": "data/forecasts.json",
                "news": "data/news_feed.json", 
                "brief_weekly": "data/brief_weekly.json",
                "backtests": "data/backtests.json"
            }
        })

    @app.get("/api/freshness")
    async def data_freshness():
        """Check freshness of all data sources."""
        # Placeholder implementation - not yet available in core.data_access
        return _ok({
            "macro_freshness_minutes": 60,
            "news_freshness_minutes": 15,
            "stocks_freshness_minutes": 5,
            "last_update": datetime.utcnow().isoformat()
        })

    # ========================= PILLAR 1: MACRO ===========================

    @app.get("/api/macro/series")
    async def macro_series(
        series_ids: Optional[str] = Query(None, description="Comma-separated series IDs"),
        ids: Optional[str] = Query(None, description="Alias for series_ids"),
        start: Optional[str] = Query(None, description="ISO date (e.g. 2020-01-01)"),
        end: Optional[str] = Query(None, description="ISO date"),
        limit: int = Query(500, ge=10, le=5000)
    ):
        """Get macro time series data - reads from pre-computed data."""
        try:
            from storage.io import load_json
            
            # Load from pre-computed macro series
            macro_data = load_json("macro_series")
            
            if macro_data and "series" in macro_data:
                requested = _parse_csv_list(series_ids) or _parse_csv_list(ids) or DEFAULT_MACRO_SERIES
                series_dict = macro_data.get("series", {})
                
                # Filter by requested series
                payload: List[Dict[str, Any]] = []
                for series_id in requested:
                    if series_id in series_dict:
                        series_info = series_dict[series_id]
                        observations = series_info.get("observations", [])
                        
                        # Filter by date range if provided
                        if start or end:
                            start_ts = pd.to_datetime(start).tz_localize(None) if start else None
                            end_ts = pd.to_datetime(end).tz_localize(None) if end else None
                            filtered_obs = []
                            for obs in observations:
                                obs_date = pd.to_datetime(obs.get("date"))
                                if start_ts and obs_date < start_ts:
                                    continue
                                if end_ts and obs_date > end_ts:
                                    continue
                                filtered_obs.append(obs)
                            observations = filtered_obs[:limit]
                        else:
                            observations = observations[:limit]
                        
                        # Convert to points format
                        points = [{"date": obs.get("date"), "value": obs.get("value")} for obs in observations]
                        
                        payload.append({
                            "id": series_id,
                            "name": series_info.get("title", series_id),
                            "unit": series_info.get("units", ""),
                            "frequency": series_info.get("frequency", "unknown"),
                            "points": points,
                        })
                
                if payload:
                    return _ok({
                        "series": payload,
                        "updated_at": macro_data.get("freshness", macro_data.get("generated_at", datetime.utcnow().isoformat())),
                    })
            
            # Fallback: compute on the fly (legacy behavior)
            requested = _parse_csv_list(series_ids) or _parse_csv_list(ids) or DEFAULT_MACRO_SERIES
            start_ts = pd.to_datetime(start).tz_localize(None) if start else None
            end_ts = pd.to_datetime(end).tz_localize(None) if end else None

            payload: List[Dict[str, Any]] = []
            for series_id in requested:
                try:
                    df = get_fred_series(series_id, start=start)
                except Exception:
                    df = pd.DataFrame(columns=[series_id])
                if df is None or df.empty:
                    continue
                column = df.columns[0]
                points = _format_points(df, column, limit=limit, start=start_ts, end=end_ts)
                if not points:
                    continue
                meta = MACRO_SERIES_META.get(series_id, {})
                payload.append({
                    "id": series_id,
                    "name": meta.get("name") or series_id,
                    "unit": meta.get("unit"),
                    "frequency": meta.get("frequency") or _infer_frequency(df.index),
                    "points": points,
                })

            if not payload:
                return _ok({
                    "series": [],
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                })

            return _ok({
                "series": payload,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            return _ok({
                "series": [],
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })

    @app.get("/api/macro/snapshot")
    async def macro_snapshot():
        """Get current macro snapshot (latest values) - reads from pre-computed data."""
        try:
            from storage.io import load_json
            
            # Load from pre-computed macro snapshot
            macro_snapshot_data = load_json("macro_snapshot")
            
            if macro_snapshot_data and "snapshot" in macro_snapshot_data:
                snapshot = macro_snapshot_data["snapshot"]
                return _ok({
                    **snapshot,
                    "freshness": macro_snapshot_data.get("freshness", macro_snapshot_data.get("generated_at")),
                    "last_update": macro_snapshot_data.get("last_update", macro_snapshot_data.get("generated_at")),
                })
            
            # Fallback: try legacy format
            result = load_macro_forecast_rows(limit=10)
            if result.get("rows"):
                rows = result.get("rows", [])
                snapshot = {}
                for row in rows:
                    for key, value in row.items():
                        if value is not None:
                            snapshot[key] = value
                return _ok(snapshot)
            
            # Empty fallback
            return _ok({
                "freshness": datetime.utcnow().isoformat(),
                "last_update": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            return _ok({
                "error": str(e),
                "freshness": datetime.utcnow().isoformat(),
            })

    @app.get("/api/macro/indicators")
    async def macro_indicators():
        """Get macro indicators with trend analysis."""
        # TODO: Implement trend analysis (YoY, MoM, etc.)
        return _ok({
            "cpi_yoy": None,
            "yield_curve_10y_2y": None,
            "recession_probability": None,
            "vix": None
        })

    # ========================= PILLAR 2: STOCKS ==========================

    @app.get("/api/stocks/prices")
    async def stock_prices(
        ticker: Optional[str] = Query(None, description="Stock ticker symbol (single ticker)"),
        tickers: Optional[List[str]] = Query(None, description="Stock ticker symbols (multiple tickers)"),
        timeframe: str = Query("1y", description="Time range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
        interval: str = Query("1d", description="Interval: 1d, 1wk, 1mo"),
        downsample: int = Query(1000, ge=100, le=10000, description="Max points (LTTB)")
    ):
        """Get stock prices - reads from pre-computed data."""
        try:
            from storage.io import load_json
            
            # Determine which tickers to process
            tickers_to_process = []
            if ticker:
                tickers_to_process = [ticker.upper()]
            elif tickers and len(tickers) > 0:
                tickers_to_process = [t.upper() for t in tickers]
            else:
                return _ok({
                    "tickers": {},
                    "range": timeframe,
                    "interval": interval,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": "Either 'ticker' or 'tickers' parameter must be provided"
                })
            
            # Load from pre-computed stocks prices
            prices_data = load_json("stocks/prices")
            
            if prices_data and "tickers" in prices_data:
                cached_tickers = prices_data.get("tickers", {})
                results = {}
                
                for ticker_symbol in tickers_to_process:
                    if ticker_symbol in cached_tickers:
                        ticker_data = cached_tickers[ticker_symbol]
                        points = ticker_data.get("points", [])
                        
                        # Downsample if needed
                        if len(points) > downsample:
                            try:
                                from core.downsample import lttb
                                points = lttb(points, threshold=downsample)
                            except ImportError:
                                # Si lttb n'est pas disponible, prendre un échantillon
                                step = len(points) // downsample
                                points = points[::max(1, step)]
                        
                        results[ticker_symbol] = {
                            "range": ticker_data.get("range", timeframe),
                            "interval": ticker_data.get("interval", interval),
                            "points": points,
                            "count": len(points),
                            "start_date": ticker_data.get("start_date"),
                            "timestamp": prices_data.get("freshness", datetime.utcnow().isoformat())
                        }
                    else:
                        results[ticker_symbol] = {"error": f"No cached data for {ticker_symbol}"}
                
                return _ok({
                    "tickers": results,
                    "range": timeframe,
                    "interval": interval,
                    "timestamp": prices_data.get("freshness", datetime.utcnow().isoformat())
                })
            
            # Fallback: compute on the fly (legacy behavior)
            from core.market_data import get_price_history
            
            timeframe_map = {
                "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
                "1y": 365, "2y": 730, "5y": 1825
            }
            days_back = timeframe_map.get(timeframe, 365)
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            
            results = {}
            for ticker_symbol in tickers_to_process:
                df = get_price_history(ticker_symbol, start=start_date, interval=interval)
                if df is None or df.empty:
                    results[ticker_symbol] = {"error": f"No data for {ticker_symbol}"}
                    continue
                
                series = df['Close'] if 'Close' in df.columns else df.iloc[:, 0]
                points = [(int(ts.timestamp()), float(val))
                         for ts, val in series.items()
                         if not pd.isna(val)]
                
                if len(points) > downsample:
                    try:
                        from core.downsample import lttb
                        points = lttb(points, threshold=downsample)
                    except ImportError:
                        step = len(points) // downsample
                        points = points[::max(1, step)]
                
                results[ticker_symbol] = {
                    "range": timeframe,
                    "interval": interval,
                    "points": points,
                    "count": len(points),
                    "start_date": start_date,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            return _ok({
                "tickers": results,
                "range": timeframe,
                "interval": interval,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            return _ok({
                "tickers": {},
                "range": timeframe,
                "interval": interval,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            })

    @app.get("/api/stocks/universe")
    async def stock_universe():
        """Get list of tracked tickers."""
        return _ok({
            "tickers": DEFAULT_STOCKS_UNIVERSE,
            "count": len(DEFAULT_STOCKS_UNIVERSE),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        })

    @app.get("/api/stocks/meta")
    async def stocks_meta(tickers: Optional[str] = Query(None, description="Comma-separated tickers")):
        """Get stocks metadata - reads from pre-computed data."""
        try:
            from storage.io import load_json
            
            # Load from pre-computed stocks metrics
            metrics_data = load_json("stocks/metrics")
            
            if metrics_data and "metrics" in metrics_data:
                requested = _parse_csv_list(tickers) or DEFAULT_STOCKS_UNIVERSE
                metrics = metrics_data.get("metrics", {})
                
                # Filter by requested tickers
                items = []
                for ticker in requested:
                    if ticker.upper() in metrics:
                        metric = metrics[ticker.upper()]
                        items.append({
                            "ticker": metric.get("ticker", ticker.upper()),
                            "name": metric.get("name"),  # À enrichir si disponible
                            "sector": metric.get("sector"),  # À enrichir si disponible
                            "industry": metric.get("industry"),  # À enrichir si disponible
                            "weight": None,
                        })
                
                return _ok({
                    "items": items,
                    "count": len(items),
                    "updated_at": metrics_data.get("freshness", datetime.utcnow().isoformat()),
                })
            
            # Fallback: compute on the fly (legacy behavior)
            requested = _parse_csv_list(tickers) or DEFAULT_STOCKS_UNIVERSE
            rows = [_compute_stock_metrics(symbol) for symbol in requested]
            items = [{
                "ticker": row["ticker"],
                "name": row.get("name"),
                "sector": row.get("sector"),
                "industry": row.get("industry"),
                "weight": None,
            } for row in rows]
            return _ok({
                "items": items,
                "count": len(items),
                "updated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            return _ok({
                "items": [],
                "count": 0,
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })

    @app.get("/api/stocks/screener")
    async def stocks_screener(
        universe: Optional[str] = Query(None, description="Comma-separated universe tickers"),
        sectors: Optional[str] = Query(None, description="Comma-separated sectors"),
        q: Optional[str] = Query(None, description="Text search"),
        min_mcap: Optional[float] = Query(None),
        max_mcap: Optional[float] = Query(None),
        min_pe: Optional[float] = Query(None),
        max_pe: Optional[float] = Query(None),
        sort: str = Query("score"),
        order: str = Query("desc"),
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=200),
    ):
        """Get stocks screener - reads from pre-computed data."""
        try:
            from storage.io import load_json
            
            # Load from pre-computed stocks metrics
            metrics_data = load_json("stocks/metrics")
            
            if metrics_data and "metrics" in metrics_data:
                tickers = _parse_csv_list(universe) or DEFAULT_STOCKS_UNIVERSE
                sector_filters = {s.lower() for s in _parse_csv_list(sectors)}
                metrics = metrics_data.get("metrics", {})
                
                # Convert metrics to rows format
                rows = []
                for ticker in tickers:
                    if ticker.upper() in metrics:
                        metric = metrics[ticker.upper()]
                        rows.append({
                            "ticker": metric.get("ticker", ticker.upper()),
                            "name": metric.get("name"),  # À enrichir
                            "sector": metric.get("sector"),  # À enrichir
                            "price": metric.get("price"),
                            "change_1d": metric.get("change_1d"),
                            "momentum_30d": metric.get("momentum_30d"),
                            "score": metric.get("score"),
                            "risk": metric.get("risk"),
                            "quality": metric.get("quality"),
                            "mcap": metric.get("mcap"),  # À enrichir
                            "pe": metric.get("pe"),  # À enrichir
                            "div_yield": metric.get("div_yield"),  # À enrichir
                        })
            else:
                # Fallback: compute on the fly (legacy behavior)
                tickers = _parse_csv_list(universe) or DEFAULT_STOCKS_UNIVERSE
                sector_filters = {s.lower() for s in _parse_csv_list(sectors)}
                rows = [_compute_stock_metrics(symbol) for symbol in tickers]

            def _match_sector(row):
                if not sector_filters:
                    return True
                sector = (row.get("sector") or "").lower()
                return sector in sector_filters

            filtered = []
            query_lower = q.lower() if q else None
            for row in rows:
                if query_lower:
                    if query_lower not in row["ticker"].lower() and query_lower not in (row.get("name") or "").lower():
                        continue
                if not _match_sector(row):
                    continue
                mcap = row.get("mcap")
                if min_mcap is not None and (mcap is None or mcap < min_mcap):
                    continue
                if max_mcap is not None and (mcap is None or mcap > max_mcap):
                    continue
                pe_val = row.get("pe")
                if min_pe is not None and (pe_val is None or pe_val < min_pe):
                    continue
                if max_pe is not None and (pe_val is None or pe_val > max_pe):
                    continue
                filtered.append(row)

            sort_field = sort if sort in {"score", "risk", "momentum_30d", "change_1d", "mcap", "pe", "div_yield"} else "score"
            reverse = (order or "desc").lower() != "asc"

            def sort_key(item: Dict[str, Any]):
                value = item.get(sort_field)
                return (value is None, value)

            filtered.sort(key=sort_key, reverse=reverse)

            total = len(filtered)
            start = (page - 1) * page_size
            sliced = filtered[start:start + page_size]
            # ensure fields subset
            fields = ["ticker","name","sector","price","change_1d","momentum_30d","score","risk","quality","mcap","pe","div_yield"]
            items = [{field: row.get(field) for field in fields} for row in sliced]
            
            # Get freshness from metrics_data if available
            updated_at = metrics_data.get("freshness", datetime.utcnow().isoformat()) if metrics_data else datetime.utcnow().isoformat()
            
            return _ok({
                "updated_at": updated_at,
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items,
            })
        except Exception as e:
            return _ok({
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "total": 0,
                "page": page,
                "page_size": page_size,
                "items": [],
                "error": str(e),
            })

    @app.get("/api/stocks/{ticker}")
    async def stock_detail(ticker: str):
        """Get detailed ticker sheet (prix + indicators + news + fundamentals)."""
        try:
            from core.market_data import get_price_history, get_fundamentals
            from analytics.phase2_technical import compute_indicators
            
            # Get price history
            series = get_close_series(ticker)
            if series is None or series.empty:
                # Try fallback approach with get_price_history
                df_prices = get_price_history(ticker, start=None, interval="1d")
                if df_prices is None or df_prices.empty:
                    raise HTTPException(status_code=404, detail=f"No price data for {ticker}")
            else:
                # Convert series to DataFrame format for indicators
                df_prices = pd.DataFrame({'Close': series})
                df_prices.index.name = 'Date'  # Make sure index has a name
            
            # Get fundamentals if available
            fundamentals = {}
            try:
                fundamentals = get_fundamentals(ticker)
            except Exception:
                # If fundamentals not available, use placeholder
                fundamentals = {
                    "sector": "N/A",
                    "market_cap": "N/A",
                    "pe_ratio": "N/A",
                    "dividend_yield": "N/A",
                    "beta": "N/A"
                }
            
            # Calculate technical indicators
            try:
                df_with_indicators = compute_indicators(df_prices)
                last_row = df_with_indicators.iloc[-1] if len(df_with_indicators) > 0 else {}
                
                technical_indicators = {
                    "rsi": float(last_row.get("RSI", 0)) if pd.notna(last_row.get("RSI")) else None,
                    "sma20": float(last_row.get("SMA_20", 0)) if pd.notna(last_row.get("SMA_20")) else None,
                    "sma50": float(last_row.get("SMA_50", 0)) if pd.notna(last_row.get("SMA_50")) else None,
                    "sma200": float(last_row.get("SMA_200", 0)) if pd.notna(last_row.get("SMA_200")) else None,
                    "macd": float(last_row.get("MACD", 0)) if pd.notna(last_row.get("MACD")) else None,
                    "macd_signal": float(last_row.get("MACD_Signal", 0)) if pd.notna(last_row.get("MACD_Signal")) else None,
                    "bollinger_upper": float(last_row.get("BB_upper", 0)) if pd.notna(last_row.get("BB_upper")) else None,
                    "bollinger_lower": float(last_row.get("BB_lower", 0)) if pd.notna(last_row.get("BB_lower")) else None,
                    "volume_sma": float(last_row.get("Volume_SMA", 0)) if pd.notna(last_row.get("Volume_SMA")) else None,
                }
            except Exception:
                # If indicators computation fails, return basic values
                last_price = float(df_prices['Close'].iloc[-1]) if 'Close' in df_prices.columns else None
                technical_indicators = {
                    "rsi": None,
                    "sma20": None,
                    "sma50": None,
                    "sma200": None,
                    "macd": None,
                    "macd_signal": None,
                    "bollinger_upper": None,
                    "bollinger_lower": None,
                    "volume_sma": None,
                }
            
            # Get recent news count for this ticker
            try:
                from api.services.news_service import get_news_feed
                news_data = get_news_feed(tickers=[ticker], since="7d", score_min=0.0, region="all", limit=50)
                news_count = news_data.count if hasattr(news_data, 'count') else 0
            except Exception:
                # If news service is not available, use a fallback
                news_count = 0
            
            # Calculate additional metrics
            last_price = float(df_prices['Close'].iloc[-1]) if 'Close' in df_prices.columns else None
            price_change_pct = None
            if len(df_prices) > 1 and 'Close' in df_prices.columns:
                prev_close = float(df_prices['Close'].iloc[-2])
                if prev_close != 0:
                    price_change_pct = ((last_price - prev_close) / prev_close) * 100
            
            # Create comprehensive ticker sheet (Fiches Ticker)
            ticker_sheet = {
                "ticker": ticker.upper(),
                "current_price": last_price,
                "price_change_pct": price_change_pct,
                "date": df_prices.index[-1].isoformat() if not df_prices.empty else None,
                "fundamentals": fundamentals,
                "technical_indicators": technical_indicators,
                "news_count": news_count,
                "trading_levels": {
                    "resistance": technical_indicators.get("sma50"),  # Example: 50-day SMA as resistance
                    "support": technical_indicators.get("sma200"),    # Example: 200-day SMA as support
                },
                "momentum": {
                    "rsi_level": "neutral" if technical_indicators.get("rsi") and 30 <= technical_indicators["rsi"] <= 70 else 
                                "overbought" if technical_indicators.get("rsi") and technical_indicators["rsi"] > 70 else 
                                "oversold" if technical_indicators.get("rsi") and technical_indicators["rsi"] < 30 else "neutral",
                    "trend": "bullish" if technical_indicators.get("sma20") and last_price and last_price > technical_indicators["sma20"] else "bearish"
                },
                "composite_score": None,  # Will be calculated if scoring is available
                "analysis": {
                    "sentiment": "neutral",  # This would come from news sentiment analysis
                    "outlook": "neutral",  # This could be derived from technicals and fundamentals
                    "key_levels": {
                        "pivot_point": None,  # TODO: Calculate pivot points
                        "stop_loss": None,
                        "target": None
                    }
                },
                "risk_metrics": {
                    "volatility": None,  # TODO: Calculate from price data
                    "beta": fundamentals.get("beta", "N/A"),
                    "correlation_with_market": None
                },
                "timeframes": {  # Additional data for different time horizons
                    "daily": {
                        "high": float(df_prices['Close'].max()) if 'Close' in df_prices.columns else None,
                        "low": float(df_prices['Close'].min()) if 'Close' in df_prices.columns else None,
                        "volume_avg": None  # Would need volume data
                    },
                    "weekly": {},  # Could be calculated from weekly aggregation
                    "monthly": {}  # Could be calculated from monthly aggregation
                }
            }
            
            # Add composite scoring if available
            try:
                from research.scoring import calculate_composite_score
                composite_score = calculate_composite_score(ticker.upper())
                ticker_sheet["composite_score"] = composite_score.get("composite_score")
                ticker_sheet["score_breakdown"] = {
                    "macro": composite_score.get("macro_score"),
                    "technical": composite_score.get("technical_score"), 
                    "news": composite_score.get("news_score")
                }
            except Exception:
                ticker_sheet["composite_score"] = None
                ticker_sheet["score_breakdown"] = None
            
            return _ok(ticker_sheet)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error retrieving data for {ticker}: {str(e)}")

    @app.get("/api/stocks/{ticker}/sheet")
    async def ticker_sheet(ticker: str):
        """Get detailed ticker sheet (Fiches Ticker) with comprehensive analysis."""
        try:
            from core.market_data import get_price_history, get_fundamentals
            from analytics.phase2_technical import compute_indicators
            from research.scoring import calculate_composite_score
            from research.alerts import alerts_for_ticker
            
            # Get price history
            series = get_close_series(ticker)
            if series is None or series.empty:
                # Try fallback approach with get_price_history
                df_prices = get_price_history(ticker, start=None, interval="1d")
                if df_prices is None or df_prices.empty:
                    raise HTTPException(status_code=404, detail=f"No price data for {ticker}")
            else:
                # Convert series to DataFrame format for indicators
                df_prices = pd.DataFrame({'Close': series})
                df_prices.index.name = 'Date'  # Make sure index has a name
            
            # Get fundamentals if available
            fundamentals = {}
            try:
                fundamentals = get_fundamentals(ticker)
            except Exception:
                # If fundamentals not available, use placeholder
                fundamentals = {
                    "sector": "N/A",
                    "industry": "N/A",
                    "market_cap": "N/A",
                    "pe_ratio": "N/A",
                    "pb_ratio": "N/A",
                    "dividend_yield": "N/A",
                    "beta": "N/A",
                    "eps": "N/A",
                    "revenue": "N/A",
                    "roe": "N/A"
                }
            
            # Calculate technical indicators
            try:
                df_with_indicators = compute_indicators(df_prices)
                last_row = df_with_indicators.iloc[-1] if len(df_with_indicators) > 0 else {}
                
                technical_indicators = {
                    "rsi": float(last_row.get("RSI", 0)) if pd.notna(last_row.get("RSI")) else None,
                    "sma20": float(last_row.get("SMA_20", 0)) if pd.notna(last_row.get("SMA_20")) else None,
                    "sma50": float(last_row.get("SMA_50", 0)) if pd.notna(last_row.get("SMA_50")) else None,
                    "sma200": float(last_row.get("SMA_200", 0)) if pd.notna(last_row.get("SMA_200")) else None,
                    "macd": float(last_row.get("MACD", 0)) if pd.notna(last_row.get("MACD")) else None,
                    "macd_signal": float(last_row.get("MACD_Signal", 0)) if pd.notna(last_row.get("MACD_Signal")) else None,
                    "bollinger_upper": float(last_row.get("BB_upper", 0)) if pd.notna(last_row.get("BB_upper")) else None,
                    "bollinger_lower": float(last_row.get("BB_lower", 0)) if pd.notna(last_row.get("BB_lower")) else None,
                    "volume_sma": float(last_row.get("Volume_SMA", 0)) if pd.notna(last_row.get("Volume_SMA")) else None,
                }
            except Exception:
                # If indicators computation fails, return basic values
                last_price = float(df_prices['Close'].iloc[-1]) if 'Close' in df_prices.columns else None
                technical_indicators = {
                    "rsi": None,
                    "sma20": None,
                    "sma50": None,
                    "sma200": None,
                    "macd": None,
                    "macd_signal": None,
                    "bollinger_upper": None,
                    "bollinger_lower": None,
                    "volume_sma": None,
                }
            
            # Get recent news count and sentiment for this ticker
            news_count = 0
            news_sentiment = 0.5  # Default neutral
            try:
                from api.services.news_service import get_news_feed
                news_data = get_news_feed(tickers=[ticker], since="7d", score_min=0.0, region="all", limit=50)
                news_count = news_data.count if hasattr(news_data, 'count') else 0
                # Calculate sentiment from news data if available
            except Exception:
                # If news service is not available, use a fallback
                news_count = 0
                
            # Calculate additional metrics
            last_price = float(df_prices['Close'].iloc[-1]) if 'Close' in df_prices.columns else None
            price_change_pct = None
            if len(df_prices) > 1 and 'Close' in df_prices.columns:
                prev_close = float(df_prices['Close'].iloc[-2])
                if prev_close != 0:
                    price_change_pct = ((last_price - prev_close) / prev_close) * 100
            
            # Calculate volatility (simple 20-day standard deviation of returns)
            volatility = None
            if len(df_prices) > 20 and 'Close' in df_prices.columns:
                returns = df_prices['Close'].pct_change().dropna().tail(20)
                if len(returns) > 1:
                    volatility = float(returns.std() * (252 ** 0.5)) * 100  # Annualized volatility
            
            # Calculate composite score
            composite_score = None
            score_breakdown = None
            try:
                comp_score = calculate_composite_score(ticker.upper())
                composite_score = comp_score.get("composite_score")
                score_breakdown = {
                    "macro": comp_score.get("macro_score"),
                    "technical": comp_score.get("technical_score"), 
                    "news": comp_score.get("news_score")
                }
            except Exception:
                pass  # Use None values if scoring fails
            
            # Get alerts for this ticker
            alerts = []
            try:
                alerts = alerts_for_ticker(df_prices, pd.DataFrame(technical_indicators, index=[0]), news_sentiment, ticker.upper())
            except Exception:
                alerts = []
            
            # Create comprehensive ticker sheet (Fiches Ticker)
            ticker_sheet = {
                "ticker": ticker.upper(),
                "company_name": ticker.upper(),  # Would come from fundamentals
                "current_price": last_price,
                "price_change": price_change_pct,
                "date": df_prices.index[-1].isoformat() if not df_prices.empty else None,
                "fundamentals": fundamentals,
                "technical_indicators": technical_indicators,
                "news_count": news_count,
                "news_sentiment": news_sentiment,
                "trading_levels": {
                    "resistance_s1": technical_indicators.get("sma50"),
                    "resistance_s2": technical_indicators.get("sma200"),
                    "support_r1": technical_indicators.get("sma20"),
                    "support_r2": None  # Could calculate more levels
                },
                "momentum": {
                    "rsi_level": "neutral" if technical_indicators.get("rsi") and 30 <= technical_indicators["rsi"] <= 70 else 
                                "overbought" if technical_indicators.get("rsi") and technical_indicators["rsi"] > 70 else 
                                "oversold" if technical_indicators.get("rsi") and technical_indicators["rsi"] < 30 else "neutral",
                    "trend": "bullish" if technical_indicators.get("sma20") and last_price and last_price > technical_indicators["sma20"] else "bearish"
                },
                "risk_metrics": {
                    "volatility": volatility,
                    "beta": fundamentals.get("beta"),
                    "max_drawdown": None  # Would need to calculate from historical data
                },
                "composite_score": composite_score,
                "score_breakdown": score_breakdown,
                "alerts": alerts,
                "analysis": {
                    "sentiment": "neutral",
                    "outlook": "neutral", 
                    "recommendation": "hold",  # Would be calculated based on all factors
                    "target_price": None,  # Would come from analysis
                    "stop_loss": None  # Would come from analysis
                },
                "timeframe_analysis": {
                    "short_term": "neutral",  # Based on technicals
                    "medium_term": "neutral",  # Based on fundamentals + technicals
                    "long_term": "neutral"   # Based on fundamentals + macro
                }
            }
            
            return _ok(ticker_sheet)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error retrieving ticker sheet for {ticker}: {str(e)}")

    # ========================= PILLAR 3: NEWS ============================

    @app.get("/api/news/feed")
    async def news_feed(
        tickers: Optional[List[str]] = Query(None, description="Optional tickers filter"),
        since: str = Query("7d", description="1h, 6h, 1d, 3d, 7d, 14d, 30d, 90d"),
        region: str = Query("all", description="Region filter (unused in v1)"),
        score_min: float = Query(0.0, ge=0.0, le=1.0, description="Minimum composite score (unused in v1)"),
        limit: int = Query(50, ge=1, le=400, description="Max 400 articles to keep payload reasonable")
    ):
        """Get news feed - serves real data from news_feed.json"""
        try:
            from storage.io import load_json

            # Load news data
            news_data = load_json("news_feed")

            if not news_data:
                # Return empty but valid structure
                updated_at_fallback = datetime.utcnow().isoformat()
                return _ok({
                    "articles": [],
                    "count": 0,
                    "filters": {
                        "tickers": tickers,
                        "since": since,
                        "limit": limit
                    },
                    "freshness": updated_at_fallback,
                    "updated_at": updated_at_fallback,  # Ajout pour compatibilité frontend
                    "source": ["file_not_found"],
                    "last_update": updated_at_fallback
                })

            # Extract articles from loaded data
            articles = news_data.get("articles", [])

            # Apply filters
            filtered_articles = articles

            # Filter by tickers if specified
            if tickers and filtered_articles:
                # Prefer explicit article tickers/symbols when available, fallback to text match
                desired = {t.upper() for t in tickers}
                def _matches(a: Dict[str, Any]) -> bool:
                    arts_tickers = {str(x).upper() for x in (a.get("tickers") or [])}
                    arts_symbols = {str(x).upper() for x in (a.get("symbols") or [])} if isinstance(a.get("symbols"), list) else set()
                    if arts_tickers & desired or arts_symbols & desired:
                        return True
                    text = (a.get("title", "") + " " + a.get("summary", a.get("description", ""))).upper()
                    return any(t in text for t in desired)

                filtered_articles = [a for a in filtered_articles if _matches(a)]

                # Never-empty guarantee: if no match, show latest with a note
                if not filtered_articles:
                    filtered_articles = articles[:limit]

            # Apply limit safely (frontend can request up to 400)
            filtered_articles = filtered_articles[: min(limit, 400)]

            last_update = news_data.get("collected_at") or news_data.get("freshness") or news_data.get("last_update") or datetime.utcnow().isoformat()
            return _ok({
                "articles": filtered_articles,
                "count": len(filtered_articles),
                "filters": {
                    "tickers": tickers,
                    "since": since,
                    "limit": limit
                },
                "freshness": last_update,
                "updated_at": last_update,  # Ajout pour compatibilité frontend
                "source": news_data.get("sources_used", ["news_feed.json"]),
                "last_update": last_update
            })

        except Exception as e:
            # Fallback: return empty structure
            updated_at_fallback = datetime.utcnow().isoformat()
            return _ok({
                "articles": [],
                "count": 0,
                "error": str(e),
                "filters": {
                    "tickers": tickers,
                    "since": since,
                    "limit": limit
                },
                "freshness": updated_at_fallback,
                "updated_at": updated_at_fallback,  # Ajout pour compatibilité frontend
                "source": ["error_fallback"],
                "last_update": updated_at_fallback
            })

    @app.get("/api/news/sentiment")
    async def news_sentiment(limit: int = Query(100, ge=1, le=500)):
        """Get aggregated sentiment by ticker (v1 minimal)."""
        result = await lakehouse_news_sentiment(limit=limit)
        if isinstance(result, dict):
            return _ok(result)
        return _ok({"sentiment": [], "count": 0})

    @app.get("/api/news/events")
    async def news_events(
        tickers: Optional[List[str]] = Query(None, description="Filter by tickers"),
        event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
        start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
        end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
        limit: int = Query(200, ge=1, le=1000)
    ):
        """Fetch structured events extracted from news articles (placeholder)."""
        result = await lakehouse_news_events(
            tickers=tickers,
            event_types=event_types,
            start=start,
            end=end,
            limit=limit,
        )
        if isinstance(result, dict):
            return _ok(result)
        return _ok({"events": [], "count": 0})

    @app.get("/api/news/features/daily")
    async def news_features_daily(
        ticker: Optional[str] = Query(None, description="Ticker filter"),
        start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
        end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
        limit: int = Query(365, ge=1, le=1095)
    ):
        """Return daily aggregated news features from gold layer v2."""
        sql = """
            SELECT *
            FROM read_parquet('data/news/gold/features_daily_v2/dt=*/features.parquet')
            WHERE (? IS NULL OR ticker = ?)
              AND (? IS NULL OR date >= ?::DATE)
              AND (? IS NULL OR date <= ?::DATE)
            ORDER BY date DESC, ticker
            LIMIT ?
        """
        params = [ticker, ticker, start, start, end, end, limit]
        try:
            rows = query_parquet(sql, params)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  news features query failed: {exc}")
            rows = []

        return _ok({"rows": rows, "count": len(rows)})

    # ======================== PILLAR 4: LLM COPILOT ======================

    @app.post("/api/copilot/ask")
    async def copilot_ask(req: CopilotAskRequest):
        """Ask LLM with RAG (5 years context). Uses LLM for intelligent responses with citations."""
        try:
            from research.rag_store import RAGStore
            from research.llm_client import ask_llm
            
            rag_store = RAGStore()
            
            # Prepare scope for RAG search
            scope = req.scope or {}
            if req.tickers:
                scope["tickers"] = req.tickers
            
            # Search in RAG store
            context_chunks = rag_store.search(scope, top_k=req.max_sources)
            
            if not context_chunks:
                return _ok({
                    "answer": f"Je n'ai pas trouvé d'informations pertinentes pour répondre à votre question: '{req.question}'. Veuillez vérifier les paramètres de recherche ou essayer une question différente.",
                    "sources": [],
                    "confidence": 0.3,
                    "warning": "Aucune source trouvée dans la mémoire",
                    "sources_count": 0,
                    "quality_status": "insufficient_sources"
                })
            
            # Check if we have at least 2 sources (requirement from vision)
            has_min_sources = len(context_chunks) >= 2
            
            # Use LLM to generate response with context
            llm_response = ask_llm(
                question=req.question,
                context_chunks=context_chunks,
                max_tokens=1000
            )
            
            # Extract sources from context_chunks for compatibility
            sources = []
            for chunk in context_chunks:
                sources.append({
                    "type": chunk["meta"]["type"],
                    "url": chunk["meta"].get("url", ""),
                    "date": chunk["meta"].get("date", ""),
                    "ticker": chunk["meta"].get("ticker", ""),
                    "excerpt": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                    "id": chunk.get("id", "")  # Include ID for tracking
                })
            
            return _ok({
                "answer": llm_response["answer"],
                "sources": sources,
                "citations": llm_response.get("citations", []),
                "model": llm_response.get("model", "unknown"),
                "confidence": 0.8 if has_min_sources else 0.4,  # High confidence if we have required sources
                "generated_at": datetime.utcnow().isoformat(),
                "sources_count": len(sources),
                "quality_status": "sufficient_sources" if has_min_sources else "insufficient_sources",
                "requirements_met": {
                    "min_sources_2": has_min_sources,
                    "quality_threshold": llm_response.get("model") != "unconfigured"  # Check if LLM was actually used
                }
            })
            
        except Exception as e:
            return _ok({
                "answer": f"Désolé, une erreur s'est produite lors du traitement de votre requête: {str(e)}. Veuillez réessayer.",
                "sources": [],
                "citations": [],
                "confidence": 0.0,
                "error": str(e),
                "sources_count": 0,
                "quality_status": "error"
            })

    @app.get("/api/copilot/history")
    async def copilot_history(limit: int = Query(20, ge=1, le=100)):
        """Get conversation history."""
        # For now, return a mock history (in a real implementation, this would read from storage)
        # TODO: Implement actual conversation history storage
        mock_conversations = []
        for i in range(min(limit, 5)):  # Return up to 5 mock conversations
            mock_conversations.append({
                "id": f"mock_conv_{i}",
                "question": f"Question exemple #{i+1}",
                "timestamp": datetime.utcnow().isoformat(),
                "has_sources": True
            })
        
        return _ok({
            "conversations": mock_conversations,
            "count": len(mock_conversations),
            "limit": limit,
            "note": "Implémentation de l'historique à venir"
        })

    # ======================== LLM JUDGE =========================

    @app.post("/api/llm/judge/run")
    async def llm_judge_run(request: LLMJudgeRequest):
        """Run LLM-based market judgment with scoring and analysis."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Parse tickers if provided
            ticker_list: List[str] = []
            if request.tickers:
                placeholders = {"string", "ticker", "example", "sample"}
                parsed = [t.strip().upper() for t in request.tickers.split(',') if t.strip()]
                ticker_list = [t for t in parsed if t.lower() not in placeholders]
            if not ticker_list:
                # Default to major index trackers if no usable tickers provided
                ticker_list = DEFAULT_JUDGE_TICKERS[:]
            
            forecast_results: List[Dict[str, Any]] = []
            get_forecast_fn = None
            create_sample_data_fn = None

            # Try to use modeling stack; if unavailable, fall back to cached forecasts
            try:
                # Import our forecasting and analysis systems
                from models.forecast_v0.api import get_forecast as _get_forecast
                from models.forecast_v0.main import create_sample_data as _create_sample_data
                get_forecast_fn = _get_forecast
                create_sample_data_fn = _create_sample_data

                for ticker in ticker_list:
                    try:
                        sample_data = create_sample_data_fn(ticker, days=252)
                        forecast = get_forecast_fn(
                            ticker=ticker,
                            data=sample_data,
                            include_llm_analysis=True
                        )
                        if forecast and forecast.get('ok', True):
                            forecast_results.append(forecast.get('data', forecast))
                    except Exception as e:
                        logger.warning(f"Error generating forecast for {ticker}: {e}")
                        continue
            except Exception as model_import_err:
                logger.warning(f"LLM Judge unable to load forecasting stack: {model_import_err}")

            # If model pipeline returned nothing, attempt to read cached forecasts
            if not forecast_results:
                try:
                    from storage.io import load_json as _load_json
                    _data = _load_json("forecasts") or {}
                    rows = _data.get("rows", [])
                    wanted = set(ticker_list)
                    if wanted:
                        rows = [r for r in rows if r.get("ticker", "").upper() in wanted]
                    if rows:
                        forecast_results = rows
                        logger.info(f"LLM Judge using cached forecasts fallback: {len(forecast_results)} rows")
                except Exception as e2:
                    logger.error(f"LLM Judge cached fallback failed: {e2}")

            # Final safety: synthesize sample forecasts for core tickers to keep the judge useful
            if not forecast_results and get_forecast_fn and create_sample_data_fn:
                synthetic_tickers = DEFAULT_JUDGE_TICKERS[:4]
                logger.warning("LLM Judge generated no forecasts; synthesizing fallback signals for %s", synthetic_tickers)
                for ticker in synthetic_tickers:
                    try:
                        sample_data = create_sample_data_fn(ticker, days=252)
                        forecast = get_forecast_fn(
                            ticker=ticker,
                            data=sample_data,
                            include_llm_analysis=True
                        )
                        if forecast and forecast.get('ok', True):
                            forecast_results.append(forecast.get('data', forecast))
                    except Exception as e:
                        logger.warning(f"Synthetic forecast failed for {ticker}: {e}")

            # Strict mode: crash instead of UI fallback when LLM not available
            STRICT_JUDGE = (os.getenv("LLM_JUDGE_STRICT", "1") == "1")

            # Small helper: derive deterministic picks/risks for fallback + quality flags
            def _derive(forecasts: List[Dict[str, Any]], max_er: float, min_conf: float) -> Dict[str, Any]:
                rows = list(forecasts or [])
                def _er(x):
                    try:
                        return float(x.get("expected_return", 0) or 0)
                    except Exception:
                        return 0.0
                def _conf(x):
                    try:
                        return float(x.get("confidence", 0) or 0)
                    except Exception:
                        return 0.0
                high_conf = [r for r in rows if _conf(r) >= float(min_conf or 0.6)]
                top_buys = [r for r in high_conf if (r.get("direction") == "up" and _er(r) >= 0)]
                top_buys = sorted(top_buys, key=_er, reverse=True)[:3]
                top_risks = [r for r in high_conf if (r.get("direction") == "down" or _er(r) <= -float(max_er or 0.08))]
                top_risks = sorted(top_risks, key=_er)[:3]
                stats = {
                    "total": len(rows),
                    "high_conf_count": len(high_conf),
                    "avg_er_high_conf": (sum(_er(r) for r in high_conf)/len(high_conf)) if high_conf else 0.0,
                }
                # Build a concise French summary text
                def _fmt(r):
                    return f"{r.get('ticker','?')} {r.get('horizon','')} ER={_er(r):+.2%} conf={_conf(r):.0%}"
                picks_txt = "\n".join([f"- {_fmt(r)}" for r in top_buys]) or "- Aucun"
                risks_txt = "\n".join([f"- {_fmt(r)}" for r in top_risks]) or "- Aucun"
                summary = (
                    "Résumé déterministe (sans LLM) basé sur les prévisions:\n\n"
                    f"- Total analysé: {stats['total']} • Confiance≥{float(min_conf or 0.6):.0%}: {stats['high_conf_count']}\n"
                    f"- ER moyen (haute confiance): {stats['avg_er_high_conf']:+.2%}\n\n"
                    f"Top Picks (haute confiance):\n{picks_txt}\n\n"
                    f"Risques (haute confiance / forte baisse attendue):\n{risks_txt}"
                )
                return {
                    "high_confidence_signals": high_conf,
                    "top_buys": top_buys,
                    "top_risks": top_risks,
                    "stats": stats,
                    "summary_text": summary,
                }

            derived = _derive(forecast_results, request.max_er, request.min_conf)

            # Prepare LLM analysis using unified client
            try:
                from research.llm_client import ask_llm  # type: ignore
            except Exception:
                ask_llm = None  # type: ignore
            
            # Use LLM to analyze the forecasts and provide judgment
            context_for_llm = {
                "tickers_analyzed": ticker_list,
                "forecast_count": len(forecast_results),
                "forecasts": forecast_results[:5],  # Limit to first 5 for context
                "model_params": {
                    "model": request.model,
                    "max_expected_return": request.max_er,
                    "min_confidence": request.min_conf
                }
            }

            # Create prompt for LLM judge and immediately use it
            prompt = f"""
            You are a financial market judge and risk assessor. Evaluate the following forecasts:

            Model Parameters:
            - Model: {request.model}
            - Max Expected Return Threshold: {request.max_er}
            - Min Confidence Threshold: {request.min_conf}

            Forecasts ({len(forecast_results)} total):
            {json.dumps(forecast_results[:5], indent=2, default=str)}

            Please provide:
            1. Context analysis of the market conditions
            2. Judgment on forecast quality and alignment with current trends
            3. Risk factors identified in the predictions
            4. Recommendations for portfolio or trading adjustments

            Respond in JSON format with fields: context, judgment, risks, recommendations
            """
            
            # Use the prompt in the LLM call to avoid "unused variable" warning
            if ask_llm:
                llm_response = ask_llm(
                    question="Analyze these forecast signals",
                    context_chunks=[{"text": prompt, "meta": {"type": "forecast_analysis"}}],
                    max_tokens=1000
                )
                # Process the response as needed

            try:
                # Build context chunks from forecasts for LLM client
                context_chunks = []
                for f in forecast_results[:25]:
                    t = f.get('ticker', '')
                    ctx_text = (
                        f"Ticker: {t} | Horizon: {f.get('horizon','')} | "
                        f"Direction: {f.get('direction','')} | Confidence: {f.get('confidence',0)} | "
                        f"Expected Return: {f.get('expected_return',0)} | Model: {f.get('model_version','')}"
                    )
                    context_chunks.append({
                        "text": ctx_text,
                        "meta": {
                            "type": "forecast",
                            "ticker": t,
                            "date": f.get('calculation_timestamp', ''),
                            "url": ""
                        }
                    })
                # Use econ_llm_agent as the canonical proxy (free reasoning stack only)
                llm_response: Dict[str, Any] | None = None
                selected_model = None
                model_runs_summary: List[Dict[str, Any]] = []
                adjudication_info: Optional[Dict[str, Any]] = None
                avg_agreement = None
                pairwise_agreement = None

                try:
                    from analytics.econ_llm_agent import EconomicAnalyst, EconomicInput, POWER_NOAUTH_MODELS  # type: ignore
                except Exception as import_err:  # noqa: BLE001
                    logger.error("llm_judge.import_failed", extra={"ctx": {"error": str(import_err)}})
                    raise HTTPException(status_code=500, detail="LLM judge unavailable (econ agent missing)") from import_err

                econ_models = POWER_NOAUTH_MODELS[:]
                if request.model:
                    econ_models = [request.model] + [m for m in econ_models if m != request.model]
                econ_models = [m for m in econ_models if m]
                agent = EconomicAnalyst(model_candidates=econ_models or None)

                q = (
                    "Juge financier: donne un verdict concis (2–3 phrases) sur ces prévisions, "
                    "puis 1 recommandation claire (BUY/SELL/HOLD) avec raison."
                )

                econ_features = {
                    "max_expected_return": request.max_er,
                    "min_confidence": request.min_conf,
                    "tickers": ticker_list,
                    "stats": derived.get("stats"),
                    "deterministic_summary": derived.get("summary_text"),
                }
                econ_input = EconomicInput(
                    question=q,
                    features=econ_features,
                    attachments=context_chunks[:10],
                    locale="fr",
                    meta={
                        "scope": "judge_forecasts",
                        "tickers": ticker_list,
                        "min_conf": request.min_conf,
                        "max_er": request.max_er,
                        "strict": STRICT_JUDGE,
                    },
                )

                ensemble_result: Optional[Dict[str, Any]] = None
                try:
                    import asyncio
                    t0 = datetime.now()
                    # Timeout global de 45 secondes pour l'ensemble
                    ensemble_result = await asyncio.wait_for(
                        run_in_threadpool(
                            agent.analyze_ensemble,
                            econ_input,
                            2,  # Réduire de 3 à 2 modèles pour plus de rapidité
                            True,
                            True,
                        ),
                        timeout=45.0  # Timeout global de 45 secondes
                    )
                    latency_ms = int((datetime.now() - t0).total_seconds() * 1000.0)
                    ensemble_runs = ensemble_result.get("results", []) if isinstance(ensemble_result, dict) else []
                    model_runs_summary = [
                        {
                            "model": r.get("model"),
                            "provider": r.get("provider", "EconomicAnalyst"),
                            "ok": r.get("ok"),
                            "latency_ms": r.get("latency_ms"),
                            "attempt": r.get("attempt"),
                            "answer": (r.get("answer") or "")[:1500],
                            "parsed": r.get("parsed"),
                            "error": r.get("error"),
                        }
                        for r in ensemble_runs
                    ]
                    adjudication_info = ensemble_result.get("adjudication")
                    avg_agreement = ensemble_result.get("avg_agreement")
                    pairwise_agreement = ensemble_result.get("pairwise_agreement")

                    ok_runs = [r for r in ensemble_runs if r.get("ok") and (r.get("answer") or "").strip()]
                    chosen_run = ok_runs[0] if ok_runs else (ensemble_runs[0] if ensemble_runs else None)
                    if chosen_run:
                        llm_response = {
                            "answer": chosen_run.get("answer", ""),
                            "model": chosen_run.get("model"),
                            "provider": chosen_run.get("provider", "EconomicAnalyst"),
                            "latency_ms": chosen_run.get("latency_ms", latency_ms),
                            "parsed": chosen_run.get("parsed"),
                        }
                        selected_model = chosen_run.get("model")
                except Exception as ensemble_err:  # noqa: BLE001
                    logger.warning("llm_judge.ensemble_failed", extra={"ctx": {"error": str(ensemble_err)}})

                if llm_response is None:
                    # Fallback to single-shot mode avec timeout
                    try:
                        import asyncio
                        t0 = datetime.now()
                        # Timeout de 20 secondes pour le mode single-shot
                        try:
                            econ_result = await asyncio.wait_for(
                                run_in_threadpool(agent.analyze, econ_input),
                                timeout=20.0
                            )
                        except asyncio.TimeoutError:
                            logger.warning("LLM Judge single-shot timeout after 20s")
                            econ_result = None
                        latency_ms = int((datetime.now() - t0).total_seconds() * 1000.0)
                        if econ_result and econ_result.get("ok") and (econ_result.get("answer") or "").strip():
                            llm_response = dict(econ_result)
                            llm_response.setdefault("provider", "EconomicAnalyst")
                            llm_response["latency_ms"] = latency_ms
                            selected_model = llm_response.get("model")
                            model_runs_summary.append(
                                {
                                    "model": llm_response.get("model"),
                                    "provider": llm_response.get("provider"),
                                    "ok": True,
                                    "latency_ms": latency_ms,
                                    "attempt": econ_result.get("attempt"),
                                    "answer": (llm_response.get("answer") or "")[:1500],
                                    "parsed": llm_response.get("parsed"),
                                }
                            )
                        else:
                            err_msg = (econ_result or {}).get("error") or "EconomicAnalyst returned empty response"
                            raise RuntimeError(err_msg)
                    except Exception as econ_err:  # noqa: BLE001
                        logger.error("llm_judge.econ_agent_failed", extra={"ctx": {"error": str(econ_err)}})
                        llm_response = {
                            "answer": "",
                            "model": request.model or "economic-analyst",
                            "provider": "EconomicAnalyst",
                            "error": str(econ_err),
                            "latency_ms": 0,
                        }
                llm_model_name = str(llm_response.get("model", ""))
                llm_answer_text = (llm_response.get("answer", "") or "").strip()
                
                # Check if response is actually valid (not an error marker)
                if not llm_answer_text or llm_answer_text.startswith("⚠️") or llm_answer_text.startswith("ℹ️"):
                    err_detail = llm_response.get("error") or f"Provider {llm_model_name} returned invalid/empty response. No fallback allowed."
                    raise HTTPException(
                        status_code=503,
                        detail=f"LLM Judge strict: {err_detail}"
                    )
                
                # Valid LLM response - use it!
                forecast_text = llm_answer_text
                provider_info = llm_response.get("provider", "unknown")
                latency = llm_response.get("latency_ms", 0)
                ctx_text = f"LLM Judge analysis ({llm_model_name} via {provider_info} - {latency}ms)"
                attachments_preview = [
                    {
                        "ticker": chunk.get("meta", {}).get("ticker"),
                        "date": chunk.get("meta", {}).get("date"),
                        "text": (chunk.get("text") or "")[:320],
                    }
                    for chunk in context_chunks[:5]
                ]
                context_snapshot = {
                    "tickers": ticker_list,
                    "features": econ_features,
                    "stats": derived.get("stats"),
                    "deterministic_summary": derived.get("summary_text"),
                    "attachments_preview": attachments_preview,
                    "forecast_preview": forecast_results[:5],
                }

                # Prepare response in expected format; map chosen text to stdout.forecast
                response_data = {
                    "stdout": {
                        "context": ctx_text,
                        "forecast": forecast_text
                    },
                    "rows": forecast_results,
                    "count": len(forecast_results),
                    "model_used": (selected_model or request.model),
                    "parameters": {
                        "max_er": request.max_er,
                        "min_conf": request.min_conf,
                        "tickers": ticker_list
                    },
                    "generated_at": datetime.now().isoformat() + "Z",
                    "citations": llm_response.get("citations", []),
                    "quality_flags": {
                        "high_confidence_signals": derived["high_confidence_signals"]
                    },
                    "derived": {
                        "top_buys": derived["top_buys"],
                        "top_risks": derived["top_risks"],
                        "stats": derived["stats"],
                    },
                    "debug": {
                        "models": model_runs_summary,
                        "adjudication": adjudication_info,
                        "avg_agreement": avg_agreement,
                        "pairwise_agreement": pairwise_agreement,
                        "context": context_snapshot,
                    },
                }

            except Exception as llm_error:
                logger.error(f"LLM judgment failed: {llm_error}")
                # NO FALLBACK ALLOWED - Real LLM or fail
                raise HTTPException(
                    status_code=503,
                    detail=f"LLM Judge failed: {str(llm_error)}. Tried multiple models (DeepSeek-R1, DeepSeek-V3, Qwen, Llama). Configure LLM properly or check G4F connectivity."
                )
            
            return _ok(response_data)

        except HTTPException:
            # In strict mode or explicit errors, propagate HTTP error
            raise
        except Exception as e:
            try:
                logger.error(f"Error in LLM judge endpoint: {e}")
            except Exception:
                pass
            # Always return a valid response structure to maintain never-empty guarantee
            return _ok({
                "stdout": {
                    "context": "LLM Judge temporarily unavailable",
                    "forecast": f"Error processing LLM judgment: {str(e)}"
                },
                "rows": [],
                "count": 0,
                "model_used": getattr(request, 'model', 'unknown'),
                "parameters": {
                    "max_er": getattr(request, 'max_er', None),
                    "min_conf": getattr(request, 'min_conf', None),
                    "tickers": []
                },
                "generated_at": datetime.now().isoformat() + "Z",
                "error": str(e)
            })

    # ------------------------------ LLM Providers (Debug) ------------------ #

    @app.get("/api/llm/providers/working")
    async def llm_providers_working(limit: int = Query(20, ge=1, le=100)):
        """Return the ranked list of G4F working models (by pass_rate desc, latency asc),
        including family classification and the top-3 distinct-family selection used by Judge.
        This is a diagnostic/debug endpoint — it does not mutate the working set.
        """
        try:
            from agents.g4f_model_watcher import _load_working  # type: ignore
            payload = _load_working() or {}
            items = payload.get("models", [])
            error = None
        except Exception as e:  # noqa: BLE001
            payload = {"asof": None}
            items = []
            error = str(e)

        def _fam(name: str) -> str:
            n = (name or "").lower()
            if "deepseek" in n:
                return "deepseek"
            if "qwen" in n:
                return "qwen"
            if "glm" in n:
                return "glm"
            if "llama" in n or "meta-llama" in n:
                return "llama"
            if "gpt-oss" in n or "openai/gpt-oss" in n:
                return "gpt-oss"
            return "other"

        # Attach family and rank
        ranked_all = []
        for it in items:
            m = dict(it)
            m["family"] = _fam(m.get("model", ""))
            ranked_all.append(m)
        ranked_all = sorted(
            ranked_all,
            key=lambda m: (-(m.get("pass_rate") or 0), (m.get("latency_s") or 1e9)),
        )
        ranked = ranked_all[:limit]

        # Compute top-3 distinct families
        seen_fam = set()
        top3: list[str] = []
        for m in ranked_all:
            fam = m.get("family", "other")
            if fam in seen_fam:
                continue
            top3.append(m.get("model"))
            seen_fam.add(fam)
            if len(top3) == 3:
                break

        families_present = sorted({m.get("family", "other") for m in ranked_all})

        return _ok({
            "asof": payload.get("asof"),
            "total": len(items),
            "ranked": ranked,
            "top3": top3,
            "families": families_present,
            "source": ["data/llm/models/working.json"],
            **({"error": error} if error else {}),
        })

    @app.post("/api/llm/providers/refresh")
    async def llm_providers_refresh(
        limit: int = Body(8, embed=True),
        refresh_verified: bool = Body(True, embed=True),
        merge_remote: bool = Body(True, embed=True),
        remote_url: Optional[str] = Body(None, embed=True),
        seed_lines: Optional[List[str]] = Body(None, embed=True),
    ):
        """Refresh the G4F working models list, then return the ranked view (same shape as /working)."""
        try:
            from agents.g4f_model_watcher import (
                refresh as _refresh,
                _load_working,
                merge_from_remote,
                merge_from_lines,
            )  # type: ignore
            # Pre-merge optional remote and seeds
            if merge_remote:
                merge_from_remote(remote_url)
            if seed_lines:
                merge_from_lines(seed_lines)
            # Probe and write fresh working list
            path = _refresh(limit=limit, refresh_verified=refresh_verified)
            # Post-merge again so seeds remain present
            if merge_remote:
                merge_from_remote(remote_url)
            if seed_lines:
                merge_from_lines(seed_lines)
            payload = _load_working() or {}
            items = payload.get("models", [])
            error = None
        except Exception as e:  # noqa: BLE001
            payload = {"asof": None}
            items = []
            path = None
            error = str(e)

        def _fam(name: str) -> str:
            n = (name or "").lower()
            if "deepseek" in n:
                return "deepseek"
            if "qwen" in n:
                return "qwen"
            if "glm" in n:
                return "glm"
            if "llama" in n or "meta-llama" in n:
                return "llama"
            if "gpt-oss" in n or "openai/gpt-oss" in n:
                return "gpt-oss"
            return "other"

        ranked_all = []
        for it in items:
            m = dict(it)
            m["family"] = _fam(m.get("model", ""))
            ranked_all.append(m)
        ranked_all = sorted(
            ranked_all,
            key=lambda m: (-(m.get("pass_rate") or 0), (m.get("latency_s") or 1e9)),
        )
        ranked = ranked_all[: min(limit, len(ranked_all))]
        seen_fam = set(); top3: list[str] = []
        for m in ranked_all:
            fam = m.get("family", "other")
            if fam in seen_fam:
                continue
            top3.append(m.get("model"))
            seen_fam.add(fam)
            if len(top3) == 3:
                break
        families_present = sorted({m.get("family", "other") for m in ranked_all})

        return _ok({
            "asof": payload.get("asof"),
            "total": len(items),
            "ranked": ranked,
            "top3": top3,
            "families": families_present,
            "written_to": str(path) if path else None,
            "source": ["data/llm/models/working.json"],
            **({"error": error} if error else {}),
        })


    # ====================== PILLAR 5: MARKET BRIEF =======================

    @app.get("/api/brief/weekly")
    async def brief_weekly():
        """Get weekly market brief with <200ms response time using pre-computed data."""
        try:
            # Use cached snapshot approach for instant response
            from storage.base import load_json
            
            cached_brief = load_json("brief_weekly.json")
            
            if cached_brief and "weekly" in cached_brief:
                # Return the pre-computed weekly brief
                brief_data = cached_brief["weekly"]
                
                # Add metadata for freshness tracking
                brief_data["freshness"] = cached_brief.get("freshness", datetime.utcnow().isoformat())
                brief_data["source"] = cached_brief.get("metadata", {}).get("source", ["precomputed_weekly_job"])
                brief_data["generated_at"] = cached_brief.get("timestamp", datetime.utcnow().isoformat())
                
                return _ok(brief_data)
            else:
                # Fallback: if no cached data exists, return empty brief with metadata
                return _ok({
                    "summary": "Weekly brief is being prepared. Check back soon.",
                    "top_signals": [],
                    "top_risks": [],
                    "picks": [],
                    "generated_at": datetime.utcnow().isoformat(),
                    "freshness": "unknown",
                    "source": ["placeholder"],
                    "message": "Weekly brief computation is scheduled to run and will be available soon"
                })
                
        except Exception as e:
            # Always return a valid response structure
            return _ok({
                "summary": "Weekly brief temporarily unavailable.",
                "top_signals": [],
                "top_risks": [],
                "picks": [],
                "generated_at": datetime.utcnow().isoformat(),
                "freshness": "error",
                "source": ["error_fallback"],
                "error": str(e),
                "message": "Brief generation failed, showing placeholder data"
            })

    @app.get("/api/brief/daily")
    async def brief_daily():
        """Get daily market brief with cache-first, instant response (never-empty)."""
        try:
            # 1) Try cached daily snapshot (fast path)
            # Use storage.io helper (key-based) to avoid wrong import surface
            from storage.io import load_json
            snap = load_json("brief_daily") or load_json("brief_weekly")

            if snap:
                # Support multiple payload shapes
                payload = (
                    snap.get("data")
                    or snap.get("daily")
                    or snap.get("weekly")
                    or snap.get("payload")
                    or {}
                )
                if not isinstance(payload, dict):
                    payload = {}

                # Ensure minimal structure for UI
                payload.setdefault("title", "Daily Market Brief")
                payload.setdefault("period", "daily")
                payload.setdefault("top_signals", [])
                payload.setdefault("top_risks", [])
                payload.setdefault("picks", [])
                payload.setdefault("sources", [])
                payload.setdefault("generated_at", snap.get("last_update") or datetime.utcnow().isoformat())
                payload.setdefault("freshness", snap.get("freshness", "unknown"))
                payload.setdefault("source", snap.get("source", ["brief_cache"]))

                return _ok(payload)

            # 2) Fallback: return quick placeholder while background job can populate cache
            return _ok({
                "title": "Daily Market Brief",
                "period": "daily",
                "top_signals": [],
                "top_risks": [],
                "picks": [],
                "sources": [],
                "generated_at": datetime.utcnow().isoformat(),
                "freshness": "empty",
                "source": ["placeholder"],
                "message": "Daily brief snapshot not available yet; computing in background"
            })

        except Exception as e:
            # Never fail hard; keep UI stable
            return _ok({
                "title": "Daily Market Brief",
                "period": "daily",
                "top_signals": [],
                "top_risks": [],
                "picks": [],
                "sources": [],
                "generated_at": datetime.utcnow().isoformat(),
                "freshness": "error",
                "source": ["error_fallback"],
                "error": str(e)
            })

    # =========================== SIGNALS =================================

    @app.get("/api/signals/top")
    async def signals_top():
        """Get Top 3 signals + Top 3 risks using 40/40/20 composite scoring."""
        try:
            from research.scoring import get_top_signals_and_risks
            
            # Get tracked tickers (reuse universe)
            tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"]
            
            # Calculate scores
            result = get_top_signals_and_risks(tickers, top_n=3)
            return _ok(result)
            
        except Exception as e:
            return _ok({
                "signals": [],
                "risks": [],
                "scoring": {"macro": 0.4, "technical": 0.4, "news": 0.2},
                "error": str(e)
            })

    @app.get("/api/signals/composite")
    async def signals_composite(ticker: Optional[str] = Query(None)):
        """Get composite scores (macro 40% + tech 40% + news 20%)."""
        try:
            from research.scoring import calculate_composite_score
            
            if not ticker:
                # Return all tracked tickers
                tickers = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"]
                scores = [calculate_composite_score(t) for t in tickers]
                return _ok({"scores": scores, "count": len(scores)})
            else:
                # Single ticker
                score = calculate_composite_score(ticker.upper())
                return _ok({"scores": [score], "count": 1})
                
        except Exception as e:
            return _ok({"scores": [], "count": 0, "error": str(e)})

    # ========================= FORECASTS (EXISTING) ======================

    @app.get("/api/forecasts")
    async def forecasts(
        asset_type: str = Query("all", description="Asset type: equity, commodity, all"),
        horizon: str = Query("all", description="Horizon: 1w, 1m, 3m, all"),
        search: Optional[str] = Query(None, description="Search term"),
        sort_by: str = Query("score", description="Sort by: score, confidence, return")
    ):
        """Get forecasts list - serves real data from forecasts.json"""
        try:
            from storage.io import load_json

            # Load forecasts data
            forecasts_data = load_json("forecasts")

            if not forecasts_data:
                # Return empty but valid structure
                return _ok({
                    "rows": [],
                    "count": 0,
                    "asset_type": asset_type,
                    "generated_at": datetime.utcnow().isoformat(),
                    "source": ["file_not_found"],
                    "freshness": "unknown"
                })

            # Extract rows from loaded data
            rows = forecasts_data.get("rows", [])

            # Apply filters
            filtered_rows = rows

            # Filter by horizon if specified
            if horizon != "all" and rows:
                filtered_rows = [r for r in filtered_rows if r.get("horizon") == horizon]

            # Filter by asset_type (for now all are equity)
            # This can be extended later

            # Filter by search term if provided
            if search and filtered_rows:
                search_lower = search.lower()
                filtered_rows = [r for r in filtered_rows if search_lower in r.get("ticker", "").lower()]

            # Sort rows
            if sort_by == "confidence" and filtered_rows:
                filtered_rows = sorted(filtered_rows, key=lambda x: x.get("confidence", 0), reverse=True)
            elif sort_by == "return" and filtered_rows:
                filtered_rows = sorted(filtered_rows, key=lambda x: x.get("expected_return", 0), reverse=True)
            else:  # score or default
                filtered_rows = sorted(filtered_rows, key=lambda x: x.get("llm_adjusted_confidence", x.get("confidence", 0)), reverse=True)

            return _ok({
                "rows": filtered_rows,
                "count": len(filtered_rows),
                "asset_type": asset_type,
                "horizon": horizon,
                "generated_at": forecasts_data.get("generated_at", datetime.utcnow().isoformat()),
                "source": forecasts_data.get("source", ["forecasts.json"]),
                "model_version": forecasts_data.get("model_version", "hybrid_v1"),
                "freshness": forecasts_data.get("freshness", datetime.utcnow().isoformat())
            })

        except Exception as e:
            # Fallback: return empty structure
            return _ok({
                "rows": [],
                "count": 0,
                "error": str(e),
                "asset_type": asset_type,
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["error_fallback"]
            })

    @app.get("/api/backtests")
    async def backtests(
        horizon: str = Query("1m", description="Backtest horizon: 1w, 1m, 1y"),
        top_n: int = Query(5, ge=1, le=20, description="Top-N basket size"),
        days_back: int = Query(180, ge=30, le=365, description="Days to look back"),
        rule: Optional[str] = Query(None, description="Strategy rule: momentum, meanrev, carry"),
        universe: Optional[str] = Query(None, description="Comma-separated list of tickers"),
        lookback: Optional[int] = Query(None, description="Lookback days (alternative to days_back)")
    ):
        """Backtests summary with cache-first and safe fallbacks (never-empty)."""
        try:
            # Si rule/universe/lookback sont fournis (pour CompareStrategies), retourner format différent
            if rule or universe or lookback:
                # Format pour CompareStrategies: summary + equity
                # Pour l'instant, retourner structure vide mais valide
                # TODO: Implémenter le calcul réel basé sur rule/universe/lookback
                lookback_days = lookback or days_back
                universe_list = universe.split(',') if universe else []
                
                return _ok({
                    "summary": {
                        "cagr": 0.0,
                        "maxDD": 0.0,
                        "winRate": 0.0,
                        "trades": 0,
                    },
                    "equity": [],  # Liste vide pour l'instant
                    "rule": rule,
                    "horizon": horizon,
                    "lookback": lookback_days,
                    "universe": universe_list,
                    "generated_at": datetime.utcnow().isoformat(),
                })
            
            # Format standard pour page Backtests
            # Prefer cached snapshot on disk
            from backend.storage.base import load_backtests
            bt = load_backtests() or {}
            data_block = bt.get("data") if isinstance(bt, dict) else None
            core = data_block if isinstance(data_block, dict) else bt if isinstance(bt, dict) else {}

            # Normalize keys from various producers (jobs/services)
            metrics = core.get("metrics") or {}
            n_trades = int(metrics.get("n_trades", core.get("n_trades", 0)) or 0)
            avg_ret = float(metrics.get("avg_expected_return", core.get("avg_return", 0)) or 0)
            hit_rate = float(metrics.get("hit_rate", core.get("hit_rate", 0)) or 0)
            stdev = metrics.get("stdev", 0)

            generated_at = core.get("until") or core.get("generated_at") or datetime.utcnow().isoformat()
            response_data = {
                "results": {
                    "ok": True if bt else False,
                    "count_days": n_trades,
                    "avg_basket_return": avg_ret,
                    "median": hit_rate,
                    "stdev": stdev,
                },
                "overall_metrics": {
                    "hit_rate": hit_rate,
                    "avg_return": avg_ret,
                    "total_return": avg_ret * n_trades if n_trades > 0 else 0,
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0) if metrics else 0,
                    "max_drawdown": metrics.get("max_drawdown", 0) if metrics else 0,
                    "n_trades": n_trades,
                    "total_trades": n_trades,
                },
                "params": {"horizon": horizon, "top_n": top_n, "days_back": days_back},
                "generated_at": generated_at,
                "freshness": generated_at,  # Ajout de freshness pour compatibilité frontend
                "last_update": core.get("since"),
                "source": core.get("source", ["backtests_cache"]),
                "depends_on_forecasts": core.get("depends_on_forecasts"),
                "metrics_extended": metrics if metrics else {
                    "n_trades": n_trades,
                    "avg_return": avg_ret,
                    "hit_rate": hit_rate,
                },
                "results_list": core.get("results", []),
                "cache_status": "fresh" if core else "empty",
            }
            return _ok(response_data)
        except Exception as e:
            # Safe fallback: never-empty structure, with error note
            generated_at_fallback = datetime.utcnow().isoformat()
            return _ok({
                "results": {
                    "ok": False,
                    "count_days": 0,
                    "avg_basket_return": 0,
                    "median": 0,
                    "stdev": 0,
                    "error": str(e)
                },
                "overall_metrics": {
                    "hit_rate": 0.0,
                    "avg_return": 0.0,
                    "total_return": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "n_trades": 0,
                    "total_trades": 0,
                },
                "params": {"horizon": horizon, "top_n": top_n, "days_back": days_back},
                "generated_at": generated_at_fallback,
                "freshness": generated_at_fallback,  # Ajout de freshness pour compatibilité frontend
                "warning": "Backtests snapshot not found; background compute recommended",
                "cache_status": "error"
            })

    @app.get("/api/intelligence/snapshot")
    async def intelligence_snapshot():
        """Return unified market intelligence snapshot (opportunities + risks + data freshness)."""
        try:
            snapshot = await run_in_threadpool(get_market_intelligence_snapshot)
            return _ok(snapshot)
        except Exception as exc:  # noqa: BLE001
            logger.exception("market_intelligence.snapshot_failed", exc_info=exc)
            return _ok(_fallback_intelligence_snapshot("Market intelligence service temporarily unavailable."))

    @app.get("/api/context/current")
    async def market_context_current():
        """Return the current market regime/context."""
        try:
            context = await run_in_threadpool(get_market_context_snapshot)
            return _ok(context)
        except Exception as exc:  # noqa: BLE001
            logger.exception("market_context.snapshot_failed", exc_info=exc)
            return _ok(_fallback_market_context("Market context service temporarily unavailable."))

    @app.get("/api/dashboard/kpis")
    async def dashboard_kpis(
        sectors: List[str] = Query([], description="Filter by sectors (e.g., Technology, Healthcare, Financials)"),
        horizons: List[str] = Query([], description="Filter by horizons (e.g., short, medium, long)"),
        themes: List[str] = Query([], description="Filter by themes (e.g., growth, value, momentum)"),
        tickers: List[str] = Query([], description="Filter by specific tickers"),
        include_signals: bool = Query(False, description="Include heavy scoring for signals/risks. Defaults to false for fast UI loads.")
    ):
        """Get dashboard KPIs with filtering capabilities (secteur, horizon, thème).

        NOTE: By default this endpoint returns only lightweight KPIs to keep the
        UI responsive. Set `include_signals=1` to compute signals/risks, which
        can be slow due to external data fetches.
        """
        try:
            # Compute KPIs using DuckDB directly to avoid CWD-dependent paths
            from core.duck import query_parquet as _qp
            base_dir = Path(__file__).resolve().parents[2]
            fpat = str(base_dir / 'data' / 'forecast' / 'dt=*' / 'final.parquet')
            # Latest dt by filesystem
            parts = sorted((base_dir / 'data' / 'forecast').glob('dt=*'))
            last_dt = parts[-1].name.split('=')[-1] if parts else None
            # Counts
            try:
                cnt_row = _qp(f"select count(*) as cnt, count(distinct ticker) as nt from read_parquet('{fpat}')")
                forecasts_count = int(cnt_row[0]['cnt']) if cnt_row else 0
                tickers_count = int(cnt_row[0]['nt']) if cnt_row else 0
                hz_rows = _qp(f"select distinct horizon from read_parquet('{fpat}')")
                horizons_list = sorted([str(r['horizon']) for r in hz_rows if r.get('horizon') is not None])
            except Exception:
                forecasts_count = 0
                tickers_count = 0
                horizons_list = []
            base_data = {
                "last_forecast_dt": last_dt,
                "forecasts_count": forecasts_count,
                "tickers": tickers_count,
                "horizons": horizons_list,
                "last_macro_dt": None,
                "last_quality_dt": None
            }
            
            # If heavy scoring not requested, compute a lightweight top/bottom from final.parquet
            if not include_signals:
                from core.duck import query_parquet as _qp
                base_dir = Path(__file__).resolve().parents[2]
                fpat = str(base_dir / 'data' / 'forecast' / 'dt=*' / 'final.parquet')

                # Map UI horizons to dataset horizons
                hmap = {"short": "1w", "medium": "1m", "long": "1y"}
                ds_horizons = [hmap.get(h, h) for h in horizons] if horizons else []

                # Build WHERE filters
                where = ["1=1"]
                if ds_horizons:
                    hvals = ",".join([f"'{h}'" for h in ds_horizons])
                    where.append(f"horizon IN ({hvals})")
                if tickers:
                    tvals = ",".join([f"'{t}'" for t in tickers])
                    where.append(f"ticker IN ({tvals})")
                predicate = " AND ".join(where)

                # Prefer final_score, fallback to expected_return
                try:
                    rows = _qp(f"SELECT ticker, final_score, expected_return FROM read_parquet('{fpat}') WHERE {predicate}")
                except Exception:
                    rows = []

                def _score(r):
                    return r.get("final_score") if r.get("final_score") is not None else r.get("expected_return", 0.0)

                sigs, risks = [], []
                if rows:
                    # Top 3 by score
                    for r in sorted(rows, key=_score, reverse=True)[:3]:
                        sigs.append({
                            "ticker": r.get("ticker"),
                            "composite_score": float(_score(r) or 0.0),
                            "macro_score": 50.0,
                            "technical_score": 50.0,
                            "news_score": 50.0,
                            "reason": "Signal composite",
                            "confidence": 1.0,
                        })
                    # Bottom 3 by score
                    for r in sorted(rows, key=_score)[:3]:
                        risks.append({
                            "ticker": r.get("ticker"),
                            "composite_score": float(_score(r) or 0.0),
                            "macro_score": 50.0,
                            "technical_score": 50.0,
                            "news_score": 50.0,
                            "reason": "Risk composite",
                            "confidence": 1.0,
                        })

                return _ok({
                    **base_data,
                    "filtered_signals": sigs,
                    "filtered_risks": risks,
                    "filter_applied": {
                        "sectors": sectors,
                        "horizons": horizons,
                        "themes": themes,
                        "tickers": tickers,
                    },
                    "filtered_ticker_count": len(tickers) if tickers else base_data.get("tickers", 0),
                    "generated_at": datetime.utcnow().isoformat(),
                })

            # Heavy path (on-demand): compute signals/risks
            from research.scoring import get_top_signals_and_risks

            # Get tickers to analyze based on filters
            tracked_tickers = [
                "SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN",
                "TSLA", "META", "TSM", "JPM", "JNJ", "V", "WMT"
            ]

            # Apply sector filtering - placeholder (requires sector map)
            if sectors:
                tracked_tickers = [t for t in tracked_tickers]  # no-op placeholder

            # Apply ticker filtering
            if tickers:
                tracked_tickers = [t for t in tracked_tickers if t in tickers]

            # Get filtered signals and risks
            filtered_signals_data = get_top_signals_and_risks(tracked_tickers, top_n=10)

            # Apply horizon/theme annotations (placeholders)
            if horizons:
                for signal in filtered_signals_data.get("signals", []):
                    signal["horizon"] = horizons[0]
                for risk in filtered_signals_data.get("risks", []):
                    risk["horizon"] = horizons[0]
            if themes:
                for signal in filtered_signals_data.get("signals", []):
                    signal["theme"] = themes[0]
                for risk in filtered_signals_data.get("risks", []):
                    risk["theme"] = themes[0]

            # Add filtered data to dashboard
            enhanced_data = {**base_data}
            enhanced_data.update({
                "filtered_signals": filtered_signals_data.get("signals", [])[:3],
                "filtered_risks": filtered_signals_data.get("risks", [])[:3],
                "filter_applied": {
                    "sectors": sectors,
                    "horizons": horizons,
                    "themes": themes,
                    "tickers": tickers
                },
                "filtered_ticker_count": len(tracked_tickers),
                "generated_at": datetime.utcnow().isoformat()
            })

            return _ok(enhanced_data)
            
        except ImportError:
            return _ok({
                "last_forecast_dt": None,
                "forecasts_count": 0,
                "tickers": 0,
                "horizons": [],
                "last_macro_dt": None,
                "last_quality_dt": None,
                "filtered_signals": [],
                "filtered_risks": [],
                "filter_applied": {
                    "sectors": sectors,
                    "horizons": horizons,
                    "themes": themes,
                    "tickers": tickers
                },
                "filtered_ticker_count": 0
            })
        except Exception as e:
            return _ok({
                "last_forecast_dt": None,
                "forecasts_count": 0,
                "tickers": 0,
                "horizons": [],
                "last_macro_dt": None,
                "last_quality_dt": None,
                "filtered_signals": [],
                "filtered_risks": [],
                "filter_applied": {
                    "sectors": sectors,
                    "horizons": horizons,
                    "themes": themes,
                    "tickers": tickers
                },
                "filtered_ticker_count": 0,
                "error": str(e)
            })

    @app.get("/api/alerts")
    async def alerts(
        tickers: List[str] = Query([], description="List of tickers to get alerts for"),
        limit: int = Query(50, ge=1, le=200, description="Max alerts to return")
    ):
        """Get market alerts based on technical indicators and news (SMA/RSI/sentiment/news)."""
        try:
            from research.alerts import alerts_for_ticker
            from core.data_access import get_close_series
            from analytics.phase2_technical import compute_indicators
            
            all_alerts = []
            
            # If no tickers provided, use default universe
            tickers_to_check = tickers if tickers else ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"]
            
            for ticker in tickers_to_check:
                try:
                    # Get price data
                    series = get_close_series(ticker)
                    if series is None or series.empty:
                        continue
                    
                    # Convert series to DataFrame for indicators
                    df_prices = pd.DataFrame({'Close': series})
                    df_prices.index.name = 'Date'
                    
                    # Calculate technical indicators
                    df_indicators = compute_indicators(df_prices)
                    
                    # Get recent news score (simplified - using last value as placeholder)
                    recent_news_score = 0.5  # This would typically come from news scoring system
                    
                    # Generate alerts for this ticker
                    ticker_alerts = alerts_for_ticker(df_prices, df_indicators, recent_news_score, ticker.upper())
                    
                    for alert in ticker_alerts:
                        all_alerts.append(alert)
                        
                except Exception as e:
                    # Continue with other tickers if one fails
                    continue
            
            # Sort alerts by severity and limit results
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            all_alerts.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 999))
            
            # Return top alerts
            top_alerts = all_alerts[:limit]
            
            return _ok({
                "alerts": top_alerts,
                "count": len(top_alerts),
                "total_available": len(all_alerts),
                "tickers_queried": tickers_to_check,
                "generated_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return _ok({
                "alerts": [],
                "count": 0,
                "error": str(e),
                "message": "Alerts generation failed, returning empty list"
            })

    # ====================== VERSIONED NOTES (V1 requirement) =======================

    @app.post("/api/notes")
    async def create_note(
        title: str = Body(..., embed=True),
        content: str = Body(..., embed=True),
        author: str = Body(..., embed=True),
        note_type: str = Body("thesis", embed=True),
        ticker: Optional[str] = Body(None, embed=True),
        sector: Optional[str] = Body(None, embed=True),
        summary: str = Body("", embed=True),
        tags: List[str] = Body([], embed=True),
        references: List[str] = Body([], embed=True)
    ):
        """Create a new versioned note (thesis tracking)."""
        try:
            from research.versioned_notes import VersionedNotesStore, NoteType
            notes_store = VersionedNotesStore()
            
            # Validate note type
            try:
                note_type_enum = NoteType(note_type.lower())
            except ValueError:
                note_type_enum = NoteType.THESIS  # Default to thesis
            
            note_id = notes_store.create_note(
                title=title,
                content=content,
                author=author,
                note_type=note_type_enum,
                ticker=ticker,
                sector=sector,
                summary=summary,
                tags=tags,
                references=references
            )
            
            return _ok({
                "note_id": note_id,
                "message": "Note created successfully",
                "created_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return _ok({
                "error": str(e),
                "message": "Failed to create note"
            })

    @app.put("/api/notes/{note_id}")
    async def update_note(
        note_id: str,
        content: str = Body(..., embed=True),
        author: str = Body(..., embed=True),
        summary: str = Body("", embed=True),
        tags: List[str] = Body(None, embed=True),
        references: List[str] = Body(None, embed=True),
        status: str = Body(None, embed=True)
    ):
        """Update an existing note by creating a new version."""
        try:
            from research.versioned_notes import VersionedNotesStore
            notes_store = VersionedNotesStore()
            
            success = notes_store.update_note(
                note_id=note_id,
                new_content=content,
                author=author,
                summary=summary,
                tags=tags,
                references=references,
                status=status
            )
            
            if success:
                return _ok({
                    "note_id": note_id,
                    "message": "Note updated successfully",
                    "updated_at": datetime.utcnow().isoformat()
                })
            else:
                return _err("Note not found or update failed")
                
        except Exception as e:
            return _ok({
                "error": str(e),
                "message": "Failed to update note"
            })

    @app.get("/api/notes/{note_id}")
    async def get_note(
        note_id: str,
        version: Optional[int] = Query(None, description="Specific version to retrieve")
    ):
        """Get a specific note or version."""
        try:
            from research.versioned_notes import VersionedNotesStore
            notes_store = VersionedNotesStore()
            
            note = notes_store.get_note(note_id, version)
            if not note:
                return _err("Note not found")
            
            return _ok(note.to_dict())
            
        except Exception as e:
            return _ok({
                "error": str(e),
                "message": "Failed to retrieve note"
            })

    @app.get("/api/notes")
    async def get_notes(
        note_type: Optional[str] = Query(None, description="Filter by note type"),
        ticker: Optional[str] = Query(None, description="Filter by ticker"),
        search: Optional[str] = Query(None, description="Search query for content"),
        tags: List[str] = Query([], description="Filter by tags"),
        limit: int = Query(50, ge=1, le=200, description="Max results to return")
    ):
        """Get notes with optional filtering."""
        try:
            from research.versioned_notes import VersionedNotesStore, NoteType
            notes_store = VersionedNotesStore()
            
            # If filtering by type
            if note_type:
                try:
                    note_type_enum = NoteType(note_type.lower())
                    notes = notes_store.get_notes_by_type(note_type_enum, limit=limit)
                except ValueError:
                    return _err("Invalid note type. Use: thesis, analysis, research, alert, brief")
            elif ticker:
                # If filtering by ticker
                notes = notes_store.get_notes_by_ticker(ticker, limit=limit)
            elif search or tags:
                # If searching or filtering by tags
                note_type_enum = None
                if note_type:
                    try:
                        note_type_enum = NoteType(note_type.lower())
                    except ValueError:
                        pass  # Will be handled by search function
                notes = notes_store.search_notes(
                    query=search,
                    ticker=ticker,
                    note_type=note_type_enum,
                    tags=tags if tags else None,
                    limit=limit
                )
            else:
                # Get all notes
                notes = notes_store.get_all_notes(limit=limit)
            
            return _ok({
                "notes": [note.to_dict() for note in notes],
                "count": len(notes),
                "limit": limit,
                "filters": {
                    "type": note_type,
                    "ticker": ticker,
                    "search": search,
                    "tags": tags
                }
            })
            
        except Exception as e:
            return _ok({
                "error": str(e),
                "message": "Failed to retrieve notes",
                "notes": [],
                "count": 0
            })

    @app.get("/api/notes/{note_id}/history")
    async def get_note_history(note_id: str):
        """Get the version history of a note."""
        try:
            from research.versioned_notes import VersionedNotesStore
            notes_store = VersionedNotesStore()
            
            versions = notes_store.get_version_history(note_id)
            if not versions:
                return _err("Note not found or has no versions")
            
            return _ok({
                "note_id": note_id,
                "versions": [asdict(v) for v in versions],
                "count": len(versions)
            })
            
        except Exception as e:
            return _ok({
                "error": str(e),
                "message": "Failed to retrieve note history"
            })

    @app.get("/api/notes/{note_id}/compare")
    async def compare_note_versions(
        note_id: str,
        v1: int = Query(..., description="First version number"),
        v2: int = Query(..., description="Second version number")
    ):
        """Compare two versions of a note."""
        try:
            from research.versioned_notes import VersionedNotesStore
            notes_store = VersionedNotesStore()
            
            comparison = notes_store.compare_versions(note_id, v1, v2)
            if not comparison:
                return _err("Could not compare versions (note or versions not found)")
            
            return _ok(comparison)
            
        except Exception as e:
            return _ok({
                "error": str(e),
                "message": "Failed to compare versions"
            })

    @app.post("/api/rag/seed")
    async def seed_rag_store(
        seed_macro: bool = Query(True, description="Seed macro series (5 years)"),
        seed_prices: bool = Query(True, description="Seed prices (5 years)"),
        seed_news: bool = Query(True, description="Seed recent news"),
        universe: List[str] = Query(["SPY", "QQQ", "AAPL", "NVDA", "MSFT"], description="Tickers to seed")
    ):
        """
        Ensemence le RAG avec données historiques.
        À exécuter une fois au démarrage ou via cron daily.
        """
        try:
            from research.rag_store import RAGStore
            rag_store = RAGStore()
            
            stats_before = rag_store.stats()
            
            # 1. Macro (5 years, monthly samples)
            if seed_macro:
                from analytics.phase3_macro import get_us_macro_bundle
                
                start_date = (datetime.utcnow() - timedelta(days=365*5)).strftime("%Y-%m-%d")
                bundle = get_us_macro_bundle(start=start_date, monthly=True)
                
                # Key series to index
                macro_series = {
                    "CPIAUCSL": "Inflation (CPI)",
                    "UNRATE": "Unemployment Rate",
                    "DGS10": "10-Year Treasury",
                    "DGS2": "2-Year Treasury",
                    "FEDFUNDS": "Fed Funds Rate",
                    "INDPRO": "Industrial Production",
                    "PAYEMS": "Nonfarm Payrolls"
                }
                
                for series_id, name in macro_series.items():
                    if series_id in bundle.data.columns:
                        series = bundle.data[series_id].dropna()
                        # Sample every 3 months to avoid bloating
                        series_sampled = series.iloc[::3]
                        
                        for date, value in series_sampled.items():
                            rag_store.add_series_fact(
                                series_id=series_id,
                                name=name,
                                value=float(value),
                                date=date.strftime("%Y-%m-%d")
                            )
            
            # 2. Price data (5 years, weekly samples)
            if seed_prices:
                from core.market_data import get_price_history
                
                for ticker in universe:
                    try:
                        df = get_price_history(ticker, start=(datetime.utcnow() - timedelta(days=365*5)).strftime("%Y-%m-%d"), interval="1wk")
                        if df is not None and not df.empty:
                            for date, row in df.iterrows():
                                rag_store.add_series_fact(
                                    series_id=f"{ticker}_CLOSE",
                                    name=f"{ticker} Weekly Close",
                                    value=float(row["Close"]),
                                    date=date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                                )
                    except Exception as e:
                        continue
            
            # 3. Recent news (top 100 from last week)
            if seed_news:
                from ingestion.finnews import run_pipeline
                
                items = run_pipeline(
                    regions=["US", "CA", "INTL"],
                    window="last_week",
                    query="",
                    tgt_ticker=None,
                    per_source_cap=None,
                    limit=100
                )
                
                # Only inject if score > 0.5
                for item in items:
                    if item.get("score", 0) > 0.5:
                        rag_store.add_news_item(item)
            
            stats_after = rag_store.stats()
            
            return _ok({
                "stats_before": stats_before,
                "stats_after": stats_after,
                "added": {
                    "news": stats_after.get("news_count", 0) - stats_before.get("news_count", 0),
                    "facts": stats_after.get("facts_count", 0) - stats_before.get("facts_count", 0)
                },
                "message": "RAG seeded successfully"
            })
        
        except Exception as e:
            return _ok({
                "error": str(e),
                "message": "Failed to seed RAG"
            })

    # ====================== CORRELATIONS =======================
    
    @app.get("/api/correlations/matrix")
    async def correlations_matrix():
        """Get correlation matrix for tickers."""
        try:
            from src.services.correlation_service import get_correlation_matrix
            matrix_data = get_correlation_matrix()
            return _ok({
                "data": matrix_data,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            logger.error(f"Error in correlations_matrix: {e}", exc_info=True)
            return _ok({
                "data": {"matrix": {}, "tickers": [], "lookback_days": 90},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })
    
    @app.get("/api/correlations/network")
    async def correlations_network(threshold: float = Query(0.5, ge=0.0, le=1.0, description="Correlation threshold")):
        """Get correlation network (nodes + links) for visualization."""
        try:
            from src.services.correlation_service import get_correlation_network
            network_data = get_correlation_network(threshold=threshold)
            return _ok({
                "data": network_data,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            logger.error(f"Error in correlations_network: {e}", exc_info=True)
            return _ok({
                "data": {"nodes": [], "links": [], "threshold": threshold},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })
    
    # ====================== SECTORS =======================
    
    @app.get("/api/stocks/sectors")
    async def stocks_sectors():
        """Get sector allocation data for SectorWheel/TreemapChart."""
        try:
            # Try to load from storage
            backend_root = Path(__file__).resolve().parents[2]
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))
            
            try:
                from storage.io import load_json
            except ImportError:
                from storage.base import load_json
            
            sectors_data = load_json("stocks/sectors")
            
            if sectors_data:
                # Extract data if wrapped
                if "data" in sectors_data:
                    data = sectors_data["data"]
                elif "payload" in sectors_data:
                    data = sectors_data["payload"]
                else:
                    data = sectors_data
            else:
                data = {"sectors": [], "total_tickers": 0, "total_sectors": 0}
            
            return _ok({
                "data": data,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            logger.error(f"Error in stocks_sectors: {e}", exc_info=True)
            return _ok({
                "data": {"sectors": [], "total_tickers": 0, "total_sectors": 0},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })
    
    # ====================== EFFICIENT FRONTIER =======================
    
    @app.get("/api/backtests/efficient_frontier")
    async def efficient_frontier():
        """Get efficient frontier data for portfolio optimization."""
        try:
            # Try to load from storage
            backend_root = Path(__file__).resolve().parents[2]
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))
            
            try:
                from storage.io import load_json
            except ImportError:
                from storage.base import load_json
            
            frontier_data = load_json("backtests/efficient_frontier")
            
            if frontier_data:
                # Extract data if wrapped
                if "data" in frontier_data:
                    data = frontier_data["data"]
                elif "payload" in frontier_data:
                    data = frontier_data["payload"]
                else:
                    data = frontier_data
            else:
                data = {"frontier": [], "tickers": [], "lookback_days": 252}
            
            return _ok({
                "data": data,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            logger.error(f"Error in efficient_frontier: {e}", exc_info=True)
            return _ok({
                "data": {"frontier": [], "tickers": [], "lookback_days": 252},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })
    
    # ====================== CAPITAL FLOWS =======================
    
    @app.get("/api/flows/capital")
    async def capital_flows():
        """Get capital flows data for SankeyDiagram."""
        try:
            from src.services.flows_service import get_capital_flows
            flows_data = get_capital_flows()
            return _ok({
                "data": flows_data,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            logger.error(f"Error in capital_flows: {e}", exc_info=True)
            return _ok({
                "data": {"nodes": [], "links": [], "lookback_days": 30},
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })
    
    # ====================== ORDERBOOK =======================
    
    @app.get("/api/orderbook")
    async def orderbook(ticker: str = Query(..., description="Stock ticker symbol")):
        """Get orderbook data (bids/asks) for a ticker."""
        try:
            from src.services.market_microstructure import get_orderbook
            orderbook_data = get_orderbook(ticker.upper())
            return _ok({
                "data": orderbook_data,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            })
        except Exception as e:
            logger.error(f"Error in orderbook: {e}", exc_info=True)
            return _ok({
                "data": {
                    "ticker": ticker.upper(),
                    "bids": [],
                    "asks": [],
                    "lastPrice": 0.0,
                    "spread": 0.0,
                    "spreadPct": 0.0,
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })
    
    @app.get("/api/rag/stats")
    async def rag_stats():
        """Get RAG store statistics."""
        try:
            from research.rag_store import RAGStore
            rag_store = RAGStore()
            stats = rag_store.freshness_stats()  # Use the new freshness_stats method
            
            # Add general stats
            general_stats = rag_store.stats()
            stats.update(general_stats)
            
            return _ok({
                "stats": stats,
                "generated_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            return _ok({
                "error": str(e),
                "stats": {}
            })

# ================================= SERVER ====================================

def run_server(host: str = "127.0.0.1", port: int = 8050):
    """Run the FastAPI server."""
    import uvicorn
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    run_server()
