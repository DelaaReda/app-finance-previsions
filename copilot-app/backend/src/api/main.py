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
from dataclasses import asdict

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import pandas as pd

# Import data access layer
try:
    from core.data_access import (
        get_close_series,
        load_macro_forecast_rows
    )
    from core.market_data import get_price_history
    from core.downsample import lttb
    from core.duck import query_parquet, parquet_glob
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    # Fallback stubs
    def get_close_series(ticker): return None
    def load_macro_forecast_rows(limit=200): return {"ok": False}
    def get_price_history(ticker, **kw): return None
    def lttb(points, threshold=1000): return points
    def query_parquet(sql, params=None): return []
    def parquet_glob(*parts): return str(Path(*parts))

from api.services.news_service import (
    get_news_events as lakehouse_news_events,
    get_news_feed as lakehouse_news_feed,
    get_sentiment as lakehouse_news_sentiment,
)

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
        """Health check endpoint with enriched status information."""
        # Use relative import based on the project structure
        # Since this is in src/api, and storage is in backend/storage (outside src), 
        # we need to use a different approach
        try:
            # First try the direct import (relative to project root)
            import sys
            from pathlib import Path
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
        backtests_data = load_json("backtests.json")
        if backtests_data:
            last_updates["backtests"] = backtests_data.get("last_update")
        
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
        limit: int = Query(200, ge=1, le=1000)
    ):
        """Get macro time series data (FRED)."""
        result = load_macro_forecast_rows(limit=limit)
        # load_macro_forecast_rows returns {"rows": [...]}
        if not result.get("rows"):
            raise HTTPException(status_code=404, detail="No macro data available")
        return _ok(result["rows"])

    @app.get("/api/macro/snapshot")
    async def macro_snapshot():
        """Get current macro snapshot (latest values)."""
        result = load_macro_forecast_rows(limit=10)
        if not result.get("rows"):
            return _err("No macro data")

        rows = result.get("rows", [])
        snapshot = {}
        for row in rows:
            # The data_access function returns rows with keys like "inflation_yoy", "unemployment", etc.
            for key, value in row.items():
                if value is not None:
                    snapshot[key] = value

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
        ticker: Optional[str] = Query(None, description="Stock ticker symbol (single ticker)"),
        tickers: Optional[List[str]] = Query(None, description="Stock ticker symbols (multiple tickers)"),
        range: str = Query("1y", description="Time range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
        interval: str = Query("1d", description="Interval: 1d, 1wk, 1mo"),
        downsample: int = Query(1000, ge=100, le=10000, description="Max points (LTTB)")
    ):
        """Get stock prices with technical indicators (downsampled)."""
        # Use get_price_history which supports range filtering
        from core.market_data import get_price_history
        from datetime import datetime, timedelta

        # Determine which tickers to process
        tickers_to_process = []
        if ticker:
            tickers_to_process = [ticker]
        elif tickers and len(tickers) > 0:
            tickers_to_process = tickers
        else:
            raise HTTPException(status_code=422, detail="Either 'ticker' or 'tickers' parameter must be provided")

        # Convert range to start date
        range_map = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, "6mo": 180,
            "1y": 365, "2y": 730, "5y": 1825
        }

        days_back = range_map.get(range, 365)  # Default to 1 year
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Process tickers
        results = {}
        for ticker_symbol in tickers_to_process:
            df = get_price_history(ticker_symbol, start=start_date, interval=interval)
            if df is None or df.empty:
                results[ticker_symbol] = {"error": f"No data for {ticker_symbol}"}
                continue

            # Extract Close prices as series
            series = df['Close'] if 'Close' in df.columns else df.iloc[:, 0]  # Fallback to first column

            # Convert to points (timestamp, value)
            points = [(int(ts.timestamp()), float(val))
                      for ts, val in series.items()
                      if not pd.isna(val)]

            # Downsample if needed
            if len(points) > downsample:
                from core.downsample import lttb
                points = lttb(points, threshold=downsample)

            results[ticker_symbol] = {
                "range": range,
                "interval": interval,
                "points": points,
                "count": len(points),
                "start_date": start_date,
                "timestamp": datetime.utcnow().isoformat()
            }

        return _ok({
            "tickers": results,
            "range": range,
            "interval": interval,
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
            except:
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
            except:
                pass  # Use None values if scoring fails
            
            # Get alerts for this ticker
            alerts = []
            try:
                alerts = alerts_for_ticker(df_prices, pd.DataFrame(technical_indicators, index=[0]), news_sentiment, ticker.upper())
            except:
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
        limit: int = Query(50, ge=1, le=200)
    ):
        """Get news feed with caching. Never-empty: serves latest snapshot on failure."""
        # Map `since` to service `window`
        since_map = {
            "1d": "last_day",
            "3d": "last_week",
            "7d": "last_week",
            "14d": "last_week",
            "30d": "last_month",
            "90d": "last_month",
        }
        window = since_map.get(since, "last_week")

        # Call async service and adapt contract to API response
        result = await lakehouse_news_feed(
            tickers=tickers,
            q=None,
            limit=limit,
            window=window,
        )

        # result shape: { ok: bool, data: { items: [...], count, freshness, ... } }
        ok_flag = bool(result.get("ok", True)) if isinstance(result, dict) else True
        payload = result.get("data", {}) if isinstance(result, dict) else {}
        items = payload.get("items") or payload.get("articles") or []

        # Normalize to articles list
        articles = []
        for idx, item in enumerate(items or []):
            if not isinstance(item, dict):
                continue
            articles.append({
                "id": item.get("id") or item.get("url") or f"news_{idx+1}",
                "title": item.get("title", ""),
                "link": item.get("url") or item.get("link", ""),
                "pubDate": item.get("published") or item.get("pubDate") or datetime.utcnow().isoformat(),
                "source": item.get("source", "unknown"),
                "region": (item.get("region") or "").upper() if isinstance(item.get("region"), str) else item.get("region"),
                "summary": item.get("summary", ""),
                "score": item.get("score", 0.0),
                "importance": item.get("importance", 0.0),
                "freshness": item.get("freshness", 0.0),
                "relevance": item.get("relevance", 0.0),
                "sentiment_score": item.get("sentiment_score", item.get("sentiment", 0.0) or 0.0),
                "entities": item.get("entities", []),
                "tickers": item.get("tickers", []),
            })

        # Optional filtering by score_min (v1: simple threshold on score)
        try:
            if score_min and score_min > 0:
                articles = [a for a in articles if float(a.get("score", 0)) >= float(score_min)]
        except Exception:
            # Do not fail on bad types; keep unfiltered
            pass

        # Optional region filter (v1)
        try:
            if region and region.lower() != "all":
                region_up = region.upper()
                articles = [a for a in articles if (a.get("region") or "").upper() == region_up]
        except Exception:
            pass

        response = {
            "articles": articles,
            "count": len(articles) if payload.get("count") is None else payload.get("count"),
            "filters": {"tickers": tickers, "since": since, "limit": limit},
            "freshness": payload.get("freshness", "unknown"),
            "source": payload.get("source", []),
            "last_update": payload.get("last_update"),
        }
        return _ok(response) if ok_flag else _err("news service error")

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

    # ====================== PILLAR 5: MARKET BRIEF =======================

    @app.get("/api/brief/weekly")
    async def brief_weekly():
        """Get weekly market brief with <200ms response time using pre-computed data."""
        try:
            # Use cached snapshot approach for instant response
            from backend.storage.base import load_json
            
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
            from storage import load_json
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

    @app.get("/api/backtests")
    async def backtests(
        horizon: str = Query("1m", description="Backtest horizon: 1w, 1m, 1y"),
        top_n: int = Query(5, ge=1, le=20, description="Top-N basket size"),
        days_back: int = Query(180, ge=30, le=365, description="Days to look back")
    ):
        """Backtests summary with cache-first and safe fallbacks (never-empty)."""
        try:
            # Prefer cached snapshot on disk
            from storage import load_json
            bt = load_json("backtests") or {}
            data_block = bt.get("data") if isinstance(bt, dict) else None
            core = data_block if isinstance(data_block, dict) else bt if isinstance(bt, dict) else {}

            # Normalize keys from various producers (jobs/services)
            metrics = core.get("metrics") or {}
            n_trades = int(metrics.get("n_trades", core.get("n_trades", 0)) or 0)
            avg_ret = float(metrics.get("avg_expected_return", core.get("avg_return", 0)) or 0)
            hit_rate = float(metrics.get("hit_rate", core.get("hit_rate", 0)) or 0)
            stdev = metrics.get("stdev", 0)

            response_data = {
                "results": {
                    "ok": True if bt else False,
                    "count_days": n_trades,
                    "avg_basket_return": avg_ret,
                    "median": hit_rate,
                    "stdev": stdev,
                },
                "params": {"horizon": horizon, "top_n": top_n, "days_back": days_back},
                "generated_at": core.get("until") or core.get("generated_at") or datetime.utcnow().isoformat(),
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
            return _ok({
                "results": {
                    "ok": False,
                    "count_days": 0,
                    "avg_basket_return": 0,
                    "median": 0,
                    "stdev": 0,
                    "error": str(e)
                },
                "params": {"horizon": horizon, "top_n": top_n, "days_back": days_back},
                "warning": "Backtests snapshot not found; background compute recommended",
                "cache_status": "error"
            })

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
            from pathlib import Path as _P
            from core.duck import query_parquet as _qp
            base_dir = _P(__file__).resolve().parents[2]
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
                from pathlib import Path as _P
                base_dir = _P(__file__).resolve().parents[2]
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
                return _err("Note not found or update failed", status_code=404)
                
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
                return _err("Note not found", status_code=404)
            
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
                    return _err("Invalid note type. Use: thesis, analysis, research, alert, brief", status_code=400)
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
                return _err("Note not found or has no versions", status_code=404)
            
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
                return _err("Could not compare versions (note or versions not found)", status_code=404)
            
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
                from datetime import datetime, timedelta
                
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
                from datetime import datetime, timedelta
                
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
