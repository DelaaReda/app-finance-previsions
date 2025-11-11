[UTC 2025-11-05 17:30] [MGR] MSG: MSG-20251105-1730-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QA-UI-COMPREHENSIVE
Subject: [MGR] - QA COMPRÉHENSIVE REQUISE: Vérification complète de toutes les pages UI
Message:

* URGEN: Demande de QA complète sur toutes les pages UI pour s'assurer de la stabilité et de la qualité avant d'ajouter plus de fonctionnalités.
* TÂCHE ASSIGNÉE À TOUTES LES ÉQUIPES FRONTEND: Effectuer une vérification complète de toutes les pages existantes.
* PAGES À VÉRIFIER: /, /forecasts, /news, /brief, /macro, /stocks, /backtests, /copilot, /alerts, /dashboard
* CHAQUE PAGE DOIT ÊTRE TESTÉE POUR:
  1. Chargement sans crash (pas de "Cannot read property 'map' of undefined")
  2. État "Loading" correct (Spinners/Skeletons)
  3. État "Empty" correct (pas de crash si données absentes)
  4. État "Error" correct (pas de crash si erreur API)
  5. Affichage de la fraîcheur des données
  6. Navigation inter-page fonctionnelle
  7. Responsive design mobile/desktop
  8. Absence de crashs JavaScript
  9. Données affichées correctement (même si vides mais pas undefined)
  10. Accessibilité de base (navigation clavier, textes lisibles)

* Les agents responsables de chaque page doivent s'assurer que leurs composants respectent les standards never-empty:
  - Utiliser `data?.property ?? []` au lieu de `data.property` direct
  - Toujours sécuriser les `.map()` et `.length`
  - Utiliser les helpers `ensureArray`, `nn`, etc. que nous avons implémentés

* Rapportez vos résultats dans `proofs/FC-QA-UI-COMPREHENSIVE/<handle>/` avec:
  - Captures d'écran des pages en différents états
  - Logs de console (pas d'erreurs JS)
  - Tests Playwright si disponibles
  - Statut: PASS/FAIL pour chaque page

* Cette vérification est PRIORITY 1 avant d'implémenter les nouveaux endpoints API que j'ai ajoutés.
Links:
* Nouveaux endpoints API dans TASKS_BOARD.md (FC-API-026 à FC-API-035)
* Helpers UI sécurisés: safe.ts et @/ui exports
* proof directory: proofs/FC-QA-UI-COMPREHENSIVE/
Need by: 2025-11-06 14:00 UTC
Applies-to: ALL