"""
Brief routes exposing daily/weekly market briefs generated offline.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter

from core.response import ok
from storage.io import load_json

router = APIRouter()


def _load_brief_snapshot(key: str) -> Optional[Dict[str, Any]]:
    snapshot = load_json(key)
    if not snapshot:
        return None
    payload = snapshot.get("data")
    if isinstance(payload, dict):
        return payload
    return snapshot if isinstance(snapshot, dict) else None


def _fallback_brief(message: str) -> Dict[str, Any]:
    return {
        "summary": message,
        "market_sentiment": "UNKNOWN",
        "top_signals": [],
        "top_risks": [],
        "key_events": [],
        "macro_signals": [],
        "sector_rotation": {"top": [], "bottom": []},
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": ["fallback_empty"],
    }


@router.get("/brief/daily")
def get_daily_brief() -> Dict[str, Any]:
    brief = _load_brief_snapshot("brief_daily") or _load_brief_snapshot("brief_weekly")
    if not brief:
        brief = _fallback_brief("No daily brief available yet.")

    brief.setdefault("macro_signals", brief.get("macro", brief.get("macro_signals", [])))
    if not isinstance(brief["macro_signals"], list):
        brief["macro_signals"] = []

    brief.setdefault("sector_rotation", brief.get("sector_rotation", {"top": [], "bottom": []}))
    if not isinstance(brief["sector_rotation"], dict):
        brief["sector_rotation"] = {"top": [], "bottom": []}
    else:
        brief["sector_rotation"].setdefault("top", [])
        brief["sector_rotation"].setdefault("bottom", [])

    summary = brief.get("summary", "")
    if isinstance(summary, str):
        words = summary.split()
        if len(words) > 200:
            brief["summary"] = " ".join(words[:200])

    return ok(brief)


@router.get("/brief/weekly")
def get_weekly_brief() -> Dict[str, Any]:
    brief = _load_brief_snapshot("brief_weekly")
    if not brief:
        brief = _fallback_brief("No weekly brief available yet.")
    return ok(brief)


brief_router = router
