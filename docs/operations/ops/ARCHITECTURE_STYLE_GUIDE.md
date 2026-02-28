# Architecture Style Guide (Backend)

## Modèle recommandé

Pragmatisme avant pureté : **Domain-First + API Orchestrator**.

## Couches attendues

1. **API Orchestrator**
   - `apps/api/src/platform/*` (routes, wiring, dépendances HTTP)
   - Règle: aucune logique métier métier lourde.

2. **Application / Domain Services**
   - `apps/api/src/domains/*/application/*`
   - Règle: cas d’usage réutilisable, cache/fallback/orchestration métier.

3. **Domain Logic**
   - `apps/api/src/domains/*/api/*`, `apps/api/src/analytics/*`, `apps/api/src/research/*`, `apps/api/src/core/*`
   - Règle: logique testable et indépendante du framework.

4. **Infrastructure**
   - `apps/api/src/platform/legacy/*`, `apps/api/src/ingestion/*`, `apps/api/runtime/*`
   - Règle: intégration provider/fichiers, pas de contrat API ici.

## Règles transverses

- Les routes orchestrent, les services composent, les domaines calculent.
- Les appels LLM passent par des points dédiés (pas d’inline provider dans les routes).
- Un endpoint conserve un contrat stable (`ok/data`, erreurs structurées).
- Réutiliser en premier:
  - `docs/ops/REUSE_MODULES_CATALOG.md`
  - `docs/ops/LARGE_MODULE_REUSE_INDEX.md`
- Priorité d’emplacement:
  - Backend: `apps/api/src`
  - Frontend: `apps/web/src`
