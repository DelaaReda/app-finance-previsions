"""Compatibility shim for relative imports from `platform.main`."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # apps/api/src
_SERVICES_ROOT = _ROOT / "services"
_MARKET_DATA = _ROOT / "domains" / "market_data" / "application"
_FORECASTS = _ROOT / "domains" / "forecasts" / "application"
_COPILOT = _ROOT / "domains" / "copilot" / "application"
_JUDGE = _ROOT / "domains" / "judge" / "application"

__path__ = [  # type: ignore[var-annotated]
    str(_SERVICES_ROOT),
    str(_MARKET_DATA),
    str(_FORECASTS),
    str(_COPILOT),
    str(_JUDGE),
]
