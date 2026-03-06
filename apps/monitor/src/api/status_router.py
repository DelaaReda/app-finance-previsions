from __future__ import annotations

from fastapi import APIRouter
from typing import Callable, Dict, Any


def create_status_router(get_status: Callable[[], Dict[str, Any]]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/status")
    def api_status():
        return get_status()

    return router
