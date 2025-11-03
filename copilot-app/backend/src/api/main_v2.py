# src/api/main_v2.py
"""
FastAPI backend v0.1 - Production-ready API with full traçability
Maps React services to Python modules via service facades.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# Import schemas
from api.schemas import (
    HealthResponse, HealthData, HealthStatus,
    FreshnessResponse, FreshnessData, DataSourceFreshness, FreshnessStatus,
    MacroOverviewResponse, MacroSnapshotResponse, MacroIndicatorsResponse,
    StockOverviewResponse, StockUniverseResponse,
    NewsFeedResponse, SentimentResponse,
    CopilotAskRequest, CopilotAskResponse,
    BriefResponse, SignalsResponse,
    ErrorResponse
)

# Import services
from api.services.macro_service import (
    get_macro_overview,
    get_macro_snapshot,
    get_macro_indicators
)
from api.services.stocks_service import (
    get_stock_overview,
    get_stock_universe
)
from api.services.news_service import (
    get_news_feed,
    get_sentiment
)


# ================================= APP SETUP =================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Finance Copilot API",
        description="""
        Backend API for Financial Copilot - 5 Pillars Architecture
        
        **Pillars:**
        1. Macro - FRED, VIX, economic indicators
        2. Stocks - Prices, technical indicators, signals
        3. News - RSS feeds with scoring
        4. Copilot - LLM Q&A with RAG
        5. Brief - Market reports
        
        **Traçability:** All responses include source, timestamp, and hash
        """,
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "*"  # TODO: Restrict in production
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                ok=False,
                error=exc.detail
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                ok=False,
                error=f"Internal server error: {str(exc)}"
            ).dict()
        )
    
    # Register routes
    register_routes(app)
    
    return app


# ================================= ROUTES ====================================

def register_routes(app: FastAPI):
    """Register all API routes."""
    
    # ========================= HEALTH ===========================
    
    @app.get(
        "/api/health",
        response_model=HealthResponse,
        tags=["health"],
        summary="Health check"
    )
    async def health_check():
        """Check if API is operational."""
        return HealthResponse(
            ok=True,
            data=HealthData(
                status=HealthStatus.UP,
                timestamp=datetime.utcnow(),
                version="0.1.0"
            )
        )
    
    @app.get(
        "/api/freshness",
        response_model=FreshnessResponse,
        tags=["health"],
        summary="Data freshness check"
    )
    async def data_freshness():
        """Check freshness of all data sources."""
        # TODO: Implement real freshness checks
        return FreshnessResponse(
            ok=True,
            data=FreshnessData(
                macro=DataSourceFreshness(
                    last_update=datetime.utcnow(),
                    age_hours=0.5,
                    status=FreshnessStatus.FRESH
                ),
                stocks=DataSourceFreshness(
                    last_update=datetime.utcnow(),
                    age_hours=1.0,
                    status=FreshnessStatus.FRESH
                ),
                news=DataSourceFreshness(
                    last_update=datetime.utcnow(),
                    age_hours=0.25,
                    status=FreshnessStatus.FRESH
                )
            )
        )
    
    # ========================= PILLAR 1: MACRO ===========================
    
    @app.get(
        "/api/macro/overview",
        response_model=MacroOverviewResponse,
        tags=["macro"],
        summary="Macro economic overview"
    )
    async def macro_overview(
        range: str = Query("5y", description="Time range (1m, 3m, 6m, 1y, 2y, 3y, 5y, 10y, all)"),
        series: Optional[str] = Query(None, description="Comma-separated FRED series IDs")
    ):
        """
        Get macro economic data with FRED series.
        Returns time series with full traçability.
        """
        try:
            data = get_macro_overview(range_str=range, series_ids=series)
            return MacroOverviewResponse(ok=True, data=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch macro data: {str(e)}"
            )
    
    @app.get(
        "/api/macro/snapshot",
        response_model=MacroSnapshotResponse,
        tags=["macro"],
        summary="Current macro snapshot"
    )
    async def macro_snapshot():
        """Get latest values for key macro indicators."""
        try:
            data = get_macro_snapshot()
            return MacroSnapshotResponse(ok=True, data=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch macro snapshot: {str(e)}"
            )
    
    @app.get(
        "/api/macro/indicators",
        response_model=MacroIndicatorsResponse,
        tags=["macro"],
        summary="Derived macro indicators"
    )
    async def macro_indicators():
        """Get computed indicators (CPI YoY, yield curve, recession prob, VIX)."""
        try:
            data = get_macro_indicators()
            return MacroIndicatorsResponse(ok=True, data=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to compute indicators: {str(e)}"
            )
    
    # ========================= PILLAR 2: STOCKS ==========================
    
    @app.get(
        "/api/stocks/{ticker}/overview",
        response_model=StockOverviewResponse,
        tags=["stocks"],
        summary="Stock overview with technicals"
    )
    async def stock_overview(
        ticker: str,
        features: str = Query("all", description="Features: technicals,fundamentals,signals,news,all"),
        range: str = Query("1y", description="Time range (1m, 3m, 6m, 1y, 2y, 5y, max)"),
        downsample: int = Query(1000, ge=100, le=10000, description="Max points (LTTB)")
    ):
        """
        Get complete stock overview including:
        - Price history (downsampled with LTTB)
        - Technical indicators (RSI, MACD, SMA, Bollinger)
        - Trading signals
        - Composite score (macro 40% + tech 40% + news 20%)
        """
        try:
            data = get_stock_overview(
                ticker=ticker.upper(),
                features=features,
                range_str=range,
                downsample=downsample
            )
            return StockOverviewResponse(ok=True, data=data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch stock data: {str(e)}"
            )
    
    @app.get(
        "/api/stocks/universe",
        response_model=StockUniverseResponse,
        tags=["stocks"],
        summary="List of tracked tickers"
    )
    async def stock_universe():
        """Get list of all tracked stock tickers."""
        try:
            data = get_stock_universe()
            return StockUniverseResponse(ok=True, data=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch universe: {str(e)}"
            )
    
    # ========================= PILLAR 3: NEWS ============================
    
    @app.get(
        "/api/news/feed",
        response_model=NewsFeedResponse,
        tags=["news"],
        summary="News feed with scoring"
    )
    async def news_feed(
        tickers: Optional[str] = Query(None, description="Comma-separated tickers (e.g., AAPL,MSFT)"),
        since: str = Query("7d", description="Time period (1h, 6h, 1d, 3d, 7d, 14d, 30d, 90d)"),
        score_min: float = Query(0.0, ge=0.0, le=1.0, description="Minimum score filter"),
        region: str = Query("all", description="Region (US, CA, EU, INTL, all)"),
        limit: int = Query(50, ge=1, le=200, description="Max articles")
    ):
        """
        Get news feed with scoring (freshness, source quality, relevance).
        Supports filtering by ticker, region, time period, and minimum score.
        """
        try:
            data = get_news_feed(
                tickers=tickers,
                since=since,
                score_min=score_min,
                region=region,
                limit=limit
            )
            return NewsFeedResponse(ok=True, data=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch news: {str(e)}"
            )
    
    @app.get(
        "/api/news/sentiment",
        response_model=SentimentResponse,
        tags=["news"],
        summary="Aggregated sentiment by ticker"
    )
    async def news_sentiment():
        """Get sentiment scores aggregated by ticker."""
        try:
            data = get_sentiment(limit=100)
            return SentimentResponse(ok=True, data=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to compute sentiment: {str(e)}"
            )
    
    # ======================== PILLAR 4: COPILOT ======================
    
    @app.post(
        "/api/copilot/ask",
        response_model=CopilotAskResponse,
        tags=["copilot"],
        summary="Ask LLM with RAG"
    )
    async def copilot_ask(request: CopilotAskRequest):
        """
        Ask question to LLM with RAG context (≥5 years).
        Returns answer with cited sources and confidence score.
        """
        # TODO: Implement RAG
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LLM Copilot not yet implemented"
        )
    
    # ====================== PILLAR 5: BRIEF =======================
    
    @app.get(
        "/api/brief/weekly",
        response_model=BriefResponse,
        tags=["brief"],
        summary="Weekly market brief"
    )
    async def brief_weekly():
        """Get weekly market brief with Top 3 signals and risks."""
        # TODO: Implement brief generation
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Weekly brief not yet implemented"
        )
    
    @app.get(
        "/api/brief/daily",
        response_model=BriefResponse,
        tags=["brief"],
        summary="Daily market brief"
    )
    async def brief_daily():
        """Get daily market brief."""
        # TODO: Implement brief generation
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Daily brief not yet implemented"
        )
    
    # =========================== SIGNALS =================================
    
    @app.get(
        "/api/signals/top",
        response_model=SignalsResponse,
        tags=["signals"],
        summary="Top 3 signals and risks"
    )
    async def signals_top():
        """
        Get Top 3 signals and Top 3 risks based on composite scoring:
        - Macro: 40%
        - Technical: 40%
        - News: 20%
        """
        # TODO: Implement composite scoring
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Composite scoring not yet implemented"
        )


# ================================= SERVER ====================================

def run_server(host: str = "127.0.0.1", port: int = 8050):
    """Run the FastAPI server with uvicorn."""
    import uvicorn
    app = create_app()
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    # Read port from environment or use default
    port = int(os.getenv("API_PORT", "8050"))
    run_server(port=port)
