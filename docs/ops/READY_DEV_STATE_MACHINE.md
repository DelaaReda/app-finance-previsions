# READY_DEV State Machine

## Canonical States
- `WAITING_DEP`
- `READY_PLANNER`
- `READY_DEV`
- `IN_PROGRESS`
- `DONE`
- `BLOCKED`

## Transition Rules
- `WAITING_DEP -> READY_PLANNER`: all dependencies resolved.
- `READY_PLANNER -> READY_DEV`: dev-executable minimum contract validated.
- `READY_DEV -> IN_PROGRESS`: dev claim/progress starts.
- `IN_PROGRESS -> DONE|BLOCKED`: unchanged runtime rule.

## Backward Compatibility
- Legacy `READY` is interpreted as `READY_PLANNER` during migration.
- Queue/workboard synchronization accepts `READY`, `READY_PLANNER`, `READY_DEV`.

## Dev Claim Policy
- Claim on `READY_DEV` is allowed with soft-missing fields.
- Soft-missing fields are autofilled and traced in issues.

## Runtime Reconcile Rules (2026-03-06)
- Dev force-claim is triggered only when `READY_DEV>0` (not merely `READY_PLANNER`).
- If dev sees only `READY_PLANNER` tasks, runner emits `DELTA=READY_PLANNER_PENDING_NORMALIZATION` with `NEXT=owner=planner|scrum_master; action=normalize_to_ready_dev`.
- Doctor/monitor normalization treats `READY` and `READY_PLANNER` as equivalent for mismatch detection.

### 2026-03-06 update
- Legacy task state token `READY` is now normalized to `READY_PLANNER` before recompute.
- For `role=dev`, recompute promotes ready-like tasks to `READY_DEV` deterministically.
- Queue/workboard sync now preserves `READY_DEV` end-to-end for actionable dev lanes.
