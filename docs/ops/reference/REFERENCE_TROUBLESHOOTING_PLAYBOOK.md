# Troubleshooting Playbook (Ops Runtime)

## Changelog
- **2026-03-04**: New document; consolidated deep-troubleshooting workflow for orchestration runtime, monitor, contracts, and coordination bus.

## 1) Purpose and Scope
This playbook provides deterministic incident response steps for orchestration/runtime issues.

Scope:
- Core lane blockers.
- Contract guard failures.
- Queue/workboard mismatch.
- Message bus and advisory communication issues.
- Monitor drift/staleness.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- Troubleshooting **MUST** isolate root cause before patching.
- Every incident response **MUST** include before/after validation evidence.
- Runtime fixes **SHOULD** be surgical and reversible.
- Operators **MUST NOT** treat historical errors as active blockers without recent evidence.

## 3) Interfaces and Schemas
### Incident record template
- `incident_id`
- `detected_at`
- `symptom`
- `root_cause`
- `impact`
- `fix`
- `verification`
- `residual_risk`

### Critical evidence sources
- `logs-codex-runs/fc-ticks/*.tick.log`
- `logs-codex-runs/role-runner/*.live.log`
- `logs-codex-runs/role-runner/*.events.log`
- `docs/operations/orchestrator/priority-queue.json`
- `docs/operations/orchestrator/parallel-workstreams.json`
- `logs-codex-runs/orchestrator-state/agent-message-bus.jsonl`

## 4) Runtime Behavior and Edge Cases
Common failure patterns:
1. `CONTRACT_GUARD_BLOCK` loops from missing required fields.
2. `none_no_signal` loops despite actionable queue/workboard state.
3. Path drift between canonical and alias orchestrator roots.
4. Stale locks causing skip loops.
5. Advisory lane confusion treated as core blocker.

Edge handling:
- Validate lock ownership/age before cleanup.
- Validate fresh state recomputation before claiming tasks.
- Re-test monitor root selection when UI appears stale.

## 5) Operator Commands and Expected Outputs
### Core diagnostic sequence
```bash
bash scripts/fc_health_check.sh --strict
bash scripts/monitor_agents.sh
bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779
bash scripts/dependency_recompute.sh
cat logs-codex-runs/monitor-lan-url.txt
```
Expected:
- explicit health + lane + source diagnostics.
- host-side monitor URL available via LAN proxy.

### Contract diagnostics
```bash
python3 platform/automation/tests/test_role_contract_guard.py
python3 platform/automation/tests/test_role_runtime_context.py
```
Expected:
- no contract/runtime context regressions.

### Message bus diagnostics
```bash
bash platform/automation/agent_message_bus.sh stats
bash platform/automation/agent_message_bus.sh active --role dev --json
```
Expected:
- coherent posted/delivered/actioned/closed counters and actionable role feed.

## 6) Observability and Troubleshooting
### Fast triage order
1. Confirm core lane status (`planner/dev/admin`) from `/api/status?lite=1`.
2. Check recent hard blockers in `/api/runtime-diagnostics`.
3. Correlate with per-role tick and runner event logs.
4. Validate queue/workboard consistency.
5. Validate message bus activity if coordination is involved.

Access note:
- VM-local UI/API: `http://127.0.0.1:7779/`
- Mac host UI/API: `http://192.168.64.9:7780/`
- public tunnels: disabled by default

### Deep method (for complex incidents)
- Isolate root cause vs noise.
- Prove causal chain (timestamps/process/session/locks/state).
- Apply minimal scoped fix.
- Measure before/after.
- Verify no runtime regressions.

### Operator Reporting Format (mandatory)
Every runtime report SHOULD follow this fixed order so comparisons remain deterministic:
1. `Santé`
2. `Batches`
3. `Agents`
4. `Blocages`
5. `Lecture réelle`
6. `Action recommandée`

Use this helper for a compact, normalized readout:
```bash
bash scripts/fc_status_brief.sh
```

## 7) Compatibility and Migration Notes
- During config migration, prefer documenting whether behavior came from YAML config or ENV fallback.
- Keep compatibility aliases readable, but always verify canonical source freshness.
- If doctor is not yet deployed, use health+monitor scripts as temporary split diagnostics.

## 8) Acceptance Criteria
- Incidents can be diagnosed end-to-end with deterministic evidence.
- Fixes are verifiable and do not introduce hidden regressions.
- Troubleshooting flow is reproducible by any operator without tribal context.
