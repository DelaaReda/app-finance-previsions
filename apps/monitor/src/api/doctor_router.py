from __future__ import annotations

from fastapi import APIRouter
from typing import Callable, Dict, Any


def create_doctor_router(get_snapshot: Callable[[bool], Dict[str, Any]]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/doctor")
    def api_doctor(refresh: int = 0):
        return get_snapshot(bool(int(refresh)))

    @router.get("/api/doctor/latest")
    def api_doctor_latest():
        return get_snapshot(False)

    return router
