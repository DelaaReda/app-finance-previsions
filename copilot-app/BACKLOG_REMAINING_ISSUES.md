# 📋 Backlog - Issues Restantes

**Date**: 2025-11-10  
**Status**: ✅ Majorité des correctifs appliqués, quelques améliorations restantes

---

## 🔥 Priorité Haute

### 1. Calcul réel de `expected_return` dans les prévisions
- [ ] **Backend**: Implémenter le calcul de `expected_return` basé sur les signaux ML + LLM
- [ ] **Backend**: Remplacer les placeholders `+0.01%` par des valeurs réelles
- [ ] **Fichier**: `copilot-app/backend/models/forecast_hybrid_v1.py`
- [ ] **Test**: Vérifier que les valeurs ER varient selon les tickers

**Impact**: Les prévisions affichent actuellement des valeurs statiques identiques pour tous les tickers.

---

### 2. Market Regime dynamique
- [ ] **Backend**: Faire en sorte que `/api/context/current` se mette à jour automatiquement
- [ ] **Backend**: Calculer le régime basé sur les données récentes (24h)
- [ ] **Frontend**: Ajouter un `refetchInterval` dans `useMarketContext` (actuellement 5 min)
- [ ] **Fichier**: `copilot-app/backend/services/context_service.py`
- [ ] **Fichier**: `copilot-app/frontend/webapp/src/hooks/useMarketContext.ts`

**Impact**: Le badge "Normal • 50% confidence" reste statique même après mise à jour des données.

---

### 3. KPIs Dashboard - Vérification du calcul
- [ ] **Backend**: Vérifier que `high_confidence_pct` est bien calculé et non null
- [ ] **Backend**: S'assurer que les prévisions avec `confidence > 0.6` sont bien comptées
- [ ] **Fichier**: `copilot-app/backend/api/routes/dashboard.py` (ligne 225)
- [ ] **Test**: Vérifier avec des données de test que le pourcentage est correct

**Impact**: Les KPIs affichent 0% même quand il y a des prévisions avec haute confiance.

---

## ⚙️ Priorité Moyenne

### 4. Judge Page - Améliorations UX
- [ ] **Frontend**: Ajouter pagination pour les verdicts (actuellement limité à 10)
- [ ] **Frontend**: Ajouter indicateur de fraîcheur "Mise à jour : XXh" 
- [ ] **Backend**: Inclure `last_updated` dans la réponse `/api/judge`
- [ ] **Fichier**: `copilot-app/frontend/webapp/src/pages/LLMJudge.tsx`
- [ ] **Fichier**: `copilot-app/backend/api/routes/judge.py`

**Impact**: L'utilisateur ne sait pas quand les verdicts ont été générés.

---

### 5. Macro Refresh Button
- [ ] **Frontend**: Ajouter bouton "🔄 Rafraîchir" dans `MacroWidget.tsx`
- [ ] **Frontend**: Connecter le bouton à `refetch()` de `useQuery`
- [ ] **Fichier**: `copilot-app/frontend/webapp/src/components/widgets/MacroWidget.tsx`

**Impact**: L'utilisateur ne peut pas forcer une mise à jour manuelle des données macro.

---

### 6. Système i18n (Internationalisation)
- [ ] **Frontend**: Créer fichier `src/i18n/fr.ts` avec dictionnaire FR
- [ ] **Frontend**: Créer hook `useTranslation()` 
- [ ] **Frontend**: Remplacer tous les textes EN par des traductions FR
- [ ] **Fichiers**: Tous les composants avec textes en anglais
- [ ] **Exemples**: "Refresh" → "Rafraîchir", "success" → "succès", "Adaptive Mode Active" → "Mode adaptatif actif"

**Impact**: Mélange FR/EN dans l'interface, expérience utilisateur incohérente.

---

## 🚀 Priorité Basse (Optimisations)

### 7. Lazy Loading des composants
- [ ] **Frontend**: Implémenter `React.lazy()` pour chaque widget du dashboard
- [ ] **Frontend**: Ajouter `Suspense` avec fallback loader
- [ ] **Fichier**: `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`
- [ ] **Exemple**: `const ForecastCardsWidget = React.lazy(() => import('@/components/widgets/ForecastCardsWidget'))`

**Impact**: Le dashboard charge tout d'un coup, ralentissant le temps de chargement initial.

---

### 8. Cache React Query optimisé
- [ ] **Frontend**: Ajuster `staleTime` par type de donnée (forecasts: 2min, macro: 1h, news: 15min)
- [ ] **Frontend**: Ajouter `cacheTime` approprié pour éviter re-fetch inutiles
- [ ] **Fichiers**: Tous les hooks `useQuery` dans `src/hooks/`

**Impact**: Requêtes API répétées inutilement, consommation de bande passante.

---

### 9. Loader global pendant fetch initial
- [ ] **Frontend**: Créer composant `GlobalLoader` basé sur `isFetching` de React Query
- [ ] **Frontend**: Afficher un spinner/barre de progression pendant le chargement initial
- [ ] **Fichier**: `copilot-app/frontend/webapp/src/components/system/GlobalLoader.tsx`
- [ ] **Intégration**: Ajouter dans `App.tsx` ou `AppShell.tsx`

**Impact**: L'utilisateur ne sait pas si les données sont en cours de chargement.

---

## 📊 Résumé des priorités

| Priorité | Issues | Effort estimé | Impact |
|----------|--------|---------------|--------|
| 🔥 Haute | 3 | ~4h | Critique - données statiques |
| ⚙️ Moyenne | 3 | ~3h | Important - UX |
| 🚀 Basse | 3 | ~4h | Optimisation - Performance |

**Total estimé**: ~11h de développement

---

## ✅ Checklist de validation

Après chaque correction:
- [ ] Tester l'endpoint avec `curl` ou Postman
- [ ] Vérifier les logs backend
- [ ] Tester dans le frontend (http://localhost:5173)
- [ ] Vérifier qu'aucune régression n'est introduite
- [ ] Mettre à jour la documentation si nécessaire

---

## 🎯 Prochaines étapes recommandées

1. **Sprint 1** (Priorité Haute - 4h):
   - Corriger le calcul de `expected_return`
   -Rendre le market regime dynamique
   -Vérifier le calcul des KPIs

2. **Sprint 2** (Priorité Moyenne - 3h):
   -Améliorer la page Judge (pagination + fraîcheur)
   -Ajouter bouton refresh Macro
   -Créer système i18n de base

3. **Sprint 3** (Priorité Basse - 4h):
   -Implémenter lazy loading
   -Optimiser cache React Query
   -Ajouter loader global

---

**Note**: Les endpoints critiques sont fonctionnels. Ces améliorations visent à rendre l'application plus dynamique, performante et user-friendly.

