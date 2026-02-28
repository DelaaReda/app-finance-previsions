"""Compatibility layer for legacy `backend.*` imports."""

from __future__ import annotations

import importlib
import sys


def _alias_package(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return
    setattr(sys.modules[__name__], module_name, module)
    sys.modules[f"{__name__}.{module_name}"] = module


for _mod in [
    "services",
    "jobs",
    "analytics",
    "agents",
    "storage",
    "core",
    "research",
    "runners",
    "models",
    "ingestion",
    "taxonomy",
    "scheduler",
]:
    _alias_package(_mod)

