---
name: skill-triage-board
description: Build a prioritized shortlist of external OpenClaw skills before installation. Use when asked to scan a large skill catalog, pick best candidates for a project, and produce ALLOW/REVIEW/BLOCK recommendations with reasons.
---

# Skill Triage Board

Create a practical shortlist from large skill lists.

## Workflow

1. Define objective and constraints (project type, risk tolerance, required capabilities).
2. Gather candidate links/slugs from user source (GitHub list, ClawHub query, docs).
3. Filter out low-signal items (duplicates, joke/demo/test skills, unclear ownership).
4. Score remaining candidates on:
   - relevance to task
   - maintenance freshness
   - transparency of behavior
   - external side effects (messaging, network, credentials)
5. Produce a compact board:
   - ALLOW (safe enough for immediate trial)
   - REVIEW (needs manual inspection)
   - BLOCK (clear risk or off-scope)
6. Recommend top 3 to install first with expected payoff.

## Output format

- Objective
- Top candidates (name + why)
- ALLOW / REVIEW / BLOCK table
- Next action plan (install order + validation checks)

## Guardrails

- Prefer read-only or low-privilege skills first.
- Flag hidden outbound messaging, hardcoded IDs, remote script execution.
- Do not claim a skill is safe without source evidence.
