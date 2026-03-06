# PO Scrum Master Cron Runbook

## Purpose
Run advisory `po_scrum_master` automatically every 5 minutes in full profile to improve communication/dispatch recommendations without affecting core health.

## Scheduling
Configured by `scripts/fc_setup_crons.sh`.

- Cron expression default: `*/5`
- Role invocation:
  - `FC_ENABLE_PO_SCRUM_MASTER=1`
  - `FC_PO_SCRUM_MASTER_RUN_NOW=1`
  - `TMUX_ROLE_ENABLE_PO_SCRUM_MASTER=1`
  - `ROLE_ALLOW_FILE_EDITS=0`

## Feature flag
- `FC_PO_SCRUM_MASTER_CRON_ENABLED`
  - `1` by default in full profile
  - `0` by default in canary profile

## Logs
- `logs-codex-runs/fc-ticks/scrum_master.cron.log`
- Advisory report file: `docs/ops/PO_SCRUM_MASTER_REPORTS.md`

## Health model
- Core health remains computed from `planner/dev/admin` only.
- `po_scrum_master` is advisory and must never trigger global `DEGRADED` by itself.

## Rollback
- Set `FC_PO_SCRUM_MASTER_CRON_ENABLED=0`
- Re-run `bash scripts/fc_setup_crons.sh --full`

## Manual Run-Now (VM canonical)
Use:
```bash
bash scripts/po_scrum_master_run_now.sh
```

Behavior:
- Resolves workspace root through `platform/automation/lib/workspace_paths.sh` and enforces VM runtime guard.
- Uses canonical writable workspace (no implicit `/shared` fallback drift).
- Invokes runner via `bash` and checks runner file existence (`-f`), not executable bit.
- Keeps advisory constraints (`ROLE_ALLOW_FILE_EDITS=0`, no delivery ownership actions).

## Start / Validate / Recover / Rollback / Evidence

### Start
```bash
FC_PO_SCRUM_MASTER_CRON_ENABLED=1 bash scripts/fc_setup_crons.sh --profile full
```

### Validate
```bash
crontab -l | rg 'cron_po_scrum_master_tick\.sh|fc_agent_tick\.sh scrum_master'
tail -n 80 logs-codex-runs/fc-ticks/scrum_master.cron.log
```

### Recover
```bash
bash scripts/po_scrum_master_run_now.sh
```

### Rollback
```bash
FC_PO_SCRUM_MASTER_CRON_ENABLED=0 bash scripts/fc_setup_crons.sh --profile full
```

### Evidence path
- `logs-codex-runs/fc-ticks/scrum_master.cron.log`
- `docs/ops/PO_SCRUM_MASTER_REPORTS.md`
- `docs/ops/AGENT_MESSAGE_BUS.jsonl`

## Scheduling note
Default cron expression is `3-58/5` (one run every 5 minutes, offset from minute 3) to avoid simultaneous collision with top-of-minute planner ticks.
## Update 2026-03-06 — Advisory Contract Clarification

- `po_scrum_master` remains advisory-only.
- It does not participate in core health computation (`planner/dev/admin` only).
- Contract guard defaults `scrum_master` mode to advisory non-blocking.
- Any advisory BLOCKED output is normalized to:
  - `STATUS=IN_PROGRESS`
  - `VERDICT=GO_WITH_CAUTION`
  - `BLOCKER_ID=NONE`
