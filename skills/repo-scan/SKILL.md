---
name: repo-scan
description: Perform a fast, bounded repository scan for planner or architecture tasks. Use when you need targeted codebase truth, likely entrypoints, and a minimal implementation shortlist without editing files.
---

# Repo Scan

Use this skill when the task is:
- architecture triage
- planner framing
- dependency tracing
- identifying the minimum files to change

## Workflow

1. Start with `rg`, not broad file dumps.
2. Identify the 1-3 canonical entrypoints only.
3. Read only the minimum surrounding code needed to confirm:
   - source of truth
   - current data flow
   - likely edit surface
4. Return a concise shortlist:
   - relevant files
   - key symbols/functions
   - why they matter
   - likely risks

## Guardrails

- Do not read the whole repo.
- Do not infer architecture from legacy docs if canonical code/docs disagree.
- Prefer canonical docs:
  - `docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md`
  - `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`

## Required output

Return:
- current truth
- minimal file shortlist
- open unknowns
- recommended next edit order
