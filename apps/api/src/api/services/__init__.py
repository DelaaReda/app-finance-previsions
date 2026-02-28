"""Compatibility package for legacy `api.services` imports."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # apps/api/src
__path__ = [  # type: ignore[var-annotated]
    str(_ROOT / "domains" / "forecasts" / "application"),
    str(_ROOT / "domains" / "market_data" / "application"),
    str(_ROOT / "domains" / "copilot" / "application"),
    str(_ROOT / "domains" / "judge" / "application"),
    str(_ROOT / "platform" / "legacy" / "services"),
    str(_ROOT / "platform" / "legacy" / "services" / "legacy"),
    str(_ROOT / "platform" / "legacy" / "data"),
]
