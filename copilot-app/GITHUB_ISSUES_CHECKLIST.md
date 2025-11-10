# 📋 Checklist GitHub Issues - Finance Copilot

**Date**: 2025-11-10  
**Format**: Prêt à copier dans GitHub Issues

---

## 🔥 Priorité Haute

### Issue #1: Calcul réel de `expected_return` dans les prévisions

**Contexte**:  
Les prévisions affichent actuellement des valeurs statiques identiques (`+0.01%`) pour tous les tickers. Le calcul existe dans `forecast_hybrid_v1.py` mais doit être vérifié et amélioré.

**Étapes de reproduction**:
1. Aller sur `/forecasts`
2. Observer que tous les tickers ont le même `expected_return`
3. Vérifier que les valeurs ne varient pas selon les signaux techniques

**Solution proposée**:
- [ ] Vérifier que `_calculate_technical_signals()` retourne des valeurs variées
- [ ] Améliorer le calcul de `expected_return` basé sur la force des signaux
- [ ] Ajouter des tests unitaires pour valider la variation des valeurs
- [ ] Vérifier que les valeurs ER varient entre -2% et +2% selon les signaux

**Fichiers concernés**:
- `copilot-app/backend/models/forecast_hybrid_v1.py` (lignes 49-83)

**Estimation**: 2h

---

### Issue #2: Market Regime dynamique (backend)

**Contexte**:  
Le badge "Normal • 50% confidence" reste statique même après mise à jour des données. Le service `context_service.py` doit utiliser des données plus récentes (24h) pour calculer le régime.

**Étapes de reproduction**:
1. Observer le badge de régime dans le dashboard
2. Attendre 2 minutes (refresh interval)
3. Vérifier que le régime ne change pas même si les données changent

**Solution proposée**:
- [ ] Modifier `_classify_regime()` pour utiliser les données des 24h dernières
- [ ] Ajouter un calcul de tendance basé sur les prévisions récentes
- [ ] Invalider le cache du contexte après mise à jour des données
- [ ] Ajouter des logs pour tracer les changements de régime

**Fichiers concernés**:
- `copilot-app/backend/services/context_service.py` (lignes 120-149)

**Estimation**: 3h

---

### Issue #3: Vérification calcul KPIs Dashboard

**Contexte**:  
Les KPIs affichent parfois 0% même quand il y a des prévisions avec haute confiance. Vérifier que le calcul de `high_confidence_pct` est correct.

**Étapes de reproduction**:
1. Générer des prévisions avec `confidence > 0.6`
2. Vérifier le dashboard KPIs
3. Observer si `high_confidence_pct` est bien calculé

**Solution proposée**:
- [ ] Ajouter des logs de debug dans `dashboard.py` pour tracer le calcul
- [ ] Vérifier que `HIGH_CONF_THRESHOLD` (0.6) est bien utilisé
- [ ] Tester avec des données de test variées
- [ ] Ajouter un test unitaire pour le calcul des KPIs

**Fichiers concernés**:
- `copilot-app/backend/api/routes/dashboard.py` (lignes 220-225)

**Estimation**: 1h

---

## ⚙️ Priorité Moyenne

### Issue #4: Judge Page - Pagination et fraîcheur

**Contexte**:  
Les verdicts sont limités à 10 et il n'y a pas d'indicateur de fraîcheur clair.

**Étapes de reproduction**:
1. Aller sur `/judge`
2. Observer qu'il n'y a que 10 verdicts affichés
3. Vérifier qu'il n'y a pas de pagination

**Solution proposée**:
- [ ] Ajouter pagination avec `limit` et `offset` dans le frontend
- [ ] Ajouter un indicateur "Mise à jour : il y a XXh" plus visible
- [ ] Ajouter un tri par date (plus récent en premier)
- [ ] Ajouter un filtre par verdict (buy/sell/neutral)

**Fichiers concernés**:
- `copilot-app/frontend/webapp/src/pages/LLMJudge.tsx`
- `copilot-app/backend/api/routes/judge.py`

**Estimation**: 2h

---

### Issue #5: Système i18n (Internationalisation)

**Contexte**:  
Mélange FR/EN dans l'interface : "Refresh", "success", "Adaptive Mode Active", etc.

**Étapes de reproduction**:
1. Parcourir l'interface
2. Observer les textes en anglais
3. Lister tous les textes à traduire

**Solution proposée**:
- [ ] Créer `src/i18n/fr.ts` avec dictionnaire FR
- [ ] Créer hook `useTranslation()`
- [ ] Remplacer progressivement tous les textes EN
- [ ] Ajouter support pour changement de langue (optionnel)

**Fichiers concernés**:
- Tous les composants frontend avec textes en anglais
- Nouveau: `copilot-app/frontend/webapp/src/i18n/fr.ts`
- Nouveau: `copilot-app/frontend/webapp/src/hooks/useTranslation.ts`

**Estimation**: 4h

---

## 🚀 Priorité Basse (Optimisations)

### Issue #6: Lazy Loading des composants

**Contexte**:  
Le dashboard charge tout d'un coup, ralentissant le temps de chargement initial.

**Étapes de reproduction**:
1. Ouvrir le dashboard
2. Observer le temps de chargement initial
3. Vérifier que tous les widgets se chargent en parallèle

**Solution proposée**:
- [ ] Implémenter `React.lazy()` pour chaque widget
- [ ] Ajouter `Suspense` avec fallback loader
- [ ] Prioriser le chargement des widgets critiques (KPIs, Forecasts)
- [ ] Mesurer l'amélioration du temps de chargement

**Fichiers concernés**:
- `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`
- Tous les fichiers de widgets

**Estimation**: 3h

---

### Issue #7: Cache React Query optimisé

**Contexte**:  
Requêtes API répétées inutilement, consommation de bande passante.

**Étapes de reproduction**:
1. Ouvrir les DevTools → Network
2. Observer les requêtes répétées
3. Vérifier les `staleTime` dans les hooks

**Solution proposée**:
- [ ] Ajuster `staleTime` par type de donnée:
  - Forecasts: 2 min
  - Macro: 1 h
  - News: 15 min
  - Stocks: 5 min
- [ ] Ajouter `cacheTime` approprié
- [ ] Utiliser `keepPreviousData` pour les transitions

**Fichiers concernés**:
- Tous les hooks `useQuery` dans `src/hooks/`

**Estimation**: 2h

---

### Issue #8: Loader global pendant fetch initial

**Contexte**:  
L'utilisateur ne sait pas si les données sont en cours de chargement.

**Étapes de reproduction**:
1. Ouvrir le dashboard
2. Observer qu'il n'y a pas de loader global visible
3. Vérifier que les widgets chargent individuellement

**Solution proposée**:
- [ ] Créer composant `GlobalLoader.tsx`
- [ ] Utiliser `useIsFetching()` de React Query
- [ ] Afficher un spinner/barre de progression
- [ ] Intégrer dans `App.tsx` ou `AppShell.tsx`

**Fichiers concernés**:
- Nouveau: `copilot-app/frontend/webapp/src/components/system/GlobalLoader.tsx`
- `copilot-app/frontend/webapp/src/App.tsx`

**Estimation**: 2h

---

## 📊 Résumé des Issues

| # | Titre | Priorité | Estimation | Status |
|---|-------|----------|------------|--------|
| 1 | Calcul réel de `expected_return` | 🔥 Haute | 2h | ⏳ À faire |
| 2 | Market Regime dynamique (backend) | 🔥 Haute | 3h | ⏳ À faire |
| 3 | Vérification calcul KPIs Dashboard | 🔥 Haute | 1h | ⏳ À faire |
| 4 | Judge Page - Pagination et fraîcheur | ⚙️ Moyenne | 2h | ⏳ À faire |
| 5 | Système i18n (Internationalisation) | ⚙️ Moyenne | 4h | ⏳ À faire |
| 6 | Lazy Loading des composants | 🚀 Basse | 3h | ⏳ À faire |
| 7 | Cache React Query optimisé | 🚀 Basse | 2h | ⏳ À faire |
| 8 | Loader global pendant fetch initial | 🚀 Basse | 2h | ⏳ À faire |

**Total estimé**: 19h

---

## ✅ Format GitHub Issue (exemple)

```markdown
## Contexte
[Description du problème]

## Étapes de reproduction
1. [Étape 1]
2. [Étape 2]
3. [Étape 3]

## Solution proposée
- [ ] Tâche 1
- [ ] Tâche 2
- [ ] Tâche 3

## Fichiers concernés
- `path/to/file1.py`
- `path/to/file2.tsx`

## Estimation
X heures

## Labels
- `priority: high` / `priority: medium` / `priority: low`
- `backend` / `frontend` / `fullstack`
- `enhancement` / `bug` / `optimization`
```

---

**Note**: Les issues critiques (#1, #2, #3) doivent être traitées en priorité car elles affectent la qualité des données affichées. Les autres peuvent être faites progressivement.

