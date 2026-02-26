# Incident Taxonomy (Ops / Orchestration)

Objectif: réduire la charge mentale en standardisant les problèmes d’exécution (cron/tmux/runner) dans des **codes courts** + une structure de rapport.

## Codes (à utiliser dans ADMIN_TEAM_CHAT / reports)

### Cron / Scheduler
- `CRON_TIMEOUT` : job execution timed out
- `CRON_ERROR` : lastStatus=error
- `STALE_RUNNING` : runningAtMs présent mais pas de process live
- `SCHEDULER_LAG` : nextRunAtMs / run_age anormal (drift)

### Runner / Output contract
- `TMUX_REPLY_UNPARSEABLE`
- `TMUX_RESPONSE_UNSTRUCTURED`
- `EVIDENCE_MISSING_EXEC_REPORT`
- `EVIDENCE_MISSING_ISSUES`
- `EVIDENCE_MISSING_SUGGESTIONS`
- `ROLE_ARTIFACT_MISSING`
- `PREANNOUNCE_EVIDENCE_MISSING`

### Delivery / Governance
- `DELIVERY_TARGET_MISSING`
- `MODEL_NOT_ALLOWED`
- `THINKING_NOT_MAX`

### Progress / Flow
- `NO_DELTA_STREAK`
- `NO_PROGRESS_STREAK`
- `QUEUE_READY_NOT_DISPATCHED`

## Reporting format (obligatoire)

Dans `docs/ops/ADMIN_TEAM_CHAT.md`:

- `[ts] [admin] TYPE: ALERT MSG: exec_issue=<CODE>; scope=<role|cron|system>; evidence=<file:line|jobId|contract_ref>; impact=<delivery|ops|cost>; suggestion=<NEXT_ACTION_UNIQUE>`

Règle: **une action unique** par incident, pas de listes infinies.
