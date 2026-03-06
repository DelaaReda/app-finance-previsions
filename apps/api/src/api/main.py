"""Compatibility wrapper for legacy import paths."""

from __future__ import annotations

import importlib

_FACTORY = importlib.import_module("platform.app_factory")
_LEGACY = importlib.import_module("platform.main")
create_app = _FACTORY.create_app  # type: ignore[attr-defined]
_STOCKS_PRICES_RESPONSE_CACHE = _LEGACY._STOCKS_PRICES_RESPONSE_CACHE  # type: ignore[attr-defined]
_NEWS_FEED_RESPONSE_CACHE = _LEGACY._NEWS_FEED_RESPONSE_CACHE  # type: ignore[attr-defined]

__all__ = [
    "create_app",
    "_STOCKS_PRICES_RESPONSE_CACHE",
    "_NEWS_FEED_RESPONSE_CACHE",
]
