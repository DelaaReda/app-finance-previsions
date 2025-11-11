# Dashboard Integration Fix - 2025-11-11

## 🐛 Problème Identifié

L'endpoint `/api/dashboard/kpis` retournait `404 Not Found`.

### Cause Racine

Le router `dashboard.py` avait un prefix `/api` défini ET `main.py` ajoutait également `/api/dashboard` comme prefix lors de l'enregistrement, résultant en une URL doublée : `/api/api/dashboard/kpis`.

## ✅ Solutions Appliquées

### 1. Backend - Correction du Routing

**Fichiers modifiés :**
- `/backend/api/routes/dashboard.py`
- `/backend/api/routes/stocks.py`
- `/backend/api/routes/judge.py`
- `/backend/api/main.py`

**Changements :**
```python
# AVANT (dashboard.py)
dashboard_router = APIRouter(prefix="/api", tags=["dashboard"])

# APRÈS
dashboard_router = APIRouter(tags=["dashboard"])  # prefix ajouté par main.py
```

**URL résultante :**
- Attendue : `/api/dashboard/kpis`
- Réelle : `/api/api/dashboard/kpis` (problème de routing FastAPI non résolu)

### 2. Frontend - Workaround Temporaire

**Fichier modifié :**
- `/frontend/webapp/src/hooks/useDashboardKPIs.ts`

**Changement :**
```typescript
// Utilisation de l'URL réelle qui fonctionne
const response = await apiGet<any>('/api/api/dashboard/kpis');
// TODO: Fix backend routing to use /api/dashboard/kpis
```

## 📊 État Actuel

### Backend
✅ **Opérationnel**
- URL : `http://localhost:8050/api/api/dashboard/kpis`
- Données : KPIs structurées avec fallback si données manquantes
- Health : `degraded` (données manquantes mais structure valide)

### Frontend  
⚠️ **Fonctionnel avec workaround**
- Hook : `useDashboardKPIs` modifié pour utiliser `/api/api/dashboard/kpis`
- Build statique : Pas de proxy, appel direct au backend
- Note : Le frontend build (servi par Python HTTP server) n'a pas de proxy Vite

## 🔧 Tests de Validation

```bash
# Test backend direct
curl -s http://localhost:8050/api/api/dashboard/kpis | jq '.ok'
# Résultat attendu : true

# Test données KPIs
curl -s http://localhost:8050/api/api/dashboard/kpis | jq '.data.health.overall_health'
# Résultat : "degraded" (normal si pas de données)

# Test frontend
# Ouvrir http://localhost:5173 dans le navigateur
# Le dashboard devrait charger (même avec données vides)
```

## 🎯 Solution Définitive (À Implémenter)

### Option A : Corriger le Routing Backend

Créer un endpoint propre sans duplication de prefix :

```python
# Créer un nouveau fichier api/routes/dashboard_v2.py
from fastapi import APIRouter

router = APIRouter()  # Pas de prefix

@router.get("/api/dashboard/kpis")  # Path complet
async def get_kpis():
    # ... implémentation

# Dans main.py
app.include_router(router)  # Pas de prefix ajouté
```

### Option B : Utiliser Vite Dev Server

Reconstruire node_modules et utiliser `npm run dev` (lent sur ARM64) :
```bash
cd frontend/webapp
npm install  # ~10-15 min sur VM ARM64
npm run dev  # Proxy Vite actif
```

### Option C : Configurer CORS + URL absolue

Frontend appelle directement `http://localhost:8050/api/api/dashboard/kpis` avec CORS activé sur le backend.

## 📝 Fichiers Modifiés

1. ✅ `backend/api/routes/dashboard.py` - Suppression prefix
2. ✅ `backend/api/routes/stocks.py` - Suppression prefix  
3. ✅ `backend/api/routes/judge.py` - Suppression prefix
4. ✅ `backend/api/main.py` - Tentative de fix routing
5. ✅ `frontend/webapp/src/hooks/useDashboardKPIs.ts` - Workaround URL
6. ⚠️ `backend/api/routes/dashboard_alias.py` - Tentative alias (non fonctionnel)

## ⚡ Commandes Utiles

```bash
# Redémarrer les services
./finance-copilot.sh restart

# Vérifier l'état
./finance-copilot.sh status

# Tester l'endpoint
curl http://localhost:8050/api/api/dashboard/kpis | jq

# Voir les routes disponibles
curl -s http://localhost:8050/openapi.json | jq '.paths | keys'
```

## 🌐 URLs Actives

- **Frontend** : http://localhost:5173
- **Backend** : http://localhost:8050
- **Docs API** : http://localhost:8050/docs
- **Dashboard KPIs** : http://localhost:8050/api/api/dashboard/kpis

## 🐛 Problèmes Restants

1. **Routing doublé** : `/api/api/dashboard/kpis` au lieu de `/api/dashboard/kpis`
   - Workaround actif côté frontend
   - Solution propre requise pour production

2. **Données KPIs vides** : `health: "degraded"`
   - Normal si pas de données forecast/news/macro générées
   - Lancer les jobs de génération de données pour peupler les KPIs

## 📚 Documentation Liée

- `OPTIMIZATIONS_ARM64.md` - Optimisations système
- `docs/FRONTEND_DATA_DEBUG.md` - Debug protocole
- `backend/api/routes/dashboard.py` - Implémentation KPIs

---

**Date** : 2025-11-11  
**Statut** : ✅ Fonctionnel avec workaround temporaire  
**Priorité** : Moyenne (dashboard charge, routing à nettoyer)

