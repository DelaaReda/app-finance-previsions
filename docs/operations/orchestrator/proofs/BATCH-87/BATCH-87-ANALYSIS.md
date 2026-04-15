# BATCH-87-ANALYSIS - Cadrage canonique du copilot portfolio-first brief/ask/open

Date: 2026-04-15T10:43:00Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-87-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Pattern de reference: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Delta produit vise
- Garder `BATCH-87` focalise sur une experience portfolio-first: brief du jour, action priorisee sur portefeuille ou watchlist, puis ouverture directe d'un memo d'investissement en un clic.
- Ne pas ouvrir de second batch, ne pas refondre le frontend, et ne pas detourner le flux vers une boucle d'analyse sans livraison.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Pattern endpoint reutilisable: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface runtime existante: `apps/api/runtime/copilot.sh`
- Surfaces web existantes: `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`, `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`

## Decisions de scope
1. Flux unique et dependances strictes
   - `BATCH-87` reste le seul stream canonique actif.
   - Le prochain pas apres cette cloture est `BATCH-87-ARCH`; aucun dispatch `dev` ne doit contourner `ARCH`.

2. Backend avant wiring UI
   - Le brief portfolio-first et l'action memo-open se construisent dans la pile `copilot` existante.
   - La route garde seulement parsing/enveloppe/cache/singleflight; la logique metier et la forme produit restent dans l'application ou une facade endpoint dediee.

3. UI en reuse, pas en redesign
   - Les widgets existants servent de surface d'integration pour le brief classe, le CTA ask/open et l'ouverture memo.
   - Les changements frontend doivent rester du wiring et de la presentation de donnees sur la base des composants existants.

## Tracks attendus
- `BATCH-87-ARCH`
  Figera le contrat public, la repartition route/service et les guardrails de reuse.
- `BATCH-87-DEV-01`
  Implementera la normalisation backend du brief portfolio-first et l'action priorisee.
- `BATCH-87-DEV-02`
  Branchera l'existant web sur le payload classe et l'ouverture memo sans redesign.
- `BATCH-87-DEV-03`
  Fermera la matrice de tests et la verification d'integration.
- `BATCH-87-ADMIN-01`
  Validera la verite runtime et l'absence de faux positif d'orchestration.

## Guardrails
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: nouveau batch parallele ou relance d'analyse hors flux canonique
- Interdit: refonte visuelle frontend ou patch moniteur hors besoin explicite du stream

## Acceptance gate pour sortir ANALYSIS
- Un artefact planner cite `architecture_plan_ref`, `architecture_audit` et `vision_alignment`.
- Les surfaces canoniques impactees `apps/api`, `apps/web`, `apps/api/runtime` sont nommees explicitement.
- Le prochain pas runtime est `BATCH-87-ARCH`, pas un nouveau batch ni un dispatch direct `dev`.

## Next
- Fermer `BATCH-87-ANALYSIS`, puis reprendre `BATCH-87-ARCH` pour transformer ce cadrage en contrat d'architecture exploitable par `dev`.
