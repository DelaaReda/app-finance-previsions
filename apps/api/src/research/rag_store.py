"""Bridge: research.rag_store -> platform/legacy/research/rag_store"""
from __future__ import annotations
import sys
from pathlib import Path

_legacy = Path(__file__).resolve().parents[1] / "platform" / "legacy"
if str(_legacy) not in sys.path:
    sys.path.insert(0, str(_legacy))

from platform.legacy.research.rag_store import RAGStore  # noqa: F401, E402

__all__ = ["RAGStore"]
