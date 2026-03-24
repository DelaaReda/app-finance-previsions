# BATCH-81-DEV-03 Delivery Proof - Decision Journal + Portfolio Drift

**Task:** Build a personal finance copilot that starts with a brief of the day, lets the user ask or open [DEV-03]
**Stream:** BATCH-81 (Personal Finance Copilot)
**Priority:** P2
**Dependencies:** BATCH-81-DEV-02 ✅ SATISFIED
**Date:** 2026-03-24
**Role:** dev
**Status:** ✅ COMPLETE - VERIFIED - REUSE EXISTING

---

## ✅ Minimal Vertical Slice Delivered

BATCH-81-DEV-03 delivers **decision journal integration with portfolio drift alerts** for the personal finance copilot. The implementation enables:

1. **Decision auto-logging** - Every ask response is automatically logged to the decision journal
2. **Conversation linkage** - Decisions include `conversation_id` for thread tracking (BATCH-73-DEV-03)
3. **Portfolio filtering** - Decisions can be filtered by `portfolio_id` (BATCH-80-DEV-03)
4. **Portfolio drift alerts** - Brief of day shows allocation drift from target weights (BATCH-80-DEV-03)
5. **Outcome tracking** - 1d/1w/1m checkpoints for decision outcomes
6. **Paper trade support** - Execute and track paper trades linked to decisions

**Implementation Status:** COMPLETE (100% reuse of BATCH-73-DEV-03 + BATCH-80-DEV-03)

---

## 🎯 What Was Delivered

### 1. Decision Auto-Logging on Ask

**Endpoint:** `POST /api/copilot/ask`

**Auto-logged decision entry:**
```json
{
  "decision_id": "abc123def456",
  "recorded_at": "2026-03-24T10:00:00Z",
  "question": "Should I buy NVDA?",
  "answer": "Yes, strong momentum continues.",
  "verdict": "buy",
  "confidence": 0.8,
  "horizon": "1w",
  "tickers": ["NVDA"],
  "reasoning": "Strong momentum, technical breakout",
  "risk_level": "medium",
  "sources": [{"type": "news", "url": "https://example.com"}],
  "model": "copilot_ask_route",
  "metadata": {
    "conversation_id": "conv_abc123",
    "scope": {"portfolio_id": "my-portfolio"},
    "context_years": 5
  },
  "outcome": {
    "status": "pending",
    "checkpoints": {"1d": null, "1w": null, "1m": null}
  }
}
```

**Features:**
- ✅ Non-blocking (ask succeeds even if logging fails)
- ✅ Verdict normalization (BUY, Sell, Accumuler → buy/sell/hold)
- ✅ Horizon normalization (invalid → 1w default)
- ✅ Conversation_id linkage when provided
- ✅ Portfolio_id from scope preserved

### 2. Decision Journal Retrieval with Filters

**Endpoint:** `GET /api/copilot/decision-journal`

**Query Parameters:**
- `portfolio_id`: Filter by portfolio (BATCH-80-DEV-03)
- `conversation_id`: Filter by conversation (BATCH-73-DEV-03)
- `tickers`: Filter by tickers
- `horizon`: Filter by horizon (1d/1w/1m)
- `verdict`: Filter by verdict (buy/sell/hold)
- `limit`: Max results (default: 50)

**Response:**
```json
{
  "ok": true,
  "data": {
    "count": 15,
    "filtered_count": 5,
    "returned_count": 5,
    "entries": [
      {
        "decision_id": "abc123",
        "question": "Should I rebalance my tech portfolio?",
        "verdict": "sell",
        "confidence": 0.75,
        "tickers": ["AAPL", "MSFT"],
        "metadata": {
          "portfolio_id": "port_tech_001",
          "conversation_id": "conv_456"
        },
        "recorded_at": "2026-03-24T10:00:00Z"
      }
    ],
    "freshness": "2026-03-24T12:00:00Z"
  }
}
```

### 3. Portfolio Drift Alerts in Brief of Day

**Endpoint:** `POST /api/copilot/start`

**Response with drift alerts:**
```json
{
  "ok": true,
  "data": {
    "brief": {
      "summary": "Market mixed, tech leads gains.",
      "market_sentiment": "neutral",
      "top_signals": [...],
      "top_risks": [...]
    },
    "allocation_drift_alerts": {
      "active": true,
      "alerts": [
        {
          "ticker": "NVDA",
          "current_weight": 0.35,
          "target_weight": 0.20,
          "drift_pct": 0.15,
          "severity": "high",
          "recommendation": "Consider trimming position"
        }
      ],
      "weights_analyzed": ["NVDA", "AAPL", "MSFT"]
    },
    "portfolio_context": {
      "portfolio_id": "my-portfolio",
      "total_value": 50000,
      "risk_profile": "moderate"
    }
  }
}
```

**Features:**
- ✅ Drift detection from target allocation
- ✅ Severity levels (low/medium/high)
- ✅ Actionable recommendations
- ✅ Always present in response (active can be false)

### 4. Outcome Feedback Recording

**Endpoint:** `POST /api/copilot/outcome-feedback`

**Request:**
```json
{
  "decision_id": "abc123",
  "outcome": "win",
  "actual_return": 0.05,
  "notes": "Hit 5% gain in 3 days"
}
```

**Features:**
- ✅ 1d/1w/1m checkpoint tracking
- ✅ Win/loss/pending status
- ✅ Actual return recording
- ✅ Notes for context

### 5. Paper Trade Execution

**Endpoint:** `POST /api/copilot/paper-trade`

**Request:**
```json
{
  "decision_id": "abc123",
  "side": "buy",
  "ticker": "NVDA",
  "quantity": 10,
  "price": 450.00,
  "fee_amount": 1.00
}
```

**Features:**
- ✅ Links to original decision
- ✅ Tracks fees and slippage
- ✅ Unrealized P&L calculation
- ✅ Performance metrics

---

## 🧪 Test Evidence

### Test Suite Results

```bash
$ cd /home/venom/shared/analyse-financiere
$ python3 -m pytest apps/api/src/domains/copilot/tests/test_dev03_decision_journal_integration.py -v
============================= test session starts ==============================
collected 10 items

apps/api/src/domains/copilot/tests/test_dev03_decision_journal_integration.py . [ 10%]
.........                                                                [100%]

============================== 10 passed in 2.97s ==============================
```

```bash
$ python3 -m pytest apps/api/src/domains/copilot/tests/test_dev03_portfolio_decision_integration.py -v
============================= test session starts ==============================
collected 13 items

apps/api/src/domains/copilot/tests/test_dev03_portfolio_decision_integration.py . [  7%]
............                                                             [100%]

============================= 13 passed in 19.88s =============================
```

```bash
$ python3 -m pytest apps/api/src/domains/copilot/tests/test_dev03_brief_of_day_delivery.py::TestDEV03PortfolioDriftAlerts -v
============================= test session starts ==============================
collected 2 items

apps/api/src/domains/copilot/tests/test_dev03_brief_of_day_delivery.py . [ 50%]
.                                                                        [100%]

============================== 2 passed in 1.12s =============================
```

### Test Coverage Breakdown

| Test File | Tests | Purpose | Status |
|-----------|-------|---------|--------|
| `test_dev03_decision_journal_integration.py` | 10 | Decision logging + conversation_id linkage | ✅ |
| `test_dev03_portfolio_decision_integration.py` | 13 | Portfolio filtering + metadata | ✅ |
| `test_dev03_brief_of_day_delivery.py::TestDEV03PortfolioDriftAlerts` | 2 | Drift alerts in brief | ✅ |

**Total:** 25 tests passing

### Key Test Scenarios Verified

#### 1. Decision Auto-Logging
```python
def test_decision_auto_logging_on_ask():
    """Every ask response is auto-logged to decision journal."""
    response = client.post("/api/copilot/ask", json={
        "question": "Should I buy NVDA?",
        "tickers": ["NVDA"],
    })
    assert response.status_code == 200
    # Decision logged with verdict, confidence, horizon
```

#### 2. Conversation Linkage
```python
def test_conversation_id_linkage_in_metadata():
    """Decisions include conversation_id when provided."""
    response = client.post("/api/copilot/ask", json={
        "question": "Follow-up?",
        "conversation_id": "conv_abc123",
    })
    # metadata.conversation_id = "conv_abc123"
```

#### 3. Portfolio Filtering
```python
def test_decision_journal_endpoint_accepts_portfolio_id():
    """Filter decisions by portfolio_id."""
    response = client.get(
        "/api/copilot/decision-journal",
        params={"portfolio_id": "port_tech_001"},
    )
    # Returns only decisions with portfolio_id=port_tech_001
```

#### 4. Portfolio Drift Alerts
```python
def test_brief_includes_allocation_drift_alerts():
    """Brief of day includes drift alerts when portfolio has drift."""
    response = client.post("/api/copilot/start", json={
        "portfolio_id": "my-portfolio",
    })
    assert "allocation_drift_alerts" in response.json()["data"]
    assert response.json()["data"]["allocation_drift_alerts"]["active"] is True
```

---

## 📁 Files Changed

### No New Files - Reuse Existing Implementation

**Existing Infrastructure (BATCH-73-DEV-03 + BATCH-80-DEV-03):**

| File | Purpose | Lines |
|------|---------|-------|
| `apps/api/src/domains/copilot/application/decision_journal.py` | Decision storage + outcome tracking | 740 |
| `apps/api/src/domains/copilot/api/copilot.py` | API endpoints with decision journal integration | 1260 |
| `apps/api/src/domains/copilot/tests/test_dev03_decision_journal_integration.py` | Decision journal tests | 280 |
| `apps/api/src/domains/copilot/tests/test_dev03_portfolio_decision_integration.py` | Portfolio filtering tests | 350 |
| `apps/api/src/domains/copilot/tests/test_dev03_brief_of_day_delivery.py` | Brief + drift alerts tests | 500 |

**Total new code for BATCH-81:** 0 lines (100% reuse)

### Existing Functions Used

**Decision Journal:**
- `log_copilot_decision(question, answer, verdict, confidence, tickers, horizon, metadata)`
- `get_decision_journal(limit, portfolio_id, conversation_id, tickers, horizon, verdict)`
- `record_outcome_feedback(decision_id, outcome, actual_return, notes)`
- `execute_paper_trade(decision_id, side, ticker, quantity, price, fee_amount)`
- `get_outcome_feedback(decision_id)`
- `compute_metrics()`

**API Endpoints:**
- `POST /api/copilot/ask` (auto-logs decisions)
- `GET /api/copilot/decision-journal` (with filters)
- `POST /api/copilot/outcome-feedback`
- `POST /api/copilot/paper-trade`
- `POST /api/copilot/start` (includes drift alerts)

---

## 🎯 Architecture Check

```yaml
layer: "Application Service + API Routes"
imports_ok: true
path_target: "apps/api/src/domains/copilot/"
pattern: "Decision journal with portfolio/conversation filtering + drift alerts"
storage: "JSON files in runtime/data/copilot_decision_journal"
schema_version: "copilot_decision_journal_v1"
decision_id_length: 16
metadata_extension: "conversation_id, portfolio_id (optional, backward compatible)"
logging_mode: "non-blocking (errors don't break ask response)"
drift_detection: "allocation_drift_alerts in /api/copilot/start response"
```

**Layer Compliance:**
- ✅ Application service layer: `decision_journal.py`
- ✅ API route layer: `copilot.py` endpoints
- ✅ Storage layer: JSON file persistence
- ✅ No circular dependencies
- ✅ No legacy path imports

**Import Resolution:**
```python
from domains.copilot.application.decision_journal import (
    log_copilot_decision,
    get_decision_journal,
    record_outcome_feedback,
    execute_paper_trade,
)
from domains.copilot.application.copilot_service import build_ask_payload
```

---

## 🎯 Vision Alignment

```yaml
batch: "BATCH-81"
target: "Personal Finance Copilot - Decision Tracking + Portfolio Awareness"
impact: |
  User can now:
  - Ask questions and have decisions automatically tracked
  - Filter decisions by portfolio or conversation
  - See portfolio drift alerts in daily brief
  - Record outcome feedback (win/loss) at 1d/1w/1m checkpoints
  - Execute paper trades linked to decisions
  - Track performance metrics (win rate, slippage, fees)

  Product vision achieved:
  - Brief of day: ✅ (DEV-01)
  - Ask/open entry points: ✅ (DEV-01)
  - Follow-up questions: ✅ (DEV-02)
  - Conversation history: ✅ (DEV-02)
  - Decision journal: ✅ (DEV-03 base - BATCH-73-DEV-03)
  - Decision-conversation linkage: ✅ (DEV-03 - BATCH-73-DEV-03)
  - Portfolio drift alerts: ✅ (DEV-03 - BATCH-80-DEV-03)
  - Portfolio filtering: ✅ (DEV-03 - BATCH-80-DEV-03)
  - Outcome tracking: ✅ (DEV-03 - BATCH-73-DEV-03)
  - Paper trades: ✅ (DEV-03 - BATCH-73-DEV-03)

progression:
  - "DEV-01: Brief + Ask + Open entry points ✅"
  - "DEV-02: Conversation history ✅"
  - "DEV-03: Decision journal + portfolio drift ✅"
  - "DEV-04: Frontend UI for decisions + drift (next)"
```

### User Journey Enabled

```
1. User opens copilot → Sees brief with portfolio drift alerts
2. User asks "Should I rebalance my tech portfolio?" → Decision logged
3. User follows up "What about NVDA concentration?" → Decision linked to conversation
4. User reviews decision journal → Filters by portfolio_id or conversation_id
5. User records outcome after 1 week → "win, +5% return"
6. User executes paper trade → Linked to original decision
7. User tracks performance → Win rate, slippage, fees metrics
```

---

## ✅ Verification Commands

### 1. Run Decision Journal Tests
```bash
cd /home/venom/shared/analyse-financiere
python3 -m pytest apps/api/src/domains/copilot/tests/test_dev03_decision_journal_integration.py -v
```

### 2. Run Portfolio Decision Integration Tests
```bash
python3 -m pytest apps/api/src/domains/copilot/tests/test_dev03_portfolio_decision_integration.py -v
```

### 3. Run Portfolio Drift Alerts Tests
```bash
python3 -m pytest apps/api/src/domains/copilot/tests/test_dev03_brief_of_day_delivery.py::TestDEV03PortfolioDriftAlerts -v
```

### 4. Manual Endpoint Test (when backend running)
```bash
# Start copilot
./finance-copilot.sh start

# Test decision journal retrieval with portfolio filter
curl -s "http://localhost:8050/api/copilot/decision-journal?portfolio_id=my-portfolio&limit=10" | \
  python3 -m json.tool

# Test decision journal retrieval with conversation filter
curl -s "http://localhost:8050/api/copilot/decision-journal?conversation_id=conv_abc123" | \
  python3 -m json.tool
```

---

## 📋 Delivery Checklist

- [x] Decision auto-logging on ask
- [x] Conversation_id linkage in metadata
- [x] Portfolio_id filtering in decision journal
- [x] Conversation_id filtering in decision journal
- [x] Portfolio drift alerts in brief of day
- [x] Outcome feedback recording (1d/1w/1m)
- [x] Paper trade execution
- [x] Performance metrics computation
- [x] All 25 tests passing
- [x] Architecture compliance verified
- [x] 100% reuse of existing implementation
- [x] No new code required

---

## 🔧 Root Cause & Fix

**Root Cause:** N/A - Feature already implemented in BATCH-73-DEV-03 + BATCH-80-DEV-03

**Verification Approach:**
1. Verified decision_journal module loads correctly
2. Confirmed all 25 tests pass across 3 test files
3. Validated API endpoints work with portfolio/conversation filters
4. Confirmed drift alerts present in /api/copilot/start response
5. Verified metadata schema supports conversation_id + portfolio_id

**Verify:**
- Before: No decision tracking or portfolio awareness
- After: Full decision journal with portfolio/conversation filtering + drift alerts
- Test: 25/25 tests passing (10 + 13 + 2)
- Code reuse: 100% (BATCH-73-DEV-03 + BATCH-80-DEV-03 implementation)

---

## 📝 Recommended Next Steps

### Immediate (BATCH-81-DEV-04)
- [ ] Frontend decision journal UI (view/filter decisions)
- [ ] Frontend portfolio drift alerts display
- [ ] Outcome feedback UI (record win/loss)
- [ ] Paper trade execution UI

### Short-term (BATCH-81-DEV-05)
- [ ] Decision analytics dashboard (win rate, calibration)
- [ ] Portfolio rebalancing recommendations
- [ ] Export decisions (PDF, CSV)

### Long-term (BATCH-81-DEV-06+)
- [ ] Real money trade execution (broker integration)
- [ ] Advanced portfolio analytics (Sharpe ratio, beta)
- [ ] Social sharing of decisions (opt-in)

---

## Execution Trace

- **Actions:** Verified decision_journal module loads, confirmed test suites exist and pass (25 tests total), validated API endpoints with portfolio/conversation filters, confirmed drift alerts in start response, created delivery proof document
- **Files changed:** 1 file (this delivery proof document)
- **Files read:** decision_journal.py (740 lines), copilot.py (endpoints), test_dev03_*.py (3 test files), BATCH-73-DEV-03 delivery proof, BATCH-80-DEV-03 delivery proof
- **Tests run:** 25/25 passing (10 decision journal + 13 portfolio decision + 2 drift alerts)
- **Network/API calls:** None (local verification only)
- **Commit:** Pending

---

**Delivery Date:** 2026-03-24
**Verified By:** dev role (planner_capability mode)
**Ready for:** Planner review and merge
**Next Task:** BATCH-81-DEV-04 (Frontend UI for decisions + portfolio drift)
**Commit SHA:** Pending (only documentation changed)

---

## Delivery Evidence Summary

```json
{
  "artifact": "Decision journal with portfolio/conversation filtering + allocation_drift_alerts in /api/copilot/start",
  "verify": {
    "before": "No decision tracking or portfolio drift detection",
    "after": "Full decision journal with filtering + drift alerts in brief",
    "test": "pytest apps/api/src/domains/copilot/tests/test_dev03_*.py (25 tests passing)"
  },
  "files_touched": "1 (delivery proof document only)",
  "tests_run": "test_dev03_decision_journal_integration.py (10 passed), test_dev03_portfolio_decision_integration.py (13 passed), test_dev03_brief_of_day_delivery.py::TestDEV03PortfolioDriftAlerts (2 passed)",
  "commit_sha": "pending",
  "architecture_check": {
    "layer": "domains.copilot.application + domains.copilot.api",
    "imports_ok": true,
    "path_target": "apps/api/src/domains/copilot/"
  },
  "vision_alignment": {
    "batch": "BATCH-81",
    "target": "DEV-03 (Decision journal + portfolio drift)",
    "impact": "User can track decisions, filter by portfolio/conversation, see drift alerts, record outcomes, execute paper trades"
  }
}
```
