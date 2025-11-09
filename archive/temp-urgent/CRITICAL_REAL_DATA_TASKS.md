
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