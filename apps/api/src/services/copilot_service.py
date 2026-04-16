"""
Bridge: services.copilot_service -> domains/copilot/application/copilot_service
Fix 2026-04-16: expose the canonical domain module itself so monkeypatches and
shared start-route helpers stay in sync across legacy import paths.
"""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

_src = Path(__file__).resolve().parents[1]
for _p in [str(_src), str(_src / "domains")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_domain_module = import_module("domains.copilot.application.copilot_service")
globals().update(_domain_module.__dict__)
sys.modules[__name__] = _domain_module
