# ✅ TASKS_BOARD_V2.md CRÉÉ !

J'ai créé un **nouveau board de tâches modernisé** , il est important de reutilise les api's et modules deja existants et seulement de adapter le output des modules existants, exemple de module copilot-app/backend/src/analytics/econ_llm_agent.py

---

## 📋 CE QUI EST LIVRÉ

**Fichier:** `TASKS_BOARD_V2.md`

### **Structure:**

1. **Format des Tâches** - Convention de nommage (BE-XXX, FE-XXX, FS-XXX, etc.)
2. **14 Tâches Détaillées** organisées par priorité
3. **Steps précis** avec code examples pour chaque tâche
4. **DoD (Definition of Done)** claire pour validation

***

## 🎯 TÂCHES CRÉÉES

### **P0 CRITIQUE - Intégration Backend (6 tâches, 470 pts)**

**BE-100: API Portfolio Summary** (100 pts, M)
- Créer endpoint `/api/portfolio/summary`
- Modèle Pydantic + Service + Route FastAPI
- Données réelles via `yfinance`
- Steps complets avec code Python

**FE-100: Connecter Portfolio Header** (60 pts, S)
- Hook TanStack Query `usePortfolio`
- Connecter composant aux données réelles
- Loading/Error states

**BE-101: API Candlestick Chart** (90 pts, M)
- Endpoint `/api/stocks/{symbol}/candlestick`
- Données OHLCV réelles
- Calcul MA(20)
- Events (earnings)

**FE-101: Connecter Candlestick** (70 pts, S)
- Hook `useCandlestick`
- Remplacer données mock
- Timeframe selector

**FE-102: Hover Crosshair + Tooltip** (50 pts, S)
- Interactivité candlestick
- Tooltip OHLCV détaillé
- Smooth UX

**FE-104: Navigation Diamond Fix** (50 pts, S)
- Corriger bug close immédiat
- stopPropagation()
- Delayed close

***

### **P1 ÉLEVÉE - Features Avancées (5 tâches, 450 pts)**

**BE-102: API Heatmap Correlation** (80 pts, M)
- Endpoint `/api/portfolio/correlation`
- Calcul corrélations réelles
- Matrix 8x8

**BE-103: API Treemap Allocation** (80 pts, M)
- Endpoint `/api/portfolio/allocation`
- Holdings avec sectors et returns

**BE-104: API Market Volatility** (80 pts, M)
- Endpoint `/api/market/volatility`
- Données VIX via FRED API

**BE-105: API Trade Ideas** (120 pts, L)
- Endpoint `/api/trading/ideas`
- Détection signaux techniques
- Stop loss/target automatique

**BE-106: API News Feed** (90 pts, M)
- Endpoint `/api/news`
- Flux RSS + sentiment

***

### **P2 MOYENNE - Polish & UX (3 tâches, 120 pts)**

**FE-103: Widget Menu Dropdown** (40 pts, S)
- Bouton ⋮ fonctionnel
- 4 options (Pin, Export, Share, Settings)

**UI-100: Win Rate Circular Chart** (60 pts, S)
- Remplacer cercle noir
- Chart 72% avec stats

***

## 🌟 POINTS FORTS DU NOUVEAU BOARD

### **1. Basé sur V19 Architecture**
- Tâches alignées avec le frontend existant
- Data mapping défini clairement
- Structure TypeScript → Python cohérente

### **2. Steps Ultra-Détaillés**
- Code examples pour chaque tâche
- Fichiers précis à créer/modifier
- Commandes curl pour tester

### **3. DoD Claire**
- Checklist validation
- Proof requirements
- Tests requis

### **4. Priorités Intelligentes**
- P0: Intégration backend critique (données réelles)
- P1: Features avancées (heatmap, volatility, news)
- P2: Polish UX (interactions, widgets)

### **5. Points d'Attention**
- Gestion erreurs
- Patterns (never-empty, cache, etc.)
- Performance considerations

***

## 📊 EXEMPLE TÂCHE COMPLÈTE

**BE-100: API Portfolio Summary** contient:

✅ **Why** - Contexte et problème  
✅ **Pré-requis** - Ce qu'il faut avant  
✅ **Steps détaillés** (7 étapes):
  1. Créer modèle Pydantic (avec code Python complet)
  2. Créer service Portfolio (avec logique métier)
  3. Créer endpoint API (avec FastAPI route)
  4. Enregistrer router
  5. Tester l'endpoint (avec commandes curl)
  6. Ajouter cache
  7. Documentation

✅ **DoD** - 10 checkpoints de validation  
✅ **Points d'attention** - Pièges à éviter

***

## 🎯 RECOMMANDATIONS UTILISATION

**Pour débuter rapidement:**
1. **FE-100** (60 pts) - Connecter Portfolio Header (simple hook)
2. **FE-104** (50 pts) - Fix Navigation (bugfix JS)
3. **UI-100** (60 pts) - Win Rate Chart (composant visuel)

**Pour impact maximum:**
1. **BE-100** (100 pts) - API Portfolio (fondation backend)
2. **BE-101** (90 pts) - API Candlestick (chart pro)
3. **BE-105** (120 pts) - API Trade Ideas (feature avancée)

---

## 🔥 DIFFÉRENCES AVEC LEGACY BOARD

| Aspect | Legacy (FC-XXX) | Nouveau (BE-XXX, FE-XXX) |
|--------|-----------------|--------------------------|
| **Tech Stack** | MUI, Dash, Streamlit | Mantine v7, Tremor, FastAPI |
| **Format** | Sections mélangées | Organisé par priorité claire |
| **Steps** | Parfois vagues | Ultra-détaillés avec code |
| **Code Examples** | Rares | Chaque tâche a du code |
| **Data Mapping** | Absent | Aligné avec TypeScript frontend |
| **Testing** | Minimal | DoD avec tests requis |
| **Architecture** | Ancienne | Basée sur V19 actuelle |

***

## 📈 STATISTIQUES

**Total:** 14 tâches, 1,040 points

**Par catégorie:**
- Backend: 6 tâches (540 pts)
- Frontend: 6 tâches (380 pts)
- UI/UX: 1 tâche (60 pts)
- Test: 1 tâche (60 pts)

**Par effort:**
- S (0.5j): 7 tâches
- M (1-2j): 6 tâches
- L (3-5j): 1 tâche

---

## ✨ EXEMPLE CODE FOURNI

Chaque tâche backend contient du **code Python complet** comme:

```python
# Modèle Pydantic
class Portfolio(BaseModel):
    totalValue: float
    dailyChange: DailyChange
    holdings: List[Holding]
    sparkline: List[float]

# Service
class PortfolioService:
    def get_portfolio_summary(self) -> Portfolio:
        # Logique avec yfinance
        ...

# Endpoint FastAPI
@router.get("/api/portfolio/summary")
async def get_portfolio_summary():
    return portfolio_service.get_portfolio_summary()
```

Chaque tâche frontend contient du **code TypeScript complet** comme:

```typescript
// Hook TanStack Query
export function usePortfolio() {
  return useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: async () => {
      const response = await apiGet<Portfolio>('/api/portfolio/summary');
      return response.data;
    },
  });
}
```

# 📋 LISTE COMPLÈTE DES TÂCHES - BACKEND FASTAPI PYTHON

Voici la liste détaillée de **toutes les tâches backend** à ajouter, spécifiques à FastAPI Python :

---

## 🎯 P0 CRITIQUE - FONDATIONS BACKEND

### **BE-100: API Portfolio Summary**
- **Points:** 100
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/portfolio/summary`
- **Tech:** FastAPI + Pydantic + yfinance
- **Livrables:**
  - Modèle `Portfolio` (totalValue, dailyChange, holdings, sparkline)
  - Service `PortfolioService.get_portfolio_summary()`
  - Route FastAPI avec response_model
  - Cache Redis (TTL 60s)
  - Tests unitaires

### **BE-101: API Candlestick Chart**
- **Points:** 90
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/stocks/{symbol}/candlestick?timeframe=1W`
- **Tech:** FastAPI + yfinance + pandas
- **Livrables:**
  - Modèle `CandlestickData` (candles OHLCV, MA(20), events)
  - Service `CandlestickService.get_candlestick_data(symbol, timeframe)`
  - Calcul MA(20) avec pandas rolling
  - Route FastAPI avec query params
  - Cache Redis (TTL 5min)

### **BE-102: API Heatmap Correlation**
- **Points:** 80
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/portfolio/correlation`
- **Tech:** FastAPI + pandas + numpy
- **Livrables:**
  - Modèle `HeatmapData` (stocks list, correlation matrix 8x8)
  - Service avec `DataFrame.corr()` pour calculs
  - Matrix symétrique validée
  - Route FastAPI
  - Cache Redis (TTL 1h)

### **BE-103: API Treemap Allocation**
- **Points:** 80
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/portfolio/allocation`
- **Tech:** FastAPI + Pydantic
- **Livrables:**
  - Modèle `TreemapData` (holdings avec value, sector, return)
  - Service qui formate holdings pour treemap
  - Calcul allocations par secteur
  - Route FastAPI
  - Cache Redis (TTL 30min)

### **BE-104: API Market Volatility (VIX)**
- **Points:** 80
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/market/volatility?timeframe=1W`
- **Tech:** FastAPI + fredapi (FRED API)
- **Livrables:**
  - Modèle `VolatilityData` (current VIX, historical, zones)
  - Service avec FRED API integration
  - Calcul zones de risque (Low/Medium/High)
  - Route FastAPI
  - Cache Redis (TTL 5min)

### **BE-105: API Trade Ideas**
- **Points:** 120
- **Effort:** L (3-5j)
- **Endpoint:** `GET /api/trading/ideas`
- **Tech:** FastAPI + ta-lib (technical analysis)
- **Livrables:**
  - Modèle `TradeIdea` (signal, entry, target, stopLoss, riskReward)
  - Service détection signaux (breakout, reversal)
  - Calcul automatique stop loss/target
  - Performance tracking (wins/losses)
  - Route FastAPI
  - Cache Redis (TTL 15min)

### **BE-106: API News Feed**
- **Points:** 90
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/news?limit=15`
- **Tech:** FastAPI + feedparser (RSS) + transformers (sentiment)
- **Livrables:**
  - Modèle `NewsItem` (headline, sentiment, impact, source)
  - Service parsing RSS (Reuters, Bloomberg)
  - Sentiment analysis avec transformers
  - Route FastAPI avec pagination
  - Cache Redis (TTL 10min)

***

## 🤖 P1 ÉLEVÉE - AI & INTELLIGENCE

### **BE-107: API LLM Judge (Consensus Multi-Modèles)**
- **Points:** 150
- **Effort:** L (3-5j)
- **Endpoint:** `POST /api/ai/judge`
- **Tech:** FastAPI + openai + anthropic + google-generativeai + asyncio
- **Livrables:**
  - Modèle `LLMJudgeResponse` (consensus, confidence, models opinions)
  - Service async avec 3 LLMs (GPT-5, Claude, Gemini)
  - `asyncio.gather()` pour calls parallèles
  - Rate limiting (10 req/h par user)
  - Cache intelligent (question + context hash, TTL 5min)
  - Fallback si 1 LLM fail
  - Documentation coût par requête (~$0.10)

### **BE-108: API AI Suggestions**
- **Points:** 90
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/ai/suggestions`
- **Tech:** FastAPI + openai (GPT-4)
- **Livrables:**
  - Modèle `Suggestion` (text, priority, category, action)
  - Service analyse portfolio (concentration, secteurs)
  - Analyse news récentes pour suggestions
  - Détection anomalies (volumes, volatilité)
  - Génération 3-5 suggestions prioritaires
  - Route FastAPI
  - Cache Redis (TTL 10min)

### **BE-109: API Market Calendar**
- **Points:** 85
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/calendar/events?from=2024-11-20&to=2024-11-27`
- **Tech:** FastAPI + yfinance (earnings) + requests (Fed calendar)
- **Livrables:**
  - Modèle `CalendarEvent` (date, time, type, impact)
  - Service intégration earnings calendar (Yahoo)
  - Intégration Fed events (calendrier officiel)
  - Intégration economic data (FRED)
  - Filtrage par holdings user
  - Route FastAPI avec date range
  - Cache Redis (TTL 1h)

### **BE-110: API Copilot Chat (Streaming)**
- **Points:** 130
- **Effort:** L (3-5j)
- **Endpoint:** `POST /api/copilot/chat` (SSE streaming)
- **Tech:** FastAPI + openai (GPT-4) + Redis + SQLAlchemy
- **Livrables:**
  - Modèles `ChatMessage`, `ChatRequest`, `ChatResponse`
  - Service context-aware (sait facette actuelle)
  - Conversation memory (Redis pour actif, DB pour historique)
  - Streaming avec `StreamingResponse` FastAPI
  - Suggested follow-ups intelligents
  - Storage Redis + PostgreSQL
  - Tests streaming

---

## 📊 P2 MOYENNE - DATA & ANALYTICS

### **BE-111: API Portfolio Breakdown**
- **Points:** 75
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/portfolio/breakdown`
- **Tech:** FastAPI + pandas + numpy
- **Livrables:**
  - Modèle `PortfolioBreakdown` (bySector, byAsset, byRisk)
  - Service calcul allocations secteurs
  - Calcul métriques risque (volatility, beta, sharpe)
  - Route FastAPI
  - Cache Redis (TTL 30min)

### **BE-112: API Historical Sparklines**
- **Points:** 70
- **Effort:** M (1-2j)
- **Endpoint:** `GET /api/portfolio/sparkline?period=60`
- **Tech:** FastAPI + pandas
- **Livrables:**
  - Service données historiques (60 jours)
  - Calcul valeur portfolio journalière
  - Array 60 points pour sparkline
  - Route FastAPI
  - Cache Redis (TTL 1h)

***

## 📊 RÉSUMÉ BACKEND

**Total:** 12 tâches backend  
**Points:** 1,005 pts

**Par priorité:**
- **P0 CRITIQUE:** 7 tâches - 640 pts
- **P1 ÉLEVÉE:** 4 tâches - 455 pts (AI/Intelligence)
- **P2 MOYENNE:** 2 tâches - 145 pts (Analytics)

***

## 🔧 STACK TECHNIQUE BACKEND

**Framework:**
- FastAPI (async/await)
- Pydantic (modèles validation)
- uvicorn (ASGI server)

**Data & APIs:**
- yfinance (stocks data)
- fredapi (economic data)
- pandas + numpy (calculs)
- ta-lib (technical analysis)

**AI & LLM:**
- openai (GPT-4/5)
- anthropic (Claude)
- google-generativeai (Gemini)
- transformers (sentiment analysis)

**Storage:**
- Redis (cache + sessions)
- PostgreSQL (persistance)
- SQLAlchemy (ORM)

**Monitoring:**
- slowapi (rate limiting)
- prometheus_client (métriques)
