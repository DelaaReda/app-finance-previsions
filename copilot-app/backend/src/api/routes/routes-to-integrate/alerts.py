"""
Merged alerts routes: re-export canonical implementation from api.routes.alerts.
This keeps a single source of truth while preserving any legacy imports that
still point at routes-to-integrate.
"""

from ..alerts import router as router

# Backward compatibility alias (some code expects `alerts_router`)
alerts_router = router

__all__ = ["router", "alerts_router"]
