# 📋 Feature Backlog — App Finance Prévisions

**Date**: 2025-10-29
**Architecte**: Claude Sonnet 4.5
**Méthode de Priorisation**: RoI = (Utilité × Impact) / max(1, Effort - 1)

---

## 🎯 Légende

- **Utilité (U)**: 1-5 (gain pour décision investisseur non expert)
- **Impact (I)**: 1-5 (amélioration mesurable: temps gagné, clarté, couverture)
- **Effort (E)**: 1-5 (complexité technique, refactors requis)
- **RoI**: Score calculé (priorité haute si > 10)
- **Bloquants**: Liste explicite (partition absente, schéma manquant, dépendance externe)

---

## 📊 Résumé Priorisation

| Rang | Idée | RoI | Catégorie |
|------|------|-----|-----------|
| 1 | Investor Overview (intégration /integration_overview) | 25.0 | UX |
| 2 | Backtest Agent Complet (equity curve + metrics) | 18.0 | Data |
| 3 | Agents Health Panel (/integration_agents_health finalisé) | 16.0 | UX |
| 4 | Macro Enrichissement (PMI, ISM, LEI, VIX, spreads) | 12.5 | Data |
| 5 | News → Signal LLM (sentiment daily) | 12.0 | LLM |
| 6 | Deep Ticker Snapshot Multi-Horizons | 12.0 | UX |
| 7 | ML Baseline Intégration (fusion complète) | 10.7 | Agents |
| 8 | Evaluation Agent Full (MAE/RMSE/hit_ratio) | 10.0 | Data |
| 9 | Arbitre Multi-Agents LLM (ensemble élargi) | 9.0 | LLM |
| 10 | Portfolio Explainability (Why tilts?) | 8.0 | UX |
| 11 | Alerts Badge Dynamique (count errors sidebar) | 8.0 | UX |
| 12 | Beginner Mode (tooltips globaux) | 6.7 | UX |
| 13 | SearXNG News Ingestion | 6.0 | Infrastructure |
| 14 | Watchlist Coverage Quality (badge par ticker) | 6.0 | Data |
| 15 | LLM Judge Full (model evaluation UI) | 6.0 | LLM |
| 16 | Earnings Impact Analysis | 5.3 | Analytics |
| 17 | Regime Switching Indicators | 5.0 | Analytics |
| 18 | Risk Parity Portfolio Optimizer | 5.0 | Analytics |
| 19 | WebSocket Live Updates | 4.0 | Infrastructure |
| 20 | Multi-User Auth | 3.0 | Infrastructure |

---

## 📦 IDÉES DÉTAILLÉES

---

### [01] 🥇 Investor Overview (intégration /integration_overview)

**Description**:
Finaliser la page `/integration_overview` (actuellement DEV-only) pour production. Centralise:
- **Carte Régime Macro**: Badge coloré (expansion/désinflation/contraction) + tendance (↗️↘️➡️)
- **Carte Risque**: Low/Medium/High (sources: VIX, unemployment, spreads) + explication 1 phrase
- **Top-N Final**: Table Top-10 equity + commodities (score, direction, confiance, horizon 1m)
- **Synthèse LLM**: Card avec drivers clés (3-5 bullets FR) + bouton "Relancer maintenant"
- **Logs LLM**: Affichage temps réel (désactivé pendant exécution, spinner)

**Données requises**:
- `data/macro/forecast/dt=*/macro_forecast.parquet` (colonnes: `regime`, `risk_level`, `inflation_yoy`, `yield_curve_slope`, `unemployment`, `recession_prob`)
- `data/forecast/dt=*/final.parquet` (colonnes: `ticker`, `horizon`, `final_score`, `direction`, `confidence`)
- `data/forecast/dt=*/commodities.parquet` (colonnes: `commodity_name`, `ticker`, `expected_return`, `direction`, `confidence`)
- `data/llm_summary/dt=*/summary.json` (clés: `regime`, `risk_level`, `outlook_days_7`, `key_drivers`, `contributors`)

**Valeur pour Reda**:
- **Vision 360° en 1 page** (30s vs 5 min actuellement)
- **Compréhension contexte macro** (régime/risque expliqué)
- **Drivers LLM synthétisés** (évite lecture 10+ sources)

**UX (composants Dash + IDs stables)**:
- `#overview-regime-card` (Badge + trend + explication)
- `#overview-risk-card` (Badge + metrics table: VIX, unemployment, spreads)
- `#overview-topN-table` (DataTable tri par score desc, 10 rows, export CSV)
- `#overview-llm-summary` (Card avec key_drivers bullets)
- `#overview-llm-run-btn` (Button "Relancer maintenant" + spinner)
- `#overview-llm-run-log` (Div logs stdout, max-height 300px, scroll auto)

**Priorisation**:
- **U = 5** (besoin #1 Reda: overview quotidien)
- **I = 5** (réduction 80% temps décision initiale)
- **E = 2** (page existe, juste finaliser + tests)
- **RoI = (5×5) / max(1,2-1) = 25.0** ⭐

**Bloquants**:
- ✅ Partition `llm_summary` existe (Sprint Sonnet-2 livré)
- ✅ Schema `macro_forecast` existe
- ⚠️ Champs `regime`, `risk_level` pas toujours présents dans macro_forecast → **à ajouter dans macro_forecast_agent.py**

**Modules réutilisés**:
- `src/tools/parquet_io.py`: `read_parquet_latest()`
- `src/dash_app/data/loader.py`: `read_json()`, `load_json_latest()`
- `src/tools/make.py`: `run_make("llm-summary-run")`

**Étapes dev (atomiques)**:
1. Lire page actuelle `/integration_overview` (src/dash_app/pages/integration_overview.py) → identifier gaps
2. Enrichir `macro_forecast_agent.py` pour inclure `regime` (classification expansion/contraction) et `risk_level` (low/medium/high)
3. Créer layout Overview avec 4 cartes + bouton LLM
4. Implémenter callback bouton LLM (run_make + disable/enable + logs live)
5. Ajouter tests dash.testing (test_overview_page.py)
6. Retirer gate `DEVTOOLS_ENABLED` si tests OK

---

### [02] 🥈 Backtest Agent Complet

**Description**:
Finaliser `src/agents/backtest_agent.py` pour générer:
- **Equity curve**: Series temporelle `date, equity` (cumulative returns Top-N strategy)
- **Metrics complètes**: CAGR, Sharpe, Sortino, MaxDD, Win Rate, Avg Return
- **Baseline comparison**: SPY buy-hold vs Top-N

Actuellement: `details.parquet` écrit mais pas de courbe équité ni métriques Sharpe/Sortino.

**Données requises**:
- `data/forecast/dt=*/forecasts.parquet` (historique 252+ jours)
- `data/prices/ticker=*/prices.parquet` (5 ans minimum)
- Sortie: `data/backtest/dt=*/results.parquet` (date, strategy, equity), `summary.json` (CAGR, Sharpe, Sortino, MaxDD, win_rate, avg_return)

**Valeur pour Reda**:
- **Validation stratégie**: "Top-10 momentum aurait généré +15% CAGR vs +10% SPY"
- **Confiance signaux**: Sharpe > 1.0 = robustesse, MaxDD < -20% = acceptable
- **Comparaison visuelle**: Courbe équité vs SPY

**UX**:
- Page `/backtests` déjà existe, améliorer:
  - `#backtest-curve-chart` (Plotly line, 2 traces: Top-N vs SPY)
  - `#backtest-metrics-card` (Grid 2×3: CAGR/Sharpe/Sortino/MaxDD/WinRate/AvgReturn)
  - `#backtest-comparison-table` (Strategy, CAGR, Sharpe, MaxDD)

**Priorisation**:
- **U = 5** (confiance stratégie = besoin clé investisseur)
- **I = 4** (prouve robustesse système)
- **E = 3** (logique backtest à écrire, mais pattern vectorisé Pandas simple)
- **RoI = (5×4) / max(1,3-1) = 10.0** (mais boost à 18.0 car fondamental)

**Bloquants**:
- ✅ Partitions forecasts + prices existent
- ⚠️ Besoin historique forecasts 252+ jours → **vérifier coverage actuel**

**Modules réutilisés**:
- `src/core/market_data.py`: `get_price_history("SPY")`
- `src/tools/parquet_io.py`: `read_parquet_latest()`

**Étapes dev**:
1. Lire agent actuel `src/agents/backtest_agent.py` → identifier ce qui est fait
2. Implémenter equity curve génération:
   - Walk-forward: chaque jour, lire forecasts dt-1, sélectionner Top-N, calculer return day
   - Cumul equity curve
3. Calculer metrics:
   - CAGR: `(equity_final / equity_start)^(252/days) - 1`
   - Sharpe: `mean(daily_returns) / std(daily_returns) * sqrt(252)`
   - Sortino: idem mais std seulement downside
   - MaxDD: max drawdown from peak
   - Win Rate: % jours positifs
4. Fetch SPY baseline (yfinance)
5. Écrire `results.parquet` + `summary.json`
6. Tests unitaires: `tests/unit/test_backtest_metrics.py` (fixture prix mock, vérifier CAGR/Sharpe)

---

### [03] 🥉 Agents Health Panel

**Description**:
Finaliser `/integration_agents_health` pour production. Affiche:
- **Badges agents**: 🟢 (< 24h), 🟡 (24-48h), 🔴 (> 48h) par agent
- **Latest dt**: Affichage dernière partition écrite
- **Actions manuelles**: Boutons `run_make(target)` pour chaque agent (equity-forecast, macro-forecast, llm-summary-run, etc.)
- **Locks**: Anti double-clic (disable bouton pendant exécution + lock file TTL 1h)
- **Logs live**: Stdout/stderr en temps réel (4s refresh)
- **Pipeline DAG**: Visualisation dépendances (mermaid ou Plotly tree)

**Données requises**:
- `data/quality/dt=*/freshness.json` (colonnes: `latest.forecast_dt`, `latest.macro_forecast_dt`, etc.)
- Makefile targets (liste hardcodée: equity-forecast, commodity-forecast, macro-forecast, llm-summary-run, backtest, update-monitor, data-quality, etc.)
- Locks: `artifacts/locks/<target>.lock` (timestamp creation, TTL 3600s)

**Valeur pour Reda**:
- **Monitoring santé système** (1 coup d'œil)
- **Déclenchement manuel agents** (forcer refresh si données périmées)
- **Logs debugging** (comprendre échecs sans terminal)

**UX**:
- `#agents-health-table` (Table: Agent, Status Badge, Latest dt, Last Modified, Action Button)
- `#agents-logs-{target}` (Div logs par agent, collapsible)
- `#agents-dag-chart` (Plotly sankey ou mermaid)

**Priorisation**:
- **U = 4** (Reda veut autonomie pour refresh)
- **I = 5** (réduit dépendance dev pour ops)
- **E = 3** (page existe partiellement, ajouter actions + locks)
- **RoI = (4×5) / max(1,3-1) = 10.0** (boost à 16.0 car ops critical)

**Bloquants**:
- ✅ `src/tools/make.py` existe
- ⚠️ Lock mechanism à implémenter (`src/tools/lock.py` à créer)

**Modules réutilisés**:
- `src/tools/make.py`: `run_make(target)`
- `src/tools/parquet_io.py`: `latest_partition()`

**Étapes dev**:
1. Créer `src/tools/lock.py`:
   ```python
   def acquire_lock(name: str, ttl: int = 3600) -> bool:
       lock_path = Path("artifacts/locks") / f"{name}.lock"
       if lock_path.exists() and (time.time() - lock_path.stat().st_mtime < ttl):
           return False  # Lock held
       lock_path.parent.mkdir(parents=True, exist_ok=True)
       lock_path.write_text(str(time.time()))
       return True

   def release_lock(name: str):
       lock_path = Path("artifacts/locks") / f"{name}.lock"
       if lock_path.exists():
           lock_path.unlink()
   ```
2. Modifier page `/integration_agents_health` pour ajouter boutons + callbacks
3. Callback `run_agent(target)`:
   - Vérifier lock (acquire)
   - Si lock OK: `run_make(target, timeout=900)` en background
   - Disable bouton
   - Refresh logs 4s interval
   - Release lock quand terminé
4. Tests dash.testing: `test_agents_health_page.py` (click button → logs appear → button re-enable)

---

### [04] Macro Enrichissement (PMI, ISM, LEI, VIX, spreads)

**Description**:
Enrichir `src/agents/macro_forecast_agent.py` avec indicateurs additionnels:
- **PMI Manufacturing** (S&P Global, FRED: MANEMP)
- **ISM Manufacturing** (FRED: NAPM)
- **Leading Economic Index** (FRED: USSLIND)
- **VIX** (yfinance: ^VIX)
- **Credit Spreads** (FRED: BAMLH0A0HYM2, high yield OAS)

Actuellement: CPI YoY, unemployment, DGS10, DGS2, slope, recession_prob seulement.

**Données requises**:
- FRED series: `MANEMP`, `NAPM`, `USSLIND`, `BAMLH0A0HYM2`
- yfinance: `^VIX`
- Sortie: Ajouter colonnes à `data/macro/forecast/dt=*/macro_forecast.parquet`

**Valeur pour Reda**:
- **Couverture macro complète** (10+ indicateurs vs 4 actuellement)
- **Meilleure détection régimes** (PMI/ISM early signals croissance)
- **VIX = peur marché** (compréhension risque)

**UX**:
- Pages `/regimes` et `/risk` affichent déjà graphiques → ajouter traces PMI/ISM/LEI/VIX
- Pas de changement layout

**Priorisation**:
- **U = 4** (contexte macro plus riche)
- **I = 4** (early signals améliore forecasts)
- **E = 2** (juste ajouter fetches FRED/yfinance)
- **RoI = (4×4) / max(1,2-1) = 16.0** (mais baissé à 12.5 car non critique immédiat)

**Bloquants**:
- ⚠️ Dépendance FRED API (rate limits, delays H-48)
- ⚠️ VIX parfois manquant weekends

**Modules réutilisés**:
- `src/core/market_data.py`: `get_fred_series()`, `get_price_history("^VIX")`

**Étapes dev**:
1. Modifier `src/agents/macro_forecast_agent.py`:
   ```python
   pmi = get_fred_series("MANEMP", start="-5y")
   ism = get_fred_series("NAPM", start="-5y")
   lei = get_fred_series("USSLIND", start="-5y")
   vix = get_price_history("^VIX", start="-5y")["Close"]
   spreads = get_fred_series("BAMLH0A0HYM2", start="-5y")
   ```
2. Ajouter colonnes à DataFrame macro_forecast
3. Écrire parquet
4. Modifier pages `/regimes` et `/risk` pour afficher nouveaux indicateurs (traces Plotly additionnelles)
5. Tests integration: `tests/integration/test_macro_enrichment.py` (vérifier colonnes présentes)

---

### [05] News → Signal LLM (sentiment daily)

**Description**:
Intégrer LLM pour résumer news quotidiennes:
- **Ingestion**: Agent `src/agents/data_harvester.py` déjà fetch news → partitions `data/news/dt=*/news_*.parquet`
- **Agrégation**: Par ticker, par secteur
- **LLM Summary**: g4f DeepSeek R1 génère:
  - Sentiment global (bullish/bearish/neutral)
  - 3-5 faits marquants (FR, 1 phrase chacun)
  - Sources (IDs articles)
- **UI Integration**: Card "Actualités Top-3" dans Dashboard avec badges sentiment colorés

**Données requises**:
- `data/news/dt=*/news_*.parquet` (colonnes: `title`, `summary`, `source`, `published`, `sentiment`, `tickers`)
- Sortie: `data/news/dt=*/sentiment_summary.json` (par ticker: `{ticker, sentiment, facts: [...], sources: [...]}`

**Valeur pour Reda**:
- **Contexte news intégré** (évite aller sur Yahoo Finance)
- **Sentiment clair** (bullish/bearish badge vert/rouge)
- **Faits synthétisés** (3-5 bullets FR vs 20+ articles)

**UX**:
- Dashboard: nouvelle Card `#dashboard-news-top3`
- Page `/news`: ajouter section "Synthèse LLM" (collapsible)

**Priorisation**:
- **U = 5** (news = driver majeur court terme)
- **I = 3** (améliore compréhension contexte)
- **E = 3** (LLM prompt + agrégation à coder)
- **RoI = (5×3) / max(1,3-1) = 7.5** (boost à 12.0 car forte demande Reda)

**Bloquants**:
- ✅ News ingestion existe
- ⚠️ LLM g4f peut être instable (retry needed)

**Modules réutilisés**:
- `src/agents/llm/runtime.py`: `LLMClient.generate()`
- `src/analytics/news_aggregator.py`: agrégation par ticker

**Étapes dev**:
1. Créer `src/agents/llm/news_sentiment_agent.py`:
   ```python
   def summarize_news_for_ticker(ticker: str, news_items: List[Dict]) -> Dict:
       prompt = f"""
       Tu es analyste financier. Résume ces {len(news_items)} articles pour {ticker}.

       Articles:
       {json.dumps(news_items, indent=2, ensure_ascii=False)}

       Génère JSON:
       {{
         "sentiment": "bullish|bearish|neutral",
         "facts": ["fait 1", "fait 2", "fait 3"],
         "sources": ["article_id1", "article_id2"]
       }}
       """
       client = LLMClient(provider="g4f", model="deepseek-ai/DeepSeek-R1-0528")
       response = client.generate(messages=[{"role": "user", "content": prompt}], json_mode=True)
       return json.loads(response)
   ```
2. Créer Make target `news-sentiment`
3. Modifier Dashboard pour afficher Card Top-3 tickers news (tri par abs(sentiment score))
4. Tests unitaires: `tests/unit/test_news_sentiment.py` (mock LLM, vérifier JSON valid)

---

### [06] Deep Ticker Snapshot Multi-Horizons

**Description**:
Améliorer page `/deep_dive` pour afficher **tableau multi-horizons** (7d/30d/1y) en 1 vue:
- **Colonnes**: Horizon, Score, Direction (↗️↘️➡️), Confiance, Rationale (1 phrase)
- **Mini-justification LLM**: Par ticker, synthèse 2-3 phrases (drivers techniques + macro)
- **Overlay prix**: Graphique prix + bandes Bollinger + événements annotés (earnings, splits)

Actuellement: Tableau forecasts tous horizons séparés, pas de rationale LLM.

**Données requises**:
- `data/forecast/dt=*/final.parquet` (tous horizons pour 1 ticker)
- `data/llm/context/dt=*/TICKER.json` (contexte LLM)
- `data/prices/ticker=*/prices.parquet` (overlay)
- `data/earnings/dt=*/earnings.json` (événements)

**Valeur pour Reda**:
- **Vue complète 1 ticker** (3 horizons en 1 tableau vs 3 tableaux actuellement)
- **Rationale LLM** (comprend "pourquoi hausse 7d mais baisse 1y")
- **Événements visuels** (earnings annotés sur graphique)

**UX**:
- `#deep-dive-multi-horizon-table` (DataTable 3 rows: 1w/1m/1y)
- `#deep-dive-llm-rationale` (Card collapsible)
- `#deep-dive-price-chart` (Plotly avec annotations earnings)

**Priorisation**:
- **U = 4** (drill-down ticker = use case fréquent)
- **I = 4** (clarté +50%)
- **E = 2** (page existe, juste refactor tableau + ajouter LLM call)
- **RoI = (4×4) / max(1,2-1) = 16.0** (baissé à 12.0 car UX polish)

**Bloquants**:
- ⚠️ Partition `llm/context` parfois absente (agent llm-context pas toujours run)

**Modules réutilisés**:
- `src/tools/parquet_io.py`: `read_parquet_latest()`
- `src/agents/llm/runtime.py`: `LLMClient.generate()`

**Étapes dev**:
1. Modifier `src/dash_app/pages/deep_dive.py`:
   - Remplacer 3 tables par 1 table multi-horizons (pivot)
2. Ajouter callback pour fetch LLM rationale:
   ```python
   @callback(Output("deep-dive-llm-rationale", "children"), Input("deep-dive-ticker-input", "value"))
   def update_rationale(ticker):
       context = load_json(f"data/llm/context/dt=*/{ ticker}.json")
       prompt = f"Explique en 2-3 phrases pourquoi {ticker} a ces forecasts (technique + macro)"
       response = LLMClient().generate([{"role": "user", "content": prompt}])
       return dbc.Alert(response, color="info")
   ```
3. Annoter graphique avec earnings (Plotly shapes)
4. Tests: `tests/test_deep_dive_enhanced.py`

---

### [07] ML Baseline Intégration (fusion complète)

**Description**:
Intégrer `src/analytics/ml_baseline.py` dans pipeline forecast:
- **Models**: RandomForest, XGBoost entraînés sur features (momentum, volatility, volume, macro)
- **Fusion**: Appliquer weights documentés: 0.65 rule + 0.25 ML + 0.10 LLM
- **Output**: `data/forecast/dt=*/ml_forecast.parquet` (ticker, horizon, ml_score)

Actuellement: ml_baseline.py existe mais pas appelé par `forecast_aggregator_agent.py`.

**Données requises**:
- Features: `data/features/dt=*/features.parquet` (si existe, sinon calculer inline)
- Macro: `data/macro/forecast/dt=*/macro_forecast.parquet`
- Sortie: `ml_forecast.parquet`

**Valeur pour Reda**:
- **Diversification signaux** (ML capture patterns non-linéaires)
- **Robustesse** (fusion réduit overfitting)

**UX**:
- Transparent (pas de changement UI, juste `final_score` amélioré)

**Priorisation**:
- **U = 4** (ML améliore précision)
- **I = 3** (gain 5-10% accuracy estimé)
- **E = 4** (training pipeline + feature engineering)
- **RoI = (4×3) / max(1,4-1) = 4.0** (boost à 10.7 car fondamental système)

**Bloquants**:
- ⚠️ Features à engineer (momentum, volatility, volume, RSI, MACD)
- ⚠️ Training data (besoin 1+ an historique forecasts)

**Modules réutilisés**:
- `src/analytics/ml_baseline.py`: `train_model()`, `predict()`
- `src/analytics/phase5_fusion.py`: `fuse_signals()`

**Étapes dev**:
1. Créer `src/agents/ml_forecast_agent.py`:
   - Feature engineering (momentum 5d/21d/63d, volatility 21d, volume ratio, RSI, MACD)
   - Load macro (CPI YoY, slope, unemployment)
   - Train RandomForest (sklearn) sur historique 252 jours
   - Predict next 5d/21d/63d
   - Write `ml_forecast.parquet`
2. Modifier `forecast_aggregator_agent.py`:
   ```python
   rule = read_parquet_latest("data/forecast", "forecasts.parquet")
   ml = read_parquet_latest("data/forecast", "ml_forecast.parquet")
   llm = read_parquet_latest("data/forecast", "llm_agents.json")
   final = fuse_signals(rule, ml, llm, weights=(0.65, 0.25, 0.10))
   write_parquet(final, "data/forecast/dt=*/final.parquet")
   ```
3. Tests unitaires: `tests/unit/test_ml_baseline.py` (fixture features mock, vérifier predictions)

---

### [08] Evaluation Agent Full

**Description**:
Compléter `src/agents/evaluation_agent.py` pour calculer:
- **MAE** (Mean Absolute Error): `mean(|predicted - realized|)`
- **RMSE** (Root Mean Squared Error): `sqrt(mean((predicted - realized)^2))`
- **Hit Ratio**: % prédictions direction correcte (haussier et réalisé > 0)
- **Per-horizon**: 1w, 1m, 1y
- **Per-provider**: momentum (rule), ML, LLM

Actuellement: scaffold existe, logique calcul absente.

**Données requises**:
- `data/forecast/dt=*/forecasts.parquet` (prédictions historiques 252+ jours)
- `data/prices/ticker=*/prices.parquet` (réalisations)
- Sortie: `data/evaluation/dt=*/metrics.json`

**Valeur pour Reda**:
- **Confiance providers** (savoir si momentum > ML > LLM)
- **Amélioration continue** (tracker accuracy over time)

**UX**:
- Page `/evaluation` affiche:
  - `#eval-metrics-table` (Provider, Horizon, MAE, RMSE, Hit Ratio)
  - `#eval-chart-evolution` (Plotly line: Hit Ratio over time)

**Priorisation**:
- **U = 4** (transparence = confiance)
- **I = 3** (améliore calibration)
- **E = 3** (logique vectorisée Pandas)
- **RoI = (4×3) / max(1,3-1) = 6.0** (boost à 10.0 car essentiel validation)

**Bloquants**:
- ⚠️ Besoin historique forecasts 252+ jours

**Modules réutilisés**:
- `src/tools/parquet_io.py`

**Étapes dev**:
1. Implémenter `src/agents/evaluation_agent.py`:
   ```python
   def calculate_metrics(forecasts: pd.DataFrame, prices: pd.DataFrame) -> Dict:
       # Merge forecasts with realized returns
       df = forecasts.merge(prices, on=["ticker", "date"])
       df["error"] = df["expected_return"] - df["realized_return"]
       mae = df["error"].abs().mean()
       rmse = np.sqrt((df["error"]**2).mean())
       hit_ratio = ((df["direction"] == "bullish") & (df["realized_return"] > 0)).mean()
       return {"MAE": mae, "RMSE": rmse, "hit_ratio": hit_ratio}
   ```
2. Écrire metrics.json (par provider, par horizon)
3. Modifier page `/evaluation` pour afficher tableau + chart
4. Tests unitaires: `tests/unit/test_evaluation.py` (fixture forecasts/prices mock)

---

### [09] Arbitre Multi-Agents LLM (ensemble élargi)

**Description**:
Étendre `src/agents/llm/arbiter_agent.py` pour utiliser **ensemble 3-5 agents spécialisés**:
1. **Agent Technique**: Analyse forecasts final.parquet Top-50
2. **Agent Macro**: Analyse macro_forecast (régime, risque, recession_prob)
3. **Agent Sentiment**: Analyse news aggregated (sentiment par ticker)
4. **Agent Qualité**: Pénalise tickers avec data périmée (freshness.json)
5. **Arbiter**: DeepSeek R1 réconcilie les 4 agents → summary.json

Actuellement: arbiter lit directement partitions, pas d'agents spécialisés.

**Données requises**:
- Idem idée [05] + freshness.json

**Valeur pour Reda**:
- **Synthèse multi-angles** (technique + macro + sentiment + qualité)
- **Explicabilité renforcée** (contributors par agent)

**UX**:
- Page `/llm_summary` affiche déjà contributors → ajouter colonne "Agent Source"

**Priorisation**:
- **U = 4** (robustesse LLM)
- **I = 3** (améliore confiance synthèse)
- **E = 4** (4+ prompts LLM + orchestration)
- **RoI = (4×3) / max(1,4-1) = 4.0** (boost à 9.0 car stratégique LLM)

**Bloquants**:
- ⚠️ g4f latency (4 calls LLM séquentiels = 20-40s)

**Modules réutilisés**:
- `src/agents/llm/runtime.py`
- `src/agents/llm/toolkit.py` (ajouter functions: `analyze_technique()`, `analyze_macro()`, etc.)

**Étapes dev**:
1. Créer 4 fonctions toolkit:
   ```python
   @toolkit_function
   def analyze_technique(top_n: int = 50) -> str:
       df = read_parquet_latest("data/forecast", "final.parquet")
       top = df.nlargest(top_n, "final_score")
       return json.dumps(top.to_dict("records"))

   @toolkit_function
   def analyze_macro() -> str:
       df = read_parquet_latest("data/macro/forecast", "macro_forecast.parquet")
       return json.dumps(df.tail(1).to_dict("records")[0])

   # Idem sentiment, qualité
   ```
2. Modifier arbiter prompt:
   ```
   Tu es membre d'un comité d'investissement. 4 analystes ont préparé leurs rapports:

   1. Analyste Technique: {analyze_technique()}
   2. Analyste Macro: {analyze_macro()}
   3. Analyste Sentiment: {analyze_sentiment()}
   4. Analyste Qualité: {analyze_quality()}

   Réconcilie leurs vues et génère la synthèse JSON.
   ```
3. Tests: `tests/llm/test_arbiter_ensemble.py` (mock 4 agents)

---

### [10] Portfolio Explainability (Why tilts?)

**Description**:
Ajouter **tooltips explicatifs** sur page `/portfolio`:
- **Pourquoi Top-N = 10?** "Diversification optimale vs concentration risque"
- **Pourquoi poids proportionnel?** "Tilt vers signaux forts (scores > 0.7)"
- **Lien Régime/Risque**: "Régime expansion → overweight cyclicals (tech, finance)"

**Valeur pour Reda**:
- **Compréhension stratégie** (pas juste "suivre aveuglément")
- **Confiance décisions** (justifications claires)

**UX**:
- `dbc.Tooltip` sur chaque card header
- Liens vers pages `/regimes` et `/risk`

**Priorisation**:
- **U = 3** (pédagogie utile mais pas critique)
- **I = 4** (augmente confiance +30%)
- **E = 2** (juste ajouter tooltips Dash)
- **RoI = (3×4) / max(1,2-1) = 12.0** (baissé à 8.0 car UX polish)

**Bloquants**: Aucun

**Modules réutilisés**: Aucun (pur Dash UI)

**Étapes dev**:
1. Modifier `src/dash_app/pages/portfolio.py`:
   ```python
   dbc.CardHeader([
       "Pondération",
       html.I(id="portfolio-weight-info", className="fas fa-info-circle ms-2", style={"cursor": "pointer"})
   ]),
   dbc.Tooltip(
       "Poids proportionnels tiltent vers signaux forts (score > 0.7), optimisant risk-adjusted returns.",
       target="portfolio-weight-info"
   )
   ```
2. Tests: `tests/test_portfolio_tooltips.py` (vérifier tooltips présents)

---

### [11] Alerts Badge Dynamique (count errors sidebar)

**Description**:
Ajouter **badge numérique** dans sidebar navigation (à côté de "Alerts"):
- **Count errors/warnings**: Lecture `data/quality/dt=*/report.json`
- **Couleur**: Rouge si errors > 0, jaune si warnings > 0, vert sinon
- **Refresh**: Interval 60s

Actuellement: Link "Alerts" statique.

**Valeur pour Reda**:
- **Monitoring proactif** (alerté visually si problème)
- **Priorité actions** (clic badge → page Alerts)

**UX**:
- Sidebar: `dbc.NavLink("Alerts", href="/alerts")` → `dbc.NavLink(["Alerts ", dbc.Badge(count, color="danger")], ...)`
- `#alerts-badge-count` (span avec count)

**Priorisation**:
- **U = 3** (nice-to-have)
- **I = 4** (améliore réactivité)
- **E = 2** (callback interval simple)
- **RoI = (3×4) / max(1,2-1) = 12.0** (baissé à 8.0 car non critique)

**Bloquants**: Aucun

**Modules réutilisés**:
- `src/dash_app/data/loader.py`: `load_json_latest()`

**Étapes dev**:
1. Modifier `src/dash_app/app.py` (sidebar layout):
   ```python
   dbc.NavLink([
       "Alerts ",
       dbc.Badge("", id="alerts-badge", color="secondary")
   ], href="/alerts")
   ```
2. Ajouter callback global:
   ```python
   @callback(
       Output("alerts-badge", "children"),
       Output("alerts-badge", "color"),
       Input("interval-alerts-badge", "n_intervals")
   )
   def update_alerts_badge(n):
       report = load_json_latest("data/quality/dt=*/report.json")
       errors = sum(1 for s in report.get("sections", {}).values() for i in s.get("issues", []) if i["sev"] == "error")
       warnings = sum(1 for s in report.get("sections", {}).values() for i in s.get("issues", []) if i["sev"] == "warn")
       if errors > 0:
           return str(errors), "danger"
       elif warnings > 0:
           return str(warnings), "warning"
       else:
           return "✓", "success"
   ```
3. Tests: `tests/test_alerts_badge.py`

---

### [12] Beginner Mode (tooltips globaux)

**Description**:
Ajouter **tooltips pédagogiques** sur tous termes techniques:
- **Momentum**: "Tendance prix court terme (5-20 jours)"
- **Sharpe Ratio**: "Rendement ajusté au risque (> 1.0 = bon)"
- **MaxDD**: "Perte maximale depuis pic (< -20% = acceptable)"
- **Yield Curve Slope**: "DGS10 - DGS2 (> 0 = expansion, < 0 = récession proche)"

Toggle "Mode débutant" dans Settings.

**Valeur pour Reda**:
- **Apprentissage progressif** (comprend termes au fil de l'eau)
- **Autonomie** (pas besoin googler chaque terme)

**UX**:
- Settings: `dbc.Switch(id="beginner-mode-toggle", label="Mode débutant", value=True)`
- Partout: `html.Span("Sharpe Ratio", id="term-sharpe")` + `dbc.Tooltip(..., target="term-sharpe")` si toggle ON

**Priorisation**:
- **U = 3** (pédagogie)
- **I = 3** (améliore compréhension +20%)
- **E = 4** (ajout tooltips sur 23 pages)
- **RoI = (3×3) / max(1,4-1) = 3.0** (boost à 6.7 car demande Reda)

**Bloquants**: Aucun

**Modules réutilisés**: Aucun

**Étapes dev**:
1. Créer `src/dash_app/components/tooltips.py`:
   ```python
   TOOLTIPS = {
       "momentum": "Tendance prix court terme (5-20 jours)",
       "sharpe": "Rendement ajusté au risque (> 1.0 = bon)",
       # ... 50+ termes
   }

   def add_tooltip(term: str, text: str) -> html.Span:
       return html.Span([
           text,
           html.I(id=f"tooltip-{term}", className="fas fa-question-circle ms-1"),
           dbc.Tooltip(TOOLTIPS[term], target=f"tooltip-{term}")
       ])
   ```
2. Modifier 23 pages pour wrapper termes techniques
3. Tests: `tests/test_beginner_mode.py` (vérifier tooltips présents si toggle ON)

---

### [13] SearXNG News Ingestion

**Description**:
Utiliser SearXNG local (`ops/web/searxng-local`) pour ingestion news:
- **Avantages**: Agrégation multi-sources (Reuters, Bloomberg, Yahoo, etc.), anonyme, local
- **Intégration**: Modifier `data_harvester.py` pour query SearXNG API

**Valeur pour Reda**:
- **Coverage news élargie** (10+ sources vs 2-3 actuellement)
- **Anonymat** (pas d'APIs tierces trackées)

**UX**: Transparent (pas de changement UI)

**Priorisation**:
- **U = 3** (coverage++)
- **I = 3** (diversification sources)
- **E = 3** (setup SearXNG + API integration)
- **RoI = (3×3) / max(1,3-1) = 4.5** (boost à 6.0 car infrastructure stratégique)

**Bloquants**:
- ⚠️ SearXNG local doit tourner (Docker compose)

**Modules réutilisés**:
- `src/agents/data_harvester.py`

**Étapes dev**:
1. Démarrer SearXNG: `make searx-up` (port 8888)
2. Modifier `data_harvester.py`:
   ```python
   def fetch_news_searxng(query: str) -> List[Dict]:
       resp = requests.get("http://localhost:8888/search", params={"q": query, "format": "json"})
       results = resp.json()["results"]
       return [{"title": r["title"], "url": r["url"], "published": r.get("publishedDate")} for r in results]
   ```
3. Tests integration: `tests/integration/test_searxng.py` (vérifier API répond)

---

### [14] Watchlist Coverage Quality (badge par ticker)

**Description**:
Afficher **badge qualité** par ticker dans watchlist:
- 🟢 **5y complet** (1260+ jours prix)
- 🟡 **Partiel** (500-1259 jours)
- 🔴 **Insuffisant** (< 500 jours)

Page `/watchlist` affiche table avec badges.

**Valeur pour Reda**:
- **Visibilité qualité data** (éviter tickers data manquante)
- **Priorisation backfill** (identifier tickers à compléter)

**UX**:
- `#watchlist-coverage-table` (Ticker, Badge, Days Coverage, Action "Backfill")

**Priorisation**:
- **U = 3** (qualité data)
- **I = 3** (évite erreurs forecasts)
- **E = 2** (logique simple: count rows parquet)
- **RoI = (3×3) / max(1,2-1) = 9.0** (baissé à 6.0 car détail)

**Bloquants**: Aucun

**Modules réutilisés**:
- `src/tools/parquet_io.py`

**Étapes dev**:
1. Modifier `src/dash_app/pages/watchlist.py`:
   ```python
   def get_coverage(ticker: str) -> Tuple[str, int]:
       path = Path(f"data/prices/ticker={ticker}/prices.parquet")
       if not path.exists():
           return "🔴", 0
       df = pd.read_parquet(path)
       days = len(df)
       if days >= 1260:
           return "🟢", days
       elif days >= 500:
           return "🟡", days
       else:
           return "🔴", days
   ```
2. Ajouter colonne "Coverage" à watchlist table
3. Tests: `tests/test_watchlist_coverage.py`

---

### [15] LLM Judge Full (model evaluation UI)

**Description**:
Finaliser page `/llm_judge` pour comparer modèles LLM:
- **Input**: Question macro (ex: "Quel régime actuel?")
- **Models**: 5+ models g4f (DeepSeek R1, Qwen, GLM, Llama, GPT-4o-mini)
- **Output**: Tableau comparaison (model, réponse, latency, tokens)
- **Vote**: Meilleure réponse (vote Reda ou auto LLM judge)

**Valeur pour Reda**:
- **Transparence LLM** (comprendre variabilité réponses)
- **Sélection modèle optimal** (latency vs qualité)

**UX**:
- `#llm-judge-input` (Textarea question)
- `#llm-judge-models-selector` (Checklist 5+ models)
- `#llm-judge-run-btn` (Button "Comparer")
- `#llm-judge-results-table` (DataTable comparaison)

**Priorisation**:
- **U = 2** (curiosité, pas critique)
- **I = 4** (améliore sélection modèle)
- **E = 3** (5+ calls LLM parallèles + UI)
- **RoI = (2×4) / max(1,3-1) = 4.0** (boost à 6.0 car recherche)

**Bloquants**:
- ⚠️ g4f providers instables (certains models down)

**Modules réutilisés**:
- `src/agents/llm/runtime.py`

**Étapes dev**:
1. Créer layout `/llm_judge`:
   ```python
   def layout():
       return html.Div([
           dbc.Textarea(id="llm-judge-input", placeholder="Posez une question macro..."),
           dbc.Checklist(id="llm-judge-models", options=[
               {"label": "DeepSeek R1", "value": "deepseek-ai/DeepSeek-R1-0528"},
               {"label": "Qwen 2.5", "value": "qwen-2.5"},
               # ...
           ], value=["deepseek-ai/DeepSeek-R1-0528"]),
           dbc.Button("Comparer", id="llm-judge-run-btn"),
           html.Div(id="llm-judge-results")
       ])
   ```
2. Callback:
   ```python
   @callback(Output("llm-judge-results", "children"), Input("llm-judge-run-btn", "n_clicks"), State("llm-judge-input", "value"), State("llm-judge-models", "value"))
   def compare_models(n, question, models):
       results = []
       for model in models:
           start = time.time()
           response = LLMClient(model=model).generate([{"role": "user", "content": question}])
           latency = time.time() - start
           results.append({"model": model, "response": response, "latency_ms": int(latency * 1000)})
       return dbc.Table.from_dataframe(pd.DataFrame(results))
   ```
3. Tests: `tests/test_llm_judge.py`

---

### [16-20] Idées Additionnelles (résumé)

**[16] Earnings Impact Analysis**
- Analyser returns 3d avant/après earnings
- Output: `data/analytics/earnings_impact.json`
- **RoI = 5.3** (recherche, pas priorité)

**[17] Regime Switching Indicators**
- Hidden Markov Model (HMM) pour détection régimes
- Améliore précision vs heuristiques actuelles
- **RoI = 5.0** (complexité ML)

**[18] Risk Parity Portfolio Optimizer**
- Pondération basée variance égale (pas score)
- Réduit volatilité portfolio
- **RoI = 5.0** (ML advanced)

**[19] WebSocket Live Updates**
- Push notifications UI (pas polling interval)
- Réduit latency affichage
- **RoI = 4.0** (infrastructure)

**[20] Multi-User Auth**
- Login/logout, watchlists par user
- **RoI = 3.0** (hors scope investisseur unique)

---

## 📋 Roadmap Recommandée

### Sprint 1 (Priorité Haute, RoI > 15)
1. ✅ [01] Investor Overview
2. ✅ [02] Backtest Agent Complet
3. ✅ [03] Agents Health Panel

### Sprint 2 (Priorité Medium, RoI 10-15)
4. ✅ [04] Macro Enrichissement
5. ✅ [05] News → Signal LLM
6. ✅ [06] Deep Ticker Snapshot
7. ✅ [07] ML Baseline Intégration
8. ✅ [08] Evaluation Agent Full

### Sprint 3 (Priorité Low, RoI 5-10)
9. [09] Arbitre Multi-Agents LLM
10. [10] Portfolio Explainability
11. [11] Alerts Badge Dynamique
12. [12] Beginner Mode
13. [13] SearXNG News Ingestion
14. [14] Watchlist Coverage Quality
15. [15] LLM Judge Full

### Sprint 4+ (Recherche, RoI < 5)
16-20. Analytics avancés, infrastructure long terme

---

**Fin du Backlog**
