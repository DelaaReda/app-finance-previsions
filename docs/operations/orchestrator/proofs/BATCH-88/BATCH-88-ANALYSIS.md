# BATCH-88-ANALYSIS - Cadrage canonique du brief portfolio-first avec ranked actions

Date: 2026-04-15T11:32:35Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-88-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Pattern de reference: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Delta produit vise
- Garder `BATCH-88` focalise sur un brief du jour portfolio-first qui expose l'action priorisee la plus utile sur portefeuille ou watchlist.
- Ouvrir le memo d'investissement en un clic depuis le brief, sans detour par une nouvelle surface ou un nouveau batch.
- Eviter une nouvelle boucle d'analyse: l'action canonique suivante apres cette cloture est `BATCH-88-ARCH`.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Pattern endpoint reutilisable: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface runtime existante: `apps/api/runtime/copilot.sh`
- Surfaces web existantes: `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`, `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`

## Decisions de scope
1. Flux unique et dependances strictes
   - `BATCH-88` reste le seul stream canonique actif.
   - Le prochain pas est `BATCH-88-ARCH`; aucun dispatch `dev` ne doit contourner `ARCH`.

2. Backend et contrat avant wiring complet
   - Le classement du brief, la priorisation d'action et le memo-open restent dans la pile `copilot` existante.
   - La route garde seulement parsing/enveloppe/cache/singleflight; la logique produit et le payload public vivent dans l'application ou une facade endpoint dediee.

3. UI en reuse, pas en redesign
   - Les composants existants servent d'hote au brief classe et au CTA memo-open.
   - Aucun nouveau subtree frontend, aucune refonte visuelle, aucun detour monitor hors besoin explicite du stream.

## Tracks attendus
- `BATCH-88-ARCH`
  Fige le contrat public, la repartition route/service et les guardrails de reuse.
- `BATCH-88-DEV-01`
  Implementera la normalisation backend du brief portfolio-first et l'action priorisee.
- `BATCH-88-DEV-02`
  Branchera l'existant web sur le payload classe et l'ouverture memo sans redesign.
- `BATCH-88-DEV-03`
  Fermera la matrice de tests et la verification d'integration.
- `BATCH-88-ADMIN-01`
  Validera la verite runtime et l'absence de faux positif d'orchestration.

## Guardrails
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: nouveau batch parallele ou relance d'analyse hors flux canonique
- Interdit: refonte visuelle frontend ou patch monitor hors besoin explicite du stream

## Acceptance gate pour sortir ANALYSIS
- Un artefact planner cite `architecture_plan_ref`, `architecture_audit` et `vision_alignment`.
- Les surfaces canoniques impactees `apps/api`, `apps/web`, `apps/api/runtime` et `platform/automation` sont nommees explicitement.
- Le prochain pas runtime est `BATCH-88-ARCH`, pas un nouveau batch ni un dispatch direct `dev`.

## Next
- Fermer `BATCH-88-ANALYSIS`, puis reprendre `BATCH-88-ARCH` pour transformer ce cadrage en contrat d'architecture exploitable par `dev`.
