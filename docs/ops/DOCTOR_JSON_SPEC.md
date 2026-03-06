# Doctor JSON Spec (doctor.v1)

## Sources
- CLI: `scripts/fc_doctor.sh --json`
- Python implementation: `platform/automation/fc_doctor.py`
- Monitor API passthrough: `/api/doctor`, `/api/doctor/latest`
- Legacy fallback (debug only): `FC_DOCTOR_LEGACY=1 scripts/fc_doctor.sh --json`

## Contract
Top-level payload:
- `status`: `ok | degraded | error`
- `generated_at`: ISO UTC timestamp
- `checks`: object keyed by check name
- `meta`: `{ schema_version, duration_ms }`

Checks currently implemented:
- `workspace_root`
- `sessions`
- `locks`
- `queue_workboard`
- `providers`

## Exit codes (CLI)
- `0`: ok
- `1`: degraded
- `2`: error

## Operational use
Use doctor output in gates and monitor diagnostics to avoid ambiguity between runtime stale states and true infra failures.

## Deterministic status mapping
- `ok`: no failed check and no degraded check.
- `degraded`: at least one degraded check, no failed check.
- `error`: at least one failed check.

## Mandatory check identifiers
- `workspace_root`
- `sessions`
- `locks`
- `queue_workboard`
- `providers`

All integrations (CLI and monitor API) must expose the same check keys and status mapping.
