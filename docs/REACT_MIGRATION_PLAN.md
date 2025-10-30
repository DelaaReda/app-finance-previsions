# 🚀 Plan de Migration React - État et Prochaines Étapes

**Date**: 2025-10-30  
**Commit de référence**: 44072a6  
**Objectif**: Migration progressive Dash/Streamlit → React selon VISION.md

---

## 📊 État Actuel

### ✅ Infrastructure de Base (Existante)

**Webapp déjà en place** (`/webapp`):
- ✅ Vite + React 18.3.1
- ✅ React Router 6.26.2
- ✅ TanStack Query 5.56.2 (data fetching)
- ✅ TypeScript configuré
- ✅ Proxy API vers port 8050

**Pages déjà créées**:
- ✅ `/pages/Dashboard.tsx` - KPIs basiques
- ✅ `/pages/Forecasts.tsx` - Liste prévisions
- ✅ `/pages/LLMJudge.tsx` - Interface LLM
- ✅ `/pages/Backtests.tsx` - Backtests (placeholder)

**API Client**:
- ✅ `/api/client.ts` - Fetch wrapper avec traceId
- ✅ Support `apiGet()` et `apiPost()`
- ✅ Type-safe avec `ApiResult<T>`

**Providers**:
- ✅ `QueryClientProvider` configuré
- ✅ React Query Devtools activé

---

## 🎯 Architecture Cible selon VISION.md

### 5 Piliers Fonctionnels à Implémenter

```
1. MACRO (FRED, VIX, cycles)
   └── /pages/Macro.tsx 🆕

2. ACTIONS (prix + indicateurs)
   └── /pages/Stocks.tsx 🆕

3. NEWS (RSS + scoring)
   └── /pages/News.tsx 🆕

4. LLM COPILOT (Q&A + RAG)
   └── /pages/Copilot.tsx 🆕

5. MARKET BRIEF (hebdo/journalier)
   └── /pages/MarketBrief.tsx 🆕
```

### Composants Transverses

```
SIGNALS (Top 3 signaux / Top 3 risques)
├── /components/signals/TopSignals.tsx 🆕
└── /components/signals/TopRisks.tsx 🆕

CHARTS (avec source + timestamp obligatoire)
├── /components/charts/MacroChart.tsx 🆕
├── /components/charts/PriceChart.tsx 🆕
└── /components/charts/ChartWithSource.tsx 🆕

LAYOUT
├── /components/layout/Header.tsx 🆕
├── /components/layout/Sidebar.tsx 🆕
└── /components/layout/Footer.tsx 🆕

NEWS
├── /components/news/NewsFeed.tsx 🆕
└── /components/news/NewsCard.tsx 🆕
```

---

## 🏗️ Structure de Dossiers Proposée

```
webapp/src/
├── pages/                    # Pages principales (routes)
│   ├── Dashboard.tsx         ✅ (à enrichir)
│   ├── Macro.tsx            🆕 Pilier 1
│   ├── Stocks.tsx           🆕 Pilier 2
│   ├── News.tsx             🆕 Pilier 3
│   ├── Copilot.tsx          🆕 Pilier 4
│   ├── MarketBrief.tsx      🆕 Brief hebdo/journalier
│   ├── TickerSheet.tsx      🆕 Fiche détaillée ticker
│   ├── Forecasts.tsx        ✅ (existe)
│   ├── Backtests.tsx        ✅ (existe)
│   └── LLMJudge.tsx         ✅ (existe)
│
├── components/              # Composants réutilisables
│   ├── layout/
│   │   ├── Header.tsx       🆕 Nav principale
│   │   ├── Sidebar.tsx      🆕 Menu latéral
│   │   └── Footer.tsx       🆕 Pied de page
│   ├── signals/
│   │   ├── TopSignals.tsx   🆕 Top 3 opportunités
│   │   └── TopRisks.tsx     🆕 Top 3 risques
│   ├── charts/
│   │   ├── MacroChart.tsx   🆕 Graphiques macro
│   │   ├── PriceChart.tsx   🆕 Graphiques prix
│   │   └── ChartWithSource.tsx 🆕 Wrapper avec citation
│   ├── news/
│   │   ├── NewsFeed.tsx     🆕 Flux news
│   │   └── NewsCard.tsx     🆕 Carte news individuelle
│   └── common/
│       ├── Card.tsx         🆕 Composant Card générique
│       ├── LoadingSpinner.tsx 🆕 Spinner
│       └── ErrorMessage.tsx 🆕 Messages d'erreur
│
├── services/                # API clients par pilier
│   ├── api.ts              ✅ (client.ts renommé)
│   ├── macro.service.ts    🆕 Services pilier macro
│   ├── stocks.service.ts   🆕 Services pilier actions
│   ├── news.service.ts     🆕 Services pilier news
│   ├── copilot.service.ts  🆕 Services LLM/RAG
│   └── brief.service.ts    🆕 Services Market Brief
│
├── hooks/                   # Custom hooks React Query
│   ├── useMacroData.ts     🆕 Hook données macro
│   ├── useStockData.ts     🆕 Hook données actions
│   ├── useNews.ts          🆕 Hook news
│   └── useCopilot.ts       🆕 Hook LLM Q&A
│
├── types/                   # TypeScript types
│   ├── macro.types.ts      🆕 Types pilier macro
│   ├── stocks.types.ts     🆕 Types pilier actions
│   ├── news.types.ts       🆕 Types pilier news
│   ├── copilot.types.ts    🆕 Types LLM/RAG
│   └── common.types.ts     🆕 Types communs
│
├── utils/                   # Helpers
│   ├── formatters.ts       🆕 Format dates, nombres
│   ├── scoring.ts          🆕 Calcul scores composites
│   └── constants.ts        🆕 Constantes app
│
├── app/
│   └── providers.tsx       ✅ (existe)
│
├── App.tsx                 ✅ (à enrichir avec layout)
└── main.tsx                ✅ (existe)
```

---

## 🔄 Backend API Python (à créer/étendre)

### Endpoints requis selon VISION

```python
# 1. MACRO
GET /api/macro/series         # Séries FRED (CPI, VIX, 10Y...)
GET /api/macro/snapshot       # Snapshot macro actuel
GET /api/macro/indicators     # Indicateurs avancés

# 2. ACTIONS
GET /api/stocks/prices        # Prix + indicateurs (SMA, RSI, MACD)
GET /api/stocks/universe      # Liste tickers surveillés
GET /api/stocks/{ticker}      # Fiche complète ticker

# 3. NEWS
GET /api/news/feed            # Flux news paginé + scoré
GET /api/news/by-ticker       # News filtrées par ticker
GET /api/news/sentiment       # Sentiment agrégé

# 4. LLM COPILOT
POST /api/copilot/ask         # Q&A avec RAG (5 ans contexte)
GET /api/copilot/history      # Historique conversations
POST /api/copilot/what-if     # Scénarios what-if

# 5. MARKET BRIEF
GET /api/brief/weekly         # Brief hebdomadaire
GET /api/brief/daily          # Brief journalier
POST /api/brief/generate      # Génération on-demand

# 6. SIGNALS
GET /api/signals/top          # Top 3 signaux + Top 3 risques
GET /api/signals/composite    # Scores composites (40/40/20)

# EXISTANTS
GET /api/dashboard/kpis       ✅
GET /api/forecasts            ✅
POST /api/llm/judge/run       ✅
```

---

## 📋 Plan d'Exécution Progressif

### Phase 1: Foundation (1-2 jours) 🎯 PRIORITAIRE

**Objectif**: Mettre en place l'architecture de base

- [ ] Créer structure dossiers complète
- [ ] Créer fichiers types TypeScript de base
- [ ] Créer composants layout (Header, Sidebar, Footer)
- [ ] Enrichir App.tsx avec layout complet
- [ ] Créer composants common (Card, LoadingSpinner, ErrorMessage)

**Fichiers à créer** (15 fichiers):
```
types/common.types.ts
types/macro.types.ts
types/stocks.types.ts
types/news.types.ts
types/copilot.types.ts
components/layout/Header.tsx
components/layout/Sidebar.tsx
components/layout/Footer.tsx
components/common/Card.tsx
components/common/LoadingSpinner.tsx
components/common/ErrorMessage.tsx
utils/formatters.ts
utils/scoring.ts
utils/constants.ts
App.tsx (refactor)
```

---

### Phase 2: Pilier MACRO (2-3 jours)

**Objectif**: Implémenter le premier pilier complet

- [ ] Backend: Endpoints `/api/macro/*`
- [ ] Frontend: Service `macro.service.ts`
- [ ] Frontend: Hook `useMacroData.ts`
- [ ] Frontend: Composant `MacroChart.tsx`
- [ ] Frontend: Page `Macro.tsx`
- [ ] Tests: E2E macro complet

**Indicateurs à afficher**:
- CPI YoY (inflation)
- VIX (volatilité)
- 10Y-2Y yield curve (récession)
- Fed Funds Rate
- Graphiques avec **source + timestamp obligatoire**

---

### Phase 3: Pilier ACTIONS (2-3 jours)

**Objectif**: Implémenter les données actions

- [ ] Backend: Endpoints `/api/stocks/*`
- [ ] Frontend: Service `stocks.service.ts`
- [ ] Frontend: Hook `useStockData.ts`
- [ ] Frontend: Composant `PriceChart.tsx`
- [ ] Frontend: Page `Stocks.tsx`
- [ ] Frontend: Page `TickerSheet.tsx`
- [ ] Tests: E2E stocks complet

**Données à afficher**:
- Prix OHLCV (downsampled via LTTB)
- Indicateurs: SMA20, RSI, MACD
- Volume
- Comparaisons secteur

---

### Phase 4: Pilier NEWS (2-3 jours)

**Objectif**: Implémenter le flux news

- [ ] Backend: Endpoints `/api/news/*`
- [ ] Frontend: Service `news.service.ts`
- [ ] Frontend: Hook `useNews.ts`
- [ ] Frontend: Composants `NewsFeed.tsx` + `NewsCard.tsx`
- [ ] Frontend: Page `News.tsx`
- [ ] Tests: E2E news complet

**Features**:
- Flux RSS agrégé + scoré (fraîcheur/pertinence/source)
- Filtres: ticker, région, timeframe
- Déduplication intelligente
- Sentiment analysis

---

### Phase 5: Pilier LLM COPILOT (3-4 jours)

**Objectif**: Implémenter le copilote LLM

- [ ] Backend: Endpoints `/api/copilot/*`
- [ ] Backend: Intégration RAG (5 ans données)
- [ ] Frontend: Service `copilot.service.ts`
- [ ] Frontend: Hook `useCopilot.ts`
- [ ] Frontend: Page `Copilot.tsx`
- [ ] Tests: E2E copilot + RAG

**Features**:
- Q&A avec contexte (macro + prix + news)
- Citations obligatoires (sources + dates)
- Historique conversations
- What-if scenarios
- **Limites explicites** (pas de prédictions, pas de conseils financiers)

---

### Phase 6: SIGNALS + BRIEF (2 jours)

**Objectif**: Implémenter Top 3 signaux/risques + brief

- [ ] Backend: Endpoints `/api/signals/*` + `/api/brief/*`
- [ ] Frontend: Composants `TopSignals.tsx` + `TopRisks.tsx`
- [ ] Frontend: Page `MarketBrief.tsx`
- [ ] Génération brief hebdo automatique
- [ ] Export HTML/MD

**Scoring composite** (selon VISION):
- Macro: 40%
- Technical: 40%
- News: 20%

---

### Phase 7: Dashboard Enrichi (1 jour)

**Objectif**: Enrichir le dashboard avec tous les piliers

- [ ] Intégrer TopSignals + TopRisks
- [ ] Widgets macro (mini-charts)
- [ ] Widgets actions (top movers)
- [ ] Widgets news (dernières alertes)
- [ ] Lien vers brief hebdo

---

### Phase 8: Polish + Tests (2-3 jours)

**Objectif**: Finaliser la migration

- [ ] Tests E2E complets (Playwright)
- [ ] Tests unitaires composants (Vitest)
- [ ] Performance: auditer latence API
- [ ] Performance: optimiser bundle size
- [ ] Accessibilité (a11y audit)
- [ ] Documentation utilisateur
- [ ] Guide déploiement

---

## 🎨 Design System Proposé

### Palette Couleurs (Finance-friendly)

```css
/* Primaires */
--color-primary: #2563eb;    /* Bleu professionnel */
--color-success: #10b981;    /* Vert (signaux positifs) */
--color-danger: #ef4444;     /* Rouge (risques) */
--color-warning: #f59e0b;    /* Orange (attention) */

/* Neutres */
--color-bg-dark: #0f172a;    /* Fond sombre */
--color-bg-card: #1e293b;    /* Cartes */
--color-text: #f1f5f9;       /* Texte principal */
--color-text-muted: #94a3b8; /* Texte secondaire */

/* Accents */
--color-macro: #8b5cf6;      /* Violet (macro) */
--color-stocks: #06b6d4;     /* Cyan (actions) */
--color-news: #f97316;       /* Orange (news) */
```

### Typographie

```css
/* Titres */
--font-heading: 'Inter', system-ui, sans-serif;
--font-body: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace; /* Données numériques */

/* Tailles */
--text-xs: 0.75rem;   /* 12px */
--text-sm: 0.875rem;  /* 14px */
--text-base: 1rem;    /* 16px */
--text-lg: 1.125rem;  /* 18px */
--text-xl: 1.25rem;   /* 20px */
--text-2xl: 1.5rem;   /* 24px */
```

### Spacing

```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
```

---

## 📦 Dépendances à Ajouter

```json
{
  "dependencies": {
    "recharts": "^2.10.0",          // Charts React-friendly
    "date-fns": "^3.0.0",           // Manipulation dates
    "clsx": "^2.0.0",               // Utility classes
    "react-markdown": "^9.0.0",     // Render markdown (brief)
    "react-syntax-highlighter": "^15.5.0"  // Code syntax (copilot)
  },
  "devDependencies": {
    "vitest": "^1.0.0",             // Tests unitaires
    "@testing-library/react": "^14.0.0",
    "@testing-library/user-event": "^14.5.0",
    "playwright": "^1.40.0"         // Tests E2E
  }
}
```

---

## 🚦 Critères de Succès

### KPIs VISION (à valider)

- ✅ Couverture ≥ 90% tickers ≤ 24h
- ✅ Fraîcheur news médiane < 10 min
- ✅ Brief ≤ 2 pages (annexes à part)
- ✅ 100% graphiques avec **source + timestamp**
- ✅ 80% réponses LLM avec ≥ 2 sources

### Métriques Performance

- Latence API: < 200ms (p95)
- Taille bundle JS: < 500KB (gzipped)
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3.5s
- Lighthouse Score: ≥ 90

---

## 🔄 Migration Progressive (Zero Downtime)

### Stratégie

1. **Coexistence**: Dash/Streamlit reste actif sur port 8050
2. **React parallèle**: Port 5173 (dev) / 3000 (prod)
3. **API unifiée**: Backend Python sert les deux UIs
4. **Migration graduelle**: Feature par feature
5. **Kill switch**: Retour Dash/Streamlit si problème React

### Rollout

- **Semaine 1-2**: Foundation + Pilier MACRO (beta users)
- **Semaine 3-4**: Piliers ACTIONS + NEWS (50% users)
- **Semaine 5-6**: Piliers COPILOT + BRIEF (100% users)
- **Semaine 7**: Décommission Dash/Streamlit

---

## 📞 Support Migration

### Points de contact

- **Architecture data**: Voir `VALIDATION_DATA_LAYER.md`
- **VISION app**: Voir `docs/VISION.md`
- **Guide agents**: Voir `docs/AGENT_GUIDE.md`
- **Architecture**: Voir `docs/ARCHITECTURE.md`

### Questions fréquentes

**Q: Puis-je utiliser Tailwind CSS ?**
A: Oui, mais garde les utility classes minimales. Privilégie CSS modules pour les composants complexes.

**Q: Comment gérer le state global ?**
A: TanStack Query pour data fetching. Zustand ou Context API si vraiment besoin de state global (navigation, user prefs).

**Q: Downsampling côté client ou serveur ?**
A: **Serveur** (via `core/downsample.py`). Client reçoit déjà 1000 points max.

---

**Prêt à démarrer la Phase 1 ?** 🚀
