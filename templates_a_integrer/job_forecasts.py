"""
Forecasts job: compute real forecasts and persist snapshot (no mock).
If upstream signals unavailable, keep previous snapshot; do NOT write fake rows.
"""
from __future__ import annotations
from typing import Dict, Any, List
from backend.storage.base import save_json, load_json

def _compute_forecasts() -> List[Dict[str, Any]]:
    # TODO: IMPLEMENT real pipeline:
    # 1) load prices + macro + news features
    # 2) run ML model
    # 3) optional LLM ranking/validation
    # 4) return list of rows
    return []  # returning empty here does not write fake data

def run_forecast_job() -> Dict[str, Any]:
    prev = load_json("forecasts.json")
    rows = _compute_forecasts()
    if rows:
        save_json({"rows": rows}, "forecasts.json", source="forecasts_pipeline", status="OK")
        return {"rows": rows}
    # If nothing computed, keep previous snapshot untouched
    return (prev or {"data": {"rows": []}, "status": "NO_SNAPSHOT"})["data"]
