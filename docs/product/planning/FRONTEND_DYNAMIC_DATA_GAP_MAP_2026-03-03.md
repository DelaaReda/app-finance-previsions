# Frontend Dynamic Data Gap Map (2026-03-03)

## Scope
Audit cible du frontend forecasts pour identifier les zones encore pilotées par données statiques/simulées alors que des endpoints dynamiques existent déjà.

## Gaps confirmés

1. Facettes/tab content encore statique
- Fichier: `apps/web/src/domains/forecasts/pages/app.js`
- Signal: `loadFacetteContent()` appelle `generateFacetteContent()` (placeholder synthétique) au lieu d’un renderer branché aux payloads live.

2. Données UI hybrides (live + fallback figé)
- Fichier: `apps/web/src/domains/forecasts/pages/app.js`
- Signal: nombreux `FALLBACK_*` et vues (story/insights/calendar/trade ideas) qui gardent des trajectoires mock même après hydration.

3. Transformation non déterministe côté connecteur
- Fichier: `apps/web/src/domains/forecasts/contracts/apiConnector.js`
- Signal: `transformNewsItem()` injecte `Math.random()` dans `effect`, ce qui produit des écarts UI non traçables.

4. Duplication du connecteur API
- Fichiers:
  - `apps/web/src/domains/forecasts/contracts/apiConnector.js` (canonique)
  - `apps/web/src/apiConnector.js` (legacy/duplicate)
- Risque: dérive de contrats et confusion d’inclusion script.

5. Visualisations encore pilotées par séries statiques
- Fichier: `apps/web/src/domains/forecasts/pages/app.js`
- Signal: plusieurs charts utilisent des tableaux figés (ex. volatility/heatmap/story points) au lieu des séries live quand disponibles.

## Batch mapping

## BATCH-27 — Frontend Dynamic Data Coverage
Objectif: brancher les facettes et widgets au flux live existant sans créer de nouvelle stack.

## BATCH-28 — Frontend Dynamic UX Hardening
Objectif: fiabiliser la couche UX dynamique (freshness/error/degraded) et rendre la qualité des données visible.

## Success gates
- Les facettes principales n’affichent plus de placeholder synthétique quand les payloads live existent.
- Aucune donnée aléatoire (`Math.random`) dans les transformations de réponse API.
- Un seul connecteur API canonique pour le domaine forecasts.
- États `loading/error/stale` visibles sur les widgets critiques.

## Front/Back Coverage Matrix

- Gap contrat backend/frontend -> BATCH-27-DEV-01
- Gap rendering dynamique facettes/widgets -> BATCH-27-DEV-02
- Gap determinisme + duplication connector -> BATCH-27-DEV-03
- Gap freshness/error metadata backend -> BATCH-28-DEV-01
- Gap visualisation d etats runtime UI -> BATCH-28-DEV-02
- Gap validation e2e nominal/degrade -> BATCH-28-DEV-03

