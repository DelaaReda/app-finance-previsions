# BATCH-71-PLAN proof

- Task: `BATCH-71-PLAN`
- Source: `admin/infra reliability slice`
- Date: `2026-03-20`

## Root cause

The canonical projections kept a stale top-level `active_cycle` anchored on `BATCH-24` even though the direct queue/workboard rows for `BATCH-24` were already `CLOSED` / `DONE`. That drift blocked planner closure because the current planner task had no delivery proof artifact and the runtime could still read a contradictory cycle header.

## Fix applied

- Hardened runtime consumers so `active_cycle.active_batch_ids` are intersected with actually open queue/workboard rows.
- Ran canonical planner `reconcile-state` to realign runtime projections.
- Verified the canonical projections now expose `active_cycle.active_batch_ids=["BATCH-71"]` and demote `BATCH-24` to `recent_completed_batch_ids`.

## Verify

`before=top_level_active_cycle_claimed_B24_while_B24_rows_were_CLOSED_DONE;after=canonical_projections_now_point_to_B71_and_runtime_snapshot_reports_runnable_task_ids_BATCH_71_PLAN;test=planner_runtime_actions_reconcile_state+planner_board_runtime_snapshot+doctor_refresh_ok`

## Architecture check

`PASS(runtime_truth_and_open_queue_workboard_rows_override_stale_projection_cycle_headers;planner_no_longer_treats_closed_batch_as_active)`

## Vision alignment

`PASS(restores_planner_focus_to_the_current_delivery_stream_B71_instead_of_a_closed_historical_batch)`
