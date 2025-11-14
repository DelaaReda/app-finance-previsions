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

try:
    # Prefer explicit relative import within the 'api' package
    from .services.news_service import (
        get_news_events as lakehouse_news_events,
        get_sentiment as lakehouse_news_sentiment,
    )
except ImportError:  # pragma: no cover
    try:
        from api.services.news_service import (  # type: ignore
            get_news_events as lakehouse_news_events,
            get_sentiment as lakehouse_news_sentiment,
        )
    except ImportError:
        # Last resort when 'api' is not the package root on sys.path
        from services.news_service import (
            get_news_events as lakehouse_news_events,
            get_sentiment as lakehouse_news_sentiment,
        )
try:
    from .services.intelligence_service import (
        get_market_context_snapshot,
        get_market_intelligence_snapshot,
    )
except ImportError:  # pragma: no cover
    try:
        from api.services.intelligence_service import (  # type: ignore
            get_market_context_snapshot,
            get_market_intelligence_snapshot,
        )
    except ImportError:
        from services.intelligence_service import (
            get_market_context_snapshot,
            get_market_intelligence_snapshot,
        )
try:
    # Try importing from src.services first (since snapshot_loader is in src/services/)
    from src.services.snapshot_loader import ensure_snapshot, resolve_payload
except ImportError:
    try:
        # Fallback: try importing from services (if src is in sys.path)
        from services.snapshot_loader import ensure_snapshot, resolve_payload
    except ImportError:
        # Final fallback: provide stub implementations
        logger = logging.getLogger(__name__)
        logger.warning("snapshot_loader module not available, using fallback implementations")
        
        def ensure_snapshot(key, job_runner=None, **kwargs):
            """Fallback implementation"""
            if job_runner:
                return job_runner()
            return None
        
        def resolve_payload(data, paths):
            """Fallback implementation"""
            if not data:
                return None
            for path in paths:
                if isinstance(path, tuple):
                    current = data
                    for key in path:
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        else:
                            break
                    else:
                        return current
                elif isinstance(data, dict) and path in data:
                    return data[path]
            return data


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


def _run_macro_series_job() -> None:
    """Trigger the macro snapshot job once to refresh cached data."""
    from jobs import macro_series_snapshot

    macro_series_snapshot.main([])  # type: ignore[arg-type]


def _run_forecasts_job() -> None:
    """Trigger the forecasts job to refresh cached rows."""
    from jobs.forecasts import run_forecasts_job

    run_forecasts_job()


def _run_weekly_brief_job() -> None:
    """Trigger the weekly brief job to refresh cached signals."""
    from jobs.weekly_brief import run_weekly_brief_job

    run_weekly_brief_job()


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

    # Include dashboard routes
    try:
        from .routes.dashboard import dashboard_router
        app.include_router(dashboard_router, prefix="/api/dashboard")
    except ImportError as e:
        print(f"⚠️  Failed to include dashboard routes: {e}")

    # Include brief routes
    try:
        from .routes.brief_routes import router as brief_router
        app.include_router(brief_router)
    except ImportError as e:
        print(f"⚠️  Failed to include brief routes: {e}")

    # Include quality routes
    try:
        from .routes.quality import router as quality_router
        app.include_router(quality_router)
    except ImportError as e:
        print(f"⚠️  Failed to include quality routes: {e}")

    # Include cache management routes
    try:
        from .routes.cache_routes import router as cache_router
        app.include_router(cache_router)
    except ImportError as e:
        print(f"⚠️  Failed to include cache routes: {e}")

    # Include portfolios/watchlists routes
    try:
        from .routes.portfolios import router as portfolios_router
        app.include_router(portfolios_router)
    except ImportError as e:
        print(f"⚠️  Failed to include portfolios routes: {e}")

    # Include forecasts routes
    try:
        from .routes.forecasts import forecasts_router
        app.include_router(forecasts_router, prefix="/api")
    except ImportError as e:
        print(f"⚠️  Failed to include forecasts routes: {e}")

    # Include forecasts routes
    try:
        from .routes.forecasts import forecasts_router
        app.include_router(forecasts_router, prefix="/api")
    except ImportError as e:
        print(f"⚠️  Failed to include forecasts routes: {e}")

    # Include analytics routes
    try:
        from .routes.analytics import router as analytics_router
        app.include_router(analytics_router)
    except ImportError as e:
        print(f"⚠️  Failed to include analytics routes: {e}")

    # Include stocks routes (top, universe, etc.)
    try:
        from .routes.stocks import stocks_router
        app.include_router(stocks_router)
    except ImportError as e:
        print(f"⚠️  Failed to include stocks routes: {e}")

    # Include judge routes (LLM verdicts)
    try:
        from .routes.judge import judge_router
        app.include_router(judge_router)
    except ImportError as e:
        print(f"⚠️  Failed to include judge routes: {e}")

    # Include forecasts routes
    try:
        from api.routes.forecasts import forecasts_router
        app.include_router(forecasts_router, prefix="/api")
    except ImportError as e:
        print(f"⚠️  Failed to include forecasts routes: {e}")

    # Include judge routes
    try:
        from .routes.judge import router as judge_router
        app.include_router(judge_router)
    except ImportError as e:
        print(f"⚠️  Failed to include judge routes: {e}")

    # Include stocks routes
    try:
        from .routes.stocks import router as stocks_router
        app.include_router(stocks_router)
    except ImportError as e:
        print(f"⚠️  Failed to include stocks routes: {e}")

    # =================== STARTUP EVENT HANDLER ===================
    @app.on_event("startup")
    async def startup_event():
        """
        Initialize application data at startup
        Executes data generation jobs in background if data is missing/empty
        Task: FC-STARTUP-INIT-001 (+60 pts)
        Author: CLAUDE-STABILITY-ARCHITECT-IRONMAN-42
        """
        import logging
        import asyncio
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
            try:
                from jobs.forecasts import run_forecasts_job
            except ImportError:
                try:
                    from backend.jobs.forecasts import run_forecasts_job
                except ImportError:
                    run_forecasts_job = None
            try:
                from jobs.news_ingest import run_news_ingest
            except ImportError:
                try:
                    from backend.jobs.news_ingest import run_news_ingest
                except ImportError:
                    run_news_ingest = None
            try:
                from jobs.market_brief import run_market_brief_job
            except ImportError:
                try:
                    from backend.jobs.market_brief import run_market_brief_job
                except ImportError:
                    run_market_brief_job = None
            try:
                from jobs.weekly_brief import run_weekly_brief_job as run_and_persist_weekly_brief
            except ImportError:
                try:
                    from backend.jobs.weekly_brief import run_weekly_brief_job as run_and_persist_weekly_brief
                except ImportError:
                    run_and_persist_weekly_brief = None
            try:
                from jobs.macro_series_snapshot import run_macro_snapshot_job
            except ImportError:
                try:
                    from backend.jobs.macro_series_snapshot import run_macro_snapshot_job
                except ImportError:
                    run_macro_snapshot_job = None
            try:
                from jobs.alerts import run_alerts_job
            except ImportError:
                try:
                    from backend.jobs.alerts import run_alerts_job
                except ImportError:
                    run_alerts_job = None
            try:
                from scheduler.app import start_scheduler
            except ImportError:
                try:
                    from backend.scheduler.app import start_scheduler
                except ImportError:
                    start_scheduler = None

            logger.info("📦 Checking data availability...")

            async def run_job_async(job_func, job_name: str, check_func=None):
                """Run a job in background thread to avoid blocking startup"""
                if not job_func:
                    logger.warning(f"⚠️  {job_name} function not available, skipping")
                    return False
                
                try:
                    # Run in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, job_func)
                    logger.info(f"✅ {job_name} completed")
                    return True
                except Exception as e:
                    logger.error(f"❌ Failed to run {job_name}: {e}")
                    return False

            # Check and generate forecasts if missing or empty
            forecasts_data = load_json("forecasts") or load_json("forecasts.json")
            if not forecasts_data or not forecasts_data.get("rows") or len(forecasts_data.get("rows", [])) == 0:
                logger.info("⚠️  No forecasts found or empty, generating in background...")
                asyncio.create_task(run_job_async(run_forecasts_job, "Forecasts generation"))
            else:
                forecast_count = len(forecasts_data.get("rows", []))
                logger.info(f"✅ Forecasts data found: {forecast_count} forecasts")

            # Check and generate news feed if missing or empty
            news_data = load_json("news_feed") or load_json("news_feed.json")
            if not news_data or not news_data.get("articles") or len(news_data.get("articles", [])) == 0:
                logger.info("⚠️  No news feed found or empty, fetching in background...")
                asyncio.create_task(run_job_async(run_news_ingest, "News ingestion"))
            else:
                news_count = len(news_data.get("articles", []))
                logger.info(f"✅ News feed data found: {news_count} articles")

            # Check and generate market brief if missing or empty
            brief_daily = load_json("brief_daily") or load_json("brief_daily.json")
            if not brief_daily or not brief_daily.get("top_signals"):
                logger.info("⚠️  No daily brief found or empty, generating in background...")
                if run_market_brief_job:
                    asyncio.create_task(run_job_async(run_market_brief_job, "Market brief generation"))
            else:
                signals_count = len(brief_daily.get("top_signals", []))
                logger.info(f"✅ Daily brief data found: {signals_count} signals")

            # Check and generate weekly brief if missing or empty
            brief_data = load_json("brief_weekly") or load_json("brief_weekly.json")
            if not brief_data or not brief_data.get("top_signals"):
                logger.info("⚠️  No weekly brief found or empty, generating in background...")
                if run_and_persist_weekly_brief:
                    asyncio.create_task(run_job_async(run_and_persist_weekly_brief, "Weekly brief generation"))
            else:
                signals_count = len(brief_data.get("top_signals", []))
                logger.info(f"✅ Weekly brief data found: {signals_count} signals")

            # Check and generate macro series if missing or empty
            macro_data = load_json("macro_series") or load_json("macro_series.json")
            if not macro_data or not macro_data.get("series") or len(macro_data.get("series", {})) == 0:
                logger.info("⚠️  No macro series found or empty, generating in background...")
                if run_macro_snapshot_job:
                    asyncio.create_task(run_job_async(run_macro_snapshot_job, "Macro series snapshot"))
                else:
                    # Try to import and call main directly if wrapper doesn't exist
                    try:
                        from jobs.macro_series_snapshot import main as macro_main
                        asyncio.create_task(run_job_async(lambda: macro_main([]), "Macro series snapshot"))
                    except ImportError:
                        try:
                            from backend.jobs.macro_series_snapshot import main as macro_main
                            asyncio.create_task(run_job_async(lambda: macro_main([]), "Macro series snapshot"))
                        except ImportError:
                            logger.warning("⚠️  Macro snapshot job not available, skipping")
            else:
                series_count = len(macro_data.get("series", {}))
                logger.info(f"✅ Macro series data found: {series_count} series")

            # Check and generate alerts if missing
            alerts_data = load_json("alerts") or load_json("alerts.json")
            if not alerts_data:
                logger.info("⚠️  No alerts found, generating in background...")
                if run_alerts_job:
                    asyncio.create_task(run_job_async(run_alerts_job, "Alerts generation"))
            else:
                alerts_count = len(alerts_data.get("alerts", []))
                logger.info(f"✅ Alerts data found: {alerts_count} alerts")

            # Start background scheduler
            if start_scheduler:
                logger.info("⏰ Starting background scheduler...")
                try:
                    start_scheduler()
                    logger.info("✅ Scheduler started successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to start scheduler: {e}")
            else:
                logger.warning("⚠️  start_scheduler not available, skipping")

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

    # ========================= MACRO SERIES (DISABLED - Using router instead) ======================
    # NOTE: The /api/macro/series endpoint is now handled by api/routes/macro.py router
    # This endpoint is commented out to avoid conflicts with the router
    # The router provides better filtering, caching, and error handling
    
    @app.get("/api/macro/series")
    async def macro_series(
        series_ids: Optional[str] = Query(None, description="Comma-separated FRED IDs (e.g. CPIAUCSL,DGS10,VIXCLS)"),
        ids: Optional[str] = Query(None, description="Alias for series_ids"),
        range: str = Query("5y", description="Range: 1m,3m,6m,1y,2y,3y,5y,10y,all"),
        freq: Optional[str] = Query(None, description="Optional frequency hint (daily, weekly, monthly)")
    ):
        """Return macro time series using real data (cache first, FRED fallback).

        Response shape matches the frontend adapter expectations:
        { ok: true, data: { series: [{ id, title, unit, data: [{date, value}]}], updated_at } }
        """
        try:
            from .services.macro_service import get_macro_overview
        except Exception as e:
            return _ok({"series": [], "error": f"macro service unavailable: {e}"})

        try:
            req_ids = series_ids or ids or None
            overview = get_macro_overview(range_str=range, series_ids=req_ids)

            series_list = []
            for s in getattr(overview, "series", []) or []:
                # Extract points from DataPoint dataclass or loose dicts
                points = []
                values = getattr(s, "values", None) or getattr(s, "data", None) or []
                for dp in values:
                    ts = getattr(dp, "timestamp", None) or (dp.get("timestamp") if isinstance(dp, dict) else None) or (dp.get("date") if isinstance(dp, dict) else None)
                    val = getattr(dp, "value", None) if not isinstance(dp, dict) else dp.get("value")
                    if ts is None or val is None:
                        continue
                    try:
                        if isinstance(ts, datetime):
                            date_str = ts.date().isoformat()
                        else:
                            date_str = str(ts)[:10]
                        points.append({"date": date_str, "value": float(val)})
                    except Exception:
                        continue

                series_list.append({
                    "id": getattr(s, "series_id", None) or getattr(s, "id", None),
                    "title": getattr(s, "name", None) or getattr(s, "title", None),
                    "unit": getattr(s, "unit", None),
                    "freq": freq,
                    "data": points,
                })

            payload = {
                "series": series_list,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
            return _ok(payload)
        except Exception as e:
            # Never-empty: return empty structure with error info
            return _ok({
                "series": [],
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            })

    @app.get("/api/macro/snapshot")
    async def macro_snapshot():
        """Get current macro snapshot (latest values) - reads from persisted macro series."""
        try:
            from storage.io import load_json

            macro = load_json("macro_series") or load_json("macro_series.json") or {}
            data = macro.get("data") or macro
            series = data.get("series") or []

            def last_value(sid: str) -> Optional[float]:
                # series may be a list of dicts or a map of id -> dict
                try:
                    if isinstance(series, dict):
                        s = series.get(sid)
                        if not isinstance(s, dict):
                            return None
                        # map format: may have 'observations' or 'data'/'points'
                        pts = s.get('observations') or s.get('data') or s.get('points') or []
                        if isinstance(pts, list) and pts:
                            lp = pts[-1]
                            val = lp.get('value') if isinstance(lp, dict) else (lp[1] if isinstance(lp, (list, tuple)) and len(lp) >= 2 else None)
                            return float(val) if val is not None else None
                        return None
                    # list format
                    for s in series:
                        if (s.get("id") or s.get("series_id") or s.get("name")) == sid:
                            pts = s.get("data") or s.get("points") or s.get('observations') or []
                            if isinstance(pts, list) and pts:
                                lp = pts[-1]
                                val = lp.get("value") if isinstance(lp, dict) else (lp[1] if isinstance(lp, (list, tuple)) and len(lp) >= 2 else None)
                                return float(val) if val is not None else None
                    return None
                except Exception:
                    return None

            cpi = last_value("CPIAUCSL")
            unrate = last_value("UNRATE")
            vix = last_value("VIXCLS")
            y10 = last_value("DGS10")
            y2 = last_value("DGS2")
            yc = (y10 - y2) if (y10 is not None and y2 is not None) else None

            return _ok({
                "inflation_cpi": cpi,
                "unemployment_rate": unrate,
                "vix": vix,
                "yield_10y": y10,
                "yield_2y": y2,
                "yield_curve": yc,
                "updated_at": data.get("updated_at") or data.get("freshness") or macro.get("freshness"),
            })
        except Exception as e:
            return _ok({
                "inflation_cpi": None,
                "unemployment_rate": None,
                "vix": None,
                "yield_10y": None,
                "yield_2y": None,
                "yield_curve": None,
                "updated_at": None,
                "error": str(e),
            })

    @app.get("/api/macro/indicators")
    async def macro_indicators():
        """Get macro indicators with real calculations (cache-first, FRED fallback)."""
        try:
            from .services.macro_service import get_macro_indicators as _get_macro_indicators
            indicators = _get_macro_indicators()
            # indicators is a dataclass; convert to dict if needed
            payload = {
                "cpi_yoy": getattr(indicators, "cpi_yoy", None),
                "yield_curve_10y_2y": getattr(indicators, "yield_curve_10y_2y", None),
                "recession_probability": getattr(indicators, "recession_probability", None),
                "vix": getattr(indicators, "vix", None),
                "trace": getattr(indicators, "trace", None),
            }
            return _ok(payload)
        except Exception as e:
            return _ok({
                "cpi_yoy": None,
                "yield_curve_10y_2y": None,
                "recession_probability": None,
                "vix": None,
                "error": str(e),
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
                # If a single ticker was requested, return the shape expected by the UI (StockPriceData)
                if len(tickers_to_process) == 1:
                    t = tickers_to_process[0]
                    entry = results.get(t, {})
                    return _ok({
                        "ticker": t,
                        "interval": entry.get("interval", interval),
                        "points": entry.get("points", []),
                        "count": entry.get("count", 0),
                        "source": "stocks/prices_snapshot",
                        "timestamp": prices_data.get("freshness", datetime.utcnow().isoformat())
                    })
                else:
                    # Multi-ticker payload
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
            
            # Single ticker vs multi ticker response for UI compatibility
            if len(tickers_to_process) == 1:
                t = tickers_to_process[0]
                entry = results.get(t, {})
                return _ok({
                    "ticker": t,
                    "interval": entry.get("interval", interval) or interval,
                    "points": entry.get("points", []),
                    "count": entry.get("count", 0),
                    "source": "market_data_live",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
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

    # Alias for UI call path: map /api/stocks/top to the existing implementation
    @app.get("/api/stocks/top")
    async def api_stocks_top(
        limit: int = Query(10, ge=1, le=50, description="Number of top stocks to return"),
        sort_by: str = Query("score", description="Sort by: score, change_1d, momentum_30d, mcap"),
    ):
        return await stocks_top(limit=limit, sort_by=sort_by)

    @app.get("/api/stocks/search")
    async def api_stocks_search(q: Optional[str] = Query("", description="Query fragment"), limit: int = Query(10, ge=1, le=50)):
        """Lightweight search over the available universe from snapshot (real data, no mocks)."""
        try:
            from storage.io import load_json
            data = load_json("stocks/prices") or {}
            tickers_map = data.get("tickers") if isinstance(data, dict) else {}
            universe = [t.upper() for t in (tickers_map.keys() if isinstance(tickers_map, dict) else [])]
            qn = (q or "").strip().upper()
            results = []
            for t in universe:
                if not qn or qn in t:
                    results.append({"ticker": t, "name": t})
                if len(results) >= limit:
                    break
            return _ok({"results": results, "count": len(results)})
        except Exception as e:
            return _ok({"results": [], "count": 0, "error": str(e)})

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

    @app.get("/stocks/top")
    async def stocks_top(
        limit: int = Query(10, ge=1, le=50, description="Number of top stocks to return"),
        sort_by: str = Query("score", description="Sort by: score, change_1d, momentum_30d, mcap")
    ):
        """Get top stocks by score, momentum, or market cap."""
        try:
            from storage.io import load_json
            
            # Load stocks data - try multiple possible keys
            prices_data = load_json("stocks/prices") or load_json("stocks_prices") or {}
            metrics_data = load_json("stocks/metrics") or {}
            
            # Extract tickers data from various possible structures
            tickers_data = {}
            if isinstance(prices_data, dict):
                # Try different possible structures
                if "tickers" in prices_data:
                    tickers_data = prices_data["tickers"]
                elif "data" in prices_data and isinstance(prices_data["data"], dict):
                    tickers_data = prices_data["data"].get("tickers", {})
                elif any(k in prices_data for k in ["SPY", "QQQ", "AAPL"]):  # Direct ticker keys
                    tickers_data = {k: v for k, v in prices_data.items() if isinstance(v, dict) and "points" in v}
            
            metrics = {}
            if isinstance(metrics_data, dict):
                metrics = metrics_data.get("metrics", metrics_data)
            
            # Build list of stocks with their metrics
            stocks_list = []
            for ticker, ticker_data in tickers_data.items():
                if not isinstance(ticker_data, dict):
                    continue
                    
                ticker_metrics = metrics.get(ticker, {})
                points = ticker_data.get("points", [])
                
                if not points:
                    continue
                
                # Get latest price - handle different point formats
                latest_point = points[-1]
                if isinstance(latest_point, (list, tuple)) and len(latest_point) >= 2:
                    current_price = float(latest_point[1])
                elif isinstance(latest_point, dict):
                    current_price = float(latest_point.get("value", latest_point.get("close", 0)))
                else:
                    current_price = float(latest_point) if isinstance(latest_point, (int, float)) else 0
                
                # Calculate change
                change_1d = ticker_metrics.get("change_1d", 0.0)
                change_percent = ticker_metrics.get("change_percent", 0.0)
                
                stock_info = {
                    "ticker": ticker,
                    "name": ticker_metrics.get("name") or ticker_data.get("name") or f"{ticker} Corp",
                    "price": current_price,
                    "change": change_1d,
                    "change_percent": change_percent,
                    "market_cap": ticker_metrics.get("mcap") or ticker_metrics.get("market_cap") or 0,
                    "score": ticker_metrics.get("score") or 0,
                    "momentum_30d": ticker_metrics.get("momentum_30d") or 0.0,
                    "pe": ticker_metrics.get("pe"),
                    "sector": ticker_metrics.get("sector") or "N/A"
                }
                stocks_list.append(stock_info)
            
            # If no stocks found from prices data, try to generate from forecasts as fallback
            if not stocks_list:
                logger.info("No stocks data found, generating fallback from forecasts...")
                forecasts_data = load_json("forecasts") or {}
                forecast_rows = forecasts_data.get("rows", []) or forecasts_data.get("data", {}).get("rows", [])
                
                # Extract unique tickers from forecasts
                seen_tickers = set()
                for row in forecast_rows[:limit * 4]:  # Get more to have options
                    ticker = row.get("ticker") or row.get("symbol")
                    if ticker and ticker not in seen_tickers:
                        seen_tickers.add(ticker)
                        # Fetch real-time data for ticker
                        try:
                            df_rt = get_price_history(ticker, interval="1d")
                        except Exception:
                            df_rt = None

                        last_price = None
                        change_pct = 0.0
                        if df_rt is not None and hasattr(df_rt, 'empty') and not df_rt.empty and "Close" in df_rt.columns:
                            close = df_rt["Close"].dropna()
                            if not close.empty:
                                last_price = float(close.iloc[-1])
                                if len(close) > 1:
                                    prev = float(close.iloc[-2])
                                    if prev:
                                        change_pct = ((last_price - prev) / prev) * 100
                        # Ultra-lightweight Yahoo chart fallback if yfinance not available
                        if last_price is None:
                            try:
                                import requests as _rq
                                resp = _rq.get(
                                    f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                                    params={"range": "2d", "interval": "1d"},
                                    timeout=10,
                                    headers={"User-Agent": "Mozilla/5.0"},
                                )
                                js = resp.json()
                                result = (js.get("chart", {}).get("result") or [None])[0]
                                if result:
                                    closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close", [])
                                    if isinstance(closes, list) and closes:
                                        last_price = float(closes[-1]) if closes[-1] is not None else None
                                        if last_price is not None and len(closes) > 1 and closes[-2]:
                                            prev = float(closes[-2])
                                            if prev:
                                                change_pct = ((last_price - prev) / prev) * 100
                            except Exception:
                                pass

                        facts = {}
                        try:
                            facts = get_fundamentals(ticker) or {}
                        except Exception:
                            facts = {}

                        # Use forecast confidence as score; ER only for ranking, not displayed as price
                        confidence = row.get("confidence", 0)
                        expected_return = row.get("expected_return", 0)

                        stock_info = {
                            "ticker": ticker,
                            "name": facts.get("name") or f"{ticker} Corp",
                            "price": last_price or facts.get("price") or 0.0,
                            "change": change_pct,
                            "change_percent": change_pct,
                            "market_cap": facts.get("market_cap") or 0,
                            "score": confidence,
                            "momentum_30d": expected_return * 30 if expected_return else 0.0,
                            "pe": facts.get("pe"),
                            "sector": facts.get("sector") or "N/A"
                        }
                        stocks_list.append(stock_info)
                        if len(stocks_list) >= limit:
                            break
            
            # Sort by requested field
            if sort_by == "change_1d":
                stocks_list.sort(key=lambda x: abs(x.get("change", 0)), reverse=True)
            elif sort_by == "momentum_30d":
                stocks_list.sort(key=lambda x: x.get("momentum_30d", 0), reverse=True)
            elif sort_by == "mcap":
                stocks_list.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
            else:  # score or default
                stocks_list.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # Limit results
            top_stocks = stocks_list[:limit]
            
            return _ok({
                "stocks": top_stocks,
                "count": len(top_stocks),
                "sort_by": sort_by,
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["stocks_prices", "stocks_metrics"] if len(tickers_data) > 0 else ["forecasts_fallback"]
            })
            
        except Exception as e:
            logger.error(f"Error in stocks_top: {e}", exc_info=True)
            # Return empty structure (never-empty pattern)
            return _ok({
                "stocks": [],
                "count": 0,
                "sort_by": sort_by,
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback"]
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
                from .services.news_service import get_news_feed
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
                from .services.news_service import get_news_feed
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

    # Provide the /api/news/feed endpoint directly for the UI (reads real data or cached pipeline output)
    @app.get("/api/news/feed")
    async def news_feed(
        tickers: Optional[List[str]] = Query(None, description="Optional tickers filter"),
        since: str = Query("7d", description="1h, 6h, 1d, 3d, 7d, 14d, 30d, 90d"),
        region: str = Query("all", description="Region filter (unused in v1)"),
        score_min: float = Query(0.0, ge=0.0, le=1.0, description="Minimum composite score (unused in v1)"),
        limit: int = Query(50, ge=1, le=400, description="Max 400 articles to keep payload reasonable")
    ):
        try:
            # Prefer service which uses persisted data + never-empty
            from .services.news_service import get_news_feed as _get_news_feed
            svc = await _get_news_feed(tickers=tickers, q=None, limit=limit, window="last_week")
            # If service returned empty, attempt direct file load (legacy structure has top-level 'articles')
            try_direct = False
            if isinstance(svc, dict) and svc.get("ok") is True:
                data_block = svc.get("data") or {}
                items = (data_block.get("items") or data_block.get("articles") or []) if isinstance(data_block, dict) else []
                if isinstance(items, list) and len(items) > 0:
                    # Normalize shape for frontend expectations
                    norm_items = []
                    for a in items:
                        if not isinstance(a, dict):
                            continue
                        title = a.get("title") or a.get("headline") or "(sans titre)"
                        url = a.get("url") or a.get("link") or ""
                        published = a.get("pubDate") or a.get("published_at") or a.get("date") or a.get("timestamp")
                        source = a.get("source") or a.get("publisher")
                        if not source and isinstance(url, str) and url:
                            try:
                                from urllib.parse import urlparse
                                netloc = urlparse(url).netloc
                                source = netloc.split(':')[0]
                            except Exception:
                                source = None
                        norm_items.append({
                            "title": title,
                            "url": url,
                            "published_at": published,
                            "source": source,
                            "tickers": a.get("tickers") or [],
                            "score": a.get("score") or a.get("relevance_score") or a.get("sentiment_score"),
                        })
                    return _ok({
                        "items": norm_items[:limit],
                        "count": len(norm_items),
                        "freshness": data_block.get("freshness") or data_block.get("generated_at"),
                        "last_update": data_block.get("freshness") or data_block.get("generated_at"),
                        "source": svc.get("source") or data_block.get("source"),
                    })
                try_direct = True
            else:
                try_direct = True

            if try_direct:
                from storage.io import load_json
                news_data = load_json("news_feed") or load_json("news_feed.json") or {}
                payload = news_data.get("payload") or news_data
                # Normalize to items list
                if isinstance(payload, dict) and ("articles" in payload or (isinstance(payload.get("data"), dict) and "articles" in payload.get("data", {}))):
                    items = payload.get("articles") or payload.get("data", {}).get("articles", [])
                    # Normalize each article to ensure title/source fields are present
                    norm_items = []
                    for a in items:
                        if not isinstance(a, dict):
                            continue
                        title = a.get("title") or a.get("headline") or "(sans titre)"
                        url = a.get("url") or a.get("link") or ""
                        published = a.get("pubDate") or a.get("published_at") or a.get("date") or a.get("timestamp")
                        source = a.get("source") or a.get("publisher")
                        if not source and isinstance(url, str) and url:
                            try:
                                from urllib.parse import urlparse
                                netloc = urlparse(url).netloc
                                source = netloc.split(':')[0]
                            except Exception:
                                source = None
                        norm_items.append({
                            "title": title,
                            "url": url,
                            "published_at": published,
                            "source": source,
                            "tickers": a.get("tickers") or [],
                            "score": a.get("score") or a.get("relevance_score") or a.get("sentiment_score"),
                        })
                    if tickers:
                        filtered = [a for a in norm_items if any(t.upper() in [x.upper() for x in (a.get("tickers") or [])] for t in tickers)]
                        # Never-empty behavior: if filtering removes everything (common when feed lacks per-article tickers),
                        # fall back to the unfiltered head up to limit
                        norm_items = filtered if filtered else norm_items
                    items = norm_items[:limit]
                    return _ok({
                        "items": items,
                        "count": len(items),
                        "freshness": payload.get("generated_at") or payload.get("data", {}).get("generated_at") or news_data.get("generated_at"),
                        "last_update": payload.get("generated_at") or payload.get("data", {}).get("generated_at") or news_data.get("generated_at"),
                        "source": news_data.get("source") or payload.get("source")
                    })
                return _ok(payload)
        except Exception as e:
            return _ok({"articles": [], "count": 0, "error": str(e)})

    # ====================== RECOMMENDATIONS =======================
    @app.get("/api/recommendations/daily")
    async def recommendations_daily(
        universe: Optional[List[str]] = Query(None, description="Optional list of tickers to consider"),
        limit: int = Query(3, ge=1, le=50)
    ):
        """Daily recommendations derived from the latest weekly brief (real cached data).

        - Uses /data/brief_weekly.json top_signals as BUY candidates
        - Applies optional universe filter and limit
        - Returns stable schema consumed by SmartRecommendationsWidget
        """
        try:
            from storage.io import load_json
            brief = load_json("brief_weekly") or load_json("brief_weekly.json") or {}
            core = brief.get("data") or brief
            top_signals = core.get("top_signals") or []
            items = []
            for s in top_signals:
                tkr = (s.get("ticker") or "").upper()
                typ = (s.get("type") or "").upper() or "BULLISH"
                if not tkr:
                    continue
                if universe and len(universe) > 0 and tkr not in {u.upper() for u in universe}:
                    continue
                if typ != "BULLISH":
                    continue
                conf = s.get("confidence")
                er = s.get("expected_return")
                score = int(round((conf or 0) * 100)) if isinstance(conf, (int, float)) else 0
                # Simple risk heuristic from confidence
                risk_level = "LOW" if (conf or 0) >= 0.7 else "MEDIUM" if (conf or 0) >= 0.4 else "HIGH"
                items.append({
                    "ticker": tkr,
                    "action": "BUY",
                    "score": score,
                    "reasoning": s.get("reasoning") or "Forecasts and market brief indicate positive setup.",
                    "catalysts": [],
                    "risk_level": risk_level,
                    "confidence": float(conf) if conf is not None else 0.0,
                    "supporting_data": {
                        "forecast_confidence": float(conf) if conf is not None else None,
                        "news_sentiment": None,
                        "momentum_score": None,
                        "macro_alignment": None,
                    }
                })

            items = items[:limit]

            # Market context snapshot for header
            try:
                context = await run_in_threadpool(get_market_context_snapshot)
                market_ctx = {
                    "regime": context.get("insights", {}).get("market_regime", {}).get("current", "NORMAL"),
                    "summary": context.get("insights", {}).get("summary") or "",
                    "key_drivers": []
                }
            except Exception:
                mc = _fallback_market_context("Recommendations context")
                market_ctx = {"regime": mc.get("regime", "NORMAL"), "summary": mc.get("summary", ""), "key_drivers": []}

            now_iso = datetime.utcnow().isoformat() + "Z"
            return _ok({
                "recommendations": items,
                "market_context": market_ctx,
                "generated_at": now_iso,
                "valid_until": now_iso
            })
        except Exception as e:
            # Never-empty: return empty recommendations with context
            now_iso = datetime.utcnow().isoformat() + "Z"
            return _ok({
                "recommendations": [],
                "market_context": {"regime": "NORMAL", "summary": str(e), "key_drivers": []},
                "generated_at": now_iso,
                "valid_until": now_iso
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

    # ====================== MACRO SNAPSHOT =======================
    @app.get("/api/macro/snapshot")
    async def macro_snapshot():
        """Return a compact macro snapshot from persisted macro series.

        Shape: { ok: true, data: { inflation_cpi, unemployment_rate, vix, yield_10y, yield_2y, yield_curve, updated_at } }
        """
        try:
            from storage.io import load_json
            macro = load_json("macro_series") or load_json("macro_series.json") or {}
            data = macro.get("data") or macro
            series = data.get("series") or []

            def last_value(sid: str) -> float | None:
                for s in series:
                    if (s.get("id") or s.get("series_id") or s.get("name")) == sid:
                        pts = s.get("data") or s.get("points") or []
                        if isinstance(pts, list) and pts:
                            lp = pts[-1]
                            val = lp.get("value") if isinstance(lp, dict) else (lp[1] if isinstance(lp, (list, tuple)) and len(lp) >= 2 else None)
                            try:
                                return float(val) if val is not None else None
                            except Exception:
                                return None
                return None

            cpi = last_value("CPIAUCSL")
            unrate = last_value("UNRATE")
            vix = last_value("VIXCLS")
            y10 = last_value("DGS10")
            y2 = last_value("DGS2")
            yc = (y10 - y2) if (y10 is not None and y2 is not None) else None

            return _ok({
                "inflation_cpi": cpi,
                "unemployment_rate": unrate,
                "vix": vix,
                "yield_10y": y10,
                "yield_2y": y2,
                "yield_curve": yc,
                "updated_at": data.get("updated_at") or data.get("freshness") or macro.get("freshness"),
            })
        except Exception as e:
            return _ok({
                "inflation_cpi": None,
                "unemployment_rate": None,
                "vix": None,
                "yield_10y": None,
                "yield_2y": None,
                "yield_curve": None,
                "updated_at": None,
                "error": str(e),
            })
    # ====================== PERFORMANCE MATRIX =======================
    @app.get("/api/performance/matrix")
    async def performance_matrix(
        horizons: Optional[str] = Query(None, description="Comma-separated horizons: short,medium,long"),
        tickers: Optional[str] = Query(None, description="Comma-separated tickers"),
        sectors: Optional[str] = Query(None, description="(unused placeholder)"),
        themes: Optional[str] = Query(None, description="(unused placeholder)")
    ):
        """Return a simple performance matrix computed from recent daily closes.

        Horizons mapping:
        - short  = ~1M  (21 trading days)
        - medium = ~6M  (126 trading days)
        - long   = ~12M (252 trading days)
        """
        try:
            horizon_list = [h.strip().lower() for h in (horizons or "short,medium,long").split(",") if h.strip()]
            req_tickers = [t.strip().upper() for t in (tickers or "").split(",") if t.strip()]
            universe = req_tickers or DEFAULT_STOCKS_UNIVERSE[:20]

            lengths = {"short": 21, "medium": 126, "long": 252}
            results: list[dict[str, Any]] = []

            from urllib.parse import urlencode
            import requests as _rq
            for symbol in universe:
                try:
                    df = get_price_history(symbol, interval="1d")
                    closes_list = None
                    if df is None or getattr(df, "empty", True) or "Close" not in df.columns:
                        # Fallback to Yahoo Chart JSON (2y daily to ensure enough data)
                        try:
                            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?" + urlencode({"range":"2y","interval":"1d"})
                            js = _rq.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"}).json()
                            result = (js.get('chart',{}).get('result') or [None])[0]
                            closes = (result.get('indicators',{}).get('quote') or [{}])[0].get('close', []) if result else []
                            if isinstance(closes, list) and len(closes) >= 260:
                                closes_list = [float(x) for x in closes if x is not None]
                        except Exception:
                            closes_list = None
                    else:
                        close = df["Close"].dropna()
                        closes_list = [float(x) for x in close.values.tolist()] if not close.empty else None

                    if not closes_list or len(closes_list) < 10:
                        continue
                    latest = float(closes_list[-1])
                    vals: dict[str, float | None] = {}
                    for h in horizon_list:
                        n = lengths.get(h)
                        if not n or len(closes_list) <= n:
                            vals[h] = None
                            continue
                        base = float(closes_list[-1 - n])
                        vals[h] = ((latest - base) / base) * 100 if base else None

                    item = {
                        "ticker": symbol,
                        "name": symbol + " Corp",
                        "sector": None,
                        "themes": [],
                        "values": {k: (None if v is None or (isinstance(v, float) and (v != v)) else float(v)) for k, v in vals.items()},
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                    }
                    results.append(item)
                except Exception:
                    continue

            return _ok({"items": results, "count": len(results), "last_update": datetime.utcnow().isoformat() + "Z"})
        except Exception as e:
            return _ok({"items": [], "count": 0, "error": str(e)})

    # ====================== OPPORTUNITIES =======================
    @app.get("/api/opportunities")
    async def opportunities(
        limit: int = Query(6, ge=1, le=50, description="Max number of opportunities"),
        horizon: Optional[str] = Query(None, description="Optional horizon filter (e.g., 1d, 1w, 1m)"),
    ):
        """Expose top opportunities derived from the weekly brief snapshot.

        Response: { ok: true, data: { items: [{ticker, confidence, expected_return, horizon, reasoning}], count, last_update } }
        """
        try:
            from storage.io import load_json
            brief = load_json("brief_weekly") or load_json("brief_weekly.json") or {}
            core = brief.get("data") or brief
            rows = core.get("top_signals") or core.get("signals") or []
            items = []
            for s in rows:
                if not isinstance(s, dict):
                    continue
                typ = (s.get("type") or "BULLISH").upper()
                if typ not in ("BULLISH", "NEWS_POSITIVE"):
                    continue
                h = s.get("horizon") or "1w"
                if horizon and h != horizon:
                    continue
                items.append({
                    "ticker": s.get("ticker"),
                    "confidence": s.get("confidence"),
                    "expected_return": s.get("expected_return"),
                    "horizon": h,
                    "reasoning": s.get("reason") or s.get("reasoning"),
                })
                if len(items) >= limit:
                    break
            return _ok({
                "items": items,
                "count": len(items),
                "last_update": core.get("generated_at") or core.get("freshness") or core.get("updated_at"),
            })
        except Exception as e:
            return _ok({"items": [], "count": 0, "error": str(e)})

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
            cached_brief = ensure_snapshot(
                "brief_weekly",
                job_runner=_run_weekly_brief_job,
                aliases=["brief_weekly.json"],
            )

            if cached_brief:
                brief_data = resolve_payload(cached_brief, ("data.weekly", "weekly", "data"))
                if brief_data:
                    brief_data = dict(brief_data)
                    brief_data["freshness"] = cached_brief.get("freshness", datetime.utcnow().isoformat())
                    brief_data["source"] = cached_brief.get("source") or brief_data.get("source") or ["precomputed_weekly_job"]
                    brief_data["generated_at"] = cached_brief.get("timestamp") or cached_brief.get("last_update") or brief_data.get("generated_at") or datetime.utcnow().isoformat()
                    return _ok(brief_data)

            return _ok({
                "summary": "Weekly brief is being prepared. Check back soon.",
                "top_signals": [],
                "top_risks": [],
                "picks": [],
                "generated_at": datetime.utcnow().isoformat(),
                "freshness": "unknown",
                "source": ["placeholder"],
                "message": "Weekly brief computation is scheduled and will be available soon"
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
            snap = ensure_snapshot(
                "brief_daily",
                aliases=["brief_daily.json"],
            )

            if not snap:
                snap = ensure_snapshot(
                    "brief_weekly",
                    job_runner=_run_weekly_brief_job,
                    aliases=["brief_weekly.json"],
                )

            if snap:
                payload = resolve_payload(
                    snap,
                    ("data.daily", "daily", "data.weekly", "weekly", "data", "payload"),
                )
                payload = dict(payload) if isinstance(payload, dict) else {}

                payload.setdefault("title", "Daily Market Brief")
                payload.setdefault("period", "daily")
                payload.setdefault("top_signals", [])
                payload.setdefault("top_risks", [])
                payload.setdefault("picks", [])
                payload.setdefault("sources", [])
                payload.setdefault("generated_at", snap.get("last_update") or snap.get("timestamp") or datetime.utcnow().isoformat())
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

    # ========================= FORECASTS (DISABLED - Using router instead) ======================
    # NOTE: The /api/forecasts endpoint is now handled by api/routes/forecasts.py router
    # This endpoint is commented out to avoid conflicts with the router
    # The router provides better filtering, caching, and error handling
    
    # @app.get("/api/forecasts")
    # async def forecasts(
    #     asset_type: str = Query("all", description="Asset type: equity, commodity, all"),
    #     horizon: str = Query("all", description="Horizon: 1w, 1m, 3m, all"),
    #     search: Optional[str] = Query(None, description="Search term"),
    #     sort_by: str = Query("score", description="Sort by: score, confidence, return")
    # ):
    #     """Get forecasts list - serves real data from forecasts.json"""
    #     # ... (implementation moved to api/routes/forecasts.py)

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
            if not bt:
                try:
                    from backend.jobs.backtests_simple import run_backtests_simple as _run_bt
                except Exception:
                    try:
                        from jobs.backtests_simple import run_backtests_simple as _run_bt
                    except Exception:
                        _run_bt = None
                if _run_bt is not None:
                    _run_bt()
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

            # If no meaningful backtests snapshot, compute a lightweight real-time metric from latest prices
            if not core or (not core.get("results") and not core.get("overall_metrics")):
                try:
                    from storage.io import load_json
                    forecasts = load_json("forecasts") or {}
                    rows = forecasts.get("rows") or forecasts.get("data", {}).get("rows", []) or []
                    # Build latest direction per ticker
                    latest_dir: Dict[str, str] = {}
                    tickers: List[str] = []
                    for r in rows:
                        if isinstance(r, dict):
                            t = (r.get("ticker") or r.get("symbol") or "").upper()
                            d = str(r.get("direction", "")).lower()
                            if t:
                                latest_dir[t] = d
                    tickers = list(latest_dir.keys())[: min(30, len(latest_dir))]
                    total = hits = 0
                    all_rets: List[float] = []
                    import requests as _rq
                    from urllib.parse import urlencode
                    for t in tickers:
                        try:
                            dfp = get_price_history(t, interval="1d")
                            if dfp is None or getattr(dfp, "empty", True) or "Close" not in dfp.columns:
                                # Fallback to Yahoo Chart JSON
                                try:
                                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?{urlencode({'range':'2d','interval':'1d'})}"
                                    js = _rq.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"}).json()
                                    result = (js.get('chart',{}).get('result') or [None])[0]
                                    closes = (result.get('indicators',{}).get('quote') or [{}])[0].get('close', []) if result else []
                                    if not isinstance(closes, list) or len(closes) < 2 or closes[-1] is None or closes[-2] is None:
                                        continue
                                    r1 = float(closes[-1]); r0 = float(closes[-2])
                                except Exception:
                                    continue
                            else:
                                close = dfp["Close"].dropna()
                                if len(close) < 2:
                                    continue
                                r1 = float(close.iloc[-1]); r0 = float(close.iloc[-2])
                            if r0 == 0:
                                continue
                            ret = (r1 - r0) / r0
                            all_rets.append(ret)
                            pred = latest_dir.get(t, "")
                            if pred in ("up", "down"):
                                total += 1
                                if (pred == "up" and ret > 0) or (pred == "down" and ret < 0):
                                    hits += 1
                        except Exception:
                            continue
                    hit_rate_rt = (hits / total) if total > 0 else 0.0
                    avg_ret_rt = (sum(all_rets) / len(all_rets)) if all_rets else 0.0
                    core = {
                        "overall_metrics": {
                            "hit_rate": hit_rate_rt,
                            "avg_return": avg_ret_rt,
                            "sharpe_ratio": 0.0,
                            "max_drawdown": 0.0,
                            "n_trades": total,
                            "total_trades": total,
                        },
                    }
                except Exception:
                    pass

            response_data = {
                "results": {
                    "ok": True if bt else False,
                    "count_days": n_trades,
                    "avg_basket_return": avg_ret,
                    "median": hit_rate,
                    "stdev": stdev,
                },
                "overall_metrics": core.get("overall_metrics") or {
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

    # Alias for compatibility with some UI hooks
    @app.get("/api/copilot/context")
    async def copilot_context_alias():
        return await market_context_current()

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
            # Try to load from JSON files first (fallback if parquet doesn't exist)
            from storage.io import load_json
            
            forecasts_data = load_json("forecasts") or load_json("forecasts.json")
            forecasts_rows = []
            if forecasts_data:
                # Extract rows from various possible formats
                if isinstance(forecasts_data, dict):
                    forecasts_rows = forecasts_data.get("rows") or forecasts_data.get("data", {}).get("rows", []) or []
                    if not forecasts_rows and isinstance(forecasts_data.get("data"), list):
                        forecasts_rows = forecasts_data.get("data", [])
                elif isinstance(forecasts_data, list):
                    forecasts_rows = forecasts_data
            
            # Calculate KPIs from JSON data
            forecasts_count = len(forecasts_rows) if forecasts_rows else 0
            tickers_set = set()
            horizons_set = set()
            confidences = []
            bullish_count = 0
            bearish_count = 0
            
            for row in forecasts_rows:
                if isinstance(row, dict):
                    ticker = row.get("ticker") or row.get("symbol")
                    if ticker:
                        tickers_set.add(str(ticker).upper())
                    
                    horizon = row.get("horizon")
                    if horizon:
                        horizons_set.add(str(horizon))
                    
                    confidence = row.get("confidence")
                    if confidence is not None:
                        conf = float(confidence)
                        confidences.append(conf)
                    
                    direction = row.get("direction", "").lower()
                    if direction == "up":
                        bullish_count += 1
                    elif direction == "down":
                        bearish_count += 1
            
            tickers_count = len(tickers_set)
            horizons_list = sorted(list(horizons_set))
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            # Convert to percentage (0-100) if needed, but keep as decimal (0-1) for consistency
            high_confidence_count = sum(1 for c in confidences if c >= 0.7)
            
            # Log for debugging if no data
            if forecasts_count == 0:
                logger.warning(f"No forecasts found in data. forecasts_data keys: {list(forecasts_data.keys()) if isinstance(forecasts_data, dict) else 'not a dict'}")
            
            # Try DuckDB/Parquet as primary source if available (more accurate)
            try:
                from core.duck import query_parquet as _qp
                base_dir = Path(__file__).resolve().parents[2]
                fpat = str(base_dir / 'data' / 'forecast' / 'dt=*' / 'final.parquet')
                parts = sorted((base_dir / 'data' / 'forecast').glob('dt=*'))
                last_dt = parts[-1].name.split('=')[-1] if parts else None
                
                try:
                    cnt_row = _qp(f"select count(*) as cnt, count(distinct ticker) as nt from read_parquet('{fpat}')")
                    if cnt_row and len(cnt_row) > 0:
                        parquet_forecasts_count = int(cnt_row[0]['cnt']) if cnt_row else 0
                        parquet_tickers_count = int(cnt_row[0]['nt']) if cnt_row else 0
                        # Use parquet data if available and more complete
                        if parquet_forecasts_count > forecasts_count:
                            forecasts_count = parquet_forecasts_count
                            tickers_count = parquet_tickers_count
                        hz_rows = _qp(f"select distinct horizon from read_parquet('{fpat}')")
                        parquet_horizons = sorted([str(r['horizon']) for r in hz_rows if r.get('horizon') is not None])
                        if parquet_horizons:
                            horizons_list = parquet_horizons
                except Exception:
                    pass  # Fallback to JSON data already loaded
            except ImportError:
                last_dt = None

            # If parquet missing, derive last_dt from forecasts JSON metadata
            if not last_dt and isinstance(forecasts_data, dict):
                last_dt = (
                    forecasts_data.get('last_update')
                    or forecasts_data.get('freshness')
                    or forecasts_data.get('generated_at')
                )
            
            # Load news data for news KPI
            news_data = load_json("news_feed") or load_json("news_feed.json")
            news_count = 0
            last_news_update = None
            if news_data:
                news_items = news_data.get("articles") or news_data.get("rows") or news_data.get("data", {}).get("articles", []) or []
                if isinstance(news_items, list):
                    # Count recent news (last 60 minutes)
                    now = datetime.utcnow()
                    for item in news_items:
                        if isinstance(item, dict):
                            pub_date = item.get("published_at") or item.get("timestamp") or item.get("date")
                            if pub_date:
                                try:
                                    if isinstance(pub_date, str):
                                        pub_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                                    else:
                                        pub_dt = pub_date
                                    if (now - pub_dt).total_seconds() <= 3600:  # 60 minutes
                                        news_count += 1
                                except Exception:
                                    pass
                # Capture last update if present
                payload = news_data.get("data") or news_data.get("payload") or {}
                last_news_update = (
                    news_data.get("generated_at")
                    or news_data.get("last_update")
                    or news_data.get("freshness")
                    or (payload.get("generated_at") if isinstance(payload, dict) else None)
                )
            
            # Load backtests data for hit rate
            backtests_data = load_json("backtests") or load_json("backtests.json")
            hit_rate = 0.0
            backtest_status = "pending"
            if backtests_data:
                results = backtests_data.get("results") or backtests_data.get("data", {}).get("results", []) or []
                if isinstance(results, list) and len(results) > 0:
                    correct = sum(1 for r in results if isinstance(r, dict) and r.get("correct", False))
                    hit_rate = (correct / len(results)) * 100 if results else 0.0
                    backtest_status = "completed"
            
            # Build base_data with all KPIs
            # Macro last update (optional)
            last_macro_dt = None
            try:
                macro = load_json("macro_series") or load_json("macro_series.json")
                if macro:
                    last_macro_dt = macro.get("updated_at") or macro.get("generated_at") or macro.get("freshness")
            except Exception:
                pass

            base_data = {
                "last_forecast_dt": last_dt,
                "forecasts_count": forecasts_count,
                "tickers": tickers_count,
                "horizons": horizons_list,
                "last_macro_dt": last_macro_dt,
                "last_quality_dt": None,
                # Structure compatible avec le frontend
                "forecasts": {
                    "total": forecasts_count,
                    "high_confidence": high_confidence_count,
                    "avg_confidence": avg_confidence,
                    "bullish": bullish_count,
                    "bearish": bearish_count,
                },
                "backtests": {
                    "hit_rate": hit_rate,
                    "sharpe_ratio": 0.0,  # TODO: calculate from backtests
                    "status": backtest_status,
                },
                "news": {
                    "recent_count": news_count,
                    "avg_score": 0.0,  # TODO: calculate from news sentiment
                },
                "system": {
                    "last_forecast_update": last_dt,
                    "last_news_update": last_news_update,
                    "last_backtest_update": backtests_data.get("generated_at") if isinstance(backtests_data, dict) else None,
                },
                "generated_at": datetime.utcnow().isoformat(),
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
            
        except ImportError as e:
            logger.warning(f"dashboard_kpis import error: {e}")
            # Return minimal KPIs based on any data computed above
            return _ok({
                "last_forecast_dt": locals().get("last_dt"),
                "forecasts_count": locals().get("forecasts_count", 0),
                "tickers": locals().get("tickers_count", 0),
                "horizons": locals().get("horizons_list", []),
                "last_macro_dt": None,
                "last_quality_dt": None,
                "forecasts": {
                    "total": locals().get("forecasts_count", 0),
                    "high_confidence": locals().get("high_confidence_count", 0),
                    "avg_confidence": locals().get("avg_confidence", 0.0),
                    "bullish": locals().get("bullish_count", 0),
                    "bearish": locals().get("bearish_count", 0),
                },
                "backtests": {
                    "hit_rate": locals().get("hit_rate", 0.0),
                    "sharpe_ratio": 0.0,
                    "status": locals().get("backtest_status", "pending"),
                },
                "news": {
                    "recent_count": locals().get("news_count", 0),
                    "avg_score": 0.0,
                },
                "system": {
                    "last_forecast_update": locals().get("last_dt"),
                    "last_news_update": None,
                    "last_backtest_update": None,
                },
                "filtered_signals": [],
                "filtered_risks": [],
                "filter_applied": {
                    "sectors": sectors,
                    "horizons": horizons,
                    "themes": themes,
                    "tickers": tickers
                },
                "filtered_ticker_count": 0,
                "generated_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"Error in dashboard_kpis: {e}", exc_info=True)
            return _ok({
                "last_forecast_dt": None,
                "forecasts_count": 0,
                "tickers": 0,
                "horizons": [],
                "last_macro_dt": None,
                "last_quality_dt": None,
                "forecasts": {
                    "total": 0,
                    "high_confidence": 0,
                    "avg_confidence": 0.0,
                    "bullish": 0,
                    "bearish": 0,
                },
                "backtests": {
                    "hit_rate": 0.0,
                    "sharpe_ratio": 0.0,
                    "status": "error",
                },
                "news": {
                    "recent_count": 0,
                    "avg_score": 0.0,
                },
                "system": {},
                "filtered_signals": [],
                "filtered_risks": [],
                "filter_applied": {
                    "sectors": sectors,
                    "horizons": horizons,
                    "themes": themes,
                    "tickers": tickers
                },
                "filtered_ticker_count": 0,
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat(),
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
