# PO Scrum Master Reports

## Scope
- Advisory lane only (`po_scrum_master` / technical role `scrum_master`).
- No delivery ownership (no claim/complete/handoff workboard tasks).
- Health core remains computed on `planner/dev/admin` only.

## Execution Modes
- Scheduled in `full` profile every 5 minutes (cron managed by `scripts/fc_setup_crons.sh`).
- Manual run-now supported via:
  - `bash scripts/po_scrum_master_run_now.sh`

## Expected Output Per Run
1. Investigation summary (root-cause oriented):
  - blocked roles, active blockers, runtime evidence source files.
2. Optional targeted communications:
  - `message_to_planner.sh`, `message_to_dev.sh`, `message_to_admin.sh`
  - anti-loop with `message_id`.
3. Report line in this file with UTC timestamp and concise actions.

## Doctor and Monitor Context
- Doctor CLI: `bash scripts/fc_doctor.sh --json`
- Monitor endpoints:
  - `/api/status`
  - `/api/runtime-diagnostics`
  - `/api/doctor`

## Runbook Note
- If advisory lane becomes noisy, disable quickly:
  - `FC_PO_SCRUM_MASTER_CRON_ENABLED=0 bash scripts/fc_setup_crons.sh --profile full`
## 2026-03-04T22:38:05Z
- Advisory run: diagnostic runtime pour roadmap + blocages.
- Planner/dev/admin présentent encore des pannes de session: `ensure_role_session_ready: command not found`, puis repli vers checkpoint.
- Symptômes additionnels: `session_not_ready` (planner/dev), `prompt_stall_abort`/`rc=124` (admin), avec quelques cycles d’attente `admin_tshape=inactive=1`.
- Bilan statut: BATCH-27-ANALYSIS en IN_PROGRESS (planner), BATCH-10 READY et ciblable.
- Cause probable: régression wrapper runner, non-trouvabilité de `ensure_role_session_ready` entraînant dépendance à fallback + baisse de productivité.
- Risque immédiat: progression de BATCH-27 fragile si on dispatche un nouveau ticket sans résoudre ce flux d’exécution.
- Action recommandée: priorité 1 = stabiliser `platform/automation/cron_tmux_role_runner.sh` (chemin/function), puis un recheck de 3 ticks, ensuite reprendre `planner` IN_PROGRESS.
