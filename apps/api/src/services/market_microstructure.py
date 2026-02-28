"""Compatibility orderbook service."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from services.service_standard import unwrap_storage_payload
from storage.io import load_json


def _extract_orderbook(raw: Any, ticker: str) -> Dict[str, Any]:
    payload = unwrap_storage_payload(raw or {})
    if isinstance(payload, dict):
        if "data" in payload and isinstance(payload["data"], dict):
            return payload["data"]
        if "payload" in payload and isinstance(payload["payload"], dict):
            return payload["payload"]
        if payload:
            return payload
    return {
        "ticker": ticker,
        "bids": [],
        "asks": [],
        "lastPrice": 0.0,
        "spread": 0.0,
        "spreadPct": 0.0,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_orderbook(ticker: str) -> Dict[str, Any]:
    ticker = ticker.upper()
    return _extract_orderbook(load_json(f"market/orderbook_{ticker}"), ticker)

