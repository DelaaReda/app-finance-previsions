from __future__ import annotations

import os
import subprocess
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


def safe_tail(path: Path, lines: int, timeout_ms: int = 1200) -> list[str]:
    n = max(1, int(lines))
    timeout_s = max(0.1, float(timeout_ms) / 1000.0)
    if not path.exists():
        return []
    try:
        proc = subprocess.run(
            ["tail", "-n", str(n), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout_s,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.splitlines()
    except Exception:
        pass
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
    except Exception:
        return []


def detect_runtime_host_kind(root: Path) -> dict[str, str]:
    """
    Best-effort host context for monitor diagnostics.
    Never raises and never blocks API responses.
    """
    fallback = {
        "runtime_host_kind": "unknown",
        "runtime_is_vm": "0",
        "source": "fallback",
    }
    script = root / "scripts" / "runtime_host_check.sh"
    if not script.exists():
        return fallback
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=1.2,
            check=False,
        )
    except Exception:
        return fallback
    if proc.returncode != 0:
        return fallback
    out: dict[str, str] = {}
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return {
        "runtime_host_kind": out.get("runtime_host_kind", "unknown"),
        "runtime_is_vm": out.get("runtime_is_vm", "0"),
        "source": "runtime_host_check.sh",
    }
