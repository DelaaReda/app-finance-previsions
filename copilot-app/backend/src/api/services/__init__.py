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
    get_news_feed
)

# Only import get_sentiment if it exists 
try:
    from api.services.news_service import get_sentiment
except ImportError:
    # Define a placeholder if the function doesn't exist
    async def get_sentiment(*args, **kwargs):
        return {"sentiment": [], "count": 0}

__all__ = [
    "get_macro_overview",
    "get_macro_snapshot",
    "get_macro_indicators",
    "get_stock_overview",
    "get_stock_universe",
    "get_news_feed",
]

# Add get_sentiment to __all__ if it was successfully imported
import sys
current_module = sys.modules[__name__]
if hasattr(current_module, 'get_sentiment'):
    __all__.append("get_sentiment")
