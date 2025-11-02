# 🔍 Inspection Complète Triplex - App Finance Prévisions

**Inspecteur:** Analyse Automatisée Approfondie  
**Date:** 2 novembre 2025  
**Type:** Audit Complet Multi-Couches  
**Statut:** 🔴 Plusieurs gaps critiques identifiés

---

## 📋 Table des Matières

1. [Backend Python - Gaps Critiques](#backend-python)
2. [Frontend React - Gaps & Connexions Manquantes](#frontend-react)
3. [Configuration & Environment](#configuration)
4. [Tests & Qualité](#tests-qualité)
5. [Documentation Manquante](#documentation)
6. [Dépendances Circulaires & Imports Cassés](#dépendances)
7. [Performance & Optimisation](#performance)
8. [Sécurité & Production](#sécurité)
9. [Plan d'Action Complet](#plan-action)

---

## 🐍 Backend Python - Gaps Critiques

### 1. Module `core/data_access.py` ❌ MANQUANT COMPLET

**Status:** 🔴 **BLOQUANT**  
**Fichier:** `src/core/data_access.py`  
**Impact:** Bloque `research/scoring.py` entièrement

#### Imports Cassés Détectés
```python
# Dans research/scoring.py:20-22
from core.data_access import (
    get_close_series,           # ❌ MANQUANT
    load_macro_forecast_rows,   # ❌ MANQUANT
    load_news_features         # ❌ MANQUANT
)
```

#### Utilisations dans le Code
```python
# scoring.py:77 - score_technical()
close_series = get_close_series(ticker)  # ❌ CRASH

# scoring.py:50 - score_macro_conditions()
macro_data = load_macro_forecast_rows(limit=1)  # ❌ CRASH

# scoring.py:145 - score_news_sentiment()
news_data = load_news_features(limit=100)  # ❌ CRASH
```

**Conséquence:** `/api/brief` inutilisable, scoring impossible

---

### 2. Module `analytics/indicators_basic.py` ❌ RÉFÉRENCÉ MAIS ABSENT

**Status:** 🟡 **FALLBACK EXISTE**  
**Fichier:** `src/analytics/indicators_basic.py`  
**Impact:** Fallback dans `research/materialize.py`

#### Référence Trouvée
```python
# research/materialize.py:27
from analytics.indicators_basic import compute_indicators  # <— module fallback
```

**Note:** `analytics.phase2_technical.compute_indicators()` existe et est complet. Probablement un ancien nom/alias.

**Action Requise:**
- Option A: Créer symlink/alias `indicators_basic.py` → `phase2_technical.py`
- Option B: Corriger import dans `materialize.py`

---

### 3. Fonction `compute_composite_brief()` ❌ MANQUANTE

**Status:** 🔴 **BLOQUANT**  
**Fichier:** `src/research/scoring.py`  
**Impact:** Route `/api/brief` crash

#### Appel dans API
```python
# api/main.py:274
brief = compute_composite_brief(period=period, universe=universe)  # ❌ CRASH
```

#### Signature Attendue
```python
def compute_composite_brief(
    period: str,        # "daily" | "weekly"
    universe: List[str] # ["SPY", "QQQ", ...]
) -> Dict[str, Any]:
    """
    Returns:
        {
            "top_signals": List[Signal],
            "top_risks": List[Signal],
            "picks": List[Pick],
            "sources": List[Source],
            "generated_at": str,
            "period": str,
            "universe": List[str]
        }
    """
```

**Fonctions Disponibles (OK):**
- ✅ `calculate_composite_score(ticker)` - Existe
- ✅ `get_top_signals_and_risks(tickers, top_n)` - Existe

**Besoin:** Fonction wrapper qui agrège les deux ci-dessus

---

### 4. RAG Store - Pas de Pipeline d'Ensemencement

**Status:** 🟡 **INCOMPLET**  
**Fichier:** `src/research/rag_store.py`  
**Lignes:** 307 lignes (complet pour lecture/écriture)

#### Méthodes Existantes ✅
```python
class RAGStore:
    ✅ def add_news_item(item: Dict)
    ✅ def add_news_items(items: List[Dict])
    ✅ def add_series_fact(series_id, name, value, date)
    ✅ def add_series_facts(series_dict: Dict)
    ✅ def search(scope, top_k=10) -> List[Dict]
    ✅ def stats() -> Dict[str, int]
    ✅ def clear()
    ✅ def freshness_stats() -> Dict[str, float]  # Ligne 217
```

#### Gaps RAG
1. **❌ Pas d'endpoint `/api/rag/seed`** - Doit ensemencer initial
2. **❌ Pas de job quotidien** - Refresh news automatique
3. **❌ Pas de méthode `seed_historical()`** - 5 ans macro/prix
4. **⚠️ Recherche basique** - Tri par score/date uniquement (pas d'embeddings)

**Conséquence:** RAG vide par défaut, Q&A sans contexte

---

### 5. Client LLM Non Implémenté

**Status:** 🔴 **MANQUANT COMPLET**  
**Fichier:** `src/research/llm_client.py` ❌ N'EXISTE PAS

#### Appel dans API
```python
# api/main.py:401 (TODO commenté)
# TODO: Intégrer avec analytics/econ_llm_agent ou research/nlp_enrich
answer = f"Basé sur {len(context_chunks)} sources..."  # ❌ PLACEHOLDER
```

#### Module Potentiel Existant
```bash
src/analytics/econ_llm_agent.py  # ✅ EXISTE (137 lignes)
```

**Vérification Requise:** Est-ce que `econ_llm_agent` peut servir de client ?

---

### 6. Imports Inutilisés dans `api/main.py`

**Status:** 🟡 **CODE SMELL**  
**Fichier:** `api/main.py`

#### Imports Non Utilisés Détectés
```python
# Ligne 21
from ingestion.finnews import run_pipeline as run_news_pipeline, list_sources
#                                                                ^^^^^^^^^^^^ ❌ JAMAIS UTILISÉ

# Ligne 22
from analytics.phase2_technical import load_prices, compute_indicators, technical_signals
#                                      ^^^^^^^^^^^ ❌ JAMAIS UTILISÉ
#                                                                       ^^^^^^^^^^^^^^^^ ❌ JAMAIS UTILISÉ
```

**Impact:** Confus pour les développeurs, imports fantômes

---

### 7. Routes API Incomplètes/Placeholders

#### `/api/dashboard/kpis` - Placeholders
```python
# api/main.py:292-307
return {
    "ok": True,
    "data": {
        "last_forecast_dt": None,        # ❌ PLACEHOLDER
        "forecasts_count": 0,             # ❌ PLACEHOLDER
        "tickers": 0,                     # ❌ PLACEHOLDER
        "horizons": [],                   # ❌ PLACEHOLDER
        "last_macro_dt": None,            # ❌ PLACEHOLDER
        "last_quality_dt": None           # ❌ PLACEHOLDER
    }
}
```

**Besoin:** Calculs réels depuis RAG/data

---

#### `/api/forecasts` - Stub Vide
```python
# api/main.py:430-448
# TODO: Brancher sur analytics/forecaster.py ou lire parquet
return {
    "ok": True,
    "data": {
        "rows": [],              # ❌ STUB
        "count": 0,              # ❌ STUB
        "asset_type": asset_type
    }
}
```

**Module Disponible:** `src/analytics/forecaster.py` ✅ EXISTE  
**Action:** Connecter route au module

---

#### `/api/stocks/prices` - Param `range` Ignoré
```python
# api/main.py:140-183
def get_stock_prices(
    tickers: List[str] = Query(...),
    range: str = Query("1y", ...),      # ⚠️ PARAMÈTRE DÉCLARÉ
    interval: str = Query("1d", ...)
):
    # ...
    df = get_price_history(ticker, start=None, interval=interval)  # ❌ `range` IGNORÉ
```

**Besoin:** Mapper `range` → `start` date

---

### 8. Gestion d'Erreurs Faible

#### Pas de Classes d'Exception Personnalisées
```bash
# Recherche dans research/
grep "class.*Exception" src/research/*.py
# Résultats: Seulement dans web_navigator.py (4 classes)
```

#### Exceptions Utilisées
- ✅ `research/web_navigator.py`:
  - `RedirectError`
  - `NonJSONError`
  - `ForbiddenError`
  - `TooManyRequestsError`

- ❌ Autres modules: Utilisent `Exception` générique ou `RuntimeError`

**Besoin:**
```python
# src/core/exceptions.py - À CRÉER
class DataAccessError(Exception): ...
class ScoringError(Exception): ...
class RAGError(Exception): ...
class LLMError(Exception): ...
```

---

## ⚛️ Frontend React - Gaps & Connexions Manquantes

### 1. Hook `useBriefs` - Appel Incomplet

**Status:** 🟡 **IMPLÉMENTATION PARTIELLE**  
**Fichier:** `webapp/src/hooks/useBriefs.ts`

#### Service Brief Simplifié
```typescript
// webapp/src/services/brief.service.ts
export async function fetchBrief(
  period: 'daily' | 'weekly' = 'weekly',
  universe: string[] = ['SPY', 'QQQ']  // ❌ PARAMÈTRE DÉCLARÉ MAIS JAMAIS ENVOYÉ
): Promise<ApiResponse<BriefData>> {
  return apiGet<BriefData>(`/brief/${period}`)  // ❌ Manque query params ?universe=...
}
```

**Correction Requise:**
```typescript
export async function fetchBrief(
  period: 'daily' | 'weekly' = 'weekly',
  universe: string[] = ['SPY', 'QQQ']
): Promise<ApiResponse<BriefData>> {
  const params = {
    universe: universe.join(',')  // ✅ AJOUTER
  }
  return apiGet<BriefData>(`/brief/${period}`, params)
}
```

---

### 2. Service Copilot - Méthodes Manquantes

**Status:** 🟡 **INCOMPLET**  
**Fichier:** `webapp/src/services/copilot.service.ts`

#### Méthodes Implémentées
```typescript
export const copilotService = {
  ask: async (request) => { ... },      // ✅ OK
  getHistory: async (limit) => { ... }, // ✅ OK
  // ❌ MANQUANTS:
  // getRAGStats() - Appelé dans Copilot.tsx:21
  // createSession() - Appelé dans Copilot.tsx:29
}
```

#### Appels dans Page Copilot
```typescript
// webapp/src/pages/Copilot.tsx:18-24
const { data: ragStats } = useQuery({
  queryKey: ['rag-stats'],
  queryFn: async () => {
    const result = await copilotService.getRAGStats()  // ❌ MÉTHODE N'EXISTE PAS
    return result.ok ? result.data : null
  },
})

// Copilot.tsx:27-37
const createSession = useMutation({
  mutationFn: async () => {
    const result = await copilotService.createSession()  // ❌ MÉTHODE N'EXISTE PAS
    if (!result.ok) throw new Error(result.error)
    return result.data
  },
})
```

**Correction Requise:**
```typescript
// Ajouter dans copilot.service.ts
export const copilotService = {
  ask: ...,
  getHistory: ...,
  
  getRAGStats: async () => {
    return apiGet('/rag/stats')  // ✅ AJOUTER
  },
  
  createSession: async () => {
    return apiPost('/copilot/session', {})  // ✅ AJOUTER
  }
}
```

---

### 3. Page MarketBrief - Type Brief Incomplet

**Status:** 🟡 **TYPES MANQUANTS**  
**Fichier:** `webapp/src/pages/MarketBrief.tsx`

#### Propriétés Utilisées Mais Non Typées
```typescript
// MarketBrief.tsx:59-132
brief.title                  // ❌ Non dans type BriefData ?
brief.date                   // ❌ Non dans type BriefData ?
brief.executive_summary      // ❌ Non dans type BriefData ?
brief.macro_snapshot         // ❌ Non dans type BriefData ?
brief.market_snapshot        // ❌ Non dans type BriefData ?
brief.news_snapshot          // ❌ Non dans type BriefData ?
brief.key_takeaways          // ❌ Non dans type BriefData ?
brief.version                // ❌ Non dans type BriefData ?
```

**Vérification Type Actuel:**
```bash
# À vérifier dans:
webapp/src/types/brief.types.ts
webapp/src/types/brief.ts
```

---

### 4. Page Dashboard - Route `/dashboard/kpis` Non Alignée

**Status:** 🟡 **CONTRAT API DIFFÉRENT**  
**Fichier:** `webapp/src/pages/Dashboard.tsx`

#### Frontend Attend
```typescript
// Dashboard.tsx:14-40
type DashboardData = {
  kpis: { ... },
  top_signals: Signal[],       // ✅ OK si filtres vides
  top_risks: Signal[],          // ✅ OK si filtres vides
  market_overview?: { ... },    // ❌ Backend ne retourne pas
  filtered_signals?: Signal[],  // ❌ Backend ne retourne pas
  filtered_risks?: Signal[],    // ❌ Backend ne retourne pas
  filter_applied?: { ... },     // ❌ Backend ne retourne pas
  filtered_ticker_count?: int   // ❌ Backend ne retourne pas
}
```

#### Backend Retourne (api/main.py:292)
```python
{
    "ok": True,
    "data": {
        "last_forecast_dt": None,
        "forecasts_count": 0,
        # ... SEULEMENT kpis, PAS de signals/risks
    }
}
```

**Problème:** Frontend assume que `/dashboard/kpis` retourne signals/risks, mais backend ne le fait pas.

**Solutions:**
1. Backend ajoute `top_signals`/`top_risks` dans `/dashboard/kpis`
2. Frontend fait 2 appels séparés: `/dashboard/kpis` + `/brief`

---

### 5. Composants Utilisés Mais Non Vérifiés

**Fichiers à Vérifier:**
```bash
webapp/src/components/signals/TopSignals.tsx      # ✅ Utilisé
webapp/src/components/signals/TopRisks.tsx        # ✅ Utilisé
webapp/src/components/common/Card.tsx             # ✅ Utilisé
webapp/src/components/common/LoadingSpinner.tsx   # ✅ Utilisé
webapp/src/components/common/ErrorMessage.tsx     # ✅ Utilisé
webapp/src/components/layout/MainLayout.tsx       # ✅ Utilisé
```

**Action:** Vérifier que ces composants existent réellement

---

### 6. API Client - Pas de Gestion d'Erreurs HTTP

**Status:** 🟡 **FRAGILE**  
**Fichier:** `webapp/src/services/api.ts`

#### Implémentation Actuelle
```typescript
// api.ts:20-27
export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<ApiResult<T>> {
  const q = params ? '?' + new URLSearchParams(params).toString() : ''
  const r = await fetch(`/api${path}${q}`, { headers: defaultHeaders() })
  return r.json()  // ❌ PAS DE VÉRIFICATION r.ok
}
```

**Problème:** Si API retourne 500, on parse quand même le JSON

**Correction:**
```typescript
export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<ApiResult<T>> {
  const q = params ? '?' + new URLSearchParams(params).toString() : ''
  const r = await fetch(`/api${path}${q}`, { headers: defaultHeaders() })
  
  // ✅ AJOUTER
  if (!r.ok) {
    const error = await r.text()
    return { ok: false, error: `HTTP ${r.status}: ${error}` }
  }
  
  return r.json()
}
```

---

## ⚙️ Configuration & Environment

### 1. `.env` Minimal - Variables Critiques Manquantes

**Fichier:** `.env.sample`

#### Contenu Actuel
```bash
# .env.sample
FRED_API_KEY=               # ✅ OK
AF_ALLOW_INTERNET=0         # ✅ OK
```

#### Variables Manquantes pour MVP
```bash
# LLM
OPENAI_API_KEY=             # ❌ MANQUANT
OPENAI_BASE_URL=https://api.openai.com/v1  # ❌ MANQUANT
LLM_MODEL=gpt-4o-mini       # ❌ MANQUANT

# Database (si nécessaire)
DATABASE_URL=               # ❌ MANQUANT (si RAG → Postgres)

# API
API_PORT=8050               # ❌ MANQUANT (hardcodé dans main.py)
API_HOST=127.0.0.1          # ❌ MANQUANT

# Logging
LOG_LEVEL=INFO              # ❌ MANQUANT
LOGURU_LEVEL=INFO           # ❌ MANQUANT

# Cache
REDIS_URL=                  # ⚠️ Optionnel mais utile

# Finnhub (si utilisé)
FINNHUB_API_KEY=            # ⚠️ Utilisé dans peers_finder.py:57
```

---

### 2. Configuration Hardcodée dans Code

#### Ports et URLs
```python
# run_api.py:23-25
uvicorn.run(
    app,
    host="127.0.0.1",  # ❌ HARDCODÉ
    port=8050,         # ❌ HARDCODÉ
    reload=True,
    log_level="info"   # ❌ HARDCODÉ
)
```

**Besoin:** Lire depuis env

```python
# ✅ CORRECTION
import os
uvicorn.run(
    app,
    host=os.getenv("API_HOST", "127.0.0.1"),
    port=int(os.getenv("API_PORT", "8050")),
    reload=os.getenv("ENV") == "dev",
    log_level=os.getenv("LOG_LEVEL", "info")
)
```

---

#### Universe par Défaut
```python
# api/main.py:266
universe: List[str] = Query(["SPY", "QQQ"], ...)  # ❌ HARDCODÉ
```

**Besoin:**
```python
# Dans config.py
DEFAULT_UNIVERSE = ["SPY", "QQQ", "AAPL", "NVDA", "MSFT"]

# Dans api/main.py
from core.config import Config
universe: List[str] = Query(Config().DEFAULT_UNIVERSE, ...)
```

---

## 🧪 Tests & Qualité

### 1. Tests Unitaires - Couverture Faible

**Status:** 🟡 **INCOMPLET**

#### Structure Tests
```bash
tests/
├── __init__.py
├── test_*.py  # À VÉRIFIER combien existent
```

**Action:** Compter les tests existants
```bash
find tests/ -name "test_*.py" | wc -l
```

---

### 2. Tests d'Intégration - Absents

**Status:** 🔴 **MANQUANT**

#### Tests Critiques Manquants
- ❌ Test E2E: `/api/brief` → frontend affichage
- ❌ Test E2E: `/api/copilot/ask` → réponse + citations
- ❌ Test RAG: Seed → Search → Vérifier top_k
- ❌ Test scoring: calculate_composite_score cohérent
- ❌ Test pipeline: News ingestion → RAG → Q&A

---

### 3. Linting & Type Checking

#### Python
```bash
# Vérifier présence
ls pyproject.toml  # ruff config?
ls mypy.ini        # mypy config?
```

**Action Requise:**
```bash
# Installer outils
pip install ruff mypy pytest-cov

# Configurer
ruff check src/ --fix
mypy src/ --strict
pytest --cov=src tests/
```

---

#### TypeScript
```bash
# webapp/tsconfig.json existe ?
cat webapp/tsconfig.json | grep strict
```

**Action:** Vérifier `strict: true` activé

---

## 📚 Documentation Manquante

### 1. AGENTS.md - Incomplet pour Agent-Stack-OSS

**Fichier:** `agent-stack-oss/docs/AGENTS.md`

**Sections Manquantes:**
- ❌ Commandes typecheck/lint spécifiques au projet principal
- ❌ Structure de `/Users/venom/Documents/analyse-financiere` (repo parent)
- ❌ Comment intégrer agent avec API FastAPI

---

### 2. API Documentation - Swagger Incomplet

**Route:** `http://localhost:8050/docs`

**Gaps Probables:**
- ⚠️ Descriptions endpoints
- ⚠️ Exemples de requêtes/réponses
- ⚠️ Codes d'erreur documentés

**Vérification:**
```bash
curl http://localhost:8050/openapi.json | jq '.paths["/api/brief"]'
```

---

### 3. README Principal - Section Déploiement Absente

**Fichier:** `README.md`

**Sections Manquantes:**
- ❌ Déploiement production (Docker, systemd, etc.)
- ❌ Configuration Nginx/Apache reverse proxy
- ❌ Backup stratégie (RAG data, cache)
- ❌ Monitoring & Alerting
- ❌ Scaling (multiple workers)

---

## 🔗 Dépendances Circulaires & Imports Cassés

### 1. Import Circulaire Potentiel

```python
# research/materialize.py:21
from analytics.phase2_technical import ...

# analytics/phase2_technical.py (hypothétique)
from research.materialize import ...  # ❌ CIRCULAIRE ?
```

**Action:** Vérifier avec outil
```bash
pip install pydeps
pydeps src --max-bacon=2 --cluster -o deps.svg
```

---

### 2. Imports Relatifs vs Absolus - Incohérent

#### Style Mixte Détecté
```python
# Certains fichiers:
from core.market_data import ...        # ✅ Absolu

# Autres fichiers:
from ..core.market_data import ...     # ⚠️ Relatif
```

**Recommendation:** Standardiser sur absolus partout

---

## ⚡ Performance & Optimisation

### 1. RAG Search - O(n) Linéaire

**Fichier:** `src/research/rag_store.py:104-215`

#### Implémentation Actuelle
```python
def search(self, scope, top_k=10):
    results = []
    
    # ❌ LIT TOUT LE FICHIER LIGNE PAR LIGNE
    with open(self.news_file, "r") as f:
        for line in f:
            chunk = json.loads(line)
            # Filtrage en mémoire
            if tickers and chunk_ticker not in tickers:
                continue
            results.append(chunk)
    
    # ❌ TRI EN MÉMOIRE (O(n log n))
    results.sort(key=lambda x: ...)
    return results[:top_k]
```

**Problème:** Si 100k news items, charge TOUT en RAM à chaque recherche

**Solutions:**
1. **Court terme:** Index en mémoire (dict par ticker)
2. **Moyen terme:** SQLite FTS5 ou DuckDB
3. **Long terme:** Embeddings + FAISS/Qdrant

---

### 2. Pas de Cache HTTP

**Fichier:** `api/main.py`

#### Endpoints Sans Cache
```python
@app.get("/api/macro/series")  # ❌ Pas de cache header
@app.get("/api/stocks/prices") # ❌ Pas de cache header
```

**Impact:** Frontend recharge macro toutes les 10min (hooks/useMacroData.ts:7)

**Solution:**
```python
from fastapi import Response

@app.get("/api/macro/series")
async def get_macro_series(..., response: Response):
    # Cache 1h (données macro stables)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return ...
```

---

### 3. Pas de Pagination

**Routes Concernées:**
- `/api/news/feed` - Retourne limit fixe (max 200)
- `/api/forecasts` - Pas de pagination implémentée

**Besoin:**
```python
@app.get("/api/news/feed")
async def get_news_feed(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),  # ✅ AJOUTER
    ...
):
    items = run_news_pipeline(..., limit=limit+offset)[offset:]
    return {
        "items": items,
        "count": len(items),
        "offset": offset,
        "has_more": len(items) == limit  # ✅ AJOUTER
    }
```

---

## 🔒 Sécurité & Production

### 1. CORS Trop Permissif (Dev OK, Prod ❌)

**Fichier:** `api/main.py:36-43`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],  # ✅ OK pour dev
    allow_credentials=True,
    allow_methods=["*"],      # ⚠️ Trop permissif
    allow_headers=["*"],      # ⚠️ Trop permissif
)
```

**Production Requise:**
```python
import os

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # ✅ Limiter
    allow_headers=["Content-Type", "X-Trace-Id"],  # ✅ Explicite
)
```

---

### 2. Pas de Rate Limiting

**Status:** 🔴 **ABSENT**

**Endpoints Vulnérables:**
- `/api/copilot/ask` - Coûteux (LLM)
- `/api/brief` - Coûteux (scoring)
- `/api/rag/seed` - Très coûteux

**Solution:**
```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/copilot/ask")
@limiter.limit("10/minute")  # ✅ AJOUTER
async def copilot_ask(...):
    ...
```

---

### 3. Secrets dans Logs Potentiel

**Fichier:** `src/core/config.py:102-115`

```python
def to_dict(self, exclude_secrets: bool = True) -> Dict[str, Any]:
    # ✅ Bonne pratique: exclude_secrets par défaut
    ...
```

**Vérifier:** Que loguru ne log pas `Config.to_dict(exclude_secrets=False)`

---

### 4. Pas de Validation Input Stricte

**Exemple:**
```python
# api/main.py:99-103
@app.get("/api/macro/series")
async def get_macro_series(
    ids: List[str] = Query(...),  # ❌ Accepte N'IMPORTE QUOI
    start: Optional[str] = Query(None),  # ❌ Pas de validation format date
    ...
):
```

**Correction:**
```python
from pydantic import validator
from datetime import datetime

class MacroSeriesRequest(BaseModel):
    ids: List[str]
    start: Optional[str] = None
    
    @validator('ids')
    def validate_ids(cls, v):
        if len(v) > 20:  # ✅ Limiter
            raise ValueError("Max 20 series")
        for sid in v:
            if not sid.isalnum():  # ✅ Alphanumeric only
                raise ValueError(f"Invalid series_id: {sid}")
        return v
    
    @validator('start')
    def validate_start(cls, v):
        if v:
            try:
                datetime.fromisoformat(v)  # ✅ Valider format
            except:
                raise ValueError("start must be ISO format YYYY-MM-DD")
        return v

@app.get("/api/macro/series")
async def get_macro_series(req: MacroSeriesRequest = Depends()):
    ...
```

---

## 📊 Récapitulatif par Criticité

### 🔴 BLOQUANT MVP (5)
1. `core/data_access.py` manquant
2. `compute_composite_brief()` manquant
3. RAG non ensemencé (pas de données)
4. Client LLM non implémenté
5. Routes API placeholders (`/dashboard/kpis`)

### 🟡 IMPORTANT (8)
6. `analytics/indicators_basic.py` référencé
7. Imports inutilisés `api/main.py`
8. Frontend `useBriefs` incomplet
9. Frontend `copilotService` méthodes manquantes
10. Contrat API Dashboard ≠ Frontend
11. `.env` variables manquantes
12. Tests E2E absents
13. RAG Search performance O(n)

### 🟢 AMÉLIORATIONS (7)
14. Exceptions personnalisées
15. Cache HTTP headers
16. Pagination news/forecasts
17. CORS production-ready
18. Rate limiting
19. Input validation stricte
20. Documentation déploiement

---

## 🎯 Plan d'Action Complet

### Phase 0: Vérification (2h)
```bash
# 1. Vérifier modules existants
find src/ -name "*.py" | xargs grep "^def \|^class " | wc -l

# 2. Vérifier imports cassés
python -m py_compile src/**/*.py 2>&1 | grep -i error

# 3. Vérifier frontend build
cd webapp && npm run build

# 4. Lancer API sans crashes
python run_api.py &
curl http://localhost:8050/health

# 5. Tester chaque endpoint
for ep in /health /api/macro/series?ids=CPIAUCSL /api/news/feed; do
  echo "Testing $ep"
  curl -s http://localhost:8050$ep | jq '.ok'
done
```

---

### Phase 1: Déblocage MVP (12-15h)

#### Jour 1 (4-5h)
**Matin:**
- [ ] Créer `src/core/data_access.py` (3 fonctions)
- [ ] Tester scoring: `python -c "from research.scoring import calculate_composite_score; print(calculate_composite_score('AAPL'))"`

**Après-midi:**
- [ ] Implémenter `compute_composite_brief()` dans `scoring.py`
- [ ] Tester `/api/brief`: `curl http://localhost:8050/api/brief`

---

#### Jour 2 (4-5h)
**Matin:**
- [ ] Créer endpoint `/api/rag/seed`
- [ ] Ensemencer macro 5 ans (CPIAUCSL, UNRATE, DGS10, DGS2)
- [ ] Ensemencer prix 5 ans (SPY, QQQ weekly)

**Après-midi:**
- [ ] Vérifier `rag_store.stats()` > 1000 chunks
- [ ] Ensemencer news top 100 semaine

---

#### Jour 3 (4-5h)
**Matin:**
- [ ] Créer `src/research/llm_client.py`
- [ ] Tester avec OpenAI: `ask_llm("Test", [{"text": "Context", "meta": {...}}])`

**Après-midi:**
- [ ] Brancher `/api/copilot/ask` sur LLM
- [ ] Tester Q&A: `curl -X POST http://localhost:8050/api/copilot/ask -d '{"question": "Inflation ?"}'`
- [ ] Vérifier ≥2 citations

---

### Phase 2: Frontend (6-8h)

#### Jour 4 (3-4h)
- [ ] Corriger `brief.service.ts` (ajouter param `universe`)
- [ ] Ajouter méthodes `copilotService`: `getRAGStats()`, `createSession()`
- [ ] Vérifier types `BriefData` complets
- [ ] Tester affichage MarketBrief

#### Jour 5 (3-4h)
- [ ] Corriger `/api/dashboard/kpis` (ajouter signals/risks)
- [ ] Ou séparer appels frontend
- [ ] Améliorer `apiGet()` gestion erreurs HTTP
- [ ] Tests E2E manuels toutes pages

---

### Phase 3: Qualité & Sécurité (8-10h)

#### Jour 6 (4-5h)
- [ ] Compléter `.env.sample`
- [ ] Externaliser config hardcodée
- [ ] Ajouter cache headers
- [ ] Ajouter pagination `/api/news/feed`

#### Jour 7 (4-5h)
- [ ] Rate limiting endpoints coûteux
- [ ] Input validation Pydantic
- [ ] CORS production-ready
- [ ] Exceptions personnalisées

---

### Phase 4: Tests & Documentation (6-8h)

#### Jour 8 (3-4h)
- [ ] Tests unitaires scoring (3 fonctions)
- [ ] Tests unitaires RAG (seed + search)
- [ ] Tests API (brief, copilot, macro)

#### Jour 9 (3-4h)
- [ ] Documenter déploiement (Docker, systemd)
- [ ] Documenter backup/restore RAG
- [ ] Swagger descriptions
- [ ] README section production

---

## 🔢 Métriques d'Achèvement

### MVP Ready ✅
- [ ] Brief généré < 30s
- [ ] Q&A répond < 10s avec ≥2 citations
- [ ] RAG > 1000 chunks
- [ ] 5 tickers couverts
- [ ] News fraîcheur médiane < 60min
- [ ] Tous endpoints 2xx
- [ ] Frontend affiche données réelles

### Production Ready ✅
- [ ] Tests unitaires > 70% couverture
- [ ] Rate limiting actif
- [ ] CORS configuré
- [ ] Logs structurés
- [ ] Monitoring basic (health endpoint)
- [ ] Documentation déploiement
- [ ] Backup automatisé

---

## 📝 Notes Finales

### Points Positifs ✅
1. **Architecture solide** - Séparation claire backend/frontend
2. **Modules core complets** - `phase2_technical`, `phase3_macro`
3. **Pipeline news robuste** - `finnews.py` bien implémenté
4. **RAG store basique** - Fonctionnel pour MVP
5. **Types frontend** - Bonne utilisation TypeScript

### Risques Critiques ⚠️
1. **RAG performance** - O(n) intenable > 10k items
2. **Pas de monitoring** - Pas de métriques/alertes
3. **LLM coûts** - Pas de budget/throttling
4. **Single point of failure** - RAG = 2 fichiers JSONL
5. **Pas de CI/CD** - Déploiement manuel

### Recommandations Architecturales
1. **Court terme:** SQLite pour RAG (FTS5)
2. **Moyen terme:** PostgreSQL + pgvector
3. **Long terme:** Qdrant/Weaviate si > 100k chunks
4. **Monitoring:** Prometheus + Grafana basic
5. **CI/CD:** GitHub Actions (lint → test → deploy)

---

**Document généré:** 2 novembre 2025  
**Prochaine révision:** Post-implémentation Phase 1  
**Maintenu par:** Inspection Automatisée Continue
