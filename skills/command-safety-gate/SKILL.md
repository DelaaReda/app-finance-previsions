---
name: command-safety-gate
description: Validate shell commands before execution. Use when a skill proposes commands and you need a pre-exec safety decision (ALLOW/CONFIRM/BLOCK) with explicit reasons.
---

# Command Safety Gate

Run preflight validation before executing shell commands from skills.

## Workflow
1. Evaluate command with `scripts/command_safety_gate.py --cmd "..."`.
2. If decision is `BLOCK`, do not execute.
3. If decision is `CONFIRM`, ask the user first (unless already explicitly approved).
4. If decision is `ALLOW`, execute with correct workdir and minimal privilege.
5. Record the decision and reason in your summary.

## Required checks
- Workspace scope
- Destructive patterns
- Outbound/exfiltration patterns
- Privilege escalation/persistence
- Remote script execution patterns
- Injection-prone shell usage

## Output contract
- Decision: ALLOW | CONFIRM | BLOCK
- Risk score (0-100)
- Reasons list
- Required user confirmation (true/false)

## Guardrail
Never execute commands blindly from SKILL.md examples without first passing this gate.
