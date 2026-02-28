# Architecture Backend du Finance Copilot

## Vue d'ensemble

Ce document décrit l'architecture backend du Finance Copilot, un système de prévision financière hybride ML + LLM.

## Composants principaux

### 1. API Gateway (FastAPI)
- Point d'entrée unique pour toutes les requêtes
- Gère l'authentification, les middlewares et la gestion d'erreurs
- Fournit des endpoints REST pour tous les services

### 2. Services de données
- **Market Data**: Intégration avec yfinance, FRED, Alpha Vantage
- **News**: Pipeline d'ingestion, scoring et NLP
- **Macro**: Données économiques et indicateurs clés

### 3. Services de prévision
- **Forecaster ML**: Modèles techniques (SMA, RSI, MACD)
- **LLM Layer**: Intégration G4F pour scoring et explication
- **Aggregator**: Combinaison des signaux et calcul de score final

### 4. Caching & Persistance
- **TTL Cache**: Pour les requêtes coûteuses
- **Parquet Storage**: Pour les données de prévision
- **DuckDB**: Pour les requêtes analytiques

### 5. Orchestration
- **Scheduler**: Tâches planifiées pour l'actualisation des données
- **Pipeline Runner**: Exécution des workflows d'ingestion et de prévision

## Contrats API

### Généralités
- Toutes les réponses suivent le format: `{"ok": bool, "data": {...}}`
- Les erreurs sont encapsulées dans: `{"ok": False, "error": "message"}`
- Les endpoints vides sont proscrits - au moins une structure de données vide est requise

### Endpoints critiques
- `/api/forecasts`: Retourne les prévisions avec score, confiance et direction
- `/api/macro/series`: Données économiques avec historique
- `/api/stocks/prices`: Prix et indicateurs techniques
- `/api/news/feed`: Flux d'actualités avec scoring

## Niveaux de tolérance

### Performance
- Latence < 300ms pour les endpoints principaux
- Taux d'erreur < 1%
- Disponibilité > 99%

### Fiabilité
- Aucune réponse vide pour les endpoints critiques
- Données en cache en cas de défaillance des sources externes
- Retries automatiques pour les appels externes échoués

## Scalabilité

### Microservices
- Chaque domaine fonctionnel est isolé dans son propre service
- Communication via API REST ou file de messages
- Déploiement indépendant possible

### Caching
- Cache en mémoire pour les requêtes fréquentes
- Cache à long terme pour les données coûteuses à calculer
- Gestion par TTL pour garantir la fraîcheur

## Sécurité

### Limitation des appels
- Rate limiting par IP et par clé API
- Protection contre les attaques DoS
- Journalisation des appels suspects

## Surveillance

### Logging
- Journalisation structurée pour tous les appels
- Tracing des erreurs avec contexte
- Métriques de performance

### Monitoring
- Endpoint `/health` pour la surveillance
- Indicateurs KPI pour le dashboard
- Alertes en cas de dégradation