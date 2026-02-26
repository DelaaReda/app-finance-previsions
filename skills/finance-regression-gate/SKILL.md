---
name: finance-regression-gate
description: Run a compact backend/frontend regression gate for analyse-financiere with reproducible endpoint checks and machine-readable results. Use after each implementation cycle.
---

# Finance Regression Gate

Execute a fast, repeatable quality gate before reporting progress.

## Trigger

Use this skill when the user asks to:
- validate backend/frontend after changes
- run a smoke/regression check
- confirm delivery readiness with evidence

## Workflow

1. Run `scripts/run_gate.sh`
2. Collect endpoint statuses and judge quality payload
3. Save JSON result to `finance-app/openclaw-gates/`
4. Report PASS/FAIL with failing checks only

## Minimum checks

- `GET /api/health`
- `GET /api/stocks/prices?ticker=AAPL`
- `GET /api/news/feed`
- `GET /api/forecasts`
- `GET /api/judge/quality?horizon_days=5&min_samples=20`
- Frontend root `/`

## Guardrails

- Do not claim PASS if any critical endpoint fails.
- Include exact failed endpoint and HTTP code.
