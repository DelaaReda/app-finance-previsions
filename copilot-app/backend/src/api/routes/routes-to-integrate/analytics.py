"""
Merged analytics routes: rely on api.routes.analytics as the canonical source.
This module re-exports the router for compatibility with legacy imports.
"""

from ..analytics import router as router

__all__ = ["router"]
