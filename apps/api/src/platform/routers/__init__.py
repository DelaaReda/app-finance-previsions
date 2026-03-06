from .health import create_health_router
from .macro import create_macro_router
from .stocks import create_stocks_router
from .news import create_news_router
from .forecasts import create_forecasts_router
from .brief import create_brief_router
from .copilot import create_copilot_router
from .notes import create_notes_router
from .rag import create_rag_router
from .signals import create_signals_router
from .critical import create_critical_router

__all__ = [
    "create_health_router",
    "create_macro_router",
    "create_stocks_router",
    "create_news_router",
    "create_forecasts_router",
    "create_brief_router",
    "create_copilot_router",
    "create_notes_router",
    "create_rag_router",
    "create_signals_router",
    "create_critical_router",
]
