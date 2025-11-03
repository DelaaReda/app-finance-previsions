"""
Weekly brief: heavy compute pre-generated weekly.
If compute fails, keep previous snapshot.
"""
from __future__ import annotations
from typing import Dict, Any
from backend.storage.base import save_json, load_json

def _compute_weekly_brief() -> Dict[str, Any]:
    # TODO: IMPLEMENT heavy aggregation (signals + macro + sectors + news highlights)
    return {}

def run_weekly_brief() -> Dict[str, Any]:
    prev = load_json("weekly_brief.json")
    data = _compute_weekly_brief()
    if data:
        save_json(data, "weekly_brief.json", source="weekly_pipeline", status="OK")
        return data
    return (prev or {"data": {"weekly": {}}, "status": "NO_SNAPSHOT"})["data"]
