---
status: active
last_verified: 2026-03-13
---

# Planner orchestrator target spec

## Canonical role of planner
- `planner` is the only scheduler.
- `planner` consumes runtime state imported from Plane.
- `planner` decides dispatch, collect, merge, retry, and recovery from SQLite or event state.

## Current implementation reality
- Planner graph runtime and durable execution paths already exist.
- `planner_subagent_manager.py` still carries too much bridge logic and must be flattened into a capability executor.
- `parallel_workstream.py` still carries too much mutation or planning weight and must be reduced.

## Canonical flow
1. Backlog is created and prioritized in Plane OSS.
2. Plane webhook or reconciliation sync imports module and work item changes into runtime.
3. Runtime persists canonical execution state in SQLite and event state.
4. `planner` schedules executable work from runtime state.
5. Compatibility projections refresh from runtime state.

## Code boundary rules
- Provider fallback, backend routing, and quota policy live in `model_plane.py` and `codex_cli_adapter.py`.
- `planner_subagent_manager.py` must not own generic provider policy or global orchestration policy.
- `parallel_workstream.py` is a projection or controlled mutation helper only.
- OpenClaw persistent agents are reserved for operator-plane duties, not default execution of short-lived capabilities that fit a bounded `codex exec`.

## Execution defaults
- `codex exec` is primary.
- `qwen cli` is fallback for agents only through `ModelInvocationPort`.
- `g4f` is excluded from agent execution.
- `platform/agents_sdk` is archived and non-canonical.

## Bridge removal priorities
- make planner graph the uncontested write-primary path
- stop using legacy registries as coordination canon
- keep compatibility buses and registries as transitional diagnostics only
- expose `worker_orphan_count` and prefer bounded invocations over new persistent workers
