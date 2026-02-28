# Command Safety Checklist (Pre-Execution)

Use this checklist before running any shell command from a skill or ad-hoc flow.

## 1) Intent + scope
- Command is necessary for the user request.
- Working directory is correct (`/home/venom/analyse-financiere` unless explicitly requested).
- Side effects are understood (files changed, network calls, services touched).

## 2) Destructive risk
- Block by default: `rm -rf /`, filesystem wipes, recursive deletes outside workspace.
- Prefer recoverable delete (`trash`) over hard delete where possible.
- Require explicit user confirmation for destructive operations.

## 3) Exfiltration / external actions
- Detect outbound actions: `curl/wget` to unknown hosts, message/post/send commands.
- Require explicit user intent for external messaging, posting, or data export.
- Never send secrets from `.env`, `~/.ssh`, credentials files.

## 4) Privilege / persistence
- Flag `sudo`, service changes (`systemctl`), startup persistence, cron edits.
- Require confirmation for privilege escalation or daemon config changes.

## 5) Supply-chain execution
- Block `curl|bash`, `wget|sh`, and remote script execution without review.
- Prefer pinned versions/checksums before installing binaries.

## 6) Injection / unsafe shell patterns
- Flag `eval`, `bash -c` with untrusted interpolation, unquoted vars from user input.
- Use parameterized arguments where possible.

## 7) Observability
- Log why command is safe + expected result.
- After execution: capture exit code, key output, touched files.

## Fast policy output
- `ALLOW`: safe, in-scope, no high-risk markers.
- `CONFIRM`: medium/high-risk but user-confirmable.
- `BLOCK`: clearly unsafe or off-scope.
