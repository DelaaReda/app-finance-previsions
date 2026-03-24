---
status: canonical
last_verified: 2026-03-13
---

# Documentation Classification Matrix

Purpose: classify `docs/*` by reading priority and prevent competing entrypoints.

## Active

Use these first for current runtime, architecture discovery, and day-to-day delivery.

| Scope | Canonical entrypoint |
|-------|----------------------|
| Ops landing | `docs/ops/README.md` |
| Active shortlist | `docs/ops/ACTIVE_DOCS_INDEX.md` |
| Runtime/architecture discovery | `docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md` |
| Runtime mode truth | `docs/ops/CANONICAL_RUNTIME_MODE.md` |
| Workspace/path truth | `docs/ops/AGENT_WORKSPACE_INDEX.md` |
| Product vision | `docs/product/PRODUCT_VISION.md` |
| Active planning | `docs/product/planning/README.md` |
| Design hub | `docs/architecture/README.md` |

## Reference

Useful, but not primary truth unless called by an active document.

| Scope | Path pattern |
|-------|--------------|
| Design/reference material | `docs/architecture/*` |
| Data quality and reports | `docs/data/*` |
| Memory/meta hubs | `docs/memory-hub/*` |
| Task navigation hubs | `docs/tasks-hub/*` |
| Ops reference tree | `docs/ops/reference/*` |
| Canonical specs linked from active docs | selected active `docs/ops/*.md` files only |

## Compatibility

Readable for transition or alias resolution, but not the first place to start.

| Scope | Path pattern |
|-------|--------------|
| Physical storage alias for ops docs | `docs/ops/ops/*` |
| Product aliases | `docs/planning/*`, `docs/scrum/*` |
| Compatibility notes under ops | `docs/ops/*` files explicitly marked `compatibility_note` |
| Human-facing orchestrator projections | `docs/operations/orchestrator/*` |

## Historical / Archive

Do not treat these as current architecture truth.

| Scope | Path pattern |
|-------|--------------|
| Historical ops tree | `docs/operations/*` |
| Archived ops docs | `docs/ops/archive/*` |
| Legacy orchestration summaries | `docs/ops/archive/ARCHIVE_ORCHESTRATION_LEAN.md` |
| Archived/superseded plans | dated or explicitly archived docs moved under `docs/ops/archive/*` |
| Archived cutover and lane-transition docs | `docs/ops/archive/PLANNER_MONO_LANE_CUTOVER_RUNBOOK.md`, `docs/ops/archive/ARCHIVE_READY_DEV_STATE_MACHINE.md`, `docs/ops/archive/SCRUM_MASTER_OPERATIONAL_SPEC.md` |
| Legacy-orchestrator tree | `docs/orchestrator-ops.legacy-20260228/*` |

## Reading order

1. `docs/ops/README.md`
2. `docs/ops/ACTIVE_DOCS_INDEX.md`
3. `docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md`
4. `docs/product/PRODUCT_VISION.md`
5. `docs/product/planning/README.md`

## Rules

- Cite `docs/ops/*` for current operational guidance.
- Cite `docs/product/*` for product and planning.
- Cite `docs/architecture/*` for design intent and reuse.
- Treat `docs/operations/*` as historical or physical storage unless an active doc says otherwise.
- If two documents disagree, the one with the stronger current classification wins.
