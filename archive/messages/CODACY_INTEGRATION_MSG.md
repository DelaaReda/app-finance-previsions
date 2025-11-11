[UTC 2025-11-05 14:00] [MGR-UPDATE] MSG: MSG-20251105-1400-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-CODACY-ANALYZE
Subject: [MGR-UPDATE] - CODE QUALITY: Intégration Codacy pour détection et correction des problèmes
Message:

* NOUVELLE PROCÉDURE QUALITÉ: Intégration de Codacy-CLI pour analyse automatique de la qualité du code.
* OUTIL RECOMMANDÉ: `codacy-cli analyze` pour détecter les problèmes de code avant chaque livraison.
* UTILISATION RECOMMANDÉE:
  1. Analyse complète: `codacy-cli analyze`
  2. Analyse spécifique ESLint: `codacy-cli analyze --tool eslint`
  3. Format SARIF pour intégration: `codacy-cli analyze --tool eslint --format sarif`
  4. Analyse fichier spécifique: `codacy-cli analyze path/to/file.js`
  5. Sauvegarde des résultats: `codacy-cli analyze -t eslint --format sarif -o eslint.sarif`

* Cela permettra de:
  - Détecter les problèmes de style et de qualité avant commit
  - Identifier les vulnérabilités de sécurité
  - Améliorer la maintenabilité du code
  - Réduire les bugs en production
  - Assurer une homogénéité dans les standards de code

* TOUTES LES TÂCHES doivent maintenant inclure une analyse Codacy avant le commit final.
* Les résultats d'analyse doivent être partagés dans les preuves (`proofs/<TASK-ID>/<handle>/codacy-results/`)
* Cela renforce notre système de quality gates: code + preuve + score + codacy analysis.

* AVANT de pousser chaque commit, exécutez:
  ```bash
  codacy-cli analyze --tool eslint --format sarif -o codacy-eslint-results.sarif
  ```
* Vérifiez les problèmes identifiés et corrigez-les avant le push final.
Links:
* codacy-cli installation and usage
* SARIF results format for integration
* docs/codacy-integration-standards.md (à créer)
Need by: 2025-11-06 10:00 UTC
Applies-to: ALL