"""
Compatibility shim for legacy imports written as `src.*`.

After flattening backend/src -> backend/, we keep import compatibility by
registering an in-memory package alias named `src` that points to backend/.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
import os


def _register_src_alias() -> None:
    backend_root = Path(__file__).resolve().parent
    backend_root_str = str(backend_root)
    module = sys.modules.get("src")
    if module is None:
        module = types.ModuleType("src")
        module.__file__ = __file__
        module.__path__ = [backend_root_str]
        module.__package__ = "src"
        sys.modules["src"] = module
        return

    paths = list(getattr(module, "__path__", []))
    if backend_root_str not in paths:
        paths.insert(0, backend_root_str)
        module.__path__ = paths


def _ensure_workspace_root_on_sys_path() -> None:
    # Default OFF to avoid non-deterministic path side effects.
    # Enable explicitly only when needed for local troubleshooting.
    if os.environ.get("FC_ENABLE_WORKSPACE_ROOT_SYSPATH", "0").strip() not in {"1", "true", "yes"}:
        return
    backend_root = Path(__file__).resolve().parent
    for candidate in backend_root.parents:
        if (candidate / "AGENTS.md").exists() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
            break


_register_src_alias()
_ensure_workspace_root_on_sys_path()
