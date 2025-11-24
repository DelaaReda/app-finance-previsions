"""
Merged dashboard routes: re-export canonical implementation from api.routes.dashboard.
Keeps a single implementation while preserving compatibility with legacy imports.
"""

from ..dashboard import dashboard_router, router

__all__ = ["dashboard_router", "router"]
