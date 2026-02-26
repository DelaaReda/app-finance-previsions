# OpenClaw PO Operations (finance app)

Updated: 2026-02-24

## Objective
Use OpenClaw as Product Owner to pilot multi-agent execution through `scripts/qwen_orchestrator.py`.

## Core commands

### Session + channel health
```bash
openclaw channels status --probe
openclaw doctor
```

### Orchestrator status
```bash
cd /Users/venom/Documents/analyse-financiere
python3 scripts/qwen_orchestrator.py --tmux-cmd status
python3 scripts/analyze_orchestrator_runs.py --runs-dir finance-app/orchestrator-runs --limit 8
```

### Dispatch a feature
```bash
cd /Users/venom/Documents/analyse-financiere
python3 scripts/qwen_orchestrator.py \
  --agent-bin qwen \
  --rounds 3 \
  --with-architect \
  --with-manager \
  --feature "<objective + acceptance criteria>"
```

## Enabled plugins
- whatsapp
- memory-core
- llm-task
- lobster

## Known quirk
OpenClaw doctor repeatedly prints:
- `channels.whatsapp.enabled` unknown key

Functionality remains OK (channel connected + delivery works).

## Agent routing
- Dedicated agent configured: `finance-po`
- Binding configured: WhatsApp direct peer `+14389799898` -> `finance-po`

Operational rule:
```bash
openclaw agent --agent finance-po --message "<task>"
```

Do not rely on implicit routing from `openclaw agent --to ...`.

## Active skills (finance-po profile)
- `finance-po-orchestrator`
- `coding-agent`
- `tmux`
- `api-tester`
- `playwright-mcp`
- `e2e-testing-patterns`
- `test-runner`
- `debug-pro`
- `backend-patterns`
- `senior-architect`
- `cto-advisor`
- `receiving-code-review`
- `conventional-commits`
- `git-summary`
- `unfuck-my-git-state`
- `task-status`
- `session-logs`
- `github`
- `gh-issues`
- `prompt-log`

## Skill security posture
- Source catalog: `awesome-openclaw-skills`
- Vetted via `clawhub inspect` + static pattern scan
- Rollout report: `/Users/venom/Documents/analyse-financiere/finance-app/openclaw-skills-rollout-2026-02-24.md`
- Full audit JSON: `/Users/venom/Documents/analyse-financiere/finance-app/openclaw-skill-audit.json`
