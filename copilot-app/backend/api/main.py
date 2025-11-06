"""
Main API file for Finance Copilot
This is the entry point that uvicorn runs when using api.main:create_app
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.response import ok, err
from storage.io import save_json, load_json
import logging
from datetime import datetime
import sys
import os

# Setup structured logging with JSON formatter
from core.logging.structured_log import configure_logging
configure_logging()

logger = logging.getLogger(__name__)

# Create main FastAPI app
app = FastAPI(
    title="Finance Copilot API",
    description="Backend API for React frontend - 5 Pillars: Macro, Stocks, News, Copilot, Brief",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://0.0.0.0:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trace ID and finance middleware
from src.core.middleware import FinanceMiddleware
app.add_middleware(FinanceMiddleware)

@app.on_event("startup")
async def startup_event():
    """
    Initialize data on first startup if not present
    Integration by: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
    Task: FC-INT-009 - Ensure data is available immediately on API start
    """
    logger.info("🚀 API startup - checking for data files...")
    
    try:
        from storage.base import load_forecasts
        
        # Check if forecast data exists
        forecasts = load_forecasts()
        
        if forecasts is None or not forecasts.get('data', {}).get('rows'):
            logger.info("⚠️  No forecast data found, initializing...")
            
            # Import and run initialization
            import sys
            from pathlib import Path
            backend_path = str(Path(__file__).parent.parent)
            if backend_path not in sys.path:
                sys.path.insert(0, backend_path)
            
            from jobs.initialize_data import initialize_all_data
            results = initialize_all_data()
            
            logger.info(f"✅ Data initialization complete: {results}")
        else:
            forecast_count = len(forecasts.get('data', {}).get('rows', []))
            last_update = forecasts.get('last_update', 'unknown')
            logger.info(f"✅ Forecast data exists: {forecast_count} forecasts, last update: {last_update}")
            
    except Exception as e:
        logger.warning(f"⚠️  Could not initialize data on startup: {str(e)}")
        logger.info("API will continue but may return empty data until jobs run")

@app.get("/")
def root():
    """Root endpoint for health check."""
    return {"status": "ok", "service": "Finance Copilot API", "version": "1.0.0"}


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    try:
        return ok({
            "status": "up",
            "backend_up": True,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "last_updates": {},
            "data_paths": {
                "forecasts": "data/forecasts.json",
                "news": "data/news_feed.json", 
                "brief_weekly": "data/brief_weekly.json",
                "backtests": "data/backtests.json"
            }
        })
    except Exception as e:
        return err(500, f"Health check failed: {str(e)}")


@app.get("/api/forecasts")
def get_forecasts():
    """Forecasts endpoint - serves cached snapshot with never-empty guarantee."""
    try:
        forecasts_data = load_json("forecasts.json")
        if forecasts_data and "data" in forecasts_data:
            return ok(forecasts_data["data"])
        else:
            return ok({
                "rows": [],
                "count": 0,
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback"],
                "message": "No cached forecasts available - system computing in background"
            })
    except Exception as e:
        return ok({
            "rows": [],
            "count": 0,
            "error": str(e),
            "message": "Forecasts temporarily unavailable - showing fallback data"
        })


@app.get("/api/news/feed")
def get_news_feed():
    """News feed endpoint - serves cached snapshot with never-empty guarantee."""
    try:
        news_data = load_json("news_feed.json")
        if news_data and "data" in news_data:
            return ok(news_data["data"])
        else:
            return ok({
                "articles": [],
                "count": 0,
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["fallback"],
                "message": "No cached news feed available - system fetching in background"
            })
    except Exception as e:
        return ok({
            "articles": [],
            "count": 0,
            "error": str(e),
            "message": "News feed temporarily unavailable - showing fallback data"
        })


def create_app():
    """
    Application factory function for uvicorn.
    This is the function that uvicorn calls when running 'api.main:create_app'
    """
    logger.info("Creating FastAPI application instance...")
    
    # Register all routes and services
    try:
        # Include routes from the main source API
        from src.api.main import register_routes
        register_routes(app)
        logger.info("Successfully registered routes from src.api.main")
    except ImportError as e:
        logger.warning(f"Could not import routes from src.api.main: {e}")
        # Continue with basic endpoints if the main routes fail
    
    # Include additional routes specific to this API entry point
    try:
        from api.routes.health import router as health_router
        app.include_router(health_router, prefix="/api")
        logger.info("Successfully registered health routes")
    except ImportError:
        logger.info("No specific health routes module found, using basic health endpoint")
    
    try:
        from api.routes.forecasts import router as forecasts_router
        app.include_router(forecasts_router, prefix="/api")
        logger.info("Successfully registered forecasts routes")
    except ImportError:
        logger.info("No specific forecasts routes module found, using basic forecasts endpoint")
    
    try:
        from api.routes.news import router as news_router
        app.include_router(news_router, prefix="/api")
        logger.info("Successfully registered news routes")
    except ImportError:
        logger.info("No specific news routes module found, using basic news endpoint")
    
    try:
        from api.routes.backtests import router as backtests_router
        app.include_router(backtests_router, prefix="/api")
        logger.info("Successfully registered backtests routes")
    except ImportError:
        logger.info("No specific backtests routes module found, using basic backtests endpoint")
    
    logger.info("FastAPI application created successfully")
    return app


if __name__ == "__main__":
    # This should match the uvicorn call in run_api.py
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8050, log_level="info")