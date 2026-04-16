# BATCH-96-DEV-01 Proof

- Task: `show what changed today and what matters now [DEV-01]`
- Scope: harden the `copilot`/`personal-finance` start-route contract around scope-first open actions and fallback behavior.

## Root Cause

- The route-level fallback path could discard an already usable endpoint payload after a retry path, degrading contract evidence.
- Contract tests still encoded pre-scope-first expectations for open actions, ranked actions, and fallback metadata.

## Fix Applied

- Preserve the fallback-ready endpoint payload in `apps/api/src/domains/copilot/api/copilot.py` when rescue/context rebuild does not improve the response.
- Update targeted route contract tests to match the canonical sorted ticker behavior and the currently exposed fallback payload shape.

## Verification

- Command:
  - `PYTHONPATH=apps/api/src python3 -m pytest -q apps/api/src/domains/copilot/tests/test_dev01_delivery_proof.py apps/api/src/domains/copilot/tests/test_copilot_context_route_fallback.py apps/api/src/domains/copilot/tests/test_copilot_domain_router.py`
- Result:
  - `30 passed`
- Public EC2 spot-check:
  - `/api/copilot/start?tickers=NVDA&tickers=MSFT` returns `ranked_action.id=open_msft`
  - `/api/personal-finance/start?tickers=NVDA&tickers=MSFT` returns `open_targets=["ticker:MSFT","ticker:NVDA","market","opportunities","/personal-finance"]`
