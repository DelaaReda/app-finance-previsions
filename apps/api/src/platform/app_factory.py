from __future__ import annotations

from fastapi import FastAPI

from .bootstrap.runtime import bootstrap_runtime


def create_app() -> FastAPI:
    """Canonical app factory entrypoint.

    This is intentionally thin during the progressive strangler migration:
    bootstrap hooks live under ``platform.bootstrap.*`` while the current
    route surface remains in ``platform.main``.
    """
    bootstrap_runtime()
    from .main import create_app as legacy_create_app

    return legacy_create_app()
