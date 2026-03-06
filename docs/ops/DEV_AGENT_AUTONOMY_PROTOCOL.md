# Dev Agent Autonomy Protocol

## Changelog
- **2026-03-04**: Full rewrite in English; added strict issue-reporting contract, message-ack behavior, and autonomy coaching metrics.

## 1) Purpose and Scope
This protocol defines how the `dev` lane delivers continuously, with architecture-safe changes and verifiable QA evidence.

Scope:
- Tick-level behavior and delivery loop.
- Required evidence contract fields.
- Message bus acknowledgements.
- Anti-stall and parent-coaching signals.

## 2) Normative Rules (MUST/SHOULD/MUST NOT)
- `dev` **MUST** prioritize `IN_PROGRESS` tasks, then `READY` tasks.
- `dev` **MUST** follow: `claim -> patch -> test -> complete/handoff` when work is available.
- `dev` **MUST NOT** produce repeated `analysis_only` while actionable work exists.
- `dev` **MUST** include `issues`, `issue_count`, `issue_severity` on every tick.
- `run_note` **MUST** be a meaningful mini-paragraph (minimum 5 words).
- `dev` **MUST** reuse existing modules/APIs/components before creating new ones.

## 3) Interfaces and Schemas
### Required evidence fields (always)
- `task_update`
- `issues`
- `issue_count`
- `issue_severity`
- `lock_check`
- `run_note`
- `DEV_ARTIFACT` (or current role artifact marker)

### Required for non-delivery updates (`analysis_only|none_no_ready|none_no_signal`)
- `channels_read`
- `impact_assessment`
- `impact_action`

### Required for close/handoff (`complete|handoff`)
- `cmd`
- `tests_run`
- `root_cause`
- `fix_applied`
- `verify`
- `qa_proof`

### Issue schema constraints
- `issues=none` iff `issue_count=0` and `issue_severity=none`.
- If `issue_count>0`, `issues` must be CSV and count must match.
- If blocked, severity must be `medium|high|critical`.

## 4) Runtime Behavior and Edge Cases
- If queue/workboard state diverges, `dev` should document mismatch and perform minimal corrective action.
- Fallback contracts may be auto-filled only for technical fallback sources; normal agent output remains strict.
- Repeated no-signal cycles with active work are treated as a stall and must trigger delivery action next tick.

## 5) Operator Commands and Expected Outputs
- Dev parent monitor:
```bash
bash scripts/dev_parent_monitor.sh --strict
```
Expected:
- Clear verdict and streak counters.

- Guard tests:
```bash
python3 platform/automation/tests/test_role_contract_guard.py
python3 platform/automation/tests/test_role_contract_guard_dev_evidence.py
```
Expected:
- No contract regressions for `dev` evidence.

- Runtime context tests:
```bash
python3 platform/automation/tests/test_role_runtime_context.py
```
Expected:
- Message injection and core runtime context remain valid.

## 6) Observability and Troubleshooting
Primary sources:
- `logs-codex-runs/fc-ticks/dev.tick.log`
- `logs-codex-runs/role-runner/dev.live.log`
- `logs-codex-runs/role-runner/dev.events.log`
- `docs/operations/orchestrator/agent-iteration-issues.jsonl`

Useful APIs:
- `GET /api/agent-insights`
- `GET /api/iteration-issues?role=dev&n=30`
- `GET /api/runtime-diagnostics`

## 7) Compatibility and Migration Notes
- Legacy role aliases can map to `dev` only in explicit compatibility mode.
- Evidence strictness remains enforced even during config migration (`YAML > ENV fallback`).
- Message bus acknowledgement fields are additive and backward-compatible.

## 8) Acceptance Criteria
- `dev` no longer stalls in repeated weak no-op cycles when actionable work exists.
- Every blocked tick includes a valid issue report.
- Delivery ticks include command/test evidence when closing tasks.
- Parent coaching metrics identify `RECOVERING|STALLED|DELIVERING` behavior patterns.
