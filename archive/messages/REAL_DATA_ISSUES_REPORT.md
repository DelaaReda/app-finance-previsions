[UTC 2025-11-05 18:30] [MGR-UPDATE] MSG: MSG-20251105-1830-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-NO-MOCKS-INTEGRATION-TESTS
Subject: [MGR-UPDATE] - RÉSULTATS CRITIQUES: Tests end-to-end "no-mocks" révèlent problèmes de données réelles
Message:

* RÉSULTATS DES TESTS D'INTÉGRATION "NO-MOCKS" - Problèmes critiques identifiés dans les données réelles!
* Tests exécutés: `npx playwright test tests/ui/integration-data.spec.ts`
* PROBLÈMES IDENTIFIÉS:
  1. `/api/forecasts` - Renvoie `{"rows":[],"count":0}` → AUCUNE PRÉVISION RÉELLE dans les snapshots
  2. `/api/news/feed` - Renvoie `articles: []` avec filtres tickers → DONNÉES NEWS MANQUANTES
  3. Backend ne lit pas correctement les fichiers de données réelles → toujours 0 résultats
  4. Système de seeding non opérationnel → pas de données réelles dans les endpoints critiques

* TÂCHES CRITIQUES À ASSIGNER IMMÉDIATEMENT:
  - [FC-REAL-SEED-001] - Alimenter les snapshots avec données réelles (forecasts.json, news_feed.json)
  - [FC-REAL-PIPE-001] - Pipeline d'ingestion réelle (Yahoo, RSS, FRED) → données persistées  
  - [FC-REAL-DATA-001] - Fix data paths et vérification CWD backend pour lecture correcte
  - [FC-REAL-TEST-001] - Tests "no-mocks" avec données réelles garanties

* Ces problèmes confirment que nous avons des "endpoints vides" malgré les structures never-empty correctes
* Le système est techniquement stable mais SANS DONNÉES RÉELLES → inutilisable pour les utilisateurs
* Priorité absolue: remplacer les snapshots vides par des données réelles provenant des pipelines d'ingestion
* Je vais créer les tâches ci-dessous dans TASKS_BOARD.md avec assignation aux agents appropriés
Links:
* curl /api/forecasts returns {rows:[],count:0}
* curl /api/news/feed returns articles:[]
* test-results/integration-data-* screenshots showing failures
* docs/no-mocks-testing.md (approche de test "real data only")
Need by: 2025-11-06 18:00 UTC
Applies-to: ALL