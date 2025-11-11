# LLM-JUDGE-503-FIX : Diagnostic

**Agent** : ELENA-39 🕷️  
**Date** : 2025-11-07  
**Problem** : LLM Judge returns 503 "no answer from dynamic model selector"  
**URL** : http://localhost:5173/judge

---

## 🔍 Problem Analysis

### Error Message
```
HTTP 503 Service Unavailable
{"detail": "LLM Judge strict: 503: LLM Judge strict: no answer from dynamic model selector"}
```

### Code Flow

1. **Frontend** (`LLMJudge.tsx`):
   - Calls `POST /api/llm/judge/run`
   - Sends: `{model: "deepseek-ai/DeepSeek-V3-0324-Turbo", tickers: "AAPL,MSFT,NGD.TO", max_er: 0.08, min_conf: 0.6}`

2. **Backend** (`main.py` line 997-1300):
   - Receives request
   - Tries to generate forecasts
   - Calls `ask_llm()` from `research/llm_client.py`
   - If LLM fails → should return fallback

3. **LLM Client** (`llm_client.py`):
   - Tries to get LLM client (OpenAI or G4F)
   - Tries multiple models in fallback list:
     - Requested model (e.g., "deepseek-ai/DeepSeek-V3-0324-Turbo")
     - "gpt-4o-mini"
     - G4F_DEFAULT_MODEL env var
   - If ALL fail → returns fallback with error message

### Root Cause

**G4F (gpt4free) is FAILING to connect to providers!**

Possible reasons:
1. **No internet connection** (unlikely - we fetched news/prices)
2. **G4F providers down/blocked**
3. **Model name invalid** ("deepseek-ai/DeepSeek-V3-0324-Turbo" may not exist on G4F)
4. **Timeout** (G4F can be slow)
5. **G4F library version issue**

### Evidence

Line 132-134 in `llm_client.py`:
```python
except Exception as e:  # try next model
    last_err = e
    continue
```

If ALL models fail, it returns fallback (line 136-139):
```python
fb = "⚠️ LLM indisponible. Résumé des sources:\n\n"
return {"answer": fb, "citations": [], "model": "fallback", "tokens": 0, "error": str(last_err or "llm_failed")}
```

But somewhere the error is raised as 503 instead of returning the fallback!

---

## 🎯 Solution Options

### Option 1: Use Fallback Gracefully (Quick Fix)
- Modify Judge endpoint to ALWAYS return 200 with fallback
- Show deterministic analysis instead of LLM verdict
- User still gets useful info (top picks, risks)

### Option 2: Fix G4F Connection (Proper Fix)
- Test G4F with simple models
- Use working models only
- Add timeout/retry logic

### Option 3: Add Local Fallback Logic (Best UX)
- If LLM unavailable, use deterministic analysis
- Show message "LLM unavailable - using deterministic analysis"
- User still gets results (based on forecasts data)

---

## ✅ Recommended Fix: Option 1 + 3 Combined

**Modify Judge endpoint to never fail** - return deterministic analysis as fallback.

The code already has `_derive()` function (line 1049-1089) that creates deterministic analysis!

```python
def _derive(forecasts: List[Dict[str, Any]], max_er: float, min_conf: float) -> Dict[str, Any]:
    # ... generates top_buys, top_risks, summary_text
    return {
        "high_confidence_signals": high_conf,
        "top_buys": top_buys,
        "top_risks": top_risks,
        "stats": stats,
        "summary_text": summary,  # ← This is the fallback text!
    }
```

**Problem** : The endpoint raises 503 instead of using this fallback!

---

## 🔧 Fix Strategy

1. Wrap LLM call in try/except
2. If LLM fails → use deterministic fallback
3. Return 200 with fallback message
4. User sees results (not 503 error)

---

**Next** : Implement the fix!
