---
name: whatsapp-compact-report
description: Produce compact WhatsApp-ready technical updates from verbose logs or long AI outputs. Use when response length hurts readability on mobile chat.
---

# WhatsApp Compact Report

Convert long technical outputs into short, readable WhatsApp messages.

## Trigger

Use this skill when output is long and the user needs compact chat visibility.

## Workflow

1. Pass raw text/log into `scripts/compact_report.py`
2. Keep only high-signal sections: done, blockers, next, evidence
3. Enforce max character budget
4. Output WhatsApp-safe formatting only (no markdown tables/headers)

## Output style

- Use single-line sections with bullets
- Keep message under configured max chars
- Include file paths/commands only when actionable

## Guardrails

- Do not hide blockers.
- Preserve at least one concrete evidence line.
