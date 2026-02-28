"""Judge template reuse facade.

Provides stable access to canonical judge helpers and builders.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional, Tuple
import asyncio


def build_judge_verdict(row: Dict[str, Any], profile: Optional[str] = None) -> Any:
    from services.judge_builder import build_judge_verdict as _build_judge_verdict

    return _build_judge_verdict(row=row, profile=profile)


def load_judge_profile(name: str) -> Any:
    from services.judge_pipeline import load_profile as _load_profile

    return _load_profile(name)


def score_judge_news(news_list: list[dict], cap: int = 5) -> list[dict]:
    from services.judge_pipeline import score_news as _score_news

    return _score_news(news_list, cap=cap)


def stable_cache_key(namespace: str, payload: Dict[str, Any]) -> str:
    from api.templates.judge_like_endpoint import stable_cache_key as _stable_cache_key

    return _stable_cache_key(namespace=namespace, payload=payload)


async def compute_singleflight(
    inflight: Dict[str, asyncio.Task],
    inflight_lock: asyncio.Lock,
    key: str,
    compute_fn: Callable[[], Awaitable[Dict[str, Any]]],
) -> Tuple[Dict[str, Any], bool]:
    from api.templates.judge_like_endpoint import compute_singleflight as _compute_singleflight

    return await _compute_singleflight(
        inflight=inflight,
        inflight_lock=inflight_lock,
        key=key,
        compute_fn=compute_fn,
    )
