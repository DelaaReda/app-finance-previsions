"""Compatibility shim for legacy `api.templates.judge_like_endpoint` imports."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_TARGET = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "platform"
    / "legacy"
    / "api"
    / "templates"
    / "judge_like_endpoint.py"
)
_SPEC = spec_from_file_location("legacy_judge_like_endpoint", _TARGET)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load judge_like_endpoint shim from {_TARGET}")

_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)  # type: ignore[union-attr]
globals().update(_MODULE.__dict__)
__all__ = [name for name in _MODULE.__dict__ if not name.startswith("_")]
