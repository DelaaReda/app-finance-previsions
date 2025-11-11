[UTC 2025-11-05 14:30] [MGR] MSG: MSG-20251105-1430-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-CODACY-EXECUTION
Subject: [MGR] - OBLIGATOIRE: Exécuter Codacy analysis et corriger les problèmes identifiés
Message:

* TÂCHE OBLIGATOIRE pour tous les agents: Exécuter les analyses Codacy et corriger les problèmes identifiés.
* Les tâches FC-QM-CODACY-001 à 004 sont maintenant disponibles dans TASKS_BOARD.md pour implémentation de la stack qualité.
* CHAQUE AGENT doit exécuter les commandes suivantes et corriger les problèmes identifiés:
  
  1. Analyse complète: `codacy-cli analyze`
  2. Analyse spécifique ESLint: `codacy-cli analyze --tool eslint`
  3. Générer SARIF: `codacy-cli analyze -t eslint --format sarif -o eslint.sarif`
  4. Analyser fichiers spécifiques critiques:
     - `codacy-cli analyze --tool eslint copilot-app/backend/src/api/main.py`
     - `codacy-cli analyze --tool eslint copilot-app/frontend/webapp/src/api/client.ts`
     - `codacy-cli analyze --tool eslint copilot-app/frontend/webapp/src/components/ErrorBoundary.tsx`
     - `codacy-cli analyze --tool eslint copilot-app/backend/storage/json_storage.py`
     - `codacy-cli analyze --tool eslint copilot-app/backend/services/cache_service.py`

* RÉSULTATS attendus:
  - Fichiers SARIF générés dans `proofs/FC-QM-CODACY-EXECUTION/`
  - Corrections des problèmes critiques et de sécurité identifiés
  - Amélioration de la qualité du code (maintenabilité, accessibilité, performance)
  - Code toujours respectant les standards never-empty et sécurité

* AVANT chaque push, les agents doivent maintenant:
  1. Exécuter l'analyse Codacy
  2. Corriger les problèmes critiques
  3. S'assurer que les standards de qualité sont respectés
  4. Sauvegarder les rapports SARIF dans les preuves

* Ceci renforce notre système de quality gates: tests + preuves + codacy analysis.
Links:
* TASKS_BOARD.md (section FC-QM-CODACY-001 à 004)
* scripts/quality/codacy-analyze.sh (à créer pour automatisation)
* docs/quality/codacy-integration.md (à créer pour guidelines)
Need by: 2025-11-06 12:00 UTC
Applies-to: ALL