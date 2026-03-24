# Commit-Only Workflow Policy

Status: active
Updated: 2026-03-13

This repository uses a commit-only workflow.

## Canonical rule

- Changes land as direct commits.
- Pull requests are not part of the canonical delivery path.
- Review discipline happens before commit, through architectural arbitration and scope control.
- A commit must reduce ambiguity or reduce non-canonical plumbing. It must not expand both at once.

## Commit gate

Before creating or keeping a commit, the author must answer:

1. Does this commit add canonical business logic?
2. Does this commit add a thin adapter to a canonical tool?
3. Or does this commit add generic plumbing that the repo should not own?

If the answer is `3`, do not keep the change in its current form.

## Allowed commit classes

- `canon`: business logic, planner invariants, proof schemas, runtime truth invariants
- `adapt`: adapter to `LangGraph`, `SQLite`, `OpenClaw`, `systemd`, `OpenTelemetry`
- `compat`: required legacy projection only
- `archive`: deprecation, superseded docs, retirement of non-canonical paths

## Commit constraints

- One commit, one purpose.
- No commit may introduce a second scheduler.
- No commit may introduce a second source of truth if SQLite graph state can carry the state.
- No commit may add a new operator-health wrapper if `OpenClaw doctor/status/health` already covers the need.
- No commit may make text the canonical mutation format.
- No commit may expand persistent `worker_*` fleets without an explicit canonical runtime decision.
- No commit may cross the provider boundary between app plane and agent runtime plane.

## Architectural arbitration

The repository keeps only:

- planner decision logic
- batch, task, and handoff invariants
- delivery proof contracts
- business projections such as queue and workboard
- monitor business views

The repository does not reimplement:

- generic checkpointing or replay
- generic process supervision
- generic cron orchestration already covered by `OpenClaw` or `systemd`
- generic technical tracing already covered by `OpenTelemetry`
- generic operator health checks already covered by `OpenClaw`

## Tool-first policy

Use the canonical tool instead of custom plumbing:

- durable orchestration: `LangGraph`
- runtime truth: `SQLite`
- contract validation: `Pydantic`
- operator plane: `OpenClaw`
- VM supervision: `systemd`
- technical telemetry: `OpenTelemetry`

If a change adds a new script in one of these domains, the author must justify why the canonical tool is insufficient.

## Commit message discipline

Preferred prefixes:

- `canon:`
- `adapt:`
- `compat:`
- `archive:`

Examples:

- `canon: tighten planner delivery proof invariant`
- `adapt: route doctor provider health through openclaw status`
- `compat: keep queue projection aligned with runtime event store`
- `archive: mark openai agents integration plan as superseded`

## Refusal cases

Reject or rewrite a change if it introduces:

- a new scheduler lane
- a new JSON file as canonical runtime state
- a new hidden control-plane
- a new text parser as mutation truth
- a new provider-routing policy outside `ModelInvocationPort`
- a new persistent worker pattern where bounded invocation is enough

## Relationship to canonical runtime

This policy is subordinate to:

- [CANONICAL_RUNTIME_MODE.md](/home/venom/analyse-financiere/docs/ops/CANONICAL_RUNTIME_MODE.md)
- [APP_VS_AGENT_PROVIDER_BOUNDARY.md](/home/venom/analyse-financiere/docs/ops/APP_VS_AGENT_PROVIDER_BOUNDARY.md)
- [ACTIVE_DOCS_INDEX.md](/home/venom/analyse-financiere/docs/ops/ACTIVE_DOCS_INDEX.md)
