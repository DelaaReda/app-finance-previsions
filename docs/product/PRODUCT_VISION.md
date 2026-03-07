---
status: canonical
last_verified: 2026-03-07
canonical_replaces:
  - docs/VISION.md
---

# Finance Copilot Product Vision

## One sentence
Build a personal finance copilot that turns macro, market, and news noise into explainable actions in 2-3 clicks.

## Target user
- Primary user: the owner of this repo, managing personal investments solo
- Profile: financially literate, not a full-time market analyst
- Pain point: spending 3-10 hours per week collecting fragmented signals before making a decision
- Expected gain: faster decisions without giving up traceability or freshness

## Core value
- Signal over noise: market context, forecasts, and news are ranked instead of dumped raw
- Explainable-first: every important output should show why, what sources were used, and how fresh they are
- Personal-use first: optimize for one serious user, not for multi-tenant SaaS concerns
- Low-friction workflow: dashboard, deep dive, and copilot answers should feel like one decision surface

## What the product must do well
### P0 decision loop
- Show what changed today and what matters now
- Tell the user whether the current market regime looks risky, neutral, or opportunistic
- Answer "what should I do with my portfolio today?" with a structured recommendation
- Keep data fresh enough for daily decision-making, with explicit degraded-mode signals when freshness slips

### P1 supporting capabilities
- Multi-asset forecasts with short justifications and confidence
- Deep dives on a ticker, sector, or macro theme in one interaction
- News summaries prioritized by portfolio impact, not just chronology
- A judge/copilot layer that synthesizes multiple signals into a usable decision

## Product principles
- Explainable-first: no opaque verdict without reasons and source traceability
- Proof-first delivery: a feature is not done until API/UI/runtime proof exists
- Freshness is part of correctness: stale data must be visible, not silently treated as healthy
- Real data over mock data: degraded mode is allowed, fake confidence is not
- Low-cost runtime by default: prefer architecture and model choices that keep the personal-use budget under control

## Technical constraints
- Runtime environment: local VM-first, not expensive cloud infrastructure
- Response budget: standard decision flows should complete in seconds, not minutes
- Freshness budget: a short cache window is acceptable; silent staleness is not
- Provider strategy: model/provider choices remain config-driven, with stronger models reserved for orchestration and harder delivery work

## Non-goals
- No automated trading or broker execution
- No social/community feature set
- No enterprise multi-user requirements
- No "AI magic" that hides evidence or contradicts product guardrails

## Success looks like this
- The user can open the app and understand the market situation in under a minute
- The user can reach a portfolio action recommendation in 2-3 clicks
- Forecasts, news, and copilot outputs carry freshness and source signals that are easy to trust or challenge
- The system reduces research time materially while staying cheap enough to run continuously for personal use
