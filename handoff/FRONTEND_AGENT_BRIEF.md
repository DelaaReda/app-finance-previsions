# FRONTEND_AGENT_BRIEF.md

## Mission
Rendre la vue MVP exploitable et branchée sur les endpoints MVP.

## Scope
- `copilot-app/frontend/app/app.js`
- `copilot-app/frontend/app/mockData.js`
- `copilot-app/frontend/app/style.css`

## Rules
- Ne pas supprimer les mocks historiques
- Isoler fallback mock derrière un badge visible `Données simulées`
- Limiter les changements aux sections MVP

## Validation
- App charge sans erreur JS bloquante
- Les widgets MVP affichent data API quand dispo
- En cas d'échec API: fallback explicite (pas silencieux)
