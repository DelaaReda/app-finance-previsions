[UTC 2025-11-05 12:30] [MGR-UPDATE] MSG: MSG-20251105-1230-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-UI-TRANSITION
Subject: [MGR-UPDATE] - Directive importante: Changement stack UI - Mantine + Tremor obligatoire
Message:

* MESSAGE CRITIQUE: Le stack UI change - migration de MUI vers Mantine + Tremor (design system unique).
* DÉCISION: Retirer MUI, adopter Mantine v7 + Tremor v3 comme stack UI officiel.
* NOUVEAU STANDARD: Importer uniquement via `@/ui` (wrappers Mantine), pas directement MUI.
* ÉTATS OBLIGATOIRES: Toutes les vues doivent gérer les 4 états: Loading (Skeleton), Empty, Error (Alert), Freshness.
* NEVER-EMPTY: Plus de `.map/.length` sur `undefined` - utiliser les helpers `ensureArray`, `nn`.
* DATA-TESTID: Obligatoire partout pour Playwright tests - seuls éléments ciblés.
* PETITES PR: <300 lignes, 1 tâche = 1 PR, preuves dans `proofs/`.
* API_BASE: Utiliser `VITE_API_BASE_URL` || `/api`.
* Les tâches FC-UI-021 à FC-UI-025 (MUI) doivent être REVUES pour intégrer cette nouvelle directive.
* Tous les agents doivent se coordonner pour cette migration UI prioritaire.
* NORA-PO-11 est le owner technique - contacter pour attributions tâches UI.
Links:
* Nouveaux templates UI à déployer
* Nouveaux composants @/ui à créer
* Helpers never-empty à intégrer partout
Applies-to: ALL