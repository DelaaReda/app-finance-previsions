# 🚀 UI THEMING MISSIONS - Material UI Integration

## FC-UI-021 — Thème Material UI (Design System)

**Status**: AVAILABLE to claim

**But**: Implémenter le thème Material UI basé sur l'exemple officiel `material-ui-vite-ts` pour améliorer l'UX et l'accessibilité.

**Fichiers**

* `frontend/webapp/package.json`
* `frontend/webapp/vite.config.ts`
* `frontend/webapp/src/App.tsx`
* `frontend/webapp/src/main.tsx`
* `frontend/webapp/src/theme.ts`
* `frontend/webapp/src/components/ui/*`

**Étapes**

1. **Setup Material UI**:
   - Ajouter `@mui/material`, `@emotion/react`, `@emotion/styled` aux dépendances
   - Configurer le Vite pour supporter le CSS de MUI
   - Créer un fichier `theme.ts` avec la personnalisation de la palette

2. **Wrapper principal**:
   - Encapsuler l'application dans `ThemeProvider` et `CssBaseline`
   - Remplacer le CSS global par les composants MUI équivalents

3. **Migration progressive**:
   - Convertir les composants UI critiques un par un (Dashboard, Forecasts, News)
   - Conserver la structure existante mais améliorer avec MUI
   - Tester chaque conversion pour s'assurer de la non-régression

**DoD**

* Tous les composants UI utilisent les composants MUI
* Thème cohérent appliqué à l'ensemble de l'application
* Palettes de couleurs personnalisées pour le thème financier
* Application respecte les normes d'accessibilité WCAG
* Aucun crash UI sur les composants migrés

---

## FC-UI-022 — Composants UI MUI (Page Components)

**Status**: AVAILABLE to claim

**But**: Convertir les composants pages vers Material UI avec des layouts professionnels.

**Fichiers**

* `frontend/webapp/src/pages/Dashboard.tsx`
* `frontend/webapp/src/pages/Forecasts.tsx`
* `frontend/webapp/src/pages/News.tsx`
* `frontend/webapp/src/pages/MarketBrief.tsx`
* `frontend/webapp/src/layouts/*`

**Étapes**

1. **Layout principal**:
   - Créer un layout avec AppBar, Drawer, et Footer en MUI
   - Implémenter le routing MUI avec `Tab` ou `BottomNavigation`

2. **Pages critiques**:
   - Dashboard: Grilles MUI (`Grid`, `Card`, `Paper`, `Typography`)
   - Forecasts: Tableaux MUI (`Table`, `TableHead`, `TableBody`, `TableCell`)
   - News: Listes MUI (`List`, `ListItem`, `ListItemText`, `Card`)
   - Briefs: Accordion MUI pour les sections

3. **Responsive design**:
   - Utiliser les breakpoints MUI pour mobile/desktop
   - Tester sur différentes tailles d'écran

**DoD**

* Toutes les pages principales utilisent les composants MUI
* Layout responsive fonctionnel sur mobile et desktop
* Navigation intuitive avec barre latérale ou tabs
* Performance comparable ou meilleure qu'avant la migration

---

## FC-UI-023 — Data Visualization MUI (Charts & Graphs)

**Status**: AVAILABLE to claim

**But**: Remplacer les graphiques actuels par des composants MUI X (DataGrid, Charts).

**Fichiers**

* `frontend/webapp/src/components/charts/*`
* `frontend/webapp/src/pages/Forecasts.tsx`
* `frontend/webapp/src/pages/Backtests.tsx`

**Étapes**

1. **Install MUI X**:
   - Ajouter `@mui/x-data-grid`, `@mui/x-charts` aux dépendances
   - Configurer les licences (open source)

2. **Remplacer DataGrid**:
   - Utiliser `DataGridPro` ou `DataGrid` pour les prévisions
   - Implémenter le tri, filtre, pagination nativement
   - Améliorer l'accessibilité des données tabulaires

3. **Remplacer graphiques**:
   - Utiliser `LineChart`, `BarChart`, `PieChart` pour les visualisations
   - Intégrer avec les données d'API existantes
   - Ajouter des tooltips et interactions MUI

**DoD**

* Tous les tableaux de données utilisent MUI DataGrid
* Graphiques remplacés par MUI Charts avec interactions améliorées
* Chargement des graphiques plus rapide avec MUI X
* Accessibilité WCAG respectée pour toutes les visualisations

---

## FC-UI-024 — Formulaires & Inputs MUI

**Status**: AVAILABLE to claim

**But**: Mettre à jour les formulaires et inputs avec les composants MUI pour une meilleure UX.

**Fichiers**

* `frontend/webapp/src/components/forms/*`
* `frontend/webapp/src/pages/Settings.tsx`
* `frontend/webapp/src/api/forms/*`

**Étapes**

1. **Champs de formulaire**:
   - Utiliser `TextField`, `Select`, `Autocomplete` MUI
   - Implémenter la validation MUI avec `TextField` props
   - Gérer les erreurs et feedbacks utilisateur

2. **Composants complexes**:
   - DatePicker MUI pour les filtres de dates
   - Slider MUI pour les paramètres de seuils
   - Switch MUI pour les options d'affichage

3. **Accessibilité**:
   - Labels correctement associés
   - Navigation clavier fonctionnelle
   - Support des lecteurs d'écran

**DoD**

* Tous les formulaires UI utilisent les composants MUI
* Validation des formulaires intégrée avec MUI
* Expérience utilisateur améliorée pour les interactions
* Support complet des normes d'accessibilité

---

## FC-UI-025 — Migration complète et tests

**Status**: AVAILABLE to claim

**But**: Compléter la migration UI et valider la stabilité globale.

**Fichiers**

* Tous les composants UI existants
* Scripts de test e2e
* Documentation de migration

**Étapes**

1. **Audit final**:
   - Vérifier que tous les composants UI sont migrés
   - Tester la performance et le bundle size
   - Valider l'accessibilité complète

2. **Tests de régression**:
   - Mettre à jour les tests Playwright pour les nouveaux composants
   - Vérifier que toutes les fonctionnalités sont intactes
   - Exécuter les tests de performance

3. **Documentation**:
   - Créer un guide de migration pour l'équipe
   - Documenter les nouveaux patterns MUI
   - Mettre à jour les stories Storybook (si existant)

**DoD**

* 100% des composants UI migrés vers MUI
* Tous les tests passent (unitaires, e2e, performance)
* Bundle size optimal (pas de régression significative)
* Documentation mise à jour pour l'équipe
* Aucun bug d'accessibilité ou de performance