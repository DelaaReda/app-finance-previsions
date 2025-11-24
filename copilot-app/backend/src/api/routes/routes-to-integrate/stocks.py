"""
Merged stocks routes: use api.routes.stocks as the canonical implementation.
Thin wrapper retained so legacy imports continue to resolve.
"""

from ..stocks import router, stocks_router

__all__ = ["router", "stocks_router"]
