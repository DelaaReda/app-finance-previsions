"""
Portfolios API Routes - Manage user portfolios/watchlists
Author: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: API-PORTFOLIO-001 - Portfolio/Watchlist management
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.core.response import ok, err
from backend.services.portfolio_service import (
    get_portfolio_service,
    Portfolio,
    PortfolioPerformance
)

router = APIRouter()


# Request/Response models
class PortfolioCreateRequest(BaseModel):
    """Request body for creating a portfolio"""
    name: str = Field(..., description="Portfolio name", example="Tech Watchlist")
    description: str = Field(default="", description="Portfolio description")
    tickers: List[str] = Field(default_factory=list, description="Initial tickers", example=["AAPL", "MSFT", "GOOGL"])
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class PortfolioUpdateRequest(BaseModel):
    """Request body for updating a portfolio"""
    name: Optional[str] = Field(None, description="New name")
    description: Optional[str] = Field(None, description="New description")
    tickers: Optional[List[str]] = Field(None, description="New tickers list")
    metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")


class TickersRequest(BaseModel):
    """Request body for adding/removing tickers"""
    tickers: List[str] = Field(..., description="List of ticker symbols", example=["AAPL", "MSFT"])


@router.get("/portfolios")
def list_portfolios():
    """
    List all user portfolios
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "portfolios": [
          {
            "id": "uuid",
            "name": "Tech Watchlist",
            "description": "My tech stocks",
            "tickers": ["AAPL", "MSFT", "GOOGL"],
            "created_at": "2025-11-06T...",
            "updated_at": "2025-11-06T..."
          }
        ],
        "count": 1
      }
    }
    ```
    """
    try:
        service = get_portfolio_service()
        portfolios = service.list_portfolios()
        
        return ok({
            "portfolios": [p.model_dump() for p in portfolios],
            "count": len(portfolios)
        })
    except Exception as e:
        return err(f"Failed to list portfolios: {str(e)}", code=500)


@router.post("/portfolios")
def create_portfolio(request: PortfolioCreateRequest):
    """
    Create a new portfolio
    
    **Request Body:**
    ```json
    {
      "name": "Tech Watchlist",
      "description": "FAANG stocks",
      "tickers": ["AAPL", "MSFT", "GOOGL", "META", "AMZN"]
    }
    ```
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "uuid",
        "name": "Tech Watchlist",
        ...
      }
    }
    ```
    """
    try:
        service = get_portfolio_service()
        portfolio = service.create_portfolio(
            name=request.name,
            description=request.description,
            tickers=request.tickers,
            metadata=request.metadata
        )
        
        return ok(portfolio.model_dump())
    except Exception as e:
        return err(f"Failed to create portfolio: {str(e)}", code=500)


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    """
    Get a specific portfolio by ID
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "uuid",
        "name": "Tech Watchlist",
        ...
      }
    }
    ```
    """
    try:
        service = get_portfolio_service()
        portfolio = service.get_portfolio(portfolio_id)
        
        if not portfolio:
            return err(f"Portfolio {portfolio_id} not found", code=404)
        
        return ok(portfolio.model_dump())
    except Exception as e:
        return err(f"Failed to get portfolio: {str(e)}", code=500)


@router.put("/portfolios/{portfolio_id}")
def update_portfolio(portfolio_id: str, request: PortfolioUpdateRequest):
    """
    Update an existing portfolio
    
    **Request Body (all fields optional):**
    ```json
    {
      "name": "Updated name",
      "description": "Updated description",
      "tickers": ["AAPL", "MSFT", "NVDA"]
    }
    ```
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "uuid",
        ...
      }
    }
    ```
    """
    try:
        service = get_portfolio_service()
        portfolio = service.update_portfolio(
            portfolio_id=portfolio_id,
            name=request.name,
            description=request.description,
            tickers=request.tickers,
            metadata=request.metadata
        )
        
        if not portfolio:
            return err(f"Portfolio {portfolio_id} not found", code=404)
        
        return ok(portfolio.model_dump())
    except Exception as e:
        return err(f"Failed to update portfolio: {str(e)}", code=500)


@router.delete("/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: str):
    """
    Delete a portfolio
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "deleted": true,
        "id": "uuid"
      }
    }
    ```
    """
    try:
        service = get_portfolio_service()
        deleted = service.delete_portfolio(portfolio_id)
        
        if not deleted:
            return err(f"Portfolio {portfolio_id} not found", code=404)
        
        return ok({
            "deleted": True,
            "id": portfolio_id
        })
    except Exception as e:
        return err(f"Failed to delete portfolio: {str(e)}", code=500)


@router.post("/portfolios/{portfolio_id}/tickers")
def add_tickers(portfolio_id: str, request: TickersRequest):
    """
    Add tickers to portfolio
    
    **Request Body:**
    ```json
    {
      "tickers": ["NVDA", "AMD"]
    }
    ```
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "uuid",
        "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD"],
        ...
      }
    }
    ```
    """
    try:
        service = get_portfolio_service()
        portfolio = service.add_tickers(portfolio_id, request.tickers)
        
        if not portfolio:
            return err(f"Portfolio {portfolio_id} not found", code=404)
        
        return ok(portfolio.model_dump())
    except Exception as e:
        return err(f"Failed to add tickers: {str(e)}", code=500)


@router.delete("/portfolios/{portfolio_id}/tickers/{ticker}")
def remove_ticker(portfolio_id: str, ticker: str):
    """
    Remove a ticker from portfolio
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "id": "uuid",
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        ...
      }
    }
    ```
    """
    try:
        service = get_portfolio_service()
        portfolio = service.remove_tickers(portfolio_id, [ticker])
        
        if not portfolio:
            return err(f"Portfolio {portfolio_id} not found", code=404)
        
        return ok(portfolio.model_dump())
    except Exception as e:
        return err(f"Failed to remove ticker: {str(e)}", code=500)


@router.get("/portfolios/{portfolio_id}/performance")
def get_portfolio_performance(
    portfolio_id: str,
    benchmark: str = Query("SPY", description="Benchmark ticker")
):
    """
    Get portfolio performance metrics
    
    **Query Parameters:**
    - `benchmark`: Benchmark ticker (default: SPY)
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "portfolio_id": "uuid",
        "portfolio_name": "Tech Watchlist",
        "tickers_count": 5,
        "total_return": 0.15,
        "avg_return": 0.03,
        "volatility": 0.25,
        "sharpe_ratio": 1.2,
        "vs_benchmark": {
          "benchmark": "SPY",
          "outperformance": 0.05
        },
        "calculated_at": "2025-11-06T..."
      }
    }
    ```
    
    **Note:** Performance calculation is a placeholder.
    Real implementation would require historical price data.
    """
    try:
        service = get_portfolio_service()
        performance = service.get_performance(portfolio_id, benchmark)
        
        if not performance:
            return err(f"Portfolio {portfolio_id} not found", code=404)
        
        return ok(performance.model_dump())
    except Exception as e:
        return err(f"Failed to get performance: {str(e)}", code=500)


@router.get("/portfolios/{portfolio_id}/performance/timeseries")
def get_portfolio_performance_timeseries(
    portfolio_id: str,
    benchmark: str = Query("SPY", description="Benchmark ticker"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get portfolio performance time series data for charts
    
    **Query Parameters:**
    - `benchmark`: Benchmark ticker (default: SPY)
    - `start_date`: Start date (YYYY-MM-DD), defaults to 1 year ago
    - `end_date`: End date (YYYY-MM-DD), defaults to today
    
    **Returns:**
    ```json
    {
      "ok": true,
      "data": {
        "portfolio": {
          "dates": ["2024-01-01", "2024-01-02", ...],
          "equity_curve": [100, 101.5, 103.2, ...],
          "drawdown": [0, -0.5, -1.2, ...],
          "returns": [0, 1.5, 1.7, ...]
        },
        "benchmark": {
          "dates": ["2024-01-01", "2024-01-02", ...],
          "equity_curve": [100, 100.8, 101.5, ...],
          "returns": [0, 0.8, 0.7, ...]
        },
        "metrics": {
          "total_return": 0.287,
          "annualized_return": 0.287,
          "volatility": 0.312,
          "sharpe_ratio": 0.92,
          "max_drawdown": -0.185,
          "win_rate": 0.537
        },
        "comparison": {
          "benchmark_ticker": "SPY",
          "portfolio_return": 0.287,
          "benchmark_return": 0.241,
          "outperformance": 0.046,
          "correlation": 0.84,
          "beta": 1.15,
          "alpha": 0.018
        }
      }
    }
    ```
    
    **Note:** Requires yfinance for historical data fetching.
    """
    try:
        service = get_portfolio_service()
        portfolio = service.get_portfolio(portfolio_id)
        
        if not portfolio:
            return err(f"Portfolio {portfolio_id} not found", code=404)
        
        if not portfolio.tickers:
            return err("Portfolio has no tickers", code=400)
        
        # Use performance service for calculations
        from backend.services.portfolio_performance_service import get_performance_service
        
        perf_service = get_performance_service()
        metrics, comparison, portfolio_timeseries = perf_service.calculate_performance(
            tickers=portfolio.tickers,
            weights=None,  # Equal-weighted
            start_date=start_date,
            end_date=end_date,
            benchmark=benchmark
        )
        
        # Also calculate benchmark timeseries
        _, _, benchmark_timeseries = perf_service.calculate_performance(
            tickers=[benchmark],
            weights=None,
            start_date=start_date,
            end_date=end_date,
            benchmark=benchmark
        )
        
        return ok({
            "portfolio": portfolio_timeseries.model_dump(),
            "benchmark": benchmark_timeseries.model_dump(),
            "metrics": metrics.model_dump(),
            "comparison": comparison.model_dump()
        })
        
    except Exception as e:
        return err(f"Failed to get performance timeseries: {str(e)}", code=500)
