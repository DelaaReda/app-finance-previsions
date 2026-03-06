# Migration Summary (Current-State Delta + Deprecations)

## Changelog
- **2026-03-04**: Full rewrite in English; replaced historical narrative with current-state delta, deprecation map, and approved target architecture trajectory.

## 1) Purpose and Scope
This summary tracks migration status from legacy orchestration and monolithic runtime patterns to the current canonical architecture.

It records:
- What is currently live.
- What is approved target but not fully enforced.
- What is deprecated and scheduled for removal.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Documentation **MUST** distinguish `Current (observed)` from `Target (approved)`.
- Deprecated behavior **MUST** include replacement path and removal criteria.
- Migration steps **SHOULD** be progressive with compatibility windows, not big-bang rewrites.

## 3) Interfaces and Schemas
### Current (observed)
- Core runtime lanes: `planner/dev/admin`.
- Advisory lane: `scrum_master` exists but manual-gated in tick launcher.
- Monitor health policy already uses core roles only.
- Message bus exists with events: `message_posted`, `message_delivered`, `message_action`, `message_closed`.
- Runner config file exists at `/home/venom/analyse-financiere/platform/automation/config/runner.v1.yaml` (JSON-compatible YAML content).

### Target (approved)
- `po_scrum_master` scheduled every 5 minutes in `full` profile only.
- Runner config becomes YAML v1 canonical source with startup validation and explicit ENV sunset.
- Doctor JSON CLI+API becomes a single diagnostics contract.

## 4) Runtime Behavior and Edge Cases
- Full profile currently schedules planner/dev/admin + utilities.
- Canary profile currently schedules planner/dev only.
- Compatibility aliases (`docs/orchestrator-ops`) remain in use for some consumers.
- Some target components are documented before strict runtime enforcement (expected during migration windows).

## 5) Operator Commands and Expected Outputs
- Check current cron profile output:
```bash
bash scripts/fc_setup_crons.sh --profile full
bash scripts/fc_setup_crons.sh --profile canary
```
Expected:
- Full: planner/dev/admin entries.
- Canary: planner/dev entries; admin paused.

- Check monitor status:
```bash
curl -s http://127.0.0.1:7779/api/status | jq '{health,agents,po_scrum_master}'
```
Expected:
- health based on core lanes; advisory object present.

## 6) Observability and Troubleshooting
Track migration drift via:
- `docs/operations/orchestrator/executors-monitoring-latest.json`
- `docs/operations/orchestrator/agent-iteration-issues.jsonl`
- `logs-codex-runs/health-snapshot.log`
- `logs-codex-runs/role-runner/*.events.log`

## 7) Compatibility and Migration Notes
### Deprecation map
- Legacy role aliases in tick launcher: compatibility-only.
- Alias orchestrator root (`docs/orchestrator-ops`): compatibility-only.
- ENV-heavy runner config: transitional, to be sunset after YAML strict mode activation.

### Removal checkpoints
- Remove compatibility-only pathways after:
  1. YAML strict mode enabled.
  2. Doctor JSON contract deployed.
  3. Monitor and runtime consumers no longer read legacy aliases.

## 8) Acceptance Criteria
- Every migration statement is tagged as current or target.
- Deprecated items have replacement and removal conditions.
- Runtime and documentation no longer conflict on core policies.
