# BATCH-89-ANALYSIS - Cadrage canonique du personal-finance copilot brief/ask/open

Date: 2026-04-15T15:41:00Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-89-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Pattern de reference: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Delta produit vise
- Garder `BATCH-89` focalise sur un copilot personal-finance qui ouvre sur un brief du jour, expose une action priorisee sur portefeuille ou watchlist, puis laisse ask/open sans sortir des surfaces existantes.
- Eviter une nouvelle boucle d'analyse ou un nouveau stream parallele: l'action canonique suivante apres cette cloture est `BATCH-89-ARCH`.
- Rester sur un delta utilisateur visible: brief priorise et memo-open en un clic, pas un patch d'orchestration sans livraison produit.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Pattern endpoint reutilisable: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface runtime existante: `apps/api/runtime/copilot.sh`
- Surfaces web existantes: `apps/web/src/domains/forecasts/pages/personal-finance-start.html`, `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`

## Decisions de scope
1. Flux unique et dependances strictes
   - `BATCH-89` reste le seul stream canonique actif.
   - Le prochain pas apres cette cloture est `BATCH-89-ARCH`; aucun dispatch `dev` ne doit contourner `ARCH`.

2. Backend et contrat avant wiring final
   - Le brief, le ranking d'action et le memo-open restent dans la pile `copilot` existante.
   - La route garde parsing/enveloppe/cache/singleflight; la logique produit et le payload public restent dans l'application ou une facade endpoint dediee.

3. UI en reuse, pas en redesign
   - Les surfaces `personal-finance-start.html` et `copilot-panel.html` servent d'hote au brief classe et au CTA memo-open.
   - Aucun nouveau subtree frontend, aucun `copilot-app/*`, aucune derive monitor hors besoin explicite du stream.

## Tracks attendus
- `BATCH-89-ARCH`
  Figera le contrat public, la repartition route/service et les guardrails de reuse.
- `BATCH-89-DEV-01`
  Implementera la normalisation backend du brief portfolio-first et l'action priorisee.
- `BATCH-89-DEV-02`
  Branchera l'existant web sur le payload classe et l'ouverture memo sans redesign.
- `BATCH-89-DEV-03`
  Fermera la matrice de tests et la verification d'integration.
- `BATCH-89-ADMIN-01`
  Validera la verite runtime et l'absence de faux positif d'orchestration.

## Guardrails
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: nouveau batch parallele ou relance d'analyse hors flux canonique
- Interdit: refonte visuelle frontend ou patch runtime non lie au stream produit

## Acceptance gate pour sortir ANALYSIS
- Un artefact planner cite `architecture_plan_ref`, `architecture_audit` et `vision_alignment`.
- Les surfaces canoniques impactees `apps/api`, `apps/web`, `apps/api/runtime` et `platform/automation` sont nommees explicitement.
- Le prochain pas runtime est `BATCH-89-ARCH`, pas un nouveau batch ni un dispatch direct `dev`.

## Next
- Fermer `BATCH-89-ANALYSIS`, puis reprendre `BATCH-89-ARCH` pour transformer ce cadrage en contrat d'architecture exploitable par `dev`.
