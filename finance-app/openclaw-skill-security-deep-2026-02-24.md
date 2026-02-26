# OpenClaw Skills Security Deep Audit

Date: 2026-02-24

## Scope
- Skills analyzed: **19**

## Tools Used
- `clawhub_vt_gate_inference`: enabled
- `bandit`: enabled
- `pip_audit`: enabled
- `safety`: enabled
- `secret_regex_scan`: enabled
- `static_rule_scan`: enabled
- `shell_hardening_checks`: enabled

## Global Summary
- Risk buckets: HIGH=1 MEDIUM=8 LOW=10
- VT suspicious flags (inferred): 9
- Bandit findings: 26
- Secret-like hits: 0

## Per Skill (Top Risk First)
- **senior-architect** | level=HIGH score=25 | vt=True | bandit=10 | static=0 | secrets=0
- **task-status** | level=MEDIUM score=24 | vt=True | bandit=9 | static=0 | secrets=0
- **codex-quota** | level=MEDIUM score=23 | vt=True | bandit=6 | static=0 | secrets=0
- **codex-orchestration** | level=MEDIUM score=15 | vt=True | bandit=0 | static=0 | secrets=0
- **commit-analyzer** | level=MEDIUM score=15 | vt=True | bandit=0 | static=0 | secrets=0
- **cto-advisor** | level=MEDIUM score=15 | vt=True | bandit=0 | static=0 | secrets=0
- **prompt-log** | level=MEDIUM score=15 | vt=True | bandit=0 | static=0 | secrets=0
- **receiving-code-review** | level=MEDIUM score=15 | vt=True | bandit=0 | static=0 | secrets=0
- **unfuck-my-git-state** | level=MEDIUM score=15 | vt=True | bandit=0 | static=0 | secrets=0
- **api-tester** | level=LOW score=6 | vt=False | bandit=0 | static=3 | secrets=0
- **e2e-testing-patterns** | level=LOW score=4 | vt=False | bandit=0 | static=2 | secrets=0
- **debug-pro** | level=LOW score=2 | vt=False | bandit=0 | static=1 | secrets=0
- **finance-po-orchestrator** | level=LOW score=2 | vt=False | bandit=0 | static=1 | secrets=0
- **test-runner** | level=LOW score=2 | vt=False | bandit=0 | static=1 | secrets=0
- **playwright-mcp** | level=LOW score=1 | vt=False | bandit=1 | static=0 | secrets=0
- **backend-patterns** | level=LOW score=0 | vt=False | bandit=0 | static=0 | secrets=0
- **conventional-commits** | level=LOW score=0 | vt=False | bandit=0 | static=0 | secrets=0
- **git-summary** | level=LOW score=0 | vt=False | bandit=0 | static=0 | secrets=0
- **multi-factor-strategy** | level=LOW score=0 | vt=False | bandit=0 | static=0 | secrets=0

## Artifact
- JSON: `/Users/venom/Documents/analyse-financiere/finance-app/openclaw-skill-security-deep-2026-02-24.json`
