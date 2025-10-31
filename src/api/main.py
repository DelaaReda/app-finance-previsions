# src/api/main.py
"""
FastAPI backend for React frontend.
Serves all 5 pillars according to VISION.md
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import pandas as pd

# Import data access layer
try:
    from core.data_access import (
        get_close_series,
        load_macro_forecast_rows,
        check_data_freshness
    )
    from core.market_data import get_price_history
    from core.downsample import lttb
    from core.duck import query_parquet, parquet_glob
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    # Fallback stubs
    def get_close_series(ticker): return None
    def load_macro_forecast_rows(limit=200): return {"ok": False}
    def check_data_freshness(): return {}
    def get_price_history(ticker, **kw): return None
    def lttb(points, threshold=1000): return points
    def query_parquet(sql, params=None): return []
    def parquet_glob(*parts): return str(Path(*parts))

from api.services.news_service import get_news_feed as lakehouse_news_feed, get_sentiment as lakehouse_news_sentiment

# ================================= APP SETUP =================================

def create_app() -> FastAPI:
    """Create and configure FastAPI app."""
    app = FastAPI(
        title="Finance Copilot API",
        description="Backend API for React frontend - 5 Pillars: Macro, Stocks, News, Copilot, Brief",
        version="0.1.0"
    )

    # CORS middleware (allow React dev server)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Routes
    register_routes(app)

    return app

# ================================= MODELS ====================================

class ApiResponse(BaseModel):
    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None

# ================================= HELPERS ===================================

def _ok(data: Any) -> Dict:
    return {"ok": True, "data": data}

def _err(msg: str) -> Dict:
    return {"ok": False, "error": msg}

def _latest_partition(base: str) -> Optional[str]:
    """Get latest dt=YYYYMMDD partition."""
    parts = sorted(Path(base).glob("dt=*"))
    return parts[-1].name.split("=")[-1] if parts else None

# ================================= ROUTES ====================================

def register_routes(app: FastAPI):
    """Register all API routes."""

    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return _ok({
            "status": "up",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.1.0"
        })

    @app.get("/api/freshness")
    async def data_freshness():
        """Check freshness of all data sources."""
        return _ok(check_data_freshness())

    # ========================= PILLAR 1: MACRO ===========================

    @app.get("/api/macro/series")
    async def macro_series(
        series_ids: Optional[str] = Query(None, description="Comma-separated series IDs"),
        limit: int = Query(200, ge=1, le=1000)
    ):
        """Get macro time series data (FRED)."""
        result = load_macro_forecast_rows(limit=limit)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail="No macro data available")
        return _ok(result["rows"])

    @app.get("/api/macro/snapshot")
    async def macro_snapshot():
        """Get current macro snapshot (latest values)."""
        result = load_macro_forecast_rows(limit=10)
        if not result.get("ok"):
            return _err("No macro data")
        
        rows = result.get("rows", [])
        snapshot = {}
        for row in rows:
            series = row.get("series")
            value = row.get("value")
            if series and value is not None:
                snapshot[series] = value
        
        return _ok(snapshot)

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
        ticker: str = Query(..., description="Stock ticker symbol"),
        interval: str = Query("1d", description="Interval: 1d, 1wk, 1mo"),
        downsample: int = Query(1000, ge=100, le=10000, description="Max points (LTTB)")
    ):
        """Get stock prices with technical indicators (downsampled)."""
        series = get_close_series(ticker)
        if series is None or series.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        # Convert to points (timestamp, value)
        points = [(int(ts.timestamp()), float(val)) 
                  for ts, val in series.items() 
                  if not pd.isna(val)]

        # Downsample if needed
        if len(points) > downsample:
            points = lttb(points, threshold=downsample)

        return _ok({
            "ticker": ticker,
            "interval": interval,
            "points": points,
            "count": len(points),
            "source": "features" if "features" in str(series) else "legacy",
            "timestamp": datetime.utcnow().isoformat()
        })

    @app.get("/api/stocks/universe")
    async def stock_universe():
        """Get list of tracked tickers."""
        # TODO: Read from watchlist or config
        return _ok({
            "tickers": ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"],
            "count": 8
        })

    @app.get("/api/stocks/{ticker}")
    async def stock_detail(ticker: str):
        """Get detailed ticker sheet (prix + indicators + news)."""
        series = get_close_series(ticker)
        if series is None or series.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        last_price = float(series.iloc[-1]) if not series.empty else None
        
        return _ok({
            "ticker": ticker,
            "last_price": last_price,
            "date": series.index[-1].isoformat() if not series.empty else None,
            "indicators": {
                "rsi": None,  # TODO: from features
                "sma20": None,
                "macd": None
            },
            "news_count": 0  # TODO: from news features
        })

    # ========================= PILLAR 3: NEWS ============================

    @app.get("/api/news/feed")
    async def news_feed(
        tickers: Optional[List[str]] = Query(None, description="Optional tickers filter"),
        since: str = Query("7d", description="1h, 6h, 1d, 3d, 7d, 14d, 30d, 90d"),
        region: str = Query("all", description="Region filter"),
        score_min: float = Query(0.0, ge=0.0, le=1.0, description="Minimum composite score"),
        limit: int = Query(50, ge=1, le=200)
    ):
        """Get news feed with scoring from the lakehouse."""
        data = lakehouse_news_feed(
            tickers=tickers,
            since=since,
            score_min=score_min,
            region=region,
            limit=limit,
        )

        response = {
            "articles": [article.model_dump() for article in data.articles],
            "count": data.count,
            "total": data.total,
            "filters": data.filters.model_dump(exclude_none=True),
            "trace": data.trace.model_dump(),
        }
        return _ok(response)

    @app.get("/api/news/sentiment")
    async def news_sentiment(limit: int = Query(100, ge=1, le=500)):
        """Get aggregated sentiment by ticker."""
        data = lakehouse_news_sentiment(limit=limit)
        response = {
            "sentiment": data.sentiment,
            "count": data.count,
            "trace": data.trace.model_dump(),
        }
        return _ok(response)

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

    class CopilotAskRequest(BaseModel):
        question: str
        context_years: int = 5
        max_sources: int = 10

    @app.post("/api/copilot/ask")
    async def copilot_ask(req: CopilotAskRequest):
        """Ask LLM with RAG (5 years context)."""
        # TODO: Implement RAG query
        return _ok({
            "answer": "LLM Copilot not yet implemented",
            "sources": [],
            "confidence": 0.0,
            "warning": "This is a placeholder response"
        })

    @app.get("/api/copilot/history")
    async def copilot_history(limit: int = Query(20, ge=1, le=100)):
        """Get conversation history."""
        # TODO: Implement conversation history
        return _ok({"conversations": [], "count": 0})

    # ====================== PILLAR 5: MARKET BRIEF =======================

    @app.get("/api/brief/weekly")
    async def brief_weekly():
        """Get weekly market brief."""
        # TODO: Generate/fetch weekly brief
        return _ok({
            "title": "Weekly Market Brief",
            "date": datetime.utcnow().date().isoformat(),
            "sections": [],
            "placeholder": True
        })

    @app.get("/api/brief/daily")
    async def brief_daily():
        """Get daily market brief."""
        # TODO: Generate/fetch daily brief
        return _ok({
            "title": "Daily Market Brief",
            "date": datetime.utcnow().date().isoformat(),
            "sections": [],
            "placeholder": True
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
        """Get forecasts list."""
        # Reuse existing dash_app.api logic
        try:
            from dash_app.api import forecasts as dash_forecasts
            result = dash_forecasts(asset_type, horizon, search, sort_by)
            if result.get("ok"):
                return _ok(result["data"])
            else:
                raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
        except ImportError:
            return _ok({"rows": [], "count": 0, "note": "Forecasts API not available"})

    @app.get("/api/dashboard/kpis")
    async def dashboard_kpis():
        """Get dashboard KPIs."""
        try:
            from dash_app.api import dashboard_kpis as dash_kpis
            result = dash_kpis()
            if result.get("ok"):
                return _ok(result["data"])
            else:
                return _err(result.get("error", "Unknown error"))
        except ImportError:
            return _ok({
                "last_forecast_dt": None,
                "forecasts_count": 0,
                "tickers": 0,
                "horizons": [],
                "last_macro_dt": None,
                "last_quality_dt": None
            })

# ================================= SERVER ====================================

def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the FastAPI server."""
    import uvicorn
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    run_server()
