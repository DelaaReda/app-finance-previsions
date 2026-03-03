# Claude Desktop Deep Troubleshoot

## Purpose
`use-claude-deep-troubleshoot` is a stable, repeatable diagnostic workflow for Claude Desktop on this VM.

It checks:
- Local installation/runtime state (`claude-desktop`, Electron process, key log files)
- High-signal Claude Desktop log patterns (`oauth`, `upstream`, `500`, bootstrap/account state)
- Network/API health probes for OAuth endpoints
- Official status page (`status.claude.com`)

It then returns a clear verdict:
- `HEALTHY`
- `DEGRADED_REMOTE`
- `LOCAL_CONFIG_ISSUE`
- `DEGRADED_REMOTE_AND_LOCAL`

## Command
Primary command:
```bash
scripts/use-claude-deep-troubleshoot.sh
```

Compatibility alias (typo-friendly):
```bash
scripts/use-claude-deep-troobleshoot.sh
```

## Options
```bash
scripts/use-claude-deep-troubleshoot.sh --help
```

Key options:
- `--open-chat "prompt"`: open a new Claude Desktop chat if healthy
- `--force-open-chat`: force open even if degraded
- `--no-network`: run local-only checks (skip HTTP probes/status page)

## Exit Codes
- `0`: healthy
- `10`: degraded remote
- `20`: local config issue
- `30`: remote + local issues

## Report Output
Each run writes a report to:
```bash
logs-codex-runs/claude-deep-troubleshoot-YYYYMMDD-HHMMSS.txt
```

## Standard Workflow
1. Run deep troubleshoot:
```bash
scripts/use-claude-deep-troubleshoot.sh
```
2. If verdict is `DEGRADED_REMOTE`, do not brute-force retries. Re-run periodically.
3. Once verdict becomes `HEALTHY`, run a smoke test chat:
```bash
scripts/use-claude-deep-troubleshoot.sh --open-chat "post-recovery-smoke-test"
```
4. If smoke test succeeds, continue normal usage.

## "Service Is Back" Checklist
Use this checklist before declaring recovery:
1. Status indicator is normal (not minor/major/critical outage).
2. OAuth probes stop returning `503`.
3. Main log no longer accumulates:
   - `oauth failed: authorize returned 503`
   - `no healthy upstream`
   - `upstream connect error`
   - `Navigation ... failed with status code 500`
4. New chat opens from wrapper:
```bash
scripts/claude_desktop_new_chat.sh --prompt "post-recovery-smoke-test"
```

## Notes
- This feature is intentionally non-destructive by default.
- It is designed to separate remote outages from local misconfiguration.
- Avoid ad-hoc temporary hacks during incidents; use this runbook for consistent triage.
- For UI prompt automation with direct text extraction (input -> output), use:
  - `docs/ops/CLAUDE_DESKTOP_UI_IO.md`
