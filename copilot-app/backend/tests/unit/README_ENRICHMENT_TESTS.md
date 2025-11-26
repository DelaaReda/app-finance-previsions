# Unit Tests - Phase 1 Enrichments

**Status:** Test structure complete, waiting for implementations

## Test Files

### `test_enrichment.py`
Tests for Phase 1 data enrichments:
- Fusion score calculation
- Tech enrichment (with freshness validation)
- Fundamental minimal (yfinance live)

**Lines:** 370  
**Tests:** 17 (currently skipped)  
**Coverage:** Fusion (6 tests), Tech (5 tests), Fundamental (4 tests), Integration (2 tests)

## Running Tests

```bash
# All enrichment tests
pytest tests/unit/test_enrichment.py -v

# Specific test class
pytest tests/unit/test_enrichment.py::TestFusionScore -v

# Specific test
pytest tests/unit/test_enrichment.py::TestFusionScore::test_fusion_basic -v

# By keyword
pytest tests/unit/test_enrichment.py -k "fusion" -v

# Show skipped tests
pytest tests/unit/test_enrichment.py -v -rs
```

## Test Activation

Tests are currently **skipped** with `pytest.skip()` waiting for Codex implementations.

**To activate:**
1. Codex implements function (e.g., `compute_fusion_score()`)
2. Claude uncomments corresponding tests
3. Run pytest to validate
4. Fix any issues
5. Move to next function

## Test Coverage

### Fusion Score (6 tests)
- ✓ Basic calculation (score, conviction, dominant_signal)
- ✓ Dominant signal detection (highest phase)
- ✓ High conviction (scores agree)
- ✓ Low conviction (scores diverge)
- ✓ Missing phases handling
- ✓ No valid scores error

### Tech Enriched (5 tests)
- ✓ Fresh judge_features usage
- ✓ Stale detection (>24h) → ValueError
- ✓ Missing ticker → ValueError
- ✓ Live calculation fallback
- ✓ No timestamp handling

### Fundamental Minimal (4 tests)
- ✓ Basic yfinance fetch
- ✓ Valuation signals (cheap/fair/expensive based on P/E)
- ✓ Error handling (invalid ticker, yfinance failure)
- ✓ Missing fields (graceful degradation)

### Integration (2 tests)
- ✓ Full pipeline (all 3 enrichments)
- ✓ Latency measurement (target: <1000ms)

### Parametrized Tests
- ✓ Multiple tickers (AAPL, MSFT, GOOGL)
- ✓ Freshness boundaries (1h, 12h, 23h, 25h, 48h)

## Helper Functions

```python
create_fresh_timestamp(hours_ago=0)
# → ISO timestamp for freshness testing

create_test_phases(scores={...})
# → Test phase data with scores

create_test_judge_features(ticker, hours_ago=1)
# → Test judge_features with timestamp
```

## Expected Results After Implementation

```
tests/unit/test_enrichment.py::TestFusionScore::test_fusion_basic PASSED
tests/unit/test_enrichment.py::TestFusionScore::test_fusion_dominant_signal PASSED
tests/unit/test_enrichment.py::TestFusionScore::test_fusion_high_conviction PASSED
tests/unit/test_enrichment.py::TestFusionScore::test_fusion_low_conviction PASSED
tests/unit/test_enrichment.py::TestFusionScore::test_fusion_missing_phases PASSED
tests/unit/test_enrichment.py::TestFusionScore::test_fusion_no_scores PASSED

tests/unit/test_enrichment.py::TestTechEnriched::test_tech_from_fresh_features PASSED
tests/unit/test_enrichment.py::TestTechEnriched::test_tech_stale_features_fails PASSED
tests/unit/test_enrichment.py::TestTechEnriched::test_tech_missing_ticker PASSED
tests/unit/test_enrichment.py::TestTechEnriched::test_tech_live_fallback PASSED
tests/unit/test_enrichment.py::TestTechEnriched::test_tech_no_timestamp PASSED

tests/unit/test_enrichment.py::TestFundamentalMinimal::test_fundamental_basic PASSED
tests/unit/test_enrichment.py::TestFundamentalMinimal::test_fundamental_valuation_signals PASSED
tests/unit/test_enrichment.py::TestFundamentalMinimal::test_fundamental_error_handling PASSED
tests/unit/test_enrichment.py::TestFundamentalMinimal::test_fundamental_missing_fields PASSED

tests/unit/test_enrichment.py::TestEnrichmentIntegration::test_full_enrichment_pipeline PASSED
tests/unit/test_enrichment.py::TestEnrichmentIntegration::test_enrichment_latency PASSED

======================== 17 passed in 2.5s ========================
```

## Coordination with Codex

**Claude's responsibility:**
- ✅ Test structure created
- ⏳ Activate tests as functions are implemented
- ⏳ Run pytest and report results
- ⏳ Add edge case tests if needed

**Codex's responsibility:**
- ⏳ Implement `compute_fusion_score()`
- ⏳ Implement `get_tech_enriched()`
- ⏳ Implement `get_fundamental_minimal()`
- ⏳ Signal when ready for test activation

**Process:**
1. Codex implements function
2. Codex updates plan: "Task X.Y complete"
3. Claude uncomments tests for that function
4. Claude runs pytest
5. Claude reports: PASS or issues found
6. Fix issues if any
7. Move to next function

## Current Status

```
TestFusionScore:          ⏸️  WAITING (6 tests ready)
TestTechEnriched:         ⏸️  WAITING (5 tests ready)
TestFundamentalMinimal:   ⏸️  WAITING (4 tests ready)
Integration:              ⏸️  WAITING (2 tests ready)
```

**Ready to activate as soon as implementations are complete! 🚀**
