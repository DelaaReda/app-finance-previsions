"""
Bridge: services.g4f_client -> domains/judge/application/g4f_client
Permet a research/llm_client.py d'importer call_llm sans connaitre la structure domains/.
Cree 2026-03-03 -- fix copilot LLM always-fallback.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ajouter domains/ au path si necessaire
_src = Path(__file__).resolve().parents[1]
_domains = _src / "domains"
for _p in (str(_src), str(_domains)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from domains.judge.application.g4f_client import (  # type: ignore
        call_llm,
        get_ranked_tested_models,
        resolve_llm_mode,
    )
    __all__ = ["call_llm", "get_ranked_tested_models", "resolve_llm_mode"]
except Exception as _e:
    import logging as _logging
    _logging.getLogger(__name__).warning("g4f_client bridge import failed: %s", _e)

    def call_llm(*args, **kwargs):  # type: ignore
        return {"ok": False, "error": f"g4f_client_bridge_failed: {_e}", "answer": ""}

    def get_ranked_tested_models(*args, **kwargs):  # type: ignore
        return []

    def resolve_llm_mode(*args, **kwargs):  # type: ignore
        return "auto"
