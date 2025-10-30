# src/api/services/stocks_service.py
"""
Stocks service facade - wraps analytics/phase2_technical.py and core/market_data.py
Includes LTTB downsampling for efficient charting.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple

import pandas as pd
import numpy as np

from core.market_data import get_price_history, get_fundamentals
from api.schemas import (
    StockOverviewData, PriceData, PricePoint, TechnicalIndicators,
    StockSignal, SignalType, CompositeScore, TraceMetadata,
    StockUniverseData
)

# Try to import phase2 functions
try:
    from analytics.phase2_technical import (
        load_prices,
        compute_indicators,
        technical_signals,
        detect_regime,
        risk_stats,
        build_technical_view
    )
    HAS_PHASE2 = True
except ImportError:
    HAS_PHASE2 = False


# Default universe (can be moved to config)
DEFAULT_UNIVERSE = [
    "SPY", "QQQ", "DIA", "IWM",  # Indices
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",  # Tech
    "JPM", "BAC", "WFC", "GS",  # Finance
    "XOM", "CVX", "COP",  # Energy
    "JNJ", "UNH", "PFE", "ABBV"  # Healthcare
]


def _hash_data(data: Any) -> str:
    """Generate SHA256 hash of data."""
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


def lttb_downsample(points: List[Tuple[float, float]], threshold: int) -> List[Tuple[float, float]]:
    """
    Largest-Triangle-Three-Buckets (LTTB) downsampling algorithm.
    Preserves visual shape while reducing points.
    
    Args:
        points: List of (x, y) tuples
        threshold: Target number of points
    
    Returns:
        Downsampled list of (x, y) tuples
    """
    if len(points) <= threshold or threshold <= 2:
        return points
    
    # Always keep first and last
    sampled = [points[0]]
    
    # Bucket size (minus first and last point)
    bucket_size = (len(points) - 2) / (threshold - 2)
    
    a = 0  # Start from first point
    
    for i in range(threshold - 2):
        # Calculate point range for this bucket
        avg_range_start = int((i + 1) * bucket_size) + 1
        avg_range_end = int((i + 2) * bucket_size) + 1
        avg_range_end = min(avg_range_end, len(points))
        
        # Calculate average point of next bucket (for triangle area calc)
        avg_x = sum(p[0] for p in points[avg_range_start:avg_range_end]) / (avg_range_end - avg_range_start)
        avg_y = sum(p[1] for p in points[avg_range_start:avg_range_end]) / (avg_range_end - avg_range_start)
        
        # Get the range for this bucket
        range_offs = int(i * bucket_size) + 1
        range_to = int((i + 1) * bucket_size) + 1
        
        # Point a
        point_a_x, point_a_y = points[a]
        
        max_area = -1
        next_a = range_offs
        
        # Find point with largest triangle area
        for j in range(range_offs, range_to):
            if j >= len(points):
                break
            
            # Calculate triangle area
            point_j_x, point_j_y = points[j]
            area = abs(
                (point_a_x - avg_x) * (point_j_y - point_a_y) -
                (point_a_x - point_j_x) * (avg_y - point_a_y)
            ) * 0.5
            
            if area > max_area:
                max_area = area
                next_a = j
        
        sampled.append(points[next_a])
        a = next_a
    
    # Always keep last point
    sampled.append(points[-1])
    
    return sampled


def _parse_range(range_str: str) -> Tuple[Optional[str], Optional[str]]:
    """Convert range string to yfinance period/start."""
    ranges = {
        "1m": ("1mo", None),
        "3m": ("3mo", None),
        "6m": ("6mo", None),
        "1y": ("1y", None),
        "2y": ("2y", None),
        "5y": ("5y", None),
        "max": ("max", None)
    }
    return ranges.get(range_str, ("1y", None))


def get_stock_overview(
    ticker: str,
    features: str = "all",
    range_str: str = "1y",
    downsample: int = 1000
) -> StockOverviewData:
    """
    Get complete stock overview with technical indicators, signals, and news.
    
    Args:
        ticker: Stock ticker symbol
        features: Comma-separated features (technicals, fundamentals, signals, news, all)
        range_str: Time range (1m, 3m, 6m, 1y, 2y, 5y, max)
        downsample: Max points for price history (LTTB)
    
    Returns:
        StockOverviewData with all requested features
    """
    feature_list = features.lower().split(",") if features != "all" else ["technicals", "signals"]
    
    # Get price history
    period, start = _parse_range(range_str)
    df = get_price_history(ticker, start=start, interval="1d") if start else None
    
    # Fallback to phase2 if core doesn't work
    if df is None or df.empty:
        if HAS_PHASE2:
            df = load_prices(ticker, period=period)
        else:
            raise ValueError(f"No price data for {ticker}")
    
    if df.empty:
        raise ValueError(f"No price data for {ticker}")
    
    # Current price info
    last_close = float(df["Close"].iloc[-1])
    last_date = df.index[-1].date()
    
    # Calculate price change
    prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else last_close
    change = last_close - prev_close
    change_pct = (change / prev_close * 100) if prev_close != 0 else 0.0
    
    price_data = PriceData(
        current=last_close,
        change=change,
        change_percent=change_pct,
        currency="USD",
        date=last_date
    )
    
    # Price history (downsampled)
    close_series = df["Close"].dropna()
    points = [(int(idx.timestamp()), float(val)) for idx, val in close_series.items()]
    
    if len(points) > downsample:
        points = lttb_downsample(points, downsample)
    
    price_history = [PricePoint(timestamp=int(t), value=v) for t, v in points]
    
    # Technical indicators
    technicals = None
    if "technicals" in feature_list or "all" in feature_list:
        if HAS_PHASE2:
            try:
                ind = compute_indicators(df)
                last = ind.df.iloc[-1]
                
                technicals = TechnicalIndicators(
                    rsi=float(last.get("RSI_14", np.nan)) if pd.notna(last.get("RSI_14")) else None,
                    sma20=float(last.get("SMA_20", np.nan)) if pd.notna(last.get("SMA_20")) else None,
                    sma50=float(last.get("SMA_50", np.nan)) if pd.notna(last.get("SMA_50")) else None,
                    sma200=float(last.get("SMA_200", np.nan)) if pd.notna(last.get("SMA_200")) else None,
                    macd={
                        "value": float(last.get("MACD", np.nan)) if pd.notna(last.get("MACD")) else None,
                        "signal": float(last.get("MACD_Signal", np.nan)) if pd.notna(last.get("MACD_Signal")) else None,
                        "histogram": float(last.get("MACD_Hist", np.nan)) if pd.notna(last.get("MACD_Hist")) else None,
                    },
                    bollinger={
                        "upper": float(last.get("BB_Upper", np.nan)) if pd.notna(last.get("BB_Upper")) else None,
                        "middle": float(last.get("BB_Middle", np.nan)) if pd.notna(last.get("BB_Middle")) else None,
                        "lower": float(last.get("BB_Lower", np.nan)) if pd.notna(last.get("BB_Lower")) else None,
                    }
                )
            except Exception as e:
                print(f"⚠️  Failed to compute technicals: {e}")
    
    # Signals
    signals = []
    if "signals" in feature_list or "all" in feature_list:
        if HAS_PHASE2:
            try:
                ind = compute_indicators(df)
                sig = technical_signals(ind)
                
                # Convert score to signal type
                score = sig.score
                if score > 0.3:
                    sig_type = SignalType.BULLISH
                elif score < -0.3:
                    sig_type = SignalType.BEARISH
                else:
                    sig_type = SignalType.NEUTRAL
                
                # Main signal
                main_signal = StockSignal(
                    type=sig_type,
                    strength=abs(score),
                    message=f"Composite score: {score:.2f}",
                    source="composite"
                )
                signals.append(main_signal)
                
                # Individual component signals
                for label in sig.labels[:3]:  # Top 3 labels
                    signals.append(StockSignal(
                        type=sig_type,
                        strength=abs(score) * 0.7,  # Slightly lower strength
                        message=label,
                        source="technical"
                    ))
                    
            except Exception as e:
                print(f"⚠️  Failed to compute signals: {e}")
    
    # Composite score (mock for now - will be implemented properly later)
    composite_score = None
    if "signals" in feature_list or "all" in feature_list:
        composite_score = CompositeScore(
            total=0.65,  # TODO: Implement real scoring
            macro=0.6,
            technical=0.7,
            news=0.65
        )
    
    # Create trace
    trace = _create_trace("yfinance/phase2", last_date, {
        "ticker": ticker,
        "points": len(price_history),
        "features": feature_list
    })
    
    return StockOverviewData(
        ticker=ticker,
        price=price_data,
        price_history=price_history,
        technicals=technicals,
        signals=signals,
        composite_score=composite_score,
        trace=trace
    )


def get_stock_universe() -> StockUniverseData:
    """
    Get list of tracked tickers.
    
    Returns:
        StockUniverseData with ticker list
    """
    # TODO: Read from config or database
    return StockUniverseData(
        tickers=DEFAULT_UNIVERSE,
        count=len(DEFAULT_UNIVERSE)
    )
