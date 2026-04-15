# BATCH-88-ARCH - Plan d'architecture brief portfolio-first avec ranked action

Date: 2026-04-15T11:48:12Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-88-ARCH-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Reference pattern: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Cible produit
- Garder `BATCH-88` centre sur un brief du jour portfolio-first qui expose une action priorisee utile sur portefeuille ou watchlist et ouvre un memo d'investissement en un clic.
- Transformer `BATCH-88-ANALYSIS` en architecture executable sans nouveau batch, sans relance `ANALYSIS`, et sans redesign frontend.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Contrat partage a completer: `packages/contracts/copilot_v1.py`
- Pattern endpoint reutilisable: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface page existante: `apps/web/src/domains/forecasts/pages/personal-finance-start.html`
- Surfaces widget existantes: `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`, `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`

## Decisions d'architecture
1. Contrat partage portfolio-first d'abord
   - Remplacer le placeholder `packages/contracts/copilot_v1.py` par un contrat type pour le payload start/brief.
   - Le contrat cible doit porter au minimum `brief_of_day`, `ranked_action`, `ask[]`, `open[]`, `portfolio_context`, et les metadonnees standard `ok`, `data`, `generated_at`, `source[]`, `warnings[]`, `fallback_used` quand necessaire.

2. Route fine, endpoint service dans le domaine
   - `copilot.py` reste limite au parsing, cache, singleflight, namespace rewrite et enveloppe HTTP.
   - L'assemblage du payload public, le ranking de l'action et la normalisation memo-open doivent vivre dans une couche `application/*`, idealement un `copilot_endpoint_service.py` appuye sur `copilot_service.py`.
   - Le pattern a copier est Judge-parity pour la separation route/service, pas la taille du monolithe `judge.py`.

3. Reuse UI incrementale
   - `personal-finance-start.html` reste la page d'entree du stream et continue de charger `copilot-panel.html`.
   - `copilot-panel.html` consomme le brief, les `ask/open`, et le CTA principal.
   - `portfolio-health.html` porte le contexte portefeuille/watchlist et les signaux de risque expliquant l'action priorisee.
   - Aucun nouveau subtree frontend, aucune refonte visuelle, aucun detour vers `copilot-app/*`.

4. Validation backend avant finition UX
   - `DEV-01` fige le contrat partage et la facade endpoint/service.
   - `DEV-02` branche la page et les widgets existants sur le payload classe sans changer l'architecture UI.
   - `DEV-03` ferme les tests route delegation, contrat, fallback/degraded, metadonnees, et compatibilite page/widget.

## Guardrails
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: nouveau batch parallele ou relance d'analyse
- Interdit: refonte visuelle frontend ou patch monitor hors besoin explicite du stream

## Acceptance gate
- `packages/contracts/copilot_v1.py` n'est plus un placeholder et couvre le payload portfolio-first public.
- La route `copilot.py` ne garde pas de logique metier profonde sur le ranking ou le memo-open.
- Les payloads degrades restent never-empty, machine-readable, et compatibles avec `personal-finance-start.html` et les widgets existants.
- Les preuves `DEV-01..03` citent `root_cause`, `fix_applied`, `verify(before/after/test)`, `files_touched`, `tests_run`.

## Handoff attendu
- Handoff a `dev` sur `BATCH-88-DEV-01`.
- Portee du prochain pas: contrat partage + facade endpoint/service backend, sans nouveau lot ni redesign UI.
