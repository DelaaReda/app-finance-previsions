# Monitor Architecture Specification

## Purpose
Define FC Monitor behavior for the current planner-orchestrator runtime.

The monitor must reflect current runtime truth, not historical topology.

## Current Runtime Model
- execution mode is derived from runner config and environment
- target execution mode is `planner_experimental`
- in `planner_experimental`, the only scheduled core role is `planner`
- `dev`, `admin`, and `scrum_master` remain visible as capability outputs or planner-owned subagent activity, not as independent core cron lanes

## Normative Rules
- Monitor **MUST** compute health from `core_roles` derived from execution mode.
- In `planner_experimental`, `core_roles` **MUST** equal `["planner"]`.
- Monitor **MUST** expose orchestration truth, delivery truth, and product-value truth.
- Legacy advisory fields **MUST** be treated as compatibility surfaces, not architectural truth.
- API payloads **MUST NOT** regress required keys unexpectedly.

## Required Status Payload Concepts
- `execution_mode`
- `core_roles`
- `agents`
- `planner_subagents`
- `dynamic_workers`
- `queue_workboard_integrity`
- `orchestration`
- `agent_messages`
- `doctor`

Compatibility:
- `po_scrum_master` may still appear for historical or compatibility reasons
- it is not part of the target architecture contract

## Health Policy

### Target mode: `planner_experimental`
Health is based on:
- planner freshness
- planner contract validity
- queue/workboard integrity
- runtime provider health
- delivery/product-value signals where available

Planner-owned subagent failures are relevant only insofar as they affect planner progress or delivery truth.

### Compatibility modes
When running in non-target profiles, monitor may still compute health from legacy core roles.

## Runtime Behavior
- Monitor resolves execution mode first, then derives `core_roles`.
- Monitor must prefer canonical orchestrator data under `docs/operations/orchestrator`.
- Monitor should surface planner-owned delegation via `planner_subagents`.
- Monitor should emphasize value and blockages over raw agent chatter.

## Access Model
- VM-local monitor endpoint remains `http://127.0.0.1:7779/`.
- Host-facing canonical monitor endpoint is `http://192.168.64.9:7780/`.
- `7780` is a LAN proxy managed by `scripts/monitor_stack_guard.sh`.
- Public tunnels are disabled by default and are not part of normal monitor architecture.

Reference:
- [MONITOR_ACCESS_RUNBOOK.md](/home/venom/analyse-financiere/docs/ops/MONITOR_ACCESS_RUNBOOK.md)

## Product/Delivery Signals
The monitor should progressively expose:
- delivery proof sufficiency
- stale READY / stalled progress
- product-vs-orchestration work ratio
- copilot usable vs fallback
- forecast real vs placeholder
- data freshness

## Operator Commands
```bash
bash scripts/monitor_stack_guard.sh
cat logs-codex-runs/monitor-lan-url.txt
curl -s http://127.0.0.1:7779/api/status?lite=1 | jq '{health,execution_mode,core_roles,planner_subagents}'
curl -s http://192.168.64.9:7780/api/status?lite=1 | jq '{health,execution_mode,core_roles,planner_subagents}'
bash scripts/fc_doctor.sh --json | jq '.checks.sessions,.checks.providers'
```

Expected in target mode:
- `execution_mode="planner_experimental"`
- `core_roles=["planner"]`

## Acceptance Criteria
- monitor reflects planner-only scheduling correctly
- planner-owned subagent visibility is additive and non-confusing
- legacy advisory fields no longer define the runtime model
- status/doctor remain coherent with each other
