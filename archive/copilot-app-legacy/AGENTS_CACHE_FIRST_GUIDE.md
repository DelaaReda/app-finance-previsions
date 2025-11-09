# 📘 Guide Agents - Architecture Cache-First

**Date**: 2025-01-27  
**Agent**: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Status**: ✅ **GUIDE POUR TOUS LES AGENTS**

---

## 🎯 Principe Fondamental

**Les agents tournent en backend et sauvegardent les données. Le frontend lit directement depuis les fichiers pré-enregistrés.**

```
Agent/Job → Calcule → Sauvegarde (storage.io) → Fichier JSON
                                              ↓
                                    Endpoint API (load_json)
                                              ↓
                                    Frontend (React Query)
```

---

## ✅ Règles Strictes pour les Agents

### 1. **Jobs = Calcul + Sauvegarde UNIQUEMENT**

```python
# ✅ BON - jobs/mon_job.py
from storage.io import save_json

def run_mon_job():
    # 1. Calculer les données
    resultat = calculer_donnees()
    
    # 2. Sauvegarder avec storage.io
    save_json("ma_cle", resultat, source=["job:mon_job"], version="v1")
    
    return {"status": "completed"}
```

**❌ MAUVAIS** :
- ❌ Ne pas appeler l'API depuis un job
- ❌ Ne pas calculer dans les endpoints
- ❌ Ne pas sauvegarder dans les endpoints (sauf cas exceptionnel)

---

### 2. **Endpoints = Lecture Seulement**

```python
# ✅ BON - main.py
@app.get("/api/mon-endpoint")
async def mon_endpoint():
    from storage.io import load_json
    
    # Charger depuis fichier pré-calculé
    data = load_json("ma_cle")
    
    if not data:
        # ✅ Retourner structure vide mais valide
        return _ok({
            "items": [],
            "count": 0,
            "freshness": datetime.utcnow().isoformat(),
        })
    
    # ✅ Filtrer/trier les données chargées (pas de calcul)
    filtered = [item for item in data.get("items", []) if ...]
    
    return _ok({
        "items": filtered,
        "count": len(filtered),
        "freshness": data.get("freshness"),  # ✅ Toujours présent
    })
```

**❌ MAUVAIS** :
- ❌ Ne pas calculer dans les endpoints
- ❌ Ne pas appeler des fonctions de calcul lourdes
- ❌ Ne pas faire d'appels API externes (sauf cas exceptionnel)

---

### 3. **Scheduler = Planification des Jobs**

```python
# ✅ BON - scheduler/app.py
from backend.jobs.mon_job import run_mon_job

scheduler.add_job(
    func=run_mon_job,
    trigger="cron",
    hour=2,
    minute=0,  # Tous les jours à 2h00
    id='mon_job',
    name='Mon job quotidien',
)
```

**Fréquences recommandées** :
- **News** : 15 minutes (données très dynamiques)
- **Forecasts** : Quotidien (calculs lourds)
- **Briefs** : Quotidien/Hebdomadaire
- **Backtests** : Hebdomadaire (calculs très lourds)
- **KPIs** : Sur demande ou toutes les heures

---

## 📋 Checklist pour Nouveaux Agents

### Étape 1 : Créer le Job

- [ ] Créer `jobs/mon_job.py`
- [ ] Implémenter `run_mon_job()` qui :
  - [ ] Calcule les données
  - [ ] Utilise `save_json(key, payload, source=[...])`
  - [ ] Retourne `{"status": "completed"}`

### Étape 2 : Ajouter au Scheduler

- [ ] Importer le job dans `scheduler/app.py`
- [ ] Ajouter `scheduler.add_job(...)` avec fréquence appropriée
- [ ] Tester le job manuellement : `python -m backend.jobs.mon_job`

### Étape 3 : Créer l'Endpoint

- [ ] Créer endpoint dans `main.py` : `@app.get("/api/mon-endpoint")`
- [ ] Utiliser `load_json("ma_cle")` uniquement
- [ ] Retourner structure vide si `load_json` retourne `None`
- [ ] Inclure `freshness` dans la réponse

### Étape 4 : Créer le Hook Frontend

- [ ] Créer `hooks/useMonEndpoint.ts`
- [ ] Utiliser React Query avec :
  - [ ] `staleTime: 5-15 minutes` (selon fréquence job)
  - [ ] `refetchOnWindowFocus: false`
  - [ ] `refetchOnMount: false` (si données peu changeantes)

### Étape 5 : Tester

- [ ] Vérifier que le job sauvegarde dans `data/ma_cle.json`
- [ ] Vérifier que l'endpoint lit depuis le fichier
- [ ] Vérifier que le frontend affiche les données
- [ ] Vérifier que `freshness` est présent

---

## 🔍 Vérification Architecture

### Endpoints à Vérifier

| Endpoint | Utilise `load_json` ? | Job Existe ? | Status |
|----------|----------------------|--------------|--------|
| `/api/forecasts` | ✅ | ✅ `forecasts.py` | ✅ OK |
| `/api/news/feed` | ✅ | ✅ `news_ingest.py` | ✅ OK |
| `/api/brief/daily` | ✅ | ✅ `weekly_brief.py` | ✅ OK |
| `/api/brief/weekly` | ✅ | ✅ `weekly_brief.py` | ✅ OK |
| `/api/backtests` | ✅ | ✅ `backtests_job.py` | ✅ OK |
| `/api/dashboard/kpis` | ✅ | ✅ `dashboard_refresh.py` | ✅ OK |
| `/api/stocks/prices` | ❌ | ❌ | ⚠️ À CORRIGER |
| `/api/stocks/meta` | ❌ | ❌ | ⚠️ À CORRIGER |
| `/api/stocks/screener` | ❌ | ❌ | ⚠️ À CORRIGER |
| `/api/macro/series` | ❌ | ⚠️ `macro_ingest.py` existe | ⚠️ À VÉRIFIER |
| `/api/macro/snapshot` | ❌ | ⚠️ `macro_ingest.py` existe | ⚠️ À VÉRIFIER |

---

## 🚨 Endpoints à Corriger

### `/api/stocks/prices`

**Problème** : Calcule à la volée avec `get_price_history()`

**Solution** :
1. Créer `jobs/stocks_prices_refresh.py` qui :
   - Calcule les prix pour tous les tickers
   - Sauvegarde avec `save_json("stocks/prices", {...})`
2. Modifier endpoint pour utiliser `load_json("stocks/prices")`

### `/api/stocks/meta` et `/api/stocks/screener

**Problème** : Calcule à la volée avec `_compute_stock_metrics()`

**Solution** :
1. Créer `jobs/stocks_metrics_refresh.py` qui :
   - Calcule les métriques pour tous les tickers
   - Sauvegarde avec `save_json("stocks/metrics", {...})`
2. Modifier endpoints pour utiliser `load_json("stocks/metrics")`

### `/api/macro/series` et `/api/macro/snapshot`

**Problème** : Calcule à la volée avec `load_macro_forecast_rows()`

**Solution** :
1. Vérifier que `jobs/macro_ingest.py` sauvegarde correctement
2. Modifier endpoints pour utiliser `load_json("macro/series")` et `load_json("macro/snapshot")`

---

## 📝 Exemple Complet

### Job Backend

```python
# jobs/stocks_metrics_refresh.py
from storage.io import save_json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def run_stocks_metrics_job():
    """Calcule et sauvegarde les métriques de tous les tickers"""
    logger.info("Starting stocks metrics refresh job...")
    
    from backend.src.api.main import DEFAULT_STOCKS_UNIVERSE, _compute_stock_metrics
    
    # Calculer pour tous les tickers
    metrics = {}
    for ticker in DEFAULT_STOCKS_UNIVERSE:
        try:
            metrics[ticker] = _compute_stock_metrics(ticker)
        except Exception as e:
            logger.warning(f"Failed to compute metrics for {ticker}: {e}")
            metrics[ticker] = {"error": str(e)}
    
    # Sauvegarder
    payload = {
        "metrics": metrics,
        "tickers": list(metrics.keys()),
        "count": len(metrics),
    }
    
    save_json("stocks/metrics", payload, source=["job:stocks_metrics_refresh"], version="v1")
    
    logger.info(f"✅ Saved metrics for {len(metrics)} tickers")
    return {"status": "completed", "count": len(metrics)}
```

### Endpoint API

```python
# main.py
@app.get("/api/stocks/meta")
async def stocks_meta(tickers: Optional[str] = Query(None)):
    from storage.io import load_json
    
    # Charger depuis fichier pré-calculé
    data = load_json("stocks/metrics")
    
    if not data:
        return _ok({
            "items": [],
            "count": 0,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        })
    
    # Filtrer par tickers si demandé
    requested = _parse_csv_list(tickers) if tickers else None
    metrics = data.get("metrics", {})
    
    if requested:
        metrics = {t: metrics.get(t) for t in requested if t in metrics}
    
    # Formater pour l'API
    items = [{
        "ticker": ticker,
        "name": m.get("name"),
        "sector": m.get("sector"),
        "industry": m.get("industry"),
        "weight": None,
    } for ticker, m in metrics.items() if not m.get("error")]
    
    return _ok({
        "items": items,
        "count": len(items),
        "updated_at": data.get("freshness", datetime.utcnow().isoformat()),
    })
```

### Scheduler

```python
# scheduler/app.py
from backend.jobs.stocks_metrics_refresh import run_stocks_metrics_job

# Ajouter au scheduler
scheduler.add_job(
    func=run_stocks_metrics_job,
    trigger="cron",
    hour=1,  # Tous les jours à 1h00
    minute=0,
    id='stocks_metrics_job',
    name='Refresh stocks metrics',
)
```

---

## 🎯 Résumé

**Architecture Cache-First = Agents Backend + Frontend Lecture Directe**

1. ✅ **Jobs calculent et sauvegardent** (`save_json`)
2. ✅ **Endpoints lisent uniquement** (`load_json`)
3. ✅ **Scheduler planifie les jobs** (APScheduler)
4. ✅ **Frontend cache agressif** (React Query)

**Tous les agents doivent suivre cette architecture !**

---

**Status**: ✅ **GUIDE CRÉÉ - À SUIVRE PAR TOUS LES AGENTS**

