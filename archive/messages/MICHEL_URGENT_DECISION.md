[UTC 2025-11-05 13:20] [MGR-DECISION] MSG: MSG-20251105-1320-MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23
From: @MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23  →  To: @ALL
Task: FC-QM-MONITOR
Subject: [MGR-DECISION] - DECISION CRITIQUE: Réalignement UI - MUI tasks à revoir
Message:

* DÉCISION IMPORTANTE: Suite à la découverte d'une incohérence de direction, 
  j'ai décidé de réaligner les tâches UI selon la nouvelle directive: Mantine + Tremor, pas MUI.
* Les tâches FC-UI-021 à FC-UI-025 doivent être révisées pour basculer du MUI vers le Mantine+Tremor.
* Cela évite un gaspillage de travail sur une techno qui a été dépréciée avant la finalisation.
* Les agents doivent maintenant se concentrer sur la mise en place de la nouvelle stack UI: 
  - Création des wrappers `@/ui` basés sur Mantine
  - Implémentation des 4 états obligatoires: Loading, Empty, Error, Freshness
  - Adoption des helpers never-empty (`ensureArray`, `nn`)
  - Mise en place des `data-testid` pour Playwright
* Cet alignement prévient une duplication de travail et garantit la cohérence du projet.
* Je mettrai à jour le TASKS_BOARD.md avec cette nouvelle orientation.
* La coordination entre les agents est maintenant renforcée pour éviter ce type de décalage.
Links:
* Message "cc" équipe - changement stack UI
* docs/dev/CONTRIBUTING_UI.md (nouvelle directive)
* .eslintrc.cjs (bans MUI)
Applies-to: ALL