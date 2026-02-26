# Role Contract EVIDENCE Schema (v1)

Objectif: rendre `EVIDENCE` exploitable par machine + humain (audit, dedupe, gates), et reduire les "preuves narratives" non verifiables.

## Format (recommande)
- `EVIDENCE` est une suite de paires `key=value` separees par `;`
- Case-insensitive (les scripts normalisent souvent en uppercase)
- Pas d'espaces autour de `=` ou `;`
- Valeurs multi-elements: utiliser `,` (ex: `tests_run=pytest:PASS,curl_health:PASS`)

Exemple:
`task_update=complete;lock_check=ok;run_note=Ajoute un cache stable et tests;stream_id=BATCH-02;task_id=BE-123;backend_artifact=copilot-app/backend/src/api/main.py;cmd=bash scripts/backend_regression_gate.sh --no-live;tests_run=pytest:PASS`

## Clés minimales (baseline)
Toujours presentes:
- `task_update=<claim|complete|handoff|blocked|analysis_only|none_no_ready|none_no_signal>`
- `lock_check=ok`
- `run_note=<phrase (>= 5 mots) décrivant l’action du tick, sans ';'>`
- `<role>_artifact=<path_or_proof>` (au minimum 1 artefact role-specifique)
- `queue_version=<checksum_or_version>`
- `workboard_version=<checksum_or_version>`

Delivery (`task_update=claim|complete|handoff`) MUST aussi contenir:
- `intent_id=<id_unique>`
- `intent_chat_ref=<timestamp_ou_ref_chat>`
- `intent_memory_ref=<path#ligne_ou_timestamp>`
- `edit_scope=<zone_touchee>`

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
- `tools_used=<comma_list>` (ex: `web.search,web.fetch,playwright-mcp`)
- `web_ref=<url_or_doc_ref>` (si recherche/navigation web effectuee)
- `browser_ref=<trace_or_session_ref>` (si verification browser/cdp)
- `tooling_check=<PASS|BLOCKED>` (etat preflight `scripts/dev_qa_tooling_check.sh`)
- `tooling_ref=<path_or_run_ref>` (log ou trace du preflight outillage)
- `planned_files=<csv_paths>` (fichiers cibles annonces avant edition)
- `eta_minutes=<delai_estime>` (TTL de pre-annonce)

## Exigences par `task_update` (enforcement progressif)
Les exigences ci-dessous sont `SHOULD` en phase 1 et deviennent `MUST` (au moins pour `complete`) en phase 2.

- `claim`:
  - `stream_id`, `task_id`
  - `intent_id`, `intent_chat_ref`, `intent_memory_ref`, `edit_scope`
- `complete`:
  - `stream_id`, `task_id`, `<role>_artifact`
  - `cmd` et `tests_run` (ou `cmd=SKIP(...)` / `tests_run=SKIP(...)`)
  - `intent_id`, `intent_chat_ref`, `intent_memory_ref`, `edit_scope`
- `handoff`:
  - `handoff_id`, `to_role`, `task_id`
  - `intent_id`, `intent_chat_ref`, `intent_memory_ref`, `edit_scope`
- `blocked`:
  - `blocker_id`, `owner_role`, `eta_utc`
- `analysis_only`:
  - `analysis_refs=<paths>` (ou `analysis_refs=SKIP(no_ready)` si pertinent)
  - si usage web/browser: `tools_used` + `web_ref`/`browser_ref`

## Notes pratiques
- Les scripts gate utilisent souvent une normalisation en uppercase; `planner_artifact=` et `PLANNER_ARTIFACT=` sont equivalentes.
- Si une commande est volontairement non executee (ex: environnement indisponible), ne pas simuler: utiliser `cmd=SKIP(<raison>)`.
- Ne pas "debugger" avec 30 commandes dans `cmd=`: la preuve machine (cmd/tests_run) reste utile, mais `run_note` doit expliquer en langage humain ce qui a été tenté/changé/verifié pour faciliter le troubleshooting.
