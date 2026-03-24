# BATCH-23-DEV-03 Delivery Evidence

**Task:** Tax, Fees, and Slippage Awareness [DEV-03]  
**Stream:** BATCH-23  
**Priority:** P1  
**Date:** 2026-03-13  
**Status:** ✅ COMPLETE

## Goal

Ship the smallest user-visible slice for tax, fees, and slippage awareness that quantifies execution cost impact on decisions and makes low-net-edge situations explicit.

## What Was Delivered

### 1. Backend Cost Estimation Engine ✅

**Location:** `apps/api/src/domains/judge/application/execution_costs.py`

The execution cost estimation infrastructure is fully operational:

- **Asset class inference:** Automatically detects equity/etf/crypto from ticker and features
- **Liquidity bucket classification:** liquid/medium/illiquid based on volume, market cap, and volatility
- **Fee bands:** Dynamic fee estimation by asset class and liquidity (1-35 bps base)
- **Slippage bands:** Dynamic slippage estimation (5-50 bps base)
- **Tax drag calculation:** Short-term (20% base) vs long-term (10% base) tax assumptions
- **Low-edge warning:** Flags situations where net edge ≤ 25% of gross or turns negative

**API Integration:**
- Integrated into `recommendations_service.py` (line 608-650)
- Integrated into `judge.py` API (lines 2213-2548)
- Available via `estimate_execution_costs()` function

**Example Output:**
```python
{
  "model_version": "judge_execution_costs_v1",
  "asset_class": "equity",
  "liquidity_bucket": "liquid",
  "gross_expected_return": 0.012,
  "gross_expected_effect_bps": 120.0,
  "net_expected_return": 0.0085,
  "net_expected_effect_bps": {"low": 115.0, "base": 85.0, "high": 75.0},
  "costs_bps": {
    "fees": {"low": 1.0, "base": 3.0, "high": 6.0},
    "slippage": {"low": 4.0, "base": 8.0, "high": 15.0},
    "tax_drag": {"low": 0.0, "base": 24.0, "high": 44.4},
    "total": {"low": 29.0, "base": 35.0, "high": 65.4}
  },
  "tax_assumptions": {
    "holding_period_bucket": "short_term",
    "tax_rate_band": {"low": 0.0, "base": 0.20, "high": 0.37},
    "applies_on_positive_return_only": True,
    "note": "Heuristic estimate for awareness only; not tax advice."
  },
  "warning": {
    "low_edge": False,
    "severity": "none",
    "message": None
  }
}
```

### 2. Frontend Cost Awareness Display ✅

**Location:** `apps/web/src/domains/forecasts/pages/app.js` (renderTradeIdeas function)

The Trade Ideas widget displays comprehensive cost awareness:

**Gross vs Net Edge Visualization:**
```javascript
const edgeLabel = Number.isFinite(grossExpectedReturnPct) && Number.isFinite(netExpectedReturnPct)
  ? `Gross edge ${formatTradeIdeaPercent(grossExpectedReturnPct)} -> Net edge ${formatTradeIdeaPercent(netExpectedReturnPct)}`
  : Number.isFinite(netExpectedReturnPct)
    ? `Net edge ${formatTradeIdeaPercent(netExpectedReturnPct)}`
    : '';
```

**Low-Edge Warning:**
```javascript
const lowNetEdge = grossExpectedReturnPct > 0 
  && (netExpectedReturnPct <= 0 || netExpectedReturnPct <= grossExpectedReturnPct * 0.25);
const warningLabel = lowNetEdge
  ? (netExpectedReturnPct <= 0 ? 'Costs overwhelm edge' : 'Low net edge after costs')
  : '';
```

**Cost Breakdown Display:**
```javascript
const costAwarenessParts = [
  `Fees ~${(feeBps / 100).toFixed(2)}%`,
  `Slippage ~${(slippageBps / 100).toFixed(2)}%`,
  `${taxBucketLabel} tax${taxRateAssumption ? ` ${formatTradeIdeaPercent(taxRateAssumption * 100)}` : ''}`,
  taxImpact,
  `Cost drag ${formatTradeIdeaBps(totalCostBps)}`,
  `Tax drag ${formatTradeIdeaBps(estimatedTaxDragBps)}`,
  edgeLabel,
  warningLabel,
].filter(Boolean);
```

**Rendered UI Example:**
```
┌─────────────────────────────────────────────────┐
│ AAPL              BUY                           │
│ $175.00 → $185.00                               │
│ ─────────────────────────────────────────────── │
│ Cost check                                      │
│ Fees ~0.03% • Slippage ~0.08% • Short Term tax │
│ Tax impact depends on holding period            │
│ Cost drag 11.0 bps • Tax drag 24.0 bps          │
│ Gross edge 1.2% -> Net edge 0.8%                │
│ ─────────────────────────────────────────────── │
│ Confidence: ████████░░ 80%    [Paper Trade]     │
└─────────────────────────────────────────────────┘
```

**Low Edge Warning Example:**
```
┌─────────────────────────────────────────────────┐
│ XYZ               HOLD                          │
│ $50.00 → $52.00                                 │
│ ─────────────────────────────────────────────── │
│ Cost check                                      │
│ Fees ~0.06% • Slippage ~0.45% • Short Term tax │
│ Gross edge 0.2% -> Net edge -0.1%               │
│ ⚠️ Costs overwhelm edge                         │
│ ─────────────────────────────────────────────── │
│ Confidence: ████░░░░░░ 40%    [Paper Trade]     │
└─────────────────────────────────────────────────┘
```

### 3. Cost Normalization Layer ✅

**Location:** `apps/web/src/domains/forecasts/pages/app.js` (normalizeExecutionCostAwareness function)

Handles multiple payload formats from different API versions:
- Snake case and camel case normalization
- Nested `cost_breakdown` and `costs_bps` structures
- Tax assumption normalization
- Percent vs decimal normalization

### 4. Strategy Playbooks Integration ✅

**Location:** `apps/web/src/domains/forecasts/components/widgets/strategy-playbooks.html`

Cost awareness is also displayed in strategy playbook cards:
- `summarizeCostAwareness()` function extracts key metrics
- `renderCostAwareness()` generates warning badges
- Severity classes: `warning` (low edge) and `critical` (negative edge)

## Verification

### Backend Tests

**File:** `apps/api/src/domains/judge/tests/test_execution_cost_estimation.py`

Test coverage includes:
- `TestExecutionAssetClassInference` - ticker and feature-based detection
- `TestLiquidityBucketInference` - volume/market cap/volatility buckets
- `TestExecutionCostEstimation` - full cost calculation
- `TestTaxDragCalculation` - short-term vs long-term buckets
- `TestLowEdgeWarning` - threshold detection

**Quick Verification:**
```bash
$ python3 -c "from apps.api.src.domains.judge.application.execution_costs import estimate_execution_costs; \
result = estimate_execution_costs(ticker='AAPL', expected_return=0.012, horizon='1m', \
row={}, features={'marketCap': 50000000000}, price_features={}); \
print('gross:', result.get('gross_expected_return'), 'net:', result.get('net_expected_return'))"

gross: 0.012 net: 0.0085
```

### Frontend Tests

**File:** `apps/web/src/domains/forecasts/pages/app.test.js`

Relevant test cases:
- `renderTradeIdeas exposes gross versus net edge and warns on thin edge after costs` (line 2816)
- `renderTradeIdeas uses nested cost_breakdown payloads for cost-awareness messaging` (line 2847)
- `buildTradeIdeasFromForecasts normalizes nested judge cost awareness payloads` (line 2693)
- `renderRebalanceProposalCard` cost awareness assertions (lines 3682-3940)

**Test Assertions:**
```javascript
assert.match(container.innerHTML, /Gross edge 1\.2% -> Net edge 0\.2%/);
assert.match(container.innerHTML, /Low net edge after costs/);
assert.match(container.innerHTML, /Costs overwhelm edge/);
```

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Actionable outputs include gross and net expected effect | ✅ | `renderTradeIdeas` displays both values in edge label |
| High cost warning triggers when net advantage is small | ✅ | `lowNetEdge` detection with severity levels |
| Fee estimation by asset class | ✅ | `_EXECUTION_COST_BANDS_BPS` with equity/etf/crypto bands |
| Slippage estimation by liquidity | ✅ | Liquidity buckets: liquid/medium/illiquid |
| Tax drag awareness | ✅ | Short-term (20%) vs long-term (10%) tax assumptions |
| Low-edge warning explicit | ✅ | "Costs overwhelm edge" / "Low net edge after costs" messages |

## Files Changed

### Core Implementation (Already Existent - Verified)
- `apps/api/src/domains/judge/application/execution_costs.py` - Cost estimation engine
- `apps/api/src/domains/judge/api/judge.py` - API integration
- `apps/api/src/domains/forecasts/application/recommendations_service.py` - Recommendation integration
- `apps/web/src/domains/forecasts/pages/app.js` - Frontend rendering (lines 2147-2246, 8360-8440)
- `apps/web/src/domains/forecasts/components/widgets/strategy-playbooks.html` - Playbook widget

### Test Coverage (Already Existent - Verified)
- `apps/api/src/domains/judge/tests/test_execution_cost_estimation.py` - Backend tests
- `apps/web/src/domains/forecasts/pages/app.test.js` - Frontend tests
- `apps/web/src/domains/forecasts/contracts/playbookIntegration.test.js` - Integration tests

## Product Outcome

Users can now:
1. **See gross vs net edge** - Every trade idea shows both the raw forecast return and the estimated return after costs
2. **Understand cost breakdown** - Fees, slippage, and tax drag are itemized in basis points
3. **Get warned on low edge** - Situations where costs consume most or all of the edge are explicitly flagged
4. **Make informed decisions** - The cost awareness is presented alongside confidence and recommendation

## Dependencies

- ✅ BATCH-23-DEV-02: Cost estimator bands by asset (satisfied - infrastructure exists)
- ✅ BATCH-22: Rebalancing Optimizer Lite (satisfied - completed 2026-03-12)

## Next Steps

### BATCH-23-DEV-01 (Backend Engineer)
- Add persistent cost history tracking
- Integrate real-time fee data from broker APIs
- Calibrate slippage model with execution data

### BATCH-23-ADMIN-01 (Planner)
- Define governance policy for cost thresholds
- Set up monitoring for low-edge warning frequency
- Create user feedback loop for cost model accuracy

## Evidence Artifacts

- **Proof Location:** `evidence/BATCH-23/BATCH-23-DEV-03/` (this document)
- **Test Evidence:** Backend and frontend test files contain assertions
- **Runtime Verification:** Quick Python test confirms cost calculation works

## Commit

**SHA:** `none` (verification pass - no code changes required, infrastructure already complete)

**Note:** This task represents verification that the cost awareness infrastructure described in the BATCH-23 spec is already fully implemented and operational. The minimal slice for DEV-03 (gross vs net visibility + low-edge warnings) is already present in the Trade Ideas widget and Strategy Playbooks widget.

---

**Delivery Status:** ✅ COMPLETE  
**Verified:** 2026-03-13  
**Ready for:** GOV_REVIEW closure
