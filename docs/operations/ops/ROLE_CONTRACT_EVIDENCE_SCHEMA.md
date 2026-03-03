# Role Contract EVIDENCE Schema (v2 lean)

Objectif: garder un contrat strict, court, et directement aligné avec `platform/policies/role_contract_guard.py`.

## Format du contrat (8 lignes obligatoires)

Chaque sortie rôle doit contenir exactement ces clés (format `KEY: value`):
- `STATUS`
- `DELTA`
- `EVIDENCE`
- `RISKS`
- `NEXT`
- `VERDICT`
- `BLOCKER_ID`
- `NEXT_ACTION_UNIQUE`

Si une de ces clés manque, le runner applique son fallback de checkpoint.

## Format EVIDENCE

- `EVIDENCE` est une liste `key=value` séparée par `;`
- pas d'espace autour de `=`
- éviter `;` dans les valeurs

Exemple court:
`task_update=analysis_only;lock_check=ok;run_note=Analyse queue et priorites;planner_artifact=docs/product/planning/tasks.md;issues=none`

## Clés minimales (MUST)

Toujours requises:
- `task_update=<claim|complete|handoff|blocked|analysis_only|none_no_ready|none_no_signal>`
- `lock_check=ok`
- `run_note=<phrase >= 3 mots>`
- artefact rôle (une clé):
  - `planner_artifact`, `dev_artifact`, `backend_artifact`, `frontend_artifact`, `data_artifact`, `qa_artifact`, etc.
  - pour un rôle sans mapping explicite (ex: `admin`), utiliser `role_artifact`.

Règle transversale:
- si `STATUS=BLOCKED` alors `BLOCKER_ID` ne peut pas être `NONE`.

## Clés conditionnelles (MUST selon task_update)

- `task_update=claim|handoff`:
  - `stream_id` obligatoire
  - `task_id` obligatoire

- `task_update=complete`:
  - `cmd` obligatoire
  - `tests_run` recommandé (non bloquant)

- `task_update=handoff`:
  - `handoff_to` obligatoire

- `task_update=blocked` avec `BLOCKER_ID` contenant `permission` ou `read_only`:
  - `cmd_err_excerpt` obligatoire

## Clés optionnelles (SHOULD)

- `issues=<none|liste>`
- `suggestions=<none|actions>`
- `tests_run=<name:PASS|FAIL|SKIP,...>`
- `stream_id`, `task_id` aussi utiles en `complete` pour la traçabilité

Ces champs améliorent l'audit, mais ne doivent pas recréer une surcharge documentaire.

## Exemples

### Analyse simple (planner)

```text
STATUS: IN_PROGRESS
DELTA: NO_DELTA
EVIDENCE: task_update=analysis_only;lock_check=ok;run_note=Analyse queue et readiness;planner_artifact=docs/orchestrator-ops/priority-queue.json;issues=none
RISKS: none
NEXT: owner=planner; action=proposer sequencing batch
VERDICT: GO_WITH_CAUTION
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: PLANNER_ANALYSIS_20260303T210000Z
```

### Completion (dev)

```text
STATUS: DONE
DELTA: FEATURE_SHIPPED
EVIDENCE: task_update=complete;lock_check=ok;run_note=Patch endpoint et test valide;dev_artifact=apps/api/src/domains/forecasts/api/brief.py;stream_id=BATCH-06;task_id=BATCH-06-BACKEND;cmd=PYTHONPATH=. pytest -q apps/api/src/domains/forecasts/tests/test_brief_route_contract.py;tests_run=brief_route:PASS
RISKS: low
NEXT: owner=planner; action=valider et fermer task
VERDICT: GO
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: DEV_COMPLETE_BATCH06_20260303T210500Z
```

## Anti-bloat policy

Le guard lean ne demande plus:
- `channels_read`
- `impact_assessment` / `impact_action`
- `arch_rule` / `conformance` / `violations`
- `reflection_passes` / `reflection_dimensions`
- `intent_id` / `intent_registry_ref`

Ces champs peuvent rester en option locale si utiles, mais ne doivent pas être obligatoires.
