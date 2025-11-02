# État du Projet & Priorités

**Date:** 2 novembre 2025  
**Projet:** App Finance Prévisions (Copilote Financier)

---

## 📊 État Actuel

### ✅ Modules Implémentés
- **Core (données)**
  - `core/market_data.py` : FRED, yfinance OK
  - `core/config.py` : Configuration centralisée
  - `core/cache.py` : Cache TTL basique
  - `core/io_utils.py` : Lecture/écriture parquet/jsonl

- **Ingestion**
  - `ingestion/finnews.py` : Pipeline RSS robuste + dédup + scoring
  - `ingestion/bronze_pipeline.py` : Ingestion brute
  - `ingestion/gold_features_pipeline.py` : Features enrichies

- **Research**
  - `research/scoring.py` : Scoring macro/tech/news (fonctions individuelles OK)
  - `research/rag_store.py` : RAG basique (JSONL + tri date/score)
  - `research/nlp_enrich.py` : Sentiment, entités, résumés
  - `research/brief_renderer.py` : Rendu HTML/MD

- **API**
  - `api/main.py` : FastAPI avec routes principales
  - Routes OK: `/api/macro/series`, `/api/stocks/fundamentals`, `/api/news/feed`
  
- **Frontend**
  - React/Vite avec TypeScript
  - Types définis : macro, stocks, news, brief, copilot
  - Layout de base

---

## 🚨 Gaps Critiques (Bloquants MVP)

### 1. **Module `core/data_access.py` MANQUANT** 🔴
**Impact:** Bloque tout le scoring composite

**Fonctions attendues par `scoring.py`:**
```python
def get_close_series(ticker: str) -> pd.Series
def load_macro_forecast_rows(limit: int) -> Dict[str, Any]
def load_news_features(limit: int) -> Dict[str, Any]
```

**Solution:** Adapter simple qui wrappe les modules existants (1-3h)

---

### 2. **`compute_composite_brief()` ABSENT** 🔴
**Impact:** Route `/api/brief` cassée

**Attendu dans `research/scoring.py`:**
```python
def compute_composite_brief(period: str, universe: List[str]) -> Dict:
    # Appeler calculate_composite_score pour chaque ticker
    # Agréger top 3 signals + top 3 risks
    # Retourner picks (tickers > seuil)
```

**Solution:** Implémenter fonction (~1/2 journée)

---

### 3. **RAG Non Ensemencé** 🔴
**Impact:** Q&A LLM sans contexte (inutilisable)

**Manque:**
- 5 ans de séries macro (CPIAUCSL, UNRATE, T10Y2Y, VIX...)
- 5 ans de prix actions (échantillonnés)
- Injection auto des news quotidiennes

**Solution:** Endpoint `/api/rag/seed` + job initial (~1/2 journée)

---

### 4. **LLM Non Branché** 🟡
**Impact:** Route `/api/copilot/ask` retourne placeholder

**Manque:**
- Client LLM (OpenAI-compatible)
- Prompt engineering avec RAG context
- Gestion citations + fallback

**Solution:** Client minimal + prompt simple (~1/2 journée)

---

### 5. **Routes API Incomplètes** 🟡

| Route | Statut | Problème |
|-------|--------|----------|
| `/api/stocks/prices` | ⚠️ | Ignore param `range`, dépend de `analytics.phase2_technical` non vérifié |
| `/api/macro/bundle` | ⚠️ | Dépend de `analytics.phase3_macro` absent |
| `/api/brief` | 🔴 | Bloqué par `compute_composite_brief` |
| `/api/copilot/ask` | 🔴 | LLM non intégré |
| `/api/dashboard/kpis` | 🟡 | Placeholders uniquement |
| `/api/forecasts` | 🟡 | Stub vide |

---

## 🎯 Priorités (Ordre d'Exécution)

### **P0 - Déblocage MVP (1.5-2.5 jours)** 🔥

#### 1️⃣ **Adapter `core/data_access.py`** (1-3h)
```python
# Objectif: Unifier accès données pour scoring
def get_close_series(ticker: str) -> pd.Series:
    df = get_price_history(ticker, interval="1d")
    return df["Close"].dropna()

def load_macro_forecast_rows(limit=1) -> Dict:
    # Calculer inflation_yoy, yield_curve_slope, unemployment
    # depuis get_fred_series ou get_us_macro_bundle
    
def load_news_features(limit=100) -> Dict:
    items = run_news_pipeline(window="last_week", limit=limit)
    # Mapper vers {symbol, news_score_mean, hours_since_publish}
```

**Critère succès:** `research/scoring.py` s'exécute sans erreur import

---

#### 2️⃣ **Implémenter `compute_composite_brief()`** (1/2 jour)
```python
def compute_composite_brief(period: str, universe: List[str]) -> Dict:
    scores = [calculate_composite_score(t) for t in universe]
    top_signals, top_risks = get_top_signals_and_risks(universe, top_n=3)
    picks = [s for s in scores if s["composite_score"] >= 65]
    
    return {
        "top_signals": top_signals,
        "top_risks": top_risks,
        "picks": picks[:5],
        "sources": [...],
        "generated_at": datetime.utcnow().isoformat()
    }
```

**Critère succès:** `/api/brief` retourne JSON valide avec top 3 + risks

---

#### 3️⃣ **Ensemencer RAG (5 ans)** (1/2 jour)
**Tâches:**
- Endpoint `/api/rag/seed` ou `startup_event`
- Macro: 5-10 séries clés × 5 ans (échantillon mensuel)
- Prix: univers base (SPY, QQQ, AAPL...) × 5 ans (hebdo)
- News: top-N quotidien auto (score > seuil)

**Critère succès:** `rag_store.stats()` > 5000 chunks

---

#### 4️⃣ **Client LLM Minimal** (1/2 jour)
```python
# research/llm_client.py
def ask_llm(question: str, context_chunks: List[Dict]) -> Dict:
    prompt = build_prompt(question, context_chunks)
    response = openai_call(prompt)
    return {
        "answer": response,
        "citations": extract_citations(context_chunks)
    }
```

**Critère succès:** `/api/copilot/ask` retourne réponse + ≥2 citations

---

#### 5️⃣ **Durcir Routes API** (2-6h)
- `/api/stocks/prices`: respecter `range`, gérer erreurs
- `/api/macro/bundle`: bundle minimal si `phase3_macro` absent
- `/api/dashboard/kpis`: calculs réels (timestamps, counts)
- `/health`: tests effectifs FRED/yfinance/news

**Critère succès:** Toutes routes 2xx avec données cohérentes

---

### **P1 - Qualité & UX (1-2 jours)** 📈

#### 6️⃣ **Frontend - Intégration API**
- Connexion vraies routes API
- Affichage Market Brief
- Widget Copilot Q&A
- Charts macro/prix

#### 7️⃣ **Tests End-to-End**
- Smoke tests API complète
- Validation scoring 40/40/20
- Test RAG search performance

#### 8️⃣ **Cache & Performance**
- Cache disque FRED/yfinance (TTL 1h-1j)
- Optimisation queries DuckDB
- Compression parquet

---

### **P2 - V1 Features (backlog)**
- Dashboard filtres secteur/horizon
- Alertes (SMA/RSI/sentiment)
- Notes versionnées
- Export PDF Brief

---

## 📋 Checklist MVP "Go-Live"

- [ ] `/api/brief` → top_signals/risks cohérents + sources traçables
- [ ] `/api/copilot/ask` → réponse + ≥2 citations
- [ ] RAG stats → ≥5000 facts (macro+prix+news)
- [ ] Scoring composite → 40/40/20 calculé sans erreur
- [ ] Frontend → affiche brief + permet Q&A
- [ ] Tests smoke → tous endpoints 2xx
- [ ] Documentation → AGENTS.md + API docs à jour

---

## 🚀 Roadmap Semaine

| Jour | Tâche | Effort | Responsable |
|------|-------|--------|-------------|
| J1 | Adapter `data_access.py` | 3h | - |
| J1-J2 | `compute_composite_brief()` | 4h | - |
| J2 | Ensemencement RAG | 4h | - |
| J2-J3 | Client LLM minimal | 4h | - |
| J3 | Durcir routes API | 4h | - |
| J3-J4 | Tests + ajustements | 4h | - |

**Total:** ~23h → **~3 jours** pour MVP fonctionnel

---

## ⚠️ Risques & Mitigation

| Risque | Impact | Mitigation |
|--------|--------|------------|
| `analytics.phase2_technical` absent | 🔴 | Implémenter `compute_indicators()` ou stub |
| `analytics.phase3_macro` absent | 🟡 | Bundle minimal direct depuis FRED |
| Volume RAG trop grand | 🟡 | Échantillonner (mensuel/hebdo), limiter 5 ans |
| Coûts LLM | 🟡 | Timeout + cache réponses + fallback heuristique |
| News dédup cassée | 🟡 | Tests pipeline `finnews.py` |

---

## 📝 Notes Techniques

### Modules à Créer
1. `src/core/data_access.py` (adapter)
2. `src/research/llm_client.py` (client LLM)
3. `src/analytics/phase2_technical.py` (si absent)
4. `src/analytics/phase3_macro.py` (si absent)

### Modules à Modifier
1. `src/research/scoring.py` (+compute_composite_brief)
2. `api/main.py` (corriger routes, imports)
3. `src/research/rag_store.py` (+méthode seed)

---

## 🎯 Objectif Final MVP

**Un copilote financier fonctionnel qui:**
1. Génère un Market Brief hebdo avec Top 3 signaux/risques
2. Répond aux questions utilisateur avec citations (RAG 5 ans)
3. Agrège macro (FRED) + actions (yfinance) + news (RSS)
4. Score composite 40/40/20 traçable
5. Interface React utilisable

**KPI MVP:**
- Brief généré en < 30s
- Q&A répond en < 10s avec ≥2 sources
- 90% tickers couverts (SPY, QQQ, AAPL, NVDA, MSFT...)
- News fraîcheur médiane < 30min
