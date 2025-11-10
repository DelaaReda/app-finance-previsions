
---

## 🚀 TÂCHES CRITIQUES D'ARCHITECTURE - Issues identifiés dans l'analyse complète

Suite à l'analyse architecture complète reçue, voici les tâches prioritaires pour améliorer la stabilité, performance et qualité du système.

---

## FC-ARCH-UTILS-001 — Factorisation des utilitaires communs

**Status**: AVAILABLE to claim

**But**: Regrouper les utilitaires de chargement fichier et lecture de données pour éviter les duplications.

**Fichiers**
* `backend/src/core/data_access.py` (à créer)
* `backend/src/utils/file_loader.py` (à créer)
* `backend/src/api/routes/*` (migration vers les utilitaires partagés)
* `backend/src/services/*` (migration vers les utilitaires partagés)

**Étapes**
1. **Identifier les duplications**:
   - Trouver tous les usages de `_latest_dt_under`, `_load_equity_final`, etc.
   - Regrouper les fonctions similaires dans `core/data_access.py`

2. **Créer les utilitaires partagés**:
   - `load_latest_snapshot(key, default=None)` - charge la dernière partition
   - `ensure_safe_array(data, default=[])` - garantit never-empty pour collections
   - `get_last_update(path)` - extrait timestamp de fraîcheur
   - `load_parquet_safe(path, default=pd.DataFrame())` - charge parquet en évitant erreurs

3. **Migrer les usages existants**:
   - Changer les endpoints pour utiliser les utilitaires partagés
   - Éliminer les réimplémentations locales
   - Tester que les fonctionnalités restent intactes

**DoD**
* Aucune duplication des fonctions de chargement de données
* Tous les endpoints utilisent les mêmes utilitaires partagés
* Meilleure fiabilité des accès disque avec gestion d'erreurs centralisée
* Performance optimisée avec code factorisé
* Preuve: suppression de 5+ fonctions dupliquées, même comportement fonctionnel

---

## FC-ARCH-ERRORS-002 — Renforcement de la gestion d'erreurs

**Status**: AVAILABLE to claim

**But**: Remplacer les gestionnaires d'erreurs silencieux par des logs détaillés et des réponses propres.

**Fichiers**
* `backend/src/api/routes/*.py` (amélioration try/except)
* `backend/src/services/*.py` (amélioration gestion d'erreurs)
* `backend/src/jobs/*.py` (amélioration gestion d'erreurs)
* `backend/src/core/error_handler.py` (à créer)

**Étapes**
1. **Identifier les `except ...: pass`**:
   - Chercher tous les usages de `pass` dans les blocs except
   - Remplacer par une gestion d'erreur appropriée (log + fallback)

2. **Créer un handler d'erreur centralisé**:
   - `log_error(error, context, level="ERROR")` avec contexte détaillé
   - `safe_call(func, fallback, error_msg)` pour envelopper les appels risqués
   - `log_structured(data, level="INFO")` pour logging uniforme

3. **Mettre en place proper error responses**:
   - Remplacer les réponses vides par des structures avec `error: {code, message}`
   - Maintenir le contrat never-empty même en cas d'erreur
   - Fournir des messages utiles à l'UI pour l'affichage

**DoD**
* Tous les `except ...: pass` remplacés par des handlers appropriés
* Logging centralisé et structuré pour toutes les erreurs
* Les endpoints servent toujours des réponses structurées même en cas d'erreur
* Aucune erreur d'origine cachée dans les logs
* Preuve: capture de logs montrant erreurs structurées et contexte

---

## FC-ARCH-SCHEDULER-003 — Orchestrateur central des agents

**Status**: AVAILABLE to claim

**But**: Créer un scheduler centralisé pour orchestrer les agents dans le bon ordre et éviter les oublis.

**Fichiers**
* `backend/src/scheduler/app.py` (à étendre)
* `backend/src/scheduler/job_definitions.py` (à créer)
* `backend/src/agents/orchestrator.py` (à créer)
* `backend/src/jobs/scheduler_main.py` (à créer)

**Étapes**
1. **Définir les dépendances entre jobs**:
   - Ingestion → Prévisions → Agrégation → Briefs → Backtests
   - Créer un graphique de dépendance clair

2. **Implémenter orchestrateur central**:
   - `run_pipeline_pipeline(order=[ingestion, forecasts, aggregation, briefs, backtests])`
   - Gestion des erreurs/failures intermédiaires
   - Logging de progression des jobs

3. **Scheduler centralisé**:
   - Tâches planifiées dans un seul fichier
   - Coordination des cadences (journalier, horaire, hebdomadaire)
   - Monitoring de l'état des jobs

**DoD**
* Pipeline d'agents orchestré dans le bon ordre
* Tâches planifiées centralisées (pas de cron分散é dans plusieurs fichiers)
* Suivi de progression des jobs avec logs détaillés
* Gestion des erreurs sans arrêter le reste du pipeline
* Preuve: logs montrant l'exécution séquentielle des jobs avec dépendances respectées

---

## FC-ARCH-ENDPOINTS-004 — Optimisation des endpoints pour performance

**Status**: AVAILABLE to claim

**But**: Réduire la charge des endpoints critiques pour améliorer la performance et la réactivité.

**Fichiers**
* `backend/src/api/routes/forecasts.py`
* `backend/src/api/routes/news.py`
* `backend/src/api/routes/macro.py`
* `backend/src/api/routes/stocks.py`
* `backend/src/services/cache_service.py`

**Étapes**
1. **Analyser les endpoints les plus lents**:
   - Utiliser les logs pour identifier les endpoints avec temps de réponse élevé
   - Vérifier les calculs répétés à chaque requête

2. **Optimiser avec caches et pré-calculs**:
   - Pré-calculer les données lourdes en amont
   - Mettre en cache les réponses (TTL approprié)
   - Réduire la taille des réponses (pagination, filtrage)

3. **Vérifier la logique côté serveur vs côté client**:
   - Le tri et le filtrage devraient être faits côté serveur pour réduire la charge client
   - Éviter les transferts de grosses structures non nécessaires

**DoD**
* Temps de réponse des endpoints < 200ms (sauf exceptions justifiées)
* Aucun calcul lourd pendant les requêtes utilisateurs
* Structures de réponses optimisées (moins de données inutiles transférées)
* Caching efficace mis en place pour les endpoints coûteux
* Preuve: mesure de performance avant/après optimisation

---

## FC-ARCH-CODE-QUALITY-005 — Nettoyage du code mort et unification

**Status**: AVAILABLE to claim

**But**: Supprimer les duplications et le code mort pour améliorer la maintenabilité.

**Fichiers**
* `backend/src/dash_app/*` (code legacy à comparer avec API v2)
* `backend/src/api/main.py` (vs `main_v2.py`)
* `backend/src/api/routes/brief_routes.py` (vs `routes/brief.py`)
* `backend/src/api/services/news_service.py` (vs autres services)

**Étapes**
1. **Audit du code existant**:
   - Identifier les endpoints/fonctions redondants
   - Trouver les parties inutilisées du code
   - Comparer les versions legacy avec les nouvelles

2. **Consolider les duplications**:
   - Supprimer les routes en double
   - Fusionner les services similaires
   - Unifier les schémas de réponse

3. **Nettoyer le code mort**:
   - Supprimer les imports inutilisés
   - Éliminer les fonctions non appelées
   - Clarifier les responsabilités de chaque module

**DoD**
* Code base nettoyé de 10% de duplications/redondances
* Toutes les routes unifiées et claires
* Aucune fonction importée mais non utilisée
* Documentation mise à jour des responsabilités de chaque module
* Preuve: comparaison de taille de code avant/après nettoyage

---

## 🎯 Priorité d'exécution

1. **FC-ARCH-ERRORS-002** (gestion d'erreurs) — pour éviter les plantages silencieux
2. **FC-ARCH-UTILS-001** (utilitaires communs) — pour éviter duplication
3. **FC-ARCH-CODE-QUALITY-005** (nettoyage) — pour clarifier structure
4. **FC-ARCH-SCHEDULER-003** (orchestration) — pour pipeline stable
5. **FC-ARCH-ENDPOINTS-004** (optimisation) — pour performance

Ces tâches sont critiques pour la qualité, la performance et la maintenabilité du système.