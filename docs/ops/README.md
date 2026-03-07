---
status: canonical
last_verified: 2026-03-07
canonical_replaces:
  - /home/venom/analyse-financiere/docs/operations/README.md
---

# Ops Documentation Map

Use this index before reading operational documentation.

## Start here
- Current architecture entrypoints: [CURRENT_ARCHITECTURE_ENTRYPOINTS.md](/home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md)
- Planner target architecture: [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- Runtime/monitor behavior: [MONITOR_ARCHITECTURE_SPEC.md](/home/venom/analyse-financiere/docs/ops/MONITOR_ARCHITECTURE_SPEC.md)
- Reliability and gates: [ORCHESTRATION_RELIABILITY_SPEC.md](/home/venom/analyse-financiere/docs/ops/ORCHESTRATION_RELIABILITY_SPEC.md)
- Cron/runtime profiles: [CRON_PROFILES_SPEC.md](/home/venom/analyse-financiere/docs/ops/CRON_PROFILES_SPEC.md)
- Development cutover gate: [DEV_ACTIVATION_PREFLIGHT.md](/home/venom/analyse-financiere/docs/ops/DEV_ACTIVATION_PREFLIGHT.md)
- Product/data proof path: [FORECAST_PIPELINE_PROOF_RUNBOOK.md](/home/venom/analyse-financiere/docs/ops/FORECAST_PIPELINE_PROOF_RUNBOOK.md)

## Canonical docs
- [CURRENT_ARCHITECTURE_ENTRYPOINTS.md](/home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md)
- [PLANNER_ORCHESTRATOR_TARGET_SPEC.md](/home/venom/analyse-financiere/docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md)
- [MONITOR_ARCHITECTURE_SPEC.md](/home/venom/analyse-financiere/docs/ops/MONITOR_ARCHITECTURE_SPEC.md)
- [ORCHESTRATION_RELIABILITY_SPEC.md](/home/venom/analyse-financiere/docs/ops/ORCHESTRATION_RELIABILITY_SPEC.md)
- [CRON_PROFILES_SPEC.md](/home/venom/analyse-financiere/docs/ops/CRON_PROFILES_SPEC.md)
- [DEV_ACTIVATION_PREFLIGHT.md](/home/venom/analyse-financiere/docs/ops/DEV_ACTIVATION_PREFLIGHT.md)
- [FORECAST_PIPELINE_PROOF_RUNBOOK.md](/home/venom/analyse-financiere/docs/ops/FORECAST_PIPELINE_PROOF_RUNBOOK.md)

## Reference docs
- [AGENT_WORKSPACE_INDEX.md](/home/venom/analyse-financiere/docs/ops/AGENT_WORKSPACE_INDEX.md)
- [SYMLINKS_CATALOG.md](/home/venom/analyse-financiere/docs/ops/SYMLINKS_CATALOG.md)
- [FC_DOCTOR_SPEC.md](/home/venom/analyse-financiere/docs/ops/FC_DOCTOR_SPEC.md)
- [DOCTOR_JSON_SPEC.md](/home/venom/analyse-financiere/docs/ops/DOCTOR_JSON_SPEC.md)
- [API_ENDPOINTS.md](/home/venom/analyse-financiere/docs/ops/API_ENDPOINTS.md)
- Local git hygiene helper for runtime-generated files: `scripts/runtime_git_hygiene.sh`

## Historical / compatibility docs
These can still be useful, but they must not be treated as current architectural truth.

- `PO_SCRUM_MASTER_*`
- `SCRUM_MASTER_WORKLOG.md`
- `TEAM_CHAT.md`
- `ADMIN_LOG.md`
- `NOUVEAUX_AGENTS_ONBOARDING.md`
- `REMPISE_ORDRE_POST_MIGRATION.md`
- `DEV_AGENT_*` docs unless explicitly reconciled with planner-owned capability mode
- dated files under `docs/ops/2026-03/`

## Rule for agents
If ops documents conflict:
1. `CURRENT_ARCHITECTURE_ENTRYPOINTS.md` wins for discovery.
2. `PLANNER_ORCHESTRATOR_TARGET_SPEC.md` wins for architecture.
3. `MONITOR_ARCHITECTURE_SPEC.md` and `ORCHESTRATION_RELIABILITY_SPEC.md` win for runtime behavior.
4. Historical and compatibility docs are background only.
