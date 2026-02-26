---
name: finance-po-autopilot
description: Operate the analyse-financiere qwen_orchestrator in controlled autonomous loops with evidence logs and acceptance gates. Use when asked to run multi-hour autonomous delivery on the finance app.
---

# Finance PO Autopilot

Run long autonomous delivery cycles for the finance project while keeping evidence and control.

## Trigger

Use this skill when the user asks for:
- autonomous work for hours
- multi-agent delivery loops
- backlog progression with periodic reports

## Workflow

1. Validate runtime prerequisites
   - workspace: `/home/venom/shared/analyse-financiere`
   - orchestrator exists: `scripts/qwen_orchestrator.py`
   - agent binary exists (`/home/venom/.npm-global/bin/qwen` by default)

2. Start controlled loop
   - run `scripts/start_loop.sh` with explicit feature goal, cycle count, and interval
   - keep output logs in `finance-app/openclaw-autopilot/`

3. After each cycle
   - capture last run summary from `finance-app/orchestrator-runs/`
   - identify: done, blockers, next action

4. Apply gates before claiming success
   - API health reachable
   - regression gate executed
   - modified files listed explicitly

5. Report compactly
   - one compact update with evidence paths

## Guardrails

- Never run destructive git commands (`git reset --hard`, `git clean -fd`) unless explicitly requested.
- Do not send outbound messages to targets outside approved allowlist.
- Keep one clear objective per loop execution.
