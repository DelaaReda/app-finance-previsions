from fastapi import APIRouter
from core.response import ok
from services.forecast_service import get_all_forecasts
from services.cache_layer import load_or_compute

router = APIRouter()

@router.get("/forecasts")
def forecasts():
    snap = get_all_forecasts(lambda key,fn,source=None: load_or_compute(key,fn,source))
    payload = snap["payload"]
    payload["freshness"] = snap["last_update"]
    payload["source"] = snap["source"]
    return ok(payload)