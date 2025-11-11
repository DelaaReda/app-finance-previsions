✅ **FC-HOTFIX-009: Fix LLM Judge endpoint 404 error**

## Problème

Frontend page `/llm-judge` affichait erreur:
```
Erreur: POST /llm/judge/run 404: Not Found
```

## Diagnostic

**Frontend** (`copilot-app/frontend/webapp/src/pages/LLMJudge.tsx:14`):
```typescript
const res = await apiPost<{ stdout: { context: string; forecast: string }; rows: any[] }>(
  '/llm/judge/run',
  { model, max_er: 0.08, min_conf: 0.6, tickers }
)
```

**Client API** (`copilot-app/frontend/webapp/src/api/client.ts:8,82`):
```typescript
const API_BASE = "/api";
// ...
fetch(`${API_BASE}${path}`, ...)  // = /api/llm/judge/run ✅
```

**Backend endpoint** (`copilot-app/backend/src/api/main.py:973`):
```python
@app.post("/api/llm/judge/run")  # ✅ URL correcte
async def llm_judge_run(
    model: str = Query(...),      # ❌ Attend Query params
    max_er: float = Query(...),
    ...
):
```

**Cause**: L'endpoint attend des **Query parameters** (`?model=...&max_er=...`) mais le frontend envoie un **JSON body**.

## Solution

Changé endpoint signature pour accepter JSON body via Pydantic model:

```python
class LLMJudgeRequest(BaseModel):
    """Request body for LLM judge endpoint."""
    model: str = "deepseek-ai/DeepSeek-V3-0324-Turbo"
    max_er: float = 0.08
    min_conf: float = 0.6
    tickers: Optional[str] = None

@app.post("/api/llm/judge/run")
async def llm_judge_run(request: LLMJudgeRequest):
    """Run LLM-based market judgment with scoring and analysis."""
    ...
    # Utilise request.model, request.max_er, request.min_conf, request.tickers
```

## Modifications

**Fichier**: `copilot-app/backend/src/api/main.py`

**Lignes modifiées**: 973-1100

**Changes**:
1. Créé `LLMJudgeRequest` Pydantic model (lignes 973-978)
2. Changé signature: `async def llm_judge_run(request: LLMJudgeRequest)` (ligne 981)
3. Remplacé toutes références: `model` → `request.model`, `max_er` → `request.max_er`, etc.

## Test

Après redémarrage backend:

```bash
curl -X POST http://localhost:8050/api/llm/judge/run \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-ai/DeepSeek-V3-0324-Turbo","max_er":0.08,"min_conf":0.6,"tickers":"AAPL"}'
```

**Résultat attendu**: 200 OK avec données forecasts + LLM analysis

## Impact

✅ Page LLM Judge fonctionnelle
✅ Frontend peut poster JSON body
✅ Endpoint cohérent avec autres endpoints POST
✅ Pydantic validation automatique des inputs
