from fastapi import APIRouter
from core.response import ok
from jobs.backtests import ensure_backtests_up_to_date

router = APIRouter()

@router.get("/backtests")
def backtests():
    """Get backtests results with cache-first and invalidation logic."""
    snap = ensure_backtests_up_to_date()
    payload = snap["payload"] if "payload" in snap else snap
    payload["freshness"] = snap.get("last_update")
    payload["source"] = snap.get("source", [])
    return ok(payload)