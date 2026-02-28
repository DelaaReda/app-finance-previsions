"""Compatibility namespace for ``platform.main`` route imports.

Legacy ``platform.main`` includes modules from ``platform.routes.*``.
Canonical route implementations now live under ``domains/*/api``.
This module exposes those domain API folders as namespace search paths so legacy
imports keep working without duplicating wrappers.
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]  # apps/api/src
_FORECASTS_API = _ROOT / "domains" / "forecasts" / "api"
_MARKET_DATA_API = _ROOT / "domains" / "market_data" / "api"
_COPILOT_API = _ROOT / "domains" / "copilot" / "api"
_JUDGE_API = _ROOT / "domains" / "judge" / "api"

__path__ = [  # type: ignore[var-annotated]
    str(_FORECASTS_API),
    str(_MARKET_DATA_API),
    str(_COPILOT_API),
    str(_JUDGE_API),
]
