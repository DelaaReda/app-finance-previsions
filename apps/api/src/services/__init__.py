"""Compatibility package that exposes reusable services under a flat import path."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]  # apps/api/src
_PKG_ROOT = Path(__file__).resolve().parent  # apps/api/src/services

__path__ = [  # type: ignore[var-annotated]
    str(_PKG_ROOT),
    str(_ROOT / "domains" / "forecasts" / "application"),
    str(_ROOT / "domains" / "market_data" / "application"),
    str(_ROOT / "domains" / "copilot" / "application"),
    str(_ROOT / "domains" / "judge" / "application"),
    str(_ROOT / "platform" / "legacy" / "services"),
    str(_ROOT / "platform" / "legacy" / "services" / "legacy"),
    str(_ROOT / "platform" / "legacy" / "data"),  # optional legacy fallback for datasets
]
