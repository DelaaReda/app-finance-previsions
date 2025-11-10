# 🛠️ Roadmap de Corrections - Finance Copilot

**Date**: 2025-11-10
**Priorité**: 🔥 Critique

## 📋 Résumé des problèmes à corriger

| Priorité | Problème | Fichier | Status |
|----------|----------|---------|--------|
| 🔥 | `/api/forecasts` 404 | `api/routes/forecasts.py` | À vérifier |
| ⚙️ | KPIs Dashboard à 0% | `api/routes/dashboard.py` | À corriger |
| ⚠️ | `/api/stocks/top` 404 | `api/routes/stocks.py` | À créer |
| 🧠 | Judge LLM manquant | `api/routes/judge.py` | À créer |
| 📊 | Macro pas auto-refresh | `jobs/macro_series_snapshot.py` | À améliorer |
| 🧩 | DEV DEBUG visible | `frontend/App.tsx` | À masquer |
| 🌐 | Textes FR/EN mélangés | Multiple | À uniformiser |

---

## ✅ Corrections à appliquer

### 1. 🔥 Vérifier `/api/forecasts` (PRIORITÉ 1)

**Problème**: Endpoint retourne 404

**Vérifications**:
- [ ] Router `forecasts_router` est bien exporté dans `api/routes/forecasts.py`
- [ ] Router est bien enregistré dans `api/main.py` ligne 418
- [ ] Le préfixe `/api` est correct
- [ ] Tester: `curl http://localhost:8050/api/forecasts?horizon=short`

**Solution**: Si le router n'est pas enregistré, ajouter dans `main.py`:
```python
from api.routes.forecasts import forecasts_router
app.include_router(forecasts_router, prefix="/api", tags=["forecasts"])
```

---

### 2. ⚙️ Corriger KPIs Dashboard (PRIORITÉ 2)

**Problème**: Tous les KPIs affichent 0%

**Fichier**: `api/routes/dashboard.py`

**Corrections nécessaires**:
- [ ] Vérifier que `forecast_rows` contient bien des données
- [ ] Calculer correctement `high_confidence_pct` (confiance > 0.6)
- [ ] Calculer `success_rate` basé sur les prévisions passées
- [ ] S'assurer que `active_forecasts` compte bien les rows

**Code à vérifier** (lignes 220-280):
```python
# Calculer high_confidence_pct
high_conf_count = sum(1 for row in forecast_rows if row.get("confidence", 0) > HIGH_CONF_THRESHOLD)
high_confidence_pct = (high_conf_count / len(forecast_rows) * 100) if forecast_rows else 0.0

# Calculer success_rate (basé sur historique si disponible)
success_rate = calculate_success_rate_from_history(forecast_rows)  # À implémenter

# Active forecasts
active_forecasts = len(forecast_rows)
```

---

### 3. ⚠️ Créer `/api/stocks/top` (PRIORITÉ 3)

**Problème**: Endpoint manquant

**Fichier**: `api/routes/stocks.py`

**À créer**:
```python
@router.get("/stocks/top")
def get_top_stocks(
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("score", description="Sort by: score, change_1d, momentum_30d, mcap")
):
    """Get top stocks by score, momentum, or market cap."""
    try:
        from storage.io import load_json
        
        # Load stocks data
        prices_data = load_json("stocks/prices") or load_json("stocks_prices") or {}
        metrics_data = load_json("stocks/metrics") or {}
        
        # Extract and sort stocks
        stocks_list = build_stocks_list(prices_data, metrics_data)
        
        # Sort by requested field
        if sort_by == "change_1d":
            stocks_list.sort(key=lambda x: abs(x.get("change", 0)), reverse=True)
        elif sort_by == "momentum_30d":
            stocks_list.sort(key=lambda x: x.get("momentum_30d", 0), reverse=True)
        elif sort_by == "mcap":
            stocks_list.sort(key=lambda x: x.get("market_cap", 0), reverse=True)
        else:  # score or default
            stocks_list.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return ok({
            "stocks": stocks_list[:limit],
            "count": len(stocks_list[:limit]),
            "sort_by": sort_by,
            "generated_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in stocks_top: {e}", exc_info=True)
        return ok({
            "stocks": [],
            "count": 0,
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat()
        })
```

---

### 4. 🧠 Créer endpoint GET `/api/judge` (PRIORITÉ 4)

**Problème**: Section Judge n'apparaît pas

**Fichier**: `api/routes/judge.py` (à créer)

**À créer**:
```python
from fastapi import APIRouter
from storage.io import load_json
from core.response import ok

router = APIRouter()

@router.get("/judge")
def get_judge_verdicts(
    limit: int = Query(20, ge=1, le=100),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0)
):
    """Get LLM judge verdicts for tickers."""
    try:
        # Load judge data (généré par validate_and_generate_data.py)
        judge_data = load_json("llm_judge") or {}
        
        rows = judge_data.get("rows", [])
        
        # Filter by confidence
        if min_confidence > 0:
            rows = [r for r in rows if r.get("confidence", 0) >= min_confidence]
        
        # Sort by confidence * expected_return
        rows.sort(
            key=lambda x: x.get("confidence", 0) * abs(x.get("expected_return", 0)),
            reverse=True
        )
        
        return ok({
            "verdicts": rows[:limit],
            "count": len(rows[:limit]),
            "stats": judge_data.get("derived", {}).get("stats", {}),
            "generated_at": judge_data.get("generated_at", datetime.utcnow().isoformat())
        })
    except Exception as e:
        logger.error(f"Error in get_judge_verdicts: {e}", exc_info=True)
        return ok({
            "verdicts": [],
            "count": 0,
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat()
        })

judge_router = router
```

**Enregistrer dans `main.py`**:
```python
("judge", "api.routes.judge", "judge_router"),
```

---

### 5. 📊 Ajouter auto-refresh Macro (PRIORITÉ 5)

**Problème**: Données macro datent de 5 jours

**Fichier**: `scheduler/master_scheduler.py` ou `scheduler/app.py`

**À ajouter**:
```python
# Macro refresh job - daily at 6 AM
scheduler.add_job(
    func=self._run_macro_refresh_job,
    trigger="cron",
    hour=6,
    minute=0,
    id='macro_refresh_job',
    name='Refresh macro series data',
    replace_existing=True
)

def _run_macro_refresh_job(self):
    """Run macro series snapshot job"""
    try:
        from jobs.macro_series_snapshot import main
        result = main([])
        logger.info(f"Macro refresh job completed with code {result}")
    except Exception as e:
        logger.error(f"Macro refresh job failed: {e}")
```

---

### 6. 🧩 Masquer DEV DEBUG (PRIORITÉ 6)

**Problème**: Panneau visible en production

**Fichier**: `frontend/webapp/src/App.tsx`

**À corriger**:
```typescript
// Déjà fait dans App.tsx mais vérifier
const isDev = import.meta.env.DEV;
{isDev && <DevDebugPanel />}
```

**Vérifier aussi**: `frontend/webapp/src/components/DevDebugPanel.tsx`

---

### 7. 🌐 Uniformiser langue FR (PRIORITÉ 7)

**Problème**: Mélange FR/EN

**Fichiers à corriger**:
- `frontend/webapp/src/pages/Dashboard.tsx`
- `frontend/webapp/src/components/widgets/*.tsx`
- Tous les composants avec textes en anglais

**Créer**: `frontend/webapp/src/i18n/fr.ts`
```typescript
export const fr = {
  refresh: "Rafraîchir",
  adaptive_mode: "Mode adaptatif",
  forecast_active: "Prévisions actives",
  high_confidence: "Haute confiance",
  success_rate: "Taux de réussite",
  // ... etc
}
```

---

### 8. 📰 Nettoyer actualités (PRIORITÉ 8)

**Problème**: Doublons et liens vides

**Fichier**: `api/routes/news.py`

**À corriger**:
```python
@router.get("/news/feed")
def get_news_feed(...):
    # ... existing code ...
    
    # Remove duplicates by URL
    seen_urls = set()
    unique_articles = []
    for article in articles:
        url = article.get("url") or article.get("link")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    # Filter out articles with empty URLs
    unique_articles = [a for a in unique_articles if a.get("url") or a.get("link")]
    
    return ok({
        "articles": unique_articles,
        "count": len(unique_articles),
        ...
    })
```

---

## 🚀 Ordre d'exécution

1. ✅ Vérifier `/api/forecasts` (5 min)
2. ✅ Corriger KPIs Dashboard (15 min)
3. ✅ Créer `/api/stocks/top` (10 min)
4. ✅ Créer `/api/judge` GET (20 min)
5. ✅ Ajouter macro auto-refresh (10 min)
6. ✅ Masquer DEV DEBUG (5 min)
7. ✅ Uniformiser langue (30 min)
8. ✅ Nettoyer actualités (15 min)

**Total estimé**: ~2h

---

## ✅ Checklist de validation

Après chaque correction:
- [ ] Tester l'endpoint avec `curl`
- [ ] Vérifier les logs backend
- [ ] Tester dans le frontend
- [ ] Vérifier qu'aucune régression n'est introduite

