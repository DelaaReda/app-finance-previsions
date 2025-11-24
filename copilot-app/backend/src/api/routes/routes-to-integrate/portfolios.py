"""
Merged portfolios routes: re-export api.routes.portfolios to keep a single source
of truth and maintain compatibility with any legacy imports.
"""

from ..portfolios import router as router

__all__ = ["router"]
