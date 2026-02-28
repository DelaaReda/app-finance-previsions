# OpenClaw Skills Rollout (2026-02-24)

Source catalog reviewed:
- https://github.com/VoltAgent/awesome-openclaw-skills

## Goal
Prepare a focused Product-Owner skillset for `analyse-financiere` (orchestrator + QA + code quality), with security vetting before installation.

## Security workflow used
1. Enumerated candidate skills from the catalog.
2. Pulled metadata + files with `npx clawhub inspect`.
3. Ran static pattern scan on skill files (eval/exec/os.system/shell=True/curl|bash/sudo/rm -rf/http).
4. Installed only vetted skills.
5. Kept suspicious/high-noise skills disabled unless explicitly needed.

Raw audit export:
- `finance-app/openclaw-skill-audit.json`

## Active 20-skill profile (finance-po)
These are now the only skills injected for agent `finance-po`:

1. coding-agent
2. gh-issues
3. github
4. session-logs
5. tmux
6. api-tester
7. backend-patterns
8. conventional-commits
9. cto-advisor
10. debug-pro
11. e2e-testing-patterns
12. finance-po-orchestrator
13. git-summary
14. playwright-mcp
15. prompt-log
16. receiving-code-review
17. senior-architect
18. task-status
19. test-runner
20. unfuck-my-git-state

## Installed from awesome-openclaw-skills and enabled
- backend-patterns
- conventional-commits
- debug-pro
- git-summary
- prompt-log
- receiving-code-review
- senior-architect
- task-status
- test-runner
- unfuck-my-git-state
- cto-advisor

## Installed but kept disabled (not in active 20)
- codex-orchestration
- codex-quota
- multi-factor-strategy
- commit-analyzer

## Not installed on purpose
- skill-vetting (high scanner noise from embedded pattern examples; keep for manual review only)
- skill-vetter (utility overlap with local vetting pipeline)

## Operational notes
- `finance-po` sessions were reset so new skill filters are effective.
- `openclaw agent --agent finance-po --message "/new"` now loads exactly 20 skills.
- Keep using explicit agent selection:
  - `openclaw agent --agent finance-po --message "..."`

