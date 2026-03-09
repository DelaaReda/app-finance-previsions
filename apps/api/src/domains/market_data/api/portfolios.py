"""
Portfolios & watchlists endpoints.
Exposes the storage-backed portfolio service plus performance analytics so the
dashboard widgets stop hitting 404.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
import logging
from core.response import ok

try:
    from services import portfolio_service as _portfolio_module
    from services import portfolio_performance_service as _performance_module
except Exception:  # pragma: no cover
    try:
        from domains.market_data.application import portfolio_service as _portfolio_module
        from domains.market_data.application import (
            portfolio_performance_service as _performance_module,
        )
    except Exception:
        _portfolio_module = None
        _performance_module = None
        _get_performance_service = None
    else:
        _get_performance_service = lambda: _performance_module.get_performance_service()  # type: ignore[union-attr]
else:
    _get_performance_service = lambda: _performance_module.get_performance_service()  # type: ignore[union-attr]

if _portfolio_module is None or _performance_module is None or _get_performance_service is None:
    raise ImportError("Unable to load portfolio service modules.")

try:
    from services.service_standard import ensure_decision_contract, utc_now_iso  # type: ignore
except Exception:  # pragma: no cover
    try:
        from platform.legacy.services.service_standard import (  # type: ignore
            ensure_decision_contract,
            utc_now_iso,
        )
    except Exception:  # pragma: no cover
        ensure_decision_contract = None  # type: ignore
        utc_now_iso = None  # type: ignore

get_portfolio_service = _portfolio_module.get_portfolio_service
Portfolio = _portfolio_module.Portfolio
PortfolioPerformance = _portfolio_module.PortfolioPerformance
PortfolioRiskProfile = _portfolio_module.PortfolioRiskProfile

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    if callable(utc_now_iso):
        return utc_now_iso()
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _apply_portfolio_contract(payload: Dict[str, Any], *, source: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload

    now_iso = payload.get("generated_at") or payload.get("freshness") or _now_iso()
    payload.setdefault("generated_at", now_iso)
    payload.setdefault("freshness", now_iso)
    payload.setdefault("last_update", payload.get("last_update") or now_iso)
    payload.setdefault("source", [source])

    if callable(ensure_decision_contract):
        ensure_decision_contract(
            payload,
            default_source=source,
            verdict=payload.get("verdict", "hold"),
            confidence=payload.get("confidence") or 0.45,
            why=payload.get("why")
            or ["Portfolio payload is informational and supports dashboard context."],
            risk_level=payload.get("risk_level")
            or (payload.get("risk", {}).get("level") if isinstance(payload.get("risk"), dict) else None),
            freshness=payload.get("freshness"),
        )
        return payload

    payload.setdefault("verdict", "hold")
    payload.setdefault("confidence", 0.45)
    payload.setdefault("why", ["Portfolio payload is informational and supports dashboard context."])
    payload.setdefault("risk_level", "low")
    payload.setdefault("risk", {"level": "low", "caveat": ""})
    payload.setdefault("risk_flag", False)
    return payload


def _ok(payload: Dict[str, Any], *, source: str) -> Dict[str, Any]:
    return {"ok": True, "data": _apply_portfolio_contract(payload, source=source)}


def _error_payload(*, source: str, error: str, route_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = dict(route_payload or {})
    payload.setdefault("error", error)
    payload.setdefault("message", "Portfolio API temporarily unavailable.")
    payload.setdefault("source", [source, "critical_route_error_fallback"])
    return _ok(payload, source=source)

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


def _serialize_risk_profile(profile: PortfolioRiskProfile) -> Dict[str, Any]:
    return profile.model_dump()


@router.get("/portfolios")
def list_portfolios():
    try:
        service = get_portfolio_service()
        portfolios = service.list_portfolios()
        return _ok(
            {
                "portfolios": [_serialize_portfolio(p) for p in portfolios],
                "count": len(portfolios),
            },
            source="portfolio_list",
        )
    except Exception as exc:
        logger.error("Error listing portfolios: %s", exc, exc_info=True)
        return _error_payload(
            source="portfolio_list",
            error=str(exc),
            route_payload={"count": 0, "portfolios": []},
        )


@router.post("/portfolios", status_code=status.HTTP_201_CREATED)
def create_portfolio(request: PortfolioCreateRequest):
    try:
        service = get_portfolio_service()
        portfolio = service.create_portfolio(
            name=request.name,
            description=request.description,
            tickers=request.tickers,
            metadata=request.metadata,
        )
        return _ok(_serialize_portfolio(portfolio), source="portfolio_create")
    except Exception as exc:
        logger.error("Error creating portfolio: %s", exc, exc_info=True)
        return _error_payload(
            source="portfolio_create",
            error=str(exc),
            route_payload={},
        )


@router.get("/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    try:
        service = get_portfolio_service()
        portfolio = service.get_portfolio(portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found",
            )
        return _ok(_serialize_portfolio(portfolio), source="portfolio_get")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error getting portfolio %s: %s",
            portfolio_id,
            exc,
            exc_info=True,
        )
        return _error_payload(
            source="portfolio_get",
            error=str(exc),
            route_payload={"id": portfolio_id},
        )


@router.put("/portfolios/{portfolio_id}")
def update_portfolio(portfolio_id: str, request: PortfolioUpdateRequest):
    try:
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
        return _ok(_serialize_portfolio(portfolio), source="portfolio_update")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error updating portfolio %s: %s",
            portfolio_id,
            exc,
            exc_info=True,
        )
        return _error_payload(
            source="portfolio_update",
            error=str(exc),
            route_payload={"id": portfolio_id},
        )


@router.delete("/portfolios/{portfolio_id}")
def delete_portfolio(portfolio_id: str):
    try:
        service = get_portfolio_service()
        deleted = service.delete_portfolio(portfolio_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found",
            )
        return _ok({"deleted": True, "id": portfolio_id}, source="portfolio_delete")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting portfolio %s: %s", portfolio_id, exc, exc_info=True)
        return _error_payload(
            source="portfolio_delete",
            error=str(exc),
            route_payload={"id": portfolio_id},
        )


@router.post("/portfolios/{portfolio_id}/tickers")
def add_tickers(portfolio_id: str, request: TickersRequest):
    try:
        service = get_portfolio_service()
        portfolio = service.add_tickers(portfolio_id, request.tickers)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found",
            )
        return _ok(
            _serialize_portfolio(portfolio),
            source="portfolio_add_tickers",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error adding tickers to portfolio %s: %s",
            portfolio_id,
            exc,
            exc_info=True,
        )
        return _error_payload(
            source="portfolio_add_tickers",
            error=str(exc),
            route_payload={"id": portfolio_id},
        )


@router.delete("/portfolios/{portfolio_id}/tickers/{ticker}")
def remove_ticker(portfolio_id: str, ticker: str):
    try:
        service = get_portfolio_service()
        portfolio = service.remove_tickers(portfolio_id, [ticker])
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found",
            )
        return _ok(
            _serialize_portfolio(portfolio),
            source="portfolio_remove_ticker",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error removing ticker from portfolio %s: %s",
            portfolio_id,
            exc,
            exc_info=True,
        )
        return _error_payload(
            source="portfolio_remove_ticker",
            error=str(exc),
            route_payload={"id": portfolio_id, "ticker": ticker},
        )


@router.get("/portfolios/{portfolio_id}/performance")
def get_portfolio_performance(
    portfolio_id: str, benchmark: str = Query("SPY", description="Benchmark ticker")
):
    try:
        service = get_portfolio_service()
        performance = service.get_performance(portfolio_id, benchmark=benchmark)
        if not performance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found",
            )
        return _ok(
            _serialize_performance(performance),
            source="portfolio_performance",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error getting portfolio performance %s: %s",
            portfolio_id,
            exc,
            exc_info=True,
        )
        return _error_payload(
            source="portfolio_performance",
            error=str(exc),
            route_payload={"id": portfolio_id},
        )


@router.get("/portfolios/{portfolio_id}/risk-profile")
def get_portfolio_risk_profile(
    portfolio_id: str,
    benchmark: str = Query("SPY", description="Benchmark ticker"),
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD). Defaults to 1 year ago."
    ),
    end_date: Optional[str] = Query(
        None, description="End date (YYYY-MM-DD). Defaults to today."
    ),
):
    try:
        service = get_portfolio_service()
        risk_profile = service.get_risk_profile(
            portfolio_id,
            benchmark=benchmark,
            start_date=start_date,
            end_date=end_date,
        )
        if not risk_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found",
            )
        return _ok(
            _serialize_risk_profile(risk_profile),
            source="portfolio_risk_profile",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error getting portfolio risk profile %s: %s",
            portfolio_id,
            exc,
            exc_info=True,
        )
        return _error_payload(
            source="portfolio_risk_profile",
            error=str(exc),
            route_payload={
                "id": portfolio_id,
                "benchmark": benchmark,
                "start_date": start_date,
                "end_date": end_date,
            },
        )


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
    try:
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

        return _ok(
            {
                "portfolio": portfolio_timeseries.model_dump(),
                "benchmark": benchmark_timeseries.model_dump(),
                "metrics": metrics.model_dump(),
                "comparison": comparison.model_dump(),
            },
            source="portfolio_performance_timeseries",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error getting portfolio performance timeseries %s: %s",
            portfolio_id,
            exc,
            exc_info=True,
        )
        return _error_payload(
            source="portfolio_performance_timeseries",
            error=str(exc),
            route_payload={"id": portfolio_id},
        )
