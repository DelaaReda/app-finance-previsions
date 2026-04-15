# BATCH-89-GOV_REVIEW - Revue finale de gouvernance

Date: 2026-04-15T17:00:00Z
Owner: planner

## References canoniques
- Architecture plan ref: `docs/ops/ACTIVE_DOCS_INDEX.md`
- Architecture audit ref: `docs/ops/BATCH-89-ANALYSIS-ARCHITECTURE_AUDIT.md`
- Vision ref: `docs/product/PRODUCT_VISION.md#One sentence`
- Runtime refs: `logs-codex-runs/orchestrator-state/priority-queue.json`, `logs-codex-runs/orchestrator-state/parallel-workstreams.json`

## Constat de fermeture
- `BATCH-89-DEV-01`, `BATCH-89-DEV-02`, `BATCH-89-DEV-03` et `BATCH-89-ADMIN-01` sont `DONE` dans le workboard canonique.
- `planner_subagent_active=none` et `BATCH-89-GOV_REVIEW` est la seule tache planner encore `IN_PROGRESS`.
- Les validations fraiches du tick confirment le flux copilot brief/ask/open et la sante monitor planner-only.

## Audit architecture
- Backend conserve: `apps/api/src/domains/copilot/api/copilot.py` delegue vers `apps/api/src/domains/copilot/application/copilot_service.py`.
- Surface web conservee: `apps/web/src/domains/forecasts/pages/personal-finance-start.html` et `apps/web/src/domains/forecasts/components/widgets/copilot-panel.html`.
- Runtime truth conserve: `apps/monitor/server.py` ne reouvre pas de faux blocker planner-only apres `BATCH-89-ADMIN-01`.
- Anti-regression confirme: pas de `copilot-app/*`, pas de `backend/src/backend/src/*`, pas d'imports legacy `src.*`.

## Validation du tick
- `python3 -m pytest apps/api/src/domains/copilot/tests/test_dev03_brief_of_day_delivery.py::TestDEV03BriefOfDayContract::test_copilot_start_injects_ask_and_open_fallbacks_when_missing -q`
- `python3 -m pytest apps/monitor/tests/test_status_lite_health_semantics.py -q`
- `python3 platform/automation/compat/projections/parallel_workstream.py context --role planner --limit 5`

## Decision de gouvernance
- Clore `BATCH-89-GOV_REVIEW` maintenant pour aligner la lane planner sur l'etat runtime courant.
- Ne pas creer de nouveau batch ni relancer d'analyse: la tache canonique active a deja transitionne en `DONE` cote dev/admin, il reste seulement la fermeture planner.
- La prochaine valeur utile n'est pas un nouveau dispatch planner dans ce tick, mais la publication de cette cloture canonique.

## Vision alignment
- batch: `BATCH-89`
- target: `portfolio_first_brief_with_ranked_actions`
- impact: clot la revue finale du slice personal-finance visible sans rouvrir de churn planner ni d'orchestration parasite
