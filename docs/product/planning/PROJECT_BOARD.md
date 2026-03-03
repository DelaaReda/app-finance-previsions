# PROJECT_BOARD (Vision + Orchestration)

## Sources de vérité
- `docs/product/planning/PRODUCT_VISION.md`
- `docs/product/planning/WORKSTATE.md`
- `docs/orchestrator-ops/parallel-workstreams.json`
- `docs/orchestrator-ops/priority-queue.json`

## État courant
- **BATCH-01**: CLOSED
- **BATCH-02**: CLOSED
- **BATCH-03**: CLOSED
- **BATCH-04**: CLOSED
- **BATCH-05**: CLOSED
- **BATCH-06**: READY (actif)
- **BATCH-07**: WAITING_DEP (bloqué tant que BATCH-06 non clôturé)

## Priorité opérationnelle immédiate
1. Exécuter `BATCH-06-DEV-01`, `BATCH-06-DEV-02`, `BATCH-06-DEV-03` en lane `dev` unique avec preuves (`cmd`, `tests_run`, artefact).
2. Garder `BATCH-06-PLAN` en pilotage court: scope, dépendances, ordre de claim, critères d'acceptation.
3. N'ouvrir `BATCH-07` qu'après clôture factuelle BATCH-06 dans queue + workboard.

## Risques à surveiller
- État de tâche incohérent entre queue et workboard.
- Handoff/communication de status en retard (batch trop vite marqué complet).
- Tâches de batch suivant non bloquées par dépendance batch parent.

## Checklist de route
- [ ] Vérifier `docs/orchestrator-ops/parallel-workstreams.json` (stream/tasks BATCH-06, IDs `DEV-01/02/03`)
- [ ] Vérifier `docs/orchestrator-ops/priority-queue.json` (item BATCH-06)
- [ ] Vérifier preuves `docs/orchestrator-ops/proofs/...`
- [ ] Mettre `docs/product/planning/WORKSTATE.md` à jour après chaque transition.
