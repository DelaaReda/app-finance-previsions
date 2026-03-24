---
status: canonical
last_verified: 2026-03-13
---

# Documentation Drift Report - 2026-03-13

Purpose: record what was normalized and what still creates noise.

## Resolved in this cleanup

- Canonical discovery reduced to:
  - `docs/ops/README.md`
  - `docs/ops/ACTIVE_DOCS_INDEX.md`
  - `docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md`
  - `docs/ops/AGENT_WORKSPACE_INDEX.md`
- Path semantics clarified:
  - `docs/ops/*` = canonical citation path for current ops docs
  - `docs/operations/*` = historical tree or physical storage behind some symlinks
- Root and hub docs reframed:
  - `README.md`
  - `docs/WORKSPACE_MAP.md`
  - `docs/architecture/README.md`
- Ambiguous/legacy docs now explicitly marked:
  - `docs/REFERENCE_DEV_TOOLS_GUIDE.md`
  - `docs/ARCHIVE_ORCHESTRATION_LEAN.md`
  - `docs/ops/archive/ARCHIVE_ORCHESTRATION_AGENTS_READY.md`
  - `docs/ops/archive/OPENAI_AGENTS_PYTHON_INTEGRATION_PLAN_2026-03-13.md`
  - `docs/ops/archive/3DAY_MEMORY_DEPLOYMENT_STATUS.md`
  - `docs/ops/archive/ARCHIVE_RECOVERY_VERIFICATION_2026-03-03.md`
- Historical ops docs physically moved out of `docs/ops/` root into `docs/ops/archive/`
- Cutover / lane-transition docs removed from active root:
  - `docs/ops/archive/PLANNER_MONO_LANE_CUTOVER_RUNBOOK.md`
  - `docs/ops/archive/ARCHIVE_READY_DEV_STATE_MACHINE.md`
  - `docs/ops/archive/SCRUM_MASTER_OPERATIONAL_SPEC.md`
  - `docs/ops/archive/TMUX_HANDOFF_*`
- Non-core ops runbooks/specs moved under `docs/ops/reference/`
- Root historical guide moved to `docs/ops/archive/ARCHIVE_ORCHESTRATION_LEAN.md`
- Agent message bus JSONL moved from docs namespace to runtime state: `logs-codex-runs/orchestrator-state/agent-message-bus.jsonl`
- Product planning root reduced to current docs; historical and supporting material moved under `docs/product/planning/archive/` and `docs/product/planning/reference/`

## Remaining noise pockets

These are not blocking, but they still look more active than they should:

| Priority | Path | Why it still adds noise |
|---------|------|--------------------------|
| low | `docs/ops/reference/*` | large but intentionally separated from the canonical root |
| low | `logs-codex-runs/orchestrator-state/agent-message-bus.jsonl` | runtime coordination artifact still lives in the repo, but no longer in docs |
| low | dated reports under `docs/operations/*` | still numerous but already outside canonical entrypoints |
| low | `docs/product/planning/` current batch artifacts | intentionally visible because they belong to the active cycle |

## Recommended policy going forward

1. Any current doc in `docs/ops/*` should carry one of:
   - `canonical`
   - `reference`
   - `compatibility_note`
   - `historical`
   - `archived`
2. Any dated doc should default to `historical` unless explicitly promoted by an active index.
3. No new root-level doc under `docs/` should be created without being linked from a hub:
   - `docs/ops/README.md`
   - `docs/architecture/README.md`
   - `docs/product/planning/README.md`
4. Runtime truth must continue to point to SQLite + graph/event state, never to docs projections.

## Success condition

An agent new to the repo should be able to find the current truth in under five reads:

1. `docs/ops/README.md`
2. `docs/ops/ACTIVE_DOCS_INDEX.md`
3. `docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md`
4. `docs/product/PRODUCT_VISION.md`
5. `docs/product/planning/README.md`
