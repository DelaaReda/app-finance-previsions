"""Project namespace package for backend platform internals.

This package intentionally proxies known names from stdlib ``platform`` to avoid
import shadowing regressions in third-party code such as ``importlib`` and
``pydantic`` helpers while still exposing local modules like ``platform.main``.
"""

from __future__ import annotations

import sys
from importlib import util
from pathlib import Path


_STD_NAME = "stdlib_platform"


def _load_stdlib_platform() -> None:
    stdlib_candidate = Path("/usr/lib/python3.12/platform.py")
    if not stdlib_candidate.exists():
        for path in sys.path:
            if not path:
                continue
            candidate = Path(path) / "platform.py"
            if candidate.exists():
                stdlib_candidate = candidate
                break
        else:
            return

    spec = util.spec_from_file_location(_STD_NAME, str(stdlib_candidate))
    if spec is None or spec.loader is None:
        return
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    globals().update(
        {
            key: value
            for key, value in module.__dict__.items()
            if key.isidentifier() and not key.startswith("_")
        }
    )


_load_stdlib_platform()

