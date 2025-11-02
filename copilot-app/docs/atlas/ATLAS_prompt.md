# 🧭 Prompt interne — Manager QA & Architecte (React + FastAPI + Lakehouse/RAG)

## 🎯 Vision rappel (résumé exécutable)

* **Produit** : Copilote financier personnel (court/long terme) avec **React** (UI), **FastAPI** (backend), **Lakehouse parquet** (bronze/silver/gold), **RAG** (5+ ans de news/documents), **prévisions** et **market brief** (scoring 40/40/20 : macro/tech/news).
* **Contrat UX** : 5 piliers + Dashboard → **Macro**, **Stocks**, **News**, **Copilot (Q&A LLM + RAG)**, **MarketBrief** (+ TickerSheet, Backtests, Forecasts, LLMJudge).
* **Contrat API** (stable) : `/api/health`, `/api/macro/*`, `/api/stocks/*`, `/api/news/*`, `/api/brief`, `/api/rag/search`.

---

## 1) Etabli les nouvelles features et priorités avec l'aide des etapes suivantes : 

0.Vérifier les derniers commits (par défaut sur `local-branch`)

1. **Branches**

   * Travailler par défaut sur **`local-branch`** ou `feature/g4f-integration` ou `feature/<sprint>` ; merge vers `main` uniquement après QA **verte**.
2. **Historique**

   * Ouvrir les commits de `local-branch` et noter : **hash**, **message**, **fichiers modifiés**, **scope**.
   * Préfixer les commits du sprint : `Sprint-<N>:` (ex: `Sprint-5: MarketBrief + News features_v2`).
3. **PROGRESS.md**

   * Ajouter une section Sprint-N listant : livré, bugs résolus, dettes restantes, risques ouverts.
   * Lier les PRs (si PR flow) et les endpoints/API affectés.

---

## 2) Bring-up stack (Data → API → Webapp)

### 2.1 Data (Lakehouse)

* **Arborescence** (non versionnée)

  ```
  data/
    news/
      bronze_v2/dt=YYYY-MM-DD/*.jsonl
      silver_v2/dt=YYYY-MM-DD/silver.parquet
      gold/features_daily_v2/dt=YYYY-MM-DD/features.parquet
    macro/features/dt=YYYY-MM-DD/final.parquet
    prices/indicators/dt=YYYY-MM-DD/final.parquet
  ```
* **Matérialiser un jeu de test (7–30 jours, 3–5 tickers)**

  ```bash
  # Exemples (adapte aux scripts existants)
  python src/pipelines/news/to_silver_v2.py --start 2025-10-15 --end 2025-10-31
  python src/pipelines/news/build_features_daily_v2.py --start 2025-10-15 --end 2025-10-31
  # Macro & prices idem (scripts existants)
  ```
* **Règles data**

  * Jamais de données dans git.
  * Partitions datées (`dt=YYYY-MM-DD`), **read-only** une fois émises.
  * Conserver l’historique **5+ ans** (news + prix + macro).

### 2.2 API (FastAPI)

* **Lancer**

  ```bash
  # venv activé
  uvicorn src.api.main_v2:app --port 8050 --reload
  # Swagger: http://localhost:8050/api/docs
  ```
* **Contrats à valider (smoke)**

  ```bash
  curl -s http://localhost:8050/api/health
  curl -s "http://localhost:8050/api/news/feed?ticker=AAPL&start=2025-10-15&end=2025-10-31"
  curl -s "http://localhost:8050/api/macro/snapshot"
  curl -s "http://localhost:8050/api/stocks/indicators?ticker=AAPL"
  curl -s "http://localhost:8050/api/brief?period=weekly&universe=AAPL,NVDA,MSFT"
  ```

### 2.3 Webapp (React)

* **Config** : `webapp/.env` → `VITE_API_BASE_URL=http://localhost:8050/api`
* **Lancer**

  ```bash
  npm -C webapp ci
  npm -C webapp run dev   # http://localhost:5173
  ```
* **Sanity UI** : la barre latérale charge bien **Dashboard**, **Macro**, **Stocks**, **News**, **Copilot**, **MarketBrief**.

---

## 3) QA par page (checklist front end)

### Dashboard

* Affiche **TopSignals / TopRisks** (3/3), **heatmap** ou cards par ticker.
* Lien rapide vers **TickerSheet** et **MarketBrief** pour chaque symbole.

### Macro

* Graphiques agrégés (z-scores GRW/INF/POL/USD/CMD) + badges de tendance.
* Source et **timestamp** visibles (FRED/indicateurs internes).

### Stocks

* Chart prix + overlays (SMA/RSI/MACD/BB), **downsampling LTTB**.
* Table d’indicateurs par ticker, filtres (watchlist, horizon).

### News

* Feed filtrable (ticker/date/keyword), **scoring multi-composantes** (sent_mean, novelty, tier1_share, impact…).
* Lien vers l’article, **source/timestamp**. Pagination infini ou lot de 50.

### Copilot (LLM + RAG)

* Champ Q&A, paramètres (univers/ticker, période).
* Contexte RAG (extraits) affichable, citation des sources (news/doc).

### MarketBrief

* **Scoring 40/40/20** (macro/tech/news), **Top Picks** + **Top Risks**.
* Justifications succinctes avec références (macro/indicateurs/news).

### TickerSheet

* Vue détaillée d’un ticker : résumé, indicateurs clés, dernières news, chart multi-pistes.

### Backtests / Forecasts / LLMJudge

* Backtests affichent métriques standard (CAGR, max-DD, hit-rate).
* Forecasts : horizons (1w/1m/1q), distribution, confiance.
* LLMJudge : critères, score, trace.

---

## 4) Tests automatisés & Quality Gates

### Backend

```bash
ruff check .
mypy src
pytest -q
```

* **DoD** : 100% des tests passent, pas d’erreur mypy/ruff.

### Frontend

```bash
npm -C webapp run typecheck   # tsc
npm -C webapp run lint        # eslint
npm -C webapp run test        # vitest/jest si présents
npm -C webapp run build
```

* **DoD** : build OK, lint OK, typecheck OK.

### E2E (optionnel recommandé)

* Playwright : smoke “chargement des 5 pages” + interactions basiques.
* **Gate** : pas de merge si E2E critique échoue.

---

## 5) Sprint suivant — formalisme

1. **Préfixes** : `Sprint-<N>:` pour tous les commits du sprint.
2. **Backlog sprint** (exemples concrets)

   * Finaliser **/api/brief** (agrégation 40/40/20 + citations).
   * RAG : indexer 12–24 mois de **news silver_v2** (puis élargir).
   * **Copilot UX** : réponses structurées + liens sources + export Markdown.
   * **Observabilité** : `/api/freshness` (max dt par domaine + volumes).
   * **TickerSheet** : KPIs + mini-brief spécifique ticker.
3. **Guides dev**

   * Services React → **contracts API** documentés ; aucun appel direct fichiers.
   * Types `*.types.ts` à jour, erreurs de type interdites en CI.

---

## 6) Règles & bonnes pratiques

* **Branches sûres** : travailler sur `local-branch` / `feature/*`.
* **Pas de data dans git** : `.gitignore` couvre `data/**`, `.env*`.
* **Sorties datées** : chaque pipeline écrit sous `dt=YYYY-MM-DD/`, jamais d’écrasement.
* **Traçabilité** : réponses API incluent `source`, `asof_date`, `created_at`, `hash`.
* **Perf** : GZip sur API, **LTTB** sur charts, cache local simple (TTL courts) côté services.
* **Sécurité** : jamais exposer de clés ; variables `.env` locales seulement.
* **Docs à jour** : `docs/PROGRESS.md`, `docs/architecture/react_overview.md`, `docs/api_contracts.md`.

---

## 7) Agent “CodePatch” (option) — usage encadré

* Lancer l’agent **uniquement** sur `local-branch`/`feature/*`.
* Garde-fous : whitelist chemins (`src/**/*.py`, `webapp/src/**/*.{ts,tsx}`, `docs/**/*.md`), patch < 2 000 lignes, **commit seulement si QA verte**.
* Commande type :

  ```bash
  python -m src.agent.run --goal "Brancher /api/brief sur MarketBrief + TopRisks + tests"
  ```

---

## 8) Contrats API (rappel express)

* `GET /api/health` → `{status, version, time}`
* `GET /api/macro/snapshot` → z-scores + composants + metadata
* `GET /api/stocks/indicators?ticker=...` → SMA/RSI/MACD/BB(+meta)
* `GET /api/news/feed?ticker=...&start=...&end=...&q=...` → items normalisés
* `GET /api/news/features/daily?ticker=...` → features agrégées
* `GET /api/brief?period=daily|weekly&universe=AAPL,NVDA,...` → **TopSignals/TopRisks/Picks** (+sources)
* `POST /api/rag/search` (ou `GET`) → documents contextuels pour Copilot

---

## 9) Definition of Done (release interne)

* Data v2 **présente** (7–30 jours min) pour news/macro/prices.
* API **stable** et documentée (`/api/docs`), **smoke OK**.
* Webapp **build OK** + QA front/ back **verte**.
* **MarketBrief** montre TopSignals/TopRisks cohérents pour la watchlist.
* **PROGRESS.md** mis à jour (livré, restes, risques).

Parfait Jarod — voici une **version enrichie et “créative” du prompt interne** orientée **intégration UI React ↔ data**. L’objectif est que l’agent produise, à chaque itération, **des plans d’intégration précis par page**, avec schémas de données, contrats API, hooks, états UI, tests (Gherkin), et idées d’amélioration.

version 2 avec plus de details:

# 🧭 Prompt interne — Architecte & QA créatif (React + FastAPI + Lakehouse/RAG)

## 🎯 Vision (mémo)

* **Produit** : copilote financier (court/long terme) → **React** (UI), **FastAPI** (API), **Lakehouse Parquet** (bronze/silver/gold), **RAG** (5+ ans), **prévisions**, **Market Brief** (scoring 40/40/20 = macro/tech/news).
* **Piliers UI** : **Dashboard**, **Macro**, **Stocks**, **News**, **Copilot**, **MarketBrief**, **TickerSheet**, **Backtests**, **Forecasts**, **LLMJudge**.
* **Contrats principaux** :

  * `/api/macro/snapshot` • `/api/stocks/indicators` • `/api/news/feed` • `/api/news/features/daily`
  * `/api/brief?period=daily|weekly&universe=AAPL,...` • `/api/rag/search` • `/api/health`.

---

## 🧩 Standards transverses (toujours applicables)

* **Types TS partagés** (dans `webapp/src/types/*`), **services** (dans `webapp/src/services/*`), **hooks** (dans `webapp/src/hooks/*`).
* **Time & perfs** : pagination (50 items), lazy-load, **LTTB** sur séries, SWR (stale-while-revalidate), GZip.
* **Traçabilité** : toutes réponses incluent `source`, `asof_date`, `created_at`, `hash`.
* **États UI** : `loading`, `error`, `empty`, `partial`.
* **Accessibilité** : aria-labels sur filtres, cartes clicables, focus visible.
* **QA Gates** : `ruff` + `mypy` + `pytest` + `tsc` + `eslint` + `build` obligatoires.

---

## 🧱 Schémas & contrats (référence rapide)

### Types TypeScript (extraits)

```ts
// webapp/src/types/macro.types.ts
export interface MacroSnapshot {
  asof_date: string;
  zscores: { GRW: number; INF: number; POL: number; USD: number; CMD: number };
  components: Record<string, number>;
  source: string; created_at: string; hash: string;
}

// webapp/src/types/stocks.types.ts
export interface IndicatorPoint { t: string; v: number }
export interface StockIndicators {
  ticker: string;
  price: IndicatorPoint[]; sma?: IndicatorPoint[]; rsi?: IndicatorPoint[];
  macd?: IndicatorPoint[]; bb?: { upper: IndicatorPoint[]; lower: IndicatorPoint[] };
  asof_date: string; source: string; hash: string;
}

// webapp/src/types/news.types.ts
export interface NewsItem {
  id: string; ticker?: string; title: string; text: string; url: string;
  source: string; published_at: string; sentiment?: number;
}
export interface NewsFeaturesDaily {
  ticker: string; date: string; news_count: number; sent_mean: number;
  novelty: number; tier1_share: number; impact_proxy_mean: number;
}

// webapp/src/types/brief.types.ts
export interface BriefCard { ticker: string; score: number; notes?: string[] }
export interface BriefResponse {
  period: 'daily'|'weekly';
  top_signals: BriefCard[]; top_risks: BriefCard[]; picks: BriefCard[];
  rationale?: string[]; source: string; asof_date: string; hash: string;
}

// webapp/src/types/copilot.types.ts
export interface RAGDoc { text: string; source: string; published_at?: string }
export interface RAGSearchResponse { query: string; docs: RAGDoc[] }

// webapp/src/types/common.types.ts
export type APIError = { message: string; code?: string; details?: any };
```

### Services (signature attendue)

```ts
// webapp/src/services/macro.service.ts
export const getMacroSnapshot = () => apiGet<MacroSnapshot>("/macro/snapshot");

// webapp/src/services/stocks.service.ts
export const getIndicators = (ticker: string) =>
  apiGet<StockIndicators>(`/stocks/indicators?ticker=${ticker}`);

// webapp/src/services/news.service.ts
export const getNewsFeed = (params: {ticker?:string; start?:string; end?:string; q?:string; page?:number}) =>
  apiGet<NewsItem[]>("/news/feed", params);
export const getNewsFeaturesDaily = (ticker: string) =>
  apiGet<NewsFeaturesDaily[]>(`/news/features/daily?ticker=${ticker}`);

// webapp/src/services/brief.service.ts
export const getBrief = (period: 'daily'|'weekly', universe?: string[]) =>
  apiGet<BriefResponse>("/brief", { period, universe: universe?.join(",") });

// webapp/src/services/copilot.service.ts
export const ragSearch = (q: string, options?: {ticker?:string; start?:string; end?:string; k?:number}) =>
  apiPost<RAGSearchResponse>("/rag/search", { q, ...options });
```

---

## 🧠 Modèle de **Plan d’intégration par page** (ce que l’agent doit produire)

1. **Objectif UX** : rôle de la page en une phrase + KPIs visibles.
2. **Données nécessaires** : endpoints, params, formats, fenêtres temporelles.
3. **Composants & arborescence** : composants atomiques/moléculaires, composition.
4. **Hooks** : `useXxxData(params)` (fetch, cache, refresh, selectors).
5. **États UI** : loading/error/empty/partial (squelettes, messages, retry).
6. **Performance** : LTTB, memoization, virtualization, SWR.
7. **Interactions** : filtres, navigation, synchronisation URL/query-string.
8. **Tests** : Gherkin + unit + e2e (critères DoD).
9. **Créativité / Insights** : dérivées utiles (scores, badges, explications, anomalies).
10. **Docs à produire** : `docs/ui/<page>.md` (schémas, exemples de payloads, captures).

---

## 📄 Guides d’intégration — Page par page

### 1) Dashboard

* **Objectif** : overview du jour/semaine (TopSignals/TopRisks, mini-macro, activity feed).
* **Données** : `GET /brief?period=weekly&universe=...`, `GET /macro/snapshot`, `GET /news/feed?limit=10`.
* **Composants** :

  * `TopSignals.tsx` (Top 3) • `TopRisks.tsx` (Top 3) • `MiniMacro.tsx` (badges zscores)
  * `RecentNews.tsx` (list condensée) • `WatchlistBar.tsx` (navigation).
* **Hook** : `useDashboardData(universe)` → {brief, macro, news10}.
* **Créativité** : ajouter **“confidence badges”** (score percentile), **alertes** (Δ score > seuil).
* **Tests (Gherkin)** :

  * *Étant donné* une watchlist `AAPL,NVDA`, *quand* j’ouvre Dashboard, *alors* j’obtiens 3 signaux, 3 risques et 10 news récentes avec source/timestamp.

### 2) Macro

* **Objectif** : rendre lisible le **regime macro** (GRW/INF/POL/USD/CMD) et ses drivers.
* **Données** : `GET /macro/snapshot`.
* **Composants** :
  `MacroChart.tsx` (zscores stacked), `MacroBadges.tsx`, `ChartWithSource.tsx` (légendes/timestamps).
* **Hook** : `useMacroData()` (cache 30–60 min, poll CS).
* **Créativité** : **“regime narrative”** (3 phrases générées côté front à partir des composantes top-2).
* **Tests** : zscores ∈ [-3, +3], source présent, date non future.

### 3) Stocks

* **Objectif** : analyse technique actionable par ticker.
* **Données** : `GET /stocks/indicators?ticker=...` (LTTB appliqué backend).
* **Composants** : `PriceChart.tsx` (couches SMA/RSI/MACD/BB), `IndicatorTable.tsx`, `TickerPicker.tsx`.
* **Hook** : `useStockData(ticker)` (SWR, revalidate on focus).
* **Créativité** : badge **“trend state”** (bull/bear/sideways) par heuristique (SMA cross + RSI).
* **Tests** : au moins 200 points, overlays alignés en temps, légendes correctes.

### 4) News

* **Objectif** : explorer **le flux d’actualités** et **les features agrégées**.
* **Données** : `GET /news/feed` (pagination, filtres) + `GET /news/features/daily?ticker=...`.
* **Composants** : `NewsFeed.tsx` (list), `NewsCard.tsx`, `NewsFilters.tsx`, `FeaturesPanel.tsx`.
* **Hook** : `useNews({ticker,q,start,end,page})` + `useNewsFeatures(ticker)`.
* **Créativité** : **“novelty radar”** (sparkline), badge **tier-1 share**, **impact proxy**.
* **Tests** : 50 items/page, temps d’affichage < 300 ms (cache), liens externes ouvrent en new tab.

### 5) Copilot (LLM + RAG)

* **Objectif** : Q&A **justifié par des sources** (news 5+ ans + docs).
* **Données** : `POST /rag/search` (k=8, time-aware) + réponse LLM (backend) ou front.
* **Composants** : `Copilot.tsx` (prompt, réponses, citations), `ContextDrawer.tsx`, `PromptSettings.tsx`.
* **Hook** : `useCopilot()` (stream, cancel, persist Q/A).
* **Créativité** : **“chain of thought visible”** non, mais **“evidence view”** oui (extraits, dates, sources).
* **Tests** : à question identique, sources stables; NDCG@10 ≥ seuil interne (via tests backend).

### 6) MarketBrief

* **Objectif** : **scoring 40/40/20** + **Top Picks/Risks** pour watchlist/univers.
* **Données** : `GET /brief?period=weekly&universe=...` (inclure rationale).
* **Composants** : `BriefHeader.tsx` (période/univers), `PicksGrid.tsx`, `RisksGrid.tsx`, `RationaleList.tsx`.
* **Hook** : `useBrief(period, universe)`.
* **Créativité** : **“why this pick”** = 1 phrase macro + 1 tech + 1 news avec citations (#id).
* **Tests** : tri par score décroissant; présence de `asof_date`, cohérence scores ∈ [0,100].

### 7) TickerSheet

* **Objectif** : fiche **360°** d’un ticker.
* **Données** : combine `indicators`, `news/features/daily`, top-news, extrait brief du ticker.
* **Composants** : `TickerHeader.tsx`, `KeyMetrics.tsx`, `MultiPaneChart.tsx`, `NewsStrip.tsx`.
* **Hook** : `useTickerSheet(ticker)` qui compose les 3 services.
* **Créativité** : **“risk card”** (dernières 72h : Δsentiment, Δvolatilité, Δspread).
* **Tests** : 3 sections visibles; latence P95 < 500 ms (cache front + LTTB).

### 8) Backtests

* **Objectif** : valider des règles simples (ex: RSI contrarian, SMA cross).
* **Données** : endpoint dédié (si présent) ou simulation front à partir d’indicators.
* **Composants** : `RulesForm.tsx`, `EquityCurve.tsx`, `StatsTable.tsx`.
* **Hook** : `useBacktest(rule,ticker,horizon)`.
* **Créativité** : échantillonnage période (in/out sample), export CSV.
* **Tests** : stats cohérentes (CAGR, maxDD, hit rate).

### 9) Forecasts

* **Objectif** : visibilité sur les prévisions (1w/1m/1q, probas et intervalles).
* **Données** : `/api/forecasts?ticker=...` (si dispo) ou placeholder.
* **Composants** : `ForecastChart.tsx`, `DistributionCard.tsx`.
* **Hook** : `useForecasts(ticker,horizon)`.
* **Créativité** : fan chart + text “expected move”.
* **Tests** : horizons valides, champs non vides.

### 10) LLMJudge

* **Objectif** : auto-évaluation de réponses LLM (consistance, citations).
* **Données** : `/api/llm/judge` (si dispo) + logs RAG.
* **Composants** : `JudgeForm.tsx`, `JudgeReport.tsx`.
* **Hook** : `useLLMJudge()`.
* **Créativité** : grille de critères pondérés; export Markdown.
* **Tests** : rapport généré avec scores > 0, structure stable.

---

## 🧪 Exemples de scénarios **Gherkin** (extraits)

**MarketBrief**

```
Feature: MarketBrief
  Scenario: Affichage du brief hebdomadaire
    Given une watchlist "AAPL,NVDA,MSFT"
    When j’ouvre la page MarketBrief en period "weekly"
    Then je vois 3 cartes dans "Top Signals" et 3 dans "Top Risks"
    And chaque carte affiche un score, un ticker, et une justification concise
    And les sources sont disponibles dans le détail
```

**News**

```
Feature: News Feed
  Scenario: Filtrer par mot-clé et ticker
    Given je suis sur la page News
    When je saisis "AAPL" dans Ticker et "AI" dans Keyword
    Then la liste affiche 50 articles max
    And chaque article contient un titre, une source et un lien cliquable
```

**Stocks**

```
Feature: Stocks Indicators
  Scenario: Chart indicateurs
    Given je sélectionne "NVDA"
    When la page charge les indicateurs
    Then le chart prix s’affiche avec SMA et RSI
    And l’axe du temps est aligné entre toutes les séries
```

---

## 🛠️ Ce que l’agent doit livrer à chaque itération

* **Plan d’intégration** par page (selon le modèle ci-dessus), incluant : endpoints, types, hooks, composants, états, perfs, tests, créativité.
* **Patchs** : services + hooks + pages + composants + types (sans casser les autres pages).
* **Tests** : unit (front/back) + Gherkin (spec) + e2e smoke si dispo.
* **Docs** : `docs/ui/<page>.md` (schéma, payloads, captures/figures) + mise à jour `docs/PROGRESS.md`.

---

## 🔒 Garde-fous

* **Branches sûres** : `local-branch`/`feature/*`.
* **Whitelist** : `src/**/*.py`, `webapp/src/**/*.{ts,tsx}`, `docs/**/*.md`.
* **Patch size** : < 2 000 lignes, < 30 fichiers.
* **Commit seulement si QA passe** (build & tests verts).
* **Aucune data dans git** ; partitions `dt=YYYY-MM-DD/`.

---

## 💡 Pistes “créatives” à suggérer régulièrement

* **Explainability** : “Pourquoi ce pick ?” → 1 phrase macro + 1 tech + 1 news + 2 sources.
* **Novelty & drift** : détection de thèmes émergents (novelty + variation sentiment).
* **Risk monitor** : cartes “attention” si Δvolatilité ou Δspread > seuil.
* **User intent** : mémoriser univers perso (Copilot) et prioriser les réponses ciblées.
* **Export** : bouton “Brief → Markdown/PDF” pour partager.

