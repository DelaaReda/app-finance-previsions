# PO Scrum Master Advisory Specification

## Status
Historical compatibility document.

It documents a legacy advisory surface still visible in some runtime paths, but it is not the target operating model.

## Current Target
- no independent `po_scrum_master` target lane
- `scrum_master` remains a planner-owned capability under the planner orchestrator
- planner remains the only scheduled orchestrator lane in target mode

## Compatibility Boundary
If `po_scrum_master` appears in:
- logs
- monitor payloads
- report file paths
- wrapper scripts

interpret it as a compatibility alias or historical artifact, not as a separate architecture decision.

## Canonical Replacement
Use:
- `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`
- `docs/ops/ORCHESTRATION_RELIABILITY_SPEC.md`

for the current model.
