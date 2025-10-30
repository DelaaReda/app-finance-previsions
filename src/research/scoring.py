"""
Scoring Composite - Pilier central du copilote
Combine macro(40) + technique(40) + news(20) pour produire signaux/risques/picks.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

# Imports des modules existants
from core.market_data import get_fred_series, get_price_history
from analytics.phase2_technical import compute_indicators, technical_signals
from analytics.phase3_macro import get_us_macro_bundle
from ingestion.finnews import run_pipeline as run_news_pipeline


# ============================================================================
# CONFIGURATION
# ============================================================================
MACRO_WEIGHT = 0.40
TECH_WEIGHT = 0.40
NEWS_WEIGHT = 0.20

# Séries macro clés pour scoring
MACRO_SERIES = {
    "CPIAUCSL": "CPI",
    "VIXCLS": "VIX",
    "T10Y2Y": "Yield Curve",
    "UNRATE": "Unemployment",
}


# ============================================================================
# SCORING MACRO
# ============================================================================
def score_macro() -> Dict[str, Any]:
    """
    Score macro basé sur séries FRED clés.
    Retourne: {score: float, signals: List, risks: List, sources: List}
    """
    signals = []
    risks = []
    sources = []
    
    try:
        # Récupérer séries clés
        for series_id, name in MACRO_SERIES.items():
            df = get_fred_series(series_id, start=None)
            if df is None or df.empty:
                continue
            
            # Extraire dernière valeur
            last_value = df["value"].iloc[-1]
            prev_value = df["value"].iloc[-2] if len(df) >= 2 else None
            
            # Ajouter source
            sources.append({
                "type": "macro",
                "series": series_id,
                "name": name,
                "value": float(last_value),
                "date": df.index[-1].isoformat()
            })
            
            # Logique de signaux (simplifié - à enrichir)
            if series_id == "VIXCLS":
                if last_value < 15:
                    signals.append(f"VIX bas ({last_value:.1f}) - Faible volatilité")
                elif last_value > 25:
                    risks.append(f"VIX élevé ({last_value:.1f}) - Volatilité élevée")
            
            elif series_id == "T10Y2Y":
                if last_value < 0:
                    risks.append(f"Courbe inversée ({last_value:.2f}%) - Signal récession")
            
            elif series_id == "CPIAUCSL":
                if len(df) >= 12:
                    yoy = ((last_value / df["value"].iloc[-13]) - 1) * 100
                    if yoy > 4:
                        risks.append(f"Inflation élevée ({yoy:.1f}% YoY)")
                    elif yoy < 2:
                        signals.append(f"Inflation modérée ({yoy:.1f}% YoY)")
        
        # Score global macro (0-100)
        score = 50  # Neutre par défaut
        score += len(signals) * 10
        score -= len(risks) * 10
        score = max(0, min(100, score))
        
    except Exception as e:
        print(f"Erreur score_macro: {e}")
        score = 50
    
    return {
        "score": score,
        "signals": signals,
        "risks": risks,
        "sources": sources
    }


# ============================================================================
# SCORING TECHNIQUE
# ============================================================================
def score_technical(universe: List[str]) -> Dict[str, Any]:
    """
    Score technique pour un univers de tickers.
    Retourne: {score: float, signals: List, risks: List, picks: List, sources: List}
    """
    signals = []
    risks = []
    picks = []
    sources = []
    
    try:
        for ticker in universe:
            df = get_price_history(ticker, start=None, interval="1d")
            if df is None or df.empty:
                continue
            
            # Calculer indicateurs
            df_ind = compute_indicators(df)
            if df_ind.empty:
                continue
            
            last = df_ind.iloc[-1]
            close = last["Close"]
            rsi = last.get("RSI")
            sma_20 = last.get("SMA_20")
            sma_50 = last.get("SMA_50")
            
            # Source
            sources.append({
                "type": "technical",
                "ticker": ticker,
                "price": float(close),
                "rsi": float(rsi) if pd.notna(rsi) else None,
                "date": df_ind.index[-1].isoformat()
            })
            
            # Signaux techniques
            if pd.notna(rsi):
                if rsi < 30:
                    signals.append(f"{ticker} survendu (RSI={rsi:.1f})")
                    picks.append({
                        "ticker": ticker,
                        "rationale": f"RSI survendu à {rsi:.1f}",
                        "score": 70,
                        "type": "buy_signal"
                    })
                elif rsi > 70:
                    risks.append(f"{ticker} suracheté (RSI={rsi:.1f})")
            
            # Croisement SMA
            if pd.notna(sma_20) and pd.notna(sma_50):
                if close > sma_20 > sma_50:
                    signals.append(f"{ticker} tendance haussière (Prix > SMA20 > SMA50)")
                elif close < sma_20 < sma_50:
                    risks.append(f"{ticker} tendance baissière (Prix < SMA20 < SMA50)")
        
        # Score global technique
        score = 50
        score += len(signals) * 5
        score -= len(risks) * 5
        score = max(0, min(100, score))
        
    except Exception as e:
        print(f"Erreur score_technical: {e}")
        score = 50
    
    return {
        "score": score,
        "signals": signals,
        "risks": risks,
        "picks": picks,
        "sources": sources
    }


# ============================================================================
# SCORING NEWS
# ============================================================================
def score_news(universe: List[str], window: str = "last_week") -> Dict[str, Any]:
    """
    Score news basé sur le pipeline finnews.
    Retourne: {score: float, signals: List, risks: List, sources: List}
    """
    signals = []
    risks = []
    sources = []
    
    try:
        # Récupérer news via pipeline
        items = run_news_pipeline(
            regions=["US", "CA", "INTL"],
            window=window,
            query="",
            tgt_ticker=None,
            per_source_cap=None,
            limit=50
        )
        
        # Analyser sentiment et scoring
        for item in items[:20]:  # Top 20
            score = item.get("score", 0)
            sentiment = item.get("sentiment")
            ticker_mentions = item.get("tickers", [])
            
            # Filtrer par univers si pertinent
            relevant = not universe or any(t in universe for t in ticker_mentions)
            
            if not relevant:
                continue
            
            # Ajouter source
            sources.append({
                "type": "news",
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "score": score,
                "sentiment": sentiment,
                "published": item.get("published", "")
            })
            
            # Catégoriser selon sentiment et score
            title = item.get("title", "")
            if sentiment == "positive" and score > 0.7:
                signals.append(f"News positive: {title[:80]}...")
            elif sentiment == "negative" and score > 0.7:
                risks.append(f"News négative: {title[:80]}...")
        
        # Score global news
        avg_score = sum(s["score"] for s in sources) / len(sources) if sources else 0.5
        score = avg_score * 100
        
    except Exception as e:
        print(f"Erreur score_news: {e}")
        score = 50
    
    return {
        "score": score,
        "signals": signals,
        "risks": risks,
        "sources": sources
    }


# ============================================================================
# SCORING COMPOSITE
# ============================================================================
def compute_composite_brief(period: str = "weekly", universe: List[str] = None) -> Dict[str, Any]:
    """
    Génère le Market Brief complet avec scoring composite.
    
    Args:
        period: "daily" ou "weekly"
        universe: Liste de tickers (ex: ["SPY", "QQQ"])
    
    Returns:
        {
            top_signals: List[Dict],
            top_risks: List[Dict],
            picks: List[Dict],
            sources: List[Dict],
            scores: Dict[str, float],
            generated_at: str
        }
    """
    if universe is None:
        universe = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]
    
    window = "last_week" if period == "weekly" else "last_day"
    
    # 1. Scorer chaque pilier
    macro_result = score_macro()
    tech_result = score_technical(universe)
    news_result = score_news(universe, window)
    
    # 2. Score composite pondéré
    composite_score = (
        macro_result["score"] * MACRO_WEIGHT +
        tech_result["score"] * TECH_WEIGHT +
        news_result["score"] * NEWS_WEIGHT
    )
    
    # 3. Agréger signaux et risques
    all_signals = []
    all_signals.extend([{"text": s, "pillar": "macro", "weight": MACRO_WEIGHT} for s in macro_result["signals"]])
    all_signals.extend([{"text": s, "pillar": "technical", "weight": TECH_WEIGHT} for s in tech_result["signals"]])
    all_signals.extend([{"text": s, "pillar": "news", "weight": NEWS_WEIGHT} for s in news_result["signals"]])
    
    all_risks = []
    all_risks.extend([{"text": r, "pillar": "macro", "weight": MACRO_WEIGHT} for r in macro_result["risks"]])
    all_risks.extend([{"text": r, "pillar": "technical", "weight": TECH_WEIGHT} for r in tech_result["risks"]])
    all_risks.extend([{"text": r, "pillar": "news", "weight": NEWS_WEIGHT} for r in news_result["risks"]])
    
    # 4. Top 3 de chaque
    top_signals = all_signals[:3]
    top_risks = all_risks[:3]
    
    # 5. Picks (de tech_result)
    picks = tech_result.get("picks", [])[:5]
    
    # 6. Agréger toutes les sources
    all_sources = []
    all_sources.extend(macro_result["sources"])
    all_sources.extend(tech_result["sources"])
    all_sources.extend(news_result["sources"])
    
    return {
        "top_signals": top_signals,
        "top_risks": top_risks,
        "picks": picks,
        "sources": all_sources,
        "scores": {
            "composite": composite_score,
            "macro": macro_result["score"],
            "technical": tech_result["score"],
            "news": news_result["score"]
        },
        "generated_at": datetime.utcnow().isoformat(),
        "period": period,
        "universe": universe
    }
