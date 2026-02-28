# /api/judge - Analyse Complète

**Date:** 2025-12-06  
**Version:** v3  
**File:** `src/api/routes/judge.py` (1194 lines)

---

## 📊 OVERVIEW

**Endpoint:** `GET /api/judge`  
**Purpose:** Generate LLM-powered investment verdicts for stocks with multi-phase analysis  
**Model:** DeepSeek-V3.1 via OpenRouter (g4f client)

---

## 🔧 PARAMETERS

```python
limit: int = 20          # Max tickers to analyze (1-100)
min_confidence: float = 0.5  # Minimum confidence to include (0.0-1.0)
ticker: List[str] = None     # Filter by specific tickers
sort_by: str = "confidence"  # confidence, expected_return, score, risk_level, timestamp
sort_order: str = "desc"     # asc, desc
profile: str = "equity_1w"   # NEW: Judge profile (equity_1w, sector_regime, etc)
```

---

## 🏗️ ARCHITECTURE

### **Data Sources (6)**
1. **forecasts.json** - ML predictions (ticker, expected_return, confidence)
2. **news_feed.json** - News articles (title, sentiment, tickers)
3. **brief_daily/weekly.json** - Market context
4. **prices.json** - Historical prices for technical indicators
5. **macro_series.json** - FRED data (VIX, US10Y, CPI, DXY, WTI, Gold)
6. **judge_features.json** - Pre-computed technical indicators (RSI, MACD, etc)
7. **ownership_snapshot.json** - Sector, market cap, ownership data

### **Processing Flow**

```
1. Load Data Sources
   ↓
2. For Each Ticker:
   ├─ 2.1 Load Features (forecast, prices, ownership)
   ├─ 2.2 Compute Technical Indicators (RSI, MACD, SMA, Bollinger)
   ├─ 2.3 Get Fundamentals (yfinance: P/E, market cap, beta)
   ├─ 2.4 Enrich with judge_pipeline (fusion_score, tech_enriched, fundamental_minimal)
   ├─ 2.5 Get News (top 5 by recency × |sentiment|)
   ├─ 2.6 Build Phase Blocks (fundamental, technical, macro, sentiment, fusion)
   ├─ 2.7 Build Payload (with profile)
   ├─ 2.8 Call LLM (DeepSeek-V3.1)
   ├─ 2.9 Parse JSON Response
   └─ 2.10 Validate & Return
      ↓
3. Sort & Filter Results
   ↓
4. Return JSON Response
```

---

## 📦 KEY FUNCTIONS

### **1. Technical Indicators**
```python
_tech_for(ticker) -> Dict:
    - RSI (14-period)
    - MACD (12/26/9)
    - SMA20, SMA50
    - Volatility (std dev)
    - Price momentum
    - Volume trend
```

### **2. Macro Snapshot**
```python
_macro_snapshot() -> Dict:
    - VIX + delta_1m
    - US10Y + delta_1m
    - CPI + delta_1m
    - DXY (USD index) + delta_1m
    - WTI/Brent oil + delta_1m
    - Gold + delta_1m
```

### **3. News Selection**
```python
_news_for(ticker) -> List:
    - Filters news by ticker mention
    - Scores by: recency × |sentiment|
    - Returns top 5
    - Formats: {title, sent, ts, source, summary(100 chars), tickers}
```

### **4. Phase Blocks** (5 phases)
```python
build_phase_blocks(ticker, features, macro, news):
    1. Fundamental: P/E, growth, valuation signals
    2. Technical: RSI, MACD, trend, momentum
    3. Macro: VIX regime, rates, commodities
    4. Sentiment: News sentiment aggregate
    5. Fusion: Weighted combination (compute_fusion_score)
```

### **5. Enrichments** (Phase 1 - NEW)
```python
# Via judge_pipeline.py
- compute_fusion_score(phases) -> weighted score + conviction
- get_tech_enriched(ticker, judge_features) -> live/cached technical
- get_fundamental_minimal(ticker) -> live yfinance fundamentals
- Placeholders: options_data, flows_data, insider_trading, analyst_ratings
```

---

## 🔄 DATA FLOW DIAGRAM

```
forecasts.json ───┐
news_feed.json ───┤
macro_series.json ├──→ [Load Data] ──→ For Each Ticker:
prices.json ──────┤                      ├─ Technical Analysis
judge_features ───┘                      ├─ Fundamental Analysis (yfinance)
                                         ├─ News Scoring
                                         ├─ Phase Blocks
                                         ├─ Enrichments (judge_pipeline)
                                         └─ Build Payload
                                                ↓
                                         [LLM Call]
                                         DeepSeek-V3.1
                                         (timeout: 120s)
                                                ↓
                                         [Parse Response]
                                         - Extract last JSON line
                                         - Validate structure
                                         - Fallback on error
                                                ↓
                                         [Verdict Object]
                                         {
                                           ticker, verdict,
                                           confidence, expected_return,
                                           risk_level, reasoning,
                                           analysis, phases,
                                           phase_scores, ml_prior,
                                           data_needed, metrics
                                         }
```

---

## 📊 RESPONSE FORMAT

```json
{
  "verdicts": [
    {
      "ticker": "AAPL",
      "verdict": "buy|hold|sell",
      "confidence": 0.85,
      "expected_return": 0.12,
      "risk_level": "low|medium|high",
      "reasoning": ["bullet 1", "bullet 2", ...],
      "analysis": {
        "summary": ["..."],
        "scenarios": [{"name": "base", "probability": 0.6, "impact": "..."}],
        "risks": ["..."],
        "impacts": {
          "FX": ["..."],
          "rates": ["..."],
          "commodities": ["..."],
          "equity": ["..."]
        },
        "actions": ["..."],
        "confidence": 0.85,
        "data_needed": ["options", "flows"]
      },
      "phases": {
        "fundamental": {"score": 0.7, "summary": ["..."]},
        "technical": {"score": 0.8, "summary": ["..."]},
        "macro": {"score": 0.6, "summary": ["..."]},
        "sentiment": {"score": 0.75, "summary": ["..."]},
        "fusion": {"score": 0.73, "conviction": "medium", "dominant_signal": "technical"}
      },
      "phase_scores": {
        "fundamental": 0.7,
        "technical": 0.8,
        "macro": 0.6,
        "sentiment": 0.75,
        "fusion": 0.73
      },
      "ml_prior": {
        "expected_return": 0.12,
        "confidence": 0.85
      },
      "data_needed": ["options", "insider_trading"],
      "metrics": {
        "total_ms": 8500,
        "news_ms": 50,
        "tech_ms": 120,
        "enrichments_ms": 450,
        "payload_ms": 15,
        "llm_ms": 7800
      },
      "timestamp": "2025-12-06T19:30:00Z"
    }
  ],
  "count": 1,
  "total_ms": 8500,
  "model": "deepseek/deepseek-v3",
  "provider": "OpenRouter"
}
```

---

## ⚡ PERFORMANCE

### **Latency Breakdown (per ticker)**
```
Total: ~8-12s per ticker

1. Data Loading: ~100ms
   - forecasts, news, macro, prices

2. Technical Analysis: ~120ms
   - RSI, MACD, SMA calculations

3. Enrichments (Phase 1): ~450ms
   - Fusion score: ~50ms
   - Tech enriched: ~200ms (yfinance fallback)
   - Fundamental minimal: ~200ms (yfinance live)

4. News Scoring: ~50ms
   - Filter + score + sort

5. Payload Build: ~15ms
   - Pydantic validation

6. LLM Call: ~7-10s ⚠️ BOTTLENECK
   - API latency: 6-8s
   - Model inference: 1-2s

7. Parse + Validate: ~10ms
```

### **Optimizations Applied**
- ✅ Batch technical indicators (-40% computation)
- ✅ Reuse yfinance cache
- ✅ Top 5 news only (not all)
- ✅ Parallel data loading (async)
- ❌ LLM call not parallelizable (sequential)

---

## 🧪 CACHING

**Cache Layer:** `load_or_compute(key, compute_fn)`

```python
# Cache key format
key = f"judge_verdicts_v3_limit{limit}_conf{min_confidence}_sort{sort_by}_{sort_order}"

# TTL: Not specified (relies on file mtime)
# Invalidation: Manual or on data refresh
```

---

## 🔒 ERROR HANDLING

### **Graceful Degradation**
```python
1. LLM Import Error → 500 error (critical)
2. Data Load Failure → Empty dict fallback
3. Technical Calc Error → Skip enrichment, continue
4. yfinance Failure → Use cached judge_features
5. News Not Found → Empty news array
6. Parse LLM Error → Fallback response with base confidence
7. Validation Error → Return with error in analysis.error
```

### **Explicit Error Reporting**
```python
# All enrichments report errors explicitly
{
  "error": "no_valid_phase_scores",
  "details": "..."
}

# Errors aggregated in data_needed
analysis.data_needed = ["options", "flows", "enrichment_failed: connection timeout"]
```

---

## 🆕 PHASE 1 INTEGRATION

**judge_pipeline.py** now integrated:

```python
# In _process_row()
if build_payload:
    validated = build_payload(
        ticker=sym,
        features=payload["features"],
        macro=macro_ctx,
        news=news_items,
        attachments=news_headlines,
        phases=phase_blocks,
        ml_prior=ml_prior,
        locale="fr-FR",
        judge_features=judge_features_data,  # NEW
        profile=prof,  # NEW (Phase 2)
    )
```

**Enrichments Added:**
1. ✅ Fusion score (conviction, dominant signal, agreement %)
2. ✅ Tech enriched (RSI, MACD, Bollinger, SMAs)
3. ✅ Fundamental minimal (P/E, market cap, beta, valuation signal)
4. ✅ Placeholders (options, flows, insider, analyst → null)

---

## 🎯 CURRENT ISSUES

### **1. LLM Latency (7-10s)** 🔴
- **Root cause:** API call to OpenRouter
- **Impact:** Total response 8-12s per ticker
- **Solutions:**
  - [ ] Reduce max_tokens (2048 → 1200)
  - [ ] Prompt optimization (shorter context)
  - [ ] Batch requests (future)
  - [ ] Edge compute (future)

### **2. News Coverage Gaps** 🟡
- **Issue:** Some tickers have news_count=0
- **Status:** ✅ Fixed in news_ingest.py (ticker tagging implemented)
- **Next:** Verify after data refresh

### **3. Profile System Not Used** 🟡
- **Status:** ⚠️ Code added but `profile` param not used for weighting yet
- **TODO:** Apply `prof.sources_weights` in phase_blocks calculation

### **4. No Parallel LLM Calls** 🟡
- **Issue:** Tickers processed sequentially
- **Impact:** 10 tickers = 80-120s total
- **Solution:** Async batch processing (future)

---

## 🔮 FUTURE ENHANCEMENTS

### **Short Term (Phase 2)**
1. [ ] Use profile.sources_weights for phase weighting
2. [ ] Add profile-specific prompts
3. [ ] Test sector_regime profile
4. [ ] News tagging validation

### **Medium Term**
1. [ ] Parallel LLM calls (async batch)
2. [ ] Streaming responses
3. [ ] Cache warm-up on data refresh
4. [ ] Real-time news feed

### **Long Term**
1. [ ] Options data integration
2. [ ] Flows data (dark pool, institutional)
3. [ ] Insider trading signals
4. [ ] Analyst ratings aggregation
5. [ ] Multi-model ensemble (beyond single LLM)

---

## 📈 METRICS TRACKED

```python
metrics = {
    "total_ms": float,        # Total processing time
    "news_ms": float,         # News filtering time
    "tech_ms": float,         # Technical analysis time
    "enrichments_ms": float,  # Enrichment functions time
    "payload_ms": float,      # Payload validation time
    "llm_ms": float,          # LLM call time
    "parse_ms": float,        # JSON parsing time
}
```

**Logged events:**
- enrichment_fusion_added/skipped
- enrichment_tech_added/failed/rejected
- enrichment_fundamental_added/failed
- llm_call_success/failure
- parse_success/failure

---

## 🛠️ TESTING

```bash
# Default profile
curl "http://localhost:8050/api/judge?limit=2"

# Specific profile
curl "http://localhost:8050/api/judge?limit=2&profile=sector_regime"

# Filter by ticker
curl "http://localhost:8050/api/judge?ticker=AAPL&ticker=NVDA"

# Sort by expected return
curl "http://localhost:8050/api/judge?limit=10&sort_by=expected_return&sort_order=desc"

# High confidence only
curl "http://localhost:8050/api/judge?min_confidence=0.8"
```

---

## 📊 VERDICT QUALITY FACTORS

**Confidence depends on:**
1. ✅ Data completeness (news_count, phase_scores)
2. ✅ Phase agreement (fusion.agreement_percentage)
3. ✅ ML prior confidence
4. ✅ Enrichment success rate
5. ⚠️ LLM model quality (DeepSeek-V3.1)

**Current avg confidence:** 0.65-0.85 (after Phase 1 enrichments)

---

**Last Updated:** 2025-12-06 19:35  
**Status:** Phase 1 Complete, Phase 2 In Progress (75%)
