"""Compatibility module for legacy imports."""

from __future__ import annotations

import sys
import types

from domains.judge.api import judge as _judge_module

# Keep a shared module state so tests that monkeypatch `judge` attributes (legacy
# path) affect the actual route module (`domains.judge.api.judge`) too.
class _JudgeCompatibilityModule(types.ModuleType):
    def __getattr__(self, name: str):
        return getattr(_judge_module, name)

    def __setattr__(self, name: str, value):
        setattr(_judge_module, name, value)
        return super().__setattr__(name, value)


compat_module = sys.modules[__name__]
compat_module.__class__ = _JudgeCompatibilityModule

# Re-export every non-dunder symbol from the canonical module.
globals().update(
    {
        name: value
        for name, value in _judge_module.__dict__.items()
        if not name.startswith("__")
    }
)

# Keep these in sync when callers introspect attribute lookup directly.
for _name in [
    "_judge_module",
    "compat_module",
    "_JudgeCompatibilityModule",
]:
    globals()[_name] = globals().get(_name)

__all__ = [name for name in globals() if not name.startswith("__")]
