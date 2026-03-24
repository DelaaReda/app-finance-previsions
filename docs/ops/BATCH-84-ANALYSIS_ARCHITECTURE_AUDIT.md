## BATCH-84 Analysis Architecture Audit

- architecture_plan_ref: docs/product/PRODUCT_VISION.md
- stream_id: BATCH-84
- planner_task: BATCH-84-ANALYSIS

### Target

Build the personal finance copilot by keeping delivery work split across canonical surfaces:
- `apps/api/src/domains/*` for business logic and contracts
- `apps/api/runtime/` for orchestration and runtime bridges
- `apps/web/src/` for user-facing integration without visual refactor

### Dependency Policy

- No work under `copilot-app/*`
- No nested legacy paths such as `backend/src/backend/src/*`
- No legacy imports rooted at `src.*`
- Planner-owned orchestration must dispatch delivery through planner subagents only

### Architecture Audit

- Reuse path for finance capabilities stays in `apps/api/src/domains/*`
- Runtime coordination stays in `apps/api/runtime/`
- Web integration stays in `apps/web/src` with existing theme preserved
- Waiting downstream work may depend on planner completion, but that is not a blocker for closing this analysis task

### Acceptance Gate

- Architecture plan linked to product vision
- Canonical implementation tracks declared for API, runtime, and web
- Anti-regression guards aligned with current repository paths
- Planner can now move from analysis to subagent dispatch without new backlog interpretation
