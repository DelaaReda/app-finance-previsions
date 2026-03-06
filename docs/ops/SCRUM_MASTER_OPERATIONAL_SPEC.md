# Scrum Master Operational Specification

## Purpose
Define scrum_master as an operational unblock lane that converts stalled orchestration signals into concrete actions.

## Mode
- Default: `FC_SCRUM_MASTER_MODE=operational`
- Fallback: `FC_SCRUM_MASTER_MODE=advisory`

## Responsibilities
- Detect and remediate: `waiting_dep_persistent`, `ready_unclaimed`, `queue_workstreams_desync`, `muted_no_delta`.
- Push actionable messages to `planner|dev|admin`.
- Execute minor direct fixes; escalate sensitive fixes to admin.

## Dual Authority
- Direct (scrum_master): claim nudges, soft autofill, lightweight requeue/refresh.
- Escalated (admin): structural queue/workboard resync, stale lock repair, index rebuild.

## Escalation Policy
- `FC_SCRUM_MASTER_ESCALATE_AFTER_CYCLES=2`
- Cycle 1 without progress: targeted relaunch.
- Cycle 2 without progress: escalate to admin/planner.
- Reset on real progress (`READY* -> IN_PROGRESS`, waiting_dep drop, message action done).

## Message Bus Contract
- message_id required; if missing, runner autogenerates: `<role>-<tick_id>-<target>-<msg_hash8>`.
- Correlation fields expected: tick id, source role, optional batch id.

## Ready State Policy
- Canonical states: `WAITING_DEP`, `READY_PLANNER`, `READY_DEV`, `IN_PROGRESS`, `DONE`, `BLOCKED`.
- Dev claim allowed for `READY_DEV` even with soft-missing fields.

## Health Policy
- Core health includes `scrum_master`.
- Transient scrum-only incidents should degrade to `STALE` before `DEGRADED`.

## Rollback
- `FC_SCRUM_MASTER_MODE=advisory`
- `FC_SCRUM_MASTER_FULL_REMEDIATION=0`
