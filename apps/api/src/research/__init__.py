"""Research namespace compatibility bridge.

Expose both:
- current package modules (research/llm_client.py, research/rag_store.py, ...)
- legacy research modules (platform/legacy/research/*.py)
"""

from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_LEGACY_RESEARCH = _ROOT / "platform" / "legacy" / "research"

__path__ = [  # type: ignore[var-annotated]
    str(_HERE),
    str(_LEGACY_RESEARCH),
]
