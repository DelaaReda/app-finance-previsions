"""
Backtests: compute only when forecasts exist; results persisted.
If no forecasts yet, keep previous snapshot (do not fake).
"""
from __future__ import annotations
from typing import Dict, Any, List
from backend.storage.base import save_json, load_json

def _compute_backtests(forecasts: List[dict]) -> Dict[str, Any]:
    # TODO: IMPLEMENT realistic backtest using existing forecasts history
    return {}

def run_backtests_job() -> Dict[str, Any]:
    prev = load_json("backtests.json")
    forecasts_snap = load_json("forecasts.json") or {}
    rows = (forecasts_snap.get("data") or {}).get("rows") or []
    data = _compute_backtests(rows) if rows else {}
    if data:
        save_json(data, "backtests.json", source="backtests_pipeline", status="OK")
        return data
    return (prev or {"data": {"results": []}, "status": "NO_SNAPSHOT"})["data"]
