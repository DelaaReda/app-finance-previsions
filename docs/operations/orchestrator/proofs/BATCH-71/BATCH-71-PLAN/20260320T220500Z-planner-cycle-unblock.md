planner_task: BATCH-71-PLAN
stream_id: BATCH-71
role: planner
status: PASS

summary:
- Canonical cycle was normalized away from stale `BATCH-24` to active `BATCH-71`.
- Queue and workboard now agree that `BATCH-71` is the only live cycle.
- Planner can close `PLAN` without waiting on stale projection debt.

root_cause:
- Top-level `active_cycle.active_batch_ids` stayed stale on `BATCH-24` even though queue row was `CLOSED` and workboard stream was `DONE`.
- This hid the real live stream and created a false blocker for planner delivery proof on the new batch.

fix_applied:
- `reconcile_state(...)` now normalizes and persists `active_cycle` using only open queue/workboard rows.
- Closed stale batches are migrated into `recent_completed_batch_ids`.
- Planner completion prompt now states the exact mandatory proof fields for PLAN/ANALYSIS/ARCH/GOV_REVIEW closure.

architecture_check:
- layer=planner_runtime; imports_ok=yes; path_target=platform/automation/compat/projections/parallel_workstream.py

vision_alignment:
- batch=BATCH-71; target=personal_finance_copilot_brief_and_open; impact=planner_cycle_unblocked

verify:
- before=active_cycle_stale_on_BATCH-24_and_no_canonical_live_proof
- after=active_cycle_BATCH-71_queue_IN_PROGRESS_stream_IN_PROGRESS
- test=pytest_parallel_workstream_queue_sync_and_live_reconcile_state

tests_run:
- PYTHONPATH=platform/automation python3 -m pytest -q platform/automation/tests/test_parallel_workstream_queue_sync.py

runtime_check:
- python3 platform/automation/runtime/planner/planner_runtime_actions.py reconcile-state --board logs-codex-runs/orchestrator-state/parallel-workstreams.json --queue logs-codex-runs/orchestrator-state/priority-queue.json
