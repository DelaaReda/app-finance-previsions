"""
Compat package bridge for service modules.

We have legacy services/ (this folder) and the newer src/services/.
To avoid import errors when calling `from services.judge_pipeline import ...`
we extend __path__ to include the src/services directory, then import the
new implementation from there.
"""
from pathlib import Path
import sys
import warnings

# Extend package search path to include src/services
_pkg_dir = Path(__file__).resolve().parent
_src_services = _pkg_dir.parent / "src" / "services"
if _src_services.exists():
    if str(_src_services) not in __path__:  # type: ignore[name-defined]
        __path__.append(str(_src_services))  # type: ignore[name-defined]
    # Ensure backend/src is on sys.path for downstream imports
    src_root = _pkg_dir.parent / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

# Expose judge_pipeline helpers (from src/services)
try:
    from . import judge_pipeline  # noqa: F401
except Exception as e:  # pragma: no cover - import guard
    warnings.warn(f"services.judge_pipeline unavailable: {e}")
