"""Compatibility namespace for route imports.\n\nTests and some modules still import routes from ``api.routes`` while the\ncanonical route modules now live in domain packages.\n\nThe package exposes domain route directories as namespace search paths to keep\nimports stable:\n- ``api.routes.forecasts`` -> ``domains/forecasts/api/forecasts.py``\n- ``api.routes.dashboard`` -> ``domains/market_data/api/dashboard.py``\n- etc.\n"""

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
