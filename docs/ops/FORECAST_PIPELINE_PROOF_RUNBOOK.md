---
status: canonical
last_verified: 2026-03-07
---

# Forecast Pipeline Proof Runbook

Use this runbook to prove that the current forecasts pipeline is wired correctly end to end.

This runbook uses current repo paths only.

## Scope
This proof path answers five questions:
- Can we trigger or refresh the current forecasts path?
- Does the runtime snapshot persist in the canonical storage root?
- Does `/api/forecasts` return a healthy nominal contract?
- Do doctor and monitor agree on the product signal?
- Do we have enough evidence to call the pipeline healthy?

## Canonical paths
- Manual refresh helper: [dev_tools.sh](/home/venom/analyse-financiere/scripts/dev_tools.sh)
- API entrypoint: [main.py](/home/venom/analyse-financiere/apps/api/src/platform/main.py)
- Forecast service: [forecasts_service.py](/home/venom/analyse-financiere/apps/api/src/domains/forecasts/application/forecasts_service.py)
- Product guard: [product_priority_guard.py](/home/venom/analyse-financiere/platform/automation/product_priority_guard.py)
- Doctor CLI: [fc_doctor.sh](/home/venom/analyse-financiere/scripts/fc_doctor.sh)
- Canonical runtime storage root: `apps/api/runtime/data/`
- Compatibility alias: `data/ -> apps/api/runtime/data/`

## Preconditions
- Run from the VM workspace only: `/home/venom/analyse-financiere`
- Backend/monitor available if you want live API proof
- Local env files stay in place; do not rewrite or remove `.env` files during this check

## Step 1 — Trigger the current refresh path
Quick manual refresh:

```bash
bash scripts/dev_tools.sh refresh-data
```

What this currently does:
- runs the manual forecasts refresh helper
- runs one news ingestion pass

This is an operator proof step, not the definition of the nominal API contract by itself.

## Step 2 — Verify persisted output
Check the canonical runtime snapshot:

```bash
ls -l apps/api/runtime/data/forecasts.json
ls -l data/forecasts.json
```

Expected:
- `apps/api/runtime/data/forecasts.json` exists
- `data/forecasts.json` resolves through the compatibility alias
- file timestamp is recent enough for the current verification window

## Step 3 — Verify the API contract
Check the live forecasts contract:

```bash
curl -s 'http://127.0.0.1:8050/api/forecasts?limit=5' | jq
```

Nominal healthy contract expectations:
- `fallback_used = false`
- `freshness_status = "fresh"`
- `rows` is non-empty
- `source` / `provider_chain` does not indicate pseudo/simple/fallback nominal mode

Degraded but explicit mode is allowed only when the system really cannot produce the nominal path. In that case the payload must say so clearly.

## Step 4 — Verify doctor and monitor
Doctor:

```bash
bash scripts/fc_doctor.sh --refresh
```

Monitor:

```bash
curl -s 'http://127.0.0.1:7779/api/status' | jq
curl -s 'http://127.0.0.1:7779/api/doctor?refresh=1' | jq
```

Expected healthy signals:
- doctor product checks report `forecasts.status = ok`
- monitor product metrics report forecasts healthy, not invalid/fallback-only
- no contradiction between status and doctor after refresh

## Step 5 — Record proof
Minimum acceptable proof bundle:
- timestamp of the refresh attempt
- file proof for `apps/api/runtime/data/forecasts.json`
- `/api/forecasts?limit=5` payload excerpt proving nominal contract health
- doctor excerpt proving `forecasts.status = ok`
- monitor excerpt proving the same product signal

## Failure interpretation
- Storage missing or stale: pipeline did not persist correctly
- API returns fallback/simple markers as nominal output: forecast contract is degraded
- Doctor says degraded while API looks healthy: guard/contract mismatch
- Monitor disagrees with doctor after refresh: observability inconsistency, not product health

## Notes
- The canonical runtime data root is `apps/api/runtime/data/`; `data/` is a compatibility alias.
- This runbook validates the current pipeline as implemented; it does not bless historical forecast generators as the desired long-term architecture.
