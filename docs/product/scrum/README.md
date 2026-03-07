---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/product/planning/README.md
  - /home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md
---

# Scrum Operating Model (analyse-financiere)

Historical note:
- This scrum subtree contains older operating snapshots and backlog views.
- It is not the canonical product-planning source anymore.
- Use [docs/product/planning/README.md](/home/venom/analyse-financiere/docs/product/planning/README.md) and [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md) for current planning truth.

## Cadence
- Sprint length: **1 week** (Mon → Sun)
- Daily async standup: generated from orchestrator outputs
- Sprint Review: end of sprint
- Sprint Retrospective: end of sprint

## Roles
- Product Owner: prioritize backlog and accept/reject stories
- Scrum Master: enforce process and remove blockers
- Dev Team: planner, architect, dev, tester, qa, security, release, codex reviewer

## Definition of Ready (DoR)
A story can enter sprint only if it has:
1. Objective
2. Scope IN / Scope OUT
3. Acceptance criteria (testable)
4. Dependencies
5. Estimated effort (S/M/L)
6. Référence technique claire (si API/endpoint: `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`)

## Definition of Done (DoD)
A story is DONE only if:
1. DELTA/EVIDENCE/RISKS/NEXT present
2. VERDICT is PASS
3. BLOCKER_ID is NONE
4. Independent Codex review completed
5. Regression gate passed

## Board Columns
- BACKLOG
- READY
- IN_SPRINT
- IN_REVIEW
- BLOCKED
- DONE

## Sprint Artifacts
- `docs/scrum/sprint-current.md`
- `docs/scrum/product-backlog.md`
- `docs/scrum/retrospectives/YYYY-MM-DD.md`
