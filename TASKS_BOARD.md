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
## FC-NEW-021 — Robustness Scoring & PDF Export (Frontend) - DONE

**But**: Implémenter le système de scoring robustesse avec export PDF et panel de tuning comme spécifié dans la spécification détaillée du 2025-11-05.

**Fichiers**

* `frontend/webapp/src/lib/robustScore.ts`
* `frontend/webapp/src/ui/Ring.tsx` 
* `frontend/webapp/src/components/metrics/RobustnessScoreCard.tsx`
* `frontend/webapp/src/utils/exportPdf.ts`
* `frontend/webapp/src/components/report/ExportReportButton.tsx`
* `frontend/webapp/src/components/tuner/PresetTunerPanel.tsx`
* `frontend/webapp/src/services/backtest.service.ts`
* `frontend/webapp/src/hooks/useBacktests.ts`
* `frontend/webapp/src/pages/Backtests.tsx` (intégration)

**Étapes**

1. **Implémentation du scoring robustesse**:
   - Créé `robustScore.ts` avec les fonctions de scoring CAGR, Drawdown, WinRate, Trades
   - Calcul du score total et notation (S, A, B, C, D, E)

2. **Composant graphique Ring**:
   - Créé composant Ring avec visualisation circulaire du score de robustesse
   - Intégré avec la lib de scoring robustesse

3. **Carte de score Robustness**:
   - Créé composant RobustnessScoreCard qui affiche le ring + détails
   - Utilise les couleurs appropriées selon le score

4. **Export PDF**:
   - Ajouté dépendances: `jspdf html2canvas`
   - Créé utilitaire `exportPdf.ts` avec html2canvas + jsPDF
   - Bouton export pour cibler n'importe quelle section

5. **Panel de Tuning**:
   - Créé PresetTunerPanel avec interface pour tester variantes backtests
   - Intégré avec API backtests
   - Affichage des résultats avec les scores de robustesse

6. **Intégration**:
   - Intégré les composants dans la page Backtests.tsx
   - Appliqué les patterns never-empty pour garantir stabilité UI

**DoD**

* Système de scoring robustesse opérationnel sur la page Backtests
* Bouton d'export PDF fonctionnel pour exporter n'importe quelle section
* Panel de tuning permettant d'explorer plusieurs variantes de paramètres
* 4 composants UI (Card, Ring, ExportButton, TunerPanel) prêts à être réutilisés
* Protection contre crashes avec helpers never-empty (ensureArray, etc.)
* UI fully responsive et accessible

**Completed by**: ALEX-FINANCE-ANALYST-SUPERMAN-29

**Files created/updated**:
- `frontend/webapp/src/lib/robustScore.ts` - Library for robustness scoring calculations
- `frontend/webapp/src/components/metrics/RobustnessScoreCard.tsx` - Score visualization component
- `frontend/webapp/src/components/tuner/PresetTunerPanel.tsx` - Parameter tuning panel
- `frontend/webapp/src/components/report/ExportReportButton.tsx` - PDF export functionality
- `frontend/webapp/src/utils/exportPdf.ts` - PDF export utilities
- `frontend/webapp/src/services/backtest.service.ts` - Backtest API service layer
- `frontend/webapp/src/hooks/useBacktests.ts` - React Query hooks for backtests
- `frontend/webapp/src/pages/Backtests.tsx` - Integrated backtest page with new components

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
**Status**: DONE to claim
**Owner**: Frontend team

Completed by: ALEX-API-ARCHITECT-SUPERMAN-7
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

---

## FC-API-026 — Stocks Screener (filtrage avancé)

**Status**: DONE by LENA-LLM-STRATEGIST-WONDERWOMAN-21

**But**: Endpoint `/api/stocks/screener` pour filtrage avancé de stocks avec multiples critères (secteur, capitalisation, ratios financiers, etc.).

**Fichiers**
* `backend/api/routes/stocks_extra.py`
* `backend/services/stock_screener.py` 
* `backend/models/stock_filters.py`
* `backend/storage/base.py` (système de filtrage sur les données de stock existantes)

**Étapes**
1. **Modèle de filtres**:
   - Créer modèles pour les critères de filtrage (sector, marketCap, PE, PB, Dividend Yield, etc.)
   - Valider les paramètres d'entrée (min/max ranges valides)
   - Système de tri paramétrable (par performance, volatilité, valeur, etc.)

2. **Service de screening**:
   - Charger les données de stock existantes
   - Appliquer les filtres sélectionnés
   - Retourner liste de stocks filtrée avec métadonnées
   - Inclure des métriques de performance et de risque

3. **Endpoint API**:
   - GET `/api/stocks/screener` avec query params
   - Paramètres: sector, minMarketCap, maxPE, dividendYieldMin, etc.
   - Pagination et tri intégrés

**DoD**
* `/api/stocks/screener?sector=Technology&minMarketCap=1000000000` retourne stocks filtrés
* Tous les filtres fonctionnent correctement
* Never-empty - retourne tableau même si pas de résultats (pas de null)
* Performance acceptable - < 500ms pour requête complète
* Données enrichies avec indicateurs techniques et fondamentaux

**Preuve**: Système complet de stock screener implémenté avec filtres avancés (secteur, capitalisation boursière, ratios P/E et P/B, rendement dividendes, prix, volume, volatilité, beta, ROE, croissance EPS), validation de paramètres, tri configurable, pagination, recherche full-text, intégration avec le système de cache pour garantir never-empty, et endpoints exposés via `/api/stocks/screener`.

---

## FC-API-027 — Stock Correlation Heatmap

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/stocks/heatmap` pour la matrice de corrélation entre actifs facilitant l'analyse multi-actifs.

**Fichiers**
* `backend/api/routes/stocks_extra.py`
* `backend/services/correlation_calculator.py`
* `backend/models/correlation_matrix.py`
* `backend/jobs/correlation_calculator.py`

**Étapes**
1. **Calcul de corrélation**:
   - Calculer les coefficients de corrélation (Pearson) entre paires d'actifs
   - Historique configurable (7j, 30j, 90j, 1a)
   - Sauvegarder dans `data/stocks/correlations.json`

2. **Service heatmap**:
   - Charger matrice de corrélation
   - Filtre par univers de tickers (si spécifié)
   - Format adapté pour visualisation (tremor Heatmap)

3. **Endpoint API**:
   - GET `/api/stocks/heatmap` avec paramètres de période et univers
   - Retourne structure matricielle avec coeff. de corrélation

**DoD**
* `/api/stocks/heatmap?ticker=SPY&ticker=QQQ&window=30d` retourne matrice de corrélation
* Données structurées pour intégration facile dans tremor Heatmap
* Méta-données sur la période et la fraîcheur des données
* Never-empty pattern respecté

---

## FC-API-028 — Multi-Asset Performance Table

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/stocks/performance` pour comparer les performances des différents actifs avec benchmarks.

**Fichiers**
* `backend/api/routes/stocks_extra.py`
* `backend/services/performance_calculator.py`
* `backend/models/performance_metrics.py`

**Étapes**
1. **Calcul de performance**:
   - Calculer returns (1d, 1w, 1m, 3m, 6m, 1y) pour chaque actif
   - Comparer à benchmarks (SPY, QQQ, etc.)
   - Calculer alpha, beta, sharpe ratio

2. **Service de performance**:
   - Prendre liste de tickers en entrée
   - Générer tableau de performance comparée
   - Sauvegarder snapshot pour never-empty

3. **Endpoint API**:
   - GET `/api/stocks/performance` avec paramètres de benchmark et période
   - Retourne tableau structuré pour DataGrid

**DoD**
* `/api/stocks/performance?benchmark=SPY&tickers=AAPL&tickers=MSFT` retourne tableau performance
* Toutes les mesures de performance sont présentes (returns, alpha, beta, sharpe)
* Format compatible avec DataGrid Mantine pour affichage UI
* Never-empty - retourne structure même si pas de données

---

## FC-API-029 — Economic Calendar

**Status**: DONE by LENA-LLM-STRATEGIST-WONDERWOMAN-21

**But**: Endpoint `/api/macro/calendar` pour le calendrier des événements économiques à venir.

**Fichiers**
* `backend/models/economic_calendar.py`
* `backend/jobs/calendar_ingest.py`
* `backend/routes/macro_extra.py`

**Étapes**
1. **Ingestion de calendrier**:
   - Sources: FRED, Investing.com, etc.
   - Récupérer événements à venir (nom, date, importance, consensus, réel)
   - Sauvegarder dans `data/macro/calendar.json`

2. **Service de calendrier**:
   - Filtrer par date de début/fin
   - Niveau d'importance configurable
   - Groupe par catégorie (emploi, inflation, Fed, etc.)

3. **Endpoint API**:
   - GET `/api/macro/calendar` avec filtres de période et importance
   - Retourne événements ordonnés chronologiquement
   - Inclure impact anticipé sur les marchés

**DoD**
* `/api/macro/calendar?start=2025-11-05&end=2025-11-12` retourne événements à venir
* Données incluent: titre, date/heure, importance (high/medium/low), consensus, devise
* Fraîcheur et sources dans la réponse
* Never-empty - même si pas d'événements cette semaine

**Preuve**: Calendrier économique complet implémenté avec système de récupération d'événements économiques à venir (FOMC, NFP, CPI, ECB meetings, etc.), intégration avec prédictions d'impact ML, sauvegarde persistante des données dans le système de cache, endpoint API fonctionnel avec filtres par période et importance, et garantie never-empty maintenue même en cas d'absence d'événements.

---

## FC-API-030 — News Impact Analysis

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/news/analysis` pour l'analyse détaillée des impacts des news sur les actifs.

**Fichiers**
* `backend/api/routes/news_extra.py`
* `backend/services/news_analyzer.py`
* `backend/models/news_impact.py`
* `analytics/news_impact.py`

**Étapes**
1. **Analyse d'impact**:
   - Corrélation entre news publication et mouvement prix
   - Analyse de sentiment lié à tickers spécifiques
   - Calcul de l'impact présumé sur les actifs mentionnés

2. **Service d'analyse**:
   - Charger news et données de prix historiques
   - Calculer les corrélations et impacts
   - Sauvegarder dans `data/news/impact_analysis.json`

3. **Endpoint API**:
   - GET `/api/news/analysis` avec filtres par ticker et période
   - Retourne scores d'impact et corrélations

**DoD**
* `/api/news/analysis?ticker=NVDA&window=7d` retourne impact analysis
* Données incluent: impact_score, sentiment_change, price_correlation, relevance_score
* Compatible avec affichage dans UI pour news sentiment analysis
* Never-empty - retourne structure même si pas d'impacts significatifs

---

## FC-API-031 — Risk Analytics Dashboard

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/analytics/risks` pour l'analyse des risques de portefeuille (VaR, Beta, Corrélation).

**Fichiers**
* `backend/api/routes/analytics.py`
* `backend/services/risk_calculator.py`
* `backend/models/risk_metrics.py`
* `analytics/risk_analytics.py`

**Étapes**
1. **Calcul de risque**:
   - Value at Risk (VaR) historique et paramétrique
   - Beta par rapport au marché (SPY)
   - Corrélations entre actifs
   - Volatilité implicite/explicite

2. **Service de risque**:
   - Calculer métriques pour portefeuille ou actifs spécifiés
   - Sauvegarder snapshots dans `data/analytics/risks.json`
   - Gestion de la fraîcheur des données

3. **Endpoint API**:
   - GET `/api/analytics/risks` avec paramètres de portefeuille
   - Retourne ensemble complet de métriques de risque

**DoD**
* `/api/analytics/risks?ticker=SPY&ticker=QQQ` retourne métriques de risque
* Données incluent: VaR, Beta, Sharpe, Volatilité, Corrélations
* Format prêt pour intégration UI dans dashboard de risque
* Never-empty - même si données limitées

---

## FC-API-032 — Prediction Accuracy Analytics

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/analytics/predictions` pour les statistiques de performance des prédictions (accuracy, hit-rate).

**Fichiers**
* `backend/api/routes/analytics.py`
* `backend/services/prediction_analyzer.py`
* `backend/models/accuracy_metrics.py`
* `analytics/prediction_accuracy.py`

**Étapes**
1. **Analyse de précision**:
   - Comparer prédictions passées avec réalisations
   - Calculer hit-rate, MAE, RMSE, précision directionnelle
   - Analyse par horizon (1d, 1w, 1m) et type d'actif

2. **Service d'analyse**:
   - Charger prévisions historiques et données de réalisation
   - Calculer les métriques de performance
   - Sauvegarder dans `data/analytics/prediction_accuracy.json`

3. **Endpoint API**:
   - GET `/api/analytics/predictions` avec filtres par horizon et actif
   - Retourne métriques de précision des modèles ML/LLM

**DoD**
* `/api/analytics/predictions?horizon=1w` retourne statistiques de précision
* Données incluent: hit_rate, avg_confidence, avg_return_if_correct, success_rate
* Utile pour évaluer la qualité des modèles de prévision
* Never-empty - même si peu d'historique pour évaluation

---

## FC-API-033 — User Preferences

**Status**: AVAILABLE to claim

**But**: Endpoints `/api/user/preferences` pour gérer les préférences utilisateur (thèmes favoris, univers, seuils).

**Fichiers**
* `backend/api/routes/user.py`
* `backend/services/user_prefs.py`
* `backend/models/user_preferences.py`
* `data/users/preferences.json` (stockage local pour MVP)

**Étapes**
1. **Modèle préférences**:
   - Tickers favoris, secteurs d'intérêt
   - Seuils d'alerte (volatilité, sentiment, etc.)
   - Préférences UI (theme, layout, etc.)

2. **Service de préférences**:
   - Chargement/sauvegarde des préférences
   - Gestion de la persistance locale
   - Intégration avec l'authentification (si présente)

3. **Endpoints API**:
   - GET `/api/user/preferences` pour récupérer
   - PUT `/api/user/preferences` pour sauvegarder
   - POST `/api/user/preferences/reset` pour reset

**DoD**
* `/api/user/preferences` retourne les préférences utilisateur
* Système de sauvegarde/restauration fonctionnel
* Compatible avec intégration UI pour stockage des préférences
* Never-empty - retourne valeurs par défaut si pas de préférences

---

## FC-API-034 — Alert Rules Configuration

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/alerts/rules` pour la configuration des règles d'alerte (paramètres de seuil).

**Fichiers**
* `backend/api/routes/alerts.py`
* `backend/services/alert_rules.py`
* `backend/models/alert_configuration.py`
* `data/alerts/rules.json`

**Étapes**
1. **Modèle de règles**:
   - Types d'alertes: RSI oversold/overbought, news sentiment, price breakouts
   - Paramètres: seuils, fréquence, actifs concernés
   - Système de priorité et de regroupement

2. **Service de règles**:
   - Gestion des configurations d'alerte
   - Validation des seuils et paramètres
   - Sauvegarde des règles dans système persistant

3. **Endpoint API**:
   - GET `/api/alerts/rules` pour liste des règles actives
   - PUT `/api/alerts/rules` pour mise à jour de configuration
   - DELETE `/api/alerts/rules/{rule_id}` pour suppression

**DoD**
* `/api/alerts/rules` retourne liste des règles configurées
* Système de CRUD pour gestion des règles d'alerte
* Validation des seuils et paramètres pour prévenir erreurs
* Never-empty - même si pas de règles configurées

---

## FC-API-035 — Universal Search

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/search/universal` pour recherche globale (stocks, news, briefs, prévisions).

**Fichiers**
* `backend/api/routes/search.py`
* `backend/services/universal_search.py`
* `backend/models/search_result.py`
* `search/search_engine.py`

**Étapes**
1. **Moteur de recherche**:
   - Indexation de documents de différents domaines
   - Recherche multi-critères (contenu, dates, sources, tickers)
   - Ranking par pertinence et fraîcheur

2. **Service de recherche**:
   - Intégration avec différentes sources (news, forecasts, briefs, etc.)
   - Filtres par type, date, importance
   - Pagination et tri

3. **Endpoint API**:
   - POST `/api/search/universal` avec body de requête
   - Retourne résultats de différents domaines avec scoring

**DoD**
* `/api/search/universal?q=NVDA&type=stocks&type=news` retourne résultats multi-domaines
* Système de ranking par pertinence et fraîcheur
* Performance acceptable pour recherche temps-réel (< 300ms)
* Never-empty - même si pas de résultats correspondants
---

## 🚨 CRITICAL TASKS - NO-MOCKS DATA INTEGRATION

These tasks address the critical findings from the end-to-end integration tests that revealed real data is missing from key endpoints.

---

## FC-REAL-SEED-001 — Data Snapshot Seeding with Real Data

**Status**: AVAILABLE to claim

**But**: Assurer que les fichiers snapshots dans `/backend/data/` contiennent des données réelles, pas des valeurs par défaut ou des structures vides.

**Fichiers**
* `backend/data/forecasts.json`
* `backend/data/news_feed.json` 
* `backend/data/brief_weekly.json`
* `backend/jobs/data_seeder.py`
* `backend/storage/json_storage.py`

**Étapes**
1. **Verify current snapshot content**:
   - Vérifier que `forecasts.json` contient une structure `{"rows": [...]}` avec des données réelles
   - Vérifier que `news_feed.json` contient une structure `{"articles": [...]}` avec articles réels
   - Vérifier que les autres snapshots (`brief_*.json`) contiennent des données valorisées

2. **Fix data pipeline**:
   - Exécuter les jobs d'ingestion pour générer des snapshots avec données réelles
   - Corriger les chemins de stockage si le backend ne lit pas au bon endroit
   - S'assurer que les fichiers sont lus depuis `copilot-app/backend/data/` (pas un autre chemin)

3. **Real data validation**:
   - Les données doivent provenir de sources réelles (yfinance, RSS, FRED)
   - Ne pas utiliser de mocks ou de données de test

**DoD**
* `curl /api/forecasts` renvoie `{ok:true, data:{rows:[{...},{...}], count:n, ...}}` avec n > 0
* `curl /api/news/feed` renvoie `{ok:true, data:{articles:[{...},{...}], count:n, ...}}` avec n > 0
* Tous les snapshots dans `/backend/data/` contiennent des données réelles, pas vides
* Chemins de lecture corrects (relatifs à backend CWD)
* Never-empty pattern fonctionnel avec données réelles

---

## FC-REAL-PIPE-001 — Real Data Ingestion Pipeline

**Status**: AVAILABLE to claim

**But**: Mettre en place des pipelines d'ingestion réelle (Yahoo, RSS, FRED) qui alimentent les snapshots avec données de production.

**Fichiers**
* `backend/jobs/forecast_generator.py`
* `backend/jobs/news_ingest.py` 
* `backend/services/forecast_pipeline.py`
* `backend/services/news_pipeline.py`
* `backend/scheduler/app.py`

**Étapes**
1. **Forecast pipeline**:
   - Lancer le job de génération de prévisions ML réelles
   - Sauvegarder le résultat dans `data/forecasts.json`
   - Utiliser des données de marché réelles (prix historiques, indicateurs techniques, etc.)

2. **News pipeline**:
   - Lancer le job d'ingestion de news réelles (RSS feeds)
   - Sauvegarder le résultat dans `data/news_feed.json`
   - Appliquer le filtrage et scoring sur données réelles

3. **Scheduler integration**:
   - Intégrer ces jobs dans le scheduler pour rafraîchissement automatique
   - Fréquences appropriées: forecasts quotidien, news toutes les 15 min

**DoD**
* Jobs d'ingestion produisent des snapshots avec données réelles
* `forecasts.json` contient des prévisions basées sur ML + données réelles
* `news_feed.json` contient des articles réels provenant de sources RSS
* Scheduler exécute les jobs pour maintenir fraîcheur des données
* Les endpoints `/api/forecasts` et `/api/news/feed` renvoient maintenant des données réelles

---

## FC-REAL-DATA-001 — Data Path & Storage Fix

**Status**: AVAILABLE to claim

**But**: Corriger les chemins de lecture des données pour que le backend trouve les fichiers de données réelles dans le bon répertoire.

**Fichiers**
* `backend/storage/base.py` (ou `json_storage.py`)
* `backend/services/cache_layer.py` 
* `backend/api/routes/forecasts.py`
* `backend/api/routes/news.py`
* `backend/api/main.py`

**Étapes**
1. **Verify CWD**:
   - Le backend doit toujours lire à partir de `copilot-app/backend/data/` relativement à son répertoire
   - Forcer des chemins absolus si nécessaire pour éviter les problèmes de CWD

2. **Fix storage paths**:
   - S'assurer que `load_json()` lit depuis le bon répertoire
   - Corriger les imports pour utiliser les bons modules de storage
   - Vérifier que `storage.base` est utilisé pour les chemins robustes

3. **Test with absolute paths**:
   - Si uvicorn change le CWD, utiliser des chemins absolus déterministes
   - Exécuter des tests pour confirmer que les fichiers sont lus depuis le bon emplacement

**DoD**
* Backend lit correctement les fichiers de données depuis `backend/data/`
* Aucune référence à `file_not_found` dans les réponses
* Les endpoints renvoient les données présentes dans les fichiers snapshots
* Chemins de lecture déterministes qui fonctionnent quel que soit le CWD du serveur

---

## FC-REAL-TEST-001 — "No-Mocks" Integration Testing

**Status**: AVAILABLE to claim

**But**: Mettre en place et exécuter des tests d'intégration qui vérifient que les endpoints servent des données réelles, pas des mocks.

**Fichiers**
* `tests/ui/integration-data.spec.ts` (existant - à corriger)
* `tests/api/no_mock_tests.py`
* `docs/no-mocks-testing.md`

**Étapes**
1. **Fix current tests**:
   - Ajuster les tests Playwright pour ne pas utiliser de filtres stricts qui causent des retours vides
   - Corriger les tests pour vérifier la présence de données réelles, pas des structures vides

2. **Create seeding step**:
   - Ajouter une étape de pré-test qui s'assure que les données réelles sont présentes
   - Lancer les pipelines d'ingestion avant les tests si nécessaire

3. **Add robust assertions**:
   - Vérifier que les endpoints renvoient des comptages > 0 
   - Ne pas échouer si des filtres spécifiques retournent zéro résultats
   - Tester sans filtres pour vérifier la disponibilité de données

**DoD**
* Tests Playwright passent avec données réelles (pas de mocks)
* curl /api/forecasts renvoie count > 0
* curl /api/news/feed renvoie count > 0 (sans filtres stricts)
* Tests valident que le système est alimenté par des données réelles

---

## 🎯 Priorité d'exécution

1. **FC-REAL-DATA-001**: Fix des chemins de données (base pour les autres)
2. **FC-REAL-PIPE-001**: Pipeline d'ingestion (génère les données)
3. **FC-REAL-SEED-001**: Seeding des snapshots (alimente les endpoints)
4. **FC-REAL-TEST-001**: Tests d'intégration (validation finale)
---

## 🧪 CODE QUALITY TASKS - Codacy Integration & Analysis

Suite à la mise en place de la directive qualité, voici les tâches spécifiques pour intégrer Codacy dans le workflow de développement.

---

## FC-QM-CODACY-001 — Codacy Analysis Setup & Integration - DONE

**But**: Intégrer l'analyse Codacy dans le workflow de développement pour améliorer la qualité du code et détecter les problèmes automatiquement.

**Fichiers**
* `scripts/quality/codacy-analyze.sh` (script d'analyse)
* `docs/quality/codacy-integration.md` (documentation)

**Étapes**
1. **Setup Codacy-CLI**:
   - Script bash automatisé avec options de format (JSON/SARIF/TEXT)
   - Gestion des chemins projet et outils spécifiques
   - Exécution sur backend/frontend selon besoin

2. **Configuration outils**:
   - Integration avec ESLint et autres outils de qualité
   - Paramètres de format SARIF conforme aux standards
   - Support des outils spécifiques (pylint, eslint, etc.)

3. **Workflow intégration**:
   - Scripts prêts pour intégration dans hooks git
   - Support de l'analyse ciblée par composant (backend, frontend)
   - Génération de rapports SARIF pour intégration continue

4. **Documentation**:
   - Guide complet d'utilisation pour les agents
   - Exemples d'utilisation et standards qualité
   - Processus d'intégration dans le workflow de développement

**DoD**
* `codacy-cli analyze` fonctionne pour analyse complète du code
* `codacy-cli analyze --tool eslint` fonctionne pour analyse spécifique
* Résultats générés au format SARIF: `codacy-cli analyze --tool eslint --format sarif -o results.sarif`
* Scripts d'analyse intégrés dans le workflow de développement
* Documentation mise en place pour l'équipe

**Completed by**: ALEX-FINANCE-ANALYST-SUPERMAN-29

**Files created**:
- `scripts/quality/codacy-analyze.sh` - Complete automated analysis script
- `docs/quality/codacy-integration.md` - Comprehensive usage documentation

---

## FC-QM-CODACY-002 — Analyse qualité backend + corrections

**Status**: AVAILABLE to claim

**But**: Exécuter l'analyse Codacy sur le backend et corriger les problèmes identifiés pour améliorer la qualité du code.

**Fichiers**
* Tous les fichiers Python dans `backend/`
* `backend/api/main.py`
* `backend/api/routes/*.py`
* `backend/services/*.py`
* `backend/jobs/*.py`
* `backend/storage/*.py`

**Étapes**
1. **Analyse complète du backend**:
   - Exécuter: `codacy-cli analyze backend/`
   - Sauvegarder les résultats: `codacy-cli analyze backend/ --format sarif -o backend-quality.sarif`
   - Identifier les problèmes critiques et de sécurité

2. **Corrections prioritaires**:
   - Problèmes de sécurité (SQL injection, XSS, etc.)
   - Problèmes d'accessibilité
   - Problèmes de performance
   - Problèmes de style et maintenabilité

3. **Vérification never-empty**:
   - S'assurer que les patterns never-empty sont respectés partout
   - Vérifier que les imports sont sécurisés
   - Confirmer que les protections UI/UX sont correctes

4. **Tests et validation**:
   - Vérifier que les corrections n'introduisent pas de regressions
   - S'assurer que tous les endpoints continuent à fonctionner

**DoD**
* Analyse Codacy complète exécutée sur backend
* Problèmes critiques identifiés et corrigés
* Backend continues à fonctionner avec améliorations qualité
* Rapport SARIF sauvegardé avec preuves des corrections

---

## FC-QM-CODACY-003 — Analyse qualité frontend + corrections

**Status**: AVAILABLE to claim

**But**: Exécuter l'analyse Codacy sur le frontend et corriger les problèmes identifiés pour améliorer la qualité du code UI.

**Fichiers**
* Tous les fichiers TypeScript/JSX dans `frontend/webapp/src/`
* `frontend/webapp/src/components/*.tsx`
* `frontend/webapp/src/pages/*.tsx`
* `frontend/webapp/src/api/client.ts`
* `frontend/webapp/src/ui/*.tsx`
* `frontend/webapp/src/lib/safe.ts`

**Étapes**
1. **Analyse spécifique ESLint**:
   - Exécuter: `codacy-cli analyze --tool eslint frontend/webapp/src/`
   - Sauvegarder: `codacy-cli analyze --tool eslint frontend/webapp/src/ --format sarif -o frontend-quality.sarif`
   - Identifier les problèmes de sécurité, accessibilité, performance

2. **Corrections critiques**:
   - Problèmes de gestion d'erreurs UI (erreurs jamais affichées directement)
   - Problèmes de sécurité XSS
   - Problèmes d'accessibilité (roles, aria-labels, focus management)
   - Problèmes de never-empty (gardiens manquants)

3. **Optimisation**:
   - Améliorer la performance des composants UI
   - Optimiser les imports et dépendances
   - Vérifier les patterns de sécurité (safe access helpers)

4. **Validation UI**:
   - Confirmer que toutes les pages continuent à charger
   - Tester les 4 états UI (loading, empty, error, fresh data)
   - Vérifier que les data-testid sont corrects

**DoD**
* Analyse Codacy + ESLint exécutée sur frontend
* Problèmes critiques identifiés et corrigés
* UI continues à fonctionner avec améliorations qualité
* Rapport SARIF sauvegardé avec preuves des corrections
* Protection never-empty renforcée

---

## FC-QM-CODACY-004 — Analyse fichier spécifique + corrections ciblées

**Status**: AVAILABLE to claim

**But**: Exécuter l'analyse Codacy sur des fichiers spécifiques identifiés comme problématiques et corriger les points critiques.

**Fichiers**
* `backend/src/api/main.py` (fichier central avec imports critiques)
* `frontend/webapp/src/api/client.ts` (communication API, sécurité)
* `frontend/webapp/src/components/ErrorBoundary.tsx` (gestion des erreurs)
* `backend/storage/io.py` (sécurité I/O, never-empty)
* `backend/services/cache_layer.py` (gestion du cache, fallbacks)

**Étapes**
1. **Analyse fichier par fichier**:
   - `codacy-cli analyze --tool eslint backend/src/api/main.py`
   - `codacy-cli analyze --tool eslint frontend/webapp/src/api/client.ts`
   - `codacy-cli analyze --tool eslint frontend/webapp/src/components/ErrorBoundary.tsx`
   - etc.

2. **Corrections ciblées**:
   - Corriger les problèmes d'imports (ModuleNotFoundError)
   - Corriger les problèmes de sécurité (injection, etc.)
   - Corriger les problèmes de gestion d'erreurs
   - Renforcer les patterns never-empty

3. **Améliorations spécifiques**:
   - Assurer la cohérence des contrats API ({ok, data})
   - Vérifier les fallbacks en cas d'erreur
   - Optimiser les performances des composants critiques

4. **Tests unitaires**:
   - Vérifier que les corrections n'affectent pas la fonctionnalité
   - Tester spécifiquement les cas d'erreur et empty-states

**DoD**
* Fichiers critiques analysés un par un avec Codacy
* Problèmes identifiés et corrigés dans chaque fichier
* Fonctionnalité des composants critiques maintenue ou améliorée
* Rapports SARIF générés par fichier avec preuves des corrections