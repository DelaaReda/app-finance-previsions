# BATCH-74-DEV-02: Personal Finance Copilot - Minimal Vertical Slice

**Delivery Date:** 2026-03-23  
**Status:** ✅ Complete  
**Priority:** P2  

## Product Goal

Build a personal finance copilot that starts with a brief of the day, lets the user ask or open actions.

## Minimal Slice Delivered

This delivery implements the smallest verifiable slice that provides user-facing value:

### 1. Backend API (`/api/copilot/start`)

**Location:** `apps/api/src/domains/copilot/api/copilot.py`

Returns:
```json
{
  "ok": true,
  "data": {
    "brief_of_day": {
      "summary": "Market summary...",
      "market_sentiment": "bullish",
      "top_signals": [...],
      "top_risks": [...],
      "macro_signals": [...],
      "sector_rotation": [...],
      "freshness": "2026-03-23T...",
      "source": ["brief_daily_snapshot"]
    },
    "ask": [
      { "kind": "ask", "label": "What's moving NVDA?", "prefill": { "question": "..." } }
    ],
    "open": [
      { "kind": "open", "label": "Open Live Brief", "target": "/brief/daily" }
    ],
    "generated_at": "2026-03-23T...",
    "freshness": "2026-03-23T..."
  }
}
```

### 2. Frontend Widget (`copilot-panel.html`)

**Location:** `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`

Features:
- Brief of the Day section with summary, signals, and risks
- Ask actions (pre-filled questions)
- Open actions (navigation targets)
- Portfolio context section (BATCH-71-DEV-03)
- Live badge with freshness timestamp
- Loading and error states

### 3. API Connector (`apiConnector.js`)

**Location:** `apps/web/src/domains/forecasts/contracts/apiConnector.js`

Provides:
- `getCopilotStart(tickers)` - Fetches copilot data with caching
- Auto-refresh every 2 minutes
- Fallback to daily brief if copilot start unavailable

## Test Coverage

### Backend Tests
- `apps/api/src/domains/copilot/tests/test_personal_finance_copilot_start.py`
- 8 tests covering brief structure, entry points, and scope enrichment
- All tests passing ✅

### Frontend Tests
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.test.js`
- 7 tests covering rendering, navigation, and portfolio display
- All tests passing ✅

### Integration Tests
- `apps/web/src/domains/forecasts/components/widgets/copilot-integration.test.js`
- 8 tests covering payload-shape assumptions, widget rendering helpers, and wiring hooks against a mocked copilot start payload
- All tests passing ✅

## User Value

A user opening the dashboard now sees:

1. **Brief of the Day** - A concise market summary answering "What's happening today?"
2. **Key Signals** - Top 3 market-moving signals
3. **Top Risks** - Main risks to watch
4. **Quick Actions** - Pre-built questions to ask the copilot
5. **Navigation** - One-click access to deeper views

## Architecture Alignment

### Reused Components (per task notes)
- ✅ Existing widget pattern from `forecasts/components/widgets/*`
- ✅ Shared UI wiring from `platform/js/utils/componentLoader.js`
- ✅ Existing API connector pattern
- ✅ Existing brief daily snapshot storage

### No New Dependencies
- Uses existing FastAPI router
- Uses existing storage layer
- Uses existing frontend component loader
- No npm packages added

## Freshness Guarantee

- Backend cache TTL: 30 seconds (configurable via `COPILOT_START_CACHE_TTL_SECONDS`)
- Frontend auto-refresh: 2 minutes
- Freshness timestamp displayed to user
- Source attribution shown

## Files Touched

### Created
- `apps/web/src/domains/forecasts/components/widgets/copilot-integration.test.js`

### Already Existed (Verified Working)
- `apps/api/src/domains/copilot/api/copilot.py`
- `apps/api/src/domains/copilot/application/copilot_service.py`
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`
- `apps/web/src/domains/forecasts/components/widgets/copilot-panel.test.js`
- `apps/web/src/domains/forecasts/contracts/apiConnector.js`

## How to Run Tests

```bash
# Backend tests
cd /home/venom/shared/analyse-financiere
python3 -m pytest apps/api/src/domains/copilot/tests/test_personal_finance_copilot_start.py -v

# Frontend unit tests
node apps/web/src/domains/forecasts/components/widgets/copilot-panel.test.js

# Integration tests
node apps/web/src/domains/forecasts/components/widgets/copilot-integration.test.js
```

## Next Slices (Future Work)

1. **Conversation History** - Track follow-up questions (BATCH-73-DEV-02)
2. **Decision Journal** - Log copilot recommendations (BATCH-73-DEV-03)
3. **Portfolio Integration** - Deep portfolio context (BATCH-71-DEV-03)
4. **Ask Endpoint Enhancement** - Full conversational AI

## Verification Checklist

- [x] Backend `/api/copilot/start` returns valid brief_of_day
- [x] Backend returns ask/open action lists
- [x] Frontend widget renders brief correctly
- [x] Frontend widget displays signals and risks
- [x] Frontend widget renders ask/open buttons
- [x] Freshness timestamp is visible
- [x] All targeted tests pass (backend route/service + frontend widget + mocked UI contract harness)
- [x] No new dependencies added
- [x] Reuses existing widget patterns
- [x] Documentation complete

---

**Delivery Evidence:** This minimal slice provides immediate user value (daily brief + quick actions) while establishing the foundation for richer copilot interactions.
