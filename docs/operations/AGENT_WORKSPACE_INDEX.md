# Agent Workspace Index (Canonical Reference)

## Changelog
- **2026-03-04**: Full rewrite in English; normalized canonical vs compatibility paths and added runtime ownership map.

## 1) Purpose and Scope
This index provides canonical paths and ownership boundaries for agents and operators.

It is the primary path map used by orchestration docs, monitor diagnostics, and troubleshooting workflows.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Agents **MUST** prefer canonical paths over compatibility aliases.
- Mutable runtime data **MUST NOT** be stored under source code roots.
- Ops scripts **SHOULD** resolve root via workspace helpers (writable canonical workspace first).
- Compatibility paths **MUST** be read-only compatibility unless explicitly documented.
- Runtime commands **MUST** execute in VM workspace `/home/venom/analyse-financiere`.
- Runtime commands **MUST NOT** execute on macOS host.
- Canonical runtime docs **MUST NOT** require SSH wrapper syntax (`ssh dev-vm-utm ...`) for standard operations.
- If host context is uncertain, operators **MUST** run `bash scripts/runtime_host_check.sh` and proceed only when `runtime_is_vm=1`.

## 3) Interfaces and Schemas
### Canonical workspace root
- `/home/venom/analyse-financiere`

### Core orchestration files
- Queue: `/home/venom/analyse-financiere/docs/operations/orchestrator/priority-queue.json`
- Workboard: `/home/venom/analyse-financiere/docs/operations/orchestrator/parallel-workstreams.json`
- Monitoring latest: `/home/venom/analyse-financiere/docs/operations/orchestrator/executors-monitoring-latest.json`

### Runtime logs
- Tick logs: `/home/venom/analyse-financiere/logs-codex-runs/fc-ticks/`
- Runner logs: `/home/venom/analyse-financiere/logs-codex-runs/role-runner/`
- Monitor guard logs: `/home/venom/analyse-financiere/logs-codex-runs/monitor-guard.cron.log`

### Contracts and policies
- Runner: `/home/venom/analyse-financiere/platform/automation/cron_tmux_role_runner.sh`
- Tick launcher: `/home/venom/analyse-financiere/scripts/fc_agent_tick.sh`
- Contract guard: `/home/venom/analyse-financiere/platform/policies/role_contract_guard.py`
- Runner config (v1): `/home/venom/analyse-financiere/platform/config/runner/runner.v1.yaml`
- Runner schema (v1): `/home/venom/analyse-financiere/platform/config/schema/runner.v1.schema.json`
- Doctor CLI: `/home/venom/analyse-financiere/scripts/fc_doctor.sh`

## 4) Runtime Behavior and Edge Cases
- Compatibility alias `/home/venom/analyse-financiere/docs/orchestrator-ops` may exist and be readable.
- Canonical orchestrator directory is `docs/operations/orchestrator`.
- If monitor/root detection sees stale shared roots, writable canonical root must win.

## 5) Operator Commands and Expected Outputs
- Verify runtime host context:
```bash
bash scripts/runtime_host_check.sh
```
Expected:
- `runtime_host_kind=vm_runtime`
- `runtime_is_vm=1`

- Verify canonical paths:
```bash
ls -ld docs/operations/orchestrator docs/orchestrator-ops
```
Expected:
- canonical directory present; compatibility alias may be symlink.

- Verify critical files:
```bash
test -f docs/operations/orchestrator/priority-queue.json && echo OK_QUEUE
test -f docs/operations/orchestrator/parallel-workstreams.json && echo OK_WORKBOARD
```
Expected:
- both checks print `OK_*`.

## 6) Observability and Troubleshooting
When path drift is suspected:
- Check monitor-reported `sources` in `/api/status`.
- Compare mtime and content between canonical and alias paths.
- Prefer writing state updates only to canonical paths.

## 7) Compatibility and Migration Notes
- `docs/ops/*` may symlink into `docs/operations/*`; this is expected.
- Historical `docs/orchestrator-ops/*` remains compatibility-only.
- Migration summary tracks deprecation and cutover windows.

## 8) Acceptance Criteria
- All operational runbooks point to canonical paths.
- Queue/workboard references are consistent across monitor, runner, and docs.
- Alias paths are documented as compatibility-only where applicable.
