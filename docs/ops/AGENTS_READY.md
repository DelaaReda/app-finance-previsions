# Agents Readiness

## Purpose
Define what "ready" means for the current planner-orchestrator runtime.

## Ready Means
- runtime is on the VM workspace `/home/venom/analyse-financiere`
- `planner` scheduled lane is healthy
- role sessions are fresh: stale tmux/Codex resume state does not survive a VM resume or prompt/workspace drift
- role sessions are rooted in `/home/venom/analyse-financiere`; foreign or deleted workdirs do not count as ready
- planner contracts are fresh and parseable
- queue/workboard are coherent
- queue/workboard active cycle and role-memory handoff do not disagree on the live stream; if they disagree, canonical queue/workboard wins
- planner subagent status does not override the canonical active cycle; stale rows from non-active cycles are compat debt only
- blocking interactive Codex prompts (`update`, trust/setup menus, manual choice screens) do not count as lane readiness; the lane must be recycled or restarted
- state reconciler and delivery gate are active
- monitor and doctor agree on execution mode and core roles

## Target Runtime Readiness
Target mode is:
- `execution_mode=planner_experimental`
- `core_roles=["planner"]`

Readiness is not defined by the presence of independent `dev/admin/scrum_master` cron lanes.

## Capability Readiness Under Planner

### Dev capability ready when
- planner can delegate implementation work
- delivery proof requirements are enforced
- planner-owned results can be merged cleanly
- route-mismatched `dev` capability rows do not count as active readiness and are quarantined as orchestration drift

### Admin capability ready when
- runtime diagnosis and reconciliation can be delegated
- stale locks/blockers can be repaired
- route-mismatched `admin` capability rows do not count as active readiness and are quarantined as orchestration drift

### Scrum capability ready when
- starvation/stall signals can be produced
- unblock/escalation outputs are available to planner

These capabilities do not need to exist as scheduled cron lanes in target mode.

## Operator Checks
```bash
bash scripts/runtime_host_check.sh
cat logs-codex-runs/monitor-lan-url.txt
bash scripts/fc_doctor.sh --json | jq '.checks.sessions,.checks.providers'
curl -s http://127.0.0.1:7779/api/status?lite=1 | jq '{health,execution_mode,core_roles,planner_subagents}'
curl -s http://192.168.64.9:7780/api/status?lite=1 | jq '{health,execution_mode,core_roles,planner_subagents}'
python3 -m pytest -q \
  platform/automation/tests/test_state_reconciler.py \
  platform/automation/tests/test_delivery_value_gate.py \
  platform/automation/tests/test_planner_subagent_manager.py
```

Expected:
- `runtime_is_vm=1`
- planner healthy
- stale role session artifacts recycled after large VM resume gaps
- no placeholder or shell-only tmux session is counted as an active lane without fresh execution proof
- stale planner subagent rows from inactive cycles do not redefine the current delivery stream
- execution mode and doctor aligned
- host-facing monitor link available through LAN proxy `7780`

## Compatibility Notes
- Legacy `po_scrum_master` and multi-lane readiness language is historical only.
- Compatibility scripts may still exist, but they are not the readiness target.
- Public tunnel URLs are no longer canonical readiness signals.
- `planner` and `dev` use `gpt-5.3-codex-spark` with `high` reasoning as the secondary Codex fallback before `qwen`.
- `RUN_LOCK_BUSY` on planner ticks is cadence/backpressure only; it must not be treated as proof that a stale non-active-cycle stream is still canonical.

## Team Coordination
- Use `memory/agents/admin-agents.md` as the shared manual coordination board when a cross-role human-readable board is needed.
- That board is advisory only; queue/workboard, runtime truth, and planner dispatch snapshots remain canonical.
- Do not create ad-hoc `chat_*.md` coordination files for active runtime work.
