from __future__ import annotations

import re
from typing import Any, Callable, Dict

from fastapi import APIRouter


def _parse_window_hours(raw: str | int | None, default: int = 6) -> int:
    if raw is None:
        return default
    if isinstance(raw, int):
        return max(1, min(raw, 72))
    token = str(raw).strip().lower()
    if not token:
        return default
    if token.isdigit():
        return max(1, min(int(token), 72))
    match = re.match(r"^(\d+)\s*h$", token)
    if match:
        return max(1, min(int(match.group(1)), 72))
    return default


def create_activity_router(
    get_activity: Callable[[int, int], Dict[str, Any]],
    get_tasks_active: Callable[[int, int], Dict[str, Any]],
    get_dependencies: Callable[[int], Dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/agent-activity")
    def api_agent_activity(window: str = "6h", limit: int = 300):
        return get_activity(_parse_window_hours(window, default=6), limit)

    @router.get("/api/tasks/active")
    def api_tasks_active(window: str = "6h", limit: int = 80):
        return get_tasks_active(_parse_window_hours(window, default=6), limit)

    @router.get("/api/dependencies/map")
    def api_dependencies_map(limit: int = 300):
        return get_dependencies(limit)

    return router
