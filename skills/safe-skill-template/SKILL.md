---
name: safe-skill-template
description: Build new skills with secure defaults (no hidden outbound actions, no hardcoded targets, explicit env gating). Use when creating or adapting skills from external sources.
---

# Safe Skill Template

Use this template when you create a new skill and want predictable behavior with low security risk.

## Default Security Contract

1. No hardcoded secrets, phone numbers, chat IDs, or webhook URLs.
2. No outbound network calls unless explicitly enabled by env vars.
3. No destructive shell patterns (`curl|bash`, `wget|sh`, `rm -rf`) in scripts.
4. External messaging must require explicit user action and configurable target.
5. Keep logs sanitized (never print tokens, passwords, or API keys).

## Required Skill Structure

```
your-skill/
  SKILL.md
  scripts/
  references/
```

## Authoring Rules

- Put only essential trigger/usage instructions in `SKILL.md`.
- Put implementation details in `scripts/` and call scripts with parameters.
- Put long docs/checklists in `references/`.
- Use env-based configuration:
  - `TARGET_ID` instead of hardcoded target
  - `API_BASE_URL` instead of hardcoded endpoint
  - `ENABLE_NETWORK=1` gate for outbound calls

## Pre-Enable Checklist

Run the audit script before enabling the skill:

```bash
python3 scripts/audit_skill.py --skill-dir /path/to/skill
```

Fail the review if any `HIGH` finding appears.

