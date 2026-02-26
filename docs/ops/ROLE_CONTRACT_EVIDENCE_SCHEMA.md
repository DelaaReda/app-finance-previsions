# Role Contract EVIDENCE Schema (v1)

Objectif: rendre `EVIDENCE` exploitable par machine + humain (audit, dedupe, gates), et reduire les "preuves narratives" non verifiables.

## Format (recommande)
- `EVIDENCE` est une suite de paires `key=value` separees par `;`
- Case-insensitive (les scripts normalisent souvent en uppercase)
- Pas d'espaces autour de `=` ou `;`
- Valeurs multi-elements: utiliser `,` (ex: `tests_run=pytest:PASS,curl_health:PASS`)

Exemple:
`task_update=complete;lock_check=ok;stream_id=BATCH-02;task_id=BE-123;backend_artifact=copilot-app/backend/src/api/main.py;cmd=bash scripts/backend_regression_gate.sh --no-live;tests_run=pytest:PASS`

## Clés minimales (baseline)
Toujours presentes:
- `task_update=<claim|complete|handoff|blocked|analysis_only|none_no_ready>`
- `lock_check=ok`
- `<role>_artifact=<path_or_proof>` (au minimum 1 artefact role-specifique)

## Clés recommandées (qualite / audit)
- `stream_id=<stream>`
- `task_id=<task>`
- `handoff_id=<id>`
- `to_role=<role>`
- `cmd=<commande_executee_via_exec_safe>`
- `rc=<0|nonzero|SKIP(reason)>`
- `tests_run=<name:PASS|FAIL|SKIP,...>`
- `proof_manifest=<path>` (vnext: manifeste YAML par task)
- `review_ref=<path_or_run_id>` (review independante)

## Exigences par `task_update` (enforcement progressif)
Les exigences ci-dessous sont `SHOULD` en phase 1 et deviennent `MUST` (au moins pour `complete`) en phase 2.

- `claim`:
  - `stream_id`, `task_id`
- `complete`:
  - `stream_id`, `task_id`, `<role>_artifact`
  - `cmd` et `tests_run` (ou `cmd=SKIP(...)` / `tests_run=SKIP(...)`)
- `handoff`:
  - `handoff_id`, `to_role`, `task_id`
- `blocked`:
  - `blocker_id`, `owner_role`, `eta_utc`
- `analysis_only`:
  - `analysis_refs=<paths>` (ou `analysis_refs=SKIP(no_ready)` si pertinent)

## Notes pratiques
- Les scripts gate utilisent souvent une normalisation en uppercase; `planner_artifact=` et `PLANNER_ARTIFACT=` sont equivalentes.
- Si une commande est volontairement non executee (ex: environnement indisponible), ne pas simuler: utiliser `cmd=SKIP(<raison>)`.

