# src/api/services/__init__.py
"""
Service facades for API endpoints.
Each service wraps existing Python modules without rewriting them.
"""

from api.services.macro_service import (
    get_macro_overview,
    get_macro_snapshot,
    get_macro_indicators
)

from api.services.stocks_service import (
    get_stock_overview,
    get_stock_universe
)

from api.services.news_service import (
    get_news_feed,
    get_sentiment
)

__all__ = [
    "get_macro_overview",
    "get_macro_snapshot",
    "get_macro_indicators",
    "get_stock_overview",
    "get_stock_universe",
    "get_news_feed",
    "get_sentiment",
]
