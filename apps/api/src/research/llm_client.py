"""Bridge: research.llm_client -> platform/legacy/research/llm_client"""
from __future__ import annotations
import sys
from pathlib import Path

_legacy = Path(__file__).resolve().parents[1] / "platform" / "legacy"
if str(_legacy) not in sys.path:
    sys.path.insert(0, str(_legacy))
if str(_legacy / "research") not in sys.path:
    sys.path.insert(0, str(_legacy / "research"))

# Also ensure services/ bridge is accessible
_src = Path(__file__).resolve().parents[1]
for _p in [str(_src), str(_src / "domains")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from platform.legacy.research.llm_client import ask_llm, get_llm_client  # noqa: F401, E402

__all__ = ["ask_llm", "get_llm_client"]
