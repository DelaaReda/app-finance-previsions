# WORKSTATE (legacy location)

Ce fichier est conservé pour compatibilité.

La source canonique de pilotage est maintenant :

- `docs/product/planning/WORKSTATE.md`

Le planner, les rôles et les scripts d’orchestration doivent lire :

1. `docs/planning/PRODUCT_VISION.md`
2. `docs/product/planning/WORKSTATE.md`
3. `docs/orchestrator-ops/parallel-workstreams.json`

Voir aussi `docs/orchestrator-ops/priority-queue.json`.

Ce fichier ne doit pas contenir d’état métier propre (éviter la divergence).
