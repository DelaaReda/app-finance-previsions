# Runner Modular Architecture (v1)

## Goal
Reduce orchestration risk by splitting the legacy monolithic runner into focused shell modules while preserving the 8-line contract runtime behavior.

## Module map
- `platform/automation/runner/main.sh`: module bootstrap and load order.
- `platform/automation/runner/config.sh`: versioned runner config loading/validation bridge.
- `platform/automation/runner/bootstrap.sh`: helper path resolution + shared bootstrap helpers.
- `platform/automation/runner/role_routing.sh`: role normalization and supported-role policy.
- `platform/automation/runner/session_channel.sh`: primary channel selection (`tmux`/`codex_exec`).
- `platform/automation/runner/retries.sh`: timeout/retry normalization helpers.
- `platform/automation/runner/retry_policy.sh`: retry decision helpers.
- `platform/automation/runner/contracts.sh`: contract parsing and blockers helpers.
- `platform/automation/runner/locks.sh`: lock staleness and lock-age helpers.
- `platform/automation/runner/message_bus.sh`: message bus gate helpers.
- `platform/automation/runner/tshape.sh`: T-shape targeting helpers.
- `platform/automation/runner/tshape_dispatch.sh`: takeover activation helper.
- `platform/automation/runner/telemetry.sh`: trace helper.

## Runtime wiring
- `platform/automation/cron_tmux_role_runner.sh` sources `platform/automation/runner/main.sh` if present.
- `scripts/fc_agent_tick.sh` also sources the same module entrypoint.
- Config sourcing and role normalization are centralized in modules and used by both entrypoints.

## Validation commands
- `bash -n platform/automation/cron_tmux_role_runner.sh`
- `bash -n scripts/fc_agent_tick.sh`
- `bash platform/automation/tests/test_runner_modules.sh`

## Rollback
1. Set `RUNNER_MODULE_MAIN` to an empty path in local execution env (or temporarily move `platform/automation/runner/main.sh`).
2. Keep using legacy inline logic from runner scripts.
3. Re-run `bash scripts/fc_health_check.sh --strict`.

## 2026-03-05 Runtime Contract Hardening

### Added runtime knobs
- `TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD` (default `3`): forces actionable next step when passive contracts persist on active lanes.

### Added evidence telemetry (additive)
- `fallback_reason`
- `fallback_count_window`
- `actionability_state`

These fields are emitted in fallback/reconcile paths without changing the 8-line contract shape.

### Verification
```bash
bash -n platform/automation/cron_tmux_role_runner.sh
python3 -m pytest -q platform/automation/tests/test_role_runtime_context.py
```
## Update 2026-03-06 — Dev Anti-Passive Enforcement

Runner post-contract normalization now enforces actionability for `dev`:

- If `dev_has_ready_task=1` and `dev_wait_allowed=0`, passive outputs are normalized to:
  - `STATUS=IN_PROGRESS`
  - `DELTA=READY_ITEM_AVAILABLE_RUNTIME_CONTEXT`
  - `NEXT=owner=dev; action=claim_or_progress_now`
- `analysis_only` is no longer allowed to repeat indefinitely in this context.
- Runtime evidence now includes `passive_with_ready_streak`.

New toggle:

- `FC_DEV_STRICT_ACTIONABILITY=1` (default).

Additional runner knobs (VM defaults):

- `TMUX_ROLE_DEV_AUTONOMY_STALL_THRESHOLD_TICKS=2`
- `TMUX_ROLE_DEV_AUTONOMY_ENFORCE_COOLDOWN_SECONDS=300`
- `TMUX_ROLE_DEV_AUTONOMY_MAX_ENFORCED_PER_HOUR=4`
- `TMUX_ROLE_DEV_AUTONOMY_ENFORCE_GUARD=1`

Persistent state:

- `DEV_AUTONOMY_STATE_FILE=/home/venom/.openclaw/cron/role-state/dev.autonomy.state.json`

Validation:
```bash
cd /home/venom/analyse-financiere
python3 -m pytest -q platform/automation/tests/test_dev_autonomy_enforcement.py
```
