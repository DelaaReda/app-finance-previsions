# BATCH-86-ARCH — Plan d'architecture copilot brief/ask/open

Date: 2026-04-15T08:29:38Z
Owner: planner

## Références canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-86-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Reference pattern: `docs/ops/JUDGE_PARITY_ENDPOINT_ARCHITECTURE.md`

## Cible produit
- Garder `BATCH-86` centré sur le copilot personnel: brief du jour, ouverture immédiate vers ask/open, sortie mémo explicable, sans casser le thème frontend existant.
- Faire converger le flux vers une surface Judge-parity minimale, sans refonte complète ni nouveau batch parallèle.

## Reuse-first map
- Route API existante: `apps/api/src/domains/copilot/api/copilot.py`
- Couche application existante: `apps/api/src/domains/copilot/application/copilot_service.py`
- Modèle de service endpoint: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- Surface UI existante: `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`

## Décisions d'architecture
1. Contrat public partagé d'abord
   - Stabiliser un contrat partagé `copilot_v1` pour les payloads brief/start/context utiles au panel et aux flows ask/open.
   - Aligner le contrat sur les métadonnées Judge utiles: `ok`, `data`, `generated_at`, `source[]`, `warnings[]`, `fallback_used` quand applicable.

2. Route fine, logique dans l'application
   - `copilot.py` reste un adaptateur: parsing, cache/singleflight, enveloppe HTTP, délégation.
   - La normalisation de payload, les fallbacks et l'assemblage des sorties mémo restent dans `copilot_service.py` ou une façade endpoint dédiée dans le même domaine.

3. Extraction minimale seulement si elle enlève un vrai poids de route
   - Si le flux brief/start/context garde trop de logique de forme dans la route, extraire un `copilot_endpoint_service.py` inspiré de Judge.
   - Ne pas dupliquer un second moteur de décision hors de la pile `copilot` et `judge`.

## Tracks d'implémentation attendus
- `BATCH-86-DEV-01`
  Stabiliser le contrat partagé `copilot_v1` et la parité de métadonnées pour le brief/start/context utilisé par le panel.
- `BATCH-86-DEV-02`
  Amincir `copilot.py` vers la couche application/endpoint service tout en gardant cache, singleflight et debug au niveau route seulement si endpoint-spécifique.
- `BATCH-86-DEV-03`
  Fermer la matrice de tests Judge-parity minimale: délégation de route, forme de contrat, mode dégradé, compatibilité panel existant.

## Guardrails
- Interdit: `copilot-app/*`
- Interdit: `backend/src/backend/src/*`
- Interdit: imports legacy `src.*`
- Interdit: refonte visuelle frontend ou nouveau thème
- Interdit: mélanger ici le hardening `portfolio_risk_profile_v1`; ce gap reste un sujet séparé et non patché dans ce tick

## Acceptance gate
- Le contrat public brief/start/context est partagé et stable pour le panel existant.
- La route `copilot.py` ne garde pas de logique métier profonde.
- Les payloads dégradés restent never-empty et machine-readable.
- Les preuves `DEV-01..03` citent `root_cause`, `fix_applied`, `verify(before/after/test)`, `files_touched`, `tests_run`.

## Handoff attendu
- Handoff à `dev` sur `BATCH-86-DEV-01`.
- Portée du prochain pas: contrat partagé + métadonnées backend, sans redesign UI ni nouveau lot parallèle.
