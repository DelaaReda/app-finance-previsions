# 📅 Plan d'Implémentation — Architecture Sprint

**Date**: 2025-10-29
**Architecte**: Claude Sonnet 4.5
**Durée Estimée**: 3 sprints (6 semaines, 2 semaines/sprint)
**Équipe**: 2 dev + 1 QA (Reda)

---

## 🎯 Objectifs Globaux

1. **Sprint 1 (S1)**: Livrer 3 pages prioritaires haute valeur (RoI > 15)
2. **Sprint 2 (S2)**: Enrichir données + intégrer ML baseline + News LLM
3. **Sprint 3 (S3)**: Polish UX + analytics avancés + monitoring

**Critères de Succès**:
- **Sprint 1**: Reda peut prendre décision investissement en < 2 min (vs 10 min actuellement)
- **Sprint 2**: Coverage macro complète (10+ indicateurs), forecasts accuracy > 55%
- **Sprint 3**: Beginner mode actif, backtests validés, deployment production-ready

---

## 🏃 Sprint 1 — Pages Haute Valeur (Semaines 1-2)

### Objectif
Livrer **3 pages critiques** permettant workflow Reda complet:
1. Investor Overview (vue 360°)
2. Backtest Agent Complet (validation stratégie)
3. Agents Health Panel (monitoring + actions manuelles)

---

### 📦 Livrables

#### [S1.1] Investor Overview — Page Intégrée
**Assigné**: Dev 1
**Durée**: 3 jours

**Tâches**:
1. ✅ Lire page actuelle `/integration_overview` → identifier gaps
   - Fichier: `src/dash_app/pages/integration_overview.py:1`
   - Commandes: `grep -r "integration_overview" src/dash_app/`

2. 🔧 Enrichir `macro_forecast_agent.py` pour inclure `regime` et `risk_level`
   - Fichier: `src/agents/macro_forecast_agent.py:50`
   - Logique:
     ```python
     def classify_regime(inflation_yoy, yield_curve_slope, unemployment):
         if yield_curve_slope > 0.5 and inflation_yoy < 3.0 and unemployment < 5.0:
             return "expansion_modérée"
         elif yield_curve_slope < -0.5 or unemployment > 6.0:
             return "contraction"
         elif inflation_yoy > 4.0:
             return "désinflation"
         else:
             return "incertain"

     def classify_risk(unemployment, vix=None, recession_prob=0.0):
         if unemployment > 5.5 or (vix and vix > 25) or recession_prob > 0.5:
             return "high"
         elif unemployment > 4.5 or (vix and vix > 20):
             return "medium"
         else:
             return "low"
     ```
   - Ajouter colonnes à DataFrame, écrire parquet
   - **Make target**: `macro-forecast`

3. 🎨 Créer layout Overview avec 5 cartes (spec complète dans `docs/implementation/page_specs/investor_overview.md`)
   - Cartes: Régime, Risque, Top-10 Equity, Top-5 Commodities, Synthèse LLM
   - IDs testables: `#overview-regime-card`, `#overview-risk-card`, etc.
   - Empty states FR systématiques

4. 🔄 Implémenter callbacks:
   - Callback bouton "Relancer LLM" (avec lock + logs live)
   - Callback interval refresh logs (4s)
   - Callback export CSV Top-10

5. 🧪 Tests:
   - `tests/e2e/test_overview_page.py`: Route 200, empty states, callbacks
   - `tests/integration/test_macro_enriched.py`: Vérifier colonnes `regime`, `risk_level` présentes
   - UI health: Screenshot sans .alert-danger

6. 📝 Retirer gate `DEVTOOLS_ENABLED` pour route `/integration_overview`
   - Fichier: `src/dash_app/app.py` (remove conditional page registration)

**Dépendances**: Aucune (modules existants)

**Bloquants Potentiels**:
- ⚠️ LLM summary partition peut être absente → Empty state géré
- ⚠️ Macro forecast pas de `regime`/`risk_level` → Ajout obligatoire task 2

**DoD**:
- [ ] Page accessible `/integration_overview` (production)
- [ ] 5 cartes affichées avec données réelles
- [ ] Bouton LLM fonctionne (logs + lock)
- [ ] Tests passent (3 tests E2E + 1 integration)
- [ ] UI health screenshot OK

---

#### [S1.2] Backtest Agent Complet
**Assigné**: Dev 2
**Durée**: 4 jours

**Tâches**:
1. 📖 Lire agent actuel `src/agents/backtest_agent.py` → analyser ce qui existe
   - Actuellement: `details.parquet` écrit mais pas equity curve

2. 🔧 Implémenter equity curve génération:
   ```python
   def generate_equity_curve(forecasts_hist: pd.DataFrame, prices_hist: Dict[str, pd.DataFrame], top_n: int = 10, rebalance_freq: str = "weekly") -> pd.DataFrame:
       """
       Walk-forward backtest:
       - Chaque période (jour/semaine), lire forecasts dt-1
       - Sélectionner Top-N par final_score
       - Hold jusqu'à prochain rebalance
       - Calculer return period
       - Cumul equity curve
       """
       dates = sorted(forecasts_hist["dt"].unique())
       equity = 1.0  # Start with $1
       equity_curve = []

       for i, date in enumerate(dates):
           # Read forecasts from previous period
           if i == 0:
               continue
           prev_forecasts = forecasts_hist[forecasts_hist["dt"] == dates[i-1]]
           top_tickers = prev_forecasts.nlargest(top_n, "final_score")["ticker"].tolist()

           # Calculate period return (equal weight)
           period_returns = []
           for ticker in top_tickers:
               if ticker in prices_hist:
                   price_df = prices_hist[ticker]
                   price_start = price_df[price_df["date"] == dates[i-1]]["Close"].iloc[0]
                   price_end = price_df[price_df["date"] == date]["Close"].iloc[0]
                   ret = (price_end - price_start) / price_start
                   period_returns.append(ret)

           # Portfolio return (equal weight)
           portfolio_ret = np.mean(period_returns) if period_returns else 0.0
           equity *= (1 + portfolio_ret)
           equity_curve.append({"date": date, "strategy": "Top-N", "equity": equity})

       return pd.DataFrame(equity_curve)
   ```

3. 🔧 Calculer metrics complètes:
   ```python
   def calculate_metrics(equity_curve: pd.DataFrame) -> Dict:
       returns = equity_curve["equity"].pct_change().dropna()
       days = len(equity_curve)

       cagr = (equity_curve["equity"].iloc[-1] / equity_curve["equity"].iloc[0]) ** (252 / days) - 1
       sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0.0
       sortino = returns.mean() / returns[returns < 0].std() * np.sqrt(252) if len(returns[returns < 0]) > 0 else 0.0

       # MaxDD
       cummax = equity_curve["equity"].cummax()
       drawdown = (equity_curve["equity"] - cummax) / cummax
       max_dd = drawdown.min()

       win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0.0

       return {
           "CAGR": cagr,
           "Sharpe": sharpe,
           "Sortino": sortino,
           "MaxDD": max_dd,
           "win_rate": win_rate,
           "avg_return": returns.mean(),
           "count_days": days
       }
   ```

4. 🔧 Fetch SPY baseline (yfinance) pour comparaison
   ```python
   import yfinance as yf
   spy = yf.download("SPY", start=start_date, end=end_date)
   spy_equity = (1 + spy["Close"].pct_change()).cumprod()
   ```

5. 📝 Écrire partitions:
   - `data/backtest/dt=YYYYMMDD/results.parquet` (equity curve: date, strategy, equity)
   - `data/backtest/dt=YYYYMMDD/summary.json` (metrics dict)

6. 🎨 Améliorer page `/backtests`:
   - Chart Plotly: 2 traces (Top-N vs SPY)
   - Metrics cards: Grid 2×3 (CAGR, Sharpe, Sortino, MaxDD, Win Rate, Avg Return)
   - Comparison table: Strategy | CAGR | Sharpe | MaxDD

7. 🧪 Tests unitaires:
   - `tests/unit/test_backtest_metrics.py`: Fixture prix mock, vérifier CAGR/Sharpe calcul
   - `tests/integration/test_backtest_agent.py`: Run agent, vérifier `results.parquet` + `summary.json` écrits

**Dépendances**:
- ✅ `forecasts.parquet` historique 252+ jours (vérifier coverage)
- ✅ `prices.parquet` 5y disponibles

**Bloquants Potentiels**:
- ⚠️ Historique forecasts < 252 jours → utiliser ce qui existe, noter limitation

**DoD**:
- [ ] Agent génère equity curve + metrics
- [ ] Page `/backtests` affiche chart + metrics cards
- [ ] Tests unitaires passent (metrics calculation)
- [ ] Tests integration passent (agent run)

---

#### [S1.3] Agents Health Panel
**Assigné**: Dev 1
**Durée**: 3 jours

**Tâches**:
1. 🔧 Créer `src/tools/lock.py`:
   ```python
   from pathlib import Path
   import time

   def acquire_lock(name: str, ttl: int = 3600) -> bool:
       lock_path = Path("artifacts/locks") / f"{name}.lock"
       lock_path.parent.mkdir(parents=True, exist_ok=True)

       if lock_path.exists():
           age = time.time() - lock_path.stat().st_mtime
           if age < ttl:
               return False  # Lock held
           else:
               lock_path.unlink()  # Expired, remove

       lock_path.write_text(str(time.time()))
       return True

   def release_lock(name: str):
       lock_path = Path("artifacts/locks") / f"{name}.lock"
       if lock_path.exists():
           lock_path.unlink()
   ```

2. 📖 Lire page actuelle `/integration_agents_health` → identifier ce qui manque
   - Actuellement: Table statique freshness, pas d'actions

3. 🎨 Ajouter actions manuelles:
   - Colonne "Action" dans table avec boutons (1 par agent)
   - IDs: `#agents-health-action-equity-forecast`, `#agents-health-action-macro-forecast`, etc.
   - Bouton disabled si lock held

4. 🔄 Implémenter callbacks actions:
   ```python
   @callback(
       Output("agents-health-action-equity-forecast", "disabled"),
       Output("agents-health-log-equity-forecast", "children"),
       Input("agents-health-action-equity-forecast", "n_clicks"),
       prevent_initial_call=True
   )
   def run_equity_forecast_manual(n):
       if not n:
           raise PreventUpdate

       if not acquire_lock("equity-forecast"):
           return True, dbc.Alert("Agent déjà en cours.", color="warning")

       try:
           result = run_make("equity-forecast", timeout=900)
           return False, dbc.Alert(result["stdout"], color="info" if result["returncode"] == 0 else "danger")
       finally:
           release_lock("equity-forecast")
   ```

5. 🔄 Logs live (interval 4s refresh):
   - Div logs par agent (collapsible)
   - Interval component refresh logs pendant exécution

6. 🎨 Pipeline DAG visual (optionnel, nice-to-have):
   - Mermaid diagram ou Plotly sankey
   - Affiche dépendances: `update-monitor → equity-forecast → forecast-aggregate → llm-summary`

7. 🧪 Tests:
   - `tests/e2e/test_agents_health_page.py`: Click bouton → logs appear → bouton re-enable

**Dépendances**:
- ✅ `src/tools/make.py` existe
- ✅ Freshness.json existe

**Bloquants Potentiels**: Aucun

**DoD**:
- [ ] Page affiche badges 🟢/🟡/🔴 par agent
- [ ] Boutons actions fonctionnent (lock + logs)
- [ ] Tests passent (callbacks)
- [ ] Lock mechanism testé unitairement

---

### 🧪 Sprint 1 — Tests & Validation

**Tests E2E** (dash.testing):
- `tests/e2e/test_overview_page.py` (3 tests)
- `tests/e2e/test_backtests_page.py` (2 tests)
- `tests/e2e/test_agents_health_page.py` (3 tests)

**Tests Integration**:
- `tests/integration/test_macro_enriched.py`
- `tests/integration/test_backtest_agent.py`

**Tests Unitaires**:
- `tests/unit/test_backtest_metrics.py`
- `tests/tools/test_lock.py`

**UI Health** (Playwright):
- Screenshots 3 pages (Overview, Backtests, Agents Health)
- Vérifier pas de `.alert-danger`

**DoD Sprint 1**:
- [ ] 3 pages livrées production-ready
- [ ] 12+ tests passent (E2E + integration + unit)
- [ ] UI health report vert
- [ ] Docs mises à jour (engineering_rules, module_index)
- [ ] Demo Reda OK (feedback positif)

---

## 🚀 Sprint 2 — Data Enrichment + ML + News (Semaines 3-4)

### Objectif
**Enrichir données** (macro 10+ indicateurs), **intégrer ML baseline** (fusion complète), **News LLM** (sentiment daily)

---

### 📦 Livrables

#### [S2.1] Macro Enrichissement
**Assigné**: Dev 2
**Durée**: 2 jours

**Tâches**:
1. Ajouter fetches FRED:
   - PMI: `MANEMP`
   - ISM: `NAPM`
   - LEI: `USSLIND`
   - Credit Spreads: `BAMLH0A0HYM2`

2. Ajouter fetch yfinance:
   - VIX: `^VIX`

3. Modifier `macro_forecast_agent.py` pour inclure colonnes
4. Modifier pages `/regimes` et `/risk` pour afficher nouveaux indicateurs
5. Tests integration: vérifier colonnes présentes

**DoD**:
- [ ] 5 nouveaux indicateurs macro disponibles
- [ ] Pages Risk/Regimes affichent graphiques enrichis

---

#### [S2.2] ML Baseline Intégration
**Assigné**: Dev 1
**Durée**: 4 jours

**Tâches**:
1. Créer `src/agents/ml_forecast_agent.py`:
   - Feature engineering (momentum 5d/21d/63d, volatility, RSI, MACD)
   - Load macro (CPI, slope, unemployment)
   - Train RandomForest sur historique 252 jours
   - Predict horizons 1w/1m/1y
   - Write `ml_forecast.parquet`

2. Modifier `forecast_aggregator_agent.py`:
   - Load rule (forecasts.parquet), ML (ml_forecast.parquet), LLM (llm_agents.json si existe)
   - Apply fusion: `final_score = 0.65*rule + 0.25*ML + 0.10*LLM`
   - Write `final.parquet`

3. Tests unitaires: `tests/unit/test_ml_baseline.py`
4. Make target: `ml-forecast`

**DoD**:
- [ ] Agent ML génère predictions
- [ ] Fusion 3-way appliquée (rule/ML/LLM)
- [ ] Tests passent

---

#### [S2.3] News → Signal LLM
**Assigné**: Dev 2
**Durée**: 3 jours

**Tâches**:
1. Créer `src/agents/llm/news_sentiment_agent.py`:
   - Load news derniers 7j
   - Aggregate par ticker
   - LLM summarize (sentiment + facts)
   - Write `sentiment_summary.json`

2. Modifier Dashboard:
   - Ajouter Card "Actualités Top-3" (tickers avec sentiment fort)
   - Badges colorés sentiment

3. Modifier page `/news`:
   - Section "Synthèse LLM" (collapsible)

4. Tests: mock LLM, vérifier JSON valid

**DoD**:
- [ ] Agent news sentiment fonctionne
- [ ] Dashboard affiche Top-3 news
- [ ] Tests passent

---

#### [S2.4] Evaluation Agent Full
**Assigné**: Dev 1
**Durée**: 2 jours

**Tâches**:
1. Implémenter calcul MAE/RMSE/hit_ratio
2. Écrire `metrics.json` (par horizon, par provider)
3. Modifier page `/evaluation` pour afficher tableau + chart
4. Tests unitaires

**DoD**:
- [ ] Page Evaluation affiche metrics
- [ ] Tests passent

---

### 🧪 Sprint 2 — Tests & Validation

**Tests Integration**:
- Macro enrichment (5 colonnes)
- ML forecast (predictions shape correct)
- News sentiment (JSON valid)
- Evaluation (metrics calculation)

**DoD Sprint 2**:
- [ ] 4 agents livrés (macro enriched, ML, news sentiment, evaluation)
- [ ] Fusion 3-way testée
- [ ] Tests passent (10+ tests)
- [ ] Demo Reda OK

---

## 🎨 Sprint 3 — UX Polish + Analytics + Deployment (Semaines 5-6)

### Objectif
**Polish UX** (beginner mode, tooltips, badges), **analytics avancés** (arbitre multi-agents), **deployment production**

---

### 📦 Livrables

#### [S3.1] Beginner Mode
**Assigné**: Dev 2
**Durée**: 3 jours

**Tâches**:
1. Créer `src/dash_app/components/tooltips.py` (dictionnaire 50+ termes)
2. Modifier Settings page: Toggle "Mode débutant"
3. Wrapper termes techniques sur 10 pages prioritaires
4. Tests: vérifier tooltips présents si toggle ON

**DoD**:
- [ ] Toggle Settings fonctionne
- [ ] 50+ tooltips disponibles
- [ ] 10 pages wrapped

---

#### [S3.2] Arbitre Multi-Agents LLM
**Assigné**: Dev 1
**Durée**: 3 jours

**Tâches**:
1. Créer 4 fonctions toolkit (technique, macro, sentiment, quality)
2. Modifier arbiter prompt (ensemble 4 agents)
3. Tests: mock 4 agents, vérifier synthèse

**DoD**:
- [ ] Arbitre utilise 4 agents
- [ ] Contributors table affiche source par agent
- [ ] Tests passent

---

#### [S3.3] Portfolio Explainability + Alerts Badge
**Assigné**: Dev 2
**Durée**: 2 jours

**Tâches**:
1. Ajouter tooltips page Portfolio (Why tilts?)
2. Ajouter badge dynamique Alerts sidebar (count errors)
3. Tests

**DoD**:
- [ ] Tooltips Portfolio présents
- [ ] Badge Alerts fonctionne (count live)

---

#### [S3.4] Deployment Production
**Assigné**: Dev 1 + Dev 2
**Durée**: 2 jours

**Tâches**:
1. Créer `docker-compose.yml` (Dash + agents scheduler)
2. Setup systemd service (APScheduler agents)
3. Documentation deployment (`docs/DEPLOYMENT.md`)
4. Tests smoke production-like environment

**DoD**:
- [ ] Docker compose fonctionne
- [ ] Agents scheduler 24/7
- [ ] Docs deployment complètes

---

### 🧪 Sprint 3 — Tests & Validation

**Tests E2E**:
- Beginner mode (tooltips)
- Portfolio tooltips
- Alerts badge

**Tests Integration**:
- Arbitre multi-agents

**DoD Sprint 3**:
- [ ] UX polish livré (beginner mode, tooltips, badges)
- [ ] Arbitre multi-agents fonctionne
- [ ] Deployment production-ready
- [ ] Demo finale Reda OK

---

## 📊 Récapitulatif Sprints

| Sprint | Livrables | Tests | Durée |
|--------|-----------|-------|-------|
| **S1** | 3 pages prioritaires (Overview, Backtests, Agents Health) | 12+ tests (E2E/integration/unit) | 2 sem |
| **S2** | Data enrichment (macro, ML, news, evaluation) | 10+ tests (integration/unit) | 2 sem |
| **S3** | UX polish (beginner mode, tooltips) + Deployment | 8+ tests (E2E) | 2 sem |
| **Total** | 10 features majeures | 30+ tests | 6 sem |

---

## 🛠️ Modules Réutilisés (Zéro Duplication)

### src/tools/
- ✅ `parquet_io.py`: Lecture partitions (tous agents/pages)
- ✅ `make.py`: Run Make targets (Agents Health, Observability)
- 🆕 `lock.py`: Locks anti-collision (S1.3)

### src/core/
- ✅ `io_utils.py`: Logging, JSON/Parquet I/O (tous agents)
- ✅ `market_data.py`: yfinance, FRED (agents forecast)
- ✅ `models.py`: Pydantic schemas (LLM, features)

### src/agents/llm/
- ✅ `runtime.py`: LLMClient (arbitre, news sentiment)
- ✅ `toolkit.py`: Functions registry (arbitre multi-agents)
- ✅ `schemas.py`: LLMEnsembleSummary (validation)

### src/dash_app/data/
- ✅ `loader.py`: Safe loaders (toutes pages)
- ✅ `paths.py`: Path helpers (pages Backtests, Risk, Regimes)

### src/analytics/
- ✅ `ml_baseline.py`: RandomForest/XGBoost (S2.2)
- ✅ `phase5_fusion.py`: Fusion rule (S2.2)
- ✅ `news_aggregator.py`: Agrégation news (S2.3)

---

## 🚨 Risques & Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **g4f instable** (> 50% échecs) | Moyen | Haut | Fallback Qwen/GLM, Plan B Ollama local |
| **Historique forecasts < 252j** | Faible | Moyen | Utiliser ce qui existe, noter limitation |
| **FRED rate limits** | Faible | Faible | Cache fetches, 1 run/day max |
| **Retards dev** (scope creep) | Moyen | Moyen | Priorisation stricte RoI, MVP first |
| **Bugs production** | Faible | Haut | Tests smoke avant chaque release, rollback plan |

---

## 📅 Jalons (Milestones)

- **M1 (Fin S1)**: Demo Reda avec 3 pages prioritaires ✅
- **M2 (Fin S2)**: Fusion ML complète + News LLM intégrés ✅
- **M3 (Fin S3)**: Production deployment + UX polish ✅
- **M4 (S3+1 semaine)**: Go-live production

---

## 🎓 Post-Mortem (à remplir après chaque sprint)

### Sprint 1
- **Ce qui a marché**: ...
- **Ce qui a bloqué**: ...
- **Leçons apprises**: ...
- **Ajustements S2**: ...

### Sprint 2
- ...

### Sprint 3
- ...

---

## 📚 Références

- **Backlog**: `docs/ideas/10_feature_backlog.md`
- **Page Specs**: `docs/implementation/page_specs/`
- **ADRs**: `docs/architecture/adr/`
- **Engineering Rules**: `docs/engineering_rules.md`
- **Module Index**: `docs/module_index.md`

---

**Version**: 1.0
**Next Review**: Fin Sprint 1 (retrospective)
