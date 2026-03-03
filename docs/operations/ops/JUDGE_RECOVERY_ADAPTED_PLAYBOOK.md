# Judge Recovery Adapted Playbook (Architecture-Correct)

Date: 2026-03-03
Scope: reintegration of useful legacy guidance from archived docs, adapted to the current target architecture.

## Legacy sources reintegrated

- `archive/legacy/backend-legacy-archive-20260228T012443Z/docs/JUDGE_IMPROVEMENT_PLAN.md`
- `archive/legacy/backend-legacy-archive-20260228T012443Z/docs/API_JUDGE_ANALYSIS.md`
- `archive/legacy/backend-legacy-archive-20260228T012443Z/docs/CACHE_STRATEGY.md`
- `archive/cleanup_lt100_20260228T005817Z/backend/docs/2025-12/JUDGE_SCHEMA.md`

## Path mapping (legacy -> current)

- `copilot-app/backend/src/api/routes/judge.py` -> `apps/api/src/domains/judge/api/judge.py`
- `copilot-app/backend/src/services/judge_pipeline.py` -> `apps/api/src/domains/judge/application/judge_pipeline.py`
- `copilot-app/backend/src/services/g4f_client.py` -> `apps/api/src/domains/judge/application/g4f_client.py`
- `copilot-app/backend/src/services/judge_builder.py` -> `apps/api/src/domains/judge/application/judge_builder.py`
- `copilot-app/backend/src/schemas/judge.py` -> `apps/api/src/domains/judge/contracts/schema.py`
- `data/judge_profiles/*.yaml` -> `apps/api/src/data/judge_profiles/*.yaml` (symlinked to `apps/api/runtime/data/judge_profiles/*.yaml`)

## Current runtime entrypoints

- launcher: `finance-copilot.sh`
- runtime launcher: `apps/api/runtime/copilot.sh`
- backend start: `apps/api/src/run_api.py` -> `apps/api/src/platform/run_api.py`
- app factory: `apps/api/src/platform/main.py` -> `api.main:create_app`

## Judge API contract (current)

Endpoint:
- `GET /api/judge`

Key behavior:
- stable `ok/data` response shape
- never-empty fallback behavior on errors
- strict sort enums and request validation
- profile-aware execution (`profile=equity_1w|sector_regime|...`)
- `debug=true` for trace payloads
- `debug_full=true` only when access is explicitly enabled (`JUDGE_ALLOW_DEBUG_FULL=1`)

Contract notes:
- `verdicts_raw` appears only in full debug mode
- response model uses `response_model_exclude_none=True` on main route
- phase scores are normalized and consistent with builder logic

## Profile model (reintegrated and active)

Profiles restored:
- `apps/api/src/data/judge_profiles/equity_1w.yaml`
- `apps/api/src/data/judge_profiles/sector_regime.yaml`

Usage points:
- loaded by `apps/api/src/domains/judge/application/judge_pipeline.py::load_profile`
- consumed by `apps/api/src/domains/judge/api/judge.py`
- leveraged by `apps/api/src/platform/legacy/jobs/news_ingest.py` for dynamic source ticker expansion

Fallback behavior:
- if profile file is missing/invalid, route logs warning and continues with default behavior
- pipeline tolerates `profile=None`

## Cache strategy (adapted from legacy policy)

Current Judge route cache:
- env-controlled TTL: `JUDGE_CACHE_TTL_SECONDS` (default 120s)
- deterministic cache key includes filter/sort/profile
- debug mode bypasses cache
- single-flight compute gate prevents stampede on same key

Practical policy:
- keep short TTL for volatile verdict payloads
- do not hide stale or broken results behind silent fallback
- expose cache metadata (`hit`, `age_seconds`, `ttl_seconds`) in response payload when available

## What is intentionally not reintegrated

- old `api-v1-compat` wrappers (`macro_legacy.py`, `news_legacy.py`) because current runtime uses `platform/routes` namespace mapping
- archived UI stacks (legacy dash/streamlit app trees) because not in active runtime path

## Validation checklist

1. profile files exist:
```bash
cd apps/api/src
test -f data/judge_profiles/equity_1w.yaml
test -f data/judge_profiles/sector_regime.yaml
```

2. launcher path sanity:
```bash
bash -n apps/api/runtime/copilot.sh
```

3. endpoint smoke:
```bash
curl -s "http://localhost:8050/api/judge?limit=1&profile=equity_1w" | jq '.ok'
curl -s "http://localhost:8050/api/judge?limit=1&profile=sector_regime" | jq '.ok'
```

4. debug gating sanity:
```bash
curl -s "http://localhost:8050/api/judge?limit=1&debug=true" | jq '.data.debug_pipeline? // empty'
```

