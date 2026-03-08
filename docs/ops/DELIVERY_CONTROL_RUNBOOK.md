---
status: canonical
last_verified: 2026-03-08
canonical_replaces:
  - delivery triage notes embedded in monitor/debug docs
---

# Delivery Control Runbook

Use this runbook when `delivery_integrity` or `delivery_control` goes degraded.

## Read these fields first
- `/api/status`
  - `delivery_integrity`
  - `delivery_control`
  - `planner_dispatch`
- `/api/doctor?refresh=1`
  - `checks.delivery_future_integrity`
  - `checks.browser_proof_pipeline`
  - `checks.suspicious_completions`
  - `checks.qa_review_pipeline`

## How to interpret the states
- `delivery_integrity.status`
  - broad truth across recent completions
  - includes historical debt inside the active 24h window
- `delivery_control.future_status`
  - go/no-go signal for current rollout quality
  - this is the signal to use before declaring the current system healthy
- `delivery_control.needs_proof_backfill`
  - tasks that need proof backfill
  - may include historical debt and future tasks
- `delivery_control.suspicious_completions`
  - completions lacking enough proof
  - these need review, backfill, or reopen

## Triage order
1. Check `suspicious_completions`
2. Check `browser_proof_pipeline`
3. Check `qa_review_pipeline`
4. Only then look at historical proof debt

## Operator actions
### Suspicious completion
- Inspect the task proof manifest and task metadata
- If proof exists but was not linked, backfill the proof reference
- If proof does not exist, reopen or downgrade the task instead of accepting the completion

### Browser proof missing
- Only required for UI/monitor/web-facing deliveries
- Generate browser proof with the canonical browser smoke path
- Attach the resulting proof reference to the task/proof manifest

### QA review pending
- If the task is future-scope and already completed, dispatch QA review
- If QA already ran but the task is not annotated, backfill `qa_status` and proof fields

## What is not a hard failure
- historical browser-proof debt by itself
- proof debt on tasks completed before the rollout boundary

## What is a hard failure
- future deliveries missing required browser proof
- recent suspicious completions without backfill or reopen
- future dev deliveries with no QA review status
