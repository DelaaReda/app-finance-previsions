# UI-STABILIZATION-001 : Frontend Stability Fixes - Plan

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-07  
**Mission** : Stabiliser l'UI - corriger bugs identifiés par l'équipe  
**Points estimés** : +120  
**Priorité** : 🔥 CRITICAL (tests échouent, UI instable)

---

## 🎯 Objectif

Corriger tous les bugs frontend identifiés dans les rapports d'équipe :
- ✅ Ajouter data-testid manquants (tests Playwright)
- ✅ Corriger hooks incompatibles
- ✅ Éliminer console errors
- ✅ Améliorer safe access patterns
- ✅ Tests passent à > 90%

---

## 🔍 Problèmes Identifiés (V0_BUG_REPORT.md)

### Backend (pas mon scope direct)
1. ❌ News Feed API retourne 0 articles
2. ❌ Forecasts API retourne 0 rows
3. ❌ Brief Daily API retourne 0 signals/risks

### Frontend (MON SCOPE - je corrige!)
1. ❌ data-testid manquants (68/85 tests échouent)
2. ❌ Hook useForecasts incompatible (modifié par autre agent)
3. ❌ Console errors (9 erreurs)
4. ❌ Navigation elements manquants

---

## ✅ Corrections à Appliquer

### 1. Ajouter data-testid Manquants

**Pages à corriger** :

#### Forecasts Page
```typescript
// src/pages/ForecastsMinimal.tsx
<div data-testid="forecasts-pro">
<table data-testid="forecast-table">
```

#### Macro Page
```typescript
// src/pages/Macro.tsx
<div data-testid="macro-board">
```

#### Stocks Page
```typescript
// src/pages/Stocks.tsx
<div data-testid="stocks-screener">
```

#### News Page
```typescript
// src/pages/News.tsx
<div data-testid="news-feed">
// Ajouter texte "Filtres" visible
```

#### Dashboard KPIs
```typescript
// src/components/... (KPI cards)
<Card data-testid="metric-card">
```

#### Health Page
```typescript
// src/pages/Health.tsx
<div data-testid="health-status-banner">
<Card data-testid="dataset-health-card">
```

---

### 2. Vérifier/Corriger useForecasts.ts

**Problème** : Autre agent a modifié le hook
**Impact** : Type incompatible, composants cassés

**Action** :
- Lire le hook actuel
- Vérifier compatibilité avec composants
- Ajouter safe access si nécessaire
- Adapter ou restaurer selon besoins

---

### 3. Ajouter Navigation Elements

**Problème** : Test "all pages should have navigation" échoue
**Solution** : S'assurer que AppShell a `role="navigation"` ou balises `<nav>`

---

### 4. Corriger Console Errors

**Selon V0_CONSOLE_ERRORS_FIXES.md** :
- ✅ News 422 errors : Déjà corrigé
- ✅ Forecasts 404 : Déjà corrigé
- ✅ Context/Intelligence/Recommendations 404 : Déjà corrigé avec mocks

**À vérifier** :
- S'assurer que les corrections sont bien présentes
- Pas de régression

---

## 📊 Tests à Faire Passer

### Integration Tests (integration-data.spec.ts)
**Objectif** : 27/30 (90%)

- Health endpoint → dashboard loads ✅
- Macro series → widgets render ✅
- Stocks prices → screener renders ✅
- News feed → lists cards ❌ (API vide)
- Forecasts → widget renders ❌ (API vide)
- Brief daily → page renders ❌ (API vide)

### Contract Guards (contract-guards.spec.ts)
**Objectif** : 70/85 (82%)

- Dashboard data-testid ✅
- Forecasts data-testid ❌
- Backtests data-testid ❌
- Health data-testid ❌
- Macro data-testid ❌
- Stocks data-testid ❌
- News data-testid ❌

---

## 🎯 Plan d'Action

### Phase 1 : data-testid (Quick Wins - 1h)
1. ✅ ForecastsMinimal.tsx - ajouter "forecasts-pro"
2. ✅ Macro.tsx - ajouter "macro-board"
3. ✅ Stocks.tsx - ajouter "stocks-screener"
4. ✅ News.tsx - ajouter "news-feed"
5. ✅ Health.tsx - ajouter "health-status-banner", "dataset-health-card"
6. ✅ Dashboard metric cards - ajouter "metric-card"

### Phase 2 : Safe Access Verification (30min)
1. ✅ Vérifier useForecasts.ts compatibilité
2. ✅ Ajouter guards si nécessaire
3. ✅ Vérifier tous les `.map()` sont safe

### Phase 3 : Navigation Fix (15min)
1. ✅ Ajouter role="navigation" sur AppShell
2. ✅ Vérifier liens visibles

### Phase 4 : Documentation (15min)
1. ✅ Créer PROOF avec screenshots
2. ✅ Documenter ce qui reste (backend)

---

## 📈 Résultats Attendus

### Avant Corrections
- Tests Integration : 12/30 (40%)
- Tests Contract Guards : 17/85 (20%)
- Console Errors : 9
- data-testid Coverage : 30%

### Après Corrections
- Tests Integration : 15/30 (50%) - limité par backend vide
- Tests Contract Guards : 70/85 (82%) - data-testid ajoutés
- Console Errors : 0
- data-testid Coverage : 100%

**Note** : Les tests integration ne pourront pas tous passer tant que le backend ne génère pas de données. Mais on peut corriger tout ce qui est frontend!

---

**Signé** : ELENA-39  
**Status** : Starting corrections
