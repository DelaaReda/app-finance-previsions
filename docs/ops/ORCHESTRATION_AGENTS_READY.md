# Orchestration - Pret pour agents (2026-03-03)

Objectif: checklist de validation avant reactivation et reference rapide de troubleshooting en mode lean.

---

## Validations prealables (avant reactivation)

```bash
# 1) Plomberie / board
bash platform/policies/validate_parallel_plumbing.sh
python3 scripts/parallel_workstream.py status

# 2) Tooling
bash platform/automation/dev_qa_tooling_check.sh

# 3) Backend (si taches delivery)
curl -s http://localhost:8050/api/health | jq '.status'
bash scripts/backend_regression_gate.sh --no-live

# 4) Monitor canonique (roles actifs + couverture lanes)
bash scripts/monitor_agents.sh
```

---

## Topologie runtime canonique (lean)

Le monitoring raisonne en lanes canoniques:
- `planner`: `planner`, `vision-architect-tasks-planner`, `analyst`, `architect`, `po`, `scrum_master`
- `dev`: `dev`, `backend_engineer`, `frontend_engineer`, `data_analyst`, `integrator`, `infra_engineer`, `tester`, `qa`
- `admin`: `admin`, `clawsentinel`

Important:
- Les lignes cron peuvent encore contenir des roles specialises.
- Le monitor les normalise en lanes canoniques pour eviter les faux mismatch.

### Couverture cron critique (delivery)

Ne pas se limiter a `planner/dev/admin` dans le crontab si des batches delivery sont actifs.

Rôles delivery minimum a planifier:
- `backend_engineer`
- `frontend_engineer`
- `data_analyst`

Stagger recommande:
- `planner`: `:00/:22/:44`
- `data_analyst`: `:03/:25/:47`
- `backend_engineer`: `:06/:28/:50`
- `frontend_engineer`: `:12/:34/:56`

Check rapide:
```bash
crontab -l | rg -n "fc_agent_tick.sh (planner|backend_engineer|frontend_engineer|data_analyst)"
```

Source de verite:
- `crontab -l` pour les jobs actifs
- `bash scripts/monitor_agents.sh` pour l'etat canonique et la couverture workboard

---

## Contrat role (lean) - minimum bloquant

Chaque role doit sortir les 8 lignes:
- `STATUS`, `DELTA`, `EVIDENCE`, `RISKS`, `NEXT`, `VERDICT`, `BLOCKER_ID`, `NEXT_ACTION_UNIQUE`

`EVIDENCE` minimum:
- `task_update=<claim|complete|handoff|blocked|analysis_only|none_no_ready|none_no_signal>`
- `lock_check=ok`
- `run_note=<phrase >=5 mots>`
- artefact role (`planner_artifact`, `dev_artifact`, ..., ou `role_artifact`)

Conditions:
- `claim|handoff` -> `stream_id` + `task_id`
- `complete` -> `cmd` + `tests_run`
- `handoff` -> `handoff_to`
- `STATUS=BLOCKED` -> `BLOCKER_ID` non `NONE`
- blocker permission/read_only -> `cmd_err_excerpt`

Reference detaillee: `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`.

---

## Erreurs bloquantes frequentes

### 1) `ROLE_CONTRACT_MISSING` / `TASK_UPDATE_MISSING`
Cause: contrat incomplet ou EVIDENCE non conforme.
Action: regenerer le contrat minimal lean (8 lignes + evidence minimale).

### 2) `signal_unparseable`
Cause: sortie bruitee/non parsable.
Action: sortie texte brut seulement, une cle par ligne, sans markdown.

### 3) Mismatch cron/workboard
Cause: confusion entre roles specialises et lanes canoniques.
Action: verifier `bash scripts/monitor_agents.sh` et corriger les jobs absents sur les lanes attendues.

### 4) Orphan sessions tmux
Cause: anciennes sessions (`codex_*_cron`, `qwen_*`) non alignees avec les jobs actifs.
Action: cleanup via process ops puis verifier que `orphans` baisse dans le monitor.

---

## Supervision continue (copier-coller)

```bash
# 1) Monitor canonique
bash scripts/monitor_agents.sh

# 2) Sessions tmux
 tmux list-sessions -F '#S' | sort

# 3) Etat queue/workboard
python3 scripts/parallel_workstream.py status

# 4) Logs des lanes canoniques
for r in planner dev admin; do
  echo "== $r =="
  tail -n 20 "logs-codex-runs/role-runner/${r}.live.log" 2>/dev/null || true
done

# 5) Detection rapide des derives
rg -n "NO_DELTA|NO_READY|BLOCKED|checkpoint_fallback|signal_unparseable" logs-codex-runs/role-runner/*.live.log
```

---

Voir aussi:
- `docs/ops/ORCHESTRATION_RELIABILITY_SPEC.md`
- `docs/ops/AGENTS_READY.md`
