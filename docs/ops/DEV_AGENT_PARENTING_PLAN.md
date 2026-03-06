# DEV_AGENT_PARENTING_PLAN

Objectif: rendre `dev` autonome, rapide, fiable, avec preuves de livraison vérifiables en continu.

## P0 (immédiat, 24h)

- Aligner `prompt -> guard -> monitor` sur les mêmes règles de qualité evidence.
- Refuser les preuves faibles (`?`, `TODO`, `TBD`, `FIXME`, `NONE` sans raison).
- Exiger les formats sur `complete|handoff`:
  - `verify=before=...; after=...; test=...`
  - `qa_proof=test=...; result=...`
- Exiger les formats sur `claim|complete|handoff`:
  - `architecture_check=layer=...; imports_ok=...; path_target=...`
  - `vision_alignment=batch=...; target=...; impact=...`
  - `reuse_check=<module>` ou `NONE(<raison courte>)`.

Done definition P0:
- `role_contract_guard` bloque systématiquement les contrats faibles.
- `apps/monitor` expose les écarts de qualité (missing/invalid).
- Aucun `complete` dev sans `verify` + `qa_proof` valides.

## P1 (court terme, 2-3 jours)

- Ajouter une boucle de coaching adaptative:
  - si `DEV_*_FORMAT_INVALID` >= 2 ticks: injecter une correction de prompt ciblée.
  - si `missing_*` récurrent: forcer mode claim->patch->test->complete (pas analyse passive).
- Ajouter un score `dev_parent` persistant par tick:
  - `quality_score`, `missing_fields`, `invalid_fields`, `run_note_words`, `failures_24h`.
- Ajouter garde-fou anti-stall:
  - si tâche `READY|IN_PROGRESS` et `task_update=none_*` répété, escalader en blocker actionnable.

Done definition P1:
- Le monitor affiche le score parent + tendances.
- Les boucles passives sont converties en action ou blocker explicite.

## P2 (durcissement, 1 semaine)

- Ajouter tests non-régression sur qualité evidence pour chaque rôle delivery.
- Ajouter "learning memory":
  - enregistrer top 5 causes de blocage dev et corrections efficaces.
- Ajouter gate architecture stricte:
  - preuve de réutilisation modules existants avant création de nouveaux modules.

Done definition P2:
- Taux de contrats dev `STRONG` > 80%.
- `failures_last_24h` dev <= 1 en cadence normale.
- Réduction durable des retours `BLOCKED` non-runtime.

## KPIs de pilotage

- `dev_quality_score_median_24h`
- `%contracts_dev_strong_24h`
- `%complete_with_valid_verify_qa`
- `dev_failures_last_24h`
- `delivery_probe_loops_open`
- `time_to_complete_ready_item`

## Règle d’exploitation

- Priorité absolue: livraison vérifiable sur item `IN_PROGRESS`, puis `READY`.
- Une action concrète par tick.
- Aucun patch massif: patch chirurgical + test ciblé + preuve.
