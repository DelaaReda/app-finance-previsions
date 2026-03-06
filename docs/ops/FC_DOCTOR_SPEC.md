# FC Doctor Specification (CLI + Monitor API)

## Changelog
- **2026-03-04**: New document; defines target single-doctor JSON contract and integration points.

## 1) Purpose and Scope
This spec defines a single machine-readable diagnostics contract (“doctor”) for orchestration runtime.

Scope:
- JSON output format.
- Required checks.
- Exit code semantics.
- Monitor API integration.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Doctor output **MUST** be JSON.
- Doctor **MUST** check canonical root, sessions, locks, queue/workboard, and provider state.
- Doctor **MUST** return deterministic exit codes.
- Doctor API exposure **MUST** be non-blocking for monitor responsiveness.

## 3) Interfaces and Schemas
### CLI contract (target)
- Command: `bash scripts/fc_doctor.sh --json`
- Output schema:
  - `status`: `ok|degraded|error`
  - `generated_at`
  - `schema_version`
  - `duration_ms`
  - `checks[]` with `{id,status,evidence,fix_hint}`

### Exit codes (target)
- `0`: ok
- `1`: degraded
- `2`: error

### API contract (target)
- Endpoint: `GET /api/doctor`
- Returns latest doctor snapshot and check details.

## 4) Runtime Behavior and Edge Cases
Current state:
- No canonical `fc_doctor.sh`/`fc_doctor.py` is active in runtime scripts.
- Diagnostics are currently split across `fc_health_check.sh`, `monitor_agents.sh`, and monitor APIs.

Target state:
- Consolidate split checks into single doctor contract while preserving existing scripts as compatibility wrappers.

Edge cases:
- If one check source is unavailable, doctor should degrade that check, not crash the whole payload.

## 5) Operator Commands and Expected Outputs
Current checks:
```bash
bash scripts/fc_health_check.sh --strict
bash scripts/monitor_agents.sh
```
Expected:
- Human-readable diagnostics from both scripts.

Target checks (post-implementation):
```bash
bash scripts/fc_doctor.sh --json
```
Expected:
- Single JSON payload with deterministic status/exit code.

## 6) Observability and Troubleshooting
Doctor should aggregate evidence from:
- state contracts in `/home/venom/.openclaw/cron/role-state`
- tick/runner logs in `logs-codex-runs`
- queue/workboard JSON in `docs/operations/orchestrator`
- monitor/runtime API reachability checks

## 7) Compatibility and Migration Notes
- Introduce doctor as additive capability first.
- Keep existing health scripts operational until doctor parity is reached.
- Monitor can consume cached doctor snapshot before on-demand execution.

## 8) Acceptance Criteria
- Doctor JSON contract is stable and machine-consumable.
- Exit codes align with status semantics.
- Monitor can expose doctor without harming API latency.
- Existing operators can migrate from split checks to unified doctor safely.
