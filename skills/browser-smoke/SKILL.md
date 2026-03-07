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

1. Verify browser tooling:
   - `openclaw browser status --json`
2. Open target URL:
   - `openclaw browser open "<URL>"`
3. Wait for DOM:
   - `openclaw browser wait --load domcontentloaded`
4. Capture proof:
   - `openclaw browser snapshot --labels --limit 200`
   - `openclaw browser requests --json`
   - `openclaw browser console --level error`
   - `openclaw browser errors`
   - `openclaw browser screenshot --full-page`
5. Close the browser tab:
   - `openclaw browser close`

## Required output

Return:
- target URL
- whether page loaded correctly
- network/API anomalies
- console/runtime errors
- screenshot/snapshot reference
- PASS or BLOCKED

## Reference

For the exact command sequence and troubleshooting:
- `docs/ops/OPENCLAW_BROWSER_QA.md`
- `docs/operations/ops/ENGINEERING_PLAYBOOK.md`
