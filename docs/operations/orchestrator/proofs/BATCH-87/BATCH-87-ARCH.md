# BATCH-87-ARCH - Plan d'architecture portfolio-first brief/action/memo

Date: 2026-04-15T10:52:30Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-87-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Reference pattern: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Cible produit
- Garder `BATCH-87` centre sur un copilot portfolio-first: brief du jour, action priorisee issue du portefeuille ou de la watchlist, puis ouverture directe d'un memo d'investissement en un clic.
- Transformer l'analyse precedente en architecture executable sans ouvrir un batch parallele, sans relancer `ANALYSIS`, et sans redesign frontend.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Pattern endpoint reutilisable: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface runtime existante: `apps/api/runtime/copilot.sh`
- Surfaces web existantes: `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`, `apps/web/src/domains/forecasts/components/widgets/portfolio-health.html`

## Decisions d'architecture
1. Contrat public portfolio-first d'abord
   - Figer le payload public autour d'un brief du jour, d'une action classee unique et d'un chemin memo-open explicite.
   - Garder les metadonnees machine-readable utiles a la parite Judge: `ok`, `data`, `generated_at`, `sources[]`, `warnings[]`, `fallback_used` quand applicable.

2. Route fine, logique dans l'application
   - `copilot.py` reste limite au parsing, cache, singleflight, enveloppe HTTP et delegation.
   - Le ranking de l'action, la normalisation du payload public et la preparation du memo-open restent dans `copilot_service.py` ou une facade endpoint dediee dans le meme domaine.

3. Reuse UI incrementale
   - `copilot-panel.html` porte le CTA ask/open et la lecture du brief.
   - `portfolio-health.html` accueille le contexte portefeuille/watchlist de l'action priorisee sans nouvelle arborescence frontend.

## Tracks d'implementation attendus
- `BATCH-87-DEV-01`
  Stabiliser le contrat backend du brief portfolio-first et de l'action priorisee avec payload degrade never-empty.
- `BATCH-87-DEV-02`
  Brancher les widgets existants sur le payload classe et le chemin memo-open sans redesign.
- `BATCH-87-DEV-03`
  Fermer la matrice de tests integration/contract/fallback sur les surfaces existantes.
- `BATCH-87-ADMIN-01`
  Verifier la verite runtime canonique et l'absence de faux positifs d'orchestration apres livraison.

## Guardrails
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: nouveau batch parallele ou relance d'analyse
- Interdit: refonte visuelle frontend ou patch monitor hors besoin explicite du stream

## Acceptance gate
- Le contrat public brief/action/memo est explicite et reutilise les surfaces `copilot` existantes.
- La route `copilot.py` ne garde pas de logique metier profonde sur le ranking ou le memo-open.
- Les payloads degrades restent never-empty, machine-readable, et compatibles avec les widgets existants.
- Les preuves `DEV-01..03` citent `root_cause`, `fix_applied`, `verify(before/after/test)`, `files_touched`, `tests_run`.

## Handoff attendu
- Handoff a `dev` sur `BATCH-87-DEV-01`.
- Portee du prochain pas: contrat backend + normalisation du payload public, sans nouveau lot ni redesign UI.
