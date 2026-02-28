"""
Compat wrapper for legacy news routes from ``api.routes.news*``.

We re-export the existing routers so that ``src.api.main`` can include
them without changing their internal logic.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

try:
  from api.routes.news import router as news_router  # type: ignore
  router.include_router(news_router)
except Exception:
  pass

try:
  from api.routes.news_features import router as news_features_router  # type: ignore
  router.include_router(news_features_router)
except Exception:
  pass

try:
  from api.routes.news_impact import router as news_impact_router  # type: ignore
  router.include_router(news_impact_router)
except Exception:
  pass

