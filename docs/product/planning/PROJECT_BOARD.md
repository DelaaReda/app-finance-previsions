# PROJECT_BOARD (Vision + Orchestration)

## Sources de vérité
- `docs/product/planning/PRODUCT_VISION.md`
- `docs/product/planning/WORKSTATE.md`
- `docs/orchestrator-ops/parallel-workstreams.json`
- `docs/orchestrator-ops/priority-queue.json`

## État courant
- **BATCH-01**: CLOSE
- **BATCH-02**: CLOSE
- **BATCH-03**: IN_PROGRESS
- **BATCH-04**: READY (planifié)
- **BATCH-05**: READY (planifié)
- **BATCH-06**: READY (planifié)
- **BATCH-07**: READY (planifié)

## Priorité opérationnelle immédiate
1. Poursuivre BATCH-03 avec tâches prêtes pour `frontend_engineer`, `backend_engineer`, `data_analyst`.
2. Valider completion avec workboard + queue avant ouverture de `BATCH-04`.
3. Maintenir la règle: `planner` ne doit pas réouvrir/fermer de batch sans preuve d'achèvement dans les deux sources.

## Risques à surveiller
- État de tâche incohérent entre queue et workboard.
- Handoff/communication de status en retard (batch trop vite marqué complet).
- Tâches de batch suivant non bloquées par dépendance batch parent.

## Checklist de route
- [ ] Vérifier `docs/orchestrator-ops/parallel-workstreams.json` (stream/taskes BATCH-03)
- [ ] Vérifier `docs/orchestrator-ops/priority-queue.json` (item BATCH-03)
- [ ] Vérifier preuves `docs/orchestrator-ops/proofs/...`
- [ ] Mettre `docs/product/planning/WORKSTATE.md` à jour après chaque transition.
