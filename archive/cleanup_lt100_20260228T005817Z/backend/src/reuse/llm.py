"""LLM reuse facade.

Canonical entrypoints for LLM usage in backend modules.
"""

from __future__ import annotations

from typing import Any, Optional


def call_llm(
    prompt: str,
    *,
    mode: Optional[str] = None,
    category_preference: Optional[str] = None,
    timeout: Optional[int] = None,
    max_attempts: Optional[int] = None,
) -> dict:
    from services.g4f_client import call_llm as _call_llm

    return _call_llm(
        prompt,
        mode=mode,
        category_preference=category_preference,
        timeout=timeout,
        max_attempts=max_attempts,
    )


def resolve_llm_mode(mode: Optional[str] = None) -> str:
    from services.g4f_client import resolve_llm_mode as _resolve_llm_mode

    return _resolve_llm_mode(mode=mode)


def get_ranked_tested_models(
    mode: Optional[str] = None,
    category_preference: Optional[str] = None,
) -> list[dict]:
    from services.g4f_client import get_ranked_tested_models as _get_ranked_tested_models

    return _get_ranked_tested_models(
        mode=mode,
        category_preference=category_preference,
    )


def get_economic_analyst_class() -> type:
    from analytics.econ_llm_agent import EconomicAnalyst

    return EconomicAnalyst


def get_economic_input_class() -> type:
    from analytics.econ_llm_agent import EconomicInput

    return EconomicInput


def create_economic_analyst(*args: Any, **kwargs: Any) -> Any:
    cls = get_economic_analyst_class()
    return cls(*args, **kwargs)
