# WORKSTATE — Orchestrator Improvement Loop

## Mission
Continuously improve orchestrator reliability, quality gates, and signal-to-noise by analyzing run outputs.

## Checkpoint
- last_run_at:
- status: IN_PROGRESS | DONE | BLOCKED
- current_focus:
- next_action:

## Required inputs each run
- finance-app/orchestrator-runs/*/transcript.md
- finance-app/orchestrator-runs/*/events.jsonl
- finance-app/orchestrator-runs/*/agent_activity.json
- openclaw cron runs for planner jobs

## Output artifacts
- docs/orchestrator-ops/findings.md
- docs/orchestrator-ops/improvements.md
- docs/orchestrator-ops/experiments.md

## Rules
1. Incremental only; never reset docs from scratch.
2. If no new signal, write NO_DELTA and do not commit.
3. Every recommendation must include: impact, effort, risk, rollback.
4. Prefer small reversible changes in scripts/ with evidence.
