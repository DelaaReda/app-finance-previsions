---
name: runtime-triage
description: Triage planner/OpenClaw/monitor runtime issues quickly with host checks, doctor/status, bridge probes, and the minimum logs needed to isolate the failure domain.
---

# Runtime Triage

Use this skill when the issue could be in:
- planner dispatch
- OpenClaw gateway
- monitor/doctor disagreement
- runtime state / paused vs degraded semantics

## Workflow

1. Confirm VM runtime:
   - `bash scripts/runtime_host_check.sh`
2. Check operator truth:
   - `bash scripts/fc_doctor.sh --json`
   - `curl -s http://127.0.0.1:7779/api/status`
3. Probe OpenClaw directly:
   - `openclaw agent --agent planner --json --thinking low --timeout 60 --message 'Reply exactly with OK'`
4. If planner capability dispatch is broken, inspect:
   - `platform/automation/planner_subagent_manager.py`
   - `platform/automation/worker_manager.py`
   - latest planner subagent registry/events
5. Read only the smallest relevant logs:
   - gateway log
   - monitor guard log
   - planner runner log

## Required output

Return:
- failing layer: planner | bridge | gateway | monitor | doctor | runtime state
- root cause hypothesis
- proof from one command/log line
- next repair action

## Guardrails

- Do not conflate `paused` with `degraded`.
- Do not assume a lane should be alive if planner-only mode is active.
