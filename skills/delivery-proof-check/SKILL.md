---
name: delivery-proof-check
description: Verify that a task has enough evidence to pass delivery gating. Use before claiming completion for code, config, runtime, or product work.
---

# Delivery Proof Check

Use this skill before any task is marked complete.

## Required evidence

For code/config/runtime/product work, check:
- `root_cause`
- `fix_applied`
- `verify`
- `artifact`
- `tests_run`
- `commit_sha`
- `files_touched`
- `architecture_check`
- `vision_alignment`

## Workflow

1. Inspect the latest task evidence/contract.
2. Confirm the task has a real commit if the work touched code/config/runtime.
3. Run the regression gate when the task affects product behavior:
   - `bash scripts/run_delivery_gate.sh <artifact>`
4. If web-visible behavior changed, require browser-backed proof.
5. Return one of:
   - `PASS`
   - `BLOCKED`

## Guardrails

- Do not accept narrative-only progress.
- Do not accept completion without verifiable proof.
- Do not downgrade quality by relaxing the gate.

## References

- `platform/automation/delivery_value_gate.py`
- `skills/finance-regression-gate/SKILL.md`
- `docs/operations/ops/ENGINEERING_PLAYBOOK.md`
