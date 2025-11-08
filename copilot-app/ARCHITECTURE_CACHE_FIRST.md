# 🏗️ Architecture Cache-First - Agents Backend + Frontend Lecture Directe

**Date**: 2025-01-27  
**Agent**: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Status**: ✅ **ARCHITECTURE IMPLÉMENTÉE**

---

## 🎯 Principe Fondamental

**Les agents tournent en backend et sauvegardent les données. Le frontend lit directement depuis les fichiers pré-enregistrés.**

```
┌─────────────────┐
│  Agents/Jobs    │  →  Calculent & Sauvegardent  →  `data/*.json`
│  (Backend)      │
└─────────────────┘
         │
         │ APScheduler (cron/interval)
         │
         ▼
┌─────────────────┐
│  storage.io     │  →  `save_json(key, payload)`
│  (Persistence)   │
└─────────────────┘
         │
         │ Fichiers JSON dans `backend/data/`
         │
         ▼
┌─────────────────┐
│  API Endpoints   │  →  `load_json(key)` uniquement
│  (FastAPI)       │     Jamais de calcul à la volée
└─────────────────┘
         │
         │ GET /api/forecasts
         │ GET /api/news/feed
         │ GET /api/brief/daily
         │ etc.
         │
         ▼
┌─────────────────┐
│  Frontend       │  →  Lit via React Query
│  (React)         │     Cache agressif (staleTime élevé)
└─────────────────┘
```

---

## ✅ Architecture Actuelle

### 1. **Scheduler Backend** (`backend/scheduler/app.py`)

Les jobs sont planifiés avec APScheduler :

```python
# News refresh - Toutes les 15 minutes
scheduler.add_job(run_news_ingest, "interval", minutes=15)

# Forecasts - Tous les jours à 2h00
scheduler.add_job(run_forecasts_job, "cron", hour=2, minute=0)

# Weekly brief - Dimanches à 23h30
scheduler.add_job(run_weekly_brief_job, "cron", day_of_week='sun', hour=23, minute=30)

# Backtests - Mercredis à 3h00
scheduler.add_job(run_backtests_job, "cron", day_of_week='wed', hour=3, minute=0)
```

**Démarrage automatique** : Le scheduler démarre au `startup` de l'API (`main.py` ligne 425).

---

### 2. **Jobs Sauvegardent dans `data/`** (`backend/storage/io.py`)

Tous les jobs utilisent `save_json()` :

```python
from storage.io import save_json

# Exemple: dashboard_refresh.py
save_json("dashboard/kpis", kpis, source=["job:dashboard_refresh"], version="v1")
# → Sauvegarde dans: backend/data/dashboard/kpis.json
```

**Structure des fichiers** :
- `data/forecasts.json` - Prévisions ML+LLM
- `data/news_feed.json` - Articles RSS
- `data/brief_daily.json` - Brief quotidien
- `data/brief_weekly.json` - Brief hebdomadaire
- `data/backtests.json` - Résultats backtests
- `data/dashboard/kpis.json` - KPIs dashboard
- `data/correlations/matrix.json` - Matrice corrélations
- etc.

---

### 3. **Endpoints API - Lecture Seulement** (`backend/src/api/main.py`)

**Tous les endpoints utilisent `load_json()` - JAMAIS de calcul à la volée** :

```python
@app.get("/api/forecasts")
async def forecasts(...):
    from storage.io import load_json
    
    # ✅ Charge depuis fichier pré-calculé
    forecasts_data = load_json("forecasts")
    
    if not forecasts_data:
        # ✅ Retourne structure vide mais valide (jamais d'erreur)
        return _ok({"rows": [], "count": 0, ...})
    
    # ✅ Filtre/trie les données chargées (pas de calcul)
    filtered_rows = [r for r in rows if ...]
    
    return _ok({
        "rows": filtered_rows,
        "freshness": forecasts_data.get("freshness"),  # ✅ Toujours présent
        ...
    })
```

**Endpoints vérifiés** :
- ✅ `/api/forecasts` → `load_json("forecasts")`
- ✅ `/api/news/feed` → `load_json("news_feed")`
- ✅ `/api/brief/daily` → `load_json("brief_daily")`
- ✅ `/api/brief/weekly` → `load_json("brief_weekly")`
- ✅ `/api/backtests` → `load_backtests()` (qui utilise `load_json`)
- ✅ `/api/dashboard/kpis` → `load_json("dashboard/kpis")`
- ✅ `/api/correlations/matrix` → `load_json("correlations/matrix")`
- ✅ etc.

---

### 4. **Frontend - Cache Agressif** (`frontend/webapp/src/hooks/`)

Les hooks React Query utilisent un cache long :

```typescript
// Exemple: useForecasts.ts
export function useForecasts(params) {
  return useQuery({
    queryKey: ['forecasts', params],
    queryFn: () => api.get('/api/forecasts', params),
    staleTime: 5 * 60 * 1000,  // ✅ 5 minutes
    cacheTime: 30 * 60 * 1000, // ✅ 30 minutes
    refetchOnWindowFocus: false, // ✅ Pas de refetch automatique
    refetchOnMount: false,       // ✅ Utilise cache si disponible
  });
}
```

**Optimisations** :
- `staleTime` élevé (5-15 minutes selon la donnée)
- `refetchOnWindowFocus: false` (évite refetch inutiles)
- `refetchOnMount: false` (utilise cache si disponible)

---

## 📋 Liste des Jobs Backend

| Job | Fichier | Fréquence | Sauvegarde |
|-----|---------|-----------|------------|
| **News Ingest** | `jobs/news_ingest.py` | 15 min | `data/news_feed.json` |
| **Forecasts** | `jobs/forecasts.py` | Quotidien 2h00 | `data/forecasts.json` |
| **Weekly Brief** | `jobs/weekly_brief.py` | Dimanche 23h30 | `data/brief_weekly.json` |
| **Backtests** | `jobs/backtests_job.py` | Mercredi 3h00 | `data/backtests.json` |
| **Dashboard KPIs** | `jobs/dashboard_refresh.py` | Sur demande | `data/dashboard/kpis.json` |
| **Correlations** | `jobs/correlation_calculator.py` | Sur demande | `data/correlations/matrix.json` |
| **Sector Allocation** | `jobs/sector_allocation.py` | Sur demande | `data/sectors/allocation.json` |
| **Efficient Frontier** | `jobs/efficient_frontier.py` | Sur demande | `data/portfolios/efficient_frontier.json` |
| **Capital Flows** | `jobs/capital_flow.py` | Sur demande | `data/flows/capital.json` |
| **OrderBook** | `jobs/orderbook_ingest.py` | Sur demande | `data/market/orderbook.json` |

---

## 🔧 Règles pour les Agents

### ✅ **DO (À FAIRE)**

1. **Toujours sauvegarder avec `storage.io`** :
   ```python
   from storage.io import save_json
   save_json("ma_cle", mes_donnees, source=["mon_job"], version="v1")
   ```

2. **Endpoints = Lecture seule** :
   ```python
   @app.get("/api/mon-endpoint")
   async def mon_endpoint():
       from storage.io import load_json
       data = load_json("ma_cle")
       if not data:
           return _ok({"items": [], "count": 0})  # ✅ Jamais d'erreur
       return _ok(data)
   ```

3. **Jobs = Calcul + Sauvegarde** :
   ```python
   def run_mon_job():
       # 1. Calculer
       resultat = calculer_donnees()
       
       # 2. Sauvegarder
       save_json("ma_cle", resultat, source=["mon_job"])
       
       return {"status": "completed"}
   ```

4. **Freshness toujours présent** :
   ```python
   # storage.io ajoute automatiquement "freshness"
   # Les endpoints doivent le retourner
   return _ok({
       "data": ...,
       "freshness": data.get("freshness"),  # ✅ Toujours présent
   })
   ```

---

### ❌ **DON'T (À ÉVITER)**

1. **❌ Calcul à la volée dans les endpoints** :
   ```python
   # ❌ MAUVAIS
   @app.get("/api/forecasts")
   async def forecasts():
       # Ne pas calculer ici !
       forecasts = compute_forecasts()  # ❌
       return _ok(forecasts)
   ```

2. **❌ Endpoints qui appellent des jobs directement** :
   ```python
   # ❌ MAUVAIS
   @app.get("/api/forecasts")
   async def forecasts():
       run_forecasts_job()  # ❌ Ne pas faire ça !
       return _ok(...)
   ```

3. **❌ Erreurs si données absentes** :
   ```python
   # ❌ MAUVAIS
   data = load_json("ma_cle")
   if not data:
       raise HTTPException(404, "No data")  # ❌
   
   # ✅ BON
   data = load_json("ma_cle")
   if not data:
       return _ok({"items": [], "count": 0})  # ✅
   ```

---

## 🚀 Workflow Complet

### 1. **Démarrage Backend**

```python
# main.py - startup event
@app.on_event("startup")
async def startup_event():
    # 1. Vérifier données initiales
    if not load_json("forecasts"):
        run_forecasts_job()  # ✅ Génère données initiales
    
    # 2. Démarrer scheduler
    start_scheduler()  # ✅ Jobs tournent en background
```

### 2. **Job S'exécute**

```python
# jobs/forecasts.py
def run_forecasts_job():
    # 1. Calculer
    forecasts = compute_forecasts()
    
    # 2. Sauvegarder
    save_json("forecasts", {"rows": forecasts}, source=["job:forecasts"])
    
    # ✅ Données disponibles dans data/forecasts.json
```

### 3. **Endpoint Sert les Données**

```python
# main.py
@app.get("/api/forecasts")
async def forecasts():
    data = load_json("forecasts")  # ✅ Lit depuis fichier
    return _ok(data)  # ✅ Retourne instantanément
```

### 4. **Frontend Lit**

```typescript
// hooks/useForecasts.ts
const { data } = useForecasts();  // ✅ Lit depuis API (qui lit depuis fichier)
// ✅ Cache React Query évite refetch inutiles
```

---

## 📊 Avantages de cette Architecture

### ✅ **Performance**
- **Endpoints ultra-rapides** : Lecture fichier JSON (~1-5ms)
- **Pas de calcul bloquant** : Frontend ne bloque jamais
- **Cache agressif** : React Query évite refetch inutiles

### ✅ **Fiabilité**
- **Jamais d'erreur** : Endpoints retournent toujours structure valide
- **Données toujours disponibles** : Même si job échoue, dernière version disponible
- **Déconnexion backend** : Frontend peut servir données en cache

### ✅ **Scalabilité**
- **Jobs parallèles** : Plusieurs jobs peuvent tourner simultanément
- **Pas de charge API** : Endpoints ne font pas de calculs lourds
- **Cache distribué** : Fichiers JSON peuvent être partagés (NFS, S3, etc.)

---

## 🔍 Vérification

### Checklist pour Nouveaux Agents

- [ ] Job sauvegarde avec `save_json(key, payload)`
- [ ] Endpoint utilise `load_json(key)` uniquement
- [ ] Endpoint retourne structure vide si `load_json` retourne `None`
- [ ] Endpoint retourne `freshness` dans la réponse
- [ ] Job est ajouté au scheduler (`scheduler/app.py`)
- [ ] Frontend hook utilise `staleTime` élevé
- [ ] Frontend hook désactive `refetchOnWindowFocus`

---

## 📝 Exemple Complet

### Job Backend

```python
# jobs/mon_job.py
from storage.io import save_json
from datetime import datetime

def run_mon_job():
    # Calculer
    resultat = {
        "items": [...],
        "count": len([...]),
    }
    
    # Sauvegarder
    save_json("mon_endpoint", resultat, source=["job:mon_job"], version="v1")
    
    return {"status": "completed"}
```

### Endpoint API

```python
# main.py
@app.get("/api/mon-endpoint")
async def mon_endpoint():
    from storage.io import load_json
    
    data = load_json("mon_endpoint")
    
    if not data:
        return _ok({
            "items": [],
            "count": 0,
            "freshness": datetime.utcnow().isoformat(),
        })
    
    return _ok({
        "items": data.get("items", []),
        "count": data.get("count", 0),
        "freshness": data.get("freshness"),  # ✅ Toujours présent
    })
```

### Frontend Hook

```typescript
// hooks/useMonEndpoint.ts
export function useMonEndpoint() {
  return useQuery({
    queryKey: ['mon-endpoint'],
    queryFn: () => api.get('/api/mon-endpoint'),
    staleTime: 10 * 60 * 1000,  // 10 minutes
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });
}
```

---

## 🎯 Résumé

**Architecture Cache-First = Agents Backend + Frontend Lecture Directe**

1. ✅ **Jobs tournent en background** (APScheduler)
2. ✅ **Jobs sauvegardent dans `data/`** (`storage.io`)
3. ✅ **Endpoints lisent depuis `data/`** (`load_json`)
4. ✅ **Frontend cache agressif** (React Query)

**Status**: ✅ **ARCHITECTURE IMPLÉMENTÉE ET OPÉRATIONNELLE**

