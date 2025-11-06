# V0 Bug Report - Tests d'Intégration

**Date**: 2025-11-06
**Tests Exécutés**: 30 tests d'intégration (no mocks)
**Score**: 12/30 passés (40%)

## 🔴 BUGS CRITIQUES - Backend API

### 1. News Feed API Ne Retourne Pas de Données

**Endpoint**: `GET /api/news/feed?tickers=SPY,QQQ&limit=50&sort=recent`

**Problème**:
- Chromium: `resp.ok() = false` (échec HTTP)
- Firefox/Chrome/Safari: `articles.length = 0` (pas d'articles)

**Test Failing**:
```typescript
// tests/ui/integration-data.spec.ts:33
const r = await page.request.get('/api/news/feed', {
  params: { tickers: 'SPY,QQQ', limit: '50', sort: 'recent' }
})
const feed = await json<any>(r) // ÉCHOUE ICI (chromium)
const articles = payload?.articles ?? []
expect(articles.length).toBeGreaterThan(0) // ÉCHOUE ICI (autres navigateurs)
```

**Impact**: Page `/news` ne peut pas afficher d'articles

**Solution Requise**:
- Vérifier que le backend génère des articles news
- Vérifier le endpoint `/api/news/feed` retourne bien `{ok: true, data: {articles: [...]}}`
- S'assurer que les données sont persistées

---

### 2. Forecasts API Retourne 0 Rows

**Endpoint**: `GET /api/forecasts`

**Problème**:
- API répond avec succès MAIS `payload.rows = []` (tableau vide!)
- Devrait retourner au moins 1 forecast

**Test Failing**:
```typescript
// tests/ui/integration-data.spec.ts:59
const r = await page.request.get('/api/forecasts')
const body = await json<any>(r)
const payload = body?.data ?? body
const rows = payload?.rows ?? []
expect(Array.isArray(rows)).toBeTruthy() // ✅ PASSE
expect(rows.length).toBeGreaterThan(0) // ❌ ÉCHOUE - rows.length = 0
```

**Impact**: Page `/forecasts` ne peut pas afficher de prévisions

**Solution Requise**:
- Vérifier que le job forecasts génère des données
- Vérifier le format de réponse: doit avoir `data.rows` ou `rows`
- S'assurer que les données sont persistées dans `data/forecasts.json`

**Note**: `useForecasts` hook a été modifié par un autre agent. Vérifier la compatibilité.

---

### 3. Brief Daily API Retourne 0 Signals/Risks

**Endpoint**: `GET /api/brief/daily`

**Problème**:
- API répond avec succès
- Structure OK: `{top_signals: [], top_risks: []}`
- MAIS tableaux vides!

**Test Failing**:
```typescript
// tests/ui/integration-data.spec.ts:71
const r = await page.request.get('/api/brief/daily')
const body = await json<any>(r)
const payload = body?.data ?? body
expect(Array.isArray(payload.top_signals)).toBeTruthy() // ✅ PASSE
expect(Array.isArray(payload.top_risks)).toBeTruthy() // ✅ PASSE
expect(payload.top_signals.length + payload.top_risks.length).toBeGreaterThan(0) // ❌ ÉCHOUE
```

**Impact**: Page `/brief` ne peut pas afficher de market brief

**Solution Requise**:
- Vérifier que le job `weekly_brief` génère des données
- Vérifier que les signaux sont calculés
- S'assurer que les données sont persistées dans `data/brief_weekly.json`

---

### 4. Webkit Cannot Connect (IPv6 vs IPv4)

**Problème**:
- Webkit essaie de se connecter à `::1:5173` (IPv6)
- Le serveur écoute probablement sur `127.0.0.1` (IPv4 only)

**Error**:
```
apiRequestContext.get: connect ECONNREFUSED ::1:5173
```

**Impact**: Tous les tests Webkit échouent

**Solution Requise**:
- Configurer Playwright pour forcer IPv4: `use: { baseURL: 'http://127.0.0.1:5174' }`
- OU configurer Vite pour écouter sur IPv6 aussi

---

## ✅ APIs FONCTIONNELLES

Ces endpoints marchent bien:

### Health API
```
GET /api/health
✅ Retourne {status: 'up', backend_up: true, ...}
✅ Dashboard se charge correctement
```

### Macro Series API
```
GET /api/macro/series?limit=50
✅ Retourne un tableau de rows
✅ Page /macro se charge correctement
```

### Stocks Prices API
```
GET /api/stocks/prices?ticker=SPY&interval=1d&downsample=250
✅ Retourne {tickers: {SPY: {points: [...]}}}
✅ Page /stocks se charge correctement
```

---

## 🟡 BUGS MINEURS - Frontend

### 1. Data-testid Manquants

**Impact**: Tests contract guards échouent

**Liste**:
- ✅ `dashboard-root` - présent
- ❌ `forecasts-pro` - **AJOUTÉ MAINTENANT**
- ❌ `macro-board` - manquant
- ❌ `stocks-screener` - manquant
- ❌ `news-feed` - manquant
- ❌ `metric-card` - manquant (Dashboard KPIs)

### 2. News Page - Texte "Filtres" Manquant

**Test Failing**:
```typescript
await page.goto('/news')
await expect(page.getByText('Filtres')).toBeVisible() // ❌ ÉCHOUE
```

**Solution**: Ajouter le texte "Filtres" quelque part sur la page News

---

## 📋 Action Plan pour Stabilisation V0

### Phase 1: Corriger Backend APIs (PRIORITÉ CRITIQUE)

**Durée estimée**: 1-2h

1. **News Feed API**
   ```bash
   # Vérifier backend
   curl http://127.0.0.1:8050/api/news/feed?tickers=SPY,QQQ&limit=50

   # Si vide:
   - Vérifier que le job news_ingest s'exécute
   - Vérifier que data/news_feed.json existe et a du contenu
   - Vérifier la route /api/news/feed dans backend
   ```

2. **Forecasts API**
   ```bash
   # Vérifier backend
   curl http://127.0.0.1:8050/api/forecasts

   # Si vide:
   - Vérifier que le job forecasts_generation s'exécute
   - Vérifier que data/forecasts.json existe et a du contenu
   - Vérifier format: doit avoir "rows" ou "items"
   ```

3. **Brief Daily API**
   ```bash
   # Vérifier backend
   curl http://127.0.0.1:8050/api/brief/daily

   # Si vide:
   - Vérifier que le job weekly_brief s'exécute
   - Vérifier que data/brief_weekly.json existe et a du contenu
   - Vérifier que top_signals et top_risks sont remplis
   ```

### Phase 2: Corriger Frontend data-testid

**Durée estimée**: 30min

```typescript
// src/pages/Macro.tsx
<div data-testid="macro-board">

// src/pages/Stocks.tsx
<div data-testid="stocks-screener">

// src/pages/News.tsx
<div data-testid="news-feed">

// src/pages/Dashboard.tsx - KPI cards
<Card data-testid="metric-card">
```

### Phase 3: Corriger Playwright Config

**Durée estimée**: 5min

```typescript
// playwright.config.ts
use: {
  baseURL: 'http://127.0.0.1:5174', // Force IPv4
}
```

---

## 🎯 Critères de Succès

### Minimum (MVP)
- [ ] News Feed API retourne > 0 articles
- [ ] Forecasts API retourne > 0 rows
- [ ] Brief Daily API retourne > 0 signals+risks
- [ ] Tests integration: ≥ 24/30 passés (80%)

### Optimal (V0)
- [ ] Tous les data-testid ajoutés
- [ ] Tests integration: ≥ 27/30 passés (90%)
- [ ] Tests contract guards: ≥ 70/85 passés (82%)
- [ ] 0 console errors critiques

---

## 🔍 Diagnostic Commands

### Vérifier Backend

```bash
# Health
curl http://127.0.0.1:8050/api/health | jq

# News Feed
curl "http://127.0.0.1:8050/api/news/feed?tickers=SPY,QQQ&limit=10" | jq

# Forecasts
curl http://127.0.0.1:8050/api/forecasts | jq

# Brief Daily
curl http://127.0.0.1:8050/api/brief/daily | jq

# Macro Series
curl "http://127.0.0.1:8050/api/macro/series?limit=10" | jq

# Stocks Prices
curl "http://127.0.0.1:8050/api/stocks/prices?ticker=SPY&interval=1d&downsample=10" | jq
```

### Vérifier Data Files

```bash
cd copilot-app/backend/data/

# Vérifier existence
ls -lh *.json

# Vérifier contenu
head -50 news_feed.json
head -50 forecasts.json
head -50 brief_weekly.json
```

### Re-run Tests

```bash
# Tests intégration seulement
npx playwright test tests/ui/integration-data.spec.ts --workers=1

# Tests contract guards seulement
npx playwright test tests/ui/contract-guards.spec.ts

# Tests complets
npx playwright test --reporter=html
```

---

## 📊 Métriques Actuelles

| Catégorie | Actuel | Objectif V0 |
|-----------|---------|-------------|
| Tests Intégration | 12/30 (40%) | 27/30 (90%) |
| Tests Contract Guards | 17/85 (20%) | 70/85 (82%) |
| APIs Fonctionnelles | 3/6 (50%) | 6/6 (100%) |
| Data-testid Coverage | 40% | 100% |

---

## 💡 Recommandations

1. **PRIORITÉ 1**: Corriger les 3 APIs backend qui retournent 0 données
2. **PRIORITÉ 2**: Ajouter tous les data-testid manquants
3. **PRIORITÉ 3**: Corriger Playwright config pour IPv4
4. **PRIORITÉ 4**: Re-run tests et valider ≥ 90% passent

**Temps total estimé**: 2-3h pour atteindre V0 stable

---

## 🚨 Notes Importantes

1. Les problèmes sont principalement **côté backend** (APIs ne retournent pas de données)
2. Le frontend marche bien quand les APIs retournent des données
3. `useForecasts` a été modifié par un autre agent - potentiel problème de compatibilité
4. Zod validation est en place mais ne peut pas valider des tableaux vides

**Action Immédiate Requise**:
- Investiguer pourquoi les jobs backend ne génèrent pas de données
- Vérifier les logs du backend pour erreurs
- S'assurer que tous les jobs scheduled s'exécutent correctement
