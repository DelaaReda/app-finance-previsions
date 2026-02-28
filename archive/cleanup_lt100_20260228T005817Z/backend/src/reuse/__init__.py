"""Stable reuse facades for backend modules.

Goal: reduce cognitive load for agents by exposing canonical import points.
"""

from .llm import (
    call_llm,
    get_ranked_tested_models,
    resolve_llm_mode,
    get_economic_analyst_class,
    get_economic_input_class,
)
from .forecasting import (
    build_fundamental_view,
    build_technical_view,
    build_macro_view,
    build_sentiment_view,
    run_fusion,
    build_market_snapshot,
)
from .judge import (
    build_judge_verdict,
    load_judge_profile,
    score_judge_news,
    stable_cache_key,
    compute_singleflight,
)
from .data import (
    run_quality_audit,
    run_quality_gate,
    check_timeseries,
    load_snapshot,
    resolve_snapshot_payload,
    get_close_series,
)

__all__ = [
    "call_llm",
    "get_ranked_tested_models",
    "resolve_llm_mode",
    "get_economic_analyst_class",
    "get_economic_input_class",
    "build_fundamental_view",
    "build_technical_view",
    "build_macro_view",
    "build_sentiment_view",
    "run_fusion",
    "build_market_snapshot",
    "build_judge_verdict",
    "load_judge_profile",
    "score_judge_news",
    "stable_cache_key",
    "compute_singleflight",
    "run_quality_audit",
    "run_quality_gate",
    "check_timeseries",
    "load_snapshot",
    "resolve_snapshot_payload",
    "get_close_series",
]
