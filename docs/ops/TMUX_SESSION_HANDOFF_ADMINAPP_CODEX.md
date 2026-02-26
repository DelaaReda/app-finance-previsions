# TMUX Session Handoff - AdminApp Codex

## Role
- Role name: `adminapp-codex`
- Scope: fiabilite runtime cron, coherence config globale, coordination tri-admin.

## Session snapshot (current)
1. Tri-admin sync loop active:
   - `chat -> iterations -> watchdog -> memory`
   - chat file: `docs/ops/ADMIN_TEAM_CHAT.md`
2. Runtime profile target:
   - parallel / codex-only / 17 jobs (14 roles + 2 admins + 1 stale auto-heal)
   - runner-only payloads (`bash scripts/cron_tmux_role_runner.sh <role>`)
   - baseline: `TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk`, `timeoutSeconds=480`
3. Proof-first policy:
   - role contract 8-keys obligatoire
   - `EVIDENCE` schema kv (cf. `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`)
   - DONE sans preuve => DONE->REVIEW (owner QA)

## Active priorities
1. Keep runtime stable (avoid multi-axis changes).
2. Reduce false/stale blockers in role outputs.
3. Improve delivery signal (reduce `NO_DELTA`) with one controlled change at a time.

## Key references
- `docs/ops/ADMIN_TEAM_CHAT.md`
- `docs/ops/ADMIN_TEAM_ITERATIONS.md`
- `docs/orchestrator-ops/agent-watchdog.md`
- `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- `docs/ops/CRON_STRATEGY.md`
- `docs/ops/TMUX_CRON_OPERATIONS.md`
- `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`
- `scripts/cron_tmux_role_runner.sh`
