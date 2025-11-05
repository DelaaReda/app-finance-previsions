# 🚀 UI THEMING MISSIONS - Material UI Integration (Complete Technical Guide)

## FC-UI-021 — Thème Material UI (Design System)

**Status**: AVAILABLE to claim

**But**: Implémenter le thème Material UI basé sur l'exemple officiel `material-ui-vite-ts` pour améliorer l'UX, l'accessibilité et la cohérence visuelle.

**Fichiers**
* `frontend/webapp/package.json`
* `frontend/webapp/vite.config.ts`
* `frontend/webapp/src/App.tsx`
* `frontend/webapp/src/main.tsx`
* `frontend/webapp/src/theme.ts`
* `frontend/webapp/src/layout/AppShell.tsx`
* `frontend/webapp/src/components/ui/*`

**Étapes**
1. **Setup Material UI**:
   - Installer dépendances: `@mui/material @emotion/react @emotion/styled @mui/icons-material @fontsource/roboto @mui/x-data-grid`
   - Charger police Roboto dans `main.tsx` une seule fois
   - Créer `theme.ts` avec `createTheme()` et modes light/dark

2. **Structure applicative**:
   - Encapsuler l'application dans `ThemeProvider`, `CssBaseline`, `QueryClientProvider`
   - Créer layout `AppShell.tsx` avec AppBar, Drawer, Container responsive
   - Remplacer le CSS global par les composants MUI équivalents

3. **Migration progressive**:
   - Convertir les composants UI critiques un par un (Dashboard, Forecasts, News)
   - Conserver la structure logique existante mais améliorer avec MUI
   - Tester chaque conversion pour s'assurer de la non-régression

**DoD**
* Tous les composants UI utilisent les composants MUI
* Thème cohérent appliqué à l'ensemble de l'application
* Mode clair/sombre supporté avec persistance
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
   - Dashboard: Grilles MUI (`Grid`, `Card`, `Paper`, `Typography`), KPIs en Cards
   - Forecasts: DataGrid MUI (`DataGrid`) pour les prévisions
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
* États loading/error/empty correctement gérés avec composants MUI

---

## FC-UI-023 — Data Visualization MUI (Charts & DataGrid)

**Status**: AVAILABLE to claim

**But**: Remplacer les composants de visualisation par des composants MUI X (DataGrid, Charts).

**Fichiers**
* `frontend/webapp/src/components/charts/*`
* `frontend/webapp/src/components/DataTable.tsx`
* `frontend/webapp/src/pages/Forecasts.tsx`
* `frontend/webapp/src/pages/Backtests.tsx`

**Étapes**
1. **Install MUI X**:
   - Ajouter `@mui/x-data-grid` aux dépendances
   - Configurer les licences (open source)

2. **Remplacer DataGrid**:
   - Utiliser `DataGridPro` ou `DataGrid` pour les prévisions
   - Implémenter le tri, filtre, pagination nativement
   - Améliorer l'accessibilité des données tabulaires
   - Protéger contre erreurs `map/length of undefined`

3. **Visualisations**:
   - Utiliser `@mui/x-charts` pour graphiques simples (LineChart, BarChart, etc.)
   - Intégrer avec les données d'API existantes
   - Ajouter des tooltips et interactions MUI

**DoD**
* Tous les tableaux de données utilisent MUI DataGrid
* Graphiques remplacés par MUI Charts avec interactions améliorées
* Chargement des graphiques plus rapide avec MUI X
* Accessibilité WCAG respectée pour toutes les visualisations
* Protection contre crashes UI (never-empty patterns)

---

## FC-UI-024 — UI Guards & Error Boundaries (Stabilité)

**Status**: AVAILABLE to claim

**But**: Mettre en place des garde-fous UI pour éviter les crashes (never-empty côté front).

**Fichiers**
* `frontend/webapp/src/components/ErrorBoundary.tsx`
* `frontend/webapp/src/components/EmptyState.tsx`
* `frontend/webapp/src/pages/*.tsx` (intégration)
* `frontend/webapp/src/api/client.ts` (sécurisation des appels)

**Étapes**
1. **Error Boundaries**:
   - Composant global ErrorBoundary avec message clair et bouton "Réessayer"
   - Intégrer dans le AppShell ou via React Router

2. **Sécurisation des données**:
   - Toujours `const items = Array.isArray(data?.items) ? data.items : []` au lieu de `data.items`
   - Éviter `.map` ou `.length` direct sur des propriétés potentiellement `undefined`
   - Utiliser `?? []` pour les tableaux, `?? 0` pour les nombres, `?? ""` pour les strings

3. **États UI**:
   - Loading: Spinners/Skeleton MUI pendant les appels API
   - Error: Alert MUI avec message d'erreur et bouton de retry
   - Empty: EmptyState MUI avec message clair sans crash

**DoD**
* Aucun crash dû à `.map/length of undefined` 
* Tous les composants protégés avec garde-fous
* États loading/error/empty gérés avec composants MUI
* UI jamais blanche ou cassée en cas d'erreur
* Système de fallback robuste

---

## FC-UI-025 — Migration complète et tests (Validation)

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
* Système entièrement fonctionnel avec nouvelle UI MUI