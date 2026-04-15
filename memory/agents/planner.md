# Planner agent memory
- 2026-03-20: Recheck confirmed BATCH-64 and BATCH-65 fully DONE.
- Active stream is BATCH-70.
- BATCH-70-ANALYSIS was stale IN_PROGRESS while PLAN and ARCH were already DONE and DEV-01 was READY_DEV.
- Canonical runtime repair applied by closing BATCH-70-ANALYSIS via planner_runtime_actions.py complete.
- Expected next action: dispatch or resume BATCH-70-DEV-01; do not reopen planner PLAN/ANALYSIS for this stream unless new runtime evidence appears.
- Use runtime truth/workboard as source of truth when planner.last_contract is stale.
- 2026-03-20 monitor/runtime recheck: no new code drift after 2026-03-14; live issue was operational drift.
- Monitor doctor now has a 45s budget in apps/monitor/server.py because fc_doctor live runtime cost reached ~17-37s under active planner load.
- Before resuming new delivery, inspect planner_subagent_manager status and cleanup stale running subagents with no live process (seen on BATCH-66/BATCH-68/BATCH-69/BATCH-70 during planner-only runtime).
- Treat planner_dispatch active entries older than a few hours without matching live process as stale runtime debt; cleanup first, then re-dispatch the current READY/IN_PROGRESS stream.
- Canonical runtime guard now exists in `platform/automation/runtime/truth/dispatch_snapshot.py`: SQLite-primary entries stuck `running/pending` in `wait_or_collect_result` for >45m with `last_meaningful_delta=none` are quarantined out of `active`.
- After applying the guard, a canonical planner recovery pass moved `BATCH-70` back to nominal runtime flow: stale analysis residue was quarantined, `planner_dispatch.active_count` dropped to 1, and `BATCH-70-DEV-01` became the only live `IN_PROGRESS` delivery task.
- [2026-03-20 15:38:21 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-70 task_id=BATCH-70-ANALYSIS next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-70-ANALYSIS directive=none/none message=none/none exec_report=none issues=planner_quality_autofill_missing suggestions=none
- 2026-03-20 architecture recheck: `priority-queue.json` and `parallel-workstreams.json` now advertise active cycle `BATCH-24`, so old `BATCH-70` planner memory is no longer scheduling truth.
- Treat repeated `BATCH-70-ANALYSIS` claims in planner audit / legacy subagent logs as stale runtime debt unless queue/workboard reactivate that stream.
- New routing invariant is active in code: capability `dev` must bind only to `dev` tasks and capability `admin` only to `admin` tasks; route-mismatched active/results must be ignored and quarantined, not merged.
- Planner rule: prefer queue/workboard active cycle over role memory when they disagree.
- 2026-03-20 late recheck: queue/workboard active cycle is `BATCH-24`, but `planner_subagent_manager status --role planner` still shows an active `BATCH-70-DEV-01` row and recent stale `BATCH-70-ANALYSIS` failures. Treat that as dispatch-coordination drift, not as canonical scheduling truth.
- Session freshness is no longer the primary blocker (`resume=0` confirmed after recycle). The next planner architecture fix is to stop stale non-active-cycle subagents and `RUN_LOCK_BUSY` overlap from keeping planner in `waiting_on_agents` against the wrong stream.
- 2026-03-20 live collaboration recheck: `codex_planner_cron` currently sits in `/home/venom/shared/analyse-financiere` and is blocked on an interactive Codex self-update prompt, so the tmux session itself is not evidence of productive planner work. Prefer queue/workboard + tick logs until the lane startup state is repaired.

## 2026-03-20 dispatch snapshot repair
- platform/automation/runtime/truth/dispatch_snapshot.py now quarantines active graph rows that conflict with workboard truth.
- Current truth for active stream: BATCH-70-DEV-01 is the live active capability (active_count=1, latest_owner_task_id=BATCH-70-DEV-01).
- planner.last_contract can remain stale on BATCH-70-ANALYSIS; prefer workboard + planner dispatch metrics until contract rewrite catches up.
- Do not re-open planner steps for BATCH-70; planner side is done and waiting on dev execution.
- [2026-03-20 15:45:48 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-70 task_id=BATCH-70-ANALYSIS next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-70-DEV-02 directive=none/none message=none/none exec_report=none issues=runtime_projection_mismatch,planner_quality_autofill_missing,planner_evidence_incomplete_soft suggestions=none
- [2026-03-20 16:03:24 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-70 task_id=BATCH-70-ANALYSIS next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-70-DEV-03 directive=none/none message=none/none exec_report=none issues=missing_architecture_plan_ref,missing_architecture_audit,planner_quality_autofill_missing suggestions=none
- [2026-03-20 16:34:13 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-70 task_id=BATCH-70-ANALYSIS next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-70-DEV-03 directive=none/none message=none/none exec_report=none issues=planner_complete_quote_error suggestions=none
- [2026-03-20 17:02:42 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-70 task_id=BATCH-70-ANALYSIS next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-70-ADMIN-01 directive=none/none message=none/none exec_report=none issues=dependency_policy_not_enforced,missing_architecture_plan_ref,missing_architecture_audit,planner_quality_autofill_missing suggestions=none
- [2026-03-20 17:49:52 EDT] role=planner source=primary_structured status=BLOQUE verdict=BLOCKED delta=ECHEC_VALIDATION_COMPLETE_B71_PLAN blocker=planner_delivery_proof_missing stream_id=none task_id=none next_action_unique=relancer_complete_BATCH-71-PLAN_avec_preuves_delivery_P1774043199_25697 directive=none/none message=none/none exec_report=none issues=planner_delivery_proof_missing suggestions=none
- [2026-03-20 18:04:18 EDT] role=planner source=primary_structured status=BLOCKED verdict=BLOCKED delta=DELIVERY_VALUE_INSUFFICIENT blocker=DELIVERY_VALUE_INSUFFICIENT stream_id=BATCH-71 task_id=BATCH-71-ANALYSIS next_action_unique=DELIVERY_VALUE_RETRY_PLANNER_1774044238 directive=none/none message=none/none exec_report=none issues=delivery_value_insufficient suggestions=none
- [2026-03-20 18:33:11 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-71 task_id=BATCH-71-ARCH next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-71-DEV-01 directive=none/none message=none/none exec_report=none issues=planner_quality_autofill_missing,delivery_value_insufficient suggestions=none
- [2026-03-20 19:05:00 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=none task_id=none next_action_unique=PLANNER_DISPATCH_ACTIVE_none directive=none/none message=none/none exec_report=none issues=contract_guard_claim_stream_id_missing suggestions=none
- [2026-03-20 19:32:42 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-71 task_id=BATCH-71-ANALYSIS next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-71-DEV-03 directive=none/none message=none/none exec_report=none issues=delivery_value_insufficient suggestions=none
- [2026-03-20 20:05:48 EDT] role=planner source=primary_structured status=BLOCKED verdict=BLOCKED delta=DELIVERY_VALUE_INSUFFICIENT blocker=DELIVERY_VALUE_INSUFFICIENT stream_id=BATCH-71 task_id=BATCH-71-ANALYSIS next_action_unique=DELIVERY_VALUE_RETRY_PLANNER_1774051524 directive=none/none message=none/none exec_report=none issues=planner_quality_autofill_missing,delivery_value_insufficient suggestions=none
- [2026-03-20 20:35:24 EDT] role=planner source=primary_structured status=BLOCKED verdict=BLOCKED delta=DELIVERY_VALUE_INSUFFICIENT blocker=DELIVERY_VALUE_INSUFFICIENT stream_id=BATCH-72 task_id=BATCH-72-PLAN next_action_unique=DELIVERY_VALUE_RETRY_PLANNER_1774053312 directive=none/none message=none/none exec_report=none issues=run_note_auto_fixed,planner_quality_autofill_missing,delivery_value_insufficient suggestions=none
- [2026-03-20 21:03:17 EDT] role=planner source=primary_structured status=BLOCKED verdict=BLOCKED delta=DELIVERY_VALUE_INSUFFICIENT blocker=DELIVERY_VALUE_INSUFFICIENT stream_id=BATCH-72 task_id=BATCH-72-ANALYSIS next_action_unique=DELIVERY_VALUE_RETRY_PLANNER_1774054975 directive=none/none message=none/none exec_report=none issues=delivery_value_insufficient suggestions=none
- [2026-03-20 21:38:01 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-72 task_id=BATCH-72-ARCH next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-72-DEV-01 directive=none/none message=none/none exec_report=none issues=planner_quality_autofill_missing,delivery_value_insufficient suggestions=none

  - repeated “create batch now” wording from shared prompt
  - repeated autonomy/novelty/stagnation wording already present in SYSTEM_PROMPT
- move_out_of_prompt:
  - none in this run; dynamic active-task steering already lives correctly in planner guardian patches
- tool_usage_improvements:
  - makes collect/repair/ack the explicit first move when canonical active work is downstream
  - keeps batch creation as fallback only when no executable canonical task exists
- expected_runtime_impact:
  - direct anti-churn effect by reducing premature planner rebatching and redundant ANALYSIS relaunches

Patch proposal
- patch_type: anti-churn
- create_now: yes
- target_file: platform/automation/cron_tmux_role_runner.sh
- exact_goal: shorten planner shared orchestration guidance and make canonical active-task follow-up win over automatic batch creation
- expected_gain: less redispatch, less duplicate-scope churn, clearer choice between collect/repair/ack and create/reshaper batch
- risk: low; planner still keeps the same policy in SYSTEM_PROMPT and guardian patches, only with less duplication

Measurement
- signals_to_watch:
  - planner_autobatch_stagnation_alert
  - planner_quality_autofill_missing
  - planner_evidence_incomplete_soft
  - ready_but_no_delta
  - ready_but_none_task_update
  - count of planner redispatch/retry on active downstream tasks
- success_criteria:
  - planner follows canonical downstream active tasks more often before creating new planner work
  - fewer planner retries tied to stale ANALYSIS relaunch or duplicate-scope creation
  - no increase in invalid 8-line contracts after the prompt shrink
- rollback_condition:
  - planner stops creating needed new batches when no executable canonical task exists
  - or guardian starts showing more idle/no-action failures after the patch

Decision
- next_owner: planner
- next_action: watch planner guardian/runtime signals after this shrink; if churn persists, target the planner-specific SYSTEM_PROMPT block next instead of broadening shared prompt text

## 2026-04-15T04:24:01Z vision-batch-architect

Continuity
- previous_verdict: keep BATCH-85 as sole priority; do not create a new batch before VM proof
- previous_top_priority: finish the low-cost brief/action/memo hardening and validate it on the VM
- previous_next_delivery: ship the existing copilot/portfolio/monitor reliability slice independently of orchestration churn
- changed_since_last_run: synced projections now show `BATCH-85-ANALYSIS=DONE` and `BATCH-85-ARCH=IN_PROGRESS`, but the batch object still lacks `summary`, `why_now`, and `user_visible_delta`; all `BATCH-85` work items still miss `runtime_role` and `runtime_kind`; local SQLite still has zero `BATCH-85` events; planner guardian and monitor latest still rely on stale or null secondary signals; and VM SSH remains sandbox-blocked

Reality check
- vision_alignment: mixed
- priority_clarity: clear
- active_batch_usefulness: moderate
- delivered_value_now: moderate

Top priorities
1. Finish and prove the existing `apps/api` + `apps/monitor` hardening on the brief -> ask/open -> memo slice.
2. Materialize the active batch canonically before counting progress: `BATCH-85` needs real Plane/runtime metadata and SQLite/runtime-truth presence, not just queue/workboard projection.
3. Freeze new batch creation until the active slice is VM-proven or clearly invalidated.

Rejected batch ideas
- New frontend batch for brief/top-action/watchlist polish: rejected because the existing web contracts already consume `brief_of_day`, `ask/open`, and `/personal-finance/*`; there is no theme-preserving sibling delta worth creating now.
- New memo explainability batch: rejected because `apps/api/src/domains/copilot/application/copilot_service.py` and `apps/api/src/domains/judge/application/judge_endpoint_service.py` already expose verdict, why, risks, confidence, freshness, and sources; the remaining gap is proof and reliability.
- New runtime/Plane sync batch: rejected because it would duplicate active hardening already happening in `platform/automation/*`, is not independent from the live batch, and is still too orchestration-heavy to outrank the user-facing slice.

Selected batch
- title: BATCH-85 - Fiabiliser le slice brief/action/memo a faible cout
- why_now: This remains the only active scope with direct product value. The dirty worktree shows real backend-first hardening on copilot, saved-portfolio fallback, and monitor truthfulness, while no other candidate offers a clearer or more independent user-visible delta.
- user_visible_delta: repeated `/api/copilot/start` and `/api/copilot/context` hits reuse cache, `/api/personal-finance/start` stays actionable without expensive live-risk fetches, `/api/personal-finance/ask` keeps an explainable memo contract, and monitor/status become more truthful about app health under degraded agentic/planning state.
- novelty_target: deliver a low-cost reliable brief + ask/open + memo starter path with portfolio-aware fallback and truthful status surfaces
- independence_from_active_batch: no
- create_now: no
- batch_class: hardening

Architecture fit
- aligned_with_backend_first: yes
- preserves_frontend_theme: yes
- adds_new_custom_plumbing: no
- canonical_paths_respected: no
- comments: The implementation slice uses the right product surfaces, but the active `BATCH-85` record itself is still projection-only and missing canonical batch/work-item metadata (`summary`, `why_now`, `user_visible_delta`, `runtime_role`, `runtime_kind`, `planning_source`), so creating another batch now would compound invalid planning state instead of fixing delivery.

Implementation architecture
- product slice: personal-first finance copilot starter flow: brief of the day -> immediate ask/open -> explainable investment memo -> lightweight portfolio/watchlist relevance -> honest degraded mode.
- current reality: `apps/api/src/domains/copilot/api/copilot.py` exposes `/api/copilot/context`, `/api/copilot/start`, and `/api/copilot/ask`; `apps/api/src/domains/copilot/application/copilot_service.py` already builds cached starter/context payloads, saved-portfolio context, playbook context, allocation drift alerts, and memo normalization; `apps/web/src/domains/forecasts/*` already consumes these contracts; `apps/monitor/services/status_service.py` and `apps/monitor/server.py` are being hardened for app-first truthful health; `BATCH-85` exists only in projections and not in local SQLite runtime truth.
- backend changes: finish and validate the active changes in `apps/api/src/domains/copilot/api/copilot.py` (start/context caching, namespace rewrites, never-empty payloads), `apps/api/src/domains/copilot/application/copilot_service.py` (saved portfolio fallback, low-cost context path, memo normalization, playbook/drift payloads), `apps/api/src/domains/judge/application/judge_endpoint_service.py` and `apps/api/src/domains/judge/api/judge.py` (keep personal-finance alias and explanation contract aligned), `apps/api/src/domains/market_data/application/portfolio_service.py` and `apps/api/src/domains/market_data/application/portfolio_performance_service.py` (composition-only / stale-cache fallback).
- frontend changes: none required for a new batch. Reuse existing pages/components under `apps/web/src/domains/forecasts/pages/app.js` and related contract tests; only verify contract compatibility if backend payload shapes shift.
- monitor/observability changes: keep `apps/monitor/services/status_service.py` focused on live-vs-doctor merge, runtime truth preference, OpenClaw probe correction, and app/product/agentic/planning split; keep `apps/monitor/server.py` limited to cached status endpoints and runtime-truth display, not planning logic.
- runtime/orchestration changes: only if the active batch still cannot be proven after product hardening. Then the minimal canonical fix lives in `platform/automation/runtime/planner/planner_runtime_actions.py`, `platform/automation/planner_subagent_manager.py`, and `platform/automation/runtime/truth/runtime_truth_reader.py` to materialize/import the active batch into SQLite and keep projections secondary. This is runtime debt tied to `BATCH-85`, not justification for a new sibling batch now.
- existing code to reuse: `apps/api/src/services/brief_generator.py`, `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/web/src/domains/forecasts/pages/app.js`, `apps/web/src/domains/forecasts/contracts/apiConnector.test.js`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/monitor/tests/test_status_event_store_fallback.py`, `scripts/delivery_value_smoke.sh`.
- files_or_modules_to_touch: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/api/src/domains/judge/api/judge.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/market_data/application/portfolio_service.py`, `apps/api/src/domains/market_data/application/portfolio_performance_service.py`, `apps/api/src/platform/run_api.py`, `apps/monitor/server.py`, `apps/monitor/services/status_service.py`, `apps/monitor/tests/test_status_event_store_fallback.py`, `scripts/restart_api_if_stale.sh`, `scripts/delivery_value_smoke.sh`.
- files_or_modules_not_to_touch: `apps/web/src/platform/*`, theme/shell CSS, `apps/api/runtime/*` for business logic, `docs/product/planning/*`, `memory/*` as planning truth, `logs-codex-runs/orchestrator-state/*.json`, and any new custom wrapper around Plane or runtime truth.
- api_or_contract_changes: no new route family. Keep `/api/copilot/start`, `/api/copilot/context`, `/api/personal-finance/start`, `/api/personal-finance/ask`, and memo keys stable. Only additive `cache`, `context_influence`, `playbook_context`, `allocation_drift_alerts`, `warnings`, and degraded metadata are acceptable.
- migration_or_compat_notes: `BATCH-85` is not Plane-ready and not runtime-real in this accessible environment: `priority-queue.json` has no `summary`, `why_now`, `user_visible_delta`, or `planning_source`; work items lack `runtime_role` and `runtime_kind`; and `orchestration-runtime.sqlite` has zero `BATCH-85` events. Plane MCP is unavailable here and VM SSH is sandbox-blocked, so this run cannot canonically fix creation or proof.
- proof_requirements: targeted pytest for copilot route/service cache and status fallback; smoke `scripts/delivery_value_smoke.sh`; VM proof of repeated `GET /api/copilot/context`, `GET /api/personal-finance/start`, `POST /api/personal-finance/ask`, `GET /api/status?lite=1`, and `bash scripts/fc_doctor.sh --json`.
- acceptance_criteria: the starter/context path is non-empty and cache-backed; ask returns verdict/horizon/why/risks/confidence/freshness/sources; saved portfolio/watchlist context remains useful without forced expensive live metrics; monitor/status reflect truthful app health even when planning/agentic surfaces are degraded; no frontend theme change; no projection-only batch counted as delivered.
- implementation_order: 1. finalize backend cache/fallback/memo contract hardening, 2. finalize portfolio low-cost fallback behavior, 3. finalize monitor/status truthfulness, 4. run targeted tests locally if the toolchain exists, 5. run canonical VM proof, 6. only then repair Plane/runtime metadata if a blocking gap remains.
- risks: cache TTL/signature bugs can hide freshness regressions; low-cost defaults can reduce richness if opt-in live paths disappear; `BATCH-85` still looks like false progress because projections advance without SQLite truth; VM proof is impossible in this sandbox due to SSH denial.
- non_goals: no new frontend redesign, no new batch/module, no manual queue/workboard edits, no custom planning wrapper, no pure orchestration backlog padding, no provider-plane redesign.

Decision
- create_in_plane_now: no
- if_no_reason: current batch should keep priority. No candidate is both independent and better than finishing the active hardening, and the active batch itself is not canonical enough to justify stacking a new module on top of it.
- next_owner: planner
- next_action: finish `BATCH-85` on real code surfaces, prove it on the VM, then either close it canonically or, if the backlog/runtime gap still blocks delivery, fix that gap as part of the same slice instead of creating a sibling batch.

## 2026-04-15T04:32:17Z vision-batch-architect

Continuity
- previous_verdict: no new batch; keep BATCH-85 as the only credible delivery scope.
- previous_top_priority: finish BATCH-85 hardening on the existing brief/action/memo slice and publish VM proof.
- previous_next_delivery: finish BATCH-85 backend/monitor hardening and validate it on the VM before any backlog move.
- changed_since_last_run: synced projections advanced BATCH-85 beyond planner-only setup (`BATCH-85-ANALYSIS` proof exists, `BATCH-85-ARCH` proof exists, `BATCH-85-DEV-01` now shows `IN_PROGRESS`), while the dirty worktree still matches the same backend-first hardening scope in `apps/api`, `apps/monitor`, and `platform/automation`; VM SSH and Plane MCP remain unavailable from this session.

Reality check
- vision_alignment: mixed
- priority_clarity: clear
- active_batch_usefulness: strong
- delivered_value_now: moderate

Top priorities
1. Finish BATCH-85 on the real product slice already in flight: cache-backed brief/context start path, low-cost portfolio fallback, and truthful monitor health.
2. Prove the slice on the VM with `/api/copilot/context`, `/api/personal-finance/start`, `/api/personal-finance/ask`, `api/status?lite=1`, and `fc_doctor`.
3. Only after VM proof, clean up any remaining Plane/runtime metadata gap for BATCH-85; do not open a sibling batch for the same scope.

Rejected batch ideas
- New brief/ask/open batch: rejected as redundant because the frontend already consumes this slice and BATCH-85 is the active hardening scope on the same user flow.
- New portfolio top-action batch: rejected as too dependent because the remaining delta is inside the current copilot + portfolio contract hardening already underway.
- New runtime/planner hygiene batch: rejected as too orchestration-heavy right now; any necessary metadata/runtime correction belongs as tail work inside BATCH-85 after product proof.

Selected batch
- title: BATCH-85 - Fiabiliser le slice brief/action/memo a faible cout
- why_now: It is the only active scope with a direct user-visible delta and the worktree proves it is already being implemented on canonical product surfaces instead of being speculative backlog.
- user_visible_delta: repeated starter/context hits become cache-backed, `/api/personal-finance/start` remains useful without forcing expensive live-risk fetches, `/api/personal-finance/ask` keeps a structured explainable memo, and monitor/status expose honest health even when planning or agentic surfaces degrade.
- novelty_target: reliable low-cost brief + ask/open + memo path with portfolio-aware fallback and truthful health signals
- independence_from_active_batch: no
- create_now: no
- batch_class: hardening

Architecture fit
- aligned_with_backend_first: yes
- preserves_frontend_theme: yes
- adds_new_custom_plumbing: no
- canonical_paths_respected: yes
- comments: The product implementation path is canonical (`apps/api/src/domains/*` first, existing `apps/web/src/domains/forecasts/*` reuse, `apps/monitor/*` only for truthful status). The only non-canonical part is planning provenance: BATCH-85 still appears projection-driven in this environment, which is a reason not to add another batch.

Implementation architecture
- product slice: personal-first Finance Copilot starter flow: daily brief -> immediate ask/open -> explainable memo -> portfolio/watchlist relevance -> honest degraded mode.
- current reality: `apps/api/src/domains/copilot/api/copilot.py` already owns `/api/copilot/context`, `/api/copilot/start`, and `/api/copilot/ask`; `apps/api/src/domains/copilot/application/copilot_service.py` already normalizes memo payloads and fallback context; `apps/web/src/domains/forecasts/pages/app.js` already renders the memo/start contracts; the active diffs add caching, saved-portfolio fallback, portfolio performance cache, single-worker API startup, and more truthful monitor status.
- backend changes: finish the in-flight changes in `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/judge/api/judge.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/market_data/application/dashboard_ui_service.py`, `apps/api/src/domains/market_data/application/portfolio_service.py`, `apps/api/src/domains/market_data/application/portfolio_performance_service.py`, and `apps/api/src/platform/run_api.py`.
- frontend changes: no new frontend batch needed; preserve the existing shell/theme and only verify compatibility of the current backend contracts against `apps/web/src/domains/forecasts/pages/app.js` and its tests.
- monitor/observability changes: keep the current work limited to `apps/monitor/server.py` and `apps/monitor/services/status_service.py` so app runtime, planning, provider, and runtime-truth surfaces stay truthful without adding planning logic to monitor.
- runtime/orchestration changes: only if BATCH-85 cannot be proven/closed after product hardening; then the minimum justified surfaces are `platform/automation/runtime/planner/planner_runtime_actions.py`, `platform/automation/runtime/planner/planner_board_runtime.py`, `platform/automation/planner_subagent_manager.py`, and `platform/automation/runtime/truth/runtime_truth_reader.py` to make active-state import/visibility consistent.
- existing code to reuse: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/services/brief_generator.py`, `apps/api/src/domains/judge/application/intelligence_service.py`, `apps/web/src/domains/forecasts/pages/app.js`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/monitor/tests/test_status_event_store_fallback.py`, `platform/automation/tests/test_planner_runtime_actions.py`, `platform/automation/tests/test_planner_board_runtime.py`, and `scripts/delivery_value_smoke.sh`.
- files_or_modules_to_touch: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/api/src/domains/judge/api/judge.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/market_data/application/dashboard_ui_service.py`, `apps/api/src/domains/market_data/application/portfolio_service.py`, `apps/api/src/domains/market_data/application/portfolio_performance_service.py`, `apps/api/src/platform/run_api.py`, `apps/monitor/server.py`, `apps/monitor/services/status_service.py`, `apps/monitor/tests/test_status_event_store_fallback.py`, `platform/automation/runtime/planner/planner_runtime_actions.py`, `platform/automation/runtime/planner/planner_board_runtime.py`, `platform/automation/tests/test_planner_runtime_actions.py`, `platform/automation/tests/test_planner_board_runtime.py`, `scripts/delivery_value_smoke.sh`.
- files_or_modules_not_to_touch: `apps/web/src/platform/*`, theme/shell styling, `apps/api/runtime/*` for business logic, `docs/product/planning/*`, `memory/*` as planning truth, `logs-codex-runs/orchestrator-state/*.json`, and any custom wrapper around Plane/backlog.
- api_or_contract_changes: no new route family; keep `/api/copilot/context`, `/api/copilot/start`, `/api/copilot/ask`, `/api/personal-finance/start`, and `/api/personal-finance/ask` stable, with only additive cache/fallback/degraded metadata.
- migration_or_compat_notes: Plane creation is not possible here and VM proof is blocked by SSH denial, so this run cannot repair canonical planning provenance. Do not translate that limitation into a new batch or local projection mutation.
- proof_requirements: targeted tests around copilot caching/memo contracts and monitor runtime-truth fallback, plus VM proofs for `/api/copilot/context`, `/api/personal-finance/start`, `/api/personal-finance/ask`, `/api/status?lite=1`, and `bash scripts/fc_doctor.sh --json`.
- acceptance_criteria: the starter/context path is non-empty and cheap on repeated calls; ask returns verdict/horizon/why/risks/confidence/freshness/sources; saved portfolio/watchlist context remains useful under fallback; monitor reports app runtime truthfully even if planning/agentic surfaces degrade; no theme regression; no new batch created for the same scope.
- implementation_order: 1. finish backend contract/cache/fallback hardening, 2. finish portfolio low-cost composition and performance cache behavior, 3. finish monitor/status truthfulness, 4. run targeted local tests where possible, 5. run canonical VM proof, 6. only then fix Plane/runtime metadata if still blocking.
- risks: stale caches can hide freshness regressions; low-cost defaults can reduce richness if live enrichments silently disappear; planning/runtime projections may overstate progress before SQLite/VM proof catches up; SSH denial prevents final runtime confirmation in this session.
- non_goals: no new frontend redesign, no sibling batch, no manual queue/workboard edits, no new custom orchestration plumbing, no backlog padding for pure runtime hygiene.

Decision
- create_in_plane_now: no
- if_no_reason: current batch should keep priority. No candidate is independent enough to justify a new module, and the remaining gap is finishing and proving the existing BATCH-85 slice.
- next_owner: planner
- next_action: finish BATCH-85 on the current code surfaces, validate it on the VM, then fix any leftover Plane/runtime metadata only if that still blocks canonical closure.
- [2026-04-15 00:32:59 EDT] role=planner source=primary_structured status=BLOCKED verdict=BLOCKED delta=PLANNER_RUNTIME_ACTIONS_FAILED blocker=PLANNER_RUNTIME_ACTIONS_FAILED stream_id=none task_id=none next_action_unique=PLANNER_RUNTIME_ACTIONS_FAILED directive=none/none message=none/none exec_report=none issues=none suggestions=none

## 2026-04-15T04:40:36Z endpoint-architecture-steward

Target endpoint
- endpoint: `/api/copilot/context`
- why_this_endpoint: active reliability work is already landing here, and this endpoint sits upstream of the brief/action/memo starter flow while still lacking a real shared contract.
- current_product_role: backend-first context bootstrap for brief of day, starter entry points, portfolio-aware fallback, and the `/api/personal-finance/context` alias.

Judge reference mapping
- contract_reference: `/Users/venom/Documents/analyse-financiere/packages/contracts/judge_v1.py`
- route_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/judge.py`
- application_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py`
- service_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py`
- intelligence_or_context_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/intelligence_service.py`
- invariants_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md`

Current state
- current_contract: ad hoc dict payload from `apps/api/src/domains/copilot/application/copilot_service.py:build_context_payload`, with keys like `regime`, `confidence`, `daily_brief`, `entry_points`, `copilot_start`, `portfolio_context`, `context_influence`, `regime_detection`, and `allocation_drift_alerts`; `packages/contracts/copilot_v1.py` is still a placeholder.
- route_thin_or_fat: medium-fat; `apps/api/src/domains/copilot/api/copilot.py` still owns cache keying, in-memory cache storage, singleflight, namespace rewriting, and fallback response assembly.
- application_logic_present: yes; core aggregation and fallback building live in `apps/api/src/domains/copilot/application/copilot_service.py`.
- service_layer_present: partial; there is domain application code, but no Judge-like endpoint facade dedicated to public response normalization.
- metadata_present: partial; nested payloads expose `generated_at`, `freshness`, and `source`, but the top-level endpoint contract is not standardized.
- never_empty_present: yes; route and service both fall back to snapshot/local payloads rather than raising a hard 500 in the nominal product path.
- fallback_present: yes; explicit snapshot/local fallback exists for market context and starter payloads.
- tests_present: yes for route fallback/cache and service behavior, but no shared typed contract enforcement tied to `packages/contracts/copilot_v1.py`.

Gap vs Judge
- contract_gap: Judge has a real typed shared contract in `packages/contracts/judge_v1.py`; copilot context still has no typed public DTO.
- route_gap: Judge’s target pattern is orchestration-only routing, while copilot context still embeds cache, singleflight, namespace rewrite, and fallback shaping directly in the route.
- application_gap: copilot aggregation exists, but public response normalization is still split between route helpers and application code instead of being isolated behind one endpoint-facing service.
- service_gap: there is no reusable `copilot_endpoint_service` equivalent to `judge_endpoint_service.py`.
- metadata_gap: metadata is nested and inconsistent rather than exposed as a stable top-level standard payload with explicit warnings/fallback flags.
- never_empty_gap: behavior is already never-empty, but the degraded-mode contract is implicit and not typed.
- fallback_gap: fallback is real but not standardized; frontend freshness/provenance/degradation still depend on nested conventions instead of one stable contract.
- testing_gap: route/service tests exist, but there is no typed contract test matrix comparable to Judge’s contract/orchestration/fallback coverage.

Target architecture
- target_contract: implement a real `CopilotContextResponse` family in `packages/contracts/copilot_v1.py` covering `daily_brief`, `entry_points`, `copilot_start`, `portfolio_context`, `context_influence`, `regime_detection`, `allocation_drift_alerts`, and explicit degraded metadata.
- target_route_design: keep `apps/api/src/domains/copilot/api/copilot.py` limited to input normalization, cache/singleflight, alias namespace rewrite, and service invocation.
- target_application_design: keep `build_context_payload` as the domain aggregation layer for market context, portfolio enrichment, playbook context, and brief generation.
- target_service_design: add a dedicated endpoint facade in `apps/api/src/domains/copilot/application/copilot_endpoint_service.py` to normalize metadata, fallback flags, warnings, and public shape before the route returns.
- target_metadata: expose stable top-level metadata fields such as `generated_at`, `freshness`, `source`, `warnings`, `filters_applied`, `stats`, `fallback_used`, and `cache`.
- target_fallback_model: preserve `ok=true` with snapshot-backed degraded payloads, but make degradation explicit and typed instead of route-specific.
- target_test_matrix: shared contract tests for `copilot_v1`, route orchestration/cache tests, fallback/degraded-mode tests, alias parity tests for `/api/personal-finance/context`, and endpoint-service normalization tests.

Implementation plan
- files_or_modules_to_create: `packages/contracts/copilot_v1.py` real DTOs; `apps/api/src/domains/copilot/application/copilot_endpoint_service.py`; one new copilot context contract test module.
- files_or_modules_to_modify: `apps/api/src/domains/copilot/api/copilot.py`; `apps/api/src/domains/copilot/application/copilot_service.py`; `apps/api/src/domains/copilot/tests/test_copilot_context_route_fallback.py`; `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`; any existing copilot contract tests that should validate the shared DTO.
- files_or_modules_not_to_touch: Judge route/service implementation, frontend theme/shell files, monitor status logic, queue/workboard/docs as planning truth, and any new custom wrapper around Plane/runtime truth.
- compatibility_notes: keep `/api/copilot/context` and `/api/personal-finance/context` stable; keep existing keys additive-compatible, especially `daily_brief`, `entry_points`, `copilot_start`, `portfolio_context`, `context_influence`, `regime_detection`, and `allocation_drift_alerts`.
- implementation_order: 1. define typed shared contract, 2. extract endpoint facade for normalization and metadata, 3. slim the route to orchestration-only concerns, 4. wire tests to the shared contract, 5. prove alias/cache/fallback parity.
- risks: extracting response normalization out of the route can regress namespace rewriting or cache semantics; hardening the contract can surface nested payload inconsistencies already tolerated by current consumers.
- non_goals: no new route family, no frontend redesign, no duplication of Judge monolith internals, no movement of product logic into the frontend, no global refactor of the full copilot domain.

Decision
- patch_now: no
- if_no_reason: this gap spans shared contract + new endpoint facade + route reshaping, while the current batch already contains a shippable reliability slice; host-only analysis is enough to define the next backend step, not to bundle a broader refactor blindly.
- next_owner: backend_engineer
- next_action: implement `packages/contracts/copilot_v1.py` and `copilot_endpoint_service.py`, then move `/api/copilot/context` response normalization out of the route and add shared contract coverage.

## 2026-04-15T04:38:43Z vision-batch-architect

Continuity
- previous_verdict: no new batch created; BATCH-85 remains the sole valid scope.
- previous_top_priority: finish BATCH-85 and publish VM proof on the brief/action/memo slice.
- previous_next_delivery: complete the active copilot/portfolio/monitor hardening and validate `/api/copilot/context`, `/api/personal-finance/start`, `/api/personal-finance/ask`, `/api/status?lite=1`, and `fc_doctor` on the VM.
- changed_since_last_run: the accessible runtime snapshot regressed to projection-only truth again (`priority-queue.json` still says `BATCH-85` should reopen ANALYSIS, `user_value_delta_visible=0`, and work items still lack `runtime_role`/`runtime_kind`), the local SQLite snapshot has no `events` or `planner_graph` tables at all, the dirty worktree is still concentrated on the active copilot/portfolio/monitor hardening slice, and SSH to `dev-vm-utm` is still sandbox-blocked before the remote safety gate can run.

Reality check
- vision_alignment: mixed
- priority_clarity: clear
- active_batch_usefulness: strong
- delivered_value_now: moderate

Top priorities
1. Finish BATCH-85 on the existing product slice: low-cost starter/context, portfolio-aware fallback, explainable ask/memo, and truthful monitor health.
2. Re-establish canonical proof for BATCH-85 after product hardening: VM runtime checks first, then Plane/runtime metadata convergence if still needed.
3. Keep new backlog creation frozen until the current slice is either VM-proven or clearly shown to be the wrong scope.

Rejected batch ideas
- New Judge-parity batch for `/api/copilot/start`: rejected because the endpoint gap is real but it sits inside the active BATCH-85 hardening slice and is not independent enough to justify a sibling module now.
- New watchlist/top-action batch: rejected as premature because the current starter payload, portfolio fallback, and memo contract are still the bottleneck before extra decision surfaces.
- New planner/runtime cleanup batch: rejected as too orchestration-heavy right now; any necessary reconciliation belongs as tail work inside BATCH-85 after product proof.

Selected batch
- title: BATCH-85 - Fiabiliser le slice brief/action/memo a faible cout
- why_now: It remains the only scope with visible user value already under implementation on canonical product surfaces, and no independent candidate beats finishing it.
- user_visible_delta: `/api/copilot/start` and `/api/copilot/context` stay fast and non-empty on repeated calls, `/api/personal-finance/start` stays actionable without forced live-risk fetches, `/api/personal-finance/ask` keeps an explainable memo contract, and monitor/status stop overstating runtime health.
- novelty_target: reliable low-cost brief + ask/open + memo path with portfolio-aware fallback and truthful degraded status
- independence_from_active_batch: no
- create_now: no
- batch_class: hardening

Architecture fit
- aligned_with_backend_first: yes
- preserves_frontend_theme: yes
- adds_new_custom_plumbing: no
- canonical_paths_respected: yes
- comments: the code changes stay inside `apps/api/src/domains/*`, `apps/monitor/*`, and minimal runtime truth readers. The blocker is not missing architecture detail; it is lack of canonical convergence and VM proof.

Implementation architecture
- product slice: personal-first starter flow: brief of the day -> ask/open -> explainable memo -> portfolio-aware fallback -> honest degraded mode.
- current reality: `apps/api/src/domains/copilot/api/copilot.py` already exposes the main starter/context/ask routes; `apps/api/src/domains/copilot/application/copilot_service.py` already assembles daily brief, entry points, portfolio context, playbook context, regime detection, and memo normalization; `apps/web/src/domains/forecasts/pages/app.js` already consumes the existing contracts; the active diffs remain concentrated on those surfaces plus `apps/monitor`.
- backend changes: finish the in-flight hardening in `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/judge/api/judge.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/market_data/application/dashboard_ui_service.py`, `apps/api/src/domains/market_data/application/portfolio_service.py`, `apps/api/src/domains/market_data/application/portfolio_performance_service.py`, and `apps/api/src/platform/run_api.py`.
- frontend changes: no new frontend batch. Preserve existing shell/theme and only keep contract compatibility with `apps/web/src/domains/forecasts/pages/app.js` and its tests.
- monitor/observability changes: keep the active work constrained to `apps/monitor/server.py`, `apps/monitor/services/status_service.py`, and status fallback tests so the monitor reflects app/runtime truth without becoming a planning engine.
- runtime/orchestration changes: only after product proof if closure is still blocked; then the smallest justified surfaces are `platform/automation/runtime/planner/planner_runtime_actions.py`, `platform/automation/runtime/planner/planner_board_runtime.py`, `platform/automation/runtime/truth/dispatch_snapshot.py`, and `platform/automation/runtime/truth/runtime_truth_reader.py`.
- existing code to reuse: `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/services/brief_generator.py`, `apps/api/src/domains/judge/application/intelligence_service.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/api/src/domains/market_data/tests/test_endpoint_cache_contracts.py`, `apps/monitor/tests/test_status_event_store_fallback.py`, and `scripts/delivery_value_smoke.sh`.
- files_or_modules_to_touch: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/api/src/domains/judge/api/judge.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/market_data/application/dashboard_ui_service.py`, `apps/api/src/domains/market_data/application/portfolio_service.py`, `apps/api/src/domains/market_data/application/portfolio_performance_service.py`, `apps/api/src/platform/run_api.py`, `apps/monitor/server.py`, `apps/monitor/services/status_service.py`, `apps/monitor/tests/test_status_event_store_fallback.py`, `platform/automation/runtime/planner/planner_board_runtime.py`, `platform/automation/runtime/planner/planner_runtime_actions.py`, `platform/automation/runtime/truth/dispatch_snapshot.py`, `platform/automation/runtime/truth/runtime_truth_reader.py`, and `scripts/delivery_value_smoke.sh`.
- files_or_modules_not_to_touch: `apps/web/src/platform/*`, theme/shell styling, `apps/api/runtime/*` for product behavior, `docs/product/planning/*`, `memory/*` as backlog truth, `logs-codex-runs/orchestrator-state/*.json`, and any new custom wrapper around Plane/runtime truth.
- api_or_contract_changes: no new route family. Keep `/api/copilot/start`, `/api/copilot/context`, `/api/personal-finance/start`, `/api/personal-finance/ask`, and the memo keys stable, with only additive cache/fallback/degraded metadata.
- migration_or_compat_notes: accessible local snapshots are still non-canonical for proof: `priority-queue.json` and `parallel-workstreams.json` miss required metadata, and the local SQLite snapshot lacks runtime tables. Plane MCP is unavailable here and VM SSH is sandbox-blocked, so this run cannot create or reconcile canonically.
- proof_requirements: targeted route/service tests for copilot start/context and status fallback; smoke `scripts/delivery_value_smoke.sh`; canonical VM proofs for `/api/copilot/context`, `/api/personal-finance/start`, `/api/personal-finance/ask`, `/api/status?lite=1`, and `bash scripts/fc_doctor.sh --json`.
- acceptance_criteria: starter/context responses are non-empty and cache-backed; ask returns verdict/horizon/why/risks/confidence/freshness/sources; saved portfolio/watchlist fallback remains useful without forced expensive fetches; monitor exposes truthful degraded health; no theme changes; no sibling batch created for the same slice.
- implementation_order: 1. finish backend contract/cache/fallback hardening, 2. finish portfolio low-cost composition and cache behavior, 3. finish monitor truthfulness, 4. run targeted local tests where possible, 5. run canonical VM proof, 6. only then repair Plane/runtime metadata if it still blocks closure.
- risks: cache signature drift can hide freshness regressions; low-cost defaults can silently reduce richness if live enrichments disappear; projection-only planning state can overstate progress; sandboxed SSH prevents final VM validation in this session.
- non_goals: no new frontend redesign, no sibling batch, no manual queue/workboard edits, no backlog padding, no pure orchestration batch detached from user value.

Decision
- create_in_plane_now: no
- if_no_reason: current batch should keep priority. The strongest remaining gap is finishing and proving the existing slice, not creating another module.
- next_owner: planner
- next_action: finish BATCH-85 on the existing code surfaces, validate it on the VM, then repair Plane/runtime metadata only if canonical closure is still blocked.

## 2026-04-15T04:38:43Z endpoint-architecture-steward

Target endpoint
- endpoint: GET `/api/copilot/start` (alias GET `/api/personal-finance/start`)
- why_this_endpoint: it is the closest backend entrypoint to the target experience (`brief du jour` -> `ask/open` in 2-3 clicks) and it still carries route-level cache/fallback/orchestration logic that should converge toward Judge-style thin routing.
- current_product_role: deliver the starter payload used by the personal finance home flow: brief of the day, immediate ask/open actions, portfolio-aware context, and degraded mode without breaking the frontend.

Judge reference mapping
- contract_reference: `packages/contracts/judge_v1.py`
- route_reference: `apps/api/src/domains/judge/api/judge.py`
- application_reference: `apps/api/src/domains/judge/application/judge_pipeline.py`
- service_reference: `apps/api/src/domains/judge/application/judge_endpoint_service.py`
- intelligence_or_context_reference: `apps/api/src/domains/judge/application/intelligence_service.py`
- invariants_reference: `apps/api/src/domains/judge/INVARIANTS.md`

Current state
- current_contract: implicit route/service contract returning `ok/data` with `brief_of_day`, `ask`, `open`, `generated_at`, `freshness`, `source`, `sources`, `filters_applied`, `stats`, `warnings`, `cache`, and optional `note`, `context_influence`, `portfolio_context`, `regime_detection`, `allocation_drift_alerts`; no shared `packages/contracts/*` schema exists for this endpoint.
- route_thin_or_fat: fat
- application_logic_present: yes
- service_layer_present: partial
- metadata_present: yes
- never_empty_present: yes
- fallback_present: yes
- tests_present: yes

Gap vs Judge
- contract_gap: no canonical shared contract file; frontend and tests rely on an implicit shape owned by route + service helpers.
- route_gap: the route owns cache keys, cache storage, singleflight, namespace rewriting, fallback assembly, effective-scope resolution, and final response shaping instead of delegating most of it to an application/service facade.
- application_gap: `copilot_service.build_context_payload()` exists, but starter-specific normalization (`_build_start_response`, namespace rewrites, effective-scope handling) still lives in the API layer.
- service_gap: there is no dedicated reusable start endpoint service equivalent to `judge_endpoint_service.py`; reuse is partial and spread across route-private helpers.
- metadata_gap: metadata is present but not standardized through a typed contract or a single service-level builder.
- never_empty_gap: nominally solved, but the never-empty guarantee depends on route-local fallback assembly instead of a reusable service boundary.
- fallback_gap: explicit fallback exists, but the degraded note/source/cache behavior is split across route-private helpers rather than one service decision point.
- testing_gap: route cache tests and service tests exist, but there is no shared contract test matrix anchored to a typed starter schema and no explicit thin-route regression test.

Target architecture
- target_contract: add a canonical shared starter contract in `packages/contracts/` (for example `copilot_start_v1.py`) covering `brief_of_day`, `ask`, `open`, `freshness`, `source(s)`, `warnings`, `filters_applied`, `stats`, `cache`, and additive degraded metadata.
- target_route_design: keep the FastAPI route as a thin adapter: parse `tickers/namespace/debug`, invoke a public service method, and return `{\"ok\": True, \"data\": ...}`. Cache/singleflight may stay at route boundary only if they wrap a single service call and do not own fallback logic.
- target_application_design: move starter-specific shaping into the application layer: build effective scope, rewrite namespace targets, assemble response metadata, and decide degraded note/source in one public function.
- target_service_design: expose a reusable facade (either a new `apps/api/src/domains/copilot/application/copilot_start_service.py` or a new public `build_start_payload(...)` entrypoint in `copilot_service.py`) that returns the final typed starter payload and keeps route helpers private-free.
- target_metadata: standardized `freshness/generated_at`, `source(s)`, `warnings`, `filters_applied`, `stats`, and `cache`, plus explicit degraded note/context metadata when fallback is used.
- target_fallback_model: service-level never-empty fallback using local brief + entry points + saved portfolio scope when context service is unavailable, preserving the public contract and making degradation explicit instead of inferred.
- target_test_matrix: 1. typed contract validation test, 2. route orchestration test for thin adapter behavior, 3. cache/singleflight hit + debug bypass test, 4. degraded fallback test, 5. namespace alias parity test for `/personal-finance/start`.

Implementation plan
- files_or_modules_to_create: `packages/contracts/copilot_start_v1.py` (or equivalent canonical contract module), optionally `apps/api/src/domains/copilot/application/copilot_start_service.py` if the existing `copilot_service.py` would stay too monolithic.
- files_or_modules_to_modify: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py` or the new `copilot_start_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, and `apps/api/src/domains/market_data/tests/test_endpoint_cache_contracts.py`.
- files_or_modules_not_to_touch: `apps/web/src/platform/*`, theme/shell assets, `apps/api/runtime/*`, `apps/monitor/*`, and `platform/automation/*` for this endpoint-specific convergence.
- compatibility_notes: keep `/api/copilot/start` and `/api/personal-finance/start` unchanged; preserve additive-only response evolution so existing frontend consumers keep working.
- implementation_order: 1. freeze the public contract in `packages/contracts`, 2. introduce the reusable starter service/facade, 3. slim the route to parse/cache/delegate only, 4. harden tests for contract/fallback/cache/alias behavior.
- risks: careless extraction can duplicate logic already inside `build_context_payload()`, break cache semantics, or regress namespace rewriting for `/personal-finance/start`.
- non_goals: no new route family, no frontend redesign, no ask/memo behavior rewrite, no new custom runtime plumbing.

Decision
- patch_now: no
- if_no_reason: the endpoint gap is real but still belongs to the active BATCH-85 hardening slice; patching it from this run would overlap in-flight work rather than clarify an independent next move.
- next_owner: dev
- next_action: fold `/api/copilot/start` Judge-parity convergence into BATCH-85 after the current hardening lands, starting with a shared contract and a dedicated service facade before any further frontend changes.

## 2026-04-15T04:38:31Z endpoint-architecture-steward

Target endpoint
- endpoint: /api/copilot/context
- why_this_endpoint: active BATCH-85 explicitly depends on the brief -> ask/open -> memo starter path, and `/api/copilot/context` is the backend-first entry surface that feeds both `/api/copilot/start` and the personal-finance aliases.
- current_product_role: expose the brief of day, entry points, portfolio-aware fallback context, and starter payload in one low-cost response.

Judge reference mapping
- contract_reference: `/Users/venom/Documents/analyse-financiere/packages/contracts/judge_v1.py`
- route_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/judge.py`
- application_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py`
- service_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py`
- intelligence_or_context_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/intelligence_service.py`
- invariants_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md`

Current state
- current_contract: stable `ok/data` payload with `daily_brief`, `entry_points`, `copilot_start`, `scope_tickers`, `context_influence`, optional `playbook_context`, and allocation-drift context.
- route_thin_or_fat: medium; the route is not a pure business blob, but it still owns cache, singleflight, namespace target rewriting, and some payload shaping.
- application_logic_present: yes; `apps/api/src/domains/copilot/application/copilot_service.py::build_context_payload` centralizes fallback context, saved-portfolio resolution, regime/playbook enrichment, brief loading, and starter entry-point composition.
- service_layer_present: partial; a reusable application service exists, but there is no Judge-style dedicated endpoint facade equivalent to `judge_endpoint_service.py`.
- metadata_present: partial; payload fragments expose `source`, `generated_at`, `freshness`, and warnings, but there is no shared typed metadata contract for the endpoint family.
- never_empty_present: yes; fallback tests confirm the route keeps a usable brief and entry points when context resolution fails.
- fallback_present: yes; exceptions in the context service degrade to brief + starter payload instead of a 500.
- tests_present: yes; route contract, alias, and fallback tests exist under `apps/api/src/domains/copilot/tests/`.

Gap vs Judge
- contract_gap: no shared typed contract in `packages/contracts/*` and no explicit stable response model comparable to `judge_v1.py`.
- route_gap: cache, alias rewriting, and endpoint-specific response shaping still live in the route layer.
- application_gap: business assembly exists, but endpoint-level normalization is not isolated into a typed builder/facade pair.
- service_gap: missing Judge-style endpoint service that owns final metadata normalization, namespace alias policy, and contract guarantees.
- metadata_gap: metadata is present but not standardized enough across `/copilot/context`, `/copilot/start`, and `/personal-finance/*`.
- never_empty_gap: degraded mode works, but explicit `fallback_used` / standardized warnings could be clearer.
- fallback_gap: provenance and freshness of fallback mode are visible only through mixed fragment fields, not a canonical endpoint-level contract.
- testing_gap: route tests are good, but explicit shared-contract and metadata-parity tests versus the Judge standard are missing.

Target architecture
- target_contract: introduce a shared typed contract for the copilot starter/context family under `packages/contracts/*`, preserving the current public shape and adding explicit metadata/fallback semantics.
- target_route_design: keep the FastAPI route focused on input parsing, cache/singleflight, and delegation only.
- target_application_design: keep `build_context_payload` as the business assembler for brief, portfolio fallback, playbook, and entry points.
- target_service_design: add a small Judge-style endpoint facade that normalizes metadata, namespace alias rewriting, and never-empty guarantees for `/copilot/context` and `/copilot/start`.
- target_metadata: consistent `generated_at`, `freshness/last_update`, `source`, `warnings`, `filters_applied`, `stats`, and explicit degraded/fallback markers at endpoint level.
- target_fallback_model: preserve current never-empty fallback, but surface a canonical endpoint-level degraded marker and provenance instead of relying on mixed nested fields.
- target_test_matrix: route contract test, shared-contract serialization test, fallback/degraded metadata test, namespace alias test, and cache/singleflight orchestration test.

Implementation plan
- files_or_modules_to_create: none now; the next justified addition would be a minimal endpoint-service/contract module pair only after runtime recovery.
- files_or_modules_to_modify: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_domain_router.py`, `apps/api/src/domains/copilot/tests/test_copilot_context_route_fallback.py`, and a shared contracts location under `packages/contracts/*` if the runtime blocker is cleared.
- files_or_modules_not_to_touch: `apps/web/src/platform/*`, frontend theme/shell assets, Plane/backlog docs, and compatibility projections under `logs-codex-runs/orchestrator-state/*`.
- compatibility_notes: keep `/api/copilot/context`, `/api/copilot/start`, `/api/personal-finance/start`, and `/api/personal-finance/ask` stable; only additive metadata is acceptable.
- implementation_order: 1. recover VM runtime and prove BATCH-85, 2. if the endpoint still needs hardening, extract a minimal endpoint-service/typed-contract layer, 3. add contract/metadata tests, 4. re-run VM proof.
- risks: doing architecture cleanup before VM recovery risks optimizing a non-blocking code path while the real blocker is runtime execution health.
- non_goals: no new route family, no frontend redesign, no backlog mutation, no broad copilot refactor outside the active endpoint slice.

Decision
- patch_now: no
- if_no_reason: runtime degradation on the VM is the primary blocker; an architecture patch here would improve structure but would not restore delivery without canonical runtime recovery and proof.
- next_owner: admin
- next_action: recover VM runtime first, then resume BATCH-85 proof and only apply the `/api/copilot/context` Judge-parity cleanup if the endpoint remains the limiting factor.

## 2026-04-15T04:37:41Z role-prompt-engineer

Continuity
- previous_target_role: planner
- previous_prompt_issue: shared orchestration prompt repeated planner autonomy rules and could push new batch creation before collect/repair/ack on canonical downstream active work
- changed_since_last_run: planner guardian is still red on `missing_planner_artifact` plus proof-quality drift, dynamic prompt patches now inject canonical-active-task and proof instructions, and the base `ROLE=planner` prompt was still oversized at 7186 chars despite those runtime overlays

Target
- role: planner
- prompt_source: /Users/venom/Documents/analyse-financiere/platform/automation/cron_tmux_role_runner.sh
- why_this_prompt_now: runtime signals still show planner churn risk (`PLANNER_RUNTIME_ACTIONS_FAILED`, proof gaps, canonical active dev task), and the main planner prompt was duplicating rules already injected by `SYSTEM_PROMPT`, `ORCHESTRATION_SHARED_PROMPT`, guardian feedback, and dynamic prompt patches

Prompt audit
- useful_rules: strict decision order; planner-owned completion rule for `PLAN|ANALYSIS|ARCH|GOV_REVIEW`; explicit canonical tool list (`planner_runtime_actions.py`, `planner_subagent_manager.py`); non-passive fallback `NEXT=create_or_claim_now`; batch creation constraints
- redundant_rules: planning/runtime truth reminders, planner-only scheduler reminders, frontend-theme protection, evidence/output contract details, proof field formats, novelty/autonomy language already repeated in shared/system prompt layers
- contradictory_rules: no hard contradiction found, but repeated autonomy plus batch-creation language competed with newer guardian/patch instructions that say follow canonical active downstream work first
- too_long_or_noisy_sections: oversized planner block mixed mission, doctrine, product guardrails, evidence schema, output schema, novelty policy, and batch-creation mechanics in one layer
- missing_tool_guidance: none at the prompt-source level for the chosen patch; canonical tools were already present but buried inside repeated doctrine
- likely_output_failures_caused_by_prompt: `planner_quality_autofill_missing`; `planner_evidence_incomplete_soft`; redispatch churn toward fresh ANALYSIS or batch creation while a canonical downstream task is already active; `ready_but_no_delta`; `ready_but_none_task_update`

Optimization
- keep: ordered tick policy; planner-owned completion rule; single-subagent dispatch routing; batch creation as fallback only; critical proof rule for planner-owned closes
- simplify: shorten tool list to command families; compress decision tree wording; remove repeated doctrine already enforced higher in the composed prompt
- remove: repeated planning/runtime truth exposition, repeated product/theme reminders, repeated output-contract reminders, repeated evidence formatting details already covered in `SYSTEM_PROMPT`
- move_out_of_prompt: no extraction now; keep scope local to the planner block only
- tool_usage_improvements: clearer visibility that planner should `collect` before `run`, `sync-priority` before fallback batch creation, and treat prompt/runtime/spec fixes as direct planner work
- expected_runtime_impact: direct reduction of prompt noise and clearer planner action selection under canonical-active-task pressure; should reduce useless redispatch/new-batch impulses more than it changes raw capability

Patch proposal
- patch_type: shorten
- create_now: yes
- target_file: /Users/venom/Documents/analyse-financiere/platform/automation/cron_tmux_role_runner.sh
- exact_goal: cut the `ROLE=planner` prompt to action-order, canonical tools, fallback batch creation, and planner-close proof rules only
- expected_gain: less prompt-layer conflict, better salience for collect/repair/claim actions, and lower odds of planner drifting into duplicate analysis or batch creation
- risk: low; some doctrinal reminders now live only in shared/system layers, so rollback is needed only if planner starts forgetting truths that those shared layers no longer cover in practice

Measurement
- signals_to_watch: `planner_quality_autofill_missing`; `planner_evidence_incomplete_soft`; `PLANNER_RUNTIME_ACTIONS_FAILED`; count of planner redispatches into fresh ANALYSIS or batch creation while `canonical.active_task_role != planner`; `none_no_signal` frequency on planner ticks
- success_criteria: fewer planner proof-quality issues over the next ticks, no new premature ANALYSIS or batch recreation while `BATCH-85-DEV-01` stays canonical active, and planner outputs that claim/collect/complete instead of restating doctrine
- rollback_condition: planner starts regressing on canonical truth usage or misses planner-owned close proof fields after the prompt reduction

Decision
- next_owner: planner
- next_action: observe the next planner ticks against guardian issues and keep the patch only if collect/repair/claim behavior becomes more direct than create or reopen churn

## 2026-04-15T04:39:36Z endpoint-architecture-steward

Target endpoint
- endpoint: GET /api/copilot/start
- why_this_endpoint: surface d\entrée produit principale après judge
## ${TS} endpoint-architecture-steward

Target endpoint
- endpoint: GET /api/copilot/start
- why_this_endpoint: surface d\entrée produit principale après judge
## 2026-04-15T04:42:36Z vision-batch-architect

Continuity
- previous_verdict: no new batch; BATCH-85 should remain the sole priority until VM proof exists
- previous_top_priority: finish the active brief/action/memo hardening slice and validate it on the VM
- previous_next_delivery: close the BATCH-85 delivery chain instead of opening parallel backlog
- changed_since_last_run: synced queue/workboard still show BATCH-85 as the only active batch, proofs now include BATCH-85 ANALYSIS/ARCH completion plus DEV-01 delivery proof, and local code changes remain concentrated on the same copilot/portfolio/judge/monitor hardening slice

Reality check
- vision_alignment: mixed
- priority_clarity: clear
- active_batch_usefulness: strong
- delivered_value_now: moderate

Top priorities
1. Finish BATCH-85 on the existing brief/action/memo slice and get canonical VM proof for `/api/personal-finance/start`, `/api/copilot/context`, and `/api/status`.
2. Keep the backend-first hardening on `apps/api/src/domains/copilot/*`, `apps/api/src/domains/market_data/*`, and `apps/monitor/*` coherent so the brief, top action context, and memo path stay reliable without extra plumbing.
3. After BATCH-85 proof only, converge `GET /api/copilot/start` toward Judge-parity with a shared contract and thinner route if the gap still blocks product reliability.

Rejected batch ideas
- New batch for `/api/copilot/start` Judge-parity now: rejected as too dependent on BATCH-85 because the active lot already modifies the same route, service, portfolio fallback, and monitor surfaces.
- New batch for conversation history/follow-up UX: rejected as already implicitly delivered per `docs/operations/orchestrator/proofs/BATCH-85/BATCH-85-DEV-01/delivery-proof.json`.
- New runtime/planner cleanup batch: rejected as too orchestration-heavy for this role and not a better product priority than finishing the active user-visible slice.

Selected batch
- title: BATCH-85 - Fiabiliser le slice brief/action/memo a faible cout
- why_now: it is already the active batch, it targets the primary product entry path, and opening new backlog now would only fragment delivery before VM validation exists
- user_visible_delta: more reliable brief-of-day entry, clearer ask/open starters, steadier portfolio-aware context, and fewer nominal-path failures on the existing personal-finance flow
- novelty_target: harden the current backend-first slice so the existing product entry path becomes dependable without redesign or new orchestration surfaces
- independence_from_active_batch: no
- create_now: no
- batch_class: hardening

Architecture fit
- aligned_with_backend_first: yes
- preserves_frontend_theme: yes
- adds_new_custom_plumbing: no
- canonical_paths_respected: yes
- comments: the useful work stays in `apps/api/src/domains/copilot/*`, `apps/api/src/domains/market_data/*`, and `apps/monitor/*`; no backlog JSON, runtime projection, or frontend shell invention is justified now

Implementation architecture
- product slice: personal finance copilot entry flow from brief-of-day to ask/open to memo, plus the supporting portfolio/watchlist context and monitor health visibility
- current reality: `GET /api/copilot/start` and `/api/personal-finance/start` already exist and return starter payloads; local code changes are actively hardening context fallback, saved-portfolio defaulting, Judge reuse, and monitor status, while synced runtime projections show BATCH-85 as the only active batch
- backend changes: continue hardening `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/judge/api/judge.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, and portfolio services so the starter and memo flows stay never-empty, low-cost, and provenance-aware
- frontend changes: no structural redesign; only consume existing starter payloads and aliases already present in `apps/web/src/domains/forecasts/pages/app.js` and `personal-finance-start.html` if backend proof exposes a real rendering gap
- monitor/observability changes: keep `apps/monitor/server.py` and `apps/monitor/services/status_service.py` aligned with runtime truth so `/api/status` reflects the same reliability slice and degraded states instead of stale planner/admin residue
- runtime/orchestration changes: none as a new batch; runtime work remains validation/support for BATCH-85 and must not create new wrappers or backlog projections
- existing code to reuse: `packages/contracts/judge_v1.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/copilot/application/copilot_service.py::build_context_payload`, namespace alias routes in `apps/api/src/domains/copilot/api/copilot.py`, and existing copilot/monitor tests
- files_or_modules_to_touch: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/api/src/domains/judge/api/judge.py`, `apps/api/src/domains/judge/application/judge_endpoint_service.py`, `apps/api/src/domains/market_data/application/dashboard_ui_service.py`, `apps/api/src/domains/market_data/application/portfolio_performance_service.py`, `apps/api/src/domains/market_data/application/portfolio_service.py`, `apps/monitor/server.py`, `apps/monitor/services/status_service.py`
- files_or_modules_not_to_touch: `apps/web/src/platform/*`, theme/shell assets, `platform/automation/*` as a new product batch surface, Plane/runtime JSON projections, and memory/docs as planning truth substitutes
- api_or_contract_changes: additive only; keep `/api/copilot/start`, `/api/personal-finance/start`, `/api/copilot/context`, and `/api/personal-finance/ask` stable while improving metadata consistency (`source`, `freshness`, `warnings`, `cache`, degraded notes)
- migration_or_compat_notes: preserve personal-finance namespace rewriting and current frontend payload expectations; if a shared starter contract is introduced later, it must wrap the existing shape rather than break it
- proof_requirements: canonical VM proof for `/api/personal-finance/start`, `/api/copilot/context`, and `/api/status`; route/service test proof for cache hit + debug bypass + never-empty fallback; evidence that portfolio defaulting does not force live risk fetch in nominal flow
- acceptance_criteria: active BATCH-85 surfaces return stable starter/context payloads with explicit freshness and source metadata; nominal errors degrade instead of 500ing; monitor status stays non-null and aligned with runtime truth; no new duplicate batch is required
- implementation_order: 1. finish active backend/service hardening in copilot + portfolio + judge, 2. finish monitor/status hardening, 3. run/collect tests locally, 4. validate on the VM, 5. only then decide whether shared-contract extraction is still needed
- risks: local projections can overstate readiness because VM runtime proof is unavailable from this sandbox; route/service cleanup on `copilot/start` can duplicate active BATCH-85 work if started as a separate batch too early
- non_goals: no new backlog stream, no frontend redesign, no new operator/runtime plumbing, no manual edits to queue/workboard/priority projections

Decision
- create_in_plane_now: no
- if_no_reason: current batch should keep priority because it already covers the same product slice and code surfaces, and Plane creation is not justified without an independent user-visible delta
- next_owner: dev
- next_action: finish BATCH-85 and obtain canonical VM proof before reconsidering any new batch

## 2026-04-15T04:42:36Z endpoint-architecture-steward

Target endpoint
- endpoint: GET /api/copilot/start
- why_this_endpoint: it is the main starter endpoint for the brief -> ask/open -> memo journey and it still carries route-owned orchestration that Judge has already factored better
- current_product_role: deliver the brief of the day, starter ask/open actions, and portfolio-aware degraded entry into the personal finance copilot in 2-3 clicks

Judge reference mapping
- contract_reference: `/Users/venom/Documents/analyse-financiere/packages/contracts/judge_v1.py`
- route_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/judge.py`
- application_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py`
- service_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py`
- intelligence_or_context_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/intelligence_service.py`
- invariants_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md`

Current state
- current_contract: implicit but fairly stable `ok/data` response built by `_build_start_response(...)` around `brief_of_day`, `ask`, `open`, `generated_at`, `freshness`, `source`, `warnings`, `stats`, `filters_applied`, optional note, and portfolio/context fragments
- route_thin_or_fat: fat relative to Judge; the route still owns cache lookup/store, singleflight, fallback branching, namespace rewriting, and response assembly
- application_logic_present: yes; `apps/api/src/domains/copilot/application/copilot_service.py::build_context_payload` builds daily brief, entry points, saved-portfolio context, playbook context, regime detection, and `copilot_start`
- service_layer_present: partial; there is a reusable application service, but no Judge-style dedicated endpoint facade comparable to `judge_endpoint_service.py`
- metadata_present: partial; `generated_at`, `freshness`, `source`, `warnings`, `cache`, and `stats` exist, but there is no shared typed contract guaranteeing starter metadata parity
- never_empty_present: yes; the route explicitly falls back to local brief + entry points instead of failing hard
- fallback_present: yes; both service-level context fallback and route-level fallback exist, but provenance is spread across route helpers and service builders
- tests_present: yes; cache/debug tests and service tests exist under `apps/api/src/domains/copilot/tests/`, but not a shared typed contract test

Gap vs Judge
- contract_gap: no canonical shared starter contract in `packages/contracts/*`; frontend and aliases still depend on a route-built shape rather than a typed public model
- route_gap: `apps/api/src/domains/copilot/api/copilot.py:1007-1110` still mixes adapter work with business fallback and payload shaping
- application_gap: application logic exists but starter-specific normalization remains split between the route and `_build_copilot_start_payload`
- service_gap: missing endpoint facade to own final payload normalization, metadata standardization, and alias-safe degraded behavior
- metadata_gap: metadata is present but not standardized enough across `/copilot/start`, `/copilot/context`, and `/personal-finance/start`
- never_empty_gap: degraded mode works, but explicit `fallback_used` or clearer canonical degraded markers are still absent
- fallback_gap: fallback policy is duplicated between route and service instead of being encapsulated in one reusable layer
- testing_gap: no shared contract validation anchored to a typed starter schema and no thin-route regression test that proves route/business separation

Target architecture
- target_contract: introduce a shared typed starter contract under `packages/contracts/*` for `brief_of_day`, `ask`, `open`, `generated_at`, `freshness`, `source`, `warnings`, `filters_applied`, `stats`, `cache`, and explicit degraded metadata
- target_route_design: keep `GET /api/copilot/start` as a thin FastAPI adapter that parses `tickers/namespace/debug`, handles cache/singleflight, delegates once, and returns `{\"ok\": true, \"data\": ...}`
- target_application_design: keep `build_context_payload(...)` as the broad business assembler for scope, saved portfolio, regime, and brief creation without route-only namespace concerns
- target_service_design: add a Judge-style endpoint facade for starter payload construction and degraded policy, either as `apps/api/src/domains/copilot/application/copilot_start_service.py` or a public facade extracted from `copilot_service.py`
- target_metadata: canonical endpoint-level `generated_at`, `freshness`, `source`, `warnings`, `filters_applied`, `stats`, `cache`, and explicit degraded/fallback markers
- target_fallback_model: one service-owned never-empty fallback that preserves the public contract and rewrites namespace targets consistently for `/personal-finance/start`
- target_test_matrix: shared contract serialization test, route orchestration/thinness test, cache hit + debug bypass test, degraded fallback test, and namespace alias parity test

Implementation plan
- files_or_modules_to_create: `packages/contracts/copilot_start_v1.py` and optionally `apps/api/src/domains/copilot/application/copilot_start_service.py` if extraction from `copilot_service.py` remains cleanly scoped
- files_or_modules_to_modify: `apps/api/src/domains/copilot/api/copilot.py`, `apps/api/src/domains/copilot/application/copilot_service.py`, `apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `apps/api/src/domains/copilot/tests/test_copilot_service.py`, and any focused contract test file under `apps/api/src/domains/copilot/tests/`
- files_or_modules_not_to_touch: `apps/web/src/platform/*`, frontend theme/shell assets, `apps/api/runtime/*`, `apps/monitor/*`, and `platform/automation/*` for this endpoint-specific convergence
- compatibility_notes: keep `/api/copilot/start` and `/api/personal-finance/start` stable; only additive metadata evolution is acceptable
- implementation_order: 1. freeze the starter contract, 2. extract a dedicated endpoint facade, 3. slim the route to parse/cache/delegate only, 4. add contract/fallback/cache/alias tests, 5. revalidate on VM
- risks: doing this now would overlap BATCH-85 work already in progress on the same files and could create duplicate partial abstractions before runtime proof exists
- non_goals: no new route family, no frontend redesign, no conversation-history work, no orchestration/runtime refactor disguised as endpoint work

Decision
- patch_now: no
- if_no_reason: the gap is real but not independent; it belongs inside the active BATCH-85 hardening path and should not become a separate patch from this run
- next_owner: dev
- next_action: finish BATCH-85, then extract the starter contract/facade only if `/api/copilot/start` still remains the limiting reliability point after VM proof
## 2026-04-15T04:49:00Z endpoint-architecture-steward

Target endpoint
- endpoint: GET /api/copilot/start
- why_this_endpoint: surface d'entrée produit principale après judge; elle sert le brief du jour et les actions ask/open en 2-3 clics.
- current_product_role: point d'entrée backend-first réutilisé par copilot et personal-finance pour lancer le parcours nominal utilisateur.

Judge reference mapping
- contract_reference: /home/venom/analyse-financiere/packages/contracts/judge_v1.py
- route_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/api/judge.py
- application_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py
- service_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py
- intelligence_or_context_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/intelligence_service.py
- invariants_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md

Current state
- current_contract: contrat public stable de fait avec `ok`, `data`, `generated_at`, `freshness`, `source`, `warnings`, `filters_applied`, `stats`, `cache`, `ask`, `open`, `brief_of_day`, mais il n'existe pas comme contrat partagé canonique.
- route_thin_or_fat: fat; la route gère parsing, cache TTL, singleflight, bypass debug, normalisation de namespace, fallback et assemblage de la réponse.
- application_logic_present: yes; l'agrégation métier vit surtout dans `/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_service.py`.
- service_layer_present: partial; il existe de la logique métier réutilisable mais pas de façade endpoint dédiée équivalente à `judge_endpoint_service.py`.
- metadata_present: yes; les métadonnées utiles sont déjà exposées et exploitables côté frontend.
- never_empty_present: yes; la route préserve un payload utile avec `ask/open` et brief fallback au lieu d'un vide structurel.
- fallback_present: yes; snapshot-first et route fallback existent, mais la responsabilité est partagée entre route et service.
- tests_present: yes; tests de route, cache, alias et fallback existent déjà.

Gap vs Judge
- contract_gap: absence de contrat partagé sous `packages/contracts/*`; le frontend dépend d'une shape implicite garantie seulement par la route et les tests.
- route_gap: la route est trop chargée par rapport au modèle Judge; elle porte encore de la logique de cache/orchestration/fallback qui devrait être encapsulée.
- application_gap: la logique métier n'est pas perdue, mais l'orchestration endpoint est répartie entre la route et le service au lieu d'être stabilisée dans une couche dédiée.
- service_gap: absence d'une façade réutilisable `copilot_endpoint_service` responsable du payload final, de la metadata standard et du degraded mode.
- metadata_gap: bonne base existante, mais pas de standardisation canonique de `fallback_used`, `source`, `freshness` et `warnings` via un builder/service unique.
- never_empty_gap: le comportement never-empty existe mais n'est pas garanti par un contrat typé partagé ni centralisé dans une façade endpoint.
- fallback_gap: fallback explicite mais distribué; il faut une chaîne unique snapshot-first -> degraded payload -> warning/source canonique.
- testing_gap: couverture route correcte, mais pas encore de tests de contrat partagé ni de tests dédiés de façade service équivalents à Judge.

Target architecture
- target_contract: créer `/home/venom/analyse-financiere/packages/contracts/copilot_start_v1.py` avec contrat public typé pour `ok`, `data`, `generated_at`, `freshness`, `source`, `warnings`, `filters_applied`, `stats`, `cache`, `fallback_used`.
- target_route_design: garder `/home/venom/analyse-financiere/apps/api/src/domains/copilot/api/copilot.py` comme adaptateur mince: parsing input, debug bypass simple, appel façade endpoint, enveloppe HTTP.
- target_application_design: conserver `/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_service.py` comme couche d'agrégation métier pour brief, entry points, enrichissement et contexte.
- target_service_design: créer `/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_endpoint_service.py` pour encapsuler cache/singleflight, payload final, fallback canonicalisé, normalisation metadata et compat alias.
- target_metadata: standardiser `generated_at`, `freshness`, `source[]`, `warnings[]`, `filters_applied`, `stats`, `cache`, `fallback_used` avec provenance explicite lisible par le frontend.
- target_fallback_model: une seule chaîne explicite snapshot-first; en cas de source partielle, retour `ok=true` dégradé avec provenance/warnings/fallback_used, sans 500 sur le parcours nominal.
- target_test_matrix: ajouter test de contrat partagé, test de façade endpoint, test orchestration route, test degraded fallback, test metadata standard, test alias parity `/api/personal-finance/start`.

Implementation plan
- files_or_modules_to_create: `/home/venom/analyse-financiere/packages/contracts/copilot_start_v1.py`, `/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_endpoint_service.py`, `/home/venom/analyse-financiere/apps/api/src/domains/copilot/tests/test_copilot_start_endpoint_service.py`.
- files_or_modules_to_modify: `/home/venom/analyse-financiere/apps/api/src/domains/copilot/api/copilot.py`, `/home/venom/analyse-financiere/apps/api/src/domains/copilot/application/copilot_service.py`, `/home/venom/analyse-financiere/apps/api/src/domains/copilot/tests/test_copilot_domain_router.py`, `/home/venom/analyse-financiere/apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`.
- files_or_modules_not_to_touch: `/home/venom/analyse-financiere/apps/api/src/domains/judge/api/intelligence.py`, `/home/venom/analyse-financiere/apps/api/src/domains/judge/api/quality.py`, couches runtime/planner/operator, frontend theme/shell.
- compatibility_notes: préserver strictement les routes publiques `/api/copilot/start` et `/api/personal-finance/start` ainsi que la shape actuelle pendant la migration.
- implementation_order: 1. contrat partagé 2. façade endpoint 3. migration de la route vers la façade 4. alignement des tests 5. nettoyage des helpers route-locaux.
- risks: casser l'alias `personal-finance/start`, perdre des champs implicites existants, introduire une divergence entre cache route et fallback métier si la migration est partielle.
- non_goals: réécriture complète du domaine copilot, redesign frontend, clonage monolithique de Judge, ajout de plomberie runtime.

Decision
- patch_now: no
- if_no_reason: le gain clair est structurel et nécessite un contrat partagé + une façade endpoint dédiée; ce n'est pas un patch local sans risque sur une route déjà en service.
- next_owner: dev
- next_action: implémenter `copilot_start_v1` et `copilot_endpoint_service`, puis migrer `/api/copilot/start` vers une route mince avec metadata/fallback standardisés.
## 2026-04-15T05:05:00Z endpoint-architecture-steward

Target endpoint
- endpoint: GET /api/portfolios/{portfolio_id}/risk-profile
- why_this_endpoint: surface portefeuille critique déjà consommée par le frontend; elle devait rendre sa dégradation explicite au lieu de la laisser implicite dans `source` et `warnings`.
- current_product_role: snapshot de risque actionnable pour portefeuille/watchlist avec poids, métriques, justification et garde-fous utilisables côté dashboard et copilote.

Judge reference mapping
- contract_reference: /home/venom/analyse-financiere/packages/contracts/judge_v1.py
- route_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/api/judge.py
- application_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py
- service_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py
- intelligence_or_context_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/intelligence_service.py
- invariants_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md

Current state
- current_contract: contrat public déjà stable avec `portfolio`, `benchmark`, `weights`, `metrics`, `risk_profile`, `risk_level`, `risk`, `why`, `warnings`, `filters_applied`, `stats`, `confidence`, `generated_at`, `last_update`, `source`, enveloppé par `service_response_with_metadata`.
- route_thin_or_fat: thin; la route délègue déjà à la façade `get_portfolio_risk_profile_payload(...)`.
- application_logic_present: yes; la classification métier et les fallbacks composition/live vivent dans `/home/venom/analyse-financiere/apps/api/src/domains/market_data/application/portfolio_service.py`.
- service_layer_present: yes; `/home/venom/analyse-financiere/apps/api/src/domains/market_data/application/portfolio_endpoint_service.py` joue déjà le rôle de façade endpoint.
- metadata_present: yes; provenance, fraîcheur, filtres et stats existent déjà.
- never_empty_present: yes; fallback service et fallback composition-only évitent le vide structurel.
- fallback_present: yes; fallback service et fallback métriques existent.
- tests_present: yes; `/home/venom/analyse-financiere/apps/api/src/domains/market_data/tests/test_portfolio_risk_profile_contract.py` couvre contrat, orchestration et fallback.

Gap vs Judge
- contract_gap: pas de contrat partagé `packages/contracts/*`; la shape reste locale au domaine market-data.
- route_gap: faible; la route est déjà au bon niveau.
- application_gap: faible; la logique métier est déjà isolée.
- service_gap: faible; la façade existait déjà.
- metadata_gap: la dégradation restait implicite pour `composition_only` et `metrics_unavailable`; le frontend devait l'inférer depuis `source`.
- never_empty_gap: faible; le payload était déjà robuste.
- fallback_gap: fallback présent mais `fallback_used` et `status=degraded` n'étaient pas explicitement normalisés pour tous les chemins non nominaux.
- testing_gap: les tests existants couvrent bien la forme, mais ne forcent pas encore explicitement `fallback_used`.

Target architecture
- target_contract: conserver le contrat local existant; ne pas créer de nouveau fichier tant que la consolidation `market_data` partagée n'est pas nécessaire.
- target_route_design: conserver la route mince actuelle.
- target_application_design: conserver la logique métier dans `portfolio_service.py`.
- target_service_design: enrichir `portfolio_endpoint_service.py` pour déduire et exposer explicitement la dégradation depuis les tags métier existants.
- target_metadata: `fallback_used` explicite + `status=degraded` pour `composition_only`, `metrics_unavailable` et `service_fallback`.
- target_fallback_model: garder le never-empty existant, mais rendre la provenance et le mode de fallback lisibles sans heuristique frontend.
- target_test_matrix: conserver les tests actuels; ajouter plus tard des assertions explicites sur `fallback_used` et `status` si nécessaire.

Implementation plan
- files_or_modules_to_create: none
- files_or_modules_to_modify: `/home/venom/analyse-financiere/apps/api/src/domains/market_data/application/portfolio_endpoint_service.py`
- files_or_modules_not_to_touch: `/home/venom/analyse-financiere/apps/api/src/domains/market_data/api/portfolios.py`, `/home/venom/analyse-financiere/apps/api/src/domains/market_data/application/portfolio_service.py`
- compatibility_notes: contrat public préservé; uniquement ajout de metadata additive sur la dégradation.
- implementation_order: 1. normaliser les tags `source` 2. déduire `fallback_used` 3. propager `status=degraded` depuis la façade endpoint.
- risks: consommateurs downstream non préparés à lire `fallback_used`, même si l'ajout reste backward-compatible.
- non_goals: refonte métriques live, extraction d'un contrat partagé market-data, modification de la route.

Decision
- patch_now: yes
- if_no_reason:
- next_owner: dev
- next_action: valider ensuite côté frontend/monitor que `composition_only` et `metrics_unavailable` s'affichent comme dégradés explicites.
## 2026-04-15T05:14:00Z endpoint-architecture-steward

Target endpoint
- endpoint: GET /api/portfolios/{portfolio_id}/performance
- why_this_endpoint: surface business critique pour juger la valeur d'un portefeuille; il répondait mais sans exposer clairement provenance, filtres, warnings ni fallback.
- current_product_role: métriques synthétiques de performance portefeuille comparées au benchmark pour guider la lecture portfolio/dashboard.

Judge reference mapping
- contract_reference: /home/venom/analyse-financiere/packages/contracts/judge_v1.py
- route_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/api/judge.py
- application_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py
- service_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py
- intelligence_or_context_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/application/intelligence_service.py
- invariants_reference: /home/venom/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md

Current state
- current_contract: modèle typé local `PortfolioPerformance`, mais initialement minimal: métriques de perf sans `filters_applied`, `warnings`, `source` ni `fallback_used`.
- route_thin_or_fat: thin; la route lit le service et sérialise.
- application_logic_present: yes; calcul et fallback vivent déjà dans `portfolio_service.py`.
- service_layer_present: partial; pas de façade endpoint dédiée, mais un service métier existant suffisait pour un patch local.
- metadata_present: partial avant patch; bonne après enrichissement local.
- never_empty_present: yes; le service renvoyait déjà une structure avec `null` au lieu de casser.
- fallback_present: yes; implicite avant patch, explicite après patch.
- tests_present: partial; tests de perf existent dans `test_portfolio_risk_profile_contract.py`, mais la metadata enrichie n'était pas encore l'axe principal.

Gap vs Judge
- contract_gap: pas de contrat partagé canonique; contrat local seulement.
- route_gap: faible; la route n'était pas le problème.
- application_gap: faible; la logique était déjà dans le service.
- service_gap: pas de façade dédiée, mais le plus gros manque était la normalisation de contrat métier.
- metadata_gap: absence de `filters_applied`, `stats`, `warnings`, `source`, `generated_at`, `fallback_used`.
- never_empty_gap: faible; structure vide évitée, mais sans signal de dégradation lisible.
- fallback_gap: le fallback métriques indisponibles n'était pas explicitement exposé.
- testing_gap: les tests existants ne figent pas encore cette metadata enrichie.

Target architecture
- target_contract: garder `PortfolioPerformance` comme contrat typé local enrichi tant qu'aucune façade partagée n'est nécessaire.
- target_route_design: conserver la route mince actuelle.
- target_application_design: enrichir directement `portfolio_service.py` pour exposer un payload métier complet.
- target_service_design: ne pas créer de nouveau module; améliorer le service existant.
- target_metadata: `filters_applied`, `stats`, `warnings`, `generated_at`, `source`, `fallback_used`, `error`.
- target_fallback_model: never-empty avec `fallback_used=metrics_unavailable` et source explicite sur le chemin dégradé.
- target_test_matrix: conserver les tests actuels; compléter plus tard avec assertions de metadata performance si besoin.

Implementation plan
- files_or_modules_to_create: none
- files_or_modules_to_modify: `/home/venom/analyse-financiere/apps/api/src/domains/market_data/application/portfolio_service.py`
- files_or_modules_not_to_touch: `/home/venom/analyse-financiere/apps/api/src/domains/market_data/api/portfolios.py`, `/home/venom/analyse-financiere/apps/api/src/domains/market_data/application/portfolio_endpoint_service.py`
- compatibility_notes: enrichissement additif du payload; pas de rupture d'API publique.
- implementation_order: 1. enrichir `PortfolioPerformance` 2. propager filtres/stats/warnings 3. rendre le fallback métriques explicite.
- risks: des consommateurs peuvent supposer un payload plus petit, même si les champs ajoutés restent backward-compatible.
- non_goals: création d'une façade endpoint performance, redesign du modèle benchmark, modification des routes.

Decision
- patch_now: yes
- if_no_reason:
- next_owner: dev
- next_action: observer ensuite si le frontend exploite effectivement `warnings` et `fallback_used` sur les cartes performance.
## 2026-04-15T04:44:30Z endpoint-architecture-steward

Target endpoint
- endpoint: GET /api/copilot/start
- why_this_endpoint: le commit réel de `BATCH-85-DEV-01` a renforcé le slice brief/action/memo sans résoudre la dette de structure; c’est donc l’endpoint critique à stabiliser avant de répéter le pattern sur d’autres surfaces.
- current_product_role: point d’entrée backend-first pour lancer le brief du jour puis les actions `ask` / `open` en 2-3 clics sur `copilot` et `personal-finance`.

Judge reference mapping
- contract_reference: `/Users/venom/Documents/analyse-financiere/packages/contracts/judge_v1.py`
- route_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/judge.py`
- application_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_pipeline.py`
- service_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/judge_endpoint_service.py`
- intelligence_or_context_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/application/intelligence_service.py`
- invariants_reference: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/INVARIANTS.md`

Current state
- current_contract: contrat public stable de fait avec `ok`, `data`, `generated_at`, `freshness`, `source`, `warnings`, `filters_applied`, `stats`, `cache`, `brief_of_day`, `ask`, `open`, plus contexte additionnel quand disponible, mais toujours sans contrat partagé canonique.
- route_thin_or_fat: fat; `apps/api/src/domains/copilot/api/copilot.py` gère parsing, cache TTL, singleflight, namespace rewriting, fallback, effective scope et assemblage final via `_build_start_response`.
- application_logic_present: yes; l’agrégation métier vit majoritairement dans `apps/api/src/domains/copilot/application/copilot_service.py` et reste réutilisable.
- service_layer_present: partial; il existe une couche applicative, mais pas de façade endpoint dédiée type `judge_endpoint_service.py`.
- metadata_present: yes; métadonnées utiles déjà exposées et lisibles côté frontend, mais sans builder/service canonique unique.
- never_empty_present: yes; la route retombe sur brief + ask/open au lieu de casser le frontend.
- fallback_present: yes; fallback explicite snapshot-first, mais encore partagé entre route et service.
- tests_present: yes; tests de cache, alias, service et fallback existent déjà sur le domaine copilot.

Gap vs Judge
- contract_gap: pas de contrat partagé sous `packages/contracts/*`; la shape publique reste implicite et garantie seulement par la route et les tests.
- route_gap: la route porte encore la logique d’orchestration endpoint (cache, singleflight, rewrite namespace, fallback, payload final), contrairement au modèle Judge.
- application_gap: la logique métier existe, mais le payload final starter n’est pas isolé dans une couche endpoint/application dédiée.
- service_gap: absence d’un `copilot_endpoint_service` réutilisable qui encapsule payload final, degraded mode et metadata standard.
- metadata_gap: bonne base existante, mais `fallback_used`, `source[]`, `freshness` et `warnings[]` ne sont pas normalisés par une seule façade typée.
- never_empty_gap: le comportement est bon mais la garantie dépend encore d’helpers route-locaux, pas d’un contrat/service canonique.
- fallback_gap: la chaîne fallback existe mais reste distribuée; il manque une décision unique snapshot-first -> degraded payload -> warnings/source/fallback_used.
- testing_gap: bonne couverture route, mais pas de test de contrat partagé ni de test dédié de façade endpoint comparable à Judge.

Target architecture
- target_contract: créer `/Users/venom/Documents/analyse-financiere/packages/contracts/copilot_start_v1.py` avec le contrat public canonique pour `brief_of_day`, `ask`, `open`, `generated_at`, `freshness`, `source`, `warnings`, `filters_applied`, `stats`, `cache`, `fallback_used`.
- target_route_design: garder `apps/api/src/domains/copilot/api/copilot.py` comme adaptateur mince: parsing input, debug bypass simple, appel façade, enveloppe `{ok: true, data: ...}`.
- target_application_design: conserver `copilot_service.py` comme couche d’agrégation métier pour brief, contexte, portfolio fallback et entry points.
- target_service_design: créer `apps/api/src/domains/copilot/application/copilot_endpoint_service.py` pour centraliser cache/singleflight, payload final, namespace rewrite, metadata et fallback canoniques.
- target_metadata: standardiser `generated_at`, `freshness`, `source[]`, `warnings[]`, `filters_applied`, `stats`, `cache`, `fallback_used` avec provenance explicite.
- target_fallback_model: une seule chaîne explicite snapshot-first; en cas de source partielle, retour `ok=true` dégradé avec provenance et warnings, sans 500 sur le nominal path.
- target_test_matrix: test de contrat partagé, test de façade endpoint, test orchestration route, test degraded fallback, test metadata standard, test alias parity `/api/personal-finance/start`.

Implementation plan
- files_or_modules_to_create: `/Users/venom/Documents/analyse-financiere/packages/contracts/copilot_start_v1.py`, `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/copilot/application/copilot_endpoint_service.py`, `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/copilot/tests/test_copilot_start_endpoint_service.py`
- files_or_modules_to_modify: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/copilot/api/copilot.py`, `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/copilot/application/copilot_service.py`, `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/copilot/tests/test_copilot_start_route_cache.py`, `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/copilot/tests/test_copilot_service.py`
- files_or_modules_not_to_touch: `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/intelligence.py`, `/Users/venom/Documents/analyse-financiere/apps/api/src/domains/judge/api/quality.py`, couches runtime/planner/operator, frontend theme/shell
- compatibility_notes: préserver strictement `/api/copilot/start` et `/api/personal-finance/start`; évolution additive uniquement du payload public.
- implementation_order: 1. figer le contrat partagé 2. créer la façade endpoint 3. migrer la route vers la façade 4. aligner les tests contrat/fallback/cache/alias 5. supprimer les helpers route qui deviennent redondants
- risks: casser l’alias `personal-finance/start`, perdre des champs implicites existants, ou dupliquer partiellement la logique déjà dans `build_context_payload` si l’extraction n’est pas disciplinée.
- non_goals: pas de refonte large du domaine copilot, pas de redesign frontend, pas de duplication monolithique de Judge, pas de nouvelle plomberie runtime.

Decision
- patch_now: no
- if_no_reason: le prochain gain utile est de livrer puis stabiliser le lot fiabilité déjà codé; la convergence Judge-parity de `/api/copilot/start` reste une amélioration structurelle claire mais non bloquante tant que `BATCH-85-DEV-01` reste en churn runtime.
- next_owner: dev
- next_action: après le ship du lot fiabilité, implémenter `copilot_start_v1` puis `copilot_endpoint_service` pour rendre la route `/api/copilot/start` mince sans casser la compatibilité existante.
- [2026-04-15 00:50:46 EDT] role=planner source=primary_structured status=IN_PROGRESS verdict=GO_WITH_CAUTION delta=PLANNER_DISPATCH_ACTIVE blocker=NONE stream_id=BATCH-85 task_id=BATCH-85-DEV-01 next_action_unique=PLANNER_DISPATCH_ACTIVE_BATCH-85-DEV-01 directive=none/none message=none/none exec_report=none issues=missing_result_payload suggestions=none
