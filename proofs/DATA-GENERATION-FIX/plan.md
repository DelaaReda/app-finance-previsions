# DATA-GENERATION-FIX : Plan de Correction Backend

**Agent** : ELENA-39 🕷️  
**Date** : 2025-11-07  
**Mission** : Corriger les 3 jobs backend qui génèrent 0 données  
**Points estimés** : +150 (50 par job)  
**Priorité** : 🔥 CRITICAL

---

## 🔍 Diagnostic

### Problème 1 : News Ingest (STUB)
**File** : `backend/jobs/news_ingest.py`  
**Issue** : Ligne 20 `processed_count: 0` - Ne fait RIEN !  
**Code actuel** :
```python
result = {
    "processed_count": 0,  # ❌ STUB!
    "sources": [],
    "status": "completed"
}
# In a real implementation, save results...  # ❌ Commenté!
```

**Impact** :
- API `/api/news/feed` retourne `{"articles": []}`
- Page `/news` vide
- Tests échouent

---

### Problème 2 : Forecasts (Import Error?)
**File** : `backend/jobs/forecasts.py`  
**Issue** : Code semble bon MAIS peut avoir import error  
**Code actuel** :
```python
from models.forecast_hybrid_v1 import ForecastHybridV1  # ← Import OK?
from storage.base import save_forecasts  # ← Function exists?
```

**Checks nécessaires** :
1. ✅ Vérifier que `ForecastHybridV1` existe
2. ✅ Vérifier que `save_forecasts()` existe
3. ✅ Vérifier que ça génère bien `data/forecasts.json`
4. ✅ Vérifier format de données

---

### Problème 3 : Weekly Brief (STUB)
**File** : `backend/jobs/weekly_brief.py`  
**Issue** : Lignes 21-22 `top_signals: [], top_risks: []` - Ne fait RIEN !  
**Code actuel** :
```python
result = {
    "summary": "Weekly market summary...",
    "top_signals": [],  # ❌ STUB!
    "top_risks": [],    # ❌ STUB!
    "key_events": [],
    "status": "completed"
}
# In a real implementation, save results...  # ❌ Commenté!
```

**Impact** :
- API `/api/brief/daily` retourne vide
- Page `/brief` vide
- Tests échouent

---

## ✅ Solutions

### Solution 1 : News Ingest - REAL Implementation

**Approach** : Fetch RSS feeds + scrape articles + score + save

**Steps** :
1. Import feedparser (RSS)
2. Define RSS sources (Yahoo Finance, Bloomberg, etc.)
3. Fetch articles
4. Extract title, summary, link, published_date
5. Score articles (simple keyword scoring)
6. Save to `data/news_feed.json`

**Libraries needed** : `feedparser`, `requests`

---

### Solution 2 : Forecasts - Verify & Fix

**Approach** : Check imports, test generation, ensure save works

**Steps** :
1. Read `models/forecast_hybrid_v1.py`
2. Read `storage/base.py`
3. Verify `save_forecasts()` exists
4. Test job manually
5. Check `data/forecasts.json` created

---

### Solution 3 : Weekly Brief - REAL Implementation

**Approach** : Aggregate data from forecasts + news + macro

**Steps** :
1. Load forecasts from `data/forecasts.json`
2. Load news from `data/news_feed.json`
3. Load macro indicators
4. Generate top 3 signals (bullish)
5. Generate top 3 risks (bearish)
6. Save to `data/brief_weekly.json`

**Logic** :
- **Signals** : Forecasts with direction="up" + high confidence
- **Risks** : Forecasts with direction="down" + negative news + macro warnings

---

## 📊 Expected Impact

### Before Fixes
- News API : 0 articles
- Forecasts API : 0 rows
- Brief API : 0 signals + 0 risks
- Tests : 12/30 integration (40%)

### After Fixes
- News API : ~50+ articles ✅
- Forecasts API : ~8-20 rows ✅
- Brief API : 3 signals + 3 risks ✅
- Tests : 27/30 integration (90%) ✅

---

## 🎯 Action Plan

### Phase 1 : News Ingest (1-2h)
1. ✅ Implement RSS fetching
2. ✅ Implement article scoring
3. ✅ Implement save to data/news_feed.json
4. ✅ Test job manually
5. ✅ Verify API returns articles

### Phase 2 : Forecasts Verification (30min)
1. ✅ Verify imports work
2. ✅ Test job manually
3. ✅ Check data/forecasts.json created
4. ✅ Fix if needed

### Phase 3 : Weekly Brief (1h)
1. ✅ Implement data aggregation
2. ✅ Implement signal/risk generation
3. ✅ Implement save to data/brief_weekly.json
4. ✅ Test job manually
5. ✅ Verify API returns data

### Phase 4 : Integration Test (30min)
1. ✅ Run all 3 jobs
2. ✅ Verify all data files created
3. ✅ Test APIs
4. ✅ Run Playwright tests

---

**Total Estimated Time** : 3-4h  
**Total Points** : +150 (50 per job)  
**Status** : Starting Phase 1

---

**Signé** : ELENA-39 🕷️  
**Let's fix this!** 🚀
