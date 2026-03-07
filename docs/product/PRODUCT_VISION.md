---
status: canonical
last_verified: 2026-03-07
canonical_replaces:
  - docs/VISION.md
---

# Finance Copilot Product Vision

## One sentence
Build a personal finance copilot that starts with a brief of the day, lets the user ask or open a ticker/theme immediately, and returns an explainable investment memo without breaking the existing frontend theme.

## Product thesis
The product is not a passive dashboard and not a generic chatbot.

It is a **personal deep-dive investment assistant** that:
- reduces fragmented market research into a usable decision flow
- works in a **brief + ask** rhythm
- uses watchlist and portfolio context when available
- delivers a **strong recommendation** when the evidence is sufficient
- keeps freshness, risks, and sources visible

## Target user
- Primary user: the owner of this repo, managing personal investments solo
- Profile: financially literate, but not a full-time market analyst
- Pain point: spending 3-10 hours per week collecting market, macro, and news context before acting
- Expected gain: reach a credible decision faster without losing traceability

## Core product shape
### Primary product mode
The primary mode is a **Deep-Dive Assistant**.

The main value is:
- understand what matters today
- ask a question or open a ticker/theme
- receive a recommendation that is specific enough to act on

### Entry surface
The default experience is **Brief + Ask**.

The product should open with:
- a short daily brief
- visible current regime/risk context
- immediate entry into:
  - a question
  - a ticker
  - a theme
  - a watchlist/portfolio-guided deep dive

### Personal context
The product should use:
- watchlist
- portfolio context
when available.

But it must remain useful without them.

Rule:
- without portfolio data -> useful market assistant
- with portfolio/watchlist -> more relevant, prioritized, decision-oriented assistant

## Output standard
The standard output is an **investment memo**, not a one-line chatbot reply.

Every important answer should include:
- a clear verdict
- the intended horizon
- the main reasons
- risks or invalidation conditions
- confidence
- freshness
- sources

The memo should be:
- richer than a simple signal
- shorter than a full research note
- structured enough to support a real decision

## Decision horizon
The product is optimized for:
- 1 day
- 1 week
- 1 month

It should help with tactical and near-term decisions, not only long-horizon investing and not automated trading.

## Non-negotiable product rules
- Explainable-first: no important recommendation without visible reasons and source context
- Proof-first delivery: a feature is not done without API/UI/runtime proof
- Freshness is part of correctness: stale data must be explicit
- Strong recommendation when justified: the system should take a position when evidence is sufficient
- Honest degraded mode: uncertainty and fallback must be visible, not hidden behind fake confidence
- Low-cost runtime by default: personal-use economics remain part of the product constraint

## Frontend constraint
### Theme preservation is mandatory
The existing frontend theme is a protected product asset.

The product must be improved with a **backend-first strategy**:
- prefer richer backend contracts over frontend rewrites
- keep the current theme, design tokens, palette, and shell intact
- allow only minor frontend changes when necessary to wire or display backend improvements

### What is acceptable on the frontend
- data wiring
- copy and label adjustments
- loading/degraded/stale states
- lightweight rendering changes needed to display memo-style outputs

### What is not acceptable by default
- redesigning the shell
- rewriting the theme
- replacing the design language
- breaking visual continuity to compensate for weak backend behavior

## What the product must do very well
### P0
- show what changed today and what matters now
- answer "what should I do with my portfolio today?"
- support a strong deep dive on a ticker/theme/question
- make freshness, confidence, risks, and sources visible

### P1
- multi-asset forecasts with short justification
- deep dives on tickers, sectors, macro themes, and watchlist items
- news prioritized by portfolio or market impact
- backend synthesis that turns multiple signals into a usable recommendation

## Non-goals
- no automated trading or broker execution
- no social/community features
- no enterprise multi-user priorities
- no opaque AI behavior that bypasses product guardrails
- no frontend-led product rewrite as a substitute for backend quality

## Success looks like this
- The user opens the app and understands the market situation in under a minute
- The user can ask about a ticker/theme/portfolio and receive a usable investment memo
- The product can produce strong recommendations without hiding weak evidence
- The frontend feels stable and coherent while backend intelligence improves underneath it
- The system materially reduces research time while staying viable for continuous personal use
