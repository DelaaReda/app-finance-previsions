# BATCH-90-ANALYSIS - Cadrage canonique du personal-finance copilot brief/ask/open

Date: 2026-04-15T18:37:00Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-90-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Pattern de reference: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Delta produit vise
- Garder `BATCH-90` focalise sur un copilot personal-finance qui commence par un brief du jour, expose une action priorisee, puis laisse l'utilisateur ask/open sans casser les surfaces web existantes.
- Corriger le trou de preuve planner cree par l'autobatch: l'action canonique suivante apres cette cloture est `BATCH-90-ARCH`, pas une nouvelle analyse, pas un nouveau batch.
- Rester sur un delta utilisateur visible: brief priorise et continuation memo-open en un clic, pas un patch d'orchestration sans effet produit.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Pattern endpoint reutilisable: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface runtime existante: `apps/api/runtime/copilot.sh`
- Surface web existante: `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
- Widget web existant: `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`

## Decisions de scope
1. Flux unique et dependances strictes
   - `BATCH-90` reste le seul stream canonique actif.
   - Le prochain pas apres cette cloture est `BATCH-90-ARCH`; aucun dispatch `dev` ne doit contourner `ARCH`.

2. Backend et contrat avant wiring final
   - Le brief, l'action priorisee et le memo-open restent dans la pile `copilot` existante.
   - La route garde parsing/enveloppe/cache; la logique produit et le payload public restent dans l'application ou une facade endpoint dediee.

3. UI en reuse, pas en redesign
   - Les surfaces `personal-finance-start.html` et `copilot-panel.html` servent d'hote au brief classe et au CTA ask/open.
   - Aucun nouveau subtree frontend, aucun `copilot-app/*`, aucune derive monitor hors besoin explicite du stream.

## Tracks attendus
- `BATCH-90-ARCH`
  Figera le contrat public, la repartition route/service et les guardrails de reuse.
- `BATCH-90-DEV-01`
  Implementera la normalisation backend du brief et de l'action priorisee.
- `BATCH-90-DEV-02`
  Branchera l'existant web sur le payload classe et l'ouverture ask/open sans redesign.
- `BATCH-90-DEV-03`
  Fermera la matrice de tests et la verification d'integration.
- `BATCH-90-ADMIN-01`
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
- Le prochain pas runtime est `BATCH-90-ARCH`, pas un nouveau batch ni un dispatch direct `dev`.

## Next
- Fermer `BATCH-90-ANALYSIS`, puis reprendre `BATCH-90-ARCH` pour transformer ce cadrage en contrat d'architecture exploitable par `dev`.
