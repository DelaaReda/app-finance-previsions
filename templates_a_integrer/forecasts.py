from __future__ import annotations
from fastapi import APIRouter
from backend.services.compute_runner import get_forecasts_data

router = APIRouter()

@router.get("/forecasts")
def forecasts():
    """
    Serve latest snapshot immediately. The compute job runs on schedule.
    Response structure always non-empty with metadata in wrapper.
    """
    return get_forecasts_data()
