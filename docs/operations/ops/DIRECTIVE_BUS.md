# Directive Bus (quick directives to cron roles)

## Goal

Provide a **fast broadcast mechanism** for operational directives that every cron role can read on its next tick.

This avoids copy/pasting instructions into multiple tmux sessions.

## Files

- Bus (append-only): `docs/ops/DIRECTIVE_BUS.jsonl`
- Tooling: `scripts/directive_bus.sh`

## Post a directive

Examples:

- Broadcast to all roles:
  - `bash scripts/directive_bus.sh post --targets all --kind policy --ttl-min 60 --msg "Stop new features. Focus on BATCH-02 dispatch + frontend up."`

- Target a subset:
  - `bash scripts/directive_bus.sh post --targets planner,dev,qa --kind delivery --ttl-min 45 --msg "Priorité: DISPATCH BATCH-02. Pas de refacto."`

## View active directives

- `bash scripts/directive_bus.sh active --role dev --limit 5`

## How roles consume

`scripts/cron_tmux_role_runner.sh` injects `directives_tail` into `RUNTIME_CONTEXT`.

Rule:
- roles must consider the latest matching directive (`targets` includes `all` or the role).
- if a directive blocks execution, the role should surface it as `STATUS=BLOCKED` with a concrete reason.

## Hygiene

- Keep directives short.
- Use TTL to prevent stale directives lingering.
- Prefer one action per directive.
