"""
Dashboard API routes (KPI + UI aggregates) - fixed version.

This module exposes high-level dashboard endpoints used by both the
legacy React app and the new V16 HTML UI:

- /api/dashboard/kpis              → simple KPI counters
- /api/dashboard/portfolio-summary → hero / portfolio summary widget
- /api/dashboard/allocation        → treemap + sector allocation widget
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import sys

from fastapi import APIRouter

# Ensure backend root is on sys.path so we can reuse the shared storage
# layer and the V16 dashboard UI services that live under src/.
backend_root = Path(__file__).resolve().parent.parent
src_path = backend_root / "src"
for p in (backend_root, src_path):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

from storage.io import load_json  # type: ignore

try:
    # Prefer the V16/V17 UI helpers so behaviour stays consistent with src.api.
    from src.api.services.dashboard_ui_service import (  # type: ignore
        build_portfolio_summary,
        build_portfolio_health,
        build_market_drivers_snapshot,
        build_news_impact_table,
        build_performance_snapshot,
        load_portfolio_allocation,
    )
except Exception:  # pragma: no cover - defensive fallback
    build_portfolio_summary = None  # type: ignore
    build_portfolio_health = None  # type: ignore
    build_market_drivers_snapshot = None  # type: ignore
    build_news_impact_table = None  # type: ignore
    build_performance_snapshot = None  # type: ignore
    load_portfolio_allocation = None  # type: ignore


# Create router instance
dashboard_router = APIRouter(tags=["dashboard"])


@dashboard_router.get("/kpis")
async def dashboard_kpis() -> Dict[str, Any]:
    """Get dashboard KPIs with real data."""
    try:
        forecasts_data = load_json("forecasts") or {}
        news_data = load_json("news_feed") or {}

        forecast_rows = forecasts_data.get("rows", [])
        articles = news_data.get("articles", [])

        total_forecasts = len(forecast_rows)
        high_conf_count = sum(
            1 for r in forecast_rows if (r.get("confidence") or 0) >= 0.6
        )
        bullish = sum(1 for r in forecast_rows if r.get("direction") == "up")
        bearish = sum(1 for r in forecast_rows if r.get("direction") == "down")

        news_count = len(articles)
        positive_news = sum(
            1 for a in articles if (a.get("sentiment_score") or 0) >= 0.1
        )

        return {
            "ok": True,
            "data": {
                "kpi_forecasts": {
                    "active_forecasts": total_forecasts,
                    "high_confidence_forecasts": high_conf_count,
                    "bullish_signals": bullish,
                    "bearish_signals": bearish,
                },
                "kpi_news": {
                    "total_news": news_count,
                    "positive_news": positive_news,
                },
                "health": {
                    "forecasts_available": total_forecasts > 0,
                    "news_available": news_count > 0,
                    "overall_health": (
                        "healthy" if (total_forecasts > 0 and news_count > 0) else "degraded"
                    ),
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
        }
    except Exception as e:  # never-empty fallback
        return {
            "ok": True,
            "data": {
                "kpi_forecasts": {
                    "active_forecasts": 0,
                    "high_confidence_forecasts": 0,
                    "bullish_signals": 0,
                    "bearish_signals": 0,
                },
                "kpi_news": {"total_news": 0, "positive_news": 0},
                "health": {"overall_health": "error"},
                "error": str(e),
            },
        }


@dashboard_router.get("/portfolio-summary")
async def get_portfolio_summary() -> Dict[str, Any]:
    """
    Aggregated portfolio summary used by the hero / Portfolio Summary
    widget in the new UI.
    """
    now = datetime.utcnow().isoformat() + "Z"
    try:
        if build_portfolio_summary is None:
            raise RuntimeError("dashboard_ui_service.build_portfolio_summary unavailable")
        summary = build_portfolio_summary()
        return {
            "ok": True,
            "data": summary,
            "freshness": summary.get("generated_at", now),
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "portfolio_value": None,
                "initial_capital": None,
                "total_return_pct": None,
                "win_rate_pct": None,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "forecast_next_30d_pct": None,
                "forecast_confidence_pct": None,
                "total_forecasts": 0,
                "generated_at": now,
                "error": str(e),
                "source": ["dashboard_ui_service", "error_fallback"],
            },
            "freshness": now,
        }


@dashboard_router.get("/allocation")
async def get_portfolio_allocation() -> Dict[str, Any]:
    """
    Portfolio allocation snapshot used by the treemap + sector summary
    widgets in the new UI.
    """
    now = datetime.utcnow().isoformat() + "Z"
    try:
        if load_portfolio_allocation is None:
            raise RuntimeError("dashboard_ui_service.load_portfolio_allocation unavailable")
        payload = load_portfolio_allocation()
        return {
            "ok": True,
            "data": payload,
            "freshness": payload.get("generated_at", now),
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "holdings": [],
                "sectors": [],
                "total_value": 0.0,
                "generated_at": now,
                "error": str(e),
                "source": ["dashboard_ui_service", "allocation_error_fallback"],
            },
            "freshness": now,
        }


@dashboard_router.get("/health")
async def get_portfolio_health() -> Dict[str, Any]:
    """
    Portfolio health score + backtest metrics snapshot for the
    Portfolio Health widget (compat path when running via api.main).
    """
    now = datetime.utcnow().isoformat() + "Z"
    try:
        if build_portfolio_health is None:
            raise RuntimeError("dashboard_ui_service.build_portfolio_health unavailable")
        payload = build_portfolio_health()
        return {
            "ok": True,
            "data": payload,
            "freshness": payload.get("generated_at", now),
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "portfolio_health": {
                    "overall": 50,
                    "suggestion": "Indicateurs de backtest indisponibles (fallback).",
                },
                "backtest_results": {
                    "sharpe_ratio": None,
                    "win_rate_pct": None,
                    "max_drawdown_pct": None,
                    "total_return_pct": None,
                },
                "generated_at": now,
                "error": str(e),
                "source": ["dashboard_ui_service", "health_error_fallback"],
            },
            "freshness": now,
        }


@dashboard_router.get("/market-drivers")
async def get_market_drivers() -> Dict[str, Any]:
    """
    Compact snapshot of what's driving the portfolio (Technique,
    Nouvelles, Macro, Sentiment) when running through api.main.
    """
    now = datetime.utcnow().isoformat() + "Z"
    try:
        if build_market_drivers_snapshot is None:
            raise RuntimeError("dashboard_ui_service.build_market_drivers_snapshot unavailable")
        payload = build_market_drivers_snapshot()
        return {
            "ok": True,
            "data": payload,
            "freshness": payload.get("generated_at", now),
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "drivers": [],
                "totals": {},
                "generated_at": now,
                "error": str(e),
                "source": ["dashboard_ui_service", "market_drivers_error_fallback"],
            },
            "freshness": now,
        }


@dashboard_router.get("/news-impact")
async def get_news_impact() -> Dict[str, Any]:
    """
    News Impact table used by the overview widget, built from the real
    cached news feed (compat path via api.main).
    """
    now = datetime.utcnow().isoformat() + "Z"
    try:
        if build_news_impact_table is None:
            raise RuntimeError("dashboard_ui_service.build_news_impact_table unavailable")
        payload = build_news_impact_table(limit=10)
        return {
            "ok": True,
            "data": payload,
            "freshness": payload.get("generated_at", now),
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "items": [],
                "count": 0,
                "generated_at": now,
                "error": str(e),
                "source": ["dashboard_ui_service", "news_impact_error_fallback"],
            },
            "freshness": now,
        }


@dashboard_router.get("/performance")
async def get_performance_snapshot() -> Dict[str, Any]:
    """
    Top stocks + opportunities snapshot for the performance widget
    (compat path via api.main).
    """
    now = datetime.utcnow().isoformat() + "Z"
    try:
        if build_performance_snapshot is None:
            raise RuntimeError("dashboard_ui_service.build_performance_snapshot unavailable")
        payload = build_performance_snapshot()
        return {
            "ok": True,
            "data": payload,
            "freshness": payload.get("generated_at", now),
        }
    except Exception as e:
        return {
            "ok": True,
            "data": {
                "top_stocks": [],
                "opportunities": [],
                "generated_at": now,
                "error": str(e),
                "source": ["dashboard_ui_service", "performance_error_fallback"],
            },
            "freshness": now,
        }


# Export router with expected names for the different app factories
router = dashboard_router
dashboard_router = dashboard_router
