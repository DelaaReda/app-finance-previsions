# BATCH-86-GOV_REVIEW - Revue finale de gouvernance

Date: 2026-04-15T09:53:17Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-86-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Runtime refs: `logs-codex-runs/orchestrator-state/priority-queue.json`, `logs-codex-runs/orchestrator-state/parallel-workstreams.json`

## Constat de fermeture
- `BATCH-86-DEV-01`, `BATCH-86-DEV-02`, `BATCH-86-DEV-03` et `BATCH-86-ADMIN-01` sont `DONE` dans le workboard canonique.
- `BATCH-86-GOV_REVIEW` reste la seule tache planner `IN_PROGRESS` sur ce stream.
- Aucun nouveau dispatch n'est necessaire pour produire un delta visible; la voie canonique est de fermer la revue finale sur preuves existantes.

## Audit architecture
- Backend cible conserve: `apps/api/src/domains/copilot/api/copilot.py` delegue vers `apps/api/src/domains/copilot/application/copilot_service.py`.
- Reuse pattern conserve: `apps/api/src/domains/judge/application/judge_endpoint_service.py` reste le modele de facades endpoint fines.
- Surface frontend preservee: `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`.
- Anti-regression confirme: pas de `copilot-app/*`, pas de `backend/src/backend/src/*`, pas d'imports legacy `src.*`.

## Decision de gouvernance
- Clore `BATCH-86-GOV_REVIEW` maintenant pour aligner la lane planner sur l'etat runtime courant.
- Ne pas creer de nouveau batch ni relancer d'analyse tant que `BATCH-86` n'est pas proprement referme.
- L'amelioration restante sur `projection_secondary_only` appartient a la fiabilite d'orchestration, pas au scope produit de `BATCH-86`.

## Vision alignment
- batch: `BATCH-86`
- target: `personal_finance_brief_ask_open_memo_without_theme_break`
- impact: la revue finale valide la fermeture du slice copilot visible sans casser les bornes de reuse ni reouvrir un faux cycle planner
