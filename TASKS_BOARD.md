# 📣 MESSAGE AUX AGENTS — Lisez-moi et démarrez

Équipe, bienvenue dans **Finance Copilot**.
Ici on livre **du vrai**: zéro mock, zéro “quick fix” qui masque les problèmes.
Votre mission: **rendre l’app stable, rapide et alimentée par de la vraie data**.
Lisez les reviews : [text](reviews)
[➡️ Sprint V2 (plan détaillé prêt à l’emploi)](docs/product/SPRINT_V2_TASKS.md)
[📚 Dashboard templates (Mantine + Tremor) — Guide d'utilisation](docs/DASHBOARD_TEMPLATES.md)
---

## 🔥 PRIORITY BOARD — Novembre 2025

### Legend
- Effort: S (≤0.5j) • M (1–2j) • L (3–5j)
- Tous les lots ⇒ **never-empty + preuves (curl/log + screenshot) dans `proofs/<TASK>`**

---

## P0 — Brancher la donnée réelle (immédiat)

#### FC-FE-API-CONTRACT-ALIGN — Corriger les chemins API côté front *(Effort S)*
- **Why**: Les hooks `useLegacyHealth`, `useHealth`, `useStocksScreener`, `stocksService.getPrices` appellent `/health` ou `/stocks/*` sans préfixe `/api`, entraînant des 404 malgré un backend prêt. Cela casse Dashboard (HealthBar), Stocks Screener et monitoring.
- **Steps**:
  1. Mettre à jour les services/hooks pour cibler `/api/...` (ex. `useHealth` → `/api/health` & `/api/analytics/health` lorsque disponible).
  2. Faire respecter ce contrat via un helper `pathWithApiPrefix()` dans `api/client.ts` (défaut `/api`, override env pour staging/prod) + tests unitaires.
  3. Ajouter doc courte dans `copilot-app/docs/frontend/integration.md` rappelant la règle « routes FastAPI ⇒ /api/... ».
- **DoD**:
  - `curl http://localhost:5173/api/health` via proxy OK, Dashboard affiche badges sans erreur console.
  - `pnpm run typecheck` + `pnpm run build` passent.
  - Capture Dashboard + log curl déposés dans `proofs/FC-FE-API-CONTRACT-ALIGN/`.

#### FC-FE-MANTINE-V7-HARDEN — Retirer props deprecated (refs & creatable) *(Effort S)*
- **Why**: Mantine v7 rejette `creatable`, `getCreateLabel` et refs sur composants fonctionnels (`Tooltip` + `ActionIcon` wrapper), générant warnings persistants et risque de régression lors des upgrades.
- **Steps**:
  1. Mettre en place `forwardRef` sur `ActionIcon` exporté `src/ui/index.tsx` et sur `ThemeToggle` si custom wrapper nécessaire.
  2. Migrer `MultiSelect`/`Combobox` vers API v7 (`withCheckIcon`, `useCombobox`, `creatable` → `combobox.createOption`). Fichiers concernés : `StocksScreenerWidget.tsx`, éventuels duplicates (grep `creatable`).
  3. Ajouter test Playwright rapide (Stocks page) pour garantir absence de toast d’erreur.
- **DoD**: Console Vite sans warning Mantine, test UI passe, diff validé.

#### FC-FE-STOCKS-LIVE-DATA — Débrancher mocks & 404 screener *(Effort M)*
- **Why**: `useStocksScreener` tape `/stocks/screener` (inexistant) et `stocksService.search` renvoie un tableau mocké, brisant la promesse « no mocks » et empêchant la page Stocks de montrer les scores réels.
- **Steps**:
  1. Travailler avec backend pour exposer `/api/stocks/screener` & `/api/stocks/search` (contrat inspiré de `docs/INTEGRATION_PLAN.md`), ou adapter le front sur endpoint existant + doc.
  2. Remplacer les mocks par véritable appel TanStack Query + états Loading/Empty/Errored.
  3. Ajouter preuve via `curl` + screenshot page `/stocks` affichant résultats.
- **DoD**: `/stocks` affiche données réelles sans 404; `pnpm run typecheck` OK; preuve déposée.

#### FC-API-FORECASTS-REAL — Forecasts branchés backend *(Effort M)*
- **Why**: Remplacer les mocks par les vraies prévisions pour `/forecasts` (liste + détail).
- **Inputs**: `GET /api/forecasts`, `GET /api/forecasts/:id` (cf. spec ci-dessous).
- **Steps**:
  1. Implémenter `src/services/forecasts.ts` + `src/hooks/useForecasts.ts` (TanStack Query, ensureArray, fallback env).
  2. Brancher `Forecasts.tsx` (table + panneau détail) sur le hook, supprimer mock local.
  3. Bouton “Rafraîchir” qui refetch + badge Freshness alimenté par le payload backend.
- **DoD**:
  - Page affiche ≥1 ligne en mode backend, état vide propre quand aucun résultat.
  - `pnpm run typecheck` + `pnpm run build` OK.
  - Preuves: `curl /api/forecasts`, screenshots (liste + détail) dans `proofs/FC-API-FORECASTS-REAL/`.

#### FC-API-MACRO-REAL — Macro séries FRED/VIX *(Effort M)*
- **Why**: Les graphs macro doivent refléter CPI, VIX, 10Y-2Y, chômage réels.
- **Steps**:
  1. Service `fetchMacroSeries(codes)` + hook `useMacroSeries`.
  2. `Macro.tsx`: ring progress + charts Tremor alimentés par data réelle, sélecteur période (YTD/1Y/5Y).
  3. Badge Freshness + état vide/erreur soigné.
- **DoD**: Charts = data backend (aucune valeur en dur). Preuves: JSON `macro_series.json` + capture.

#### FC-API-NEWS-REAL — Flux news + sentiment *(Effort M)*
- **Why**: Fournir le flux agrégé backend (tickers, since, score) sans crash.
- **Steps**:
  1. Service `fetchNews` + hook `useNews` (support `VITE_USE_MOCKS`).
  2. `NewsFeed.tsx`: cartes avec sentiment chip, timeago, filtres actifs.
  3. Gestion erreurs, bouton “Charger plus” si backend le permet.
- **DoD**: `/news` affiche ≥5 articles réels, empty state propre, aucun `length` crash. Preuves: `curl /api/news` + screenshot.

---

#### FC-UI-NEWS-HOOKS — NewsFeed branché au hook TanStack *(Effort M)*
- **Why**: `NewsFeed.tsx` destructure `useNews()` comme un store custom (`items`, `filters`, `loadMore`…), ce qui casse le runtime et `pnpm run typecheck`.
- **Steps**:
  1. Conserver `useNews` (UseQueryResult) et déplacer la gestion des filtres/pagination dans `NewsFeed` via `useState` + `refetch`.
  2. Alimenter les cartes depuis `data?.articles`, utiliser `isLoading` / `error` / `refetch` pour les états.
  3. Couvrir les états Loading/Empty/Error/Freshness (Mantine + composants existants).
- **DoD**: `/news` tourne sans erreur console; `pnpm run typecheck` ne remonte plus les 9 erreurs NewsFeed; capture UI (articles + filtres actifs).
- **Proof**: log typecheck + screenshot.

#### FC-UI-REMOVE-MUI — Supprimer le vestige MUI (`SourceTooltip`) *(Effort S)*
- **Why**: `src/components/ui/SourceTooltip.tsx` importe `@mui/*`, interdit (cf. `UI_PROCESS_IMPROVEMENTS`) et casse tsc faute de types.
- **Steps**:
  1. Réécrire le composant avec Mantine Tooltip (ou supprimer si inutilisé).
  2. Retirer `@mui/*` des deps & lockfile, ajouter règle ESLint `no-restricted-imports` si absente.
  3. Vérifier que les pages news/brief utilisent le nouveau composant.
- **DoD**: `rg \"@mui/\"` → 0; `pnpm run typecheck` passe cette étape; ESLint bloque toute régression.
- **Proof**: log typecheck + diff ESLint.

#### FC-BUILD-ENV-TYPES — Déclarations `import.meta.env` fiables *(Effort S)*
- **Why**: `src/config/env.ts` déclenche 3 erreurs TS (`ImportMetaEnv` incomplet), bloquant CI.
- **Steps**:
  1. Ajouter `src/vite-env.d.ts` (ou équivalent) avec interface `ImportMetaEnv` (API_BASE, USE_MOCKS, ENABLE_SSE).
  2. Documenter la convention dans `docs/dev/ui_migration_mantine.md`.
  3. Vérifier `pnpm run typecheck`.
- **DoD**: Les erreurs `ImportMetaEnv` disparaissent; doc à jour.
- **Proof**: log typecheck + snippet doc.

#### FC-API-STOCKS-SEARCH-REAL — Recherche actions sans mock *(Effort M)*
- **Why**: `stocksService.search` renvoie une liste mockée (AAPL/MSFT hardcodés), contraire à la règle « no mocks » et génère des signaux erronés.
- **Steps**:
  1. Exposer un endpoint backend (`GET /stocks/search?q=`) ou, à défaut, réutiliser `/stocks/universe` + filtrage réel (aucun tableau mock).
  2. Supprimer le tableau `mockResults`, gérer le cas 0 résultat avec `EmptyState` + CTA “élargir la requête”.
  3. Couvrir par un test (unit/service + Playwright) montrant qu’un ticker réellement suivi (ex: `NVDA`) est proposé.
- **DoD**: `rg "mockResults"` → 0; page Stocks affiche résultats backend + état vide propre; curl `/api/stocks/search?q=AAPL` figure dans les preuves.
- **Proof**: log tests + screenshot recherche + captures curl.

#### FC-UI-BRIEF-MANTINE — Refonte Market Brief Mantine/Tremor *(Effort M)*
- **Why**: `MarketBrief.tsx` utilise encore layout legacy (inline styles, boutons custom, `<select>` brut) en contradiction avec la vision Mantine.
- **Steps**:
  1. Remplacer layout par composants Mantine (`Stack`, `Card`, `SegmentedControl`, `MultiSelect`) + stylage thème.
  2. Normaliser Loading/Empty/Error + `FreshnessBadge` partagé; conserver bannière fallback mais via `Alert` Mantine.
  3. Brancher la sélection d’univers sur un refetch réel et loguer si backend ignore le param (note PO dans preuve).
- **DoD**: `rg 'backgroundColor' MarketBrief.tsx` → 0; Playwright `/brief` vert; screenshots avant/après + log réseau.
- **Proof**: Diff + vidéo toggle quotidien/hebdo + traces refetch.

---

## P1 — Copilot & Backtests (48–72h)

#### FC-COPILOT-SSE — Copilot streaming avec contexte *(Effort M)*
- **Why**: Offrir un copilote LLM contextualisé (prévision sélectionnée, filtres actifs).
- **Steps**:
  1. Implémenter `askCopilotSSE` (SSE ou fetch stream) + gestion abort.
  2. `Copilot.tsx`: zone chat, boutons rapides (“Explique la prévision”, “Risques & invalidation”), affichage streaming incremental.
  3. Gestion erreurs/réessai + log simple (optionnel) pour audits.
- **DoD**: Démo streaming (GIF/vidéo), transcript sauvegardé. Preuves: capture vidéo + log dans `proofs/FC-COPILOT-SSE/`.

#### FC-BACKTESTS-REAL — Résumé & equity curve *(Effort M)*
- **Why**: Montrer performance réelle (CAGR, maxDD, win rate, equity) pour les backtests.
- **Steps**:
  1. Service/hook `useBacktest(params)`.
  2. `Backtests.tsx`: cartes KPI + courbe Tremor + empty/erreur soigné, bouton “Recalculer”.
  3. Stocker JSON brut dans `proofs/` pour audit.
- **DoD**: KPI cohérents, courbe visible. Preuves: screenshot + JSON `backtest_<date>.json`.

---

## P2 — Hardening & Toggles (72–96h)

#### FC-MOCK-TOGGLE — Fallback mocks via env *(Effort S)*
- **Why**: Ne jamais casser l’UI si backend HS; dev rapide.
- **Steps**:
  1. Lire `VITE_USE_MOCKS` dans services, router vers MSW/mock si true.
  2. Documenter dans `docs/dev/ui_migration_mantine.md` (section “Mocks & SSE”).
- **DoD**: Mode mock ON sert des données locales sans crash; OFF = backend. Preuves: notes + capture.

#### FC-OBS-FRESHNESS — Harmoniser badges Freshness *(Effort S)*
- **Why**: Garantir cohérence freshness (forecasts, macro, news, backtests).
- **Steps**:
  1. Uniformiser `FreshnessBadge` (minutes + tooltip).
  2. Vérifier `/health` expose `last_updates` pour routes branchées.
- **DoD**: Badge indique minutes depuis dernier update (capture + log `/health`).

---

## P3 — Sprint V2 (ML / Data)

- **V2-ML-001 — Probabilistic Forecasts (Quantiles + Calibration)** *(L)*
- **V2-ML-002 — Regime & Drift Detection** *(M)*
- **V2-DATA-001 — Filings & Transcripts** *(L)*
- **V2-DATA-002 — Alt-Data (Options Flow, Short Interest)** *(L)*
- **V2-API-001 — Live Updates (SSE/WebSocket)** *(M)*
- **V2-OPS-001 — OpenTelemetry + SLOs** *(M)*

*Referencing docs/product/SPRINT_V2_TASKS.md pour détails ML/OPS.*

---

### Rappels DoD globaux
- Tests: `pnpm run typecheck` + `pnpm run build`.
- Smoke Playwright: `/`, `/forecasts`, `/macro`, `/news` (au moins composant clé rendu).
- Preuves à déposer dans `proofs/<TASK>/` (curl/log + screenshots ou GIF streaming).
- Documenter tout toggle/env dans `docs/dev/ui_migration_mantine.md` (ajouter section “Mocks & SSE”).
## FC-NEW-021 — Robustness Scoring & PDF Export (Frontend)

**Status**: AVAILABLE to claim

**But**: Implémenter le système de scoring robustesse avec export PDF et panel de tuning comme spécifié dans la spécification détaillée du 2025-11-05.

**Fichiers**

* `frontend/webapp/src/lib/robustScore.ts`
* `frontend/webapp/src/ui/Ring.tsx` 
* `frontend/webapp/src/components/metrics/RobustnessScoreCard.tsx`
* `frontend/webapp/src/utils/exportPdf.ts`
* `frontend/webapp/src/components/report/ExportReportButton.tsx`
* `frontend/webapp/src/components/tuner/PresetTunerPanel.tsx`
* `frontend/webapp/src/api/backtests.ts`
* `frontend/webapp/src/pages/Backtests.tsx` (intégration)

**Étapes**

1. **Implémentation du scoring robustesse**:
   - Créer `robustScore.ts` avec les fonctions de scoring CAGR, Drawdown, WinRate, Trades
   - Calculer le score total et la notation (S, A, B, C, D, E)

2. **Composant graphique Ring**:
   - Créer wrapper Mantine pour RingProgress avec style cohérent
   - Intégration avec la lib de scoring robustesse

3. **Carte de score Robustness**:
   - Créer composant RobustnessScoreCard qui affiche le ring + détails
   - Utiliser les couleurs appropriées selon le score

4. **Export PDF**:
   - Ajouter dépendances: `jspdf html2canvas`
   - Créer utilitaire `exportPdf.ts` avec html2canvas + jsPDF
   - Bouton export pour cibler n'importe quelle section

5. **Panel de Tuning**:
   - Créer PresetTunerPanel avec interface pour tester variantes backtests
   - Intégration avec API backtests
   - Affichage des résultats avec les scores de robustesse

6. **Intégration**:
   - Intégrer les composants dans la page Backtests.tsx
   - S'assurer que les patterns never-empty sont respectés

**DoD**

* Système de scoring robustesse opérationnel sur la page Backtests
* Bouton d'export PDF fonctionnel pour exporter n'importe quelle section
* Panel de tuning permettant d'explorer plusieurs variantes de paramètres
* 4 composants UI (Card, Ring, ExportButton, TunerPanel) prêts à être réutilisés
* Protection contre crashes avec helpers never-empty (ensureArray, etc.)
* UI fully responsive et accessible# 📊 DASHBOARD INTEGRATION PLAN - Tasks Division

This document outlines the tasks required to implement the new Dashboard with:
- Complete filters (Horizon, Universe, Themes)
- Macro sparklines (CPI & VIX AreaChart)
- Forecast cards (Top 5 + directional donut)
- News section
- Freshness system
- Never-empty protections

## FC-DASH-001 — Dashboard Component Implementation (MUI version - OBSOLETE)
**Status**: OBSOLETE (migré à Mantine+Tremor)
**Owner**: Multiple agents (LENA initially, transitionné)

**But**: Implémentation initiale du Dashboard avec MUI. Cette tâche est maintenant obsolète suite à la directive de migration vers Mantine + Tremor.

**Fichiers**
* `frontend/webapp/src/pages/Dashboard.tsx` (ancienne version MUI supprimée)
* Anciennement: MUI components (`@mui/*`)

**Historique**
- Initialement implémenté avec MUI
- Supprimé par LENA-LLM-STRATEGIST-WONDERWOMAN-21 dans le cadre de la migration UI
- Remplacé par nouvelle implémentation Mantine+Tremor (voir notes ci-dessous)

**Statut**: REMPLACÉ par nouvelle directive UI: Mantine + Tremor

---

## FC-DASH-002 — Dashboard Mantine+Tremor (Nouvelle implémentation)
**Status**: DONE by MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
**Owner**: MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23

**But**: Implémenter le Dashboard avec Mantine + Tremor, filtres et layout comme spécifié dans la directive UI du 2025-11-05.

**Fichiers**
* `frontend/webapp/src/pages/Dashboard.tsx` (nouvelle implémentation avec Mantine/Tremor)
* `frontend/webapp/src/components/ui/FreshnessBadge.tsx` (intégration requise)
* `frontend/webapp/src/lib/safe.ts` (helpers never-empty)
* `frontend/webapp/src/hooks/useForecasts.ts` (intégration avec filtres)
* `frontend/webapp/src/hooks/useMacroSeries.ts` (intégration avec sparklines)
* `frontend/webapp/src/hooks/useNews.ts` (intégration avec actualités)

**Étapes**
1. Création de la structure Dashboard avec Mantine + Tremor:
   - Grid Mantine pour layout responsive
   - Components Tremor: BarList, DonutChart, AreaChart
   - Intégration avec `@/ui` wrappers

2. Implémentation des filtres avancés:
   - SegmentedControl pour Horizon (court/moyen/long)
   - MultiSelect pour Univers (tickers multiples)
   - Thèmes (ex: growth, value, momentum)

3. Intégration macro sparklines:
   - AreaChart Tremor pour CPI et VIX
   - Système de badge fraîcheur
   - Données historiques formatées pour Tremor

4. Sections prévisions et news:
   - BarList Tremor pour Top 5 prévisions
   - Donut Chart pour répartition directionnelle
   - Section news avec sentiments
   - Protection never-empty (skeletons, empty states)

**DoD**
* Dashboard.tsx fonctionnel avec Mantine + Tremor
* Filtres interactifs propagés aux hooks de données
* Macro sparklines fonctionnelles (AreaChart Tremor)
* Prévisions affichées via BarList et DonutChart Tremor
* News section avec sentiment scoring
* Layout responsive avec Mantine Grid
* Tous les composants UI sécurisés (never-empty patterns)
* Aucun crash si données manquantes (safe access helpers)

---

## FC-DASH-002 — Hooks Data & API Integration
**Status**: CLAIMED
**Owner**: ALEX-FINANCE-ANALYST-SUPERMAN-29

**But**: Créer les hooks React et les endpoints API pour alimenter le Dashboard.

**Fichiers**
* `frontend/webapp/src/hooks/useForecasts.ts`
* `frontend/webapp/src/hooks/useMacroSeries.ts`
* `frontend/webapp/src/hooks/useNews.ts`
* `backend/api/routes/forecasts.py`
* `backend/api/routes/macro.py`
* `backend/api/routes/news.py`

**Claimed by**: ALEX-FINANCE-ANALYST-SUPERMAN-29

**Étapes**
1. **Frontend Hooks**:
   - Créer `useForecasts(options: { horizon, universe, themes })`
   - Créer `useMacroSeries(ids: string[])` pour CPI, VIX
   - Créer `useNews(options: { universe, limit })` avec sentiment si dispo
   - Utiliser `ensureArray`, `nn` pour never-empty

2. **API Endpoints**:
   - `/api/forecasts?horizon=short|medium|long&universe=SPY,QQQ&themes=growth,value,etc.`
   - `/api/macro/series?ids=CPIAUCSL,VIXCLS`
   - `/api/news?universe=SPY,QQQ&limit=6`

**DoD**
* Hooks utilisent les patterns never-empty (skeletons, fallbacks)
* Endpoints retournent structures conformes avec {ok, data} 
* Filtres du Dashboard propagent correctement aux appels API
* Aucun crash UI si hooks échouent

---

## FC-DASH-003 — Macro Sparklines (AreaChart Tremor)
**Status**: AVAILABLE to claim
**Owner**: Frontend team

**But**: Implémenter les graphiques macro avec AreaChart Tremor et badges de fraîcheur.

**Fichiers**
* `frontend/webapp/src/components/charts/MacroAreaChart.tsx`
* `frontend/webapp/src/components/ui/FreshnessBadge.tsx`
* `frontend/webapp/src/pages/Dashboard.tsx`

**Étapes**
1. Créer composant `MacroAreaChart` avec Tremor AreaChart:
   - Supporte CPI, VIX, et autres séries macro
   - Responsive design
   - Tooltips et interactions
   - Gestion de loading/error/empty states

2. Intégrer FreshnessBadge pour chaque série:
   - Affiche dernière mise à jour
   - Couleur selon fraîcheur (green/fresh, yellow/stale, red/old)
   - Position dans le coin du chart

3. Connecter aux données réelles via useMacroSeries

**DoD**
* AreaCharts fonctionnels pour CPI et VIX (ou autres)
* Badges de fraîcheur visibles et correctement colorés
* Charts stylés avec Tremor + Mantine
* Aucun crash si données macro manquantes

---

## FC-DASH-004 — Forecast Cards (Top 5 + Directional Donut)
**Status**: AVAILABLE to claim
**Owner**: Frontend team

**But**: Créer les cartes de prévisions avec BarList Tremor et donut directionnel.

**Fichiers**
* `frontend/webapp/src/components/forecasts/ForecastTop5.tsx`
* `frontend/webapp/src/components/forecasts/DirectionalDonut.tsx`
* `frontend/webapp/src/components/forecasts/ForecastCard.tsx`

**Étapes**
1. **Top 5 Prévisions**: 
   - BarList Tremor avec ticker, horizons, scores de prévision
   - Tri configurable (par confiance, retour attendu, etc.)
   - Couleurs selon direction (vert pour up, rouge pour down)

2. **Donut Directionnel**:
   - PieChart Tremor montrant répartition Up/Down/Flat
   - Calculé à partir des directions des prévisions
   - Légende claire avec pourcentages

3. **Carte de Prévision**:
   - Card Mantine avec ticker, horizon, direction, confidence
   - Couleur de bordure selon confiance
   - Niveau de détail configurable

4. Connecter aux données via useForecasts

**DoD**
* Top 5 affiché dans BarList responsive
* Donut directionnel montrant répartition Up/Down/Flat
* Cartes de prévision avec toutes les métadonnées
* Safe access pour éviter les crashes sur données incomplètes

---

## FC-DASH-005 — News Section & Sentiment Display
**Status**: AVAILABLE to claim
**Owner**: Frontend team

**But**: Créer la section News avec affichage de sentiment et badges.

**Fichiers**
* `frontend/webapp/src/components/news/NewsSection.tsx`
* `frontend/webapp/src/components/news/NewsCard.tsx`
* `frontend/webapp/src/components/ui/NewsSentimentBadge.tsx`

**Étapes**
1. **News Section**:
   - Layout grid/list pour les articles
   - Affichage titre, résumé, source, date
   - Sentiment score si disponible (0-1, rouge/vert pour négatif/positif)
   - Filtrage par univers si disponible

2. **News Cards**:
   - Card Mantine avec données structurées
   - Badges pour tickers mentionnés
   - Indicateur de sentiment (couleur ou icône)
   - Lien cliquable vers article original

3. **Sentiment Badge**:
   - Badge coloré selon sentiment (rouge/négatif, vert/positif, gris/neutre)
   - Valeur numérique si disponible
   - Intégration dans la structure de NewsCard

4. Connecter aux données via useNews

**DoD**
* Section News affichant articles avec sentiments
* Badges de sentiment clairement visibles
* News Cards stylées avec Mantine
* Never-empty: affichage propre même si pas d'articles

---

## FC-DASH-006 — System Refresh & Freshness Management
**Status**: AVAILABLE to claim
**Owner**: Frontend team (coordination Backend si needed)

**But**: Implémenter les badges de fraîcheur centralisée et le bouton Refresh All.

**Fichiers**
* `frontend/webapp/src/contexts/RefreshContext.tsx`
* `frontend/webapp/src/components/system/FreshnessTracker.tsx`
* `frontend/webapp/src/components/system/RefreshAllButton.tsx`
* `frontend/webapp/src/pages/Dashboard.tsx`

**Étapes**
1. **Contexte Refresh**:
   - Créer RefreshContext avec état global pour timestamps de fraîcheur
   - Système de propagation des événements de refresh

2. **Tracked de Fraîcheur**:
   - Composant centralisé qui stocke les dernières dates de mise à jour
   - Synchronisé avec les réponses API (last_update, freshness fields)
   - Mise à jour des badges de fraîcheur en conséquence

3. **Bouton Refresh All**:
   - Déclenche le refresh de toutes les données simultanément
   - Indicateur de chargement global
   - Retour visuel sur l'état du refresh

4. Intégration avec tous les composants du Dashboard

**DoD**
* Badges de fraîcheur visibles sur toutes les sections
* Bouton Refresh All fonctionnel
* Contexte de refresh propagé correctement à tous les composants
* Système never-empty: fallback si refresh échoue

---

## Coordination required between:
- ALEX-API-ARCHITECT: Endpoints API pour les nouveaux filtres
- ALEX-FINANCE-ANALYST: Logique de tri des prévisions selon filtres
- MAXIMILIAN: Modèles ML pour les prédictions basées sur filtres
- ALEX-BACKEND: Pipeline d'ingestion pour données macro
- LENA: Integration des données dans le nouveau format

---

## FC-INT-022 — Intelligence Dashboard Integration Plan
**Status**: CLAIMED by MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23

**But**: Intégration avancée des widgets existants avec les capacités LLM G4F pour créer une UI intelligente et complète qui analyse, recommande, s'adapte et explique les données.

**Fichiers**
* `backend/services/intelligence_service.py`
* `backend/services/context_service.py`
* `backend/api/routes/intelligence.py`
* `frontend/webapp/src/components/intelligence/IntelligenceDashboardWidget.tsx`
* `frontend/webapp/src/components/intelligence/SmartRecommendationsWidget.tsx`
* `frontend/webapp/src/components/intelligence/AdaptiveLayout.tsx`
* `frontend/webapp/src/hooks/useIntelligence.ts`
* `frontend/webapp/src/lib/llm_analyzer.py` (Python backend)

**Étapes**
1. **Intelligence Service**:
   - Agrège toutes les données disponibles (forecasts, macro, news, stocks)
   - Utilise LLM G4F pour analyse intelligente et insights
   - Endpoint: `/api/intelligence/snapshot` qui renvoie {insights, recommendations, market_regime, correlations}

2. **Context Service**:
   - Identifie le régime de marché (Bull, Bear, Sideways, Volatile, etc.)
   - Détermine les drivers dominants (macro vs tech vs news)
   - Recommende le layout/widget optimal à afficher selon le contexte

3. **Smart Recommendations**:
   - Génère "Top 3 actions à surveiller aujourd'hui"
   - Basé sur ML scoring + LLM ranking
   - Avec explications contextuelles

4. **Adaptive UI**:
   - Layout qui s'adapte selon le régime marché identifié
   - Widget placement dynamique (ex: Macro en avant en période volatile)
   - Priorisation automatique selon conditions actuelles

5. **Correlation Intelligence**:
   - Analyse des corrélations entre news→forecasts, macro→stocks, etc.
   - LLM explique pourquoi les actifs se comportent ensemble
   - Détecte les changements de corrélation

**DoD**
* IntelligenceDashboardWidget fonctionnel qui combine tous les widgets avec insights LLM
* Smart Recommendations avec explications contextuelles
* UI Adaptive qui change selon le régime marché
* Correlation Intelligence avec explications LLM
* Tous les services backend (intelligence/context) opérationnels
* Never-empty patterns respectés avec fallbacks intelligents
* Interface utilisateur intelligente qui "pense" et recommande
---

## FC-ROUTE-023 — Correction proxy Vite (Routing Frontend)

**Status**: CLAIMED by MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23

**But**: Corriger le fichier vite.config.ts qui redirige les routes frontend vers le backend à tort, causant des erreurs "Not Found" sur les pages critiques.

**Fichiers**
* `copilot-app/frontend/webapp/vite.config.ts`
* `copilot-app/frontend/webapp/src/router.tsx` (potentiellement à vérifier)
* `docs/routing-best-practices.md`

**Étapes**
1. **Identification du problème**:
   - Le fichier `vite.config.ts` a des règles de proxy incorrectes aux lignes 44-78
   - Routes comme `/forecasts`, `/brief`, `/macro`, `/stocks`, `/news`, `/copilot` sont redirigées vers le backend
   - Ces routes sont des routes frontend gérées par React Router, pas des endpoints backend
   - Le backend retourne `{"detail":"Not Found"}` car ces endpoints n'existent pas côté backend

2. **Correction du proxy**:
   - Retirer les règles de proxy pour les routes purement frontend: `/forecasts`, `/brief`, `/macro`, `/stocks`, `/news`, `/copilot`
   - Conserver uniquement les proxy pour les endpoints API réels: `/api/*`, `/health`
   - S'assurer que React Router gère correctement les routes frontend

3. **Validation de la correction**:
   - Tester la navigation entre toutes les pages: Dashboard, Forecasts, News, Brief, Macro, Stocks, etc.
   - Vérifier que les appels API continuent à fonctionner via le proxy `/api`
   - Confirmer que les routes frontend ne causent plus le message "Not Found"

**DoD**
* Fichier `vite.config.ts` corrigé: seuls `/api/*` et `/health` sont redirigés au backend
* Navigation frontend fonctionnelle sur toutes les routes (forecasts, brief, macro, news, etc.)
* Appels API backend toujours fonctionnels via le proxy
* Aucune erreur "Not Found" due à mauvaise redirection de routes
* Tests de navigation passent
* Preuve de fonctionnement: captures d'écran des pages après correction

**Impact critique**: 
* Cette correction résoudra les problèmes de navigation sur les pages spécifiques 
* Permettra aux utilisateurs d'accéder correctement aux différentes sections de l'application
* Éliminera les erreurs de type "Not Found" non justifiées
