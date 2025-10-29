# 📐 Vision Architecturale — App Finance Prévisions

**Date**: 2025-10-29
**Architecte**: Claude Sonnet 4.5
**Projet**: app-finance-previsions (Reda - Investisseur Privé)

---

## 🎯 Mission

Fournir à **Reda** (investisseur privé, non-expert) un **assistant de décision financière** qui:

1. **Agrège** les signaux multiples (technique, macro, sentiment, LLM) en **recommandations claires**
2. **Explique** les drivers clés en français, sans jargon
3. **Alerte** sur les changements importants (qualité, mouvements, événements)
4. **Visualise** les données complexes de façon accessible (graphiques, badges, cartes)
5. **Automatise** la recherche quotidienne (actualisation horaire, rapports LLM)

---

## 🧭 Principes Directeurs

### 1. **Réutilisation > Duplication**
- Aucun doublon de logique/agents/outils
- Modules existants documentés dans `module_index.md`
- Pattern: chercher d'abord dans `src/tools/`, `src/core/`, `src/analytics/`

### 2. **Séparation des Responsabilités**
- **Agents** = compute + écriture partitions (`data/<domain>/dt=YYYYMMDD[HH]/`)
- **UI Dash** = lecture + filtrage + affichage (FR)
- **Aucun appel réseau depuis l'UI** (pas de yfinance, FRED, g4f dans callbacks)

### 3. **Historique & Fraîcheur**
- Minimum **5 ans** de données prix pour séries utilisées
- Partitions horodatées immutables (jamais réécrire l'historique)
- Monitoring continu de fraîcheur (`data/quality/dt=*/freshness.json`)

### 4. **UX pour Non-Experts**
- Labels **FR** partout (régime, risque, direction, confiance)
- États vides FR systématiques ("Aucune donnée disponible pour cette période")
- JSON brut dans **expander** ("Voir JSON")
- Graphiques lisibles (légendes, tooltips, badges colorés)

### 5. **Explicabilité & Confiance**
- Toujours sourcer les recommandations (technique, macro, news, LLM)
- Rationales stockées dans partitions (colonnes `rationale`, `drivers`)
- UI affiche **qui dit quoi** (contributors table dans LLM Summary)

### 6. **Robustesse & Logs**
- Logs utiles (pas de stacktraces dans UI)
- Retry automatique (LLM, API externes)
- Locks pour éviter collisions agents (`artifacts/locks/<name>.lock`, TTL 1h)
- Tests: smoke (routes 200), dash.testing (callbacks), Playwright (UI health)

---

## 🏗️ Architecture C4 — Contexte

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Reda (Investisseur Privé)                       │
│                    Navigateur Web (Firefox/Chrome)                      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP 8050
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               App Finance Prévisions (Dash UI + Agents)                 │
│                                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────────┐   │
│  │  Dash UI     │◄───│  Partitions  │◄───│  Agents (Forecast/LLM) │   │
│  │  (23 pages)  │    │  dt=YYYYMMDD │    │  (18 agents Python)    │   │
│  └──────────────┘    └──────────────┘    └─────────────────────────┘   │
│                                                       ▲                  │
│                                                       │                  │
└───────────────────────────────────────────────────────┼──────────────────┘
                                                        │
                      ┌─────────────────────────────────┼────────────────┐
                      │                                 │                │
                      ▼                                 ▼                ▼
              ┌───────────────┐              ┌──────────────┐  ┌──────────────┐
              │  yfinance API │              │   FRED API   │  │  g4f (LLM)   │
              │  (Prix equity/│              │  (Macro US)  │  │ (DeepSeek R1)│
              │   commodities)│              │              │  │              │
              └───────────────┘              └──────────────┘  └──────────────┘
```

---

## 📦 Architecture C4 — Conteneurs

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          App Finance Prévisions                         │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Dash UI (Port 8050)                       │   │
│  │  Pages: Dashboard, Signals, Deep Dive, Alerts, Settings, etc.   │   │
│  │  Tech: Dash, Plotly, Bootstrap Cyborg theme                     │   │
│  └─────────────────┬───────────────────────────────────────────────┘   │
│                    │ Read partitions (parquet/JSON)                     │
│                    ▼                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Data Layer (Partitions)                       │   │
│  │  data/forecast/dt=*/    : forecasts, final, commodities         │   │
│  │  data/macro/dt=*/       : macro_forecast, regimes, risk          │   │
│  │  data/llm_summary/dt=*/ : summary.json (arbiter)                 │   │
│  │  data/quality/dt=*/     : freshness.json, report.json            │   │
│  │  data/prices/ticker=*/  : prices.parquet (5y)                    │   │
│  │  data/news/dt=*/        : news_*.parquet                          │   │
│  │  data/backtest/dt=*/    : results, details, summary              │   │
│  └─────────────────▲───────────────────────────────────────────────┘   │
│                    │ Write partitions (agents)                          │
│  ┌─────────────────┴───────────────────────────────────────────────┐   │
│  │                      Agent Pipeline                              │   │
│  │  • equity_forecast (momentum baseline)                           │   │
│  │  • macro_forecast (FRED: CPI, unemployment, yields)              │   │
│  │  • commodity_forecast (Gold, Oil, Silver, Copper, Corn)          │   │
│  │  • forecast_aggregator (fusion rule)                             │   │
│  │  • llm/arbiter_agent (hourly summary)                            │   │
│  │  • update_monitor (freshness)                                    │   │
│  │  • data_quality (scan issues)                                    │   │
│  │  • backtest_agent (Top-N strategy)                               │   │
│  │  • evaluation_agent (MAE/RMSE/hit_ratio)                         │   │
│  │  Tech: Python, Pandas, g4f, APScheduler                          │   │
│  └─────────────────┬───────────────────────────────────────────────┘   │
│                    │ External APIs                                      │
└────────────────────┼────────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
    yfinance       FRED         g4f
```

---

## 🎨 Personas & Use Cases

### Persona: Reda (Investisseur Privé)
- **Expertise**: Faible (pas de background finance)
- **Objectif**: Identifier 5-10 actions à fort potentiel court/moyen terme
- **Contraintes**:
  - Temps limité (30 min/jour)
  - Besoin de clarté (pas de jargon)
  - Besoin d'explicabilité (pourquoi ce signal?)
- **Workflow typique**:
  1. Ouvrir Dashboard → voir Top-10 du jour
  2. Filtrer watchlist → identifier mouvements notables
  3. Consulter Alerts → vérifier qualité données + événements (earnings)
  4. Deep Dive ticker → analyser graphiques + forecasts + LLM verdict
  5. Portfolio → proposer panier Top-5 avec pondération
  6. LLM Summary → lire synthèse horaire (régime, risque, drivers)

---

## 🔮 Vision Cible (6 mois)

### 1. **Investor Overview** (Page intégrée)
- **Carte Régime**: Expansion/Désinflation/Contraction (badge coloré + tendance)
- **Carte Risque**: Low/Medium/High (sources: VIX, spreads, unemployment)
- **Top-N Final**: Table Top-10 avec scores + directions + confiance
- **Synthèse LLM**: Drivers clés (3-5 bullets FR) + bouton "Relancer maintenant"
- **Logs LLM**: Affichage temps réel (désactivé pendant exécution)

### 2. **Deep Ticker Snapshot Amélioré**
- **Tableau multi-horizons**: 7d / 30d / 1y (score + direction + confiance)
- **Mini-justification LLM**: Par ticker, synthèse 2-3 phrases (drivers techniques + macro)
- **Overlay prix**: Graphique prix + bandes Bollinger + événements (earnings)
- **Comparateur peers**: 5 tickers similaires (secteur) avec returns 1m/3m

### 3. **Agents Health Panel**
- **Badges agents**: 🟢/🟡/🔴 par agent (freshness < 24h / 24-48h / > 48h)
- **Latest dt**: Affichage dt dernière exécution
- **Actions manuelles**: Boutons `run_make(target)` avec anti double-clic + locks
- **Logs live**: Affichage stdout/stderr (4s refresh)
- **Pipeline status**: DAG visuel (success/running/failed)

### 4. **News → Signal**
- **Ingestion quotidienne**: RSS feeds (Reuters, Bloomberg, Yahoo Finance)
- **Agrégation**: Par ticker, par secteur, par date
- **Résumé LLM g4f**: Sentiment + faits marquants (3-5 bullets par ticker)
- **Intégration Dashboard**: Card "Actualités Top-3" avec sentiment coloré

### 5. **Arbitre Multi-Agents LLM**
- **Inputs**:
  - Technique (forecast.final.parquet Top-50)
  - Macro (macro_forecast.*, regimes, risk)
  - Sentiment (news aggregated by ticker)
  - Qualité (freshness.json penalties)
- **Ensemble**: 3-5 agents spécialisés → arbiter DeepSeek R1
- **Output**: `data/llm_summary/dt=YYYYMMDDHH/summary.json`
  ```json
  {
    "regime": "expansion_modérée",
    "risk_level": "medium",
    "outlook_days_7": "positive",
    "outlook_days_30": "neutral",
    "key_drivers": [
      "Désinflation continue (CPI -0.2% MoM)",
      "Courbe des taux pentification (+15bp)",
      "Tech surperformance (NVDA +8% sur 7j, IA demande robuste)"
    ],
    "contributors": [
      {"source": "technique", "model": "momentum", "horizon": "1m", "symbol": "NVDA", "score": 0.82, "prediction": "haussier", "rationale": "Momentum 21j fort (+12%), volume confirmant"},
      {"source": "macro", "model": "regime", "horizon": "3m", "symbol": "SPY", "score": 0.65, "prediction": "modéré", "rationale": "Slope +0.35 mais unemployment stable à 4.1%"},
      {"source": "sentiment", "model": "news_llm", "horizon": "7d", "symbol": "NVDA", "score": 0.75, "prediction": "positive", "rationale": "5 articles positifs (earnings beat, nouveaux contrats cloud)"}
    ],
    "limits": [
      "Données macro H-48 (FRED delay)",
      "Faible couverture sectorielle utilities/healthcare"
    ]
  }
  ```
- **Explainability**: Chaque contributor avec sources (IDs news, dt partitions)

### 6. **Backtests & Evaluation Full**
- **Equity Curve**: Graphique interactif (Plotly) avec drawdowns annotés
- **Metrics Cards**: CAGR, Sharpe, Sortino, MaxDD, Win Rate, Avg Return
- **Strategy Comparison**: Baseline (buy-hold SPY) vs Top-N vs Watchlist-only
- **Evaluation Page**: MAE/RMSE/Hit Ratio par horizon (1w/1m/1y) + par provider (momentum/ML/LLM)

---

## 🚀 Bénéfices Attendus

### Pour Reda (Utilisateur)
1. **Gain de temps**: 3h → 30 min/jour (synthèse automatique)
2. **Clarté**: Signaux FR compréhensibles (pas de jargon)
3. **Confiance**: Explicabilité (sources + rationales)
4. **Alertes proactives**: Qualité + mouvements + earnings
5. **Décision assistée**: Top-N avec pondération automatique

### Pour le Système
1. **Maintenabilité**: Modules réutilisables, zéro duplication
2. **Testabilité**: 29 tests (E2E/integration/unit), UI health automatisée
3. **Extensibilité**: Pattern agent reproductible, LLM via runtime.py
4. **Observabilité**: Freshness monitoring, quality scanning, logs centralisés
5. **Robustesse**: Retries, locks, partitions immutables

---

## 📊 Métriques de Succès

### Court Terme (Sprint actuel)
- [ ] 3 pages prioritaires livrées (Investor Overview, Deep Snapshot, Agents Health)
- [ ] Stratégie LLM documentée + testée (arbiter multi-agents)
- [ ] Backtest agent complet (equity curve + metrics)
- [ ] Coverage tests > 80% (E2E + unit)

### Moyen Terme (3 mois)
- [ ] News → Signal intégré (LLM sentiment daily)
- [ ] ML Baseline intégré (fusion 0.65 rule + 0.25 ML + 0.10 LLM)
- [ ] Macro enrichi (PMI, ISM, LEI, VIX, spreads)
- [ ] Evaluation agent full (MAE/RMSE/hit_ratio par horizon)

### Long Terme (6 mois)
- [ ] Beginner Mode (tooltips, simplification)
- [ ] Portfolio explainability (Why tilts?)
- [ ] Deployment production (Docker, cloud)
- [ ] User guide (vidéos, walkthroughs)

---

## 🔗 Références

- **Engineering Rules**: `docs/engineering_rules.md`
- **Module Index**: `docs/module_index.md`
- **C4 Diagrams**: `docs/architecture/c4.md`
- **Data Flow**: `docs/architecture/data_flow.md`
- **Progress Tracking**: `docs/PROGRESS.md`
- **API Reference**: `docs/api/README.md`

---

**Version**: 1.0
**Next Review**: Sprint +1 (après implémentation phase 1)
