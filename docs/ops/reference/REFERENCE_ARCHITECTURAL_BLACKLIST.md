# Architectural Blacklist

Status: reference
Updated: 2026-03-13

This document lists what repository agents must not reintroduce in custom code.

Canonical references:
- [CANONICAL_RUNTIME_MODE.md](/home/venom/analyse-financiere/docs/ops/CANONICAL_RUNTIME_MODE.md)
- [APP_VS_AGENT_PROVIDER_BOUNDARY.md](/home/venom/analyse-financiere/docs/ops/APP_VS_AGENT_PROVIDER_BOUNDARY.md)
- [COMMIT_ONLY_WORKFLOW_POLICY.md](/home/venom/analyse-financiere/docs/ops/COMMIT_ONLY_WORKFLOW_POLICY.md)

## Absolute bans

- no second scheduler
- no second runtime source of truth
- no new canonical JSON or JSONL state file when SQLite graph state can carry the state
- no new operator-health wrapper if `OpenClaw doctor/status/health` already covers the need
- no new persistent `worker_*` fleet by default
- no provider fallback logic outside `ModelInvocationPort` and `CodexCliAdapter`
- no text contract as canonical mutation truth
- no queue, workboard, or logs as primary truth
- no custom checkpoint or replay framework
- no hidden second control-plane through `agents_sdk`, `codex multi_agent`, or parallel runtime managers
- no new active doc outside the canonical active set

## Repo-specific bans

- do not move orchestration authority back into `parallel_workstream.py`
- do not grow `planner_subagent_manager.py` into a second orchestrator
- do not make `openclaw_control_plane.py` carry business truth
- do not revive `platform/agents_sdk` as a primary direction
- do not route app providers through the agent runtime plane
- do not route agent providers through the app plane

## Canonical substitutions

Use these instead of custom plumbing:

- durable orchestration: `LangGraph`
- runtime truth: `SQLite`
- contract validation: `Pydantic`
- operator plane: `OpenClaw`
- VM supervision: `systemd`
- technical telemetry: `OpenTelemetry`
- LLM trace UI if needed: `Phoenix`

## Enforcement

The executable guard for this blacklist is:

- `platform/policies/architectural_policy_guard.py`

The quality gate integrates it through:

- `platform/automation/dev_quality_gate.sh`
