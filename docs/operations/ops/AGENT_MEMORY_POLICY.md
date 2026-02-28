# Agent Memory Policy (durable context)

## Goal

Make OpenClaw cron agents reliably persistent by writing their operational context to **files** that are re-ingested every tick.

## What is persisted

### Roles (via `scripts/cron_tmux_role_runner.sh`)
- Append one compact line to: `memory/agents/<role>.md`
- Line is derived from the 8-line contract:
  - status / verdict / delta / blocker_id
  - stream_id / task_id / next_action_unique
  - exec_report / issues / suggestions
  - directive_id / directive_ack (if directives_tail present)

### Admins
- `memory/agents/adminapp-codex.md`
- `memory/agents/admin-agents.md`
- `memory/agents/clawsentinel.md` (handled as role via cron runner)

Les scripts d'admin (`adminapp_codex_cron_tick.sh` et `admin_agents_tmux_tick.sh`) utilisent désormais `scripts/role_memory_append.py` pour la persistance, donc ils suivent le même format compact et la même stratégie de verrouillage/compactage que les rôles.

## Concurrency

- Writes are guarded with `flock` on:
  - roles: `~/.openclaw/cron/role-state/<role>.memory.lock`
  - admin scripts: `~/.openclaw/cron/admin-state/<admin>.memory.lock`

## Auto-compaction

To prevent drift and huge context, memory files are auto-compacted after append:
- keep first ~40 lines (header)
- keep last ~760 lines

## Rule

Persistent memory is **file-based**. Models do not retain state across runs unless we write it.
