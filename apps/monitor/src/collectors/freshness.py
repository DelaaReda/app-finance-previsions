from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable


def latest_mtime(paths: Iterable[Path]) -> float:
    latest = 0.0
    for p in paths:
        try:
            if p.exists():
                latest = max(latest, float(p.stat().st_mtime))
        except Exception:
            continue
    return latest


def detect_data_source(runtime_paths: Iterable[Path], kpi_path: Path) -> tuple[str, int]:
    runtime_ts = latest_mtime(runtime_paths)
    kpi_ts = latest_mtime([kpi_path]) if kpi_path.exists() else 0.0
    now = time.time()
    if runtime_ts > 0:
        return "runtime_snapshot", int(max(0, now - runtime_ts))
    if kpi_ts > 0:
        return "kpi_history", int(max(0, now - kpi_ts))
    return "unknown", -1
