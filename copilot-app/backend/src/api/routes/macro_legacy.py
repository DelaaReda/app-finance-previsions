"""
Compat wrapper for legacy macro routes from ``api.routes.macro``.

This allows the modern ``src.api.main`` application factory to expose
the same macro endpoints without rewriting their internals yet.
"""
from __future__ import annotations

from fastapi import APIRouter

try:
  # Import the existing router from the legacy api.routes package.
  from api.routes.macro import macro_router as legacy_macro_router  # type: ignore
except Exception:  # pragma: no cover
  legacy_macro_router = APIRouter()

router = legacy_macro_router

