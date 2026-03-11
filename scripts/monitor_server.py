#!/usr/bin/env python3
"""Compatibility wrapper for FC Monitor server.

Canonical implementation lives in: apps/monitor/server.py
"""
from __future__ import annotations

import fcntl
import importlib.util
import os
import runpy
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


_LOCK_FD: int | None = None


def _guard_vm_only() -> None:
    if sys.platform == "darwin" and os.environ.get("FC_ALLOW_LOCAL_MAC") != "1":
        expected = os.environ.get("FC_RUNTIME_WORKSPACE_ROOT", "/home/venom/analyse-financiere")
        raise SystemExit(
            "VM-only execution policy: monitor is disabled on macOS host. "
            f"Expected runtime workspace: {expected}. "
            "Set FC_ALLOW_LOCAL_MAC=1 only for exceptional debugging."
        )


def _has_monitor_deps() -> bool:
    return (
        importlib.util.find_spec("fastapi") is not None
        and importlib.util.find_spec("uvicorn") is not None
    )


def _maybe_reexec_with_monitor_venv() -> None:
    if _has_monitor_deps():
        return
    if os.environ.get("FC_MONITOR_REEXEC") == "1":
        raise ModuleNotFoundError(
            "fastapi/uvicorn introuvables. Installe-les dans apps/monitor/.venv "
            "ou dans l'interpreteur courant."
        )
    root = Path(__file__).resolve().parents[1]
    venv_python = root / "apps" / "monitor" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        raise ModuleNotFoundError(
            "fastapi/uvicorn manquants et apps/monitor/.venv absent. "
            "Cree le venv monitor puis relance."
        )
    env = dict(os.environ)
    env["FC_MONITOR_REEXEC"] = "1"
    os.execve(str(venv_python), [str(venv_python), str(Path(__file__).resolve())], env)


def _probe_monitor_up(url: str, timeout_s: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            return 200 <= int(getattr(resp, "status", 0)) < 300
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False


def _wait_until_up(url: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _probe_monitor_up(url):
            return True
        time.sleep(0.4)
    return False


def _monitor_status_url() -> str:
    url = os.environ.get("FC_MONITOR_LOCAL_URL", "").strip()
    if url:
        return url
    return os.environ.get("FC_MONITOR_STATUS_URL", "http://127.0.0.1:7779/api/monitor/access")


def _acquire_single_instance_lock(status_url: str) -> None:
    global _LOCK_FD
    lock_path = os.environ.get("FC_MONITOR_LOCK_FILE", "/tmp/fc-monitor-server.lock")
    lock_dir = os.path.dirname(lock_path)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _LOCK_FD = fd
        return
    except BlockingIOError:
        os.close(fd)
        if _wait_until_up(status_url, timeout_s=8.0):
            raise SystemExit(0)
        raise SystemExit(
            "Monitor lock busy and endpoint still unavailable after wait. "
            "Startup aborted to avoid duplicate bind."
        )


def main() -> None:
    _guard_vm_only()
    _maybe_reexec_with_monitor_venv()
    status_url = _monitor_status_url()
    if _probe_monitor_up(status_url, timeout_s=1.2):
        raise SystemExit(0)
    _acquire_single_instance_lock(status_url)
    target = Path(__file__).resolve().parents[1] / "apps" / "monitor" / "server.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
