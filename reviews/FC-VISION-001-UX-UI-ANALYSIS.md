# FC-VISION-001 : Analyse UX/UI et Vision Produit Finance Copilot

**Agent** : CLAUDE-STABILITY-ARCHITECT-IRONMAN-42
**Date** : 2025-11-04
**Status** : En cours
**Type** : Analyse multi-niveaux & Vision Produit

---

## 📋 Table des Matières

1. [Executive Summary](#executive-summary)
2. [Architecture Actuelle](#architecture-actuelle)
3. [User Journeys Critiques](#user-journeys-critiques)
4. [Pain Points Identifiés](#pain-points-identifiés)
5. [Analyse de la Qualité des Données](#analyse-de-la-qualité-des-données)
6. [Vision Produit Cible](#vision-produit-cible)
7. [Plan d'Amélioration](#plan-damélioration)

---

## 🎯 Executive Summary

### État Actuel
Finance Copilot est une application d'analyse financière **opérationnelle** mais qui souffre de problèmes de **qualité d'expérience utilisateur** et de **pertinence des données affichées**.

### Problèmes Critiques Identifiés

| Catégorie | Problème | Impact Utilisateur | Priorité |
|-----------|----------|-------------------|----------|
| **UI/UX** | Données peu utiles affichées | Confusion, perte de temps | 🔴 Critique |
| **UI/UX** | Bugs d'affichage fréquents | Frustration, perte de confiance | 🔴 Critique |
| **Data** | Manque de contexte et d'insights | Valeur limitée | 🟠 Haute |
| **Data** | Données techniques sans explication | Courbe d'apprentissage élevée | 🟠 Haute |
| **Flow** | Navigation peu intuitive | Inefficacité | 🟡 Moyenne |
| **Performance** | Temps de chargement variables | Impatience | 🟡 Moyenne |

### Recommandations Clés

1. **Recentrer sur la valeur utilisateur** : Passer de "afficher des données" à "fournir des insights actionnables"
2. **Simplifier et contextualiser** : Moins de métriques, plus de signification
3. **Améliorer la stabilité** : Zero-crash policy avec guards robustes
4. **Enrichir l'information** : Ajouter explications, tendances, recommandations

---

## 🏗️ Architecture Actuelle

### Stack Technique

**Frontend**
- Framework : React + Vite
- State Management : TanStack Query (React Query)
- Styling : Inline styles (CSS-in-JS)
- Port : 5173 (dev)
- API Client : Custom fetch wrapper avec error handling

**Backend**
- Framework : FastAPI (Python)
- Port : 8050
- Architecture : API RESTful
- Data Storage : JSON files (local filesystem)
- Caching : Custom cache layer avec load_or_compute pattern

### Data Flow Actuel

```
┌──────────────┐
│   Frontend   │
│  (React)     │
└──────┬───────┘
       │ HTTP/JSON
       ▼
┌──────────────┐      ┌─────────────┐
│   API Proxy  │─────▶│  FastAPI    │
│   (Vite)     │      │  Backend    │
└──────────────┘      └──────┬──────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌─────▼──────┐   ┌─────▼─────┐
              │  Services  │   │  Models   │
              │  Layer     │   │  (ML+G4F) │
              └─────┬──────┘   └─────┬─────┘
                    │                │
                    └────────┬───────┘
                             ▼
                    ┌────────────────┐
                    │  JSON Storage  │
                    │  /data/*.json  │
                    └────────────────┘
```

### Pages Existantes

| Page | Route | Fonction Actuelle | Utilité Réelle |
|------|-------|-------------------|----------------|
| Dashboard | `/` | Vue d'ensemble avec KPIs et Top 3 Signaux/Risques | 🟢 Bonne |
| Market Brief | `/brief` | Briefs quotidiens/hebdomadaires | 🟡 Moyenne |
| Forecasts | `/forecasts` | Liste de prévisions ML+LLM | 🔴 Faible |
| Stocks | `/stocks` | Prix et graphiques | 🟡 Moyenne |
| Macro | `/macro` | Données macroéconomiques | 🔴 Faible |
| News | `/news` | Flux d'actualités | 🟡 Moyenne |
| Copilot | `/copilot` | Interface LLM Q&A | 🟢 Bonne |
| Backtests | `/backtests` | Résultats de backtesting | 🔴 Faible |
| LLM Judge | `/judge` | Évaluation LLM | 🔴 Très faible |

---

## 👤 User Journeys Critiques

### Persona Cible : Trader/Investisseur Actif

**Objectifs Principaux**
1. Identifier rapidement les meilleures opportunités d'investissement
2. Comprendre les risques majeurs du marché
3. Prendre des décisions éclairées basées sur des données fiables
4. Suivre l'évolution de son portefeuille ou watchlist

### Journey #1 : "Trouver un signal d'achat aujourd'hui"

**Scénario** : L'utilisateur ouvre l'app le matin pour identifier des opportunités de trading

#### Flow Actuel
```
1. Ouvre Dashboard (/dashboard)
   ❌ Voit "Top 3 Signaux" mais sans explication claire
   ❌ Données parfois vides ou cryptiques
   ❌ Ne comprend pas le "composite score"

2. Clique sur Forecasts (/forecasts)
   ❌ Voit une table avec ticker, horizon, score, dir, conf, ER
   ❌ Données techniques sans contexte
   ❌ Pas de recommandation claire
   ❌ Bugs fréquents si données vides

3. Vérifie les News (/news)
   ❌ Articles sans lien clair avec les signaux
   ❌ Sentiment scores peu expliqués
   ❌ Manque de filtrage par ticker

RÉSULTAT : Confusion, perte de temps, décision non prise
```

#### Flow Idéal
```
1. Ouvre Dashboard (/dashboard)
   ✅ Voit immédiatement 3-5 opportunités classées
   ✅ Chaque signal a une explication claire en français
   ✅ Indicateurs visuels (🟢 Fort, 🟡 Moyen, 🔴 Risqué)
   ✅ Lien direct vers détails et graphique

2. Clique sur un signal pour approfondir
   ✅ Page dédiée avec graphique + contexte
   ✅ Raison du signal (technique + fondamental + news)
   ✅ Niveau de risque et horizon recommandé
   ✅ Bouton d'action clair

3. Consulte les actualités liées
   ✅ News filtrées pour ce ticker
   ✅ Impact sentiment clairement indiqué
   ✅ Timeline des événements récents

RÉSULTAT : Décision éclairée en 2-3 minutes
```

### Journey #2 : "Comprendre les risques du marché"

#### Flow Actuel
```
1. Ouvre Market Brief (/brief)
   ❌ "Top 3 Risques" affichés mais peu contextualisés
   ❌ Données macro pas reliées aux risques
   ❌ Pas de niveau de gravité

2. Consulte Macro (/macro)
   ❌ Tableau de séries temporelles incompréhensible
   ❌ Pas d'explication des indicateurs
   ❌ Manque de visualisation

RÉSULTAT : Information non exploitable
```

#### Flow Idéal
```
1. Ouvre Risk Dashboard (nouveau)
   ✅ Niveau de risque global visible (Gauge)
   ✅ Top 3-5 risques avec explication
   ✅ Impact potentiel sur portefeuille type
   ✅ Actions recommandées (hedging, diversification)

2. Approfondit un risque
   ✅ Historique et contexte
   ✅ Indicateurs macro reliés
   ✅ Tickers les plus exposés
   ✅ Stratégies de mitigation

RÉSULTAT : Compréhension claire et actions possibles
```

### Journey #3 : "Suivre mes tickers favoris"

#### Flow Actuel
```
❌ INEXISTANT - Pas de watchlist personnalisée
❌ Obligation de filtrer manuellement partout
❌ Pas de sauvegarde des préférences
```

#### Flow Idéal
```
1. Configure sa watchlist (une fois)
   ✅ Sélection de tickers
   ✅ Préférences de notification
   ✅ Sauvegarde locale

2. Dashboard personnalisé
   ✅ Vue centrée sur mes tickers
   ✅ Alertes automatiques
   ✅ Performance relative
   ✅ Signaux filtrés

RÉSULTAT : Suivi efficace et personnalisé
```

---

## 🔴 Pain Points Identifiés

### Catégorie 1 : Bugs UI et Stabilité

| Bug | Page Affectée | Cause Racine | Impact | Statut |
|-----|---------------|--------------|--------|--------|
| Crash si forecasts vide | /forecasts | Pas de guard sur `.map()` | 🔴 Critique | ⚠️ Connu |
| Loading infini | /brief weekly | Endpoint lent (8+ min) | 🔴 Critique | ⚠️ Connu |
| Données undefined | Multiple | Backend retourne null au lieu de [] | 🟠 Haute | ⚠️ Partiellement corrigé |
| Timestamp invalides | Multiple | Format datetime inconsistant | 🟡 Moyenne | ⚠️ Non traité |
| Erreurs CORS sporadiques | Toutes | Config proxy Vite instable | 🟡 Moyenne | ✅ Résolu |

### Catégorie 2 : UX/UI Design

| Problème | Description | Impact Utilisateur |
|----------|-------------|-------------------|
| **Overload d'information** | Trop de métriques techniques sans hiérarchie | Confusion, paralysie décisionnelle |
| **Jargon technique** | "RSI", "MACD", "composite_score" sans explication | Courbe d'apprentissage élevée |
| **Manque de guidage** | Pas de call-to-action claire | Utilisateur perdu |
| **Design inconsistant** | Styles inline variables, pas de design system | Manque de professionnalisme |
| **Feedback utilisateur absent** | Pas de confirmations, pas de messages de succès | Incertitude |
| **Navigation non intuitive** | Menu plat sans groupement logique | Inefficacité |
| **Mobile non optimisé** | Layout desktop only | Inutilisable sur mobile |

### Catégorie 3 : Qualité et Pertinence des Données

| Problème | Exemple | Conséquence |
|----------|---------|-------------|
| **Données brutes sans contexte** | "Score: 0.73" → Qu'est-ce que ça signifie ? | Incompréhension |
| **Pas de comparaison** | Une prévision isolée sans benchmark | Pas de référentiel |
| **Manque de tendance** | Valeurs ponctuelles sans évolution | Pas de perspective |
| **Explications absentes** | Direction "up" sans justification | Manque de confiance |
| **Données obsolètes** | Freshness badge mais pas de reload auto | Information périmée |
| **Métriques non actionnables** | Indicators sans recommandation | Valeur limitée |

---

## 📊 Analyse de la Qualité des Données

### Évaluation par Endpoint

#### ✅ `/api/dashboard/kpis` - **Qualité : Bonne**
- **Forces** : Structure claire, filtres fonctionnels, top signaux/risques pertinents
- **Faiblesses** : Manque d'explication des scores, pas de tendance historique
- **Recommandation** : Ajouter explications + graphiques d'évolution

#### 🟡 `/api/forecasts` - **Qualité : Moyenne**
- **Forces** : Système hybride ML+G4F implémenté, données structurées
- **Faiblesses** :
  - Données trop techniques (final_score, confidence, expected_return)
  - Pas d'explication des prévisions
  - Manque de contexte (pourquoi cette prévision ?)
  - Pas de comparaison avec benchmark
- **Recommandation** : Enrichir avec explications, ajouter contexte marché, simplifier présentation

#### 🟡 `/api/brief/daily` et `/api/brief/weekly` - **Qualité : Moyenne**
- **Forces** : Top signaux/risques identifiés, sources citées
- **Faiblesses** :
  - Weekly brief trop lent (8+ minutes)
  - Manque de synthèse exécutive
  - Pas de recommandations d'action
  - Picks sans justification claire
- **Recommandation** : Cacher calcul, ajouter synthèse, expliquer picks

#### 🔴 `/api/macro/series` - **Qualité : Faible**
- **Forces** : Données réelles (FRED)
- **Faiblesses** :
  - Liste brute de séries sans interprétation
  - Pas de visualisation
  - Codes series non explicites (CPI, VIX, etc.)
  - Manque d'analyse tendancielle
- **Recommandation** : Retravailler complètement l'interface, ajouter graphiques, interpréter tendances

#### 🟡 `/api/news/feed` - **Qualité : Moyenne**
- **Forces** : Flux RSS réel, sentiment scoring
- **Faiblesses** :
  - Articles pas filtrables par ticker
  - Sentiment score peu expliqué
  - Pas de catégorisation
  - Manque de hiérarchisation (impact)
- **Recommandation** : Ajouter filtres, expliquer scores, catégoriser par impact

#### 🔴 `/api/stocks/prices` - **Qualité : Faible**
- **Forces** : Données yfinance, downsampling LTTB
- **Faiblesses** :
  - Graphique brut sans overlays utiles
  - Pas d'indicateurs techniques visibles
  - Manque de comparaison multi-tickers
  - Pas d'annotations (événements, signaux)
- **Recommandation** : Ajouter overlays (MA, Bollinger), annotations, comparaison

#### 🔴 `/api/backtests` - **Qualité : Très faible**
- **Forces** : Structure prévue
- **Faiblesses** :
  - Résultats peu clairs
  - Pas de métriques standards (Sharpe, max drawdown, etc.)
  - Manque de visualisation performance
  - Pas de comparaison avec benchmark (SPY)
- **Recommandation** : Retravailler complètement avec métriques quant standard

---

## 🎯 Vision Produit Cible

### Philosophie de Design

**De "Data Display" à "Decision Support"**

L'application doit passer d'un **tableau de bord de données** à un **assistant de décision d'investissement**.

### Principes Directeurs

1. **Clarity First** : Chaque donnée affichée doit avoir un sens clair pour l'utilisateur
2. **Actionability** : Chaque insight doit mener à une action possible
3. **Context is King** : Jamais de métrique isolée sans contexte ou comparaison
4. **Progressive Disclosure** : Vue d'ensemble → Détails → Analyse approfondie
5. **Trust through Transparency** : Toujours expliquer d'où viennent les données et comment elles sont calculées

### Architecture d'Information Cible

```
┌─────────────────────────────────────────┐
│          DASHBOARD PRINCIPAL            │
│  ┌──────────────┐  ┌─────────────────┐  │
│  │ Market Pulse │  │ My Watchlist    │  │
│  │ 🟢🟡🔴       │  │ (personnalisé)  │  │
│  └──────────────┘  └─────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  Top 5 Opportunities Today       │   │
│  │  1. NVDA ⬆️ +15% potential       │   │
│  │     "Strong momentum + earnings" │   │
│  │  2. ...                          │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  Key Risks to Watch              │   │
│  │  ⚠️ Yield curve inversion        │   │
│  │  📉 VIX spike detected           │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
         │
         ├─▶ Market Intelligence
         │   ├─ Macro Overview (simplifié)
         │   ├─ Sector Rotation
         │   └─ Market Sentiment
         │
         ├─▶ Stock Analysis
         │   ├─ Ticker Deep Dive
         │   ├─ Comparison Tool
         │   └─ Screener (filtres avancés)
         │
         ├─▶ Signals & Forecasts
         │   ├─ Trading Signals (buy/sell/hold)
         │   ├─ ML Predictions (expliquées)
         │   └─ Risk Alerts
         │
         ├─▶ Portfolio (nouveau)
         │   ├─ Performance Tracking
         │   ├─ Risk Metrics
         │   └─ Optimization Suggestions
         │
         └─▶ Research & Tools
             ├─ Copilot AI Assistant
             ├─ News & Events
             ├─ Backtesting Lab
             └─ Learn (glossaire, tutoriels)
```

### Wireframes Conceptuels

#### Dashboard Principal (Vision)

```
┌─────────────────────────────────────────────────────────────┐
│  Finance Copilot                    🔔 Alerts  ⚙️ Settings  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │ Market Status    │  │ Portfolio Value  │  │ Daily P&L  │ │
│  │ 🟢 Bullish      │  │ $125,430         │  │ +$2,345   │ │
│  │ Trend: ⬆️ +2.1%│  │ ⬆️ +1.87%       │  │ 🟢 +1.9%  │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🎯 Top 5 Opportunities Today                          │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 1. NVDA  ⬆️ Strong Buy  [Score: 8.7/10]              │  │
│  │    "AI chip demand + bullish breakout"                │  │
│  │    Expected: +15-20% (30 days)  Risk: Medium          │  │
│  │    [View Details] [Add to Watchlist]                  │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 2. AAPL  ⬆️ Buy  [Score: 7.2/10]                     │  │
│  │    "Earnings beat + institutional buying"             │  │
│  │    Expected: +8-12% (30 days)  Risk: Low              │  │
│  │    [View Details] [Add to Watchlist]                  │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ ... (3 more)                                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚠️ Risk Alerts                                        │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 🔴 High: Yield curve inversion deepening             │  │
│  │    Impact: Recession risk increased to 35%            │  │
│  │    Action: Consider defensive sectors (Healthcare)    │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 🟡 Medium: VIX spiked to 22 (+15% today)             │  │
│  │    Impact: Market volatility elevated                 │  │
│  │    Action: Review stop-loss levels                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────┐  ┌─────────────────────────────────┐   │
│  │ My Watchlist   │  │ Recent Signals                  │   │
│  │ • AAPL  +1.2% │  │ • SPY: Neutral (no change)      │   │
│  │ • NVDA  +3.5% │  │ • QQQ: Bullish confirmation     │   │
│  │ • TSLA  -0.8% │  │ • AAPL: Buy signal triggered    │   │
│  │ [Manage]       │  │ [View All Signals]              │   │
│  └────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### Ticker Deep Dive (Vision)

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard        NVDA - NVIDIA Corporation        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📊 Price Chart (6M)                          $875.43  │   │
│  │                                              ⬆️ +3.5% │   │
│  │     ┌───────────────────────────────────┐             │   │
│  │ 900 │         ╱╲    ╱                  │             │   │
│  │ 850 │      ╱─    ╲╱   ╱───●            │ ← Current   │   │
│  │ 800 │   ╱─                              │             │   │
│  │ 750 │ ╱                                 │             │   │
│  │     └───────────────────────────────────┘             │   │
│  │       Jun   Jul   Aug   Sep   Oct   Nov              │   │
│  │                                                        │   │
│  │ [Overlays: ✓ MA20  ✓ MA50  ✓ Bollinger  □ Volume]    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │ 🎯 Current Signal        │  │ 📈 Technical Summary    │  │
│  │ ⬆️ STRONG BUY           │  │ RSI: 68 (Bullish)       │  │
│  │ Score: 8.7/10            │  │ MACD: Positive cross    │  │
│  │ Confidence: High (85%)   │  │ MA Trend: ⬆️ Strong    │  │
│  │                          │  │ Support: $850           │  │
│  │ Why this signal?         │  │ Resistance: $900        │  │
│  │ • Breakout above $860    │  │                         │  │
│  │ • Volume surge (+40%)    │  │ [Full Analysis]         │  │
│  │ • Earnings beat          │  │                         │  │
│  │ • Positive AI sector     │  │                         │  │
│  │                          │  │                         │  │
│  │ Expected Return: +15-20% │  │                         │  │
│  │ Time Horizon: 30 days    │  │                         │  │
│  │ Risk Level: 🟡 Medium   │  │                         │  │
│  └─────────────────────────┘  └─────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📰 Recent News & Sentiment                           │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 🟢 "NVIDIA beats Q3 earnings, AI demand soars"       │   │
│  │    2 hours ago • Sentiment: Very Positive (+0.85)    │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 🟢 "Analysts raise NVDA price target to $950"        │   │
│  │    5 hours ago • Sentiment: Positive (+0.65)         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ 🟡 "Tech sector rotation ahead?"                     │   │
│  │    1 day ago • Sentiment: Neutral (0.10)             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │ 💡 AI Copilot Insight   │  │ 📊 Compare with         │  │
│  │                          │  │ • TSLA                  │  │
│  │ "NVDA shows strong       │  │ • AMD                   │  │
│  │  momentum backed by AI   │  │ • INTC                  │  │
│  │  chip demand. Consider   │  │                         │  │
│  │  entry near $870 with    │  │ [View Comparison]       │  │
│  │  stop-loss at $840."     │  │                         │  │
│  │                          │  │                         │  │
│  │ [Ask Copilot]            │  │                         │  │
│  └─────────────────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Composants Clés à Développer

#### 1. SignalCard Component

```tsx
<SignalCard
  ticker="NVDA"
  direction="strong_buy"
  score={8.7}
  confidence={0.85}
  reason="Breakout + Earnings beat + AI sector momentum"
  expectedReturn={{ min: 15, max: 20 }}
  horizon="30d"
  risk="medium"
  actions={['View Details', 'Add to Watchlist']}
/>
```

**Affichage** :
- Badge visuel (🟢 Strong Buy, 🟡 Hold, 🔴 Sell)
- Score simplifié (X/10)
- Explication en langage naturel
- Métriques clés contextualisées
- Call-to-action claires

#### 2. RiskAlert Component

```tsx
<RiskAlert
  level="high"
  title="Yield curve inversion deepening"
  impact="Recession risk increased to 35%"
  affectedAssets={['SPY', 'Tech sector']}
  recommendation="Consider defensive sectors (Healthcare, Utilities)"
  sources={['FRED', 'Treasury data']}
/>
```

**Affichage** :
- Niveau de gravité visuel
- Explication accessible
- Impact concret
- Actions recommandées
- Sources citées

#### 3. MarketPulse Component

```tsx
<MarketPulse
  status="bullish"
  trend={+2.1}
  indicators={{
    vix: { value: 18, status: 'low' },
    breadth: { value: 68, status: 'strong' },
    sentiment: { value: 72, status: 'optimistic' }
  }}
/>
```

**Affichage** :
- Gauge visuel (couleur)
- Tendance claire
- Indicateurs simplifiés
- Interprétation automatique

---

## 🚀 Plan d'Amélioration

### Phase 1 : Stabilisation & Fondations (2 semaines)

**Objectif** : Zero-crash UI + Data quality baseline

#### Sprint 1.1 : Stabilité UI
- [ ] **FC-STABILITY-001** : Implémenter guards sur tous les composants
- [ ] **FC-STABILITY-002** : Error boundaries React globales
- [ ] **FC-STABILITY-003** : Loading states cohérents partout
- [ ] **FC-STABILITY-004** : Fallbacks pour données manquantes

**Points** : +150

#### Sprint 1.2 : Data Quality
- [ ] **FC-DATA-001** : Audit complet de tous les endpoints
- [ ] **FC-DATA-002** : Implémenter pattern "never-empty" partout
- [ ] **FC-DATA-003** : Ajouter metadata (freshness, source, version)
- [ ] **FC-DATA-004** : Tests de contrats API

**Points** : +180

### Phase 2 : Enrichissement & Contexte (3 semaines)

**Objectif** : Données → Insights

#### Sprint 2.1 : Explications & Contexte
- [ ] **FC-UX-001** : Ajouter explications à tous les scores
- [ ] **FC-UX-002** : Contextualiser les prévisions (pourquoi ?)
- [ ] **FC-UX-003** : Ajouter tendances et évolutions
- [ ] **FC-UX-004** : Implémenter comparaisons (benchmark)

**Points** : +200

#### Sprint 2.2 : Nouveaux Composants
- [ ] **FC-COMP-001** : SignalCard component
- [ ] **FC-COMP-002** : RiskAlert component
- [ ] **FC-COMP-003** : MarketPulse component
- [ ] **FC-COMP-004** : ExplanationTooltip component

**Points** : +160

### Phase 3 : Refonte UX Majeure (4 semaines)

**Objectif** : Decision Support System

#### Sprint 3.1 : Dashboard Principal
- [ ] **FC-DASH-001** : Redesign dashboard avec vision cible
- [ ] **FC-DASH-002** : Implémenter Top Opportunities section
- [ ] **FC-DASH-003** : Implémenter Risk Alerts section
- [ ] **FC-DASH-004** : Ajouter Market Pulse widget

**Points** : +250

#### Sprint 3.2 : Ticker Deep Dive
- [ ] **FC-TICKER-001** : Page dédiée par ticker
- [ ] **FC-TICKER-002** : Graphique enrichi avec overlays
- [ ] **FC-TICKER-003** : Section signaux expliqués
- [ ] **FC-TICKER-004** : News filtrées par ticker
- [ ] **FC-TICKER-005** : AI Copilot insights intégrés

**Points** : +280

### Phase 4 : Personnalisation & Avancé (3 semaines)

**Objectif** : User-centric experience

#### Sprint 4.1 : Watchlist & Portfolio
- [ ] **FC-WATCH-001** : Système de watchlist personnalisée
- [ ] **FC-WATCH-002** : Sauvegarde préférences utilisateur
- [ ] **FC-WATCH-003** : Dashboard filtré par watchlist
- [ ] **FC-WATCH-004** : Alertes personnalisées

**Points** : +220

#### Sprint 4.2 : Design System
- [ ] **FC-DESIGN-001** : Créer design system cohérent
- [ ] **FC-DESIGN-002** : Palette de couleurs pro
- [ ] **FC-DESIGN-003** : Typography scale
- [ ] **FC-DESIGN-004** : Spacing & layout system
- [ ] **FC-DESIGN-005** : Component library (Storybook)

**Points** : +180

### Phase 5 : Performance & Polish (2 semaines)

**Objectif** : Production-ready

#### Sprint 5.1 : Optimisation
- [ ] **FC-PERF-001** : Lazy loading des pages
- [ ] **FC-PERF-002** : Code splitting intelligent
- [ ] **FC-PERF-003** : Image optimization
- [ ] **FC-PERF-004** : API response caching optimisé
- [ ] **FC-PERF-005** : Lighthouse score > 90

**Points** : +150

#### Sprint 5.2 : Documentation & Tests
- [ ] **FC-DOC-001** : User guide complet
- [ ] **FC-DOC-002** : API documentation
- [ ] **FC-DOC-003** : Component documentation
- [ ] **FC-TEST-001** : Suite de tests E2E (Playwright)
- [ ] **FC-TEST-002** : Tests d'intégration
- [ ] **FC-TEST-003** : Tests unitaires composants

**Points** : +200

---

## 📈 Métriques de Succès

### KPIs Utilisateur

| Métrique | Baseline Actuel | Cible Phase 3 | Cible Phase 5 |
|----------|----------------|---------------|---------------|
| **Time to Decision** | ~10 min | ~3 min | ~1 min |
| **Crash Rate** | ~15% des sessions | <2% | 0% |
| **User Confusion Score** | 7/10 | 4/10 | 2/10 |
| **Actionability Score** | 3/10 | 7/10 | 9/10 |
| **User Satisfaction** | 5/10 | 7/10 | 8.5/10 |

### KPIs Techniques

| Métrique | Baseline | Cible |
|----------|----------|-------|
| **Lighthouse Performance** | 60 | 90+ |
| **First Contentful Paint** | 2.5s | <1s |
| **Time to Interactive** | 5s | <2s |
| **Error Rate** | 5% | <0.1% |
| **Test Coverage** | 0% | 80%+ |
| **API Response Time** | Variable (2s-8min) | <500ms (p95) |

---

## 💡 Innovations Proposées

### 1. AI Copilot Proactif

Au lieu d'un simple chatbot, le Copilot devient un assistant proactif :

- **Auto-analysis** : Analyse automatique des signaux et génère des insights
- **Contextual suggestions** : Propose des actions basées sur le contexte utilisateur
- **Natural language alerts** : "NVDA vient de franchir un niveau clé, voulez-vous en savoir plus ?"

### 2. Smart Notifications

Système d'alertes intelligent :

- **Personnalisées** : Basées sur la watchlist et les préférences
- **Priorisées** : Par niveau d'urgence et d'impact
- **Actionnables** : Chaque alerte propose une action

### 3. Comparison Engine

Outil de comparaison multi-tickers :

- **Side-by-side** : Comparer 2-5 tickers sur tous les indicateurs
- **Relative strength** : Qui performe le mieux ?
- **Correlation analysis** : Tickers similaires ou diversification ?

### 4. Learning Center

Section éducative :

- **Glossaire** : Explication de tous les termes techniques
- **Tutorials** : Comment utiliser chaque fonctionnalité
- **Strategy guides** : Guides d'investissement

---

## 🎯 Prochaines Étapes Immédiates

### Cette Semaine (Sprint 0)

1. **Valider cette vision** avec l'équipe
2. **Prioriser** les tâches Phase 1
3. **Créer les tasks** dans TASKS_BOARD.md
4. **Assigner** les agents aux différents workstreams

### Agents Recommandés par Workstream

| Workstream | Agent Lead | Tâches |
|------------|------------|--------|
| **Stabilité UI** | CLAUDE-STABILITY-ARCHITECT | FC-STABILITY-*, FC-TEST-* |
| **Data Quality** | MICHEL-DATA-QUALITY-MANAGER | FC-DATA-*, Audits |
| **Backend Services** | ALEX-BACKEND | Services, Caching, APIs |
| **UX/UI Design** | ELISE-UI-EXPERT | FC-UX-*, FC-DESIGN-*, Components |
| **ML/Forecasts** | MAXIMILIAN-FINANCE-WIZARD | Amélioration modèles, Explainability |
| **Intégration** | LENA-INTEGRATION-RELIABILITY | Tests end-to-end, Coordination |

---

## 📎 Annexes

### A. Références

- [AGENTS.md](../AGENTS.md) - Guide principal du projet
- [TASKS_BOARD.md](../TASKS_BOARD.md) - Tâches globales
- [SCORE_AGENTS.md](../SCORE_AGENTS.md) - Système de points

### B. Captures d'écran Actuelles

_(À ajouter : screenshots de l'état actuel de chaque page)_

### C. User Research

_(À compléter : interviews utilisateurs, feedback, analytics)_

---

**Prochaine mise à jour** : 2025-11-06
**Statut** : En validation
**Feedback** : claude-stability@finance-copilot.dev
