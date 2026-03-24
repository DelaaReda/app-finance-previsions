---
status: compatibility_note
last_verified: 2026-03-13
related_to:
  - /home/venom/analyse-financiere/docs/ops/CANONICAL_RUNTIME_MODE.md
  - /home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md
---

# Agent Message Bus Specification

Compatibility note:
- target architecture is planner-only scheduling
- references to `po_scrum_master` below are legacy compatibility notes, not the target topology
- JSONL message bus is a coordination surface, not canonical runtime truth

## Changelog
- **2026-03-04**: Full rewrite in English; formalized event contract, anti-loop semantics, sticky+TTL policy, and operator quickstart.

## 1) Purpose and Scope
This document specifies the targeted message bus used to inject temporary coordination directives into role prompts.

Scope:
- Message lifecycle and events.
- Sticky-until-close policy.
- Per-role delivery dedup.
- Operator command interface.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Messages **MUST** have unique `message_id`.
- Delivery **MUST** deduplicate per `(message_id, role)`.
- Sticky messages **MUST** remain active until explicitly closed or expired.
- `deliver` **MUST NOT** accept unknown, closed, or expired messages.
- `action` **MUST NOT** accept unknown or closed messages.
- `action_status` **MUST** be one of `done|deferred|blocked`.

## 3) Interfaces and Schemas
### Bus file
- Canonical file: `/home/venom/analyse-financiere/logs-codex-runs/orchestrator-state/agent-message-bus.jsonl`

Truth note:
- this file is append-only coordination history
- SQLite graph state and orchestration events remain the canonical runtime truth

### Event types
- `message_posted`
- `message_delivered`
- `message_action`
- `message_closed`

### Common fields
- `event`
- `message_id`
- `ts_utc`
- `source`
- `targets`
- `priority`
- `sticky`
- `ttl_min`
- `expires_at_utc`
- `payload`

### Delivery event fields
- `role`
- `tick_id`

### Action event fields
- `role`
- `action_status`
- `note`
- `tick_id`

## 4) Runtime Behavior and Edge Cases
- Active set for a role excludes:
  - closed messages,
  - expired messages,
  - already delivered messages for that role.
- Retries in same role should not re-inject a message once delivered.
- Close events immediately remove a message from active role feed.

## 5) Operator Commands and Expected Outputs
Wrapper scripts:
- `/home/venom/analyse-financiere/scripts/message_to_dev.sh`
- `/home/venom/analyse-financiere/scripts/message_to_planner.sh`
- `/home/venom/analyse-financiere/scripts/message_to_admin.sh`
- `/home/venom/analyse-financiere/scripts/message_close.sh`

Core CLI:
```bash
bash platform/automation/agent_message_bus.sh post --targets dev --msg "Investigate queue mismatch" --priority high --sticky 1 --ttl-min 10080
bash platform/automation/agent_message_bus.sh active --role dev --json
bash platform/automation/agent_message_bus.sh close --id MSG_... --reason resolved
```
Expected:
- Unique message ID at post.
- Active feed includes only actionable messages for role.
- Closed message removed from active output.

## 6) Observability and Troubleshooting
Monitor fields:
- `agent_messages.open_count`
- `agent_messages.open_by_role`
- `agent_messages.latest_action_status_by_role`
- `agent_messages.last_message_id_by_role`

Runtime files:
- Bus JSONL file itself.
- Runner event logs for receipt publication.

## 7) Compatibility and Migration Notes
- Legacy alias fields (`ts`, `from`, `msg`, `status`, `reason`) are kept for compatibility.
- Canonical fields remain `*_utc`, `source`, `payload`, `action_status`.
- Sticky default and TTL defaults are environment-configurable during migration.

## 8) Acceptance Criteria
- No processing loop for same `(message_id, role)`.
- `deliver` and `action` reject invalid lifecycle states.
- Monitor reflects open/delivered/actioned/closed message counters accurately.

## Legacy advisory scheduling note (2026-03-04)

- With `FC_PO_SCRUM_MASTER_CRON_ENABLED=1`, advisory `po_scrum_master` can post/close targeted messages on schedule.
- Anti-loop behavior remains unchanged:
  - one delivery per role per `message_id` until close,
  - action receipts and close events are append-only in bus history.
