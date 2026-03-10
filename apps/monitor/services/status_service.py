from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from apps.monitor.collectors.runtime_collectors import collect_queue_workboard


def build_status_snapshot(
    root: Path,
    status_builder: Callable[[], dict[str, Any]],
    *,
    include_layers: bool = True,
) -> dict[str, Any]:
    payload = status_builder()
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("layers", {})
    payload["layers"]["service"] = "status_service.v1"
    if include_layers:
        payload["layers"]["collectors"] = collect_queue_workboard(root)
    else:
        payload["layers"]["collectors_omitted"] = True
        payload["layers"]["mode"] = "lite"
    return payload
