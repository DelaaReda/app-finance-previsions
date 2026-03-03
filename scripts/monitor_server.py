#!/usr/bin/env python3
"""Compatibility wrapper for FC Monitor server.

Canonical implementation lives in: apps/monitor/server.py
"""
from __future__ import annotations

import importlib.util
import os
import runpy
import sys
from pathlib import Path


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
            "ou dans l'interpréteur courant."
        )
    root = Path(__file__).resolve().parents[1]
    venv_python = root / "apps" / "monitor" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        raise ModuleNotFoundError(
            "fastapi/uvicorn manquants et apps/monitor/.venv absent. "
            "Crée le venv monitor puis relance."
        )
    env = dict(os.environ)
    env["FC_MONITOR_REEXEC"] = "1"
    os.execve(str(venv_python), [str(venv_python), str(Path(__file__).resolve())], env)


def main() -> None:
    _maybe_reexec_with_monitor_venv()
    target = Path(__file__).resolve().parents[1] / "apps" / "monitor" / "server.py"
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
