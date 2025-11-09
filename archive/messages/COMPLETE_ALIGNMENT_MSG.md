[UTC 2025-11-06 01:30] [MGR-DECISION] MSG: MSG-20251106-0130-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-ARCH-ALIGNMENT
Subject: [MGR-DECISION] - VÉRIFICATION COMPLÈTE: Chaque endpoint et agent doit être aligné sur l'architecture récente
Message:

* DÉCISION CRITIQUE: Suite à la récente découverte de pages avec chargements infinis, je mets en place une vérification systématique de tous les endpoints et agents pour s'assurer d'une intégration complète avec l'architecture récente.
* CHAQUE AGENT DOIT VÉRIFIER ET VALIDER que ses composants:
  1. Utilisent l'architecture récente et les patterns de données actuels
  2. Génèrent et envoient des données réelles (pas de mocks/données factices)
  3. Sauvegardent les données au bon endroit (dans data/ avec format correct)
  4. S'exécutent avec fréquence appropriée (au moins chaque heure pour données dynamiques)
  5. Respectent les contrats never-empty (toujours une réponse, jamais vide)

* TÂCHES SPÉCIFIQUES CRÉÉES POUR CHAQUE AGENT:

* **@ALEX-API-ARCHITECT-SUPERMAN-7**: FC-API-ALIGN-001 - Vérifier tous les contrats API et s'assurer que tous les endpoints retournent des données structurées conformes
  - Endpoint: /api/health, /api/macro/series, /api/stocks/prices, /api/news/feed, /api/forecasts, /api/brief/daily, /api/brief/weekly
  - But: Validation que tous les endpoints respectent le format {ok: true, data: {...}} avec données réelles
  - DoD: curl tests montrent que chaque endpoint retourne des données valides, pas vides ou d'erreur

* **@ALEX-BACKEND-SUPERMAN-7**: FC-BACKEND-ALIGN-002 - Vérifier tous les jobs agents et la persistance des données
  - Endpoint: /services, /jobs, /storage système
  - But: Validation que tous les jobs d'ingestion s'exécutent correctement et alimentent les fichiers de données
  - DoD: Les fichiers dans data/ sont mis à jour fréquemment, tous les snapshots contiennent des données réelles

* **@ALEX-FINANCE-ANALYST-SUPERMAN-29**: FC-FINANCE-ALIGN-003 - Vérifier l'alignement des modèles finance avec l'architecture
  - Endpoint: /models/forecast_hybrid_v1.py, /features/features.py 
  - But: Validation que les prévisions sont générées et sauvegardées dans data/forecast/
  - DoD: /api/forecasts retourne des prévisions réelles basées sur les modèles ML+G4F, avec horodatage et sources

* **@MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7**: FC-ML-ALIGN-004 - Vérifier l'alignement des modèles ML avec le pipeline
  - Endpoint: /backend/models/, /backend/jobs/forecast_jobs.py
  - But: Validation que les modèles ML produisent des données exploitables pour les prévisions
  - DoD: Les outputs ML sont sauvegardés dans des fichiers accessibles par les endpoints API

* **@LENA-LLM-STRATEGIST-WONDERWOMAN-21**: FC-NEWS-ALIGN-005 - Vérifier l'alignement de l'ingestion news
  - Endpoint: /backend/jobs/news_ingest.py, /backend/services/news_service.py
  - But: Validation que l'ingestion news s'exécute régulièrement et sauvegarde des articles réels
  - DoD: /api/news/feed retourne des articles avec dates, titres, sentiments provenant de sources réelles

* **@STEPHANE-DATA-MASTER-BATMAN-10**: FC-TEST-ALIGN-006 - Vérifier l'alignement des tests avec données réelles
  - Endpoint: /tests/, /backend/test/
  - But: Validation que les tests utilisent des données réelles, pas des mocks
  - DoD: Tests passent avec données de production et identifient les véritables problèmes de fonctionnement

* **@MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23**: FC-QM-ALIGN-007 - Système de vérification qualité globale
  - Endpoint: /backend/quality/, /backend/services/quality_service.py
  - But: Création d'un système global pour valider que tous les autres systèmes fonctionnent correctement
  - DoD: Endpoint /api/quality/checks renvoie un état global de la santé du système et des données

* CHAQUE AGENT DOIT EXÉCUTER SON AUDIT ET METTRE À JOUR SON PROFIL DEPUIS SA DERNIÈRE INTERVENTION.
* AVANT DE PUSH, fournir preuve dans `proofs/FC-ALIGN-<AGENT-NUM>/` avec captures et résultats de tests.
* Les agents doivent s'assurer que leurs données sont persistées dans les sous-répertoires de `data/` au format approprié.
* Les jobs doivent s'exécuter avec fréquence régulière et mettre à jour les snapshots.
Links:
* TASKS_BOARD.md (sections FC-ALIGN-* tasks)
* docs/architecture_recente.md (à créer pour documenter les patterns actuels)
* scripts/verification_complete.sh (à créer pour tester tous les endpoints)
Need by: 2025-11-06 18:00 UTC
Applies-to: ALL