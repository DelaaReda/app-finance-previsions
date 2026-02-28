"""
Dashboard endpoints tailored for the V16/V17 frontend.

These routes expose high-level, UI-ready aggregates built on top of the
existing cached JSON files (forecasts, backtests, dashboard kpis, etc.).

They are intentionally light-weight and rely on the storage/cache layer
instead of recomputing heavy analytics on each request.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

# Reuse the shared V16 dashboard UI service helpers living under src/.
# We use a relative import so this module works regardless of how the
# backend package is mounted (avoids depending on ``backend.src``).
from ..services.dashboard_ui_service import (  # type: ignore
  build_portfolio_summary,
  build_portfolio_health,
  build_market_drivers_snapshot,
  build_news_impact_table,
  build_performance_snapshot,
  load_portfolio_allocation,
)

# IMPORTANT: create_app() in src/api/main.py imports `dashboard_router`
# and mounts it with `prefix="/api/dashboard"`. Therefore the paths
# below are relative to `/api/dashboard`.
dashboard_router = APIRouter(tags=["dashboard"])

@dashboard_router.get("/kpis-legacy")
async def dashboard_kpis() -> Dict[str, Any]:
  """Get dashboard KPIs with real data (never-empty fallback)."""
  try:
    forecasts_data = load_json("forecasts") or {}
    news_data = load_json("news_feed") or {}

    forecast_rows = forecasts_data.get("rows", []) or forecasts_data.get("data", {}).get("rows", [])
    articles = news_data.get("articles", []) or news_data.get("data", {}).get("articles", [])

    total_forecasts = len(forecast_rows)
    high_conf_count = sum(1 for r in forecast_rows if (r.get("confidence") or 0) >= 0.6)
    bullish = sum(1 for r in forecast_rows if r.get("direction") == "up")
    bearish = sum(1 for r in forecast_rows if r.get("direction") == "down")

    news_count = len(articles)
    positive_news = sum(1 for a in articles if (a.get("sentiment_score") or 0) >= 0.1)

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
          "overall_health": "healthy" if (total_forecasts > 0 and news_count > 0) else "degraded",
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
  Return the aggregated portfolio summary used by the hero / Portfolio
  Summary widget in the new UI.
  """
  try:
    summary = build_portfolio_summary()
    return {
      "ok": True,
      "data": summary,
      "freshness": summary.get("generated_at", datetime.utcnow().isoformat() + "Z"),
    }
  except Exception as e:
    # Never-empty contract: always return a well-formed payload, even on error.
    now = datetime.utcnow().isoformat() + "Z"
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
  Return the portfolio allocation snapshot used by the treemap +
  sector summary widgets in the new UI.
  """
  try:
    payload = load_portfolio_allocation()
    return {
      "ok": True,
      "data": payload,
      "freshness": payload.get("generated_at", datetime.utcnow().isoformat() + "Z"),
    }
  except Exception as e:
    now = datetime.utcnow().isoformat() + "Z"
    # Never-empty contract: always return a well-formed structure.
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
  Return portfolio health score + backtest metrics snapshot for the
  Portfolio Health widget.
  """
  now = datetime.utcnow().isoformat() + "Z"
  try:
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
  Return a compact snapshot of what's driving the portfolio (Technique,
  Nouvelles, Macro, Sentiment) based on real forecasts/news/macro data.
  """
  now = datetime.utcnow().isoformat() + "Z"
  try:
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
  Return the News Impact table used by the overview widget, built from
  the real cached news feed.
  """
  now = datetime.utcnow().isoformat() + "Z"
  try:
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
  Return top stocks + opportunities snapshot for the performance widget.
  """
  now = datetime.utcnow().isoformat() + "Z"
  try:
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


# For backward compatibility with older include patterns
router = dashboard_router
