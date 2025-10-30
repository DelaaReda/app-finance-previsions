# src/api/services/scoring_service.py
"""
Composite scoring service: 40% Macro + 40% Technical + 20% News
This is the CORE value proposition of the Finance Copilot.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

from api.schemas import (
    CompositeScore, TraceMetadata,
    TopSignal, SignalsData, BriefData, BriefSection
)

# Import existing modules
from core.market_data import get_fred_series, get_price_history

try:
    from analytics.phase2_technical import (
        load_prices, compute_indicators, technical_signals
    )
    HAS_PHASE2 = True
except ImportError:
    HAS_PHASE2 = False

try:
    from analytics.phase3_macro import (
        get_us_macro_bundle, macro_regime
    )
    HAS_PHASE3 = True
except ImportError:
    HAS_PHASE3 = False

try:
    from ingestion.finnews import run_pipeline, build_news_features
    HAS_FINNEWS = True
except ImportError:
    HAS_FINNEWS = False


def _hash_data(data: Any) -> str:
    """Generate SHA256 hash."""
    content = str(data).encode('utf-8')
    return hashlib.sha256(content).hexdigest()[:32]


def _create_trace(source: str, asof: date, data: Any) -> TraceMetadata:
    """Create trace metadata."""
    return TraceMetadata(
        created_at=datetime.utcnow(),
        source=source,
        asof_date=asof,
        hash=_hash_data(data)
    )


# ========================= MACRO SCORING (40%) =========================

def get_macro_contribution(ticker: Optional[str] = None) -> float:
    """
    Calculate macro environment score (0-1).
    
    Factors:
    - VIX level (low = bullish)
    - Yield curve (inverted = risk)
    - Inflation trend (falling = bullish)
    - Fed policy (accommodative = bullish)
    
    Args:
        ticker: Optional ticker (for sector-specific adjustments)
    
    Returns:
        Score 0-1 (0=bearish macro, 1=bullish macro)
    """
    if not HAS_PHASE3:
        # Fallback: basic FRED series
        return _macro_contribution_basic()
    
    try:
        # Use phase3 bundle if available
        bundle = get_us_macro_bundle()
        regime = macro_regime()
        
        score = 0.5  # Neutral baseline
        
        # VIX (low volatility = positive)
        if bundle and 'vix' in bundle:
            vix = bundle['vix'].iloc[-1].iloc[0] if not bundle['vix'].empty else 20
            if vix < 15:
                score += 0.15  # Low vol
            elif vix > 30:
                score -= 0.20  # High vol
        
        # Yield curve (positive slope = healthy)
        if bundle and 'dgs10' in bundle and 'dgs2' in bundle:
            y10 = bundle['dgs10'].iloc[-1].iloc[0] if not bundle['dgs10'].empty else 4.0
            y2 = bundle['dgs2'].iloc[-1].iloc[0] if not bundle['dgs2'].empty else 4.0
            slope = y10 - y2
            if slope > 0.5:
                score += 0.15  # Healthy curve
            elif slope < -0.2:
                score -= 0.20  # Inverted
        
        # Recession probability (from regime)
        if regime and isinstance(regime, dict):
            rec_prob = regime.get('recession_probability', 0.0)
            if rec_prob < 0.20:
                score += 0.10  # Low recession risk
            elif rec_prob > 0.50:
                score -= 0.15  # High recession risk
        
        return float(np.clip(score, 0.0, 1.0))
        
    except Exception as e:
        print(f"⚠️  Macro contribution error: {e}")
        return _macro_contribution_basic()


def _macro_contribution_basic() -> float:
    """Fallback macro scoring using simple FRED queries."""
    try:
        score = 0.5
        
        # VIX
        vix_df = get_fred_series("VIXCLS")
        if not vix_df.empty:
            vix = float(vix_df.iloc[-1, 0])
            if vix < 15:
                score += 0.15
            elif vix > 30:
                score -= 0.20
        
        # Yield curve
        y10_df = get_fred_series("DGS10")
        y2_df = get_fred_series("DGS2")
        if not y10_df.empty and not y2_df.empty:
            slope = float(y10_df.iloc[-1, 0] - y2_df.iloc[-1, 0])
            if slope > 0.5:
                score += 0.15
            elif slope < -0.2:
                score -= 0.20
        
        return float(np.clip(score, 0.0, 1.0))
        
    except Exception:
        return 0.5  # Neutral if errors


# ========================= TECHNICAL SCORING (40%) =========================

def get_technical_contribution(ticker: str) -> float:
    """
    Calculate technical analysis score (0-1).
    
    Factors:
    - RSI (30-70 neutral, <30 oversold=bullish, >70 overbought=bearish)
    - MACD (positive = bullish)
    - SMA trends (price > SMA20 > SMA50 = bullish)
    - Volume trend
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Score 0-1 (0=bearish technical, 1=bullish technical)
    """
    if not HAS_PHASE2:
        return 0.5  # Neutral if no phase2
    
    try:
        # Load prices and compute indicators
        df = load_prices(ticker, period="1y")
        if df is None or df.empty:
            return 0.5
        
        ind = compute_indicators(df)
        signals = technical_signals(ind)
        
        # Use composite score from phase2 (-1 to +1)
        raw_score = signals.score
        
        # Normalize to 0-1
        normalized = (raw_score + 1.0) / 2.0
        
        return float(np.clip(normalized, 0.0, 1.0))
        
    except Exception as e:
        print(f"⚠️  Technical contribution error for {ticker}: {e}")
        return 0.5


# ========================= NEWS SCORING (20%) =========================

def get_news_contribution(ticker: str, window: str = "last_week") -> float:
    """
    Calculate news sentiment score (0-1).
    
    Factors:
    - Mean sentiment
    - News frequency (high = attention)
    - Source quality
    - Event flags (earnings, M&A, etc.)
    
    Args:
        ticker: Stock ticker symbol
        window: Time window for news
    
    Returns:
        Score 0-1 (0=bearish news, 1=bullish news)
    """
    if not HAS_FINNEWS:
        return 0.5  # Neutral if no news
    
    try:
        # Fetch news for ticker
        items = run_pipeline(
            regions=["US", "INTL"],
            window=window,
            tgt_ticker=ticker,
            limit=50
        )
        
        if not items or len(items) == 0:
            return 0.5  # Neutral if no news
        
        # Build features
        features = build_news_features(items, target_ticker=ticker)
        
        if ticker.upper() not in features:
            return 0.5
        
        ticker_feats = features[ticker.upper()]
        
        # Mean sentiment (-1 to +1) → normalize to 0-1
        mean_sent = ticker_feats.get("mean_sentiment", 0.0)
        sent_score = (mean_sent + 1.0) / 2.0
        
        # Positive news ratio boost
        pos_ratio = ticker_feats.get("pos_ratio", 0.0)
        
        # Combine: 70% sentiment, 30% positive ratio
        score = sent_score * 0.7 + pos_ratio * 0.3
        
        return float(np.clip(score, 0.0, 1.0))
        
    except Exception as e:
        print(f"⚠️  News contribution error for {ticker}: {e}")
        return 0.5


# ========================= COMPOSITE SCORING =========================

def compute_composite_score(ticker: str) -> CompositeScore:
    """
    Compute composite score: 40% macro + 40% technical + 20% news.
    
    This is the CORE scoring algorithm.
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        CompositeScore with breakdown
    """
    # Get individual components
    macro_score = get_macro_contribution(ticker)
    tech_score = get_technical_contribution(ticker)
    news_score = get_news_contribution(ticker)
    
    # Weighted sum: 40/40/20
    total = (
        macro_score * 0.4 +
        tech_score * 0.4 +
        news_score * 0.2
    )
    
    return CompositeScore(
        total=float(np.clip(total, 0.0, 1.0)),
        macro=float(macro_score),
        technical=float(tech_score),
        news=float(news_score)
    )


def compute_universe_scores(tickers: List[str]) -> Dict[str, CompositeScore]:
    """
    Compute scores for multiple tickers.
    
    Args:
        tickers: List of ticker symbols
    
    Returns:
        Dict mapping ticker to CompositeScore
    """
    scores = {}
    for ticker in tickers:
        try:
            scores[ticker] = compute_composite_score(ticker)
        except Exception as e:
            print(f"⚠️  Failed to score {ticker}: {e}")
            # Neutral score
            scores[ticker] = CompositeScore(
                total=0.5,
                macro=0.5,
                technical=0.5,
                news=0.5
            )
    return scores


# ========================= TOP SIGNALS & RISKS =========================

def get_top_signals(
    universe: List[str],
    n: int = 3
) -> Tuple[List[TopSignal], List[TopSignal]]:
    """
    Get top N signals and top N risks from universe.
    
    Args:
        universe: List of tickers to analyze
        n: Number of top signals/risks to return
    
    Returns:
        Tuple of (signals, risks)
    """
    scores = compute_universe_scores(universe)
    
    # Sort by total score
    sorted_tickers = sorted(
        scores.items(),
        key=lambda x: x[1].total,
        reverse=True
    )
    
    # Top signals (high scores)
    signals = []
    for ticker, score in sorted_tickers[:n]:
        # Determine primary driver
        drivers = {
            "macro": score.macro,
            "technical": score.technical,
            "news": score.news
        }
        primary = max(drivers, key=drivers.get)
        
        signals.append(TopSignal(
            ticker=ticker,
            type="signal",
            category=primary,
            strength=score.total,
            message=f"Strong {primary} tailwind",
            details=f"Composite: {score.total:.2f} (M:{score.macro:.2f}, T:{score.technical:.2f}, N:{score.news:.2f})"
        ))
    
    # Top risks (low scores)
    risks = []
    for ticker, score in sorted_tickers[-n:]:
        # Determine primary risk
        drivers = {
            "macro": score.macro,
            "technical": score.technical,
            "news": score.news
        }
        primary = min(drivers, key=drivers.get)
        
        risks.append(TopSignal(
            ticker=ticker,
            type="risk",
            category=primary,
            strength=1.0 - score.total,  # Invert for risk
            message=f"Weak {primary} conditions",
            details=f"Composite: {score.total:.2f} (M:{score.macro:.2f}, T:{score.technical:.2f}, N:{score.news:.2f})"
        ))
    
    return signals, risks


# ========================= BRIEF GENERATION =========================

def build_brief(
    period: str = "weekly",
    universe: Optional[List[str]] = None
) -> BriefData:
    """
    Build market brief with top signals, risks, and picks.
    
    Args:
        period: "daily" or "weekly"
        universe: List of tickers to analyze (default: SPY, QQQ, AAPL, NVDA, MSFT)
    
    Returns:
        BriefData with all sections
    """
    if universe is None:
        universe = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT"]
    
    # Get top signals and risks
    signals, risks = get_top_signals(universe, n=3)
    
    # Get all scores for picks
    all_scores = compute_universe_scores(universe)
    
    # Top 3 picks (highest total scores)
    picks = sorted(all_scores.items(), key=lambda x: x[1].total, reverse=True)[:3]
    
    # Build sections
    sections = []
    
    # Macro section
    macro_score = get_macro_contribution()
    macro_status = "Favorable" if macro_score > 0.6 else "Challenging" if macro_score < 0.4 else "Mixed"
    sections.append(BriefSection(
        title="Macro Environment",
        content=f"Current macro conditions are {macro_status} (score: {macro_score:.2f}). "
                f"Consider VIX levels, yield curve, and inflation trends.",
        signals=None,
        risks=None
    ))
    
    # Top picks section
    pick_lines = []
    for ticker, score in picks:
        pick_lines.append(f"{ticker}: {score.total:.2f} (M:{score.macro:.2f} T:{score.technical:.2f} N:{score.news:.2f})")
    
    sections.append(BriefSection(
        title="Top Picks",
        content="\n".join(pick_lines),
        signals=[s.message for s in signals],
        risks=[r.message for r in risks]
    ))
    
    # Create trace
    trace = _create_trace(
        source="composite_scoring",
        asof=date.today(),
        data={"universe": universe, "period": period}
    )
    
    # Build composite scores dict
    composite_scores = {ticker: score for ticker, score in all_scores.items()}
    
    return BriefData(
        title=f"{period.capitalize()} Market Brief",
        date=date.today(),
        period=period,
        sections=sections,
        composite_scores=composite_scores,
        trace=trace
    )


def get_signals_top() -> SignalsData:
    """
    Get top 3 signals and top 3 risks.
    
    This is the main endpoint for the signals page.
    
    Returns:
        SignalsData with top signals and risks
    """
    universe = ["SPY", "QQQ", "DIA", "IWM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    signals, risks = get_top_signals(universe, n=3)
    
    trace = _create_trace(
        source="composite_scoring",
        asof=date.today(),
        data={"universe": universe}
    )
    
    return SignalsData(
        signals=signals,
        risks=risks,
        scoring_weights={"macro": 0.4, "technical": 0.4, "news": 0.2},
        trace=trace
    )
