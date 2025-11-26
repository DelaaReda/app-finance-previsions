# 🎯 ANALYSE COMPLÈTE - DATA ENRICHMENT STRATEGY FOR LLM JUDGE

**Date :** 2025-11-25 23:26  
**Objectif :** Rassembler TOUTES les données utiles pour maximiser la qualité des prévisions LLM

---

## 📊 ÉTAT DES LIEUX - MODULES DISPONIBLES

### **Analytics Modules Existants**

| Module | Fonction | Données Produites | Utilisé dans Judge? |
|--------|----------|-------------------|---------------------|
| **phase1_fundamental** | Analysis fondamentale avancée | Fair value, DCF, health ratios, peer multiples | ⚠️ PARTIEL via judge_features |
| **phase2_technical** | Analyse technique complète | RSI, MACD, Bollinger, patterns, support/resistance | ⚠️ PARTIEL (RSI seulement) |
| **phase3_macro** | Contexte macroéconomique | VIX, taux, commodities, régimes macro | ✅ OUI via macro_snapshot |
| **phase4_sentiment** | Sentiment multi-sources | News sentiment, social media, analyst ratings | ⚠️ PARTIEL (news seulement) |
| **phase5_fusion** | Score composite | Fusion des 4 phases, weighted score | ❌ NON |
| **phases_adapter** | Summaries légers | Phase scores + summaries | ✅ OUI |
| **ml_baseline** | ML predictions | Direction, return, confidence | ✅ OUI (ml_prior) |
| **econ_llm_agent** | LLM analysis | Structured verdict | ✅ OUI (le judge) |
| **forecaster** | Time series forecast | Price predictions | ❌ NON |
| **market_intel** | Market intelligence | Sector trends, correlations | ❌ NON |
| **recommender** | Stock recommendations | Top picks, scores | ❌ NON |

### **Data Sources Disponibles**

| Source | Fichier | Contenu | Utilisé? |
|--------|---------|---------|----------|
| **Prices** | `stocks/prices.json` | OHLCV historiques | ✅ Calcul tech |
| **News** | `news_feed.json` | Articles + sentiment | ✅ Scored top 5 |
| **Macro** | `macro_series.json` | Séries FRED (VIX, rates, CPI, DXY, commodities) | ✅ Snapshot |
| **Ownership** | `ownership_snapshot.json` | Sector, PE, beta, market cap | ✅ Features |
| **Judge Features** | `judge_features.json` | Pre-computed technical + fundamentals | ✅ Main source |
| **Forecasts** | `forecasts.json` | Prévisions existantes | ❌ Pas utilisé dans judge |
| **Brief Daily** | `brief_daily.json` | Daily market summary | ⚠️ Context only |
| **Intelligence** | `intelligence_snapshot.json` | Market intelligence summary | ❌ NON |
| **Quality Report** | `quality_report.json` | Data quality metrics | ❌ NON |
| **Recommendations** | `recommendations_daily.json` | Stock recommendations | ❌ NON |
| **Backtests** | `backtests.json` | Strategy backtest results | ❌ NON |

---

## 🔍 GAP ANALYSIS - CE QUI MANQUE

### **CRITICAL GAPS (Haute Priorité)** 🔥

#### **1. Phase 5 Fusion Score** ❌
**Manque :**
- Score composite des 4 phases
- Weighted average avec confiance
- Conviction globale

**Impact sur LLM :**
- Pas de vision holistique
- LLM doit faire la fusion lui-même (moins fiable)
- Manque un "signal fort" unifié

**Solution :**
```python
# Call phase5_fusion pour chaque ticker
from analytics.phase5_fusion import compute_fusion_score

fusion_result = compute_fusion_score(
    fundamental_score=phases["fundamental"]["score"],
    technical_score=phases["technical"]["score"],
    macro_score=phases["macro"]["score"],
    sentiment_score=phases["sentiment"]["score"],
    weights={"fundamental": 0.3, "technical": 0.25, "macro": 0.25, "sentiment": 0.2}
)

# Add to payload
payload["fusion"] = {
    "score": fusion_result.composite_score,
    "conviction": fusion_result.conviction,
    "dominant_signal": fusion_result.dominant_phase,
    "agreement": fusion_result.phase_agreement,  # % phases agree
}
```

---

#### **2. Full Technical Analysis** ⚠️
**Manque :**
- Bollinger Bands (overbought/oversold)
- MACD (momentum direction)
- Support/Resistance levels (key levels)
- Volume analysis (accumulation/distribution)
- Chart patterns (triangles, flags, etc.)

**Actuellement :** Seulement RSI + SMA

**Impact sur LLM :**
- Vision technique incomplète
- Manque signaux momentum
- Pas de niveaux clés pour risk/reward

**Solution :**
```python
# Use phase2_technical complete analysis
from analytics.phase2_technical import analyze_technical

tech_full = analyze_technical(ticker)

# Add to features
features["technical_full"] = {
    "rsi": tech_full.rsi,
    "macd": {"value": tech_full.macd, "signal": tech_full.macd_signal, "histogram": tech_full.macd_hist},
    "bollinger": {"upper": tech_full.bb_upper, "lower": tech_full.bb_lower, "position": tech_full.bb_position},
    "support_resistance": {"support": tech_full.support_levels, "resistance": tech_full.resistance_levels},
    "volume_profile": {"trend": tech_full.volume_trend, "divergence": tech_full.volume_divergence},
    "patterns": tech_full.detected_patterns,  # "ascending_triangle", "double_bottom", etc.
}
```

---

#### **3. Fundamental Deep Dive** ⚠️
**Manque :**
- Fair value (DCF + comparables)
- Health ratios (ROE, ROIC, FCF yield)
- Peer multiples (P/E, EV/EBITDA vs sector)
- Growth metrics (revenue growth, margins expansion)

**Actuellement :** Basic fundamentals seulement (PE, beta, sector)

**Impact sur LLM :**
- Pas de notion de valuation (cheap/expensive?)
- Manque santé financière
- Pas de comparaison aux pairs

**Solution :**
```python
# Use phase1_fundamental complete analysis
from analytics.phase1_fundamental import analyze_fundamental

fund_full = analyze_fundamental(ticker)

# Add to features
features["fundamental_full"] = {
    "fair_value": {
        "central": fund_full.fair_value.fv_composite,
        "upside_pct": fund_full.fair_value.upside_pct,
        "confidence": fund_full.fair_value.confidence,
    },
    "health": {
        "roe_pct": fund_full.health.roe_pct,
        "roic_pct": fund_full.health.roic_pct,
        "fcf_yield_pct": fund_full.health.fcf_yield_pct,
        "net_debt_to_ebitda": fund_full.health.net_debt_to_ebitda,
    },
    "valuation": {
        "pe_vs_sector": fund_full.zscores.pe_z,  # Z-score vs peers
        "ev_ebitda_vs_sector": fund_full.zscores.ev_ebitda_z,
    },
}
```

---

#### **4. Sentiment Multi-Source** ⚠️
**Manque :**
- Social media sentiment (Reddit, Twitter)
- Analyst ratings consensus
- Options flow (bullish/bearish positioning)
- Institutional ownership trends

**Actuellement :** News sentiment seulement (top 5 articles)

**Impact sur LLM :**
- Vision sentiment incomplète
- Manque "smart money" signals
- Pas de mesure de conviction retail vs institutional

**Solution :**
```python
# Use phase4_sentiment complete analysis
from analytics.phase4_sentiment import analyze_sentiment

sent_full = analyze_sentiment(ticker)

# Add to features
features["sentiment_full"] = {
    "news": {"score": sent_full.news_sentiment, "count": len(news_items)},
    "social": {"score": sent_full.social_sentiment, "volume": sent_full.social_volume},
    "analysts": {
        "rating": sent_full.analyst_rating,  # buy/hold/sell consensus
        "target_price": sent_full.avg_target_price,
        "upside_to_target": sent_full.upside_to_target_pct,
    },
    "institutional": {
        "ownership_pct": sent_full.inst_ownership_pct,
        "trend": sent_full.inst_trend,  # "increasing", "decreasing", "stable"
    },
}
```

---

#### **5. Market Context & Correlations** ❌
**Manque :**
- Sector performance vs benchmark
- Stock correlation to indices (SPY, QQQ)
- Peer stocks performance (similar stocks)
- Market regime (bullish, bearish, sideways)

**Impact sur LLM :**
- Pas de contexte marché élargi
- Manque understanding relative performance
- Pas de notion de risk-on/risk-off

**Solution :**
```python
# Use market_intel module
from analytics.market_intel import get_market_context

market_ctx = get_market_context(ticker)

# Add to payload
payload["market_context"] = {
    "regime": market_ctx.market_regime,  # "risk_on", "risk_off", "neutral"
    "sector_vs_spy": market_ctx.sector_performance_vs_spy,
    "stock_vs_sector": market_ctx.stock_performance_vs_sector,
    "correlation_spy": market_ctx.correlation_spy,
    "correlation_sector": market_ctx.correlation_sector,
    "peer_stocks": [
        {"ticker": p.ticker, "return_1m": p.return_1m, "correlation": p.correlation}
        for p in market_ctx.similar_stocks[:5]
    ],
}
```

---

#### **6. Historical Context & Patterns** ❌
**Manque :**
- Performance passée similaires situations
- Seasonal patterns (monthly, quarterly)
- Earnings patterns (beat/miss history)
- Reactions aux events similaires

**Impact sur LLM :**
- Pas de notion "historically, when X happens, stock does Y"
- Manque context temporel
- Pas de learning from past

**Solution :**
```python
# Historical pattern analysis
def get_historical_context(ticker):
    return {
        "similar_setups": [
            {
                "date": "2024-08-15",
                "condition": "RSI oversold + news positive",
                "outcome": "+12% 2 weeks",
                "confidence": 0.75,
            }
        ],
        "seasonal": {
            "best_month": "November",
            "worst_month": "September",
        },
        "earnings": {
            "beat_rate": 0.75,  # 75% earnings beats
            "avg_reaction": "+3.2%",  # Avg move post-earnings
        },
    }
```

---

### **MEDIUM GAPS (Priorité Moyenne)** ⚠️

#### **7. Risk Metrics** ❌
**Manque :**
- VaR (Value at Risk)
- Max drawdown historique
- Beta vs multiple indices
- Sharpe ratio
- Volatility compared to sector

**Solution :**
```python
features["risk_metrics"] = {
    "var_95": risk.var_95_pct,  # 95% VaR
    "max_drawdown_3m": risk.max_dd_3m,
    "beta_spy": risk.beta_spy,
    "beta_sector": risk.beta_sector,
    "sharpe_ratio": risk.sharpe_ratio,
    "vol_vs_sector": risk.volatility_vs_sector_pct,
}
```

---

#### **8. Earnings & Events Calendar** ❌
**Manque :**
- Prochains earnings date
- Dividends ex-date
- Splits upcoming
- Events corporates

**Impact :**
LLM ne sait pas si earnings imminent (important pour timing)

**Solution :**
```python
from agents.earnings_calendar_agent import get_upcoming_events

events = get_upcoming_events(ticker)

payload["upcoming_events"] = {
    "next_earnings": events.next_earnings_date,
    "days_to_earnings": events.days_to_earnings,
    "dividends": events.next_dividend,
    "events": [e.name for e in events.corporate_events],
}
```

---

#### **9. Backtest Results** ❌
**Manque :**
- Performance des stratégies similaires
- Win rate des signaux similaires
- Risk/reward ratio historique

**Solution :**
```python
from analytics.backtest_news_impact import backtest_similar_signals

backtest = backtest_similar_signals(ticker, current_signal)

payload["backtest"] = {
    "win_rate": backtest.win_rate,
    "avg_return": backtest.avg_return,
    "max_drawdown": backtest.max_drawdown,
    "sharpe": backtest.sharpe_ratio,
}
```

---

### **LOW PRIORITY GAPS** ℹ️

- Insider transactions
- Short interest
- Dark pool activity
- Order flow imbalance

---

## 🎯 REALISTIC DATA ENRICHMENT PLAN (LIVE-ONLY)

### **PHASE 1 : Minimal Enrichment - Live Data Only (6h)** 🔥

**Contraintes Codex :**
- ✅ Live-only (yfinance, prix real-time)
- ✅ Pas de cache risqué
- ✅ Fraîcheur vérifiée ou refus
- ✅ JSON strict, validation Pydantic
- ✅ Erreurs explicites

**Objectif :** Ajouter 40% de valeur avec données live garanties

---

#### **Task 1.1 : Fusion Score (Phase 5)** [2h]

**Source :** Calcul local depuis phases existantes

**Implémentation :**
```python
# judge_pipeline.py or judge.py
def compute_fusion_score(phases: Dict) -> Dict:
    """
    Compute fusion score from existing phase scores.
    NO external call, NO cache - pure calculation.
    """
    scores = []
    weights = {
        "fundamental": 0.30,
        "technical": 0.25,
        "macro": 0.25,
        "sentiment": 0.20,
    }
    
    phase_values = {}
    for phase_name, weight in weights.items():
        phase_data = phases.get(phase_name, {})
        score = phase_data.get("score")
        
        if score is not None and isinstance(score, (int, float)):
            scores.append((score, weight))
            phase_values[phase_name] = score
        else:
            logger.warning("fusion_missing_phase", phase=phase_name)
    
    if not scores:
        return {"error": "no_phase_scores_available"}
    
    # Weighted average
    composite = sum(s * w for s, w in scores) / sum(w for _, w in scores)
    
    # Conviction: based on std dev
    if len(scores) >= 2:
        vals = [s for s, _ in scores]
        std = np.std(vals)
        conviction = "high" if std < 0.15 else "medium" if std < 0.25 else "low"
        agreement_pct = (1 - std) * 100  # Simple heuristic
    else:
        conviction = "low"
        agreement_pct = 0
    
    # Dominant phase
    dominant = max(phase_values.items(), key=lambda x: x[1])[0] if phase_values else None
    
    return {
        "score": round(composite, 3),
        "conviction": conviction,
        "dominant_signal": dominant,
        "agreement_pct": round(agreement_pct, 1),
        "phase_count": len(scores),
    }

# Usage in build_payload()
if phases:
    fusion = compute_fusion_score(phases)
    enriched_features["fusion"] = fusion
```

**Test :**
```python
def test_fusion_score():
    phases = {
        "fundamental": {"score": 0.7},
        "technical": {"score": 0.6},
        "macro": {"score": 0.65},
        "sentiment": {"score": 0.5},
    }
    
    fusion = compute_fusion_score(phases)
    
    assert 0 <= fusion["score"] <= 1
    assert fusion["conviction"] in ["low", "medium", "high"]
    assert fusion["dominant_signal"] == "fundamental"  # Highest score
```

**Gains :**
- ✅ Single conviction metric for LLM
- ✅ No external calls (latency 0ms)
- ✅ 100% reliable (pure calculation)

---

#### **Task 1.2 : Tech Enrichment Minimal** [2h]

**Source :** `judge_features.json` (already computed) OR live calculation if fresh

**Implémentation :**
```python
def get_tech_enriched(ticker: str, judge_features: Dict) -> Dict:
    """
    Get enriched technical data from judge_features if available,
    otherwise calculate live from prices.
    
    FAIL if data stale or missing (no silent fallback).
    """
    # Check if judge_features has this ticker
    ticker_features = judge_features.get("tickers", {}).get(ticker, {})
    
    if ticker_features:
        # Check freshness
        computed_at = judge_features.get("computed_at")
        if computed_at:
            age_hours = calculate_age_hours(computed_at)
            if age_hours > 24:
                raise ValueError(f"judge_features too stale: {age_hours:.1f}h > 24h")
        
        # Use pre-computed
        tech = ticker_features.get("tech", {})
        if not tech:
            raise ValueError(f"No tech features for {ticker} in judge_features")
        
        return {
            "source": "judge_features",
            "rsi": tech.get("rsi"),
            "macd": tech.get("macd"),  # If available
            "bollinger": tech.get("bollinger"),  # If available
            "sma20": tech.get("sma20"),
            "sma50": tech.get("sma50"),
        }
    
    # Fallback: calculate live
    logger.info("tech_calculate_live", ticker=ticker)
    
    prices = load_prices_live(ticker)  # yfinance
    if not prices or len(prices) < 50:
        raise ValueError(f"Insufficient price data for {ticker}")
    
    tech_live = {
        "source": "live_calculation",
        "rsi": calculate_rsi(prices, 14),
        "sma20": calculate_sma(prices, 20),
        "sma50": calculate_sma(prices, 50),
        # MACD/Bollinger optional (add if quick to compute)
    }
    
    return tech_live
```

**Codex constraints respected:**
- ✅ Check freshness of judge_features
- ✅ FAIL if stale (raise ValueError)
- ✅ Live fallback if features unavailable
- ✅ No silent fallback

**Gains :**
- ✅ Richer technical context
- ✅ Guaranteed fresh data
- +30ms latency (live calc) OR 0ms (features)

---

#### **Task 1.3 : Fundamental Minimal** [2h]

**Source :** yfinance live (simple ratios only)

**Implémentation :**
```python
def get_fundamental_minimal(ticker: str) -> Dict:
    """
    Get minimal fundamental data from yfinance LIVE.
    
    Keep it simple:
    - P/E ratio
    - Market cap
    - Basic margins
    - NO DCF (too complex/slow)
    """
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        info = stock.info  # Live call
        
        # Extract simple metrics
        fund = {
            "source": "yfinance_live",
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "market_cap": info.get("marketCap"),
            "revenue": info.get("totalRevenue"),
            "profit_margin": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
        }
        
        # Simple "cheap/expensive" indicator
        pe = fund.get("pe_ratio")
        if pe:
            if pe < 15:
                fund["valuation_signal"] = "cheap"
            elif pe < 25:
                fund["valuation_signal"] = "fair"
            else:
                fund["valuation_signal"] = "expensive"
        
        return fund
        
    except Exception as e:
        # Explicit error, no fallback
        return {
            "error": f"yfinance_failed: {str(e)}",
            "source": "yfinance_live",
        }
```

**Why minimal?**
- ✅ Fast (<500ms per ticker)
- ✅ Live guaranteed
- ✅ Simple to validate
- ❌ NOT full DCF/peer analysis (too slow/complex for Phase 1)

**Gains :**
- ✅ Valuation context (cheap/expensive)
- ✅ Health ratios (ROE, margins)
- +500ms latency per ticker

---

### **PHASE 1 SUMMARY**

| Enrichment | Source | Latency | Reliability | Value Add |
|------------|--------|---------|-------------|-----------|
| Fusion Score | Calculation | 0ms | 100% | HIGH |
| Tech (from features) | judge_features.json | 0ms | 95% (if fresh) | MEDIUM |
| Tech (live calc) | yfinance prices | 30ms | 90% | MEDIUM |
| Fundamental minimal | yfinance live | 500ms | 85% | MEDIUM-HIGH |
| **TOTAL** | | **530ms** | | **HIGH** |

**Total enrichment time :** 6h implementation + 2h testing = **8h**

**Expected improvement :**
- Data completeness: 40% → 65% (+62%)
- LLM confidence: 0.65 → 0.75 (+15%)
- "Data needed" complaints: 40% → 20% (-50%)

---

### **PHASE 2 : Progressive Addition (After Phase 1 Stable)** ⚠️

**Conditions to start Phase 2:**
- ✅ Phase 1 deployed and stable (1 week)
- ✅ JSON parse success >99%
- ✅ Latency acceptable (<5s P95)
- ✅ No increase in errors

**Additions (1 at a time, tested individually):**

1. **Market Context Minimal** (2h)
   - Sector vs SPY performance (calculated from live prices)
   - Stock vs sector correlation
   - Source: yfinance live, simple calculations

2. **Analyst Ratings** (2h)
   - Target price consensus
   - Rating (buy/hold/sell)
   - Source: yfinance `info.recommendationKey`

3. **Earnings Proximity** (1h)
   - Days to next earnings
   - Source: yfinance `calendar`

**Each addition :**
- Test individually
- Measure latency impact
- Validate JSON parse still >99%
- Rollback if issues

---

### **PHASE 3 : Advanced (Future)** ℹ️

**Only if:**
- Phase 2 successful
- Strong business case
- Resources available

Potential additions:
- Full sentiment (social, institutional)
- Risk metrics (VaR, Sharpe)
- Historical patterns
- Backtest results

---

## ✅ UPDATED IMPLEMENTATION CHECKLIST

### **Week 1 : Phase 1 Implementation**

- [ ] **Codex:** Implement `compute_fusion_score()` in judge_pipeline.py
- [ ] **Codex:** Implement `get_tech_enriched()` with freshness check
- [ ] **Codex:** Implement `get_fundamental_minimal()` with yfinance live
- [ ] **Claude:** Unit tests for all 3 functions
- [ ] **Both:** Integration test with 1 ticker
- [ ] **Both:** Test with 10 tickers, measure latency
- [ ] **Both:** Deploy to test environment
- [ ] **Both:** Monitor for 1 week

### **Week 2 : Validation & Measurement**

- [ ] Compare LLM output quality (before/after enrichment)
- [ ] Measure confidence score improvement
- [ ] Check "data_needed" reduction
- [ ] Validate JSON parse still >99%
- [ ] Document findings

### **Week 3 : Phase 2 Decision**

- [ ] Review Phase 1 metrics
- [ ] Decide if Phase 2 warranted
- [ ] If yes, plan Phase 2 rollout (1 feature at a time)

---

**Ready to start? Codex can begin Phase 1 Task 1.1 (Fusion Score), Claude can prepare tests.**

---

## 🤝 ALIGNEMENT CLAUDE + CODEX (live-only, no-cache)

### Règles communes
- Pas de cache risqué ni de snapshot silencieux : données live-only ou refus explicite si stale/absent.
- Pas de micro-modules : rester sur des modules structurés existants, payload LLM concis (news top5, summaries 100c).
- JSON final obligatoire (dernière ligne), validation Pydantic stricte, erreurs explicites (pas de valeurs inventées).
- ML prior live-only ; si fail, champ `error` (jamais de fallback caché).

### Phase 1 (réaliste, live-only)
- Ajouter fusion_score (phase5) calculé à partir des scores phases déjà présents (poids simples) dans le pipeline existant (pas de cache).
- Tech enrichi minimal (MACD, Bollinger, key levels) depuis prix live (ou judge_features frais) ; refuser si data manquante/stale.
- Fondamentaux enrichis minimal via yfinance live (fair value simplifiée, ratios santé) ; si échec, indiquer `data_needed`.
- Conserver news lean (top5, summary 100c, age_hours), prompt JSON strict.
- Tests réels uniquement (scripts/test_judge_llm.py, curl /api/judge).

### Phase 2 (après stabilité JSON/latence)
- Sentiment élargi (analystes, institutional trend) si data live dispo et testée.
- Market context léger (sector vs SPY, corrélation SPY) calculé live si coût OK.

### Phase 3 (plus tard)
- Ensemble ML ou signaux avancés seulement après parse >99% et validation latence/coût.
- Tech snapshot éventuel avec vérif de fraîcheur stricte (fail si >24h), sinon live-only.

### Journal / Coordination
- Claude : vision enrichie (sentiment multi-source, market context, fusion avancée).
- Codex : implé live-only minimal (fusion_score, tech/fund basiques), sans cache, avec validation stricte.
- Toute nouvelle source doit être testée en réel et respecter le JSON strict, sans fallback silencieux.
