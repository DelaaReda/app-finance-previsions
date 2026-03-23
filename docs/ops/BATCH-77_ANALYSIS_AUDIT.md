# BATCH-77 Analysis Audit

Date: 2026-03-23
Scope: personal finance copilot with a daily brief and direct access to analysis views.

Canonical refs:
- docs/ops/ACTIVE_DOCS_INDEX.md
- docs/ops/PLANE_BACKLOG_INTEGRATION_SPEC.md
- docs/product/PRODUCT_VISION.md

Architecture plan ref:
- apps/api/src/domains for finance brief and analysis domain contracts
- apps/api/runtime for orchestration, freshness, and planner-owned runtime hooks
- apps/web/src for opening analysis flows without changing the current visual theme

Implementation tracks:
- API/domain contract for brief and analysis retrieval
- Runtime orchestration for freshness and planner-owned delivery flow
- Web integration to open analysis content inside the existing shell

Integration reuse:
- Reuse current `apps/api/src/domains/*` modules and runtime adapters
- Preserve `apps/web/src` structure and design tokens

Acceptance gate:
- Daily brief is backed by an API/domain contract
- Analysis can be opened or queried from the existing web shell
- Runtime orchestration stays planner-owned and compatible with the current queue/workboard
- No forbidden paths or legacy imports are introduced

Architecture audit:
- Forbidden paths remain excluded: `copilot-app/*`, `backend/src/backend/src/*`, `src.*` legacy imports
- Waiting downstream tasks are normal dependencies of this analysis output, not blockers
- The implementation should land in `apps/api` and `apps/web` with runtime support in `apps/api/runtime`
