"""
Merged forecasts routes: delegate to api.routes.forecasts to avoid duplicate logic.
Kept as a thin wrapper so any legacy imports still work.
"""

from ..forecasts import forecasts_router, router

__all__ = ["router", "forecasts_router"]
