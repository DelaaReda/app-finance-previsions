# 🗺️ Plan d'Intégration Front ↔ API ↔ Modules Python

## Date: 30 Octobre 2025
## Status: Phase 2 - Intégration complète

---

## 🎯 Vision d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                   React Frontend (UI)                       │
│         (Services & Hooks - Présentation & État)            │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP/JSON
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (/api/*)                       │
│     (Routes + Service Facades + Scoring Composite)          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Modules Python Existants                       │
│  ┌───────────┬────────────┬──────────┬──────────────────┐  │
│  │ core/     │ analytics/ │ ingestion│ research/        │  │
│  │ market_   │ phase2_    │ finnews  │ rag_store        │  │
│  │ data      │ technical  │          │ nlp_enrich       │  │
│  │           │ phase3_    │          │ brief_renderer   │  │
│  │           │ macro      │          │                  │  │
│  └───────────┴────────────┴──────────┴──────────────────┘  │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                │
│  Parquet Features + DuckDB + Cache + RAG Store              │
└─────────────────────────────────────────────────────────────┘
```

**Principes:**
- ✅ Front = Présentation & État uniquement
- ✅ Backend = Tous les calculs (indicateurs, scoring, RAG)
- ✅ Performance = TTL cache (5-15 min) + LTTB + GZip + ETag
- ✅ Traçabilité = source + timestamp + citations

---

## 📋 Pages & Intégration Détaillée

### ✅ 1. Dashboard (Synthèse actionable)

**Contenu:**
- Top 3 **Signaux** (volatilité, inflation, etc.) + raison + jauge
- Top 3 **Risques** + raison
- 3 **Picks** avec score composite (40% macro + 40% tech + 20% news)
- **Heatmap** univers (variation 1D/1W) + RSI/SMA20 au survol
- **Alerts** (badges: RSI>70, below SMA20, news spike)
- **Macro highlights** (2-3 tuiles: CPI YoY, VIX, 10Y-2Y)

**API:**
```typescript
GET /api/brief?period=weekly&universe=SPY,QQQ,AAPL
→ { 
    brief: { topSignals, topRisks, picks },
    generatedAt: "2025-10-30T14:00:00Z",
    sources: { macro, technical, news }
}

GET /api/alerts?universe=AAPL,NVDA (optionnel)
```

**Backend:**
```python
# api/services/scoring_service.py
def build_brief(period, universe):
    # Compose 40% macro + 40% tech + 20% news
    # Utilise phase3_macro, phase2_technical, finnews
    ...
```

**Acceptance:**
- ✅ Affiche ≥3 signaux/risques avec sources
- ✅ 3 picks avec score composite
- ✅ Refresh < 2s (cache)
- ✅ Clic pick → TickerSheet

---

### ✅ 2. Macro (Exploration FRED)

**Contenu:**
- Sélecteur séries (CPIAUCSL, VIXCLS, DGS10, UNRATE, etc.)
- Chart multi-séries avec période (1Y/5Y/MAX)
- **YoY toggle** pour inflation
- Lissage + export PNG
- **Regime/Nowcast** (si phase3 dispo)
- Table dernières valeurs + **source FRED**

**API:**
```typescript
GET /api/macro/series?ids=CPIAUCSL&ids=VIXCLS&start=2018-01-01
→ {
    series: [
        {
            id: "CPIAUCSL",
            points: [{t, v}, ...],
            source: "FRED",
            ts: "2025-10-30T14:00:00Z",
            url: "https://fred.stlouisfed.org/series/CPIAUCSL"
        }
    ]
}

GET /api/macro/snapshot
→ { CPIAUCSL: {last: 308.7, ts: "2025-10-01"}, ... }

GET /api/macro/regime (optionnel)
```

**Backend:**
```python
# Déjà implémenté dans macro_service.py
# get_macro_overview(), get_macro_snapshot(), get_macro_indicators()
```

**Acceptance:**
- ✅ Graphs avec source + timestamp
- ✅ YoY correct (base période)
- ✅ Export PNG ok
- ✅ Cache 1-6h

---

### ✅ 3. Stocks (Prix + Indicateurs)

**Contenu:**
- Input multi-tickers (AAPL, NVDA, MSFT)
- Chart OHLC + overlays (SMA20, RSI, MACD)
- Table KPIs (dernier RSI, distance SMA20, MACD sign)
- **Screener** (filtres RSI zones, MACD>0, distance SMA>0)

**API:**
```typescript
GET /api/stocks/prices?tickers=AAPL&tickers=NVDA&period=1y&interval=1d
→ {
    items: [
        {
            ticker: "AAPL",
            prices: [{t,o,h,l,c,v}, ...],  // downsampled LTTB
            indicators: {rsi: 65.2, sma20: 185.3, macd: 2.1}
        }
    ]
}

GET /api/stocks/screener?filters=... (optionnel)
```

**Backend:**
```python
# Déjà implémenté dans stocks_service.py
# get_stock_overview() avec LTTB downsampling
```

**Acceptance:**
- ✅ SMA/RSI/MACD calculés serveur
- ✅ KPI cohérents
- ✅ Délai < 2s/call (cache 10-15 min)
- ✅ Clic ticker → TickerSheet

---

### ✅ 4. News (Flux RSS scoré)

**Contenu:**
- Filtres: tickers, texte, période (24h/7j/30j), tier source
- Liste triée par **score** (fraîcheur + crédibilité + pertinence)
- Sentiment/tags
- Bouton **📌 Pin** pour indexer dans RAG

**API:**
```typescript
GET /api/news/feed?tickers=AAPL&limit=50&q=earnings
→ {
    items: [
        {
            id: "abc123",
            title: "Apple reports Q4 earnings...",
            url: "https://...",
            source: "Reuters",
            published: "2025-10-30T10:00:00Z",
            score: 0.85,
            tickers: ["AAPL"]
        }
    ]
}

POST /api/news/save (pour pin)
```

**Backend:**
```python
# Déjà implémenté dans news_service.py
# get_news_feed() utilise finnews.run_pipeline()
```

**Acceptance:**
- ✅ Tri par score visuel
- ✅ Bouton Pin active
- ✅ Liens ouverts
- ✅ TTL 2-5 min

---

### 🔄 5. TickerSheet (Fiche complète)

**Contenu:**
- Header: ticker, secteur, KPIs (Close, RSI, SMA20)
- Chart OHLC + overlays
- Key levels: SMA20, variation 1W/1M, pivots
- Top 5 news + scores
- **Alerts** (rsi_overbought, trend_down, news_spike)
- **CTA**: "Demander au Copilote" (pre-filled)

**API:**
```typescript
GET /api/tickers/{ticker}/sheet?period=6mo&interval=1d
→ {
    overview: {ticker, sector},
    prices: [{t,o,h,l,c,v}, ...],
    indicators: {rsi, sma20, macd},
    newsTop: [NewsItem, ...],
    levels: {sma20, variation_1w, variation_1m}
}
```

**Backend:**
```python
# TODO: Créer endpoint composite
# api/routes/tickers.py
def get_ticker_sheet(ticker, period, interval):
    # Compose prices + indicators + top 5 news + levels
    ...
```

**Acceptance:**
- ✅ Tous champs présents
- ✅ Liens news
- ✅ CTA pre-rempli → Copilot

---

### 🔄 6. MarketBrief (Rapport éditorialisé)

**Contenu:**
- Top Signals/Risks/Picks avec **citations**
- Section Macro (2-3 bullets contextualisés)
- Section Thématiques (si keywords news détectés)
- **Export HTML/Markdown**

**API:**
```typescript
GET /api/brief?period=weekly&universe=SPY,QQQ
→ BriefResponse (déjà implémenté)

GET /api/brief/export?fmt=html|md (TODO)
```

**Backend:**
```python
# TODO: Créer endpoint export
# Utiliser research/brief_renderer si dispo
```

**Acceptance:**
- ✅ Rapport lisible
- ✅ Citations présentes
- ✅ Export renvoie doc utilisable

---

### 🔄 7. Backtests (Validation stratégies)

**Contenu:**
- Config: univers, période, règle (RSI>70, SMA cross)
- Résultats: equity curve, drawdown, stats (CAGR, Sharpe, MaxDD)
- Table trades
- Comparaison benchmark (SPY)

**API:**
```typescript
POST /api/backtests/run
{
    universe: ["AAPL", "NVDA"],
    period: "2y",
    rules: {
        long_when: ["EMA12>EMA26", "RSI<30"],
        flat_when: ["RSI>70"]
    },
    fees_bps: 1.0
}
→ {
    equity_curve: [...],
    trades: [...],
    summary: {cagr, sharpe, maxdd}
}
```

**Backend:**
```python
# TODO: Créer endpoint
# Utilise analytics/phase2_technical.backtest()
```

**Acceptance:**
- ✅ Retour complet et cohérent
- ✅ Charts lisibles
- ✅ Export CSV trades

---

### 🔄 8. Forecasts (Prévisions si calculées)

**Contenu:**
- Cartes par ticker: prochaine fenêtre (1W/1M)
- Intervalle confiance
- Métriques erreur historiques
- **Avertissement** (pas de conseil financier)

**API:**
```typescript
GET /api/forecasts?tickers=AAPL,NVDA
→ {
    forecasts: [
        {
            ticker: "AAPL",
            horizon: "1W",
            prediction: 185.5,
            confidence_interval: [180, 190],
            historical_mae: 2.3
        }
    ]
}
```

**Backend:**
```python
# TODO: Si forecaster dispo
# Sinon: message "pas de forecast"
```

**Acceptance:**
- ✅ Affiche si dispo
- ✅ Sinon message clair

---

### 🔄 9. Copilot (LLM + RAG)

**Contenu:**
- Chat (question → réponse avec citations)
- Scope: tickers, horizon, thèmes
- Historique session

**API:**
```typescript
POST /api/copilot/ask
{
    question: "Quels sont les risques d'inflation pour AAPL?",
    scope: {tickers: ["AAPL"], years: 5}
}
→ {
    answer: "Basé sur les données...",
    citations: [
        {type: "news", ref: "article123", url: "...", t: "2025-10-15"},
        {type: "series", ref: "CPIAUCSL", url: "..."}
    ]
}
```

**Backend:**
```python
# TODO: Implémenter RAG complet
# Utiliser research/rag_store + nlp_enrich
```

**Acceptance:**
- ✅ Chaque réponse ≥2 citations
- ✅ Liens cliquables
- ✅ Pas d'hallucinations flagrantes

---

### 🔄 10. LLMJudge (Évaluation qualité)

**Contenu:**
- Prompt d'évaluation prédéfini
- Score + feedback (forces/faiblesses)
- Export JSON

**API:**
```typescript
POST /api/llm-judge/evaluate
{
    question: "...",
    answer: "...",
    citations: [...]
}
→ {
    score: 0.85,
    feedback: {precision, sources, coherence},
    export_json: {...}
}
```

**Backend:**
```python
# TODO: Prompt judge + scoring
```

**Acceptance:**
- ✅ Score numérique + justification
- ✅ Export JSON ok

---

## 🔧 État d'Implémentation

### ✅ Fait (v0.1)

| Endpoint | Status | Service |
|----------|--------|---------|
| `GET /api/health` | ✅ | - |
| `GET /api/freshness` | ✅ | - |
| `GET /api/macro/overview` | ✅ | macro_service |
| `GET /api/macro/snapshot` | ✅ | macro_service |
| `GET /api/macro/indicators` | ✅ | macro_service |
| `GET /api/stocks/{ticker}/overview` | ✅ | stocks_service |
| `GET /api/stocks/universe` | ✅ | stocks_service |
| `GET /api/news/feed` | ✅ | news_service |
| `GET /api/news/sentiment` | ✅ | news_service |

### 🔄 En cours (v0.2)

| Endpoint | Priorité | Composants |
|----------|----------|------------|
| `GET /api/brief` | 🔴 Critique | scoring_service (40/40/20) |
| `GET /api/tickers/{ticker}/sheet` | 🔴 Critique | Composite |
| `GET /api/signals/top` | 🔴 Critique | scoring_service |
| `GET /api/stocks/prices` | 🟡 Haute | Adapter stocks_service |

### ⏳ TODO (v0.3+)

| Endpoint | Priorité | Dépendances |
|----------|----------|-------------|
| `POST /api/copilot/ask` | 🟡 Haute | RAG store + nlp_enrich |
| `GET /api/brief/export` | 🟢 Moyenne | brief_renderer |
| `POST /api/backtests/run` | 🟢 Moyenne | phase2_technical |
| `GET /api/forecasts` | 🟢 Basse | forecaster |
| `POST /api/llm-judge/evaluate` | 🟢 Basse | Judge prompt |
| `POST /api/news/save` | 🟢 Basse | RAG store |
| `GET /api/alerts` | 🟢 Basse | Alert engine |

---

## 🎯 Prochaines Étapes Immédiates

### 1. Implémenter Scoring Composite 🔴

**Fichier:** `src/api/services/scoring_service.py`

```python
def compute_composite_score(ticker: str) -> CompositeScore:
    """
    Calcule le score composite: 40% macro + 40% tech + 20% news
    """
    # Macro score (phase3_macro)
    macro_score = get_macro_contribution(ticker)  # 0-1
    
    # Technical score (phase2_technical)
    tech_score = get_technical_contribution(ticker)  # 0-1
    
    # News score (finnews)
    news_score = get_news_contribution(ticker)  # 0-1
    
    total = macro_score * 0.4 + tech_score * 0.4 + news_score * 0.2
    
    return CompositeScore(
        total=total,
        macro=macro_score,
        technical=tech_score,
        news=news_score
    )
```

### 2. Endpoint `/api/brief` complet

**Intégration:**
- Top 3 signaux (score > 0.7)
- Top 3 risques (score < 0.3)
- 3 picks avec rationale
- Citations (sources macro/tech/news)

### 3. Endpoint `/api/tickers/{ticker}/sheet`

**Composition:**
- Prix + indicateurs (déjà OK)
- Top 5 news (déjà OK)
- Levels calculés
- Alerts générés

---

## 📚 Documentation à Créer

1. **OpenAPI spec complet** (`docs/openapi-v0.2.yaml`)
2. **Guide intégration front-end** (`docs/FRONTEND_INTEGRATION.md`)
3. **Contrats TypeScript** (générer depuis OpenAPI)
4. **Tests de contrat** (Schemathesis)

---

## ✅ Checklist Qualité

### Performance
- [ ] Cache Redis (TTL adaptatif)
- [ ] LTTB downsampling partout
- [ ] GZip + ETag sur routes lourdes
- [ ] Parquet features pour agrégats

### Traçabilité
- [x] TraceMetadata sur toutes réponses
- [ ] Citations dans brief/copilot
- [ ] Logs structurés (loguru)
- [ ] Event telemetry minimal

### Tests
- [x] Tests smoke (12 tests v0.1)
- [ ] Tests de contrat (OpenAPI)
- [ ] Tests d'intégration (modules Python)
- [ ] Tests E2E (Playwright)

### Documentation
- [x] README API v0.1
- [ ] OpenAPI spec v0.2
- [ ] Guide frontend
- [ ] Exemples cURL/Postman

---

**Status:** 📍 Phase 2 démarrée - Implémentation scoring composite  
**Prochaine milestone:** Endpoint `/api/brief` opérationnel avec 40/40/20
