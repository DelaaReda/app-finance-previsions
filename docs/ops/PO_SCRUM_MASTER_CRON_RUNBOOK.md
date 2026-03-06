# PO Scrum Master Cron Runbook

## Status
Legacy compatibility runbook only.

This document is not the target architecture.
Current target runtime is:
- planner-only scheduling
- `scrum_master` preserved as a planner-owned capability/responsibility domain

Canonical source of truth:
- `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`

## Why This File Still Exists
Some compatibility scripts, legacy report paths, and monitor fields still reference `po_scrum_master`.
This runbook remains only to explain those compatibility surfaces during transition.

## Current Interpretation
- `po_scrum_master` is not an independently authoritative target lane
- any remaining wrapper or report path is compatibility/historical
- target behavior for scrum responsibility now lives under planner-owned orchestration

## If You Need Legacy Recovery
Use only for controlled compatibility or investigation.

Example legacy invocation:
```bash
bash scripts/po_scrum_master_run_now.sh
```

This does not redefine the target architecture.

## Target Equivalent
Target scrum behavior should be implemented through:
- planner-owned scrum capability
- starvation/stall detection
- unblock/escalation recommendations returned to planner
