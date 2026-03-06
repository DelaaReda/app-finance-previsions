from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter


def build_monitor_router(
    status_handler: Callable[[], dict[str, Any]],
    runtime_diagnostics_handler: Callable[[], dict[str, Any]],
    doctor_handler: Callable[[int], dict[str, Any]],
    doctor_latest_handler: Callable[[], dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/status")
    def status_endpoint() -> dict[str, Any]:
        return status_handler()

    @router.get("/api/runtime-diagnostics")
    def runtime_diagnostics_endpoint() -> dict[str, Any]:
        return runtime_diagnostics_handler()

    @router.get("/api/doctor")
    def doctor_endpoint(refresh: int = 0) -> dict[str, Any]:
        return doctor_handler(refresh)

    @router.get("/api/doctor/latest")
    def doctor_latest_endpoint() -> dict[str, Any]:
        return doctor_latest_handler()

    return router
