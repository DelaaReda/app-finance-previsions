# Finance Copilot API - Missing Endpoints Analysis & Roadmap

**Date** : 2025-11-06  
**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Purpose** : Identify gaps in current API and propose high-value new endpoints

---

## 🔍 Current API Coverage Analysis

### ✅ Well-Covered Areas

1. **Health & Monitoring** ✅
   - `/api/health`
   - `/api/freshness`
   - `/api/cache/status`
   - `/api/cache/dependencies`

2. **Macro Data** ✅
   - `/api/macro/series`
   - `/api/macro/snapshot`
   - `/api/macro/indicators`

3. **Stocks Data** ✅
   - `/api/stocks/prices`
   - `/api/stocks/universe`
   - `/api/stocks/{ticker}`
   - `/api/stocks/{ticker}/sheet`

4. **News** ✅
   - `/api/news/feed`
   - `/api/news/sentiment`
   - `/api/news/events`
   - `/api/news/features/daily`

5. **Copilot/LLM** ✅
   - `/api/copilot/ask`
   - `/api/copilot/history`
   - `/api/llm/judge/run`

6. **Brief** ✅
   - `/api/brief/daily`
   - `/api/brief/weekly`
   - `/api/signals/top`
   - `/api/signals/composite`

7. **Analysis** ✅
   - `/api/forecasts`
   - `/api/backtests`
   - `/api/dashboard/kpis`

8. **Notes/RAG** ✅
   - `/api/notes` (CRUD)
   - `/api/rag/seed`
   - `/api/rag/stats`

9. **Alerts** ⚠️ (Read-only)
   - `/api/alerts` (GET only)

---

## ❌ Critical Gaps Identified

### 1. **Intelligence Services NOT Exposed** 🚨

Ces services existent dans le backend (créés par moi) mais **ne sont pas exposés via l'API** :

| Service | Backend File | API Endpoint | Status |
|---------|-------------|--------------|--------|
| Intelligence Service | `backend/services/intelligence_service.py` | `/api/intelligence/snapshot` | ❌ **MISSING** |
| Context Service | `backend/services/context_service.py` | `/api/context/current` | ❌ **MISSING** |
| Recommendations Service | `backend/services/recommendations_service.py` | `/api/recommendations/daily` | ❌ **MISSING** |
| Correlation Intelligence | `backend/services/correlation_intelligence_service.py` | `/api/correlations/analyzed` | ❌ **MISSING** |

**Impact** : Frontend widgets (FC-INT-022, FC-INT-024, FC-INT-025) utilisent ces services mais les endpoints ne sont pas documentés dans OpenAPI !

**Priority** : 🔥 **CRITICAL** - Ces endpoints existent mais manquent de documentation/exposition formelle

---

### 2. **Portfolio/Watchlist Management** 🚨

**Current** : Pas d'endpoints pour gérer des watchlists personnalisées

**Missing Endpoints** :
- `POST /api/portfolios` - Create watchlist
- `GET /api/portfolios` - List user watchlists
- `GET /api/portfolios/{id}` - Get watchlist details
- `PUT /api/portfolios/{id}` - Update watchlist
- `DELETE /api/portfolios/{id}` - Delete watchlist
- `POST /api/portfolios/{id}/tickers` - Add ticker to watchlist
- `DELETE /api/portfolios/{id}/tickers/{ticker}` - Remove ticker
- `GET /api/portfolios/{id}/performance` - Watchlist performance tracking

**Use Case** :
- User creates "Tech Watchlist" avec AAPL, MSFT, NVDA
- Dashboard filtre sur cette watchlist
- Track performance de la watchlist vs SPY
- Alerts sur tickers de la watchlist

**Priority** : 🔥 **HIGH**

---

### 3. **Alerts Management (Write Operations)** 🚨

**Current** : Only `GET /api/alerts` (read-only)

**Missing Endpoints** :
- `POST /api/alerts` - Create alert
- `PUT /api/alerts/{id}` - Update alert
- `DELETE /api/alerts/{id}` - Delete alert
- `POST /api/alerts/{id}/test` - Test alert condition
- `GET /api/alerts/triggered` - Get recently triggered alerts
- `POST /api/alerts/{id}/snooze` - Snooze alert

**Alert Types** :
- Price threshold (AAPL > $180)
- Sentiment shift (news sentiment < -0.5)
- Forecast change (confidence drops below 0.7)
- Correlation break (AAPL-MSFT correlation < 0.5)
- Regime change (market regime shifts to HIGH_VOLATILITY)

**Priority** : 🔥 **HIGH**

---

### 4. **Strategy Builder & Management** 🎯

**Current** : No strategy creation/management

**Missing Endpoints** :
- `POST /api/strategies` - Create trading strategy
- `GET /api/strategies` - List user strategies
- `GET /api/strategies/{id}` - Get strategy details
- `PUT /api/strategies/{id}` - Update strategy
- `DELETE /api/strategies/{id}` - Delete strategy
- `POST /api/strategies/{id}/backtest` - Run backtest on strategy
- `GET /api/strategies/{id}/performance` - Strategy performance

**Strategy Definition** :
```json
{
  "name": "Momentum + Low Vol",
  "description": "Long high momentum stocks with low volatility",
  "rules": {
    "entry": {
      "forecast_confidence": "> 0.75",
      "momentum_score": "> 0.7",
      "volatility": "< 0.3"
    },
    "exit": {
      "forecast_confidence": "< 0.5",
      "profit_target": "5%",
      "stop_loss": "2%"
    }
  },
  "universe": ["AAPL", "MSFT", "GOOGL"],
  "position_size": "equal_weight"
}
```

**Use Case** :
- User defines strategy with rules
- System backtests automatically
- Real-time signals when conditions met
- Performance tracking

**Priority** : 🟡 **MEDIUM**

---

### 5. **Search & Discovery** 🔍

**Current** : No global search

**Missing Endpoints** :
- `GET /api/search/global?q={query}` - Search across all data
- `GET /api/search/tickers?q={query}` - Search tickers
- `GET /api/search/news?q={query}` - Search news
- `GET /api/search/notes?q={query}` - Search user notes
- `GET /api/search/recommendations?filters={}` - Filter recommendations

**Features** :
- Full-text search across tickers, news, notes
- Fuzzy matching (APPL → AAPL)
- Filters (date range, sentiment, sector)
- Pagination & sorting

**Priority** : 🟡 **MEDIUM**

---

### 6. **News Advanced Analysis** 📰

**Current** : Basic news endpoints

**Missing Endpoints** :
- `GET /api/news/topics` - Topic modeling/clustering
- `GET /api/news/similar?article_id={id}` - Find similar articles
- `GET /api/news/timeline?ticker={ticker}` - News timeline for ticker
- `GET /api/news/impact?ticker={ticker}` - Measure news impact on price
- `GET /api/news/sources` - List news sources & quality scores

**Use Case** :
- Identify trending topics (e.g., "AI regulations", "Fed policy")
- Find related articles when reading one
- See news impact on stock price (before/after)
- Filter by high-quality sources

**Priority** : 🟡 **MEDIUM**

---

### 7. **Performance Tracking** 📈

**Current** : No portfolio/strategy performance tracking

**Missing Endpoints** :
- `GET /api/performance/portfolio/{id}` - Portfolio performance over time
- `GET /api/performance/strategy/{id}` - Strategy performance metrics
- `GET /api/performance/benchmark?portfolio_id={id}&benchmark={ticker}` - Compare vs benchmark
- `GET /api/performance/attribution?portfolio_id={id}` - Performance attribution analysis

**Metrics** :
- Total return, CAGR, Sharpe ratio, max drawdown
- Win rate, avg win/loss
- Monthly/quarterly returns
- Risk-adjusted metrics

**Priority** : 🟡 **MEDIUM**

---

### 8. **Export & Reporting** 📄

**Current** : No data export

**Missing Endpoints** :
- `GET /api/export/forecasts?format=csv` - Export forecasts
- `GET /api/export/portfolio/{id}?format=pdf` - Portfolio report
- `GET /api/export/backtest/{id}?format=csv` - Backtest results
- `POST /api/reports/generate` - Generate custom report

**Formats** :
- CSV (for data analysis)
- PDF (for presentations)
- JSON (for integrations)
- Excel (for financial models)

**Priority** : 🟢 **LOW**

---

### 9. **User Preferences & Settings** ⚙️

**Current** : No user settings management

**Missing Endpoints** :
- `GET /api/user/preferences` - Get user preferences
- `PUT /api/user/preferences` - Update preferences
- `GET /api/user/notifications` - Notification settings
- `PUT /api/user/notifications` - Update notifications
- `GET /api/user/activity` - User activity log

**Settings** :
- Default universe (tickers to track)
- Dashboard layout preferences
- Alert delivery methods (email, in-app)
- Data refresh frequency
- Theme (dark/light)

**Priority** : 🟢 **LOW**

---

### 10. **Backtesting Enhancements** 🧪

**Current** : Only `GET /api/backtests` (read results)

**Missing Endpoints** :
- `POST /api/backtests` - Create new backtest
- `GET /api/backtests/{id}/trades` - Get backtest trades
- `GET /api/backtests/{id}/metrics` - Detailed metrics
- `POST /api/backtests/{id}/clone` - Clone & modify backtest
- `GET /api/backtests/compare?ids=1,2,3` - Compare multiple backtests

**Enhanced Backtest Config** :
```json
{
  "strategy_id": "strategy-123",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000,
  "commission": 0.001,
  "slippage": 0.0005,
  "rebalance_frequency": "monthly"
}
```

**Priority** : 🟡 **MEDIUM**

---

## 🎯 Recommended Roadmap

### 🔥 Phase 1: Critical (Week 1) - **Expose Existing Services**

**Effort** : 1-2 days  
**Impact** : 🔥 HIGH

1. ✅ **Document existing Intelligence APIs** in OpenAPI
   - `/api/intelligence/snapshot` (already exists, needs docs)
   - `/api/context/current` (already exists, needs docs)
   - `/api/recommendations/daily` (already exists, needs docs)
   - `/api/correlations/analyzed` (already exists, needs docs)

**Action** : Update `main.py` to register these routers in OpenAPI spec

---

### 🔥 Phase 2: High-Value Additions (Week 2-3)

**Effort** : 1 week  
**Impact** : 🔥 HIGH

2. **Portfolio/Watchlist Management**
   - Backend service: `backend/services/portfolio_service.py`
   - API routes: `backend/api/routes/portfolios.py`
   - Endpoints: 8 endpoints (CRUD + performance)
   
3. **Alerts Management (Write Ops)**
   - Backend service: `backend/services/alerts_service.py`
   - API routes: `backend/api/routes/alerts.py`
   - Endpoints: 6 endpoints (CRUD + test + snooze)

---

### 🟡 Phase 3: Enhanced Features (Week 4-5)

**Effort** : 1.5 weeks  
**Impact** : 🟡 MEDIUM

4. **Strategy Builder**
   - Backend service: `backend/services/strategy_service.py`
   - API routes: `backend/api/routes/strategies.py`
   - Endpoints: 7 endpoints

5. **Search & Discovery**
   - Backend service: `backend/services/search_service.py`
   - API routes: `backend/api/routes/search.py`
   - Endpoints: 5 endpoints

6. **Backtesting Enhancements**
   - Extend `backend/api/routes/backtests.py`
   - Endpoints: 5 additional endpoints

---

### 🟢 Phase 4: Nice-to-Have (Week 6+)

**Effort** : 2 weeks  
**Impact** : 🟢 LOW-MEDIUM

7. **News Advanced Analysis**
8. **Performance Tracking**
9. **Export & Reporting**
10. **User Preferences**

---

## 📊 Impact Matrix

| Endpoint Group | Effort | Impact | Priority | Users Benefit |
|----------------|--------|--------|----------|---------------|
| Expose Existing Intelligence APIs | 🟢 Low | 🔥 High | 🔥 Critical | Immediate - widgets already use them |
| Portfolio/Watchlist | 🟡 Medium | 🔥 High | 🔥 High | Personalization + tracking |
| Alerts Management | 🟡 Medium | 🔥 High | 🔥 High | Proactive notifications |
| Strategy Builder | 🟡 Medium | 🟡 Medium | 🟡 Medium | Advanced users |
| Search & Discovery | 🟢 Low | 🟡 Medium | 🟡 Medium | Navigation & efficiency |
| Backtesting Enhancements | 🟡 Medium | 🟡 Medium | 🟡 Medium | Strategy validation |
| News Advanced Analysis | 🔴 High | 🟢 Low | 🟢 Low | Deep insights |
| Performance Tracking | 🟡 Medium | 🟡 Medium | 🟢 Low | Accountability |
| Export & Reporting | 🟢 Low | 🟢 Low | 🟢 Low | Shareability |
| User Preferences | 🟢 Low | 🟢 Low | 🟢 Low | Customization |

---

## 🚀 Quick Wins (Can do NOW)

### 1. **Expose Intelligence APIs in OpenAPI** (30 min)

**File** : `backend/api/main.py`

**Action** : These routers are already included but might not be in OpenAPI properly

```python
# Verify these are registered (they should be based on previous work)
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(context_router, prefix="/api/context", tags=["context"])
app.include_router(recommendations_router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(correlations_router, prefix="/api/correlations", tags=["correlations"])
```

**Test** :
```bash
curl http://localhost:8050/openapi.json | jq '.paths | keys' | grep -E "intelligence|context|recommendations|correlations"
```

If missing → they're not in OpenAPI spec properly!

---

### 2. **Add `/api/search/tickers` Endpoint** (1h)

**File** : `backend/api/routes/search.py` (new)

```python
from fastapi import APIRouter, Query
from typing import List

router = APIRouter()

@router.get("/tickers")
async def search_tickers(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, le=50)
):
    """
    Search for tickers by name or symbol
    
    Supports:
    - Symbol search (e.g., "AAPL")
    - Fuzzy matching (e.g., "APPL" -> "AAPL")
    - Company name search (e.g., "Apple" -> "AAPL")
    """
    # Simple implementation using existing stock universe
    from backend.api.routes.stocks import get_stock_universe
    
    universe = await get_stock_universe()
    tickers = universe.get("tickers", [])
    
    # Simple substring match (can be enhanced with fuzzy matching)
    q_lower = q.lower()
    matches = [
        ticker for ticker in tickers 
        if q_lower in ticker.lower()
    ]
    
    return {
        "query": q,
        "matches": matches[:limit],
        "total": len(matches)
    }
```

**Register** in `main.py`:
```python
from api.routes.search import router as search_router
app.include_router(search_router, prefix="/api/search", tags=["search"])
```

---

### 3. **Add Alerts Write Endpoints** (2h)

**File** : `backend/api/routes/alerts.py` (extend existing)

```python
from pydantic import BaseModel
from typing import Literal

class AlertCreate(BaseModel):
    ticker: str
    type: Literal["price", "sentiment", "forecast", "correlation"]
    condition: str  # e.g., "> 180", "< -0.5"
    message: str

class AlertUpdate(BaseModel):
    condition: str | None = None
    message: str | None = None
    active: bool | None = None

@router.post("/alerts")
async def create_alert(alert: AlertCreate):
    """Create new alert"""
    # TODO: Implement alert creation logic
    return {"id": "alert-123", **alert.dict()}

@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, alert: AlertUpdate):
    """Update existing alert"""
    return {"id": alert_id, **alert.dict()}

@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete alert"""
    return {"id": alert_id, "deleted": True}
```

---

## 🎯 My Recommendation

**Start with Phase 1** (30 min - 1h) :
1. ✅ Verify Intelligence APIs are properly exposed in OpenAPI
2. ✅ Add `/api/search/tickers` (quick win, high user value)

**Then Phase 2** (1 week) :
3. ✅ Portfolio/Watchlist Management (most requested feature)
4. ✅ Alerts Write Operations (complete the alerts system)

**Why this order?**
- Phase 1 = **Zero backend work** (just documentation)
- `/api/search/tickers` = **30 min**, **immediate user value**
- Portfolio + Alerts = **High user impact**, reasonable effort

---

**Ready to implement?** 🚀

Which phase do you want me to start with?
1. ✅ Phase 1 (Expose Intelligence APIs - 30 min)
2. ✅ Quick Win: Search Tickers (1h)
3. ✅ Phase 2: Portfolio Management (1 day)
4. ✅ Phase 2: Alerts Write Ops (4h)

---

**Signé** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39 🕷️  
**Date** : 2025-11-06  
**Status** : Analysis Complete - Awaiting prioritization
