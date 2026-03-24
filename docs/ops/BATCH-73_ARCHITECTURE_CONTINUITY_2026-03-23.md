# BATCH-73 Architecture Continuity

batch_id: BATCH-73
date: 2026-03-23
owner_role: planner

architecture_plan_ref:
- apps/api/src/domains/*
- apps/api/runtime/
- apps/web/src

architecture_audit:
- Preserve existing frontend theme and structure; limit web changes to strict micro-adjustments.
- Enforce planner-owned orchestration through `platform/automation/planner_subagent_manager.py`.
- Keep same-stream dependencies grouped before sanitize/sync priority.
- Reject legacy paths and imports: `copilot-app/*`, `backend/src/backend/src/*`, `src.*`.

implementation_tracks:
- API/domain track: daily brief, question routing, open-navigation contracts under `apps/api/src/domains/*`.
- Runtime/admin track: reconcile queue and planner-owned dispatch under `apps/api/runtime/`.
- Web integration track: consume the brief/copilot flows in `apps/web/src` without visual refactor.

integration_reuse:
- Reuse current domain modules under `apps/api/src/domains/*`.
- Reuse runtime lane publication files under `logs-codex-runs/orchestrator-state/`.
- Reuse existing web shell in `apps/web/src` and avoid token/theme changes.

acceptance_gate:
- `BATCH-73-ANALYSIS` closes only with an explicit architecture reference and audit.
- `BATCH-73-DEV-03` must be re-dispatched through planner-owned subagents with concrete verification.
- `BATCH-73-ADMIN-01` is claimed after the dev delivery path is healthy.
- `BATCH-73-GOV_REVIEW` stays downstream of admin completion.
