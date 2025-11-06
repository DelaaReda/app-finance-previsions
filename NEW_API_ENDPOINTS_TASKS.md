
---

## FC-API-026 — Stocks Screener (filtrage avancé)

**Status**: AVAILABLE to claim

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

**Status**: AVAILABLE to claim

**But**: Endpoint `/api/macro/calendar` pour le calendrier des événements économiques à venir.

**Fichiers**
* `backend/api/routes/macro_extra.py`
* `backend/services/economic_calendar.py`
* `backend/jobs/calendar_ingest.py`
* `ingestion/economic_calendar.py`

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