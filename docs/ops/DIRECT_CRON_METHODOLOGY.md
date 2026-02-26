# Direct Cron Methodology (Fallback Profile)

Status note (2026-02-25):
- This profile is kept as fallback documentation.
- Active runtime currently uses tmux role sessions.
- For active operations and monitoring, use `docs/ops/TMUX_CRON_OPERATIONS.md`.

## Goal
Run autonomous cron jobs by role without depending on a legacy orchestrator script or tmux role sessions.

## Mandatory Sources
- `AGENT_WORKFLOW.md`
- `docs/ops/ENGINEERING_PLAYBOOK.md`
- `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`

## Non-negotiable Rules
- Use only read-only analysis or explicit validation commands for the role.
- No `write/edit/git/commit`.
- No dependency on tmux role sessions.
- Keep response compact with the required template.
- If there is no concrete change, return `DELTA: NO_DELTA`.

## Required Output Template
- `STATUS`: `IN_PROGRESS|PASS|BLOCKED`
- `DELTA`
- `EVIDENCE`
- `RISKS`
- `NEXT`
- `VERDICT`: `PASS|BLOCKED`
- `BLOCKER_ID`: `<id|NONE>`
- `NEXT_ACTION_UNIQUE`

## Role Contracts

### Planner (cadence short)
- Inputs:
  - `docs/orchestrator-ops/priority-queue.json`
  - `docs/planning/WORKSTATE.md`
  - `finance-app/openclaw-gates/`
- Objective:
  - Keep queue coherence (`READY/IN_SPRINT/PASS/BLOCKED`).
  - Produce one unique next action for highest-priority `READY` item.

### Dev (cadence short)
- Mandatory checks:
  - `python3 scripts/validate_batch_state.py`
  - `bash scripts/preflight_dispatch.sh`
  - `python3 -m py_compile copilot-app/backend/src/api/main.py`
- Optional check:
  - `curl -fsS http://127.0.0.1:8050/api/health`
- Objective:
  - Report strict gate status and immediate actionable blocker if any command fails.

### Tester (cadence medium)
- Mandatory check:
  - `bash scripts/backend_regression_gate.sh --no-live`
- Objective:
  - Keep regression signal fresh and actionable.
  - Report first failing test and reproduction command on failure.

### QA (cadence medium)
- Inputs:
  - `finance-app/openclaw-gates/`
  - `docs/orchestrator-ops/priority-queue.json`
  - `docs/scrum/sprint-current.md`
- Objective:
  - Validate evidence completeness and consistency (`VERDICT`, `BLOCKER_ID`, `NEXT_ACTION_UNIQUE`).
  - Escalate if artifacts are stale/missing.

## Escalation Contract
- On first blocking failure, return:
  - exact command
  - short error cause
  - impact
  - one rollback/mitigation step
