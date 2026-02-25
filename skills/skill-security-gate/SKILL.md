---
name: skill-security-gate
description: Run a strict pre-install security gate for third-party OpenClaw skills. Use when auditing skills for backdoor risk, exfiltration behavior, hidden outbound messaging, or unsafe runtime instructions.
---

# Skill Security Gate

Apply a fail-closed audit before installing any third-party skill.

## Gate steps

1. Verify provenance
   - Identify source repo/author/version.
   - Prefer pinned commit or release tag.

2. Inspect SKILL.md and resources
   - Read SKILL.md fully.
   - Inspect scripts/references for execution paths.

3. Detect high-risk patterns
   - curl/wget piping to shell
   - eval/exec/subprocess shell usage
   - credential scraping (`.env`, `~/.ssh`, cloud keys)
   - hardcoded chat IDs, webhooks, tokens, unknown endpoints
   - obfuscated payloads (base64 decode + execute)

4. Classify behavior
   - local-only deterministic
   - network-read only
   - network-write / message-send / side effects

5. Verdict
   - ALLOW: no critical findings, behavior explicit
   - REVIEW: ambiguous behavior, medium risk
   - BLOCK: clear exfiltration/backdoor indicators

## Required deliverable

- Findings (file + line + reason)
- Risk level per finding
- Final verdict: ALLOW / REVIEW / BLOCK
- Minimal remediation to move to ALLOW

## Rule

When uncertain, choose REVIEW (or BLOCK if user safety is impacted).
