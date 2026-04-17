# Iteration Issue Reporting Spec

## Scope
This spec defines mandatory issue reporting for every active role (`planner`, `dev`, `admin`, and any active runtime role discovered by topology/crontab) on every tick.

## Contract Fields (Mandatory)
Add these keys in `EVIDENCE` for each contract:
- `issues=<none|code1,code2,...>`
- `issue_count=<integer >=0>`
- `issue_severity=<none|low|medium|high|critical>`

Issue code format:
- CSV only
- Each code must match: `^[a-z0-9_]{3,64}$`

## Consistency Rules
1. `issues=none` iff `issue_count=0` and `issue_severity=none`.
2. If `issue_count>0`, then `issues!=none` and number of codes must equal `issue_count`.
3. If `task_update=blocked` or `BLOCKER_ID!=NONE`:
- `issue_count>=1`
- `issue_severity in {medium,high,critical}`

## Enforcement (Strict Immediate)
Guard: `platform/policies/role_contract_guard.py`

Error IDs:
- `ISSUE_REPORT_MISSING`
- `ISSUE_REPORT_INVALID`
- `ISSUE_REPORT_INCONSISTENT`
- `BLOCKED_WITHOUT_ISSUE_REPORT`

Any of these errors triggers immediate block normalization.

## Valid Examples
No issue:
```text
EVIDENCE: task_update=analysis_only; lock_check=ok; run_note=analyse architecture et verification runtime complete; issues=none; issue_count=0; issue_severity=none; planner_artifact=docs/ops/ORCHESTRATION_RELIABILITY_SPEC.md
```

Blocked with issue:
```text
EVIDENCE: task_update=blocked; lock_check=ok; run_note=blocage runtime confirme avec preuve de commande locale; issues=agent_rate_limit_codex; issue_count=1; issue_severity=high; dev_artifact=apps/api/src/domains/judge/application/g4f_client.py; cmd=python3 -m pytest platform/automation/tests/test_role_contract_guard.py; cmd_err_excerpt=http_429_quota
```

## Invalid Examples
Invalid (`issues=none` with count/severity mismatch):
```text
issues=none; issue_count=1; issue_severity=high
```

Invalid (blocked without issue):
```text
task_update=blocked; issues=none; issue_count=0; issue_severity=none
```

Invalid (bad code format):
```text
issues=RATE-LIMIT; issue_count=1; issue_severity=medium
```

## Monitoring and Persistence
Canonical JSONL:
- `docs/operations/orchestrator/agent-iteration-issues.jsonl`

Read-only compatibility aliases:
- `docs/orchestrator-ops/agent-iteration-issues.jsonl`
- `logs-codex-runs/executor-monitoring/events.jsonl`

Per-record keys:
- `issues`
- `issue_count`
- `issue_severity`
- `issue_codes` (normalized list)
- `issue_reporting_ok` (bool)
- `issue_reporting_errors` (list)

Aggregates (`agent-iteration-issues-latest.json` + monitor summary):
- `issue_reports_open`
- `issue_reporting_missing_count`
- `issue_reporting_missing_roles`
- `critical_count`
- `critical_issue_roles`

## FC Monitor API/UI
Endpoints:
- `GET /api/status` -> `issue_reporting`
- `GET /api/agent-insights` -> per-agent issue report fields
- `GET /api/iteration-issues` -> recent issue rows with filters (`role`, `severity`, `recent_minutes`, `n`)

UI requirements:
- Color severity: `critical/high` red, `medium` amber, `low` blue.
- Show per-agent last issue report and missing-report badge.

## Troubleshooting Fast Path
These troubleshooting endpoints are VM-local monitor/orchestration checks, not public EC2 app-serving checks.

1. Check aggregate compliance:
```bash
curl -s http://127.0.0.1:7779/api/status | jq '.issue_reporting'
```
2. Inspect recent malformed rows:
```bash
curl -s 'http://127.0.0.1:7779/api/iteration-issues?severity=all&n=120' | jq '.items[] | select(.issue_reporting_ok==false)'
```
3. Inspect tick action lines:
```bash
tail -n 200 logs-codex-runs/fc-ticks/dev.tick.log | rg '\[ACTION\]'
```
