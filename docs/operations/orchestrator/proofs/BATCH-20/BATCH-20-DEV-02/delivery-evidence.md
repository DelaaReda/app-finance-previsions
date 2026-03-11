# BATCH-20-DEV-02 — Personal Policy Guardrails [DEV-02]

**Task ID:** BATCH-20-DEV-02  
**Task Title:** Personal Policy Guardrails  
**Stream:** BATCH-20  
**Priority:** P1  
**Dependencies:** BATCH-20-DEV-01 (✅ satisfied)  

---

## Summary

Minimal vertical slice implementing personal policy guardrails for investment recommendations. Policy-violating recommendations are automatically downgraded (BUY → HOLD) with violation badges for UI display.

---

## Delivery Evidence

### Artifact

**Frontend Components (B20-T2):**
- `apps/web/src/domains/forecasts/components/widgets/personal-policy-editor.html` - Policy editor widget
- `apps/web/src/domains/forecasts/components/widgets/violation-badge.html` - Reusable violation badge component

**Backend API:**
- `apps/api/src/domains/forecasts/api/forecasts.py` - Added endpoints:
  - `GET /forecasts/policy-validator/user-policy` - Load user policy
  - `POST /forecasts/policy-validator/user-policy` - Save user policy
  - `POST /forecasts/policy-validator/validate` - Validate recommendations (existing, enhanced)

**Tests:**
- `apps/api/src/domains/forecasts/tests/test_policy_validator_api.py` - 12 integration tests (all passing)

### Verify

**Before:**
- No policy editor UI for users to configure investment guardrails
- No violation badges on recommendation cards
- Policy validation existed only in judge endpoint service

**After:**
- Policy editor widget with:
  - Quick settings (excluded tickers, blocked actions, max risk level)
  - Custom policy rules (sector exclusion, risk limits, ESG, geographic)
  - Violation statistics dashboard
- Violation badge component with severity levels and override workflow
- Backend API for policy load/save with localStorage fallback
- 12 passing integration tests

**Test Command:**
```bash
python3 -m pytest apps/api/src/domains/forecasts/tests/test_policy_validator_api.py -v
# Result: 12 passed in 1.09s
```

### Files Touched

- `apps/api/src/domains/forecasts/api/forecasts.py` (+94 lines)
- `apps/api/src/domains/forecasts/tests/test_policy_validator_api.py` (new, 393 lines)
- `apps/web/src/domains/forecasts/components/widgets/personal-policy-editor.html` (new, 904 lines)
- `apps/web/src/domains/forecasts/components/widgets/violation-badge.html` (new, 413 lines)

**Total:** 4 files changed, 1798 insertions(+), 6 deletions(-)

### Tests Run

```
test_list_policy_types ✅
test_get_policy_template_sector_exclusion ✅
test_get_policy_template_risk_concentration ✅
test_get_user_policy_empty ✅
test_save_and_get_user_policy ✅
test_validate_recommendation_no_violations ✅
test_validate_recommendation_sector_violation ✅
test_validate_recommendation_risk_violation ✅
test_validate_recommendation_multiple_violations ✅
test_validate_recommendation_excluded_ticker ✅
test_validate_recommendation_error_handling ✅
test_save_invalid_policy_format ✅
```

**Result:** 12 passed in 1.09s

### Commit SHA

```
e962b6a745122f9dfb45b35caf4d3ad06d8394e9
```

**Commit Message:**
```
feat(batch-20-dev-02): Personal Policy Guardrails - minimal vertical slice
```

---

## Architecture Check

**Layer:** Application (policy validator service) + API (forecasts routes) + UI (widgets)

**Imports OK:**
- Reused existing `storage.io` for persistence
- Reused existing forecast widget patterns
- Reused existing violation handling patterns from judge endpoint

**Path Target:**
- `apps/api/src/domains/forecasts/` - Backend API
- `apps/web/src/domains/forecasts/components/widgets/` - Frontend components

**Integration Points:**
- Judge endpoint service already has `_apply_personal_policy_guardrails()` 
- This DEV-02 adds the UI layer (B20-T2) + API endpoints for policy management
- Policy validator service (DEV-01) provides validation logic

---

## Vision Alignment

**Batch:** BATCH-20 - Personal Policy Guardrails

**Target:** Personal Policy Guardrails [DEV-02]

**Impact:**
- Establishes frontend UI for policy configuration (B20-T2)
- Provides violation badges for recommendation cards
- Enables users to set investment guardrails:
  - Excluded tickers (auto-downgrade to HOLD)
  - Blocked actions (buy/sell/hold)
  - Maximum risk level (low/medium/high/critical)
  - Custom rules (sector exclusion, ESG, geographic, position size)

**Acceptance Criteria Met:**
- ✅ Policy violating recommendation never appears as plain BUY (downgraded to HOLD with violation badge)
- ✅ Policy revisions are versioned with timestamp (`updated_at` field, schema versioning)

---

## Implementation Notes

### Reuse Strategy (per task notes)
Following `INTEGRATION-APP-EENGINEER-RECOMMENDATIONS`:
- Reused existing widget patterns from `apps/web/src/domains/forecasts/components/widgets/`
  - `strategy-playbooks.html` - Filter bar pattern
  - `portfolio-health.html` - Widget card structure
- Reused shared UI wiring from settings modal (policy configuration fields)
- Reused violation badge patterns from existing alert/warning components

### Minimal Vertical Slice
- Focused on B20-T2 (frontend widget + violation badge)
- Backend API endpoints for policy load/save
- Integration with existing policy validator service
- Did NOT implement:
  - Policy editor modal (used inline widget)
  - Advanced policy rule builder (used simple config fields)
  - Real-time sync (used localStorage cache + backend persistence)

### Test Coverage
- 12 integration tests covering:
  - Policy types and templates
  - User policy CRUD operations
  - Recommendation validation with various violation scenarios
  - Error handling and edge cases

---

## Next Steps (for Planner)

**Remaining BATCH-20 Tasks:**
- B20-T3 (QA): Hard stop and downgrade tests - partially covered by DEV-02 tests
- B20-T4 (Planner): Override decision workflow - violation badge has override button, needs workflow

**Dependencies for BATCH-21:**
- ✅ Policy guardrails in place for execution journal
- ✅ Violation tracking for audit trail

---

*Generated by dev agent for BATCH-20-DEV-02 delivery verification*  
*Timestamp: 2026-03-11*
