# PO Scrum Master Advisory Specification

## Changelog
- **2026-03-04**: New document; defines advisory-only scope, message-routing behavior, and runtime policy for `po_scrum_master`.

## 1) Purpose and Scope
This spec defines the `po_scrum_master` lane as an advisory coordinator that investigates blockers and improves inter-agent communication.

It does not own delivery implementation.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- `po_scrum_master` **MUST** be advisory-only.
- It **MUST NOT** claim, complete, or close delivery tasks owned by core lanes.
- It **MAY** post targeted messages to `planner/dev/admin` via message bus.
- It **MUST** produce investigation summaries and references to evidence sources.
- Its internal blockers **MUST NOT** degrade global health.

## 3) Interfaces and Schemas
### Lane identity
- Technical role: `scrum_master`
- Display name: `po_scrum_master`

### Activation controls
- `FC_ENABLE_PO_SCRUM_MASTER=1`
- `FC_PO_SCRUM_MASTER_RUN_NOW=1`
- `TMUX_ROLE_ENABLE_PO_SCRUM_MASTER=1`

### Communication output
- Message bus events via `/home/venom/analyse-financiere/docs/ops/AGENT_MESSAGE_BUS.jsonl`
- Advisory report file: `/home/venom/analyse-financiere/docs/ops/PO_SCRUM_MASTER_REPORTS.md`

## 4) Runtime Behavior and Edge Cases
### Current observed behavior
- Manual run path is available via `scripts/po_scrum_master_run_now.sh`.
- Tick script rejects `scrum_master` unless explicit run-now flags are set.

### Approved target behavior
- Schedule `po_scrum_master` every 5 minutes in `full` profile only.
- Keep `canary` free of advisory cron lane.

Edge cases:
- If advisory run fails, core lane health remains computed independently.
- Message post limits and cooldown prevent noisy repost loops.

## 5) Operator Commands and Expected Outputs
- Manual execution:
```bash
bash scripts/po_scrum_master_run_now.sh
```
Expected:
- advisory run starts with explicit environment flags.

- Monitor verification:
```bash
curl -s http://127.0.0.1:7779/api/status | jq '.po_scrum_master'
```
Expected:
- advisory object present with mode/activity metadata.

## 6) Observability and Troubleshooting
Key artifacts:
- `logs-codex-runs/fc-ticks/scrum_master.tick.log`
- `logs-codex-runs/role-runner/scrum_master.live.log`
- `docs/ops/PO_SCRUM_MASTER_REPORTS.md`
- `docs/ops/AGENT_MESSAGE_BUS.jsonl`

## 7) Compatibility and Migration Notes
- Legacy alias mapping can still map `scrum_master` to planner in compatibility mode; advisory mode must override this mapping when enabled.
- Full cron activation is an approved direction and should be rolled out only in profile `full`.

## 8) Acceptance Criteria
- Advisory runs are visible and traceable.
- No delivery ownership hijack by `po_scrum_master`.
- Message routing improves coordination without introducing health regressions.
