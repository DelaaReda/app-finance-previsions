"""
Bridge: platform/legacy/services/g4f_client -> src/services/g4f_client -> domains/judge/application/g4f_client
Creé 2026-03-03 — fix call_llm=None dans research/llm_client.py (path legacy en premier).
"""
from __future__ import annotations
import sys
from pathlib import Path

# src/ root — contient domains/ et services/
_src = Path(__file__).resolve().parents[3]  # platform/legacy/services/ -> platform/legacy -> platform -> src
for _candidate in (
    str(_src),
    str(_src / "domains"),
    str(_src / "services"),
):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

try:
    from domains.judge.application.g4f_client import (  # type: ignore
        call_llm,
        get_ranked_tested_models,
        resolve_llm_mode,
    )
    __all__ = ["call_llm", "get_ranked_tested_models", "resolve_llm_mode"]
except Exception as _e:
    import logging as _log
    _log.getLogger(__name__).warning("g4f_client legacy-bridge failed: %s", _e)

    def call_llm(*a, **kw):  # type: ignore
        return {"ok": False, "error": f"bridge_failed:{_e}", "answer": ""}

    def get_ranked_tested_models(*a, **kw):  # type: ignore
        return []

    def resolve_llm_mode(*a, **kw):  # type: ignore
        return "auto"
