# Agent Activity Feed Specification

## Purpose
Expose a runtime-native activity layer so operators can understand agent progression without reading raw logs.

## Endpoints (additive, non-breaking)
- `GET /api/agent-activity?window=6&limit=300`
- `GET /api/tasks/active?window=6&limit=120`
- `GET /api/dependencies/map?limit=300`

## `/api/agent-activity` contract
Top-level keys:
- `enabled`
- `window_hours`
- `limit`
- `timeline[]`
- `throughput`
- `intentions`
- `quality`
- `tasks_active[]`
- `dependencies`
- `system_summary`
- `sources`

### `timeline[]` event schema
- `event_id`
- `ts`
- `role`
- `action` (`CLAIM|PROGRESS|TEST|PATCH|COMPLETE|HANDOFF|CHECK|NOOP|BLOCKED|RECOVER`)
- `batch_id`
- `task_id`
- `state_before`
- `state_after`
- `reason_code`
- `tick_id`
- `source_file`
- `source_kind`
- `raw_event`
- `artifact_refs[]`
- `evidence_refs[]`
- `summary`

### `throughput`
- `tasks_completed_last_hour`
- `artifacts_generated_last_hour`
- `delivery_rate`

### `system_summary`
- `what_changed_last_15m[]`
- `events_by_role_last_15m`
- `current_bottleneck`
- `recommended_next_action`
- `intentions`
- `decision_trace_quality`

## `/api/tasks/active` contract
- `window_hours`
- `limit`
- `items[]`
- `generated_at`

Each item includes:
- `task_id`
- `batch_id`
- `owner`
- `state`
- `started_at`
- `last_update`
- `progress_pct`
- `current_step`
- `artifact_output`
- `stalled`
- `stalled_reason`
- `title`

## `/api/dependencies/map` contract
- `nodes[]`
- `edges[]`
- `bottlenecks[]`
- `summary`
- `explanations[]`
- `generated_at`

## Status API addition
`GET /api/status` now includes:
- `activity_summary`
  - `events_last_1h`
  - `events_last_6h`
  - `tasks_progressed_last_1h`
  - `last_action_by_role`
  - `current_bottleneck`

## Notes
- Global health policy remains unchanged (`planner/dev/admin` core).
- Activity feed is optional via `FC_MONITOR_ACTIVITY_FEED_ENABLED`.
