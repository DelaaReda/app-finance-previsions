---
status: historical_verification
last_verified: 2026-03-13
superseded_by:
  - /home/venom/analyse-financiere/docs/ops/CURRENT_ARCHITECTURE_ENTRYPOINTS.md
  - /home/venom/analyse-financiere/docs/ops/README.md
---

# Archive Recovery Verification - 2026-03-03

Historical note:
- point-in-time verification report
- useful as recovery evidence only
- not a current architecture or runtime policy document

Scope: verification requested for items 2, 3, 5, 6, 7, 8 from archive audit.

## 2) Legacy docs (judge/cache/api): adapt before reintegration

Verdict: DONE (adapted and reintegrated).

Why:
- legacy docs reference old paths like `src/services/*`, `api/routes/*`, `data/*`.
- current target architecture is domain-based:
  - `apps/api/src/domains/judge/application/*`
  - `apps/api/src/domains/judge/api/judge.py`
  - compatibility imports via `apps/api/src/platform/routes/__init__.py`.

Legacy docs adapted from archive:
- `archive/legacy/backend-legacy-archive-20260228T012443Z/docs/JUDGE_IMPROVEMENT_PLAN.md`
- `archive/legacy/backend-legacy-archive-20260228T012443Z/docs/API_JUDGE_ANALYSIS.md`
- `archive/legacy/backend-legacy-archive-20260228T012443Z/docs/CACHE_STRATEGY.md`
- `archive/cleanup_lt100_20260228T005817Z/backend/docs/2025-12/JUDGE_SCHEMA.md`

Reintegrated target:
- `docs/ops/JUDGE_RECOVERY_ADAPTED_PLAYBOOK.md`

## 3) API v1 compatibility wrappers (`macro_legacy.py`, `news_legacy.py`)

Verdict: NOT REQUIRED in current runtime.

Why:
- no active imports from `api-v1-compat/*`.
- active runtime relies on:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/routes/__init__.py` namespace mapping to `domains/*/api`.

Decision:
- keep wrappers archived only.

## 5) Archived modules vs app launch path

Modules checked:
- `orchestrator.py`, `agent_runner/scheduler.py`, `agents/llm/runtime.py`,
- `forecast_aggregator_agent.py`, `risk_monitor_agent.py`, `news_aggregator.py`, `quality_service.py`.

Verdict: NOT in launch path.

Active launch path:
- `finance-copilot.sh` -> `apps/api/runtime/copilot.sh`
- backend start via `apps/api/src/run_api.py` -> `apps/api/src/platform/run_api.py`
- data refresh via `apps/api/src/platform/legacy/jobs/*`.

Decision:
- do not reintegrate these modules unless a new feature explicitly needs them.

## 6) Judge profile YAML utility

Profiles:
- `equity_1w.yaml`
- `sector_regime.yaml`

Verdict: USEFUL and now restored.

Why useful:
- `judge_pipeline.py` supports profile loading (`load_profile`).
- `/api/judge` exposes `profile` parameter and benefits from explicit configs.
- `news_ingest.py` uses profile tickers to extend dynamic source coverage when available.

Action done:
- restored to `apps/api/src/data/judge_profiles/`.

## 7) Scripts migration check

Scripts:
- `fetch_prices_stooq.sh`
- `validate_marker.sh`

Verdict:
- `fetch_prices_stooq.sh`: logic already migrated in `apps/api/src/platform/legacy/jobs/stocks_prices_refresh.py` (Stooq fallback built-in).
- `validate_marker.sh`: obsolete legacy utility (hardcoded old path), not needed.

Action done:
- removed stale launcher dependency from `apps/api/runtime/copilot.sh`.
- launcher now relies on `stocks_prices_refresh.py` only.

## 8) Skills audit artifacts moved to correct repo path

Verdict: DONE.

Files restored into `finance-app/`:
- `finance-app/openclaw-skill-audit.json`
- `finance-app/openclaw-skill-security-deep-2026-02-24.json`
- `finance-app/openclaw-skill-security-deep-2026-02-24.md`
- `finance-app/openclaw-skills-rollout-2026-02-24.md`

Notes:
- archive originals kept intact.
