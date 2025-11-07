"""
Portfolios & watchlists endpoints.
Exposes the storage-backed portfolio service plus performance analytics so the
dashboard widgets stop hitting 404.
"""
from typing import Any, Dict, List, Optional
from importlib import util as importlib_util
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _load_legacy_module(name: str, relative_path: str):
    module_path = _BACKEND_ROOT / relative_path
    spec = importlib_util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module {name} from {module_path}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_portfolio_module = _load_legacy_module(
    "legacy_portfolio_service",
    "services/portfolio_service.py",
)
_performance_module = None


def _get_performance_service():
    global _performance_module
    if _performance_module is None:
        _performance_module = _load_legacy_module(
            "legacy_portfolio_performance_service",
            "services/portfolio_performance_service.py",
        )
    return _performance_module.get_performance_service()


get_portfolio_service = _portfolio_module.get_portfolio_service
Portfolio = _portfolio_module.Portfolio
PortfolioPerformance = _portfolio_module.PortfolioPerformance

router = APIRouter(prefix="/api", tags=["portfolios"])


class PortfolioCreateRequest(BaseModel):
    """Payload for creating a new portfolio/watchlist."""

    name: str = Field(..., description="Portfolio name", example="Tech Watchlist")
    description: str = Field(default="", description="Optional description")
    tickers: List[str] = Field(
        default_factory=list,
        description="Initial tickers (uppercased automatically)",
        example=["AAPL", "MSFT", "NVDA"],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Arbitrary metadata stored alongside the portfolio"
    )


class PortfolioUpdateRequest(BaseModel):
    """Partial update payload."""

    name: Optional[str] = Field(None, description="New name")
    description: Optional[str] = Field(None, description="New description")
    tickers: Optional[List[str]] = Field(
        None, description="Full replacement list of tickers"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Replacement metadata object"
    )


class TickersRequest(BaseModel):
    """Add/remove tickers."""

    tickers: List[str] = Field(
        ..., description="Ticker symbols", example=["SPY", "QQQ"]
    )


def _serialize_portfolio(portfolio: Portfolio) -> Dict[str, Any]:
    return portfolio.model_dump()


def _serialize_performance(perf: PortfolioPerformance) -> Dict[str, Any]:
    return perf.model_dump()


@router.get("/portfolios")
def list_portfolios():
    service = get_portfolio_service()
    portfolios = service.list_portfolios()
    return {
        "ok": True,
        "data": {
            "portfolios": [_serialize_portfolio(p) for p in portfolios],
            "count": len(portfolios),
        },
    }


@router.post("/portfolios", status_code=status.HTTP_201_CREATED)
def create_portfolio(request: PortfolioCreateRequest):
    service = get_portfolio_service()
    portfolio = service.create_portfolio(
        name=request.name,
        description=request.description,
        tickers=request.tickers,
        metadata=request.metadata,
    )
    return {"ok": True, "data": _serialize_portfolio(portfolio)}


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    service = get_portfolio_service()
    portfolio = service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return {"ok": True, "data": _serialize_portfolio(portfolio)}


@router.put("/portfolios/{portfolio_id}")
def update_portfolio(portfolio_id: str, request: PortfolioUpdateRequest):
    service = get_portfolio_service()
    portfolio = service.update_portfolio(
        portfolio_id=portfolio_id,
        name=request.name,
        description=request.description,
        tickers=request.tickers,
        metadata=request.metadata,
    )
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return {"ok": True, "data": _serialize_portfolio(portfolio)}


@router.delete("/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: str):
    service = get_portfolio_service()
    deleted = service.delete_portfolio(portfolio_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return {"ok": True, "data": {"deleted": True, "id": portfolio_id}}


@router.post("/portfolios/{portfolio_id}/tickers")
def add_tickers(portfolio_id: str, request: TickersRequest):
    service = get_portfolio_service()
    portfolio = service.add_tickers(portfolio_id, request.tickers)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return {"ok": True, "data": _serialize_portfolio(portfolio)}


@router.delete("/portfolios/{portfolio_id}/tickers/{ticker}")
def remove_ticker(portfolio_id: str, ticker: str):
    service = get_portfolio_service()
    portfolio = service.remove_tickers(portfolio_id, [ticker])
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return {"ok": True, "data": _serialize_portfolio(portfolio)}


@router.get("/portfolios/{portfolio_id}/performance")
def get_portfolio_performance(
    portfolio_id: str, benchmark: str = Query("SPY", description="Benchmark ticker")
):
    service = get_portfolio_service()
    performance = service.get_performance(portfolio_id, benchmark=benchmark)
    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    return {"ok": True, "data": _serialize_performance(performance)}


@router.get("/portfolios/{portfolio_id}/performance/timeseries")
def get_portfolio_performance_timeseries(
    portfolio_id: str,
    benchmark: str = Query("SPY", description="Benchmark ticker"),
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD). Defaults to 1 year ago."
    ),
    end_date: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD). Defaults to today."
    ),
):
    service = get_portfolio_service()
    portfolio = service.get_portfolio(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found",
        )
    if not portfolio.tickers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio has no tickers to evaluate",
        )

    perf_service = _get_performance_service()
    metrics, comparison, portfolio_timeseries = perf_service.calculate_performance(
        tickers=portfolio.tickers,
        weights=None,
        start_date=start_date,
        end_date=end_date,
        benchmark=benchmark,
    )

    _, _, benchmark_timeseries = perf_service.calculate_performance(
        tickers=[benchmark],
        weights=None,
        start_date=start_date,
        end_date=end_date,
        benchmark=benchmark,
    )

    return {
        "ok": True,
        "data": {
            "portfolio": portfolio_timeseries.model_dump(),
            "benchmark": benchmark_timeseries.model_dump(),
            "metrics": metrics.model_dump(),
            "comparison": comparison.model_dump(),
        },
    }
