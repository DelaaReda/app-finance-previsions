# src/api/__init__.py
"""REST API package.

Keep imports lazy to avoid heavy side effects when only submodules are needed.
"""

from __future__ import annotations

from typing import Any


def create_app(*args: Any, **kwargs: Any):
    from .main import create_app as _create_app

    return _create_app(*args, **kwargs)


def run_server(*args: Any, **kwargs: Any):
    from .main import run_server as _run_server

    return _run_server(*args, **kwargs)


__all__ = ["create_app", "run_server"]
