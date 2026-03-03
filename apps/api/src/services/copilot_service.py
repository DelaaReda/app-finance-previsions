"""
Bridge: services.copilot_service -> domains/copilot/application/copilot_service
Fix 2026-03-03: permet a platform/main.py d'importer build_ask_payload.
"""
from __future__ import annotations
import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1]
for _p in [str(_src), str(_src / "domains")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from domains.copilot.application.copilot_service import (  # noqa: F401, E402
    build_ask_payload,
    build_history_payload,
    build_context_payload,
    build_report_payload,
)

__all__ = [
    "build_ask_payload",
    "build_history_payload",
    "build_context_payload",
    "build_report_payload",
]
