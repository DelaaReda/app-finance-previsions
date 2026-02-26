# Product Vision Clarified - Finance Copilot

Date: 2026-02-26
Owner: Product Clarifier (Codex) + Venom
Mode: personal-first, low-cost execution

## Product intent
Build a personal finance copilot that helps a time-constrained investor make faster, better daily portfolio decisions without spending hours reading markets/news.

## Target user (v1)
- Primary user: Venom only (single user).
- Profile: professional, self-directed investor, not a finance expert.
- Constraint: low available time for market monitoring.
- Constraint: low runtime budget.

## Core problem
- Today, decision making is slow because market signals are fragmented across many sources.
- Development is also slowed by wide scope and weak end-to-end focus.

## Value proposition
"In 2-3 clicks, get a clear portfolio decision brief for today, backed by multi-model analysis and current market context."

Expected value:
- Save 3-10 hours/week of manual research.
- Detect directional shifts earlier (risk-on/risk-off, sector rotation, geopolitics).

## Product principles
- Decision support first, not auto-trading.
- Actionable output over raw data dumps.
- Freshness target over perfect precision.
- Low-cost runtime by default (g4f/free providers first).
- Explicit confidence + evidence for each recommendation.

## Runtime and cost constraints
- Runtime AI: prefer g4f/free providers + cheap fallbacks.
- Dev acceleration: OpenAI Pro budget used for development agents only.
- Keep infra simple (local-first, no expensive managed stack).

## MVP capability scope (locked)
1. Forecast by asset/sector:
   - Direction + confidence for selected assets/sectors.
2. Multi-model analysis and judge:
   - Aggregate multiple model outputs and produce one final decision signal.
3. Ask Copilot deep analysis:
   - User asks a question and receives a grounded synthesis using market data + near-real-time context.

Freshness target:
- Market/context data gap <= 10 minutes for MVP decision surfaces.

## Decision output contract (frontend)
Per asset/sector card:
- `direction`: bullish | neutral | bearish
- `confidence`: 0-100
- `action`: accumulate | hold | reduce
- `horizon`: short (1-3d) or swing (1-2w)
- `why`: 3 key reasons max
- `risk_flag`: low | medium | high
- `updated_at`: timestamp

## Initial universe (MVP v1)
- Index/market regime: SPY, QQQ, DIA, IWM
- Metals: GLD, SLV
- AI/mega-cap focus: NVDA, MSFT, AMZN, GOOGL, META, TSLA, AAPL
- Sector ETFs: XLK, XLE, XLF, XLV, XLI

## Explicit non-goals (out of MVP)
- Auto-trading / order execution.
- Broker API integration.
- Multi-user accounts and auth complexity.
- Mobile app.
- Social/community features.
- Full macro research platform.

## Success metrics (first 30 days)
- North Star:
  - `Daily Decision Brief Completion Rate`: >= 85% of active days have a complete decision brief in < 10 minutes.
- KPI 1:
  - `Freshness SLA`: >= 90% of key tiles updated within 10 minutes.
- KPI 2:
  - `Coverage SLA`: >= 90% of MVP universe has direction+confidence+action available at each refresh cycle.

## Priority epics (product order)
- P0 - Epic 1: Data Freshness and Signal Reliability Foundation
- P0 - Epic 2: Forecast Engine (asset/sector direction + confidence + action)
- P0 - Epic 3: Multi-Model Consensus and Judge
- P0 - Epic 15: Data-Driven Forecasting Core (dataset/training/backtest/inference)
- P1 - Epic 4: Decision Cockpit Frontend (2-3 click workflow)
- P1 - Epic 5: Ask Copilot Deep Analysis (grounded Q&A)
- P1 - Epic 10: Data Source Reliability and Ingestion Automation
- P1 - Epic 11: UX Workflow and Personal Settings Basics
- P1 - Epic 12: Alerts and Daily Automation
- P1 - Epic 13: Reliability, Security, and Backup
- P1 - Epic 14: MVP Release Readiness and Go-Live
- P2 - Epic 6: Portfolio Adaptation Layer (watchlist/risk profile tuning)
- P1 - Epic 8: Cost Governance and Runtime Efficiency (free-first routing + guardrails)
- P2 - Epic 7: Geopolitical and Macro Impact Radar (event impact + regime flags)
- P2 - Epic 9: Decision Journal and Learning Loop (feedback from outcomes)

## Sprint objective baseline (1-week cadence)
- Sprint objective style:
  - one user-visible decision workflow per sprint.
  - done only if backend+frontend+cache+evidence are integrated.

- Sprint 1 target:
  - "Decision cards live": deliver reliable forecast cards for MVP universe with <=10 min freshness.

- Sprint 2 target:
  - "Consensus live": enable multi-model + judge output in decision cards and ask flow.

- Sprint 3 target:
  - "Daily workflow live": complete 2-3 click daily brief and portfolio action summary.

## Changelog
- 2026-02-26 America/New_York - Initial vision clarified from direct user answers and defaults for missing constraints.
- 2026-02-26 America/New_York - Added expansion epics for macro radar, cost governance, and learning loop continuity.
- 2026-02-26 America/New_York - Added basic-ready expansion epics for ingestion reliability, UX/settings, alerts, operations hardening, and release go-live.
- 2026-02-26 America/New_York - Added explicit P0 data-driven forecasting core epic to ensure predictions are model/data based.
