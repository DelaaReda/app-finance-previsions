# ✅ Checklist de Vérification UI

**Date**: 2025-01-27  
**Agent**: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Objectif**: Vérifier que toutes les données s'affichent correctement dans l'UI

---

## 🔍 Instructions de Vérification

### 1. **Démarrer les Services**

```bash
# Démarrer backend + frontend
./finance-copilot.sh start

# Vérifier que les services tournent
ps aux | grep -E "uvicorn|vite"
```

### 2. **Ouvrir le Navigateur**

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8050/docs`

### 3. **Ouvrir DevTools**

- **F12** ou **Cmd+Option+I** (Mac) / **Ctrl+Shift+I** (Windows)
- Onglet **Network** pour voir les requêtes
- Onglet **Console** pour voir les erreurs

---

## 📋 Checklist par Page

### ✅ **Dashboard** (`/dashboard`)

**URL**: `http://localhost:5173/dashboard`

**À vérifier**:
- [ ] Page charge en < 3 secondes
- [ ] **StatsGrid** affiche 4 métriques (Prévisions, Confiance Moy., Hit Rate, News)
- [ ] Si pas de données KPIs → Fallback vers KPIs Tremor s'affiche
- [ ] **Skeleton** visible pendant le chargement initial
- [ ] Pas d'erreur dans la console
- [ ] Dans Network → Requête `/api/dashboard/kpis` répond en < 2s

**Screenshot à prendre**:
- État initial (loading)
- État avec données (StatsGrid visible)
- État sans données (fallback Tremor)

---

### ✅ **Portfolios** (`/portfolios`)

**URL**: `http://localhost:5173/portfolios`

**À vérifier**:
- [ ] Page charge en < 3 secondes
- [ ] **3 onglets** visibles (Allocation par Secteur, Treemap, Frontière Efficiente)
- [ ] **Onglet "Allocation par Secteur"**:
  - [ ] Si données → SectorWheel + TreemapChart affichés
  - [ ] Si pas de données → EmptyState avec message clair
- [ ] **Onglet "Treemap"**:
  - [ ] Si données → TreemapChart affiché
  - [ ] Si pas de données → EmptyState
- [ ] **Onglet "Frontière Efficiente"**:
  - [ ] Si données → EfficientFrontier affiché
  - [ ] Si pas de données → EmptyState
- [ ] **Skeleton** visible pendant le chargement
- [ ] Pas d'erreur dans la console

**Screenshot à prendre**:
- État avec données (widgets visibles)
- État sans données (EmptyState)

---

### ✅ **Diagnostics** (`/diagnostics`)

**URL**: `http://localhost:5173/diagnostics`

**À vérifier**:
- [ ] Page charge en < 3 secondes
- [ ] **2 onglets** visibles (Réseau de Corrélations, Matrice de Corrélations)
- [ ] **Onglet "Réseau de Corrélations"**:
  - [ ] **Slider** pour ajuster le seuil (0.0 - 1.0)
  - [ ] Si données → CorrelationNetwork affiché
  - [ ] Si pas de données → EmptyState
- [ ] **Onglet "Matrice de Corrélations"**:
  - [ ] Si données → CorrelationHeatmap affiché
  - [ ] Si pas de données → EmptyState
- [ ] **Skeleton** visible pendant le chargement
- [ ] Pas d'erreur dans la console

**Screenshot à prendre**:
- État avec données (graphiques visibles)
- État sans données (EmptyState)
- Slider ajusté à différentes valeurs

---

### ✅ **Analytics** (`/analytics`)

**URL**: `http://localhost:5173/analytics`

**À vérifier**:
- [ ] Page charge en < 3 secondes
- [ ] Si données → **SankeyDiagram** affiché avec nodes et links
- [ ] Si pas de données → **EmptyState** avec message clair
- [ ] **Skeleton** visible pendant le chargement
- [ ] Pas d'erreur dans la console
- [ ] Dans Network → Requête `/api/flows/capital` répond en < 3s

**Screenshot à prendre**:
- État avec données (SankeyDiagram visible)
- État sans données (EmptyState)

---

### ✅ **Trading** (`/trading`)

**URL**: `http://localhost:5173/trading`

**À vérifier**:
- [ ] Page charge en < 3 secondes
- [ ] **Select** pour choisir le ticker (AAPL par défaut)
- [ ] **Button "Rafraîchir** visible
- [ ] Si données → **OrderBook** affiché avec bids/asks
- [ ] Si pas de données → **EmptyState** avec bouton "Rafraîchir"
- [ ] **Skeleton** visible pendant le chargement
- [ ] **Auto-refresh** toutes les 10 secondes (vérifier dans Network)
- [ ] Pas d'erreur dans la console

**Screenshot à prendre**:
- État avec données (OrderBook visible)
- État sans données (EmptyState)
- Changement de ticker (MSFT, NVDA, etc.)

---

## ⚡ Vérification des Performances

### Temps de Chargement

**Dans DevTools → Network**:
- [ ] `/api/dashboard/kpis` → < 2s
- [ ] `/api/correlations/matrix` → < 3s
- [ ] `/api/correlations/network` → < 3s
- [ ] `/api/stocks/sectors` → < 2s
- [ ] `/api/backtests/efficient_frontier` → < 3s
- [ ] `/api/flows/capital` → < 3s
- [ ] `/api/orderbook?ticker=AAPL` → < 2s

### Cache

**Dans DevTools → Network**:
- [ ] Recharger la page → Les requêtes doivent être mises en cache
- [ ] Temps de réponse < 100ms pour requêtes en cache
- [ ] Pas de refetch automatique quand on revient sur l'onglet

---

## 🐛 Vérification des Erreurs

### Console (DevTools → Console)

**À vérifier**:
- [ ] Aucune erreur rouge
- [ ] Aucun warning critique
- [ ] Messages de log normaux uniquement

### Network (DevTools → Network)

**À vérifier**:
- [ ] Toutes les requêtes retournent **200 OK**
- [ ] Aucune requête **404** ou **500**
- [ ] Taille des réponses raisonnable (< 1MB)

---

## 📸 Screenshots à Prendre

### Pour chaque page :

1. **État Loading** (Skeleton visible)
2. **État avec Données** (Widgets affichés)
3. **État sans Données** (EmptyState visible)
4. **État Erreur** (si applicable)

### Screenshots spécifiques :

- **Dashboard**: StatsGrid avec 4 métriques
- **Portfolios**: Les 3 onglets avec widgets
- **Diagnostics**: Slider ajusté + graphiques
- **Analytics**: SankeyDiagram avec flux
- **Trading**: OrderBook avec bids/asks + changement de ticker

---

## ✅ Résultat Attendu

### Performance
- ⚡ Temps de chargement initial: **1-3s**
- 💾 Cache efficace: **< 100ms** pour requêtes en cache
- 🔄 Pas de refetch inutile

### Affichage
- ✅ **Skeleton** pendant le chargement
- ✅ **Widgets** si données disponibles
- ✅ **EmptyState** si pas de données
- ✅ **Pas d'erreur** dans la console

### Interactions
- ✅ Changement d'onglet fonctionne
- ✅ Slider ajuste le seuil (Diagnostics)
- ✅ Select change le ticker (Trading)
- ✅ Boutons refresh fonctionnent

---

## 🚨 Problèmes à Signaler

Si vous observez :
- ❌ Temps de chargement > 5s
- ❌ Erreurs dans la console
- ❌ Widgets ne s'affichent pas même avec données
- ❌ Refetch automatique à chaque focus
- ❌ Crash de l'application

**→ Signaler avec screenshots et logs**

---

**Status**: ✅ **CHECKLIST PRÊTE POUR VÉRIFICATION MANUELLE**

