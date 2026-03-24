from __future__ import annotations

import importlib.util
from typing import Any

from .compat import PYDANTIC_ENABLED


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def build_runtime_capabilities() -> dict[str, Any]:
    return {
        "pydantic_enabled": PYDANTIC_ENABLED,
        "pydantic_ai_enabled": _module_available("pydantic_ai"),
        "langgraph_enabled": _module_available("langgraph"),
        "langgraph_graph_enabled": _module_available("langgraph.graph"),
    }
