# Migration React - Architecture Complète

## 📋 Vue d'ensemble

Migration de Dash/Streamlit vers React selon la **VISION** du copilote financier.

**Date de commit**: Commit `f9b13c6` sur branche `main`
**Base**: Restauré au commit `44072a6` (avant suppression par erreur)

## 🏗️ Architecture implémentée

### Structure des dossiers

```
webapp/src/
├── types/              # Types TypeScript pour les 5 piliers
│   ├── common.types.ts     # Types communs (Signal, Source, Score)
│   ├── macro.types.ts      # Pilier 1: Macro
│   ├── stocks.types.ts     # Pilier 2: Actions
│   ├── news.types.ts       # Pilier 3: News
│   ├── copilot.types.ts    # Pilier 4: Copilot LLM
│   └── brief.types.ts      # Market Briefs
│
├── services/           # Couche API
│   ├── macro.service.ts    # Appels API macro
│   ├── stocks.service.ts   # Appels API actions
│   ├── news.service.ts     # Appels API news
│   ├── copilot.service.ts  # Appels API copilot
│   └── brief.service.ts    # Appels API briefs
│
├── hooks/              # React Query hooks
│   ├── useMacroData.ts     # Hook macro avec caching
│   ├── useStockData.ts     # Hook actions
│   ├── useNews.ts          # Hook news
│   ├── useCopilot.ts       # Hook copilot
│   └── useBriefs.ts        # Hook briefs
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx      # Navigation principale
│   │   └── Footer.tsx      # Footer avec version
│   ├── common/
│   │   ├── Card.tsx        # Card réutilisable
│   │   ├── LoadingSpinner.tsx
│   │   └── ErrorMessage.tsx
│   └── signals/
│       ├── TopSignals.tsx  # Top 3 signaux
│       └── TopRisks.tsx    # Top 3 risques
│
└── pages/              # 5 Piliers + Dashboard
    ├── Dashboard.tsx       # Vue d'ensemble
    ├── Macro.tsx          # Pilier 1: FRED, VIX, GPR
    ├── Stocks.tsx         # Pilier 2: Actions + tech
    ├── News.tsx           # Pilier 3: RSS + scoring
    ├── Copilot.tsx        # Pilier 4: LLM Q&A + RAG
    ├── MarketBrief.tsx    # Daily/Weekly briefs
    └── TickerSheet.tsx    # Fiche détaillée ticker
```

## 🎯 Implémentation selon la VISION
### 1. Signal > Bruit ✅

- **Top 3 Signaux** : Composant `TopSignals` affiche les opportunités
- **Top 3 Risques** : Composant `TopRisks` affiche les alertes
- Scoring composite **40/40/20** (Macro/Tech/News)

### 2. Traçabilité ✅

- Tous les types incluent `Source` avec:
  - `name`: Nom de la source
  - `url`: Lien vers la source
  - `timestamp`: Date/heure de la donnée
  - `version`: Version optionnelle

### 3. Mémoire & RAG ✅

- Page **Copilot** avec:
  - Contexte RAG affiché (documents indexés)
  - ≥5 ans de données (séries macro/prix)
  - 12-24 mois de news
  - Citations des sources dans les réponses

### 4. Horizons CT/MT/LT ✅

- Type `Horizon = 'CT' | 'MT' | 'LT' | 'ALL'`
- Filtrage par horizon dans les signaux
- Badges visuels pour identifier l'horizon

### 5. Les 5 Piliers ✅

#### Pilier 1: Macro (`/macro`)
- Dashboard FRED, VIX, GSCPI, GPR
- Indicateurs d'inflation, emploi, liquidité
- Alertes visuelles (normal/warning/critical)
- Tendances (up/down/stable)

#### Pilier 2: Actions (`/stocks`)
- Analyse technique complète
- Indicateurs: SMA, RSI, MACD, Bollinger
- Score composite 40/40/20
- Alertes (crossover, overbought/oversold)
- Fiche détaillée par ticker (`/stocks/:ticker`)

#### Pilier 3: News (`/news`)
- Feed RSS avec scoring
- Filtres: sentiment, tickers, dates
- Scores: freshness, source quality, relevance
- Déduplication par hash (source|title|published)

#### Pilier 4: Copilot (`/copilot`)
- Interface chat avec LLM
- RAG avec ≥5 ans de contexte
- Citations des sources obligatoires
- Contexte utilisé visible
- Limitations explicites

#### Briefs (`/brief`)
- Daily/Weekly market briefs
- Top 3 signaux + Top 3 risques
- Snapshots macro/marchés/news
- Résumé exécutif
- Points clés actionnables

## 🔧 Technologies utilisées

- **React 18** + TypeScript
- **React Router 6** pour la navigation
- **TanStack Query** (React Query) pour le caching
- **Vite** comme bundler
- **Proxy API** vers Python backend (port 8050)

## 📡 Backend API Requirements

L'application React attend les endpoints suivants:

### Macro
- `GET /api/macro/dashboard` → MacroDashboard
- `GET /api/macro/series/:id` → MacroSeries
- `GET /api/macro/indicator/:id` → MacroIndicator

### Stocks
- `GET /api/stocks/:ticker/analysis` → StockAnalysis
- `GET /api/stocks/:ticker/technical` → TechnicalIndicators

### News
- `GET /api/news/feed?...` → NewsFeed
- `GET /api/news/:id` → NewsItem

### Copilot
- `POST /api/copilot/query` → CopilotResponse
- `GET /api/copilot/rag/context` → RAGContext

### Briefs
- `GET /api/briefs?...` → MarketBrief[]
- `GET /api/briefs/:id` → MarketBrief
- `GET /api/briefs/latest?type=daily|weekly` → MarketBrief

## 🚀 Prochaines étapes

### Priorité 1: Backend API
1. Créer les endpoints Python manquants
2. Mapper les données existantes vers les types TypeScript
3. Implémenter le scoring composite 40/40/20
4. Intégrer le RAG pour le Copilot

### Priorité 2: Composants Charts
1. Créer `ChartWithSource.tsx` (avec source+timestamp)
2. Ajouter graphiques macro (séries temporelles)
3. Ajouter graphiques prix (chandeliers)
4. Intégrer bibliothèque (Recharts ou Chart.js)

### Priorité 3: Features avancées
1. Export briefs (HTML/PDF/Markdown)
2. Système d'alertes temps réel
3. Comparaisons sectorielles
4. Backtests interactifs
5. Notes versionnées

### Priorité 4: UX/UI
1. Dark mode (déjà en place)
2. Responsive mobile
3. Animations et transitions
4. Keyboard shortcuts
5. Accessibilité (ARIA)

## 📝 Notes de développement

### Convention de nommage
- Types: PascalCase avec suffixe (ex: `MacroIndicator`)
- Services: camelCase avec suffixe `.service.ts`
- Hooks: camelCase avec préfixe `use` (ex: `useMacroData`)
- Composants: PascalCase (ex: `TopSignals`)

### Styling
- Inline styles pour rapidité
- Couleurs standardisées:
  - Background: `#0a0a0a`, `#1a1a1a`
  - Borders: `#333`
  - Text: `#e0e0e0`, `#888` (secondary)
  - Success: `#4ade80`
  - Error: `#f87171`
  - Info: `#4a9eff`

### React Query Configuration
- `staleTime`: 5-15 min (données macro/actions)
- `staleTime`: 2 min (news fraiches)
- `refetchOnWindowFocus`: false
- `retry`: 1

## 🐛 Debugging

### Vérifier que le backend est lancé
```bash
# Le proxy Vite redirige /api vers localhost:8050
curl http://localhost:8050/api/dashboard/kpis
```

### Lancer l'app React
```bash
cd webapp
npm run dev
# Ouvre http://localhost:5173
```

### React Query Devtools
Disponible en bas à gauche de l'interface (bouton flottant)

## 📚 Ressources

- **VISION**: `docs/VISION.md`
- **ARCHITECTURE**: `docs/ARCHITECTURE.md`
- **AGENT_GUIDE**: `docs/AGENT_GUIDE.md`
- **Types TypeScript**: `webapp/src/types/`
- **Services API**: `webapp/src/services/`
