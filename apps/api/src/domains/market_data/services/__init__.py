"""Compatibility package for market_data relative imports to services."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]  # apps/api/src
__path__ = [  # type: ignore[var-annotated]
    str(_ROOT / "domains" / "market_data" / "application"),
    str(_ROOT / "services"),
]
