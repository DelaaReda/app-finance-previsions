"""Legacy taxonomy namespace compatibility."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
__path__ = [str(_ROOT / "platform" / "legacy" / "taxonomy")]  # type: ignore[var-annotated]

