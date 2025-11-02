# src/research/scoring.py
"""
Composite scoring system: Macro (40%) + Technical (40%) + News (20%)
Generates Top 3 Signals and Top 3 Risks
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime

# Scoring weights (configurable)
WEIGHTS = {
    "macro": 0.40,
    "technical": 0.40,
    "news": 0.20
}

# ============================= MACRO SCORING =================================

def score_macro_conditions() -> Dict[str, float]:
    """
    Score macro conditions based on:
    - Inflation trend (lower = better)
    - Yield curve (steep positive = better)
    - Unemployment (lower = better)
    - Recession probability (lower = better)
    
    Returns dict with scores 0-100 for each indicator
    """
    try:
        from core.data_access import load_macro_forecast_rows
        result = load_macro_forecast_rows(limit=1)
        if not result.get("ok") or not result.get("rows"):
            return {"macro_score": 50.0, "detail": "no_data"}
        
        row = result["rows"][0]
        
        # Individual scores (0-100)
        inflation = row.get("inflation_yoy", 0.03)
        inflation_score = max(0, min(100, (1 - abs(inflation - 0.02) / 0.08) * 100))
        
        yield_curve = row.get("yield_curve_slope", 0)
        yield_score = max(0, min(100, (yield_curve + 1) / 2 * 100))
        
        unemployment = row.get("unemployment", 4.5)
        unemployment_score = max(0, min(100, (1 - (unemployment - 3) / 7) * 100))
        
        recession_prob = row.get("recession_prob", 0.3)
        recession_score = max(0, min(100, (1 - recession_prob) * 100))
        
        # Composite macro score
        macro_score = (
            inflation_score * 0.3 +
            yield_score * 0.3 +
            unemployment_score * 0.2 +
            recession_score * 0.2
        )
        
        return {
            "macro_score": round(macro_score, 2),
            "inflation_score": round(inflation_score, 2),
            "yield_score": round(yield_score, 2),
            "unemployment_score": round(unemployment_score, 2),
            "recession_score": round(recession_score, 2),
            "inflation_yoy": inflation,
            "yield_curve": yield_curve,
            "unemployment": unemployment,
            "recession_prob": recession_prob
        }
        
    except Exception as e:
        return {"macro_score": 50.0, "error": str(e)}

# ============================ TECHNICAL SCORING ==============================

def score_technical(ticker: str) -> Dict[str, float]:
    """
    Score technical indicators for a ticker:
    - Trend (SMA20 vs SMA50)
    - Momentum (RSI)
    - Volume
    
    Returns dict with scores 0-100
    """
    try:
        from core.data_access import get_close_series
        series = get_close_series(ticker)
        
        if series is None or len(series) < 50:
            return {"technical_score": 50.0, "ticker": ticker, "detail": "insufficient_data"}
        
        # Calculate SMA
        sma20 = series.rolling(20).mean()
        sma50 = series.rolling(50).mean()
        
        # Trend score: is price above SMAs and SMAs aligned?
        current_price = series.iloc[-1]
        current_sma20 = sma20.iloc[-1]
        current_sma50 = sma50.iloc[-1]
        
        trend_score = 0
        if current_price > current_sma20:
            trend_score += 40
        if current_sma20 > current_sma50:
            trend_score += 30
        if current_price > current_sma50:
            trend_score += 30
        
        # Simple RSI calculation (14 periods)
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        # RSI score: favor 40-70 range
        if 40 <= current_rsi <= 70:
            rsi_score = 100
        elif current_rsi < 40:
            rsi_score = max(0, current_rsi / 40 * 100)
        else:  # > 70
            rsi_score = max(0, (100 - current_rsi) / 30 * 100)
        
        # Composite technical score
        technical_score = trend_score * 0.6 + rsi_score * 0.4
        
        return {
            "technical_score": round(technical_score, 2),
            "ticker": ticker,
            "trend_score": round(trend_score, 2),
            "rsi_score": round(rsi_score, 2),
            "current_price": round(current_price, 2),
            "sma20": round(current_sma20, 2),
            "sma50": round(current_sma50, 2),
            "rsi": round(current_rsi, 2)
        }
        
    except Exception as e:
        return {"technical_score": 50.0, "ticker": ticker, "error": str(e)}

# ============================== NEWS SCORING =================================

def score_news_sentiment(ticker: Optional[str] = None) -> Dict[str, float]:
    """
    Score news sentiment:
    - Overall sentiment (positive = higher score)
    - News freshness
    - News volume
    
    Returns dict with scores 0-100
    """
    try:
        from core.data_access import load_news_features
        result = load_news_features(limit=100)
        
        if not result.get("ok") or not result.get("rows"):
            return {"news_score": 50.0, "detail": "no_news"}
        
        rows = result["rows"]
        
        # Filter by ticker if specified
        if ticker:
            rows = [r for r in rows if r.get("symbol") == ticker]
        
        if not rows:
            return {"news_score": 50.0, "ticker": ticker, "detail": "no_news_for_ticker"}
        
        # Calculate average sentiment (assume scale -1 to 1)
        sentiments = [r.get("news_score_mean", 0) for r in rows if r.get("news_score_mean")]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Convert to 0-100 scale (0 = very negative, 50 = neutral, 100 = very positive)
        news_score = (avg_sentiment + 1) / 2 * 100
        
        # Freshness bonus: recent news (last 24h) adds points
        recent_count = len([r for r in rows if r.get("hours_since_publish", 999) < 24])
        freshness_bonus = min(20, recent_count * 2)
        
        news_score = min(100, news_score + freshness_bonus)
        
        return {
            "news_score": round(news_score, 2),
            "avg_sentiment": round(avg_sentiment, 3),
            "news_count": len(rows),
            "recent_count": recent_count,
            "ticker": ticker
        }
        
    except Exception as e:
        return {"news_score": 50.0, "ticker": ticker, "error": str(e)}

# =========================== COMPOSITE SCORING ===============================

def calculate_composite_score(ticker: str) -> Dict[str, float]:
    """
    Calculate composite score for a ticker using 40/40/20 weighting.
    
    Returns:
        Dict with composite_score and component scores
    """
    macro = score_macro_conditions()
    technical = score_technical(ticker)
    news = score_news_sentiment(ticker)
    
    composite_score = (
        macro["macro_score"] * WEIGHTS["macro"] +
        technical["technical_score"] * WEIGHTS["technical"] +
        news["news_score"] * WEIGHTS["news"]
    )
    
    return {
        "ticker": ticker,
        "composite_score": round(composite_score, 2),
        "macro_score": macro["macro_score"],
        "technical_score": technical["technical_score"],
        "news_score": news["news_score"],
        "weights": WEIGHTS,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "macro": macro,
            "technical": technical,
            "news": news
        }
    }

def get_top_signals_and_risks(tickers: List[str], top_n: int = 3) -> Dict[str, List]:
    """
    Calculate composite scores for all tickers and return top signals and risks.
    
    Args:
        tickers: List of ticker symbols
        top_n: Number of top/bottom to return
        
    Returns:
        Dict with 'signals' (top N) and 'risks' (bottom N)
    """
    scores = []
    
    for ticker in tickers:
        try:
            score = calculate_composite_score(ticker)
            scores.append(score)
        except Exception as e:
            print(f"Error scoring {ticker}: {e}")
            continue
    
    # Sort by composite score
    scores.sort(key=lambda x: x["composite_score"], reverse=True)
    
    return {
        "signals": scores[:top_n],
        "risks": scores[-top_n:][::-1],  # reverse to show worst first
        "scoring_method": "composite_40_40_20",
        "weights": WEIGHTS,
        "timestamp": datetime.utcnow().isoformat(),
        "total_analyzed": len(scores)
    }

def compute_composite_brief(period: str = "weekly", universe: List[str] = None) -> Dict[str, Any]:
    """
    Génère Market Brief complet.
    
    Args:
        period: "daily" ou "weekly"
        universe: Liste de tickers (ex: ["SPY", "QQQ", "AAPL", "NVDA"])
    
    Returns:
        {
            "top_signals": [
                {
                    "ticker": str,
                    "composite_score": float (0-100),
                    "macro_score": float,
                    "tech_score": float,
                    "news_score": float,
                    "reason": str,
                    "confidence": float
                },
                ...  # Top 3
            ],
            "top_risks": [...],  # Bottom 3
            "picks": [
                {
                    "ticker": str,
                    "composite_score": float,
                    "action": "BUY" | "HOLD" | "SELL",
                    "price": float,
                    "targets": {"support": float, "resistance": float}
                },
                ...  # Tickers > 65
            ],
            "sources": [
                {"type": "macro", "series_id": str, "last_value": float},
                {"type": "news", "count": int, "window": str},
                {"type": "technical", "tickers": List[str]}
            ],
            "generated_at": str (ISO),
            "period": str,
            "universe": List[str]
        }
    """
    if universe is None:
        universe = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    # 1. Calculer scores pour chaque ticker
    scores = []
    for ticker in universe:
        try:
            score = calculate_composite_score(ticker)
            scores.append({
                "ticker": ticker,
                **score
            })
        except Exception as e:
            continue
    
    if not scores:
        return {
            "top_signals": [],
            "top_risks": [],
            "picks": [],
            "sources": [],
            "generated_at": datetime.utcnow().isoformat(),
            "period": period,
            "universe": universe,
            "error": "No scores computed"
        }
    
    # 2. Trier par composite_score
    sorted_scores = sorted(scores, key=lambda x: x["composite_score"], reverse=True)
    
    # 3. Top 3 signals (meilleurs)
    top_signals = []
    for s in sorted_scores[:3]:
        # Générer raison (composantes dominantes)
        reasons = []
        if s["macro_score"] > 65:
            reasons.append(f"Macro favorable ({s['macro_score']:.0f})")
        if s["technical_score"] > 65:  # Changed from 'tech_score' to match actual structure
            reasons.append(f"Technique fort ({s['technical_score']:.0f})")
        if s["news_score"] > 65:
            reasons.append(f"Sentiment positif ({s['news_score']:.0f})")
        
        reason = ", ".join(reasons) if reasons else "Signal composite"
        
        # Confidence (écart-type des composantes)
        components = [s["macro_score"], s["technical_score"], s["news_score"]]
        std = np.std(components)
        confidence = 1.0 - min(std / 50, 1.0)  # Moins de dispersion = plus de confiance
        
        top_signals.append({
            "ticker": s["ticker"],
            "composite_score": s["composite_score"],
            "macro_score": s["macro_score"],
            "technical_score": s["technical_score"],  # Changed from 'tech_score'
            "news_score": s["news_score"],
            "reason": reason,
            "confidence": float(confidence)
        })
    
    # 4. Top 3 risks (pires)
    top_risks = []
    for s in sorted_scores[-3:]:
        reasons = []
        if s["macro_score"] < 35:
            reasons.append(f"Macro défavorable ({s['macro_score']:.0f})")
        if s["technical_score"] < 35:  # Changed from 'tech_score' to match actual structure
            reasons.append(f"Technique faible ({s['technical_score']:.0f})")
        if s["news_score"] < 35:
            reasons.append(f"Sentiment négatif ({s['news_score']:.0f})")
        
        reason = ", ".join(reasons) if reasons else "Signal composite faible"
        
        top_risks.append({
            "ticker": s["ticker"],
            "composite_score": s["composite_score"],
            "macro_score": s["macro_score"],
            "technical_score": s["technical_score"],  # Changed from 'tech_score'
            "news_score": s["news_score"],
            "reason": reason
        })
    
    # 5. Picks (score >= 65)
    picks = []
    for s in sorted_scores:
        if s["composite_score"] >= 65:
            # Déterminer action
            if s["composite_score"] >= 75:
                action = "BUY"
            elif s["composite_score"] >= 65:
                action = "HOLD"
            else:
                action = "SELL"
            
            # Prix et niveaux (via market_data)
            try:
                from core.market_data import get_price_history
                df = get_price_history(s["ticker"], start=None, interval="1d")
                if df is not None and not df.empty:
                    price = float(df["Close"].iloc[-1])
                    # Support/Resistance simples (20d low/high)
                    support = float(df["Low"].tail(20).min())
                    resistance = float(df["High"].tail(20).max())
                else:
                    price = None
                    support = None
                    resistance = None
            except:
                price = None
                support = None
                resistance = None
            
            picks.append({
                "ticker": s["ticker"],
                "composite_score": s["composite_score"],
                "action": action,
                "price": price,
                "targets": {
                    "support": support,
                    "resistance": resistance
                }
            })
    
    # 6. Sources traçabilité
    sources = []
    
    # Macro sources
    try:
        from core.data_access import load_macro_forecast_rows
        macro_data = load_macro_forecast_rows(limit=1)
        row = macro_data["rows"][0] if macro_data["rows"] else {}
        if row.get("inflation_yoy") is not None:
            sources.append({
                "type": "macro",
                "series_id": "CPIAUCSL",
                "last_value": row["inflation_yoy"],
                "metric": "Inflation YoY (%)"
            })
        if row.get("yield_curve_slope") is not None:
            sources.append({
                "type": "macro",
                "series_id": "DGS10-DGS2",
                "last_value": row["yield_curve_slope"],
                "metric": "Yield Curve Slope (bp)"
            })
    except:
        pass
    
    # News sources
    try:
        from core.data_access import load_news_features
        news_data = load_news_features(limit=50)
        news_count = len(news_data.get("rows", []))
        sources.append({
            "type": "news",
            "count": news_count,
            "window": "last_week",
            "provider": "finnews RSS"
        })
    except:
        pass
    
    # Technical sources
    sources.append({
        "type": "technical",
        "tickers": [s["ticker"] for s in scores],
        "indicators": ["SMA", "RSI", "MACD", "BB"]
    })
    
    return {
        "top_signals": top_signals,
        "top_risks": top_risks,
        "picks": picks,
        "sources": sources,
        "generated_at": datetime.utcnow().isoformat(),
        "period": period,
        "universe": universe
    }

# ================================= EXPORT ====================================

__all__ = [
    "score_macro_conditions",
    "score_technical",
    "score_news_sentiment",
    "calculate_composite_score",
    "get_top_signals_and_risks",
    "compute_composite_brief",  # Add the new function
    "WEIGHTS"
]
