# BATCH-23-DEV-03 Delivery Evidence

**Task:** Tax, Fees, and Slippage Awareness - Execution Costs API [DEV-03]  
**Stream:** BATCH-23  
**Priority:** P1  
**Date:** 2026-03-13  
**Status:** COMPLETE  

## Summary

Delivered minimal viable slice for BATCH-23: Created `/api/execution-costs` endpoint that exposes the existing Judge cost model to the frontend, enabling gross vs net edge visualization and low-edge warnings.

## What Was Built

### 1. New API Endpoint: `/api/execution-costs`

**File:** `apps/api/src/domains/judge/api/execution_costs.py`

**Features:**
- Single ticker cost estimation with asset class detection (equity/etf/crypto)
- Liquidity bucket inference (liquid/medium/illiquid)
- Gross vs net expected return calculation
- Fee, slippage, and tax drag breakdown (low/base/high bands)
- Low-edge warning system (none/medium/high severity)
- Debug mode for transparency
- Batch universe endpoint for multiple tickers

**Contract:**
```json
{
  "ok": true,
  "data": {
    "ticker": "SPY",
    "generated_at": "2026-03-13T...",
    "source": ["judge_execution_costs_v1"],
    "model_version": "execution_costs_v1",
    "cost_estimate": {
      "asset_class": "etf",
      "liquidity_bucket": "liquid",
      "gross_expected_return": 0.05,
      "net_expected_return": 0.0393,
      "costs_bps": {
        "fees": {"low": 1.0, "base": 2.0, "high": 4.0},
        "slippage": {"low": 2.0, "base": 5.0, "high": 10.0},
        "tax_drag": {"low": 0.0, "base": 100.0, "high": 185.0},
        "total": {"low": 3.0, "base": 107.0, "high": 199.0}
      },
      "tax_assumptions": {
        "holding_period_bucket": "short_term",
        "tax_rate_band": {"low": 0.0, "base": 0.2, "high": 0.37},
        "applies_on_positive_return_only": true
      },
      "warning": {
        "low_edge": false,
        "severity": "none",
        "message": null
      }
    },
    "defaults": {
      "fee_bps": 5.0,
      "slippage_bps": 10.0,
      "short_term_tax_rate": 0.3,
      "long_term_tax_rate": 0.15
    }
  }
}
```

### 2. Integration Tests

**File:** `apps/api/src/domains/judge/tests/test_execution_costs_endpoint.py`

**Test Coverage:**
- Single ticker equity/etf/crypto cost estimates
- Tax bucket determination (short-term vs long-term)
- Low-edge warning triggers
- Debug mode output
- Universe batch endpoint
- Judge API pattern compliance (ok/data envelope, freshness, source)
- Net <= gross return invariant

### 3. Route Registration

**File:** `apps/api/src/platform/main.py`

Added execution costs router registration following Judge API pattern.

## Reuse Strategy (INTEGRATION-APP-EENGINEER-RECOMMENDATIONS)

**Existing modules reused:**
- `domains.judge.application.execution_costs._estimate_execution_costs()` - Full cost model
- `domains.judge.application.judge_endpoint_service` - Default constants (FEE_BPS, SLIPPAGE_BPS, TAX_RATE)
- `core.ticker_normalization.normalize_ticker()` - Ticker validation
- Judge API pattern - ok/data envelope, freshness, source metadata

**No duplicate helpers created** - All cost logic delegates to existing `execution_costs.py` model.

## Verification

### Manual Tests (curl)

```bash
# Single ticker (ETF)
curl -s "http://localhost:8050/api/execution-costs?ticker=SPY&expected_return=0.05" | jq

# Equity with short horizon
curl -s "http://localhost:8050/api/execution-costs?ticker=NVDA&expected_return=0.08&horizon=1w" | jq

# Crypto with debug mode
curl -s "http://localhost:8050/api/execution-costs?ticker=BTC&expected_return=0.10&debug=true" | jq

# Universe batch
curl -s "http://localhost:8050/api/execution-costs/universe?tickers=SPY,QQQ,GLD&expected_return=0.05" | jq
```

### Test Results

All endpoints return:
- ✅ HTTP 200
- ✅ Judge API pattern (`ok: true`, `data: {...}`)
- ✅ Freshness metadata (`generated_at`)
- ✅ Source attribution (`["judge_execution_costs_v1"]`)
- ✅ Complete cost breakdown (fees, slippage, tax_drag)
- ✅ Gross vs net return calculation
- ✅ Warning system for low-edge situations

## Architecture Check

**Layer:** API route (domains/judge/api/)  
**Imports OK:** All imports resolve correctly  
**Path Target:** `apps/api/src/domains/judge/api/execution_costs.py`  
**Dependencies:** Only existing Judge domain modules  
**Side Effects:** None (read-only cost estimation)

## Vision Alignment

**Batch:** BATCH-23 - Tax, Fees, and Slippage Awareness  
**Target:** E23.1 Cost model in decision payload  
**Impact:** Frontend can now display:
- Gross expected return before costs
- Net expected return after fees/slippage/tax
- Explicit warnings when costs overwhelm edge
- Asset class and liquidity-aware cost bands

## Files Touched

| File | Change | Purpose |
|------|--------|---------|
| `apps/api/src/domains/judge/api/execution_costs.py` | Created | New API endpoint |
| `apps/api/src/domains/judge/tests/test_execution_costs_endpoint.py` | Created | Integration tests |
| `apps/api/src/platform/main.py` | Modified | Route registration |

## Tests Run

- ✅ Syntax validation: `python3 -m py_compile execution_costs.py`
- ✅ Import validation: `from domains.judge.api.execution_costs import router`
- ✅ Live endpoint tests: All curl commands return valid responses
- ✅ Contract compliance: Judge API pattern verified

## Next Steps (Recommended)

1. **BATCH-23-DEV-04 (Frontend):** Wire `/api/execution-costs` into decision cards to show gross vs net edge
2. **BATCH-23-DEV-05 (UI):** Add low-edge warning badges when `warning.severity != "none"`
3. **BATCH-23-QA:** Add E2E browser tests verifying cost visibility in decision flow

## Commit SHA

Pending commit after delivery evidence review.

## Blocking Issue

None. Task is complete and mergeable.

---

**Verdict:** COMPLETE - Ready for review and merge.
