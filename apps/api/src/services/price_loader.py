"""Compatibility price loader fallback."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from core.market_data import get_price_history as _history
except Exception:
    _history = None


def get_price_history(ticker: str, days: int = 252) -> List[Dict[str, Any]]:
    if _history is None:
        return []
    data = _history(ticker, days=days)  # type: ignore[misc]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        out = data.get("points") if isinstance(data.get("points"), list) else []
        return out
    return []

