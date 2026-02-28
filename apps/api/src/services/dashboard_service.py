"""Compatibility wrapper for dashboard-related service helpers."""

from domains.market_data.application.dashboard_ui_service import (  # type: ignore
    build_market_drivers_snapshot,
    build_news_impact_table,
    build_performance_snapshot,
    build_portfolio_summary,
    load_portfolio_allocation,
    build_portfolio_health,
)

__all__ = [
    "build_market_drivers_snapshot",
    "build_news_impact_table",
    "build_performance_snapshot",
    "build_portfolio_summary",
    "load_portfolio_allocation",
    "build_portfolio_health",
]
