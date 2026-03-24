# Runner Configuration YAML v1 Specification

Compatibility note:
- target architecture is planner-only scheduling with planner-owned capabilities
- legacy role/feature names may remain in config during migration, but they do not redefine the target topology

## Changelog
- **2026-03-04**: New document; formalized YAML v1 contract, transition policy (`YAML > ENV fallback`), and strict-mode sunset.

## 1) Purpose and Scope
This spec defines the canonical runner configuration contract for orchestration runtime.

Scope:
- File format and required sections.
- Validation requirements.
- ENV fallback migration policy.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Runner config **MUST** declare `version: v1`.
- Config **MUST** include `defaults`, `roles`, `features`, `paths`.
- Core roles (`planner/dev/admin`) and advisory role (`scrum_master`) **MUST** be present in `roles`.
- During migration, resolution order **MUST** be `YAML > ENV fallback`.
- ENV fallback **MUST** be temporary and explicitly sunset.

## 3) Interfaces and Schemas
### Canonical files
- Config file: `/home/venom/analyse-financiere/platform/config/runner/runner_config.v1.yaml`
- Validation schema: `/home/venom/analyse-financiere/platform/config/runner/runner_config.schema.json`

### Required top-level keys
- `version`
- `defaults`
- `roles`
- `features`
- `paths`

### Roles block
Required role entries:
- `planner`
- `dev`
- `admin`
- `scrum_master`

Recommended role keys:
- `model`, `thinking`, `resume`, `rate_limit_precheck`, timeout fields

### Features block
Recommended flags:
- `tshape`
- `admin_dispatcher`
- planner orchestrator and compatibility flags as implemented in runtime

## 4) Runtime Behavior and Edge Cases
- Current config file is JSON-compatible content in `.yaml` path; this is acceptable during transition.
- If schema validation fails, startup behavior should move toward fail-fast in strict mode.
- Missing keys may currently fall back to ENV; this behavior is transitional.

## 5) Operator Commands and Expected Outputs
- View config:
```bash
sed -n '1,220p' platform/config/runner/runner_config.v1.yaml
sed -n '1,220p' platform/config/runner/runner_config.schema.json
```
Expected:
- valid v1 structure with required role keys.

- Regression tests:
```bash
python3 platform/automation/tests/test_role_runtime_context.py
python3 platform/automation/tests/test_runner_message_receipts.py
```
Expected:
- no runtime contract/message regressions while config migration proceeds.

## 6) Observability and Troubleshooting
- Log explicit fallback usage when ENV is used for missing YAML keys.
- Surface resolved runtime config snapshot (without secrets) in runner trace context.
- Use monitor/runtime diagnostics to verify role timeout/behavior drift.

## 7) Compatibility and Migration Notes
Migration stages:
1. Stage A: YAML present, ENV fallback allowed.
2. Stage B: YAML complete, fallback usage monitored.
3. Stage C: strict mode, fallback disabled by default.

Compatibility requirement:
- No immediate breaking change for existing cron runners during Stage A/B.

## 8) Acceptance Criteria
- Canonical config is readable and versioned.
- Schema is explicit and machine-checkable.
- Fallback behavior is documented and time-bounded.
- Runtime behavior remains stable during migration.
