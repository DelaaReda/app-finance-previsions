# BATCH-90-ARCH - Contrat d'architecture pour le personal-finance starter brief/ask/open

Date: 2026-04-15T18:40:00Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/operations/orchestrator/proofs/BATCH-90/BATCH-90-ARCH.md#guardrails-et-audit`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Pattern de reference: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Delta produit vise
- Garder `BATCH-90` centre sur le starter personal-finance deja existant: brief du jour, action priorisee portefeuille ou watchlist, puis `ask` ou `open` sans sortir des surfaces actuelles.
- Fermer `BATCH-90-ARCH` doit debloquer `BATCH-90-DEV-01` maintenant, sans relance `ANALYSIS`, sans nouveau batch, et sans detour monitor-only.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Contrat partage existant: `packages/contracts/copilot_v1.py`
- Surface runtime existante: `apps/api/runtime/copilot.sh`
- Surfaces web existantes: `apps/web/src/domains/forecasts/pages/personal-finance-start.html`, `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`, `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`

## Decisions d'architecture
1. Reuse du contrat public avant toute extension
   - `packages/contracts/copilot_v1.py` reste le contrat canonique pour `brief_of_day`, `ranked_action`, `ask`, `open`, `portfolio_context`, `warnings` et les metadonnees never-empty.
   - `DEV-01` peut durcir le contrat existant si un trou produit apparait, mais ne doit pas recreer un payload route-local concurrent.

2. Route fine, logique publique en application
   - `copilot.py` garde le parsing HTTP, le cache, le singleflight et l'enveloppe.
   - La forme publique `start`, le ranking de l'action priorisee et la preparation du CTA `open` doivent converger dans la couche `application`, en suivant le modele Judge parity.
   - `copilot_service.py` reste le coeur metier; une facade endpoint dans `application/` est autorisee si elle evite la duplication de logique dans la route.

3. Reuse UI, pas de nouveau subtree
   - `personal-finance-start.html` reste la page d'entree.
   - `copilot-panel.html` reste le host du brief, de l'action priorisee et des CTA `ask/open`.
   - `portfolio-health.html` reste le support de contexte portefeuille ou watchlist justifiant l'action classee.

4. Sequence de livraison attendue
   - `BATCH-90-DEV-01`: backend facade endpoint/service et delegation route -> application.
   - `BATCH-90-DEV-02`: wiring des surfaces web existantes sur le payload classe.
   - `BATCH-90-DEV-03`: matrice de tests contrat, fallback et integration.
   - `BATCH-90-ADMIN-01`: validation runtime et absence de faux positif d'orchestration apres livraison.

## Guardrails et audit
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: nouveau batch parallele, relance `ANALYSIS`, ou redesign frontend
- Audit architecture:
  - aucun nouveau contrat public hors `packages/contracts/copilot_v1.py`
  - aucune logique produit profonde ajoutee dans `apps/api/src/domains/copilot/api/`
  - aucune derive produit dans `apps/monitor/*`; `platform/automation/*` reste reserve a la preuve runtime, pas au comportement copilot

## Acceptance gate
- `BATCH-90-DEV-01` livre une facade backend qui garde la route fine et la forme publique stable.
- Les payloads degrades restent never-empty et compatibles avec `personal-finance-start.html`, `copilot-panel.html` et `portfolio-health.html`.
- Les preuves `DEV-01..03` citent `root_cause`, `fix_applied`, `verify(before/after/test)`, `files_touched`, `tests_run`, `commit_sha`.

## Handoff attendu
- Handoff canonique: `BATCH-90-DEV-01`
- Portee du prochain pas: finaliser la facade endpoint/service copilot et debloquer le flux brief -> ranked action -> ask/open en reuse-only.
