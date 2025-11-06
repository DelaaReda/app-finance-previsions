[UTC 2025-11-05 18:00] [MGR-UPDATE] MSG: MSG-20251105-1800-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QA-UI-COMPREHENSIVE
Subject: [MGR-UPDATE] - Procédure de test UI complète + résolution des problèmes identifiés
Message:

* PROCÉDURE DE TEST UI STANDARDISÉE (à suivre pour tous les QA):
* 1. Démarrer les services via script officiel: `./finance-copilot.sh start`
* 2. Vérifier statut: `./finance-copilot.sh status` → tous les services doivent être au vert
* 3. Exécuter Playwright tests: `cd copilot-app/frontend/webapp && npx playwright test --reporter=line`
* 4. Capturer des screenshots pour chaque page dans différents états (loading, empty, error, data)
* 5. Vérifier que les tests ne cassent pas à cause de selectors fragiles (préférer data-testid ou regex)

* PROCÉDURE POUR IDENTIFIER ET RÉSOUDRE LES PROBLÈMES:
* 1. Mauvais titres/pages: Remplacer les vérifications de texte par data-testid
  - Ex: `page.getByTestId('dashboard-root')` au lieu de recherche par titre
  - Ajouter `data-testid="brief-title"` sur les éléments critiques

* 2. Limites API non respectées côté UI: Ajouter des gardes côté client
  - Ex: News feed limit de 200 - côte UI doit limiter les requêtes à 200
  - Ajouter un clamp: `Math.min(userLimit, 200)` avant l'appel API

* 3. États vides non gérés: Vérifier que les helpers never-empty sont utilisés
  - Tous les `.map()` doivent être protégés: `(data?.items ?? []).map(...)`
  - Tous les `.length` doivent être protégés: `(data?.items ?? []).length`
  - Utiliser `ensureArray()` pour la sécurité d'accès

* 4. Données manquantes: Vérifier que les endpoints retournent des snapshots
  - Si l'endpoint est vide, le système de cache doit servir le dernier snapshot valide
  - Vérifier que les jobs de scheduler produisent les fichiers dans `data/...`

* SCREENSHOTS POUR DOCUMENTER LES PROBLÈMES:
* Sauvegarder les captures dans `proofs/SCREENSHOTS-UI-QA/<PAGE_NAME>/`
* Inclure: état loading, état empty, état error, état data, état responsive mobile
* Les captures doivent permettre d'identifier: manque de données, UI cassée, erreurs JS, manque d'accessibilité
* Utiliser Playwright pour générer des captures systématiques

* PROCÉDURE DE RÉSOLUTION:
* 1. Identifier la source du problème (backend endpoint ou frontend rendering ou communication)
* 2. Corriger les selectors fragiles pour utiliser des attributs stables (data-testid)
* 3. S'assurer que les contrats never-empty sont respectés des deux côtés (backend → frontend)
* 4. Vérifier que les snapshots sont générés par les jobs backend
* 5. Mettre à jour les tests pour utiliser des méthodes robustes

* Les agents doivent suivre cette procédure pour chaque page et rapporter dans leurs preuves:
  - Screenshots avant/après fixes
  - Tests passants avec captures
  - Logs de validation
  - Confirmation que les endpoints servent des données réelles et non vides

* Cela garantit la qualité continue et permet d'identifier les gaps à fermer.
Links:
* docs/ui-testing-procedure.md (procédure complète à créer)
* playwright tests dans copilot-app/frontend/webapp/
* screenshots dans test-results/
* preuves dans proofs/SCREENSHOTS-UI-QA/
Need by: 2025-11-06 10:00 UTC
Applies-to: ALL