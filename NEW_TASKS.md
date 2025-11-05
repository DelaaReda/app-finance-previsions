# 🚀 NEXT ITERATION TASKS (P2) - Ready to claim

## FC-P2-016 — Forecast Data Population (real data to forecasts)

**Status**: AVAILABLE to claim

**But**: remplir `/api/forecasts` avec de vraies données ML+G4F au lieu de tableaux vides.

**Fichiers**

* `backend/models/ml_forecast.py`
* `backend/models/llm_ranker.py` 
* `backend/jobs/forecasts.py`
* `backend/routes/forecasts.py`

**Étapes**

1. Exécuter le modèle ML pour produire de vraies prévisions (pas juste des structures vides)
2. Intégrer G4F pour ranking et explications
3. Sauvegarder dans `data/forecasts.json` avec horodatage et sources
4. S'assurer que `/api/forecasts` renvoie des `rows` non-vides

**DoD**

* `/api/forecasts` renvoie `{"rows": [...]}` avec des données réelles (pas vide)
* Structure: `{ticker, horizon, direction, confidence, explanation, score}`
* Fraîcheur et sources incluses

---

## FC-P2-017 — News Ingest Real Data (RSS → API)

**Status**: AVAILABLE to claim

**But**: Alimenter `/api/news/feed` avec de vraies données RSS au lieu de réponses vides.

**Fichiers**

* `backend/jobs/news_ingest.py`
* `backend/routes/news.py`
* `backend/services/news_service.py`

**Étapes**

1. Configurer les sources RSS réelles (Bloomberg, Reuters, etc.)
2. Intégrer le pipeline d'ingestion avec scraping + parsing
3. Sauvegarder dans `data/news_feed.json` avec fraîcheur
4. S'assurer que `/api/news/feed` renvoie des articles réels

**DoD**

* `/api/news/feed` renvoie `{"articles": [...]}` avec articles réels
* Articles < 15 minutes (fraîcheur garantie)
* Structure: `{title, link, pubDate, source, sentiment_score, tickers}`

---

## FC-P2-018 — ML Model Performance Tracking

**Status**: AVAILABLE to claim

**But**: Suivre la performance des modèles ML avec métriques réelles.

**Fichiers**

* `backend/models/performance_tracker.py`
* `backend/jobs/performance_report.py`
* `backend/routes/ml_performance.py`

**Étapes**

1. Calculer des métriques: hit_rate, precision, recall pour les prévisions
2. Suivre l'évolution des prévisions dans le temps
3. Sauvegarder dans `data/ml_performance.json` 
4. Endpoint pour visualiser la performance

**DoD**

* `/api/ml-performance` renvoie métriques réelles de performance
* Données historiques de performance ML stockées et accessibles

---

## FC-P2-019 — Advanced Cache Invalidation

**Status**: AVAILABLE to claim

**But**: Système intelligent d'invalidation des caches basé sur la fraîcheur des données.

**Fichiers**

* `backend/services/cache_service.py`
* `backend/jobs/cache_manager.py`

**Étapes**

1. Détecter quand les données sources changent (news, forecasts, etc.)
2. Invalider automatiquement les caches dépendants
3. Rafraîchir les snapshots en arrière-plan
4. Maintenir la fraîcheur dans les métadonnées

**DoD**

* Cache mis à jour automatiquement quand les données changent
* Fraîcheur toujours correcte dans les réponses
* `/api/*` renvoie toujours les dernières données valides

---

## FC-P2-020 — LLM Judge Integration

**Status**: AVAILABLE to claim

**But**: Intégrer le LLM Judge pour évaluer la qualité des prévisions et des analyses.

**Fichiers**

* `backend/llm_judge/judge_service.py`
* `backend/routes/judge.py`
* `backend/jobs/judge_evaluation.py`

**Étapes**

1. Intégrer G4F pour évaluation des prévisions
2. Comparer les prévisions avec les réalisations
3. Générer des rapports de performance LLM
4. Endpoint pour consulter les évaluations

**DoD**

* `/api/judge` renvoie évaluations LLM des prévisions/analyses
* Scores de qualité et explications disponibles