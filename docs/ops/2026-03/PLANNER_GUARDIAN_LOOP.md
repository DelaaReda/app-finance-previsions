# Planner Guardian Loop (2026-03)

## Goal
Keep `planner` autonomous and aligned with project vision + architecture by adding a closed-loop monitor:

1. `planner` emits contract (8 lines).
2. `planner_guardian.py` scores the contract and tracks drift streaks.
3. Guardian writes observability artifacts.
4. Guardian can publish escalation directives.
5. Next planner tick reads latest guardian feedback directly in its prompt.

## Runtime Integration
- Runner: `platform/automation/cron_tmux_role_runner.sh`
- Monitor script: `platform/automation/planner_guardian.py`

The runner calls guardian from `publish_execution_monitoring_if_enabled()`, so guardian still runs even if regular execution monitoring is disabled.

## Main Env Flags
- `TMUX_ROLE_PLANNER_GUARDIAN_ENABLED=1|0`
- `TMUX_ROLE_PLANNER_GUARDIAN_INCLUDE_IN_PROMPT=1|0`
- `TMUX_ROLE_PLANNER_GUARDIAN_LATEST_FILE`
- `TMUX_ROLE_PLANNER_GUARDIAN_EVENTS_FILE`

## Outputs
- Latest snapshot JSON:
  - `docs/orchestrator-ops/planner-guardian-latest.json`
- Append-only events JSONL:
  - `docs/orchestrator-ops/planner-guardian-events.jsonl`
- Planner contract audit JSONL (clean troubleshooting feed):
  - `docs/orchestrator-ops/planner-audit-events.jsonl`
- Planner timeline (runner events, deduplicated):
  - `docs/orchestrator-ops/planner-timeline.log`
- Role runner structured events:
  - `logs-codex-runs/role-runner/planner.events.log`
- Role runner raw live trace:
  - `logs-codex-runs/role-runner/planner.live.log`
- Guardian state/streaks:
  - `/home/venom/.openclaw/cron/role-state/planner_guardian_state.json`
- Directive bus (when drift repeats):
  - `docs/ops/DIRECTIVE_BUS.jsonl`

## Log Hygiene
- Raw trace (`planner.live.log`) keeps full detail.
- Clean trace (`planner.events.log`) keeps one-line events with dedupe window.
- Planner timeline mirrors clean events for quick human tailing.
- Planner audit captures parsed contract + evidence + guardian score per output source.

## Scoring Focus
Guardian checks:
- task_update consistency vs runtime (`queue_has_ready`, runway short)
- planner artifact presence
- architecture and vision traceability
- stream/task identifiers when delivery action is declared

Escalation trigger (deduplicated):
- `ready_idle_streak >= 3` OR
- `low_score_streak >= 3` OR
- `runway_no_batch_streak >= 3`

## Validation Commands
```bash
bash -n platform/automation/cron_tmux_role_runner.sh
python3 -m py_compile platform/automation/planner_guardian.py
```

## Notes
- Canonical orchestration paths are under `platform/automation/*`.
- `scripts/cron_tmux_role_runner.sh` is a symlink to the canonical runner.
- Keep planner changes in canonical files only to avoid drift.
