"""Backward-compatible backend entrypoint."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "platform" / "run_api.py"


def _load_run_api_module():
    spec = spec_from_file_location("legacy_platform_run_api", _TARGET)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load platform.run_api from {_TARGET}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    globals().update(module.__dict__)
    globals()["__all__"] = [name for name in module.__dict__ if not name.startswith("_")]


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(_TARGET), run_name="__main__")
else:
    _load_run_api_module()
