# Plan de Stabilisation V0 - Finance Copilot Frontend

**Date**: 2025-11-06
**Objectif**: Version stable et fonctionnelle à 100% avec données réelles

## 🔴 Bugs Critiques Identifiés

### 1. Data-testid Manquants (Tests Échouent)

**Impact**: 68/85 tests Playwright échouent

#### Dashboard
- [x] `data-testid="dashboard-root"` ✅ (déjà présent)
- [ ] `data-testid="metric-card"` sur chaque KPI card
- [ ] `data-testid="health-bar"` ✅ (existe déjà)

#### Forecasts
- [ ] `data-testid="forecasts-pro"` sur la racine de la page
- [ ] `data-testid="forecast-table"` sur la table

#### Backtests
- [ ] `data-testid="backtests-panel"` ✅ (déjà présent)
- Problème: KPI badges non trouvés par regex `/CAGR|Sharpe|Sortino|MaxDD|WinRate/i`
- Problème: Tabs Overview/Equity/Monthly/Trades non visibles

#### Health Page
- [ ] `data-testid="health-status-banner"` sur le banner système
- [ ] `data-testid="dataset-health-card"` sur chaque card dataset
- [ ] Freshness badges: ajouter classe ou data-testid

#### Macro Page
- [ ] `data-testid="macro-board"` sur la racine

#### Stocks Page
- [ ] `data-testid="stocks-screener"` sur le screener

#### News Page
- [ ] `data-testid="news-feed"` sur le feed
- [ ] Filtres visibles avec texte "Filtres"

### 2. Hook useForecasts Cassé

**Problème**: Un autre agent a complètement réécrit `useForecasts.ts`
- Return type incompatible: retourne `{rows, freshness, source, generated_at}` au lieu de `ForecastsResponse`
- Types cassés partout où le hook est utilisé
- Validation Zod ne fonctionne plus

**Solution**:
```typescript
// Option 1: Restaurer l'ancien hook avec validation Zod
// Option 2: Adapter tous les composants au nouveau format
// Option 3: Créer adaptateur de compatibilité
```

### 3. Console Errors (9 erreurs détectées)

**Impact**: Tests "pages should not have console errors" échoue

**À investiguer**:
- Erreurs JavaScript sur homepage
- Filtrer erreurs critiques vs warnings
- Corriger toutes les erreurs critiques

### 4. Navigation Manquante

**Problème**: Test "all pages should have navigation" échoue
- Sélecteur: `nav, [role="navigation"], a[href]` ne trouve rien

**Solution**:
- Ajouter `role="navigation"` sur AppShell nav
- OU s'assurer que des `<nav>` tags existent
- OU avoir au moins des `<a href>` visibles

## 🟡 Améliorations CSS/UX

### Inspiration du Testeur HTML

Le fichier `finance_app_test-v2.html` a un CSS magnifique à adapter:

```css
/* Gradients modernes */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Cards avec hover effects */
.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}

/* Stats cards avec gradients */
.stat-card {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

/* Badges colorés */
.badge.success {
  background: #d1fae5;
  color: #065f46;
}

/* Progress bars */
.progress-bar {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}
```

### À Implémenter

1. **Mantine Theme Customization**
   - Ajouter gradients custom
   - Améliorer hover effects
   - Badges plus colorés

2. **Animations**
   - Pulse sur loading states
   - Smooth transitions
   - Skeleton loaders

3. **Typography**
   - Font hierarchy claire
   - Meilleur contrast
   - Tailles responsive

## 🟢 Tests d'Intégration

### Tests Existants à Passer (integration-data.spec.ts)

- [ ] ✅ Health endpoint up and dashboard loads
- [ ] ✅ Macro series returns rows and widgets render
- [ ] ✅ News feed returns articles and lists cards
- [ ] ✅ Stocks prices returns points and screener renders
- [ ] ✅ Forecasts returns rows and widget renders
- [ ] ✅ Brief daily returns structured data and page renders

### Contract Guards (contract-guards.spec.ts)

**Résultats actuels**: 17/85 passés (20%)

**Objectif V0**: 80/85 passés (94%)

Sections à corriger:
- [ ] Dashboard Contract Guards (2 tests)
- [ ] Forecasts Contract Guards (2 tests)
- [ ] Backtests Contract Guards (5 tests)
- [ ] Health Page Contract Guards (3 tests)
- [ ] Critical UI Elements (2 tests)
- [ ] Data Freshness Guards (2 tests)

## 📋 Checklist de Stabilisation

### Phase 1: Corrections Critiques (2-3h)
- [ ] Ajouter tous les data-testid manquants
- [ ] Corriger/restaurer useForecasts.ts
- [ ] Corriger les 9 console errors
- [ ] Ajouter role="navigation" sur nav

### Phase 2: Tests (1h)
- [ ] Re-run integration tests
- [ ] Re-run contract guards
- [ ] Vérifier taux de passage > 90%
- [ ] Documenter bugs restants

### Phase 3: CSS/Polish (1-2h)
- [ ] Implémenter gradients Mantine
- [ ] Améliorer hover effects
- [ ] Ajouter animations de loading
- [ ] Responsive improvements

### Phase 4: Validation Finale (30min)
- [ ] Test manuel de toutes les pages
- [ ] Vérifier données réelles chargent
- [ ] Performance check (Lighthouse)
- [ ] Generate test report

## 🎯 Critères de Succès V0

1. **Tests**: ≥ 90% des tests passent
2. **Données**: Aucune donnée mockée, tout vient du backend
3. **Console**: 0 erreurs critiques
4. **UX**: Toutes les pages chargent < 3s
5. **Navigation**: Tous les liens fonctionnent
6. **CSS**: Look professionnel et moderne

## 🔧 Outils de Validation

### Tests Automatiques
```bash
# Integration tests (no mocks)
npx playwright test tests/ui/integration-data.spec.ts

# Contract guards (schema validation)
npx playwright test tests/ui/contract-guards.spec.ts

# Full suite
npx playwright test --reporter=html
```

### Testeur HTML Interactif
```bash
# Ouvrir le testeur dans navigateur
open tests/finance_app_test-v2.html
# Configurer: http://localhost:5174
# Cliquer "Lancer Tests Réels"
```

### Console Monitoring
```javascript
// Capturer toutes les erreurs
window.addEventListener('error', (e) => {
  console.error('Runtime Error:', e);
});

// React error boundary logs
```

## 📊 Métriques de Progression

| Catégorie | Actuel | Objectif V0 |
|-----------|---------|-------------|
| Tests Passed | 17/85 (20%) | 77/85 (90%) |
| Console Errors | 9 | 0 |
| Data-testid Coverage | 30% | 100% |
| Page Load Time | ? | < 3s |
| Lighthouse Score | ? | > 80 |

## 📝 Notes Importantes

1. **useForecasts.ts**: Un autre agent l'a modifié. Vérifier dans le git log qui et pourquoi.
2. **Zod Validation**: Déjà intégré (Phase 3 complétée) mais incompatible avec nouveau useForecasts
3. **Backend**: Tourne sur http://127.0.0.1:8050 (vérifié fonctionnel)
4. **Frontend**: Tourne sur http://localhost:5174 (vérifié fonctionnel)

## 🚀 Prochaines Étapes Immédiates

1. Attendre résultats tests d'intégration en cours
2. Créer rapport de bugs complet
3. Prioriser corrections par impact
4. Commencer par data-testid (quick wins)
5. Puis useForecasts (critique)
6. Puis console errors
7. Enfin CSS improvements
