---
status: canonical
last_verified: 2026-03-07
canonical_replaces:
  - docs/operations/README.md
---

# Current Architecture Entrypoints

Read these first. Ignore historical reports unless you are debugging a past incident.

## Canonical docs
- Product vision: [PRODUCT_VISION.md](/home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md)
- Product backlog: [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md)
- Workspace and path rules: [AGENT_WORKSPACE_INDEX.md](/home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md)
- Target runtime architecture: [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- Execution order: [PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md](/home/venom/analyse-financiere/docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md)
- Monitor/runtime behavior: [MONITOR_ARCHITECTURE_SPEC.md](/home/venom/analyse-financiere/docs/ops/MONITOR_ARCHITECTURE_SPEC.md)
- Forecast/data proof path: [FORECAST_PIPELINE_PROOF_RUNBOOK.md](/home/venom/analyse-financiere/docs/ops/FORECAST_PIPELINE_PROOF_RUNBOOK.md)

## Canonical code entrypoints
- Runner config: [runner.v1.yaml](/home/venom/analyse-financiere/platform/config/runner/runner.v1.yaml)
- Runtime state/path helper: [orchestrator_paths.py](/home/venom/analyse-financiere/platform/automation/orchestrator_paths.py)
- Planner bridge: [planner_subagent_manager.py](/home/venom/analyse-financiere/platform/automation/planner_subagent_manager.py)
- OpenClaw control plane sync: [openclaw_control_plane.py](/home/venom/analyse-financiere/platform/automation/openclaw_control_plane.py)
- Planner dispatch metrics: [planner_dispatch_metrics.py](/home/venom/analyse-financiere/platform/automation/planner_dispatch_metrics.py)
- Pre-tick reconciliation: [state_reconciler.py](/home/venom/analyse-financiere/platform/automation/state_reconciler.py)
- Delivery gate: [delivery_value_gate.py](/home/venom/analyse-financiere/platform/automation/delivery_value_gate.py)
- Browser smoke proof: [browser_smoke.py](/home/venom/analyse-financiere/platform/automation/browser_smoke.py)
- Product guard: [product_priority_guard.py](/home/venom/analyse-financiere/platform/automation/product_priority_guard.py)
- Monitor API: [server.py](/home/venom/analyse-financiere/apps/monitor/server.py)
- Doctor CLI: [fc_doctor.py](/home/venom/analyse-financiere/platform/automation/fc_doctor.py)

## Canonical reusable skills
- Browser validation: [skills/browser-smoke/SKILL.md](/home/venom/analyse-financiere/skills/browser-smoke/SKILL.md)
- Repo triage: [skills/repo-scan/SKILL.md](/home/venom/analyse-financiere/skills/repo-scan/SKILL.md)
- Runtime incident triage: [skills/runtime-triage/SKILL.md](/home/venom/analyse-financiere/skills/runtime-triage/SKILL.md)
- Delivery proof gate helper: [skills/delivery-proof-check/SKILL.md](/home/venom/analyse-financiere/skills/delivery-proof-check/SKILL.md)
- These four skills are projected into OpenClaw workspaces by:
  - [openclaw_control_plane.py](/home/venom/analyse-financiere/platform/automation/openclaw_control_plane.py)
  - [worker_manager.py](/home/venom/analyse-financiere/platform/automation/worker_manager.py)

## Agent/operator quick rules
- Explainable-first: output without sources, freshness, or reasoning is not a finished product behavior.
- Proof-first delivery: a task is not done until code/config/API/UI proof exists, not just a claimed delta.
- Use canonical paths: prefer current `apps/`, `platform/`, and `docs/ops` paths over historical aliases.
- Keep network-heavy validation explicit: unit and local checks by default, broader provider checks only when required by the task.
- Do not treat `dev`, `admin`, or `scrum_master` as autonomous cron lanes in planning docs; they are capability domains under planner authority.
- Backend-first product changes: prefer adapting backend contracts to the current frontend before changing UI structure.
- Preserve the existing frontend theme: design tokens, palette, and shell continuity are protected unless a change is explicitly justified.

## Branch decisions
- `main` is historical and not the implementation baseline.
- `origin/docs/direct-main` contributed concise vision/onboarding ideas only; its content is harvested semantically into current docs.
- `origin/cursor/define-integration-engineer-roles-39a9` contributed pipeline-proof discipline only; its legacy code paths are not canonical.
- Branches already absorbed into current architecture do not need separate reintegration work unless a canonical doc says otherwise.

## Historical docs
- Historical archive boundary: [docs/operations/README.md](/home/venom/analyse-financiere/docs/operations/README.md)
- Orchestrator evidence/runtime boundary: [docs/operations/orchestrator/README.md](/home/venom/analyse-financiere/docs/operations/orchestrator/README.md)
- `docs/orchestrator-ops/` is a compatibility alias to the same historical orchestrator tree.
