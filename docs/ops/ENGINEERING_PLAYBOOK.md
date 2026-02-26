# ENGINEERING PLAYBOOK v1 (analyse-financiere)

## Objective
Ship fast **without** shipping garbage.

## Reference Example (API)
- Endpoint/API reference guide:
  - `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`
- Usage rule:
  - Any endpoint change should align with this guide (contract, cache, fallback, tests).

## Mandatory 4-Gate Pipeline
No batch can be marked DONE unless all gates pass.

### Gate 1 — Command Safety Precheck
- Every shell command must pass `scripts/command_safety_gate.py` via `scripts/exec_safe.sh`.
- Decisions:
  - `ALLOW` → run
  - `CONFIRM` → run with risk logged (policy: no wait)
  - `BLOCK` → stop

### Gate 2 — Implementation + Targeted Tests
Per task, require:
- clear scope (IN/OUT)
- minimal code change
- targeted tests run
- evidence captured

### Gate 3 — Independent Codex Review
- Run independent reviewer with Codex (separate from the delivery role that authored the change).
- Required output: `GO` or `BLOCKED` + minimal fix list.
- If `BLOCKED`, task cannot move forward.

### Gate 4 — Regression Gate
- Run finance regression gate before release verdict.
- Output must contain `PASS` or `BLOCKED`.
  - Recommended wrapper: `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-<id>-<timestamp>.md`

---

## Agent Roles (minimum set)
- Planner
- Architect
- Dev
- Tester
- QA
- Security Analyst
- Release Manager
- Codex Reviewer (independent)

Rule: More agents without governance = chaos. Keep strict role boundaries.

---

## Mandatory Task Output Template
Every task/batch response must include:
- `DELTA`
- `EVIDENCE`
- `RISKS`
- `NEXT`
- `VERDICT: PASS|BLOCKED`
- `BLOCKER_ID: <id|NONE>`
- `NEXT_ACTION_UNIQUE`

Evidence schema reference (recommended):
- `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`

---

## Batching Policy
- **Batch-01**: small, critical, contract stabilization.
- **Batch-02+**: only opens when previous batch has QA-signed `VERDICT: PASS` artifact.
- No parallel work on tightly coupled files/contracts.

---

## KPI Dashboard (process efficiency)
Track weekly:
1. Lead time per task (start → PASS)
2. First-pass success rate (%)
3. BLOCKED recurrence by cause
4. No-op edit rate (%)
5. Reopen rate after "DONE" (%)

---

## Orchestration Commands (codex-only, recommended)
```bash
# 1) Preflight (queue + health + batch prerequisites)
bash scripts/preflight_dispatch.sh

# 2) Controlled chain (planner -> dev -> tester -> qa) for a given batch id
# Example:
# bash scripts/validate_roles_sequential.sh --roles planner,dev,tester,qa --strict-ready-chain --chain-target BATCH-02

# 3) Final artifact gate (verifies required sections + review evidence)
# Example:
# bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-02-<timestamp>.md
```

Artifact path required:
- `finance-app/openclaw-gates/batch-<id>-<timestamp>.md`
