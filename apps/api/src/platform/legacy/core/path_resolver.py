"""Canonical runtime path resolver for Finance Copilot legacy modules.

This module intentionally resolves storage/log paths to:
  - apps/api/runtime/data
  - apps/api/runtime/logs

It avoids legacy `platform/legacy/data` roots that can diverge from runtime.
"""
from pathlib import Path


def _resolve_api_root() -> Path:
    # apps/api/src/platform/legacy/core/path_resolver.py -> parents[4] = apps/api
    api_root = Path(__file__).resolve().parents[4]
    runtime_dir = api_root / "runtime"
    if runtime_dir.exists():
        return api_root
    # Defensive fallback for atypical execution contexts.
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "runtime").exists() and (candidate / "src").exists():
            return candidate
    return api_root


_API_ROOT = _resolve_api_root()
_BACKEND_ROOT = _API_ROOT  # legacy compatibility name
DATA_DIR = _API_ROOT / "runtime" / "data"
LOGS_DIR = _API_ROOT / "runtime" / "logs"

DATA_DIR.mkdir(exist_ok=True, parents=True)
LOGS_DIR.mkdir(exist_ok=True, parents=True)


def get_data_path(filename: str) -> Path:
    """Get the absolute path to a data file under runtime/data."""
    name = str(filename or "").strip()
    if not name:
        name = "default.json"
    if not name.lower().endswith(".json"):
        name = f"{name}.json"
    return DATA_DIR / name


def get_backend_root() -> Path:
    """Return the resolved API root (legacy-compatible function name)."""
    return _BACKEND_ROOT


def get_data_directory() -> Path:
    """Return the canonical runtime data directory."""
    return DATA_DIR


def ensure_directories() -> None:
    """Ensure required runtime directories exist."""
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    LOGS_DIR.mkdir(exist_ok=True, parents=True)


BACKEND_ROOT = _BACKEND_ROOT
STORAGE_PATH = DATA_DIR


if __name__ == "__main__":
    print(f"API root: {_API_ROOT}")
    print(f"Data dir: {DATA_DIR}")
    print(f"Logs dir: {LOGS_DIR}")
    print(f"Sample path (forecasts.json): {get_data_path('forecasts')}")
