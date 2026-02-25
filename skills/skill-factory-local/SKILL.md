---
name: skill-factory-local
description: Design and scaffold new local OpenClaw skills quickly with clean metadata and minimal token footprint. Use when creating custom skills for recurring workflows in the current workspace.
---

# Skill Factory Local

Create compact, high-signal skills for repeated tasks.

## Build loop

1. Define trigger sentence
   - What user asks when this skill should activate.

2. Define scope
   - Include only one clear job per skill.
   - Move optional details to references files.

3. Scaffold structure
   - `<skill-name>/SKILL.md` (required)
   - optional `scripts/`, `references/`, `assets/`

4. Write frontmatter
   - `name`: lowercase-hyphen format
   - `description`: what it does + when to use

5. Write body
   - imperative instructions
   - deterministic workflow
   - explicit output format
   - safety guardrails

6. Validate quality
   - concise (<500 lines preferred)
   - no fluff
   - no hidden side effects

7. Package only if requested
   - run package tool or keep local folder for workspace usage

## Skill quality checklist

- Single responsibility
- Clear trigger language
- Evidence-based outputs
- Explicit safety boundaries
- Minimal token cost
