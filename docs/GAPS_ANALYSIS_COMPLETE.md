# Analyse Complète des Gaps - App Finance Prévisions

**Date:** 2 novembre 2025  
**Status:** Analyse détaillée post-investigation

---

## 🎯 Résumé Exécutif

### ✅ Bonne Nouvelle
Les modules critiques `analytics.phase2_technical` et `analytics.phase3_macro` **EXISTENT** et sont **COMPLETS**.

### 🔴 Gaps Bloquants Restants

| # | Gap | Impact | Effort | Priorité |
|---|-----|--------|--------|----------|
| 1 | `core/data_access.py` manquant | 🔴 Bloque scoring | 1-3h | **P0** |
| 2 | `compute_composite_brief()` absent | 🔴 Bloque `/api/brief` | 3-4h | **P0** |
| 3 | RAG non ensemencé | 🔴 Q&A inutilisable | 4-6h | **P0** |
| 4 | LLM non intégré | 🟡 Copilot placeholder | 3-4h | **P1** |
| 5 | Imports inutilisés api/main.py | 🟡 Code smell | 15min | **P1** |

**Total effort P0:** ~8-13h (~1.5-2 jours)

---

## 📦 Inventaire des Modules

### ✅ Modules Existants & Complets

#### Core
- ✅ `core/market_data.py` - FRED, yfinance OK
- ✅ `core/config.py` - Configuration singleton
- ✅ `core/cache.py` - TTL cache
- ✅ `core/io_utils.py` - Parquet/JSONL I/O
- ✅ `core/stock_utils.py` - Utilitaires ticker
- ✅ `core/datasets.py` - Gestion partitions
- ✅ `core/data_quality.py` - Validation timeseries
- ⚠️ `core/data_access.py` - **MANQUANT** (adapter nécessaire)

#### Analytics
- ✅ `analytics/phase1_fundamental.py` - load_prices()
- ✅ `analytics/phase2_technical.py` - **COMPLET**
  - `load_prices(ticker, period, interval)` ✅
  - `compute_indicators(px)` ✅ (SMA, EMA, RSI, MACD, BB, ATR, ADX...)
  - `technical_signals(ind)` ✅ (score composite -1..+1)
  - `detect_regime(ind)` ✅ (Bull/Bear/Range)
  - `risk_stats(px)` ✅ (vol, VaR, max DD)
  - `backtest()` ✅ (moteur vectorisé)
  - `walk_forward_backtest()` ✅

- ✅ `analytics/phase3_macro.py` - **COMPLET**
  - `get_us_macro_bundle(start, monthly)` ✅
  - `macro_nowcast(bundle)` ✅ (z-scores Growth/Inflation/Policy)
  - `build_macro_factors(bundle)` ✅
  - `factor_model(ret, facs)` ✅ (expositions β)
  - `macro_regime(nc)` ✅ (Reflation/Goldilocks/Stagflation...)
  - `scenario_impact(expo, deltas)` ✅

- ✅ `analytics/phase4_sentiment.py`
- ✅ `analytics/phase5_fusion.py`
- ✅ `analytics/forecaster.py`
- ✅ `analytics/econ_llm_agent.py`
- ✅ `analytics/market_intel.py`

#### Research
- ✅ `research/scoring.py` - **Fonctions individuelles OK**
  - `score_macro_conditions()` ✅
  - `score_technical(ticker)` ✅
  - `score_news_sentiment(ticker)` ✅
  - `calculate_composite_score(ticker)` ✅
  - `get_top_signals_and_risks(tickers, top_n)` ✅
  - ⚠️ `compute_composite_brief(period, universe)` - **MANQUANT**

- ✅ `research/rag_store.py` - RAG basique
  - `add_news_item(item)` ✅
  - `add_series_fact(...)` ✅
  - `search(scope, top_k)` ✅
  - ⚠️ Pas de pipeline d'ensemencement automatique

- ✅ `research/nlp_enrich.py` - Sentiment, entités, résumés
- ✅ `research/brief_renderer.py` - HTML/MD rendering
- ✅ `research/alerts.py`
- ✅ `research/peers_finder.py`

#### Ingestion
- ✅ `ingestion/finnews.py` - Pipeline RSS + dédup + scoring
  - `run_pipeline(regions, window, query, tgt_ticker, limit)` ✅
  - `list_sources()` ✅

- ✅ `ingestion/bronze_pipeline.py`
- ✅ `ingestion/gold_features_pipeline.py`
- ✅ `ingestion/silver_pipeline.py`

#### API
- ⚠️ `api/main.py` - Routes avec gaps
  - ✅ `/api/macro/series` - OK
  - ✅ `/api/macro/bundle` - **OK** (dépend de `phase3_macro.get_us_macro_bundle`)
  - ⚠️ `/api/stocks/prices` - Ignore param `range`
  - ✅ `/api/stocks/fundamentals/{ticker}` - OK
  - ✅ `/api/news/feed` - OK
  - ✅ `/api/news/save` - OK
  - 🔴 `/api/brief` - Bloqué par `compute_composite_brief`
  - 🔴 `/api/copilot/ask` - LLM placeholder
  - 🟡 `/api/dashboard/kpis` - Placeholders
  - 🟡 `/api/forecasts` - Stub vide
  - ⚠️ Imports inutilisés: `list_sources`, `load_prices`, `technical_signals`

#### Frontend
- ✅ `webapp/src/` - React/Vite avec TypeScript
  - Types définis (macro, stocks, news, brief, copilot)
  - Layouts, components structure OK
  - ⚠️ Connexion API partielle

---

## 🔍 Analyse Détaillée des Gaps

### **Gap #1: `core/data_access.py` MANQUANT** 🔴

**Impact:** Bloque entièrement le scoring composite  
**Effort:** 1-3h  
**Priorité:** **P0 - Critique**

#### Dépendances Cassées
```python
# Dans research/scoring.py
from core.data_access import (
    get_close_series,           # MANQUANT
    load_macro_forecast_rows,   # MANQUANT
    load_news_features         # MANQUANT
)
```

#### Fonctions Attendues

**1. `get_close_series(ticker: str) -> pd.Series`**
```python
# Doit retourner série de prix Close nettoyée
# Appelé par: score_technical()
```

**2. `load_macro_forecast_rows(limit: int = 1) -> Dict[str, Any]`**
```python
# Doit retourner:
{
    "rows": [{
        "inflation_yoy": float,      # CPI YoY %
        "yield_curve_slope": float,  # 10Y - 2Y (bp)
        "unemployment": float,       # Taux chômage %
        "recession_prob": float      # 0..1
    }]
}
# Appelé par: score_macro_conditions()
```

**3. `load_news_features(limit: int = 100) -> Dict[str, Any]`**
```python
# Doit retourner:
{
    "rows": [{
        "symbol": str,
        "news_score_mean": float,       # Sentiment moyen
        "hours_since_publish": float,
    }, ...]
}
# Appelé par: score_news_sentiment()
```

#### Solution Proposée

**Créer** `src/core/data_access.py`:

```python
"""
Adapter unifié pour accès données (scoring).
Wrappe core.market_data, analytics.phase3_macro, ingestion.finnews.
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.market_data import get_price_history, get_fred_series
from analytics.phase3_macro import get_us_macro_bundle
from ingestion.finnews import run_pipeline


def get_close_series(ticker: str) -> Optional[pd.Series]:
    """
    Retourne série Close nettoyée pour un ticker.
    """
    df = get_price_history(ticker, start=None, interval="1d")
    if df is None or df.empty:
        return None
    return df["Close"].dropna()


def load_macro_forecast_rows(limit: int = 1) -> Dict[str, Any]:
    """
    Retourne snapshot macro actuel via phase3_macro.
    
    Mapping:
    - inflation_yoy: CPI YoY dernière valeur
    - yield_curve_slope: 10Y - 2Y (bp)
    - unemployment: UNRATE dernière valeur
    - recession_prob: Proxy via yield curve < 0
    """
    try:
        bundle = get_us_macro_bundle(start="2020-01-01", monthly=True)
        data = bundle.data
        
        # CPI YoY
        inflation_yoy = None
        if "CPIAUCSL" in data.columns:
            cpi = data["CPIAUCSL"].dropna()
            if len(cpi) >= 12:
                inflation_yoy = float((cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100)
        
        # Yield curve slope
        yield_curve_slope = None
        if "DGS10" in data.columns and "DGS2" in data.columns:
            dgs10 = data["DGS10"].dropna().iloc[-1] if not data["DGS10"].dropna().empty else None
            dgs2 = data["DGS2"].dropna().iloc[-1] if not data["DGS2"].dropna().empty else None
            if dgs10 is not None and dgs2 is not None:
                yield_curve_slope = float(dgs10 - dgs2)
        
        # Unemployment
        unemployment = None
        try:
            unrate = get_fred_series("UNRATE", start="2020-01-01")
            if unrate is not None and not unrate.empty:
                unemployment = float(unrate.iloc[-1])
        except:
            pass
        
        # Recession prob (proxy: yield inversé = +0.5, sinon distance à inversion)
        recession_prob = 0.0
        if yield_curve_slope is not None:
            if yield_curve_slope < 0:
                recession_prob = 0.5 + min(abs(yield_curve_slope) / 100, 0.5)
            else:
                recession_prob = max(0, 0.3 - yield_curve_slope / 100)
        
        return {
            "rows": [{
                "inflation_yoy": inflation_yoy,
                "yield_curve_slope": yield_curve_slope,
                "unemployment": unemployment,
                "recession_prob": float(recession_prob)
            }]
        }
    
    except Exception as e:
        # Fallback vide
        return {
            "rows": [{
                "inflation_yoy": None,
                "yield_curve_slope": None,
                "unemployment": None,
                "recession_prob": 0.0
            }]
        }


def load_news_features(limit: int = 100) -> Dict[str, Any]:
    """
    Retourne features news via finnews pipeline.
    
    Mapping:
    - symbol: ticker extrait (ou None)
    - news_score_mean: score moyen (0..1)
    - hours_since_publish: fraîcheur
    """
    try:
        items = run_pipeline(
            regions=["US", "CA", "INTL"],
            window="last_week",
            query="",
            tgt_ticker=None,
            per_source_cap=None,
            limit=limit
        )
        
        rows = []
        for item in items:
            # Extract ticker (first if multiple)
            tickers = item.get("tickers", [])
            symbol = tickers[0] if tickers else None
            
            # Score moyen (importance * sentiment)
            importance = item.get("importance", 0.5)
            sentiment = item.get("sentiment", 0.0) if item.get("sentiment") is not None else 0.0
            # Normaliser sentiment -1..+1 → 0..1
            sentiment_norm = (sentiment + 1) / 2
            news_score_mean = importance * sentiment_norm
            
            # Fraîcheur
            published = item.get("published", "")
            hours_since = 24.0  # default
            if published:
                try:
                    pub_dt = pd.to_datetime(published)
                    hours_since = (datetime.utcnow() - pub_dt).total_seconds() / 3600
                except:
                    pass
            
            rows.append({
                "symbol": symbol,
                "news_score_mean": float(news_score_mean),
                "hours_since_publish": float(hours_since)
            })
        
        return {"rows": rows}
    
    except Exception as e:
        return {"rows": []}
```

**Critère succès:**
```bash
python -c "from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features; print('✅ OK')"
```

---

### **Gap #2: `compute_composite_brief()` MANQUANT** 🔴

**Impact:** Route `/api/brief` cassée  
**Effort:** 3-4h  
**Priorité:** **P0 - Critique**

#### Fonction Attendue

Dans `research/scoring.py`:

```python
def compute_composite_brief(period: str, universe: List[str]) -> Dict[str, Any]:
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
        if s["tech_score"] > 65:
            reasons.append(f"Technique fort ({s['tech_score']:.0f})")
        if s["news_score"] > 65:
            reasons.append(f"Sentiment positif ({s['news_score']:.0f})")
        
        reason = ", ".join(reasons) if reasons else "Signal composite"
        
        # Confidence (écart-type des composantes)
        components = [s["macro_score"], s["tech_score"], s["news_score"]]
        std = np.std(components)
        confidence = 1.0 - min(std / 50, 1.0)  # Moins de dispersion = plus de confiance
        
        top_signals.append({
            "ticker": s["ticker"],
            "composite_score": s["composite_score"],
            "macro_score": s["macro_score"],
            "tech_score": s["tech_score"],
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
        if s["tech_score"] < 35:
            reasons.append(f"Technique faible ({s['tech_score']:.0f})")
        if s["news_score"] < 35:
            reasons.append(f"Sentiment négatif ({s['news_score']:.0f})")
        
        reason = ", ".join(reasons) if reasons else "Signal composite faible"
        
        top_risks.append({
            "ticker": s["ticker"],
            "composite_score": s["composite_score"],
            "macro_score": s["macro_score"],
            "tech_score": s["tech_score"],
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
```

**Critère succès:**
```bash
curl http://localhost:8050/api/brief?period=weekly&universe=SPY&universe=QQQ | jq '.data.top_signals'
```

---

### **Gap #3: RAG Non Ensemencé** 🔴

**Impact:** Q&A Copilot sans contexte historique  
**Effort:** 4-6h  
**Priorité:** **P0 - Critique**

#### Problème

`research/rag_store.py` existe mais:
- Pas de pipeline d'ensemencement automatique
- Aucune donnée 5 ans macro/prix
- Pas d'injection quotidienne news

#### Solution Proposée

**1. Ajouter endpoint `/api/rag/seed`**

Dans `api/main.py`:

```python
@app.post("/api/rag/seed")
async def seed_rag_store(
    seed_macro: bool = Query(True, description="Seed macro series (5 years)"),
    seed_prices: bool = Query(True, description="Seed prices (5 years)"),
    seed_news: bool = Query(True, description="Seed recent news"),
    universe: List[str] = Query(["SPY", "QQQ", "AAPL", "NVDA", "MSFT"], description="Tickers to seed")
):
    """
    Ensemence le RAG avec données historiques.
    À exécuter une fois au démarrage ou via cron daily.
    """
    try:
        stats_before = rag_store.stats()
        
        # 1. Macro (5 ans, échantillon mensuel)
        if seed_macro:
            from analytics.phase3_macro import get_us_macro_bundle
            from datetime import datetime, timedelta
            
            start_date = (datetime.utcnow() - timedelta(days=365*5)).strftime("%Y-%m-%d")
            bundle = get_us_macro_bundle(start=start_date, monthly=True)
            
            # Séries clés à indexer
            macro_series = {
                "CPIAUCSL": "Inflation (CPI)",
                "UNRATE": "Unemployment Rate",
                "DGS10": "10-Year Treasury",
                "DGS2": "2-Year Treasury",
                "FEDFUNDS": "Fed Funds Rate",
                "INDPRO": "Industrial Production",
                "PAYEMS": "Nonfarm Payrolls"
            }
            
            for series_id, name in macro_series.items():
                if series_id in bundle.data.columns:
                    series = bundle.data[series_id].dropna()
                    # Échantillonner tous les 3 mois pour ne pas gonfler
                    series_sampled = series.iloc[::3]
                    
                    for date, value in series_sampled.items():
                        rag_store.add_series_fact(
                            series_id=series_id,
                            name=name,
                            value=float(value),
                            date=date.strftime("%Y-%m-%d")
                        )
        
        # 2. Prix actions (5 ans, échantillon hebdo)
        if seed_prices:
            from core.market_data import get_price_history
            from datetime import datetime, timedelta
            
            for ticker in universe:
                try:
                    df = get_price_history(ticker, start=(datetime.utcnow() - timedelta(days=365*5)).strftime("%Y-%m-%d"), interval="1wk")
                    if df is not None and not df.empty:
                        for date, row in df.iterrows():
                            rag_store.add_series_fact(
                                series_id=f"{ticker}_CLOSE",
                                name=f"{ticker} Weekly Close",
                                value=float(row["Close"]),
                                date=date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                            )
                except Exception as e:
                    continue
        
        # 3. News récentes (top 100 dernière semaine)
        if seed_news:
            from ingestion.finnews import run_pipeline
            
            items = run_pipeline(
                regions=["US", "CA", "INTL"],
                window="last_week",
                query="",
                tgt_ticker=None,
                per_source_cap=None,
                limit=100
            )
            
            # Injecter seulement si score > 0.5
            for item in items:
                if item.get("score", 0) > 0.5:
                    rag_store.add_news_item(item)
        
        stats_after = rag_store.stats()
        
        return {
            "ok": True,
            "data": {
                "stats_before": stats_before,
                "stats_after": stats_after,
                "added": {
                    "news": stats_after.get("news", 0) - stats_before.get("news", 0),
                    "series": stats_after.get("series", 0) - stats_before.get("series", 0)
                },
                "message": "RAG seeded successfully"
            }
        }
    
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

**2. Ajouter job quotidien (optionnel)**

Dans `src/ops/daily_rag_refresh.py`:

```python
#!/usr/bin/env python3
"""
Job quotidien: ajouter news du jour au RAG.
À exécuter via cron: 0 18 * * * /path/to/.venv/bin/python ops/daily_rag_refresh.py
"""
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.rag_store import RAGStore
from ingestion.finnews import run_pipeline

rag = RAGStore()

# News du jour (top 50, score > 0.5)
items = run_pipeline(
    regions=["US", "CA", "INTL"],
    window="last_day",
    query="",
    tgt_ticker=None,
    limit=50
)

added = 0
for item in items:
    if item.get("score", 0) > 0.5:
        rag.add_news_item(item)
        added += 1

print(f"✅ Added {added} news items to RAG")
print(f"📊 RAG stats: {rag.stats()}")
```

**Critère succès:**
```bash
# 1. Ensemencer
curl -X POST http://localhost:8050/api/rag/seed

# 2. Vérifier stats
curl http://localhost:8050/api/rag/stats | jq '.data.stats'
# Attendu: {"news": >100, "series": >1000}
```

---

### **Gap #4: LLM Non Intégré** 🟡

**Impact:** Copilot retourne placeholder  
**Effort:** 3-4h  
**Priorité:** **P1 - Important**

#### Solution Proposée

**1. Créer client LLM** dans `src/research/llm_client.py`:

```python
"""
Client LLM générique (OpenAI-compatible).
Supporte OpenAI, Anthropic, local (Ollama), etc.
"""
import os
from typing import List, Dict, Any, Optional
import openai

def get_llm_client():
    """Retourne client configuré selon env."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    return openai.OpenAI(api_key=api_key, base_url=base_url)


def ask_llm(
    question: str,
    context_chunks: List[Dict[str, Any]],
    model: str = None,
    max_tokens: int = 1000
) -> Dict[str, Any]:
    """
    Interroge LLM avec contexte RAG.
    
    Args:
        question: Question utilisateur
        context_chunks: Chunks RAG (via rag_store.search())
        model: Modèle (défaut: env LLM_MODEL ou gpt-4o-mini)
        max_tokens: Limite réponse
    
    Returns:
        {
            "answer": str,
            "citations": List[Dict],
            "model": str,
            "tokens": int
        }
    """
    if not model:
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Construire contexte
    context_text = "\n\n".join([
        f"[{i+1}] {chunk['text']}\nSource: {chunk['meta'].get('url', 'N/A')} | Date: {chunk['meta'].get('date', 'N/A')}"
        for i, chunk in enumerate(context_chunks[:10])  # Limiter à 10 chunks
    ])
    
    # Prompt système
    system_prompt = """Tu es un analyste financier expert. 
    
Réponds aux questions en te basant UNIQUEMENT sur le contexte fourni.
- Cite TOUJOURS tes sources avec [numéro]
- Si l'information n'est pas dans le contexte, dis "Je n'ai pas cette information"
- Sois concis et précis
- Utilise des chiffres quand disponibles"""
    
    # Prompt utilisateur
    user_prompt = f"""Contexte (sources de données):
{context_text}

Question: {question}

Réponse (avec citations [1], [2], etc.):"""
    
    try:
        client = get_llm_client()
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        # Extraire citations (numéros entre [])
        import re
        cited_indices = set(int(m.group(1)) - 1 for m in re.finditer(r'\[(\d+)\]', answer))
        
        citations = [
            {
                "index": i + 1,
                "type": context_chunks[i]["meta"]["type"],
                "url": context_chunks[i]["meta"].get("url", ""),
                "date": context_chunks[i]["meta"].get("date", ""),
                "excerpt": context_chunks[i]["text"][:200] + "..."
            }
            for i in cited_indices
            if i < len(context_chunks)
        ]
        
        return {
            "answer": answer,
            "citations": citations,
            "model": model,
            "tokens": tokens
        }
    
    except Exception as e:
        # Fallback: résumé heuristique
        fallback_answer = f"⚠️ LLM indisponible. Voici un résumé des sources:\n\n"
        for i, chunk in enumerate(context_chunks[:5]):
            fallback_answer += f"[{i+1}] {chunk['text'][:150]}...\n"
        
        return {
            "answer": fallback_answer,
            "citations": [],
            "model": "fallback",
            "tokens": 0,
            "error": str(e)
        }
```

**2. Mettre à jour `/api/copilot/ask`** dans `api/main.py`:

```python
from research.llm_client import ask_llm

@app.post("/api/copilot/ask")
async def copilot_ask(request: CopilotRequest):
    """Q&A avec LLM + RAG citations."""
    try:
        # 1. Rechercher contexte dans RAG
        scope = request.scope or {}
        if request.tickers:
            scope["tickers"] = request.tickers
        
        context_chunks = rag_store.search(scope, top_k=10)
        
        if not context_chunks:
            return {
                "ok": True,
                "data": {
                    "answer": "Je n'ai pas trouvé de données pertinentes pour répondre à cette question. Veuillez ensemencer le RAG avec /api/rag/seed.",
                    "citations": [],
                    "generated_at": datetime.utcnow().isoformat()
                }
            }
        
        # 2. Appeler LLM
        llm_response = ask_llm(
            question=request.question,
            context_chunks=context_chunks,
            max_tokens=1000
        )
        
        return {
            "ok": True,
            "data": {
                "answer": llm_response["answer"],
                "citations": llm_response["citations"],
                "model": llm_response.get("model"),
                "tokens": llm_response.get("tokens"),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

**Configuration** (`.env`):

```bash
# LLM Provider
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1  # ou https://api.anthropic.com pour Claude
LLM_MODEL=gpt-4o-mini  # ou claude-3-5-sonnet-20241022
```

**Critère succès:**
```bash
curl -X POST http://localhost:8050/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quelle est l'\''inflation actuelle ?",
    "scope": {"type": "macro"}
  }' | jq '.data.answer'
```

---

### **Gap #5: Imports Inutilisés api/main.py** 🟡

**Impact:** Code smell, confusion  
**Effort:** 15min  
**Priorité:** **P1 - Cleanup**

#### Imports à Retirer

```python
# Dans api/main.py ligne 22-23
from analytics.phase2_technical import load_prices, compute_indicators, technical_signals
# ❌ load_prices et technical_signals non utilisés
# ✅ compute_indicators utilisé ligne 324

from ingestion.finnews import run_pipeline as run_news_pipeline, list_sources
# ❌ list_sources non utilisé
# ✅ run_news_pipeline utilisé ligne 213
```

#### Correction

```python
# Garder seulement
from analytics.phase2_technical import compute_indicators
from analytics.phase3_macro import get_us_macro_bundle
from ingestion.finnews import run_pipeline as run_news_pipeline
```

---

## 📋 Checklist d'Implémentation

### Phase 1: Déblocage Scoring (3-4h)

- [ ] **1.1** Créer `src/core/data_access.py`
  - [ ] `get_close_series(ticker)`
  - [ ] `load_macro_forecast_rows(limit)`
  - [ ] `load_news_features(limit)`
  - [ ] Test import: `python -c "from core.data_access import ..."`

- [ ] **1.2** Implémenter `compute_composite_brief()` dans `research/scoring.py`
  - [ ] Logique top_signals/top_risks
  - [ ] Picks (score >= 65)
  - [ ] Sources traçabilité
  - [ ] Test: `curl /api/brief`

### Phase 2: Ensemencement RAG (4-6h)

- [ ] **2.1** Ajouter endpoint `/api/rag/seed`
  - [ ] Macro 5 ans (échantillon mensuel/trimestriel)
  - [ ] Prix 5 ans (échantillon hebdo)
  - [ ] News récentes (top 100, score > 0.5)
  - [ ] Test: `curl -X POST /api/rag/seed`

- [ ] **2.2** Créer job daily `ops/daily_rag_refresh.py`
  - [ ] Injection news quotidienne
  - [ ] Cron setup (optionnel)

- [ ] **2.3** Vérifier stats RAG
  - [ ] `rag_store.stats()` > 1000 chunks

### Phase 3: Intégration LLM (3-4h)

- [ ] **3.1** Créer `src/research/llm_client.py`
  - [ ] `get_llm_client()`
  - [ ] `ask_llm(question, context_chunks)`
  - [ ] Fallback heuristique si erreur

- [ ] **3.2** Mettre à jour `/api/copilot/ask`
  - [ ] Appeler `ask_llm()` avec RAG context
  - [ ] Retourner citations extraites
  - [ ] Test: `curl -X POST /api/copilot/ask`

- [ ] **3.3** Configuration `.env`
  - [ ] `OPENAI_API_KEY`
  - [ ] `LLM_MODEL` (gpt-4o-mini par défaut)

### Phase 4: Corrections Mineures (1h)

- [ ] **4.1** Nettoyer imports `api/main.py`
  - [ ] Retirer `load_prices`, `technical_signals`, `list_sources`

- [ ] **4.2** Corriger `/api/stocks/prices`
  - [ ] Respecter param `range` (mapper vers `start` date)

- [ ] **4.3** Compléter `/api/dashboard/kpis`
  - [ ] Calculs réels (timestamps, counts depuis RAG/data)

---

## 🧪 Tests de Validation MVP

### Test 1: Scoring Composite
```bash
curl http://localhost:8050/api/brief?period=weekly&universe=SPY&universe=QQQ | jq '.data | {top_signals, top_risks}'
# Attendu: 3 signaux + 3 risques avec scores cohérents
```

### Test 2: RAG Stats
```bash
curl http://localhost:8050/api/rag/stats | jq '.data.stats'
# Attendu: {"news": >100, "series": >1000}
```

### Test 3: Copilot Q&A
```bash
curl -X POST http://localhost:8050/api/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Quelle est l'\''inflation US actuelle ?"}' | jq '.data | {answer, citations}'
# Attendu: Réponse avec ≥2 citations
```

### Test 4: Health Check
```bash
curl http://localhost:8050/health | jq '.services'
# Attendu: {fred: true, yfinance: true, news: true, rag: true}
```

---

## 📊 Métriques de Succès MVP

| Critère | Target | Test |
|---------|--------|------|
| Brief généré | < 30s | `time curl /api/brief` |
| Q&A réponse | < 10s | `time curl -X POST /api/copilot/ask` |
| RAG chunks | > 1000 | `curl /api/rag/stats` |
| Citations Q&A | ≥ 2 | Inspecter `.data.citations[]` |
| Tickers couverts | ≥ 5 | `/api/brief?universe=...` |
| News fraîcheur médiane | < 30min | Analyser `.data.news_top[].hours_since` |

---

## 🚨 Risques & Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| FRED API rate limit | 🟡 | Faible | Cache 24h, fallback CSV |
| LLM API coût élevé | 🟡 | Moyen | Limiter tokens, cache réponses |
| RAG JSONL trop lourd | 🟡 | Moyen | Échantillonner (mensuel/hebdo), top-N news |
| `phase3_macro` données manquantes | 🟡 | Faible | Graceful degradation, warnings explicites |
| Frontend déconnecté | 🟡 | Faible | Tests E2E, contrats API |

---

## 📝 Notes Techniques

### Modules Confirmés Complets
- ✅ `analytics/phase2_technical.py` - 841 lignes, toutes fonctions présentes
- ✅ `analytics/phase3_macro.py` - 1000 lignes, bundle macro robuste
- ✅ `ingestion/finnews.py` - Pipeline RSS fonctionnel
- ✅ `research/rag_store.py` - RAG basique mais solide

### Points de Vigilance
1. **Cohérence features news:** `load_news_features()` doit aligner champs avec `score_news_sentiment()`
2. **Qualité métriques macro:** Si `get_us_macro_bundle()` rate, fallback requis
3. **Volume RAG:** JSONL peut gonfler → monitoring taille fichier
4. **LLM timeout:** Ajouter timeout 30s + fallback heuristique

### Opportunités d'Optimisation (Post-MVP)
- Cache Redis pour FRED/yfinance (TTL 1h-1j)
- Embeddings RAG (FAISS/Qdrant) si > 10k chunks
- LLM streaming pour meilleure UX
- Compression parquet (Snappy/Zstd)

---

## 🎯 Prochaines Étapes

### Semaine 1 (J1-J3)
- **J1:** Implémenter `core/data_access.py` + tests
- **J2:** Implémenter `compute_composite_brief()` + endpoint `/api/brief`
- **J3:** Ensemencer RAG + endpoint `/api/rag/seed`

### Semaine 2 (J4-J5)
- **J4:** Client LLM + `/api/copilot/ask`
- **J5:** Tests E2E + corrections mineures

### Go-Live MVP
- Tous endpoints 2xx
- Brief généré < 30s
- Q&A avec ≥2 citations
- RAG > 1000 chunks

---

**Document maintenu par:** Analyse Automatique  
**Dernière mise à jour:** 2 novembre 2025  
**Prochaine révision:** Post-implémentation P0
