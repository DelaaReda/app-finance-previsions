# PROJECT_BOARD.md

## North Star
Livrer un **MVP Finance Copilot stable en local** (backend + frontend + 5 endpoints fiables), sans suppression destructive.

## Working Rules (Hard)
- ❌ Ne jamais supprimer de code/fichiers historiques
- ✅ Déplacer l'ancien dans `legacy/` ou repo legacy dédié
- ✅ Tickets de 2-4h max
- ✅ WIP max = 2 tickets en parallèle
- ✅ Une tâche = preuve de validation (commande/test)

## Priority Backlog (Sprint 0 - Structuration)

### TODO
- [ ] S0-T1 Cartographier les zones actives vs legacy
  - Owner: Architect
  - Deliverable: `ARCHITECTURE_MAP.md` validé
  - Validation: chemins actifs documentés + conventions import

- [ ] S0-T2 Définir workflow agents + DoD + format ticket
  - Owner: PO/Analyst
  - Deliverable: `AGENT_WORKFLOW.md`
  - Validation: templates prêts à copier-coller

- [ ] S0-T3 Politique legacy (migrations safe)
  - Owner: Architect
  - Deliverable: `LEGACY_POLICY.md`
  - Validation: checklist move + naming standard

- [ ] S0-T4 Préparer handoff prompts (roles)
  - Owner: PO
  - Deliverable: dossier `handoff/`
  - Validation: 4 briefs min (backend/frontend/data/qa)

- [ ] S0-T5 Définir MVP scope figé (v1)
  - Owner: Prioritization Analyst
  - Deliverable: `MVP_SCOPE.md`
  - Validation: in-scope/out-of-scope + endpoints cibles

### DOING
- [ ] (empty)

### DONE
- [x] S0-INIT Créer la structure de gouvernance locale
  - Preuve: `PROJECT_BOARD.md`, `AGENT_WORKFLOW.md`, `ARCHITECTURE_MAP.md`, `LEGACY_POLICY.md`, `MVP_SCOPE.md`, `handoff/*`, `legacy/README.md`

## Risks & Blockers
- Architecture hybride (`backend/services` + `backend/src/services`) peut perdre les agents
- Frontend comporte encore des mocks massifs (`mockData.js`)
- Jobs avec nombreux fallbacks peuvent masquer des pannes de data

## Daily Checkpoint Format
- Done today
- Broken / blocked
- Next 3 priorities
- Confidence (0-100)
