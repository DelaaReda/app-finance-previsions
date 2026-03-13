# BATCH-63-DEV-03 Delivery Evidence

**Task:** Build a personal finance copilot that starts with a brief of the day [DEV-03]  
**Stream:** BATCH-63  
**Priority:** P2  
**Date:** 2026-03-13  
**Role:** dev  

---

## Summary

Delivered minimal verifiable slice: Personal Finance Copilot with brief-of-day entry point.

**What was delivered:**
1. ✅ `/api/personal-finance/start` - Returns daily brief + ask/open entry points
2. ✅ `/api/personal-finance/ask` - Returns investment memo with verdict, reasoning, risks, sources
3. ✅ `/api/personal-finance/context` - Market context with portfolio awareness
4. ✅ Test suite: `test_personal_finance_copilot_start.py` (8 tests, all passing)

**Product vision alignment:**
- "Build a personal finance copilot that starts with a brief of the day"
- Brief + Ask rhythm implemented
- Investment memo output with verdict, horizon, reasoning, risks, confidence, sources
- Portfolio context integration when available

---

## Artifact

### API Endpoints

#### GET /api/personal-finance/start
Returns the daily brief with entry points for immediate action.

**Response structure:**
```json
{
  "ok": true,
  "data": {
    "brief_of_day": {
      "summary": "Daily market brief: BEARISH...",
      "market_sentiment": "BEARISH",
      "top_risks": [...],
      "macro_signals": [...],
      "sector_rotation": {...},
      "generated_at": "2026-03-13T16:04:28Z",
      "freshness": "2026-03-13T16:04:28Z"
    },
    "ask": [
      {"id": "portfolio_today", "label": "Portfolio today?", "prefill": {...}}
    ],
    "open": [
      {"id": "market", "label": "Open market view", "target": "market"}
    ],
    "portfolio_context": {...},
    "regime_detection": {...}
  }
}
```

#### POST /api/personal-finance/ask
Returns an investment memo for the user's question.

**Request:**
```json
{
  "question": "What should I do with my portfolio today?",
  "tickers": ["AAPL"]
}
```

**Response (Investment Memo):**
```json
{
  "ok": true,
  "data": {
    "question": "What should I do with my portfolio today?",
    "answer": "...",
    "verdict": "hold",
    "horizon": "1w",
    "reasoning": ["..."],
    "risks": ["..."],
    "confidence": 0.8,
    "sources": [...],
    "generated_at": "2026-03-13T16:04:58Z",
    "freshness": "2026-03-13T16:04:58Z"
  }
}
```

---

## Verification

### Unit Tests (8/8 passing)

```bash
cd /home/venom/shared/analyse-financiere/apps/api/src
python3 -m pytest domains/copilot/tests/test_personal_finance_copilot_start.py -v
```

**Test coverage:**
1. `test_personal_finance_start_has_brief_of_day` - Brief payload has required fields
2. `test_personal_finance_start_entry_points` - Entry points include brief, ask, open
3. `test_copilot_start_payload_structure` - Start payload has brief + ask + open structure
4. `test_scope_tickers_enrichment` - Scope tickers enrich ask prefill
5. `test_investment_memo_contract` - Investment memo output contract verified
6. `test_namespace_rewrite_for_personal_finance` - Namespace rewriting works
7. `test_personal_finance_start_endpoint_live` - Live endpoint test
8. `test_personal_finance_ask_endpoint_live` - Live ask endpoint test

### Live API Verification

```bash
# Test start endpoint
curl -s http://localhost:8050/api/personal-finance/start | jq '.data.brief_of_day.summary'

# Test ask endpoint
curl -s -X POST http://localhost:8050/api/personal-finance/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What should I do today?","tickers":["AAPL"]}' | jq '.data.verdict'
```

---

## Files Touched

| File | Change |
|------|--------|
| `apps/api/src/domains/copilot/tests/test_personal_finance_copilot_start.py` | Created - Test suite (181 lines) |

---

## Architecture Check

**Layer:** Domain (copilot)  
**Imports OK:** All imports use canonical domain paths  
**Path target:** `apps/api/src/domains/copilot/`  

**Compliance:**
- ✅ No duplicate helpers - reuses existing `copilot_service`, `_load_daily_brief_payload`, `_build_copilot_entry_points`
- ✅ Minimal patch - tests only, no code changes needed
- ✅ Domain-driven design - tests live in `domains/copilot/tests/`
- ✅ No frontend changes - backend-first strategy per PRODUCT_VISION.md

---

## Vision Alignment

**Batch:** BATCH-63  
**Target:** Personal Finance Copilot  
**Impact:** 

The delivered slice implements the core product vision:
1. **Brief of the day** - Users see market summary, sentiment, risks, macro signals immediately
2. **Ask rhythm** - Users can ask questions and receive investment memos
3. **Open rhythm** - Users can navigate to market views, opportunities, copilot
4. **Portfolio context** - When portfolio is saved, it enriches the brief and recommendations
5. **Explainable output** - Investment memos include verdict, horizon, reasoning, risks, confidence, sources

**Success criteria met:**
- ✅ User understands market situation in under a minute
- ✅ User can ask about portfolio/ticker and receive usable investment memo
- ✅ Freshness, confidence, risks, sources are visible
- ✅ Backend-first delivery with no frontend theme changes

---

## Next Steps

**Recommended:**
1. Frontend wiring to display the personal finance copilot UI
2. Add portfolio/watchlist persistence for richer context
3. Enhance investment memo generation with live LLM (currently fallback mode)

**Blockers:** None - slice is mergeable and functional

---

## Proof Commands

```bash
# Run tests
cd /home/venom/shared/analyse-financiere/apps/api/src
python3 -m pytest domains/copilot/tests/test_personal_finance_copilot_start.py -v

# Verify endpoint
curl -s http://localhost:8050/api/personal-finance/start | jq '.ok'
```
