---
name: browser-smoke
description: Run OpenClaw browser smoke validation for web or monitor changes with snapshot, requests, screenshot, and console/error evidence. Use after UI-affecting work or when validating operator surfaces.
---

# Browser Smoke

Use this skill when a change touches:
- monitor UI
- frontend pages
- browser-visible API behavior
- operator flows that need visual proof

## Workflow

1. Use the canonical helper first:
   - `python3 platform/automation/browser_smoke.py --url "<URL>" --label "<short-label>"`
2. Only fall back to raw `openclaw browser ...` commands if the helper is insufficient.
3. Attach the generated proof JSON and screenshot path to delivery evidence.

## Required output

Return:
- target URL
- whether page loaded correctly
- network/API anomalies
- console/runtime errors
- proof JSON path
- screenshot/snapshot reference
- PASS or BLOCKED

## Reference

For the exact command sequence and troubleshooting:
- `platform/automation/browser_smoke.py`
- `docs/ops/OPENCLAW_BROWSER_QA.md`
- `docs/operations/ops/ENGINEERING_PLAYBOOK.md`
