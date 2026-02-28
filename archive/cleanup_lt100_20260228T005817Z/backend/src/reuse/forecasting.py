"""Forecasting reuse facade.

Stable wrappers around the canonical phase modules and market intel builder.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_fundamental_view(*args: Any, **kwargs: Any) -> Any:
    from analytics.phase1_fundamental import build_fundamental_view as _build_fundamental_view

    return _build_fundamental_view(*args, **kwargs)


def build_technical_view(*args: Any, **kwargs: Any) -> Any:
    from analytics.phase2_technical import build_technical_view as _build_technical_view

    return _build_technical_view(*args, **kwargs)


def build_macro_view(*args: Any, **kwargs: Any) -> Any:
    from analytics.phase3_macro import build_macro_view as _build_macro_view

    return _build_macro_view(*args, **kwargs)


def build_sentiment_view(*args: Any, **kwargs: Any) -> Any:
    from analytics.phase4_sentiment import build_sentiment_view as _build_sentiment_view

    return _build_sentiment_view(*args, **kwargs)


def run_fusion(*args: Any, **kwargs: Any) -> Any:
    from analytics.phase5_fusion import run_fusion as _run_fusion

    return _run_fusion(*args, **kwargs)


def build_market_snapshot(
    *,
    regions: List[str],
    window: str,
    query: str = "",
    company: Optional[str] = None,
    ticker: Optional[str] = None,
    want_futures: bool = False,
) -> Dict[str, Any]:
    from analytics.market_intel import build_snapshot as _build_snapshot

    return _build_snapshot(
        regions=regions,
        window=window,
        query=query,
        company=company,
        ticker=ticker,
        want_futures=want_futures,
    )
