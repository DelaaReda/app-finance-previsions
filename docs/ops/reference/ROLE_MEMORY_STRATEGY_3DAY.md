# Role Memory Strategy (3-day, profile-aware)

## Goal

Reduce token usage per role tick while preserving enough continuity to avoid architecture regressions and repeated blocker loops.

## What is now implemented

Implementation lives in `scripts/cron_tmux_role_runner.sh` and `scripts/role_memory_append.py`.

- `TMUX_ROLE_CONTEXT_MODE=lean` by default.
- Per-role memory profile is auto-selected via `TMUX_ROLE_MEMORY_PROFILE=auto`.
- Prompt dispatch now uses `primary` vs `retry` scopes:
  - `primary`: full orchestration protocol
  - `retry`: compact protocol to reduce timeout/token burn
- Runtime tails are compacted based on profile (`summary` or `omitted`).
- Role memory summaries are auto-generated at every append:
  - `memory/agents/summaries/<role>.summary.md`
- Loader prefers summary files when present:
  - daily: `memory/summaries/YYYY-MM-DD.summary.md` (if present)
  - role: `memory/agents/summaries/<role>.summary.md` (auto-generated)

## Role memory profiles

### `coordination`

Roles:
- `planner`
- `architect`
- `po`
- `scrum_master`
- `clawsentinel`

Defaults:
- `TMUX_ROLE_MEMORY_DAILY_LINES=24`
- `TMUX_ROLE_MEMORY_ROLE_HISTORY_LINES=18`
- `TMUX_ROLE_RUNTIME_TAIL_MODE=summary`

Why:
- These roles need more cross-team/history context to orchestrate and unblock.

### `analysis`

Roles:
- `analyst`
- `qa`
- `integrator`
- `data_analyst`

Defaults:
- `TMUX_ROLE_MEMORY_DAILY_LINES=14`
- `TMUX_ROLE_MEMORY_ROLE_HISTORY_LINES=12`
- `TMUX_ROLE_RUNTIME_TAIL_MODE=summary`

Why:
- These roles need context and consistency checks, but less than coordinators.

### `delivery`

Roles:
- `dev`
- `backend_engineer`
- `frontend_engineer`
- `infra_engineer`
- `tester`
- fallback for unknown roles

Defaults:
- `TMUX_ROLE_MEMORY_DAILY_LINES=8`
- `TMUX_ROLE_MEMORY_ROLE_HISTORY_LINES=8`
- `TMUX_ROLE_RUNTIME_TAIL_MODE=omitted`

Why:
- Delivery roles need minimal action-focused context to avoid prompt bloat and execution drift.

## Runtime context compaction

In lean mode, the runner replaces heavy fields:

- `agent_memory=summary`
- `peer_contracts=summary`
- `publication_channels=summary`

Tail fields depend on profile:
- `summary` mode: `team_chat_tail`, `team_iteration_tail`, `trace_tail` set to `summary`
- `omitted` mode: same fields set to `omitted`

Memory excerpts are clipped per line to reduce prompt spikes:
- default: `TMUX_ROLE_MEMORY_MAX_LINE_CHARS=180`

`full` mode remains available and multiplies default memory line budgets by 3.

## Prompt compaction and monitoring

- Retry attempts now use a compact orchestration block (`ORCHESTRATION_RETRY_PROMPT`).
- Runner emits prompt-size traces per dispatch:
  - `dispatch_prompt scope=primary|retry ... bytes=<n>`
  - `prompt_memory_context ... bytes=<n>`

## Summary artifacts

`scripts/role_memory_append.py` now writes compact per-role summary files after each memory append:

- `memory/agents/summaries/<role>.summary.md`
- window: last 14 role memory entries
- purpose: low-token role continuity snapshot

## Optional overrides

You can override defaults per tick/job using env vars:

- `TMUX_ROLE_CONTEXT_MODE=lean|full`
- `TMUX_ROLE_MEMORY_PROFILE=auto|coordination|analysis|delivery`
- `TMUX_ROLE_MEMORY_DAILY_LINES=<int>`
- `TMUX_ROLE_MEMORY_ROLE_HISTORY_LINES=<int>`
- `TMUX_ROLE_MEMORY_MAX_LINE_CHARS=<int>`
- `TMUX_ROLE_RUNTIME_TAIL_MODE=auto|full|summary|omitted`

## Validation checklist

- `bash -n scripts/cron_tmux_role_runner.sh`
- `python3 -m py_compile scripts/role_memory_append.py`
- Check generated summaries:
  - `memory/agents/summaries/<role>.summary.md`
