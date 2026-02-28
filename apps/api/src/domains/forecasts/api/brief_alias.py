"""
Alias route to support /api/brief/{id} used by the frontend.
Maps 'daily' and 'weekly' to their respective endpoints, otherwise returns fallback.
"""
from __future__ import annotations

from fastapi import APIRouter
from typing import Any, Dict
from datetime import datetime

try:
    from storage.io import load_json
except Exception:  # pragma: no cover
    load_json = lambda key: None  # type: ignore

router = APIRouter(tags=["brief"])


def _ok(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "data": payload}


def _fallback(msg: str) -> Dict[str, Any]:
    return _ok({
        "summary": msg,
        "market_sentiment": "UNKNOWN",
        "top_signals": [],
        "top_risks": [],
        "key_events": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": ["brief_alias_fallback"],
    })


@router.get("/brief/{brief_id}")
async def get_brief_by_id(brief_id: str):
    if brief_id.lower() == "daily":
        data = load_json("brief_daily") or load_json("brief_weekly")
        if isinstance(data, dict):
            payload = data.get("data") if isinstance(data.get("data"), dict) else data
            return _ok(payload)
        return _fallback("No daily brief available yet.")

    if brief_id.lower() == "weekly":
        data = load_json("brief_weekly")
        if isinstance(data, dict):
            payload = data.get("data") if isinstance(data.get("data"), dict) else data
            return _ok(payload)
        return _fallback("No weekly brief available yet.")

    return _fallback("Unknown brief id.")

