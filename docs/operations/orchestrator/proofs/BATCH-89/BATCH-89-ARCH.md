# BATCH-89-ARCH - Plan d'architecture copilot brief/action/open portfolio-first

Date: 2026-04-15T15:58:00Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-89-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Reference pattern: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Cible produit
- Garder `BATCH-89` centre sur un brief du jour personnel qui expose une action priorisee issue du portefeuille ou de la watchlist, puis ouvre un memo d'investissement en un clic sans casser les surfaces existantes.
- Transformer `BATCH-89-ANALYSIS` en architecture executable sans nouveau batch, sans relance `ANALYSIS`, et sans redesign frontend.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Contrat partage existant: `packages/contracts/copilot_v1.py`
- Pattern endpoint reutilisable: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface runtime existante: `apps/api/runtime/copilot.sh`
- Surfaces web existantes: `apps/web/src/domains/forecasts/pages/personal-finance-start.html`, `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`, `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`

## Decisions d'architecture
1. Reutiliser `copilot_v1`, ne pas recreer un second contrat
   - `packages/contracts/copilot_v1.py` existe deja et couvre `brief_of_day`, `ranked_action`, `ask`, `open`, `portfolio_context`, `warnings`, `fallback_used`, `stats` et les metadonnees standard.
   - `DEV-01` doit durcir ce contrat existant seulement si un gap product-facing apparait; il ne doit pas reintroduire un payload route-local concurrent.

2. Extraire la forme publique hors de la route
   - `copilot.py` garde parsing, cache, singleflight, namespace rewrite et enveloppe HTTP.
   - La normalisation du payload `start`, le ranking de l'action priorisee, les metadonnees never-empty et la preparation du memo-open doivent converger vers une facade `application/copilot_endpoint_service.py` inspiree de Judge.
   - `copilot_service.py` reste le coeur metier; la facade endpoint assemble la forme publique sans dupliquer la logique.

3. Backend d'abord, reuse UI ensuite
   - `personal-finance-start.html` reste la page d'entree et continue de charger `copilot-panel.html`.
   - `copilot-panel.html` affiche le brief, l'action priorisee et les CTA ask/open.
   - `portfolio-health.html` porte le contexte portefeuille/watchlist qui explique l'action classee.
   - Aucun nouveau subtree frontend et aucun passage par `copilot-app/*`.

4. Validation ciblee avant fermeture du stream
   - `DEV-01` ferme la facade endpoint et la delegation route/service.
   - `DEV-02` branche les surfaces web existantes sur le payload classe sans redesign.
   - `DEV-03` ferme la matrice de tests delegation/contrat/fallback/metadonnees.
   - `ADMIN-01` verifie la verite runtime et l'absence de faux positif d'orchestration.

## Guardrails
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: nouveau batch parallele ou relance d'analyse
- Interdit: refonte visuelle frontend ou patch monitor hors besoin explicite du stream

## Acceptance gate
- Le contrat public reutilise `packages/contracts/copilot_v1.py` sans shape parallele route-locale.
- La route `copilot.py` n'heberge plus la logique profonde de payload `start` ou de ranking d'action.
- Les payloads degrades restent never-empty, machine-readable, et compatibles avec `personal-finance-start.html`, `copilot-panel.html` et `portfolio-health.html`.
- Les preuves `DEV-01..03` citent `root_cause`, `fix_applied`, `verify(before/after/test)`, `files_touched`, `tests_run`.

## Handoff attendu
- Handoff a `dev` sur `BATCH-89-DEV-01`.
- Portee du prochain pas: facade endpoint/service copilot et delegation backend, sans nouveau lot ni redesign UI.
