# OpenClaw No-Pivot Blueprint (Qwen-First)

## Goal

Stabilize orchestration so delivery is fast but predictable, without re-architecting every week.

## Fixed Architecture

1. `Supervisor` (single control brain, routing and decisions only).
2. `Dev` (implementation).
3. `Verifier` (quality gate, architecture/security sanity checks).

Default workflow per ticket:

`plan -> build -> verify -> done/block`

Rules:

- one active delivery track at a time unless explicitly opened by supervisor
- no always-on swarm
- no legacy non-qwen orchestration path
- evidence required before status = done

## Runtime Guardrails (Baseline)

These values are intentionally conservative:

- `agents.defaults.maxConcurrent = 2`
- `agents.defaults.subagents.maxConcurrent = 3`
- `agents.defaults.heartbeat.every = "30m"`
- `cron.sessionRetention = "8h"`
- `cron.runLog.maxBytes = 500000`
- `cron.runLog.keepLines = 500`

Skills disabled to avoid orchestration drift:

- `finance-po-autopilot`
- `finance-po-orchestrator`
- `task-orchestrator`
- `autonomous-skill-orchestrator`
- `joko-orchestrator`
- `cc-godmode`

## Apply Baseline

Use:

```bash
bash scripts/no_pivot_apply_baseline.sh --apply
```

Dry run:

```bash
bash scripts/no_pivot_apply_baseline.sh --dry-run
```

What this does:

- pauses all cron jobs
- optionally stops tmux sessions
- writes OpenClaw config guardrails
- disables high-drift legacy orchestration skills

## Controlled Execution

Keep default mode paused:

```bash
bash scripts/set_orchestration_mode.sh --mode paused --stop-sessions
```

For one-by-one checks, run a single job manually (without enabling all crons).
Important: job IDs are not stable; always refresh from the scheduler.

```bash
openclaw cron list --all
openclaw cron run <job-id> --expect-final --timeout 480000
```

Recommended probe order (core chain):
- planner -> dev -> tester -> qa

Reference spec (source of truth):
- `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`

## Success Criteria

Baseline is considered stable when:

- no surprise tmux restarts
- no uncontrolled parallel role execution
- each iteration emits verifier evidence before closure
- cron/session logs remain bounded without manual cleanup
