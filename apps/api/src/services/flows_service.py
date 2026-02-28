"""Compatibility capital-flow service."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.service_standard import utc_now_iso, unwrap_storage_payload
from storage.io import load_json


def get_capital_flows(tickers: Optional[List[str]] = None, lookback_days: int = 30) -> Dict[str, Any]:
    del tickers, lookback_days  # kept for API parity with legacy caller signatures
    data = load_json("flows/capital") or load_json("flows/capital.json")
    payload = unwrap_storage_payload(data) if data else {}
    if isinstance(payload, dict):
        return payload
    return {
        "nodes": [],
        "links": [],
        "lookback_days": lookback_days,
        "generated_at": utc_now_iso(),
    }

