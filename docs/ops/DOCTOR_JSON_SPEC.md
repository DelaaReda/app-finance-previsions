# Doctor JSON Spec (doctor.v1)

## Sources
- CLI: `scripts/fc_doctor.sh --json`
- Python implementation: `platform/automation/fc_doctor.py`
- Monitor API passthrough: `/api/doctor`, `/api/doctor/latest`
- Legacy fallback (debug only): `FC_DOCTOR_LEGACY=1 scripts/fc_doctor.sh --json`

## Contract
Top-level payload:
- `status`: `ok | degraded | error`
- `overall_status`: same current overall status as `status`, preserved for clarity
- `overall_status_source`: current aggregation source for the overall status
- `generated_at`: ISO UTC timestamp
- `checks`: object keyed by check name
- `runtime_status`: explicit runtime or agentic status
- `runtime_status_source`
- `planning_status`: explicit planning-plane status
- `planning_status_source`
- `non_runtime_degradations`: list of degraded or error checks that are outside the runtime critical path
- `meta`: `{ schema_version, duration_ms }`
- compatibility top-level fields may also be exposed for operator and runtime dashboards, including:
  - `app_runtime`
  - `agentic_runtime`
  - `planning_plane`
  - `app_providers`
  - `agent_providers`
  - `openclaw_gateway`
  - `worker_orphan_count`
  - `runtime_truth`
  - `event_store_primary`

Checks currently implemented:
- `workspace_root`
- `runtime_state`
- `plane_planning`
- `openclaw_gateway`
- `sessions`
- `locks`
- `queue_workboard`
- `providers`
- `planner_dispatch`
- `dynamic_workers`

## Exit codes (CLI)
- `0`: ok
- `1`: degraded
- `2`: error

## Operational use
Use doctor output in gates and monitor diagnostics to avoid ambiguity between runtime stale states and true infra failures.
Use `runtime_truth`, `event_store_primary`, and `runtime_truth_source` as the critical runtime indicators.
Do not treat compatibility registries as the source of truth when doctor exposes a healthy SQLite or event-store-backed runtime.
Prefer `runtime_status` over top-level `status` when the operational question is specifically "is the runtime healthy?".

## Deterministic status mapping
- `ok`: no failed check and no degraded check.
- `degraded`: at least one degraded check, no failed check.
- `error`: at least one failed check.

Important interpretation rule:
- a global `degraded` status can be caused by non-runtime checks such as `plane_planning` or `openclaw_gateway`
- runtime is considered healthy when runtime-specific checks remain `ok`, especially:
  - `runtime_state`
  - `queue_workboard`
  - `planner_dispatch`
  - `runtime_truth.event_store_primary=true`

## Mandatory check identifiers
- `workspace_root`
- `runtime_state`
- `plane_planning`
- `openclaw_gateway`
- `sessions`
- `locks`
- `queue_workboard`
- `providers`
- `planner_dispatch`
- `dynamic_workers`

All integrations (CLI and monitor API) must expose the same check keys and status mapping.
