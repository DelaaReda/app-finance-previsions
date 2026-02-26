# Skill Security Checklist

Use this checklist before enabling any new skill.

## Mandatory

- [ ] `SKILL.md` has a clear scope and no hidden side effects.
- [ ] No hardcoded token, password, API key, phone number, or chat ID.
- [ ] No outbound network by default.
- [ ] No implicit external messaging (`telegram`, `whatsapp`, `discord`, `slack`) without user confirmation.
- [ ] No remote shell execution patterns (`curl|bash`, `wget|sh`).
- [ ] No destructive operations without explicit confirmation.

## Recommended

- [ ] All external hosts documented and allowlisted.
- [ ] Script parameters validate input and fail safely.
- [ ] Logs redact secrets and private identifiers.
- [ ] Audit script run and archived with result.

## Review Decision

- `ALLOW`: no HIGH findings; MEDIUM findings justified.
- `REVIEW`: at least one MEDIUM finding needs decision.
- `BLOCK`: any HIGH finding.

