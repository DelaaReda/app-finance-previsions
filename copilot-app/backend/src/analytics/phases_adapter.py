"""
Lightweight adapter to build phase blocks (fundamental, technical, macro, sentiment, fusion)
from already-computed features, macro snapshot, and news list.

This avoids re-running heavy phase1–5 pipelines while still giving the LLM a
structured, multi-branch context.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _clamp01(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    try:
        return max(0.0, min(1.0, float(x)))
    except Exception:
        return None


def _score_from_pe(pe: Optional[float]) -> Optional[float]:
    if pe is None:
        return None
    try:
        pe = float(pe)
        if pe <= 12:
            return 0.8
        if pe <= 18:
            return 0.65
        if pe <= 25:
            return 0.5
        if pe <= 35:
            return 0.35
        return 0.2
    except Exception:
        return None


def _score_from_growth(growth: Optional[float]) -> Optional[float]:
    if growth is None:
        return None
    try:
        g = float(growth)
        if g >= 0.2:
            return 0.8
        if g >= 0.1:
            return 0.65
        if g >= 0.0:
            return 0.5
        if g >= -0.05:
            return 0.35
        return 0.2
    except Exception:
        return None


def _mean(vals: List[Optional[float]]) -> Optional[float]:
    clean = [float(v) for v in vals if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _sentiment_score(news: List[Dict[str, Any]]) -> Optional[float]:
    if not news:
        return None
    scores = []
    for n in news:
        s = n.get("sentiment_score") or n.get("sent") or n.get("sentiment")
        try:
            if s is not None:
                scores.append(float(s))
        except Exception:
            continue
    if not scores:
        return None
    return sum(scores) / len(scores)


def build_phase_blocks(
    ticker: str,
    features: Dict[str, Any],
    macro_ctx: Dict[str, Any],
    news: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return structured phase summaries and scores."""
    fund = features.get("fundamentals") or {}
    tech = features.get("tech") or {}

    # Fundamental score
    pe_score = _score_from_pe(fund.get("pe"))
    growth_score = _score_from_growth(fund.get("revenueGrowth") or fund.get("rev_growth"))
    margin = fund.get("profitMargins")
    margin_score = None
    try:
        if margin is not None:
            m = float(margin)
            if m >= 0.2:
                margin_score = 0.8
            elif m >= 0.1:
                margin_score = 0.65
            elif m >= 0.0:
                margin_score = 0.5
            elif m >= -0.05:
                margin_score = 0.35
            else:
                margin_score = 0.2
    except Exception:
        margin_score = None
    fundamental_score = _mean([pe_score, growth_score, margin_score])
    fundamental_summary = []
    if fund.get("pe") is not None:
        fundamental_summary.append(f"PE={fund.get('pe')}")
    if fund.get("revenueGrowth") is not None:
        fundamental_summary.append(f"rev_growth={fund.get('revenueGrowth')}")
    if fund.get("profitMargins") is not None:
        fundamental_summary.append(f"margin={fund.get('profitMargins')}")
    if fund.get("beta") is not None:
        fundamental_summary.append(f"beta={fund.get('beta')}")

    # Technical score
    rsi = tech.get("rsi") or features.get("rsi")
    mom1 = features.get("momentum_1m")
    mom3 = features.get("momentum_3m")
    dd3m = features.get("drawdown_3m")
    tech_score = _mean(
        [
            _clamp01((float(rsi) - 30) / 40) if rsi is not None else None,
            _clamp01(mom1),
            _clamp01(mom3),
            _clamp01(1 - abs(dd3m) if dd3m is not None else None),
        ]
    )
    tech_summary = []
    if rsi is not None:
        tech_summary.append(f"rsi={rsi}")
    if mom1 is not None:
        tech_summary.append(f"mom1m={mom1}")
    if mom3 is not None:
        tech_summary.append(f"mom3m={mom3}")
    if dd3m is not None:
        tech_summary.append(f"dd3m={dd3m}")

    # Macro score (simple, from VIX and DXY if present)
    vix = macro_ctx.get("vix")
    dxy = macro_ctx.get("dxy")
    macro_score = None
    try:
        vix_score = None
        if vix is not None:
            v = float(vix)
            if v <= 14:
                vix_score = 0.8
            elif v <= 20:
                vix_score = 0.6
            elif v <= 28:
                vix_score = 0.45
            else:
                vix_score = 0.25
        dxy_score = None
        if dxy is not None:
            d = float(dxy)
            # Rough z-scale; if >110 consider strong dollar -> slightly negative for risk
            if d <= 102:
                dxy_score = 0.65
            elif d <= 108:
                dxy_score = 0.5
            else:
                dxy_score = 0.35
        macro_score = _mean([vix_score, dxy_score])
    except Exception:
        macro_score = None
    macro_summary = []
    if vix is not None:
        macro_summary.append(f"vix={vix}")
    if macro_ctx.get("us10y") is not None:
        macro_summary.append(f"us10y={macro_ctx.get('us10y')}")
    if dxy is not None:
        macro_summary.append(f"dxy={dxy}")

    # Sentiment score
    sent_score = _sentiment_score(news)
    sent_summary = [f"mean_sent={round(sent_score,4)}"] if sent_score is not None else []

    fusion_score = _mean([fundamental_score, tech_score, macro_score, sent_score])

    return {
        "fundamental": {
            "score": fundamental_score,
            "summary": fundamental_summary,
            "details": {
                "pe": fund.get("pe"),
                "revenueGrowth": fund.get("revenueGrowth"),
                "profitMargins": fund.get("profitMargins"),
                "beta": fund.get("beta"),
            },
        },
        "technical": {
            "score": tech_score,
            "summary": tech_summary,
            "details": {
                "rsi": rsi,
                "momentum_1m": mom1,
                "momentum_3m": mom3,
                "drawdown_3m": dd3m,
            },
        },
        "macro": {
            "score": macro_score,
            "summary": macro_summary,
            "details": {
                "vix": macro_ctx.get("vix"),
                "us10y": macro_ctx.get("us10y"),
                "dxy": dxy,
            },
        },
        "sentiment": {
            "score": sent_score,
            "summary": sent_summary,
            "details": {"news_count": len(news)},
        },
        "fusion": {
            "score": fusion_score,
            "summary": [
                f"fusion_score={fusion_score}" if fusion_score is not None else "fusion_score=NA"
            ],
        },
    }
