"""No-op scheduler shim for compatibility imports."""

from __future__ import annotations

from typing import Any


def start_scheduler(*_: Any, **__: Any) -> None:
    """Compatibility no-op; scheduler orchestration is optional in this structure."""


def stop_scheduler(*_: Any, **__: Any) -> None:
    """Compatibility no-op."""

