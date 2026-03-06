"""Critical endpoint wrappers (strangler entry points).

This module centralizes envelope policy for the three critical routes:
- forecasts
- recommendations/daily
- stocks/{ticker}/sheet
"""

from __future__ import annotations

from typing import Any, Dict

from .contracts import edge_degraded, edge_ok


def forecasts_ok(payload: Dict[str, Any]) -> Dict[str, Any]:
    freshness = payload.get("freshness_age")
    freshness_s = int(freshness) if isinstance(freshness, (int, float)) else None
    return edge_ok(
        payload,
        source=["forecasts_route", "forecasts_service"],
        freshness_s=freshness_s,
        fallback=bool(payload.get("fallback_used")),
    )


def forecasts_degraded(payload: Dict[str, Any], detail: Any) -> Dict[str, Any]:
    return edge_degraded(
        payload,
        code="forecasts_route_exception",
        message="Forecasts unavailable, degraded fallback payload returned.",
        detail=detail,
        source=["forecasts_route", "critical_route_error_fallback"],
        freshness_s=None,
        fallback=True,
    )


def recommendations_ok(payload: Dict[str, Any]) -> Dict[str, Any]:
    return edge_ok(
        payload,
        source=["recommendations_daily", "weekly_brief_snapshot"],
        fallback=False,
    )


def recommendations_degraded(payload: Dict[str, Any], detail: Any) -> Dict[str, Any]:
    return edge_degraded(
        payload,
        code="recommendations_unavailable",
        message="Recommendations temporarily unavailable, fallback payload returned.",
        detail=detail,
        source=["recommendations_daily", "critical_error_fallback"],
        fallback=True,
    )


def stocks_sheet_ok(payload: Dict[str, Any]) -> Dict[str, Any]:
    return edge_ok(
        payload,
        source=["stocks_sheet_route", "market_data"],
        fallback=False,
    )


def stocks_sheet_degraded(payload: Dict[str, Any], code: str, message: str, detail: Any, source: Any) -> Dict[str, Any]:
    return edge_degraded(
        payload,
        code=code,
        message=message,
        detail=detail,
        source=source,
        fallback=True,
    )

