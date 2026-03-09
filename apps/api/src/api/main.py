"""Compatibility wrapper for legacy import paths."""

from __future__ import annotations

import importlib
import sys
from importlib import util
from pathlib import Path


def _ensure_local_platform_package() -> None:
    module = sys.modules.get("platform")
    if module is not None and getattr(module, "__path__", None):
        return

    platform_dir = Path(__file__).resolve().parents[1] / "platform"
    spec = util.spec_from_file_location(
        "platform",
        platform_dir / "__init__.py",
        submodule_search_locations=[str(platform_dir)],
    )
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError("Unable to load local platform package")

    package = util.module_from_spec(spec)
    sys.modules["platform"] = package
    spec.loader.exec_module(package)


_ensure_local_platform_package()

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
