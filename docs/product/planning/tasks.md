---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/product/planning/README.md
  - /home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md
---

# pTasks détaillées orientées exécution par agents codex (OpenClaw)

Historical note:
- This file reflects an older execution decomposition model.
- It remains useful for background task detail only.
- Do not treat it as the current backlog source of truth; use [BACKEND_FIRST_PRODUCT_BACKLOG.md](/home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md).

## Gate Status (source of truth)

- `BATCH-01`: `PASS` (QA signoff already present)
  - artifact: `finance-app/openclaw-gates/batch-01-20260225-000127.md`
  - keys: `QA_SIGNOFF: YES`, `VERDICT: PASS`, `BLOCKER_ID: NONE`
- `BATCH-02`: `PASS` (QA signoff now present)
  - artifact: `finance-app/openclaw-gates/batch-02-20260225-202042.md`
  - keys: `QA_SIGNOFF: YES`, `VERDICT: PASS`, `BLOCKER_ID: NONE`
- If a runtime role output reports `QA_PASS_SIGNATURE_UNVERIFIED`, re-check the artifact above before keeping the blocker.

## Convention de dispatch

- **Rôles (core chain)**: planner, dev, tester, qa
- **Taille cible**: 2-4h / tâche
- **Format sortie obligatoire (contrat)**: STATUS / DELTA / EVIDENCE / RISKS / NEXT / VERDICT / BLOCKER_ID / NEXT_ACTION_UNIQUE
- **EVIDENCE**: suivre `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md` (kv `key=value;...`)

## Architecture d'intégration détaillée (anti-chevauchement, sans nouvelles tâches)

- Cette section n'ajoute aucun nouvel ID. Elle précise uniquement l'ownership architecture des tâches déjà présentes dans ce backlog.

### Sources de vérité techniques

- Entrypoint API principal: `apps/api/src/platform/main.py`
- Routes modulaires: `apps/api/src/domains/{copilot|forecasts|judge|market_data}/api/*.py`
- Frontend runtime: `apps/web/src/domains/{copilot|forecasts|portfolio}/pages/*.html|*.js`
- Données simulées frontend (fallback dégradé): `apps/web/src/domains/forecasts/contracts/mockData.js`
- Gates de livraison: `scripts/run_delivery_gate.sh` + artefacts `finance-app/openclaw-gates/`
- Compat legacy (interdit pour les nouvelles livraisons produit):
  - `apps/api/src/api/main.py` (compat wrapper pour `apps/api/src/platform/main.py`)
  - `apps/api/src/domains/<domaine>/api/` exposé via `apps/api/src/api/routes/__init__.py`
  - `apps/api/src/api/schemas.py` (wrapper vers `apps/api/src/platform/legacy/api/schemas.py`)

**Règle cible:** en priorité, les nouvelles tâches doivent cibler le chemin `apps/api/src/domains/*` et `apps/api/src/platform/*`.

### Zones techniques autorisées (cible actuelle)

- `apps/api/src/platform/main.py` + `apps/api/src/platform/routes/*` : points d’entrée API, router minimal, health, bootstrap
- `apps/api/src/domains/<domaine>/api/*` : endpoints métier par domaine (copilot, forecasts, judge, market_data)
- `apps/api/src/domains/<domaine>/application/*` : logique métier/requêtes métier
- `apps/api/src/domains/<domaine>/contracts/*` : schémas/domain contracts quand nécessaires
- `apps/api/src/domains/<domaine>/tests/*` : tests unitaires/integration domaine
- `apps/api/src/platform/legacy/*` : compat/technique existante, utiliser **strictement en lecture** pour migration
- `apps/web/src/domains/*/{components,pages}` : UI métier
- `apps/web/src/platform/*` : API client, routing, config front runtime
- `platform/*` : config d’exploitation (cron, policies, features, timeouts, fallbacks)

Pour toute tâche dans `docs/product/planning/tasks.md`, la section `Scope IN` et `Fichiers cibles` doit utiliser **au moins** un élément de la zone du domaine concerné.

### Règles globales anti-chevauchement

- Un endpoint fonctionnel = un owner de tâche à la fois.
- Une tâche peut lire hors scope, mais ne modifie que son périmètre explicitement listé.
- Si une modification traverse 2 périmètres, elle doit être split selon les `Dependencies` existantes (pas de fusion opportuniste).
- Toute exception cross-scope doit être signalée dans `EVIDENCE` et validée par `qa` avant merge batch.

### Invariants forecast-first (valeur produit non-negociable)

- Valeur differenciante MVP: les APIs doivent produire des previsions data-driven actionnables, pas seulement de l'affichage de donnees brutes.
- Contrat forecast minimal attendu sur les surfaces decision: `action|direction`, `confidence`, `horizon`, `why`, `risk_flag`, `generated_at`, `freshness_status`.
- Toute tache UI liee au flux principal doit afficher explicitement la prevision issue de l'API reelle (etat nominal + degraded), sans chemin mock en nominal.
- Toute tache QA/gate doit bloquer (`BLOCKED`) si la preuve "prevision backend -> affichage UI -> evidence gate" est absente.
- Toute preuve UI valide doit inclure vérification navigateur réelle (web/browser ou Playwright/Cypress) + au moins un snapshot écran par cas critique (nominal et degraded) référencé dans l'EVIDENCE.
- Référence navigateur officielle: https://docs.openclaw.ai/tools/browser
- Les taches non-fonctionnelles (ops/securite/cout) doivent expliciter leur impact direct sur la fiabilite, latence ou disponibilite du pipeline de prevision.

### Matrice de seuils d'acceptation (definie par l'architecture)

- Regle d'heritage: si une tache ne definit pas de seuil local chiffre, elle applique le profil ci-dessous selon son ID.
- Regle de gate: tout seuil `mandatory` non atteint => `VERDICT: BLOCKED`.
- Mapping de profils:
  - `T-A*` -> `CORE-API-CONTRACT`
  - `T-B*` -> `UI-RUNTIME`
  - `T-C*` -> `DELIVERY-GATE`
  - `TV1-FRESH-*` -> `FRESHNESS`
  - `TV2-SIGNAL-*` -> `FORECAST-SIGNAL`
  - `TV3-JUDGE-*` -> `JUDGE`
  - `TV4-UI-*` -> `DECISION-UI`
  - `TV5-ASK-*` -> `ASK`
  - `TV6-PORT-*` -> `PORTFOLIO`
  - `TV7-MACRO-*` -> `MACRO`
  - `TV8-COST-*` -> `COST-GOV`
  - `TV9-LOOP-*` -> `LEARNING-LOOP`
  - `TV10-DATA-*` -> `INGESTION`
  - `TV11-UX-*` -> `UX-FLOW`
  - `TV12-ALRT-*` -> `ALERTING`
  - `TV13-OPS-*` -> `RELIABILITY-OPS`
  - `TV14-SHIP-*` -> `RELEASE-GATE`
  - `TV-ADV-01*` -> `UI-RUNTIME`
  - `TV-ADV-02*` -> `JUDGE`
  - `TV-ADV-03*` -> `DECISION-UI`
  - `TV-ADV-04*` -> `FRESHNESS`
  - `TV-ADV-05*` -> `COPILOT-HISTORY`
  - `TV-ADV-06*` -> `KPI-CONTRACT`
  - `TV-ADV-07*` -> `DECISION-BRIEF`
  - `TV-ADV-08*` -> `TEST-COVERAGE`
  - `TV-ADV-09*` -> `RELIABILITY-OPS`
  - `TV-ADV-10*` -> `RELEASE-GATE`
  - `TV-QA-01` -> `RELEASE-GATE`
  - `TV15-ML-01..05` -> `ML-FORECAST`
  - `TV15-ML-06` -> `RELEASE-GATE`
  - `TV16-FF-01..02` -> `CORE-API-CONTRACT`
  - `TV16-FF-03` -> `DECISION-BRIEF`
  - `TV16-FF-04` -> `DECISION-UI`
  - `TV16-FF-05` -> `TEST-COVERAGE`
  - `TV16-FF-06` -> `RELEASE-GATE`
- Profils et seuils:
  - `CORE-API-CONTRACT`:
    - `contract_keys_presence` mandatory `= 100%`
    - `schema_validation_pass_rate` mandatory `= 100%`
    - `p95_latency_local` target `<= 1200ms`
  - `UI-RUNTIME`:
    - `mock_path_usage_nominal` mandatory `= 0%`
    - `widget_render_success_rate` mandatory `>= 99%`
    - `ui_error_blocking_rate` mandatory `= 0%`
    - `ui_browser_smoke_pass_rate` mandatory `= 100%`
    - `ui_snapshot_artifacts` mandatory `>= 1`
  - `DELIVERY-GATE`:
    - `evidence_fields_completeness` mandatory `= 100%`
    - `threshold_checks_executed` mandatory `= 100%`
    - `false_pass_rate` mandatory `= 0%`
  - `FRESHNESS`:
    - `freshness_sla_cycles_le_10m` mandatory `>= 90%`
    - `freshness_fields_presence` mandatory `= 100%`
    - `stale_detection_delay` target `<= 120s`
  - `FORECAST-SIGNAL`:
    - `forecast_coverage_mvp` mandatory `>= 90%`
    - `signal_schema_valid_rate` mandatory `= 100%`
    - `why_non_empty_rate` mandatory `>= 90%`
    - `confidence_present_rate` mandatory `>= 95%`
  - `ML-FORECAST`:
    - `dataset_schema_valid_rate` mandatory `= 100%`
    - `training_reproducibility_pass_rate` mandatory `= 100%`
    - `data_leakage_checks_pass_rate` mandatory `= 100%`
    - `model_artifact_traceability` mandatory `= 100%`
    - `walk_forward_direction_hit_rate` target `>= 52%`
    - `confidence_calibration_error` target `<= 0.20`
  - `JUDGE`:
    - `providers_consulted_nominal` mandatory `>= 3`
    - `providers_consulted_degraded` mandatory `>= 1`
    - `judge_contract_valid_rate` mandatory `= 100%`
    - `fallback_success_rate` mandatory `>= 95%`
    - `p95_latency` target `<= 12s`
  - `DECISION-UI`:
    - `clicks_to_decision` mandatory `<= 3`
    - `forecast_card_visible_rate` mandatory `= 100%`
    - `degraded_badge_visibility` mandatory `= 100%`
    - `blocking_js_error_rate` mandatory `= 0%`
    - `decision_ui_browser_smoke_rate` mandatory `= 100%`
    - `decision_ui_snapshot_artifacts` mandatory `>= 1`
  - `ASK`:
    - `ask_contract_valid_rate` mandatory `= 100%`
    - `grounded_sources_ge_2_rate` mandatory `>= 90%`
    - `fallback_response_rate` mandatory `>= 95%`
    - `p95_latency` target `<= 15s`
  - `PORTFOLIO`:
    - `profile_save_load_success` mandatory `>= 99%`
    - `portfolio_rerank_coverage` mandatory `>= 95%`
    - `deterministic_output_on_fixture` target `>= 99%`
  - `MACRO`:
    - `macro_event_mapping_coverage` mandatory `>= 90%`
    - `macro_schema_valid_rate` mandatory `= 100%`
    - `macro_ui_strip_render_rate` target `>= 99%`
  - `COST-GOV`:
    - `free_provider_usage_rate` mandatory `>= 80%`
    - `graceful_timeout_fallback_rate` mandatory `>= 95%`
    - `hard_timeout_failure_rate` mandatory `<= 5%`
  - `LEARNING-LOOP`:
    - `journal_write_success_rate` mandatory `>= 99%`
    - `decision_capture_coverage` mandatory `>= 95%`
    - `outcome_link_rate` target `>= 90%`
  - `INGESTION`:
    - `scheduled_run_success_rate` mandatory `>= 95%`
    - `normalization_success_rate_core_feeds` mandatory `= 100%`
    - `ingestion_health_endpoint_valid_rate` target `>= 99%`
  - `UX-FLOW`:
    - `daily_flow_clicks` mandatory `<= 3`
    - `median_time_to_decision` target `<= 90s`
    - `settings_persistence_success` mandatory `>= 99%`
  - `ALERTING`:
    - `alert_dedup_rate` mandatory `>= 95%`
    - `in_app_delivery_latency` target `<= 60s`
    - `invalid_alert_payload_rate` mandatory `= 0%`
  - `RELIABILITY-OPS`:
    - `structured_log_coverage` mandatory `>= 95%`
    - `backup_restore_drill_success` mandatory `= 100%`
    - `critical_recovery_script_pass_rate` mandatory `= 100%`
  - `RELEASE-GATE`:
    - `all_mandatory_profiles_passed` mandatory `= 100%`
    - `critical_blockers_open` mandatory `= 0`
    - `rollback_drill_success` mandatory `= 100%`
  - `COPILOT-HISTORY`:
    - `history_persistence_success` mandatory `>= 99%`
    - `history_contract_valid_rate` mandatory `= 100%`
    - `mock_history_usage_nominal` mandatory `= 0%`
  - `KPI-CONTRACT`:
    - `single_kpi_source_of_truth` mandatory `= 1`
    - `kpi_contract_keys_presence` mandatory `= 100%`
    - `p95_latency_local` target `<= 1000ms`
  - `DECISION-BRIEF`:
    - `brief_completeness_rate` mandatory `>= 95%`
    - `brief_ui_consumption_success` mandatory `>= 99%`
    - `p95_latency_local` target `<= 2000ms`
  - `TEST-COVERAGE`:
    - `decision_endpoint_coverage` mandatory `>= 90%`
    - `contract_assertion_coverage` mandatory `= 100%`
    - `e2e_browser_snapshot_count` mandatory `>= 1`
    - `flaky_test_rate` mandatory `= 0%`

### Mode co-édition multi-agents (fichiers modifiés en parallèle)

- `docs/product/planning/tasks.md` est le board commun unique pour les tâches (pas de définition de tâches dans les autres docs).
- Avant édition:
  - publier l’intention via pré-annonce (`scripts/preannounce_intent.sh preannounce ...`),
  - claimer la tâche via le workboard (`scripts/parallel_workstream.py claim --role <role> --change-plan <plan> --architecture-checks <checks>`),
  - relire la section ciblée juste avant patch (`sed -n`/`rg`) pour éviter d'éditer une version périmée.
- Pendant édition:
  - patch minimal, limité à la section de la tâche claimée,
  - interdiction de refactor transverse si non requis par la tâche.
- Après édition:
  - relire le diff local (`git diff -- docs/product/planning/tasks.md`) et vérifier qu'aucune section d'une autre tâche n'a été modifiée,
  - si collision détectée sur la même section, ne pas écraser: merger explicitement les deux deltas et noter la résolution dans `EVIDENCE`.
- Règle de synchronisation:
  - docs Scrum (`sprint-next.md`, `product-backlog.md`) = vues de référence uniquement,
  - toute nouvelle granularité de tâche/ordre d'exécution doit d'abord être écrite dans `docs/product/planning/tasks.md`, puis seulement référencée ailleurs.

### Prompts de rôle (obligatoires pour la migration)

Tous les rôles doivent utiliser un `change-plan` explicite de 5+ étapes et un `architecture-checks` complet. Exemple compact (à adapter aux chemins/IDs réels):

- **planner**: `python3 scripts/parallel_workstream.py claim --role planner --change-plan "1) lire queue+workboard+workstate; 2) identifier le blocage prioritaire; 3) définir chaîne d'exécution; 4) fixer preuve attendue; 5) sécuriser rollback; 6) préparer next action unique" --architecture-checks "queue_workboard_sync,scope_boundaries,handoff_rules,reuse_gate,monitoring_readiness"`
- **dev (lane unique)**: `python3 scripts/parallel_workstream.py claim --role dev --change-plan "1) relire task IN/OUT; 2) vérifier réutilisation existant (rg); 3) patch minimal sur fichier cible; 4) test ciblé; 5) valider contrat/runtime; 6) préparer complete/handoff" --architecture-checks "domain_boundary,contract_stability,reuse_first,no_sys_path_bridge,artifact_traceability"`
- **admin**: `python3 scripts/parallel_workstream.py claim --role admin --change-plan "1) vérifier monitor/health; 2) confirmer cohérence queue/workboard; 3) valider preuves dev; 4) appliquer correction orchestration minimale; 5) revalider stabilité; 6) préparer gouvernance next step" --architecture-checks "runtime_health,cron_coverage,contract_guard,proof_integrity,rollback_status"`
- **qa (si lane active)**: `python3 scripts/parallel_workstream.py claim --role qa --change-plan "1) lire lots et dépendances; 2) valider DELTA+EVIDENCE; 3) confirmer gates; 4) vérifier monitoring; 5) décider PASS/BLOCKED; 6) publier next action unique" --architecture-checks "delivery_gate,mandatory_evidence,blockers_explicit,traceability,rollback_status"`

Règle lane active: pour les tâches non clôturées, utiliser uniquement des IDs `PLAN`, `DEV-01/02/03`, `ADMIN-01`, `GOV-REVIEW` (pas de nouveaux labels actifs backend/frontend/data).
Pour les rôles additionnels historiques (`architect`, `infra_engineer`, `analyst`, `data_analyst`, `integrator`, `po`, `scrum_master`), utiliser le modèle de `docs/ops/AGENT_ROLE_INTEGRATION_MODEL.md` uniquement si ces lanes sont réactivées explicitement.

### Monitoring post-lancement (obligatoire)

Après chaque cycle d’action du lot (ou au redémarrage de plusieurs rôles), le rôle exécute:

1. `python3 scripts/parallel_workstream.py status`
2. `python3 scripts/parallel_workstream.py sync-priority --include-pass`
3. `bash scripts/tmux_live_watchdog.sh status`
4. `python3 scripts/parallel_workstream.py validate`

Sans preuve de ces 4 points dans la `EVIDENCE`, le lot est considéré `BLOCKED`.

### Ownership architecture (tâches T-A / T-B / T-C existantes)

- `T-A1.1`
  - Owned: contrat `/api/health` uniquement.
  - Not owned: cache/freshness SLA, logique signal, UI.
- `T-A2.1` et `T-A2.2`
  - Owned: contrat `/api/stocks/prices` (mono puis multi + tests).
  - Not owned: scoring signal, widgets frontend.
- `T-A3.1` et `T-A3.2`
  - Owned: contrat `/api/news/feed` + tests dédiés.
  - Not owned: ranking avancé, orchestration UI.
- `T-A4.1`
  - Owned: unicité du chemin `/api/forecasts` (routing et contrat).
  - Not owned: moteur forecast/scoring.
- `T-A5.1`
  - Owned: robustesse `/api/copilot/ask` (fallback/erreurs).
  - Not owned: persistance historique (`/api/copilot/history`).
- `T-B1.1`, `T-B1.2`, `T-B2.1`
  - Owned: consommation frontend des endpoints MVP + transparence fallback.
  - Not owned: changement de contrat backend.
- `T-C1.1` et `T-C1.2`
  - Owned: scripts gate/runbook/orchestration.
  - Not owned: features endpoint/UI.

### Ownership architecture (Sprint W10 - tâches TV* existantes)

- `TV1-FRESH-01`
  - Owned: champs de fraîcheur (`updated_at`, `age_seconds`, `freshness_status`) sur `/api/stocks/prices`, `/api/news/feed`, `/api/forecasts`.
  - Not owned: TTL/cache policy détaillée, SLA scripts.
- `TV1-FRESH-02`
  - Owned: TTL/cache guardrails + `freshness_status=stale`.
  - Not owned: contrat signal, parcours UI.
- `TV1-FRESH-03`
  - Owned: mesure SLA et verdict script/gate.
  - Not owned: refactor endpoint métier.
- `TV2-SIGNAL-01`
  - Owned: schéma signal (`direction/confidence/action/horizon/why/risk_flag/updated_at`).
  - Not owned: extension univers complet, badges UI.
- `TV2-SIGNAL-02`
  - Owned: coverage signaux noyau (`SPY,QQQ,GLD,SLV,NVDA,TSLA`).
  - Not owned: schéma signal v1.
- `TV2-SIGNAL-03`
  - Owned: extension univers MVP + métrique couverture.
  - Not owned: adaptation UX/clickflow.
- `TV4-UI-01`
  - Owned: adapter API frontend unique pour cartes décision.
  - Not owned: logique backend signal/freshness.
- `TV4-UI-02`
  - Owned: flux 2-3 clics (navigation/assemblage UI).
  - Not owned: ajout de nouveaux contrats API.
- `TV4-UI-03`
  - Owned: badges freshness/degraded.
  - Not owned: mécanique backend SLA.
- `TV-QA-01`
  - Owned: gate E2E sprint et verdict final.
  - Not owned: développement fonctionnel endpoint/UI.

### Ownership architecture (Advance Pack - tâches TV-ADV* existantes)

- `TV-ADV-01`
  - Owned: suppression du chemin runtime mock-driven, bridge API frontend.
  - Not owned: widget Judge détaillé (TV-ADV-02), refresh orchestration (TV-ADV-03).
- `TV-ADV-02`
  - Owned: wiring widget Judge (`/api/llm/judge/run`, `/api/llm/providers/working`).
  - Not owned: refresh global UI.
- `TV-ADV-03`
  - Owned: `refreshData()` réel + synchro timestamps/states UI.
  - Not owned: calcul backend `/api/freshness`.
- `TV-ADV-04`
  - Owned: calcul réel `/api/freshness`.
  - Not owned: gate UI/clickflow.
- `TV-ADV-05`
  - Owned: persistance `/api/copilot/history` (fin mock `mock_conv_*`).
  - Not owned: endpoint agrégateur décision.
- `TV-ADV-06`
  - Owned: consolidation unique `/api/dashboard/kpis` (suppression divergence `main.py` vs `routes/dashboard.py`).
  - Not owned: autres routes dashboard non KPI.
- `TV-ADV-07`
  - Owned: endpoint agrégateur décision (`/api/decision/brief` ou équivalent validé).
  - Not owned: implémentation widget frontend complète.
- `TV-ADV-08`
  - Owned: extension couverture tests API décision.
  - Not owned: refactor métier endpoints.
- `TV-ADV-09`
  - Owned: dette de dépréciation (`@app.on_event`, `datetime.utcnow`, Pydantic v1).
  - Not owned: nouvelles features produit.
- `TV-ADV-10`
  - Owned: durcissement gate livraison (freshness/coverage/2-3 clics obligatoires).
  - Not owned: changements de contenu métier endpoints.

### Verrous de zones sensibles (pour éviter recouvrement)

- `/api/freshness` est réservé à `TV-ADV-04` (consommation seulement pour les autres).
- `/api/dashboard/kpis` est réservé à `TV-ADV-06` pendant consolidation.
- `/api/copilot/history` est réservé à `TV-ADV-05` pendant sortie du mode mock.
- `refreshData()` dans `app.js` est réservé à `TV-ADV-03`.
- `scripts/run_delivery_gate.sh` est réservé à `TV-QA-01` puis `TV-ADV-10`.

### Handoffs obligatoires entre tâches existantes

- `TV1-FRESH-01` -> `TV1-FRESH-02` -> `TV1-FRESH-03`
- `TV2-SIGNAL-01` -> `TV2-SIGNAL-02` -> `TV2-SIGNAL-03`
- `TV4-UI-01` -> `TV4-UI-02` -> `TV4-UI-03`
- `TV-ADV-01` -> `TV-ADV-02` et `TV-ADV-03`
- `TV-ADV-04`, `TV-ADV-05`, `TV-ADV-06`, `TV-ADV-07` -> `TV-ADV-08` -> `TV-ADV-10`
- `TV-ADV-06` -> `TV16-FF-01` -> `TV16-FF-03` -> `TV16-FF-04` -> `TV16-FF-05` -> `TV16-FF-06`
- `TV15-ML-04` -> `TV16-FF-01` -> `TV16-FF-02` (chemin nominal `source=model` obligatoire)
- `TV15-ML-06` -> `TV15-ML-07` -> `TV16-FF-01`
- `TV10-DATA-06` -> `TV10-DATA-07` -> `TV16-FF-09` -> `TV16-FF-10`
- `TV13-OPS-06` -> `TV13-OPS-07` -> `TV13-OPS-08` -> `TV13-OPS-09` -> `TV14-SHIP-07`

## Modèle de référence: Judge API (à réutiliser pour les autres endpoints)

- **Implémentation canonique**: `apps/api/src/domains/judge/api/judge.py` (GET `/api/judge`).
- **Pourquoi c'est le modèle**: l'endpoint montre le pattern complet "production-ready" (normalisation input, cache TTL, debug bypass, validation Pydantic, parsing JSON strict, multi-provider fallback, contrat typé pour le frontend).
- **Dépendances à réutiliser (backend)**:
  - Response envelope: `apps/api/src/platform/legacy/core/response.py` (`ok/err`) ou enveloppe `{"ok":true,"data":...}` équivalente.
  - Normalisation tickers: `apps/api/src/platform/legacy/core/ticker_normalization.py` (`normalize_ticker`, `normalize_tickers`).
  - Pipeline/validation: `apps/api/src/domains/judge/application/judge_pipeline.py` (`build_payload`, `parse_llm_answer`, `validate_llm_response`).
  - Canonicalisation typée: `apps/api/src/domains/judge/application/judge_builder.py` + `apps/api/src/schemas/judge.py`.
  - Clients LLM fallback: `apps/api/src/domains/judge/application/g4f_client.py`, `apps/api/src/services/codestral_client.py`, `apps/api/src/services/groq_client.py`.
  - Working models list (g4f): `apps/api/src/platform/legacy/agents/g4f_model_watcher.py` + endpoint debug `GET /api/llm/providers/working` (déjà présent dans `main.py`).
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS** (checklist copy-paste par endpoint):
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Avant de créer du code, **chercher** un helper existant (normalisation tickers, cache TTL, downsample, storage loader) et le réutiliser.
  - Garder un contrat stable: `ok/data` + champs standard `generated_at`, `freshness|timestamp`, `source[]`, `filters_applied`, `stats`, `warnings` (même si vide).
  - Ajouter un flag `debug=true` (query) qui:
    - **désactive le cache**, et
    - expose uniquement en debug: `debug_pipeline` (traces), `debug_payload`, `debug_llm_res` (jamais en nominal).
  - Cache TTL: utiliser le pattern Judge (key dérivée des params + TTL + prune). Si vous devez partager un cache, préférer `apps/api/src/platform/legacy/core/memory_cache.py` (`TTLCache`) ou les helpers `_response_cache_*` existants dans `apps/api/src/platform/main.py` (éviter d'introduire un nouveau cache ad-hoc).
  - LLM: forcer un format **JSON strict sur une seule ligne**, valider avant/après via Pydantic, et implémenter une chaîne de fallback (OpenRouter->g4f->Codestral->Groq) sans casser le contrat "never-empty".

### Audit de conformite Judge (constat code reel -> ajustement plan)

- Constats techniques observes:
  - `/api/freshness` reste un placeholder statique dans `main.py` (`macro/news/stocks freshness minutes` fixes) et ne suit pas encore le pattern Judge de source/freshness calcules.
  - `/api/copilot/history` retourne encore des conversations mock (`mock_conv_*`) dans `main.py`.
  - `/api/dashboard/kpis` est defini a deux endroits (`main.py` et `routes/dashboard.py`) avec risque de divergence de contrat; la route modulaire utilise `load_json(...)` sans import local explicite.
  - `/api/forecasts` (routes/forecasts.py) applique un never-empty minimal mais ne couvre pas encore la parite Judge complete (`debug=true` + bypass cache, `warnings[]`, `stats` riches, provenance `model|fallback` standardisee).
  - `/api/brief` (routes/brief_routes.py) lève `HTTPException 500` au lieu d'un fallback `ok=true` de type never-empty, contrairement au pattern Judge.
- Ajustement de plan obligatoire (sans nouveaux IDs):
  - `TV-ADV-04`: prioriser le passage de `/api/freshness` vers un calcul reel + metadata Judge-parity (`generated_at`, `source[]`, `warnings[]`, `stats`).
  - `TV-ADV-05`: sortir `/api/copilot/history` du mock et imposer le contrat persistant + provenance.
  - `TV-ADV-06`: imposer une source unique pour `/api/dashboard/kpis` et supprimer le chemin duplique.
  - `TV16-FF-01` et `TV16-FF-02`: imposer un contrat forecast unique sur APIs core avec `source=model|fallback`, `model_version`, `freshness_status`.
  - `TV16-FF-03` et `TV16-FF-04`: garantir que le brief et les surfaces UI consomment ce contrat canonique sans shape parallele.
  - `TV-ADV-08` et `TV16-FF-05`: ajouter les tests de parite Judge (contract/debug/cache/degraded) sur endpoints cibles.
  - `TV16-FF-06` et `TV-ADV-10`: bloquer release si un endpoint core reste hors parite Judge ou si la provenance forecast n'est pas visible en UI.

### Exemple de compte-rendu live Judge (format de diffusion agent)

- Adapter les numéros de ligne à la révision courante avant diffusion.
- Texte exemple:
  - Tests live faits sur `http://localhost:8050/api/judge`.
  - Points solides (bon template de base):
    - Cache fonctionnel: même requête `8.39s -> 0.01s`.
    - Contrat never-empty côté erreur interne déjà en place (`judge.py`, bloc fallback critique).
    - Endpoints qualité présents (`/quality`, `/quality/history`).
  - Améliorations prioritaires avant d’en faire le template officiel:
    1. Concurrence/cache stampede:
      - 4 requêtes identiques en parallèle: toutes en `cache_hit=false` (single-flight manquant).
    2. Contrat API trop permissif (si observé sur la version testée):
      - vérifier `response_model` OpenAPI et contraintes strictes des query params.
    3. Debug trop exposé/lourd:
      - `debug=true` payload très volumineux; imposer debug admin + payload tronqué.
    4. Cohérence `risk_level`:
      - aligner options exposées, schéma et builder (éviter toute dégradation implicite incohérente).
    5. Dette technique Pydantic:
      - corriger warnings de dépréciation (`@validator`, `max_items`) avant clonage template.
  - Message prêt à partager aux autres agents:
    - Template Judge validé en base (never-empty + cache + quality), mais bloqué pour clonage tant que single-flight cache, response_model strict OpenAPI, garde-fou debug, et cohérence risk_level ne sont pas corrigés.

### Bonification coverage audit global (2026-02-26)

- Gap 1 (pipeline prevision runtime pas assez model-driven):
  - `TV15-ML-07` + `TV16-FF-02`
- Gap 2 (frontend principal encore non branche APIs core):
  - `TV16-FF-07` + `TV16-FF-04`
- Gap 3 (placeholders/mock dans flux core):
  - `TV16-FF-08` + `TV-ADV-05`
- Gap 4 (quality monitor statique):
  - `TV10-DATA-07` + `TV16-FF-09`
- Gap 5 (gate livraison trop documentaire):
  - `TV16-FF-10` + `TV14-SHIP-07`
- Gap 6 (drift runtime/spec + stale in_progress):
  - `TV13-OPS-07` + `TV13-OPS-08`
- Gap 7 (dette deprecation framework):
  - `TV-ADV-09` + `TV13-OPS-08`
- Gap 8 (board trop massif pour execution solo):
  - `TV13-OPS-09`

---

## T-A1.1 — Verrouiller contrat `/api/health`

- **Objectif**: réponse health stable et rétro-compatible.
- **Scope IN**: normalisation shape + tests.
- **Scope OUT**: ajout observabilité avancée.
- **Prérequis**: backend bootable.
- **Fichiers cibles**: `apps/api/src/platform/main.py`, `apps/api/tests/test_health.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser le pattern Judge: enveloppe `ok/data` + `generated_at` + `source[]` (même si `/api/health` est simple).
  - Aligner les clés storage sur le reste du backend: préférer `storage.io.load_json("forecasts")`, `load_json("news_feed")`, `load_json("brief_weekly")`, `load_json("backtests")` (éviter les variantes `"*.json"` si pas nécessaires).
  - Ne pas renommer des clés existantes: ajouter des alias (ex: `timestamp`/`generated_at`) pour préserver compat client/tests.
- **Plan implémentation**:
  1. Définir schéma attendu (top-level + data).
  2. Harmoniser champs `status`.
  3. Ajuster/ajouter tests.
- **Critères d’acceptation testables**:
  - Endpoint renvoie 200 + `ok=true`.
  - `data.timestamp` présent.
- **Commandes de test**:
  - `curl -sS http://localhost:8050/api/health | jq`
  - `cd apps/api && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_health.py`
- **Evidences attendues**: payload health + pytest vert.
- **Risques**: clients dépendants anciens champs.
- **Dépendances**: aucune.

## T-A2.1 — Unifier réponse mono ticker `/api/stocks/prices`

- **Objectif**: contrat UI-friendly pour 1 ticker.
- **Scope IN**: champs `ticker, points, count, timestamp`.
- **Scope OUT**: provider data externe.
- **Prérequis**: snapshot `stocks/prices` ou fallback actif.
- **Fichiers cibles**: `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser la normalisation existante: `core/ticker_normalization.py` (pas de parsing custom des tickers).
  - Réutiliser le cache TTL déjà en place (`_response_cache_key/_get/_set` + `STOCKS_PRICES_CACHE_TTL_SECONDS`) au lieu d'introduire un nouveau cache.
  - Réutiliser le downsampling existant (`_downsample_points` / `core.downsample.lttb`) pour garder un payload UI léger.
  - Garder le contrat mono-ticker comme "subset" du multi-ticker (mêmes champs standard: `generated_at`, `freshness|timestamp`, `source[]`, `filters_applied`, `stats`, `warnings`).
- **Plan implémentation**:
  1. Vérifier mapping mono ticker.
  2. Garantir présence clés même si vide.
- **Critères d’acceptation testables**:
  - Requête `ticker=SPY` renvoie schéma conforme.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq`
- **Evidences attendues**: JSON de référence stocké dans artefact.
- **Risques**: data manquante selon environnement.
- **Dépendances**: T-A1.1.

## T-A2.2 — Tester multi ticker `/api/stocks/prices`

- **Objectif**: valider payload map multi-tickers.
- **Scope IN**: tests de contrat + cas erreur input.
- **Scope OUT**: optimisation perfs.
- **Prérequis**: T-A2.1.
- **Fichiers cibles**: `apps/api/tests/test_stocks_prices_contract.py` (nouveau)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les mêmes invariants que Judge: "never-empty" (pas de 500), `ok/data`, et clés stables (`count`, `timestamp|freshness`, `source[]`, `filters_applied`, `stats`, `warnings`).
  - Éviter les appels réseau dans les tests (pas de dépendance FRED/YFinance): baser le test sur la shape + fallback contract (payload vide acceptable, mais structure obligatoire).
- **Plan implémentation**:
  1. Ajouter tests `tickers=SPY,QQQ`.
  2. Ajouter test paramètre manquant.
- **Critères d’acceptation testables**:
  - Tests passent.
  - Aucun 500 en cas input incomplet.
- **Commandes de test**:
  - `cd apps/api && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_stocks_prices_contract.py`
- **Evidences attendues**: rapport pytest.
- **Risques**: divergence selon fixtures data.
- **Dépendances**: T-A2.1.

## T-A3.1 — Normaliser `news_feed` items

- **Objectif**: items news exploitables et homogènes.
- **Scope IN**: mapping title/url/source/date/tickers/score.
- **Scope OUT**: scoring algorithmique news.
- **Prérequis**: endpoint existant.
- **Fichiers cibles**: `apps/api/src/platform/main.py`, `apps/api/src/domains/market_data/application/news_service.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les helpers existants de normalisation (timestamps, `source[]`, filtrage fenêtre) au lieu de recoder un mapping.
  - Réutiliser `core/ticker_normalization.py` via la résolution tickers déjà utilisée côté `/api/news/feed` (éviter les filtres tickers fragiles).
  - Conserver l'alias compat `articles` (en plus de `items`) tant que le frontend n'est pas migré.
  - Garder les champs standard Judge: `generated_at`, `freshness|last_update`, `source[]`, `filters_applied`, `stats`, `warnings`.
- **Plan implémentation**:
  1. Unifier format `items`.
  2. Garder alias `articles` pour compat.
- **Critères d’acceptation testables**:
  - `items` non nul, `count` cohérent.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq`
- **Evidences attendues**: 1 payload exemple normalisé.
- **Risques**: variabilité schema source raw news.
- **Dépendances**: T-A1.1.

## T-A3.2 — Tests contrat `news_feed`

- **Objectif**: figer le contrat minimal dans des tests.
- **Scope IN**: tests items/limit/filter tickers.
- **Scope OUT**: perf tests.
- **Prérequis**: T-A3.1.
- **Fichiers cibles**: `apps/api/tests/test_news_feed_contract.py` (nouveau)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Tester le contrat (shape) avant le contenu: `ok`, `data.items`, `data.count`, `data.generated_at`, `data.source[]`.
  - Ajouter un test `tickers=SPY,QQQ` qui accepte le fallback "filter relaxed" (warning) mais refuse un 500.
- **Plan implémentation**:
  1. Ecrire tests nominal + edge cases.
  2. Valider non-régression.
- **Critères d’acceptation testables**:
  - pytest vert.
- **Commandes de test**:
  - `cd apps/api && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_news_feed_contract.py`
- **Evidences attendues**: rapport pytest.
- **Risques**: dépendance aux fixtures runtime.
- **Dépendances**: T-A3.1.

## T-A4.1 — Confirmer route unique `/api/forecasts`

- **Objectif**: éviter ambiguïtés d’implémentation forecasts.
- **Scope IN**: route active unique via router.
- **Scope OUT**: calcul des scores forecast.
- **Prérequis**: boot backend OK.
- **Fichiers cibles**: `apps/api/src/platform/main.py`, `apps/api/src/domains/forecasts/api/forecasts.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Prendre `/api/judge` comme modèle: un seul chemin "source of truth" + cache TTL + `debug=true` pour bypass cache et traces.
  - Réutiliser `src/core/response.ok/err` (routes modulaires) et harmoniser l'enveloppe (`ok/data`) avec `main.py` si nécessaire, au lieu de créer une 3e variante.
  - S'assurer que `/api/forecasts` lit les mêmes sources que Judge (`storage.io.load_json("forecasts")`) pour éviter des divergences "forecasts.json" vs "forecasts".
- **Plan implémentation**:
  1. Vérifier include_router.
  2. Supprimer incohérences commentaire/code.
- **Critères d’acceptation testables**:
  - `GET /api/forecasts` stable (10 appels sans 500).
- **Commandes de test**:
  - `for i in {1..10}; do curl -sS http://localhost:8050/api/forecasts >/dev/null; done; echo OK`
- **Evidences attendues**: log boucle OK + payload exemple.
- **Risques**: dépendance data forecasts périmée.
- **Dépendances**: T-A1.1.

## T-A5.1 — Hardening `/api/copilot/ask`

- **Objectif**: robustesse cas sans source/LLM indisponible.
- **Scope IN**: erreurs contrôlées, champs qualité.
- **Scope OUT**: amélioration modèle LLM.
- **Prérequis**: modules research importables.
- **Fichiers cibles**: `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser le client existant `apps/api/src/platform/legacy/research/llm_client.py` (`ask_llm`) et aligner son fallback sur le pattern Judge (toujours `answer` non vide + `sources[]` + `generated_at` + `source[]`).
  - Si un fallback g4f est requis, préférer `services/g4f_client.call_g4f` (sélection modèle/provider + retour normalisé) plutôt que des appels g4f inline.
  - Ajouter un mode `debug` (query/body) qui expose `model/provider` + `citations` et garde le nominal compact.
- **Plan implémentation**:
  1. Encadrer try/except avec messages déterministes.
  2. Garantir shape de fallback.
- **Critères d’acceptation testables**:
  - Réponse toujours avec `answer` + `sources`.
- **Commandes de test**:
  - `curl -sS -X POST "http://localhost:8050/api/copilot/ask" -H 'Content-Type: application/json' -d '{"question":"Etat marché"}' | jq`
- **Evidences attendues**: payload nominal/fallback.
- **Risques**: latence ou indisponibilité provider LLM.
- **Dépendances**: T-A1.1.

## T-B1.1 — Créer couche API frontend minimale

- **Objectif**: centraliser fetch MVP.
- **Scope IN**: helper fetch + timeout + gestion erreurs.
- **Scope OUT**: migration framework frontend.
- **Prérequis**: contrats API A stabilisés.
- **Fichiers cibles**: `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser le pattern backend Judge: toutes les réponses sont `ok/data` (et potentiellement `source[]`, `freshness`). Le wrapper `fetchJson` doit normaliser ces champs sans "adapter" au cas par cas.
  - Réutiliser les IDs DOM + fonctions existantes dans `app.js` (pas de rewrite UI). Objectif: brancher, pas redesign.
- **Plan implémentation**:
  1. Ajouter wrapper `fetchJson`.
  2. Mapper endpoints MVP.
- **Critères d’acceptation testables**:
  - Les appels MVP passent via wrapper unique.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - test navigateur réel sur `http://localhost:5173` + capture réseau (CDP/Playwright/Cypress).
- **Evidences attendues**: extrait code + capture réseau + `snapshot` UI (nominal + dégradé).
- **Risques**: side-effects sur fonctions legacy.
- **Dépendances**: T-A2.1, T-A3.1, T-A4.1, T-A5.1.

## T-B1.2 — Brancher widgets MVP aux données API

- **Objectif**: afficher health/news/forecasts/stocks réels.
- **Scope IN**: mapping payload -> render.
- **Scope OUT**: redesign complet UI.
- **Prérequis**: T-B1.1.
- **Fichiers cibles**: `apps/web/src/domains/forecasts/pages/app.js`, `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les widgets existants (ne pas en recréer):
    - `apps/web/src/domains/forecasts/components/header.html`
    - `apps/web/src/domains/forecasts/components/ai-suggestions-panel.html`
    - `apps/web/src/domains/forecasts/components/filter-bar.html`
    - `apps/web/src/domains/forecasts/components/header.html`
  - Réutiliser le loader `apps/web/src/platform/js` et garder le mapping `{path,target}` comme source de vérité de chargement.
  - Toujours rendre visible le `source`/`freshness` si fourni par l'API (sinon marquer fallback).
- **Plan implémentation**:
  1. Identifier widgets MVP.
  2. Injecter data API et loading states.
- **Critères d’acceptation testables**:
  - Widgets affichent data API lorsque backend up.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - test navigateur réel sur `http://localhost:5173` (nominal + refresh hard), avec snapshot.
- **Evidences attendues**: `snapshot` widgets remplis sur chaque bloc clé.
- **Risques**: couplage DOM fragile.
- **Dépendances**: T-B1.1.

## T-B2.1 — Badge « Données simulées »

- **Objectif**: transparence utilisateur fallback.
- **Scope IN**: badge visible par composant fallback.
- **Scope OUT**: système de feature flags global.
- **Prérequis**: B1 en place.
- **Fichiers cibles**: `apps/web/src/domains/forecasts/pages/app.js`, `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser les champs backend standard (`source[]`, `warnings[]`, `freshness`) pour décider du badge au lieu d'heuristiques fragiles.
  - Le badge doit être par-widget (pas un global) pour refléter les dégradations partielles (pattern Judge: contract never-empty + warnings).
- **Plan implémentation**:
  1. Ajouter booléen `isMockSource` par bloc.
  2. Rendre badge conditionnel.
- **Critères d’acceptation testables**:
  - Badge visible quand backend down ou data absente.
- **Commandes de test**:
  - Stop backend puis reload UI.
  - capture navigateur du fallback (`source=fallback`) avant/après bascule backend.
- **Evidences attendues**: captures backend up/down + snapshots UI associées.
- **Risques**: faux positifs de fallback.
- **Dépendances**: T-B1.2.

## T-C1.1 — Script gate MVP PASS/BLOCKED

- **Objectif**: une commande de gate unique.
- **Scope IN**: health + 4 endpoints + copilot ask + smoke.
- **Scope OUT**: tests perfs.
- **Prérequis**: tâches A/B principales.
- **Fichiers cibles**: `skills/finance-regression-gate/` ou `scripts/` + `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DELIVERY-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les gates existants (`scripts/backend_regression_gate.sh`, `scripts/run_delivery_gate.sh`) et compléter plutôt que créer un nouveau framework.
  - Les checks doivent consommer les endpoints via le contrat `ok/data` et remonter les `source[]/warnings[]` (pattern Judge) dans l'artefact final.
- **Plan implémentation**:
  1. Écrire script gate idempotent.
  2. Générer rapport markdown/json horodaté.
- **Critères d’acceptation testables**:
  - Sortie claire PASS/BLOCKED.
  - Rapport créé sous `finance-app/openclaw-gates/`.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - `bash <script_gate>.sh`
- **Evidences attendues**: rapport gate + code retour shell.
- **Risques**: dépendances externes ponctuellement indisponibles.
- **Dépendances**: A1..A2 (gate initial), puis A3..A5 et B1..B2 pour le gate final.

## T-C1.2 — Runbook orchestration MVP (codex/OpenClaw)

- **Objectif**: standardiser dispatch/monitoring des tâches.
- **Scope IN**: prompts par rôle, cadence check, format preuves.
- **Scope OUT**: auto-remédiation complète.
- **Prérequis**: OpenClaw opérationnel (cron + runner tmux).
- **Fichiers cibles**:
  - `docs/planning/mvp-plan.md`
  - `docs/product/planning/tasks.md`
  - `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
  - `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`
  - `scripts/preflight_dispatch.sh`
  - `scripts/validate_roles_sequential.sh`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DELIVERY-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Référencer explicitement le modèle Judge (section "Modèle de référence: Judge API") pour les conventions de contrat/caching/debug sur tous les endpoints du runbook.
  - Standardiser la collecte d'évidences: pour chaque endpoint, capturer un payload JSON + mentionner `source[]` et `freshness` dans l'artefact.
- **Plan implémentation**:
  1. Préflight (états + santé soft).
  2. Exécution séquentielle stricte par batch (planner->dev->tester->qa).
  3. Publication artefact de preuve + `run_delivery_gate`.
- **Critères d’acceptation testables**:
  - Un batch produit: contrats (8 clés) + un artefact `openclaw-gates/` gateable.
- **Commandes de test**:
  - `bash scripts/preflight_dispatch.sh`
  - `SEQUENTIAL_VALIDATE_TIMEOUT_SECONDS=480000 bash scripts/validate_roles_sequential.sh --roles planner,dev,tester,qa --strict-ready-chain --chain-target BATCH-XX`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-XX-<timestamp>.md`
- **Evidences attendues**:
  - `finance-app/openclaw-gates/batch-XX-<timestamp>.md`
  - `logs-codex-runs/role-runner/sequential-validate-*.jsonl`
- **Risques**: saturation context/token selon prompts.
- **Dépendances**: T-C1.1.

---

## Pack de dispatch (delta incrémental)

### Batch-01

- **Tâches**: `T-A1.1`, `T-A2.1`
- **Instruction commune agents**:
  - livrer strictement le scope IN
  - joindre commandes exactes exécutées
  - joindre preuves minimales (payload JSON + sortie tests)
  - terminer avec contrat complet (8 clés) et verdict `PASS|BLOCKED` motivé
- **Blocage immédiat si**:
  - absence de section EVIDENCE
  - test non exécuté
  - contrat API modifié sans test mis à jour
- **Chemin artefact obligatoire**:
  - `finance-app/openclaw-gates/batch-01-<timestamp>.md`
  - contenu minimal: `DELTA`, `EVIDENCE`, `RISKS`, `NEXT`, `VERDICT`, `BLOCKER_ID`, `NEXT_ACTION_UNIQUE`

### Handoff checklist QA (delta 20:05)

- [ ] Scope IN respecté pour chaque tâche du batch
- [ ] Au moins 1 commande de test exécutée par tâche
- [ ] Évidence textuelle copiée dans artefact gate
- [ ] Verdict explicite `PASS` ou `BLOCKED`
- [ ] Prochaine action unique définie

## Ordonnancement recommandé

1. T-A1.1
2. T-A2.1 → T-A2.2
3. T-A3.1 → T-A3.2
4. T-A4.1
5. T-A5.1
6. T-B1.1 → T-B1.2
7. T-B2.1
8. T-C1.1 → T-C1.2

## Delta tâches (cycle 20:20)

### Delta 20:20 — commandes renforcées pour `T-A1.1`

- Ajouter boucle stabilité:
  - `for i in {1..3}; do curl -sS http://localhost:8050/api/health | jq -c '{ok,status,ts:.data.timestamp}'; done`
- Critère additionnel: 3/3 réponses exploitables, sans clé absente.

### Delta 20:20 — commandes renforcées pour `T-A2.1`

- Ajouter vérification robuste des clés:
  - `for i in {1..5}; do curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq -c '{ok,ticker,count,has_points:(.data.points!=null),has_ts:(.data.timestamp!=null)}'; done`
- Critère additionnel: 5/5 réponses sans erreur serveur.

### Template d’évidence obligatoire (toutes tâches Batch-01)

```text
STATUS:
DELTA:
EVIDENCE: task_update=...;lock_check=ok;stream_id=<BATCH-ID>;task_id=<...>;cmd=...;tests_run=...
RISKS:
NEXT:
VERDICT: PASS|BLOCKED
BLOCKER_ID: NONE|...
NEXT_ACTION_UNIQUE:
```

## Delta runbook tâches (cycle 20:35)

### Lot prêt à exécution immédiate (Batch-01)

1. **T-A1.1**
   - Owner: `dev`
   - QA gate: `tester` valide commandes, `qa` signe verdict
2. **T-A2.1**
   - Owner: `dev`
   - QA gate: stabilité 5x obligatoire avant verdict

### Lot conditionnel suivant (Batch-02)

1. **T-A2.2** (tests multi-ticker)
2. **T-A3.1** (normalisation news)

**Règle d’activation Batch-02**: présence de `VERDICT: PASS` dans `finance-app/openclaw-gates/batch-01-<timestamp>.md`.

### Template d’assignation agent (copier-coller)

```text
[TASK_ID] <id>
OBJECTIF: <objectif court>
SCOPE_IN: <liste>
SCOPE_OUT: <liste>
PREREQUIS: <liste>
FICHIERS_CIBLES: <liste>
PLAN_IMPLEMENTATION: <3-5 étapes>
ACCEPTANCE_TESTABLE: <points vérifiables>
COMMANDES_TEST: <commandes exactes>
EVIDENCES_ATTENDUES: <artefacts + extraits>
RISQUES: <liste>
DEPENDANCES: <liste>
VERDICT_ATTENDU: PASS|BLOCKED
```

## Delta dispatch tâches (cycle 20:50)

### Pack Batch-02 (préparé, verrouillé)

#### Carte d’assignation prête pour `T-A2.2`

```text
[TASK_ID] T-A2.2
OBJECTIF: valider contrat multi-ticker /api/stocks/prices
SCOPE_IN: tests tickers=SPY,QQQ; test input incomplet; absence de 500
SCOPE_OUT: optimisation perf; refactor endpoint
PREREQUIS: VERDICT PASS Batch-01
FICHIERS_CIBLES: apps/api/tests/test_stocks_prices_contract.py
PLAN_IMPLEMENTATION: écrire tests -> exécuter -> corriger si rouge -> re-run vert
ACCEPTANCE_TESTABLE: pytest vert; map multi-ticker stable; cas incomplet non bloquant
COMMANDES_TEST: cd apps/api && ([ -x .venv/bin/pytest ] || (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)) && .venv/bin/pytest -q tests/test_stocks_prices_contract.py
EVIDENCES_ATTENDUES: sortie pytest + payload multi-ticker de référence
RISQUES: fixtures data divergentes
DEPENDANCES: T-A2.1
VERDICT_ATTENDU: PASS|BLOCKED
```

#### Carte d’assignation prête pour `T-A3.1`

```text
[TASK_ID] T-A3.1
OBJECTIF: normaliser le contrat /api/news/feed
SCOPE_IN: items/count + alias articles + fallback contrôlé
SCOPE_OUT: ranking news avancé
PREREQUIS: VERDICT PASS Batch-01
FICHIERS_CIBLES: apps/api/src/platform/main.py; apps/api/src/domains/market_data/application/news_service.py
PLAN_IMPLEMENTATION: normaliser mapping -> garder compat alias -> valider payload
ACCEPTANCE_TESTABLE: items non nul; count cohérent; aucune 500 en nominal
COMMANDES_TEST: curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq
EVIDENCES_ATTENDUES: payload normalisé + verdict QA
RISQUES: qualité variable des entrées news
DEPENDANCES: T-A1.1
VERDICT_ATTENDU: PASS|BLOCKED
```

### Règle de lot

- Batch-02 est exécuté en séquence stricte `T-A2.2` puis `T-A3.1`.
- Si `T-A2.2` est BLOCKED, ne pas lancer `T-A3.1`.

## Delta tâches (cycle 21:05)

### Contrôle qualité lot (ajout)

- **Nouvelle exigence commune Batch-01/Batch-02**:
  - inclure `VERDICT: PASS|BLOCKED`
  - inclure `BLOCKER_ID` (ou `NONE`)
  - inclure `NEXT_ACTION_UNIQUE`

### Patch minimal policy (ajout)

- En cas `BLOCKED`, l’agent `dev` doit proposer un patch minimal ciblé sur le fichier fautif listé dans `BLOCKER_ID`.
- Interdiction d’ouvrir des fichiers hors scope de la tâche sans justification QA.

### Evidence quality gate (ajout)

- Toute commande de test listée dans la tâche doit avoir soit:
  1) sortie utile incluse dans l’artefact, soit
  2) motif documenté de non-exécution.

## Changelog

- 2026-02-24 19:50 America/New_York — Ajout du pack de dispatch Batch-01 avec règles de preuve et conditions de blocage immédiat.
- 2026-02-24 20:05 America/New_York — Ajout du chemin d’artefact obligatoire pour Batch-01 et d’une checklist QA de handoff pour fiabiliser le verdict.
- 2026-02-24 20:20 America/New_York — Renforcement incrémental des tâches Batch-01 (boucles de stabilité health/stocks) + template d’évidence unifié PASS/BLOCKED.
- 2026-02-24 20:35 America/New_York — Ajout d’un runbook de lot (Batch-01 immédiat, Batch-02 conditionnel), règle d’activation explicite via artefact gate, et template d’assignation standardisé.
- 2026-02-24 20:50 America/New_York — Préparation du pack Batch-02 avec cartes d’assignation complètes pour T-A2.2/T-A3.1 et règle de séquencement bloquant.
- 2026-02-24 21:05 America/New_York — Ajout d’exigences communes d’artefacts (VERDICT/BLOCKER_ID/NEXT_ACTION_UNIQUE), politique de patch minimal en cas BLOCKED, et gate qualité des preuves pour toutes commandes de test listées.
- 2026-02-24 22:05 America/New_York — Alignement tâches sur environnement VM: commandes pytest auto-bootstrap + dépendances C1 réalignées pour éviter cycle avec lot A.
- 2026-02-26 14:10 America/New_York — Alignement complet sur orchestration codex-only/OpenClaw: suppression des mentions legacy et adoption du runbook `preflight_dispatch` + `validate_roles_sequential` + `run_delivery_gate`.
- 2026-02-26 America/New_York — Intégration d’un cadrage architecture anti-chevauchement sur les tâches existantes (ownership par task ID, verrous de zones sensibles, handoffs obligatoires), sans création de nouveaux IDs.
- 2026-02-26 America/New_York — Ajout du mode co-édition multi-agents: protocole claim/edit/merge, synchronisation stricte vers board commun `docs/product/planning/tasks.md`.

## Vision Task Pack - Sprint W10 (P0-first)

Source:

- `docs/product/planning/PRODUCT_VISION.md`
- `docs/product/scrum/sprint-next.md`

Execution rule:

- Keep tasks 2-4h each.
- Close only with contract output + test evidence.
- Prioritize user-visible decision flow over refactor work.

### TV1-FRESH-01 - Freshness metadata contract (P0)

- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: rendre la fraicheur visible et cohérente sur les endpoints core.
- **Scope IN**:
  - standardiser `updated_at`, `age_seconds`, `freshness_status` sur:
    - `/api/stocks/prices`
    - `/api/news/feed`
    - `/api/forecasts`
- **Scope OUT**: optimisation perf profonde des providers.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/forecasts/api/forecasts.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/storage/ttl.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/core/path_resolver.py; apps/api/src/platform/main.py (_response_cache_* / _utc_now_iso)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FRESHNESS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser un helper commun de fraicheur (TTL + statut + raison) pour eviter une logique dupliquee entre endpoints et UI.
  - Imposer le contrat minimal commun: freshness_status, stale_reason, source_status, generated_at et warnings[].
  - Propager explicitement letat degraded jusquau frontend (pas de fallback silencieux).
- **Acceptation testable**:
  - les 3 endpoints exposent les 3 champs de fraicheur.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq`
  - `curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq`
  - `curl -sS "http://localhost:8050/api/forecasts" | jq`
- **Dependencies**: none

### TV1-FRESH-02 - Cache TTL and stale guardrails (P0)

- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: garantir la cible <=10 minutes sur surfaces critiques.
- **Scope IN**:
  - TTL cache configurable pour prices/news/forecasts
  - fallback explicite si data stale (`freshness_status=stale`)
- **Scope OUT**: stockage distribue/cache externe.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/market_data/application/news_service.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/storage/ttl.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/core/path_resolver.py; apps/api/src/platform/main.py (_response_cache_* / _utc_now_iso)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FRESHNESS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser un helper commun de fraicheur (TTL + statut + raison) pour eviter une logique dupliquee entre endpoints et UI.
  - Imposer le contrat minimal commun: freshness_status, stale_reason, source_status, generated_at et warnings[].
  - Propager explicitement letat degraded jusquau frontend (pas de fallback silencieux).
- **Acceptation testable**:
  - aucun fallback silencieux; stale signalé explicitement.
- **Commandes de test**:
  - `cd apps/api && .venv/bin/pytest -q tests/test_endpoint_cache_contracts.py`
- **Dependencies**: TV1-FRESH-01

### TV1-FRESH-03 - Freshness SLA checker (P0)

- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: mesurer et prouver le SLA de fraicheur.
- **Scope IN**:
  - script de contrôle SLA (>=90% cycles <=10m)
  - sortie PASS/BLOCKED + métriques
- **Scope OUT**: monitoring cloud externe.
- **Fichiers cibles**:
  - `scripts/`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/storage/ttl.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/core/path_resolver.py; apps/api/src/platform/main.py (_response_cache_* / _utc_now_iso)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FRESHNESS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser un helper commun de fraicheur (TTL + statut + raison) pour eviter une logique dupliquee entre endpoints et UI.
  - Imposer le contrat minimal commun: freshness_status, stale_reason, source_status, generated_at et warnings[].
  - Propager explicitement letat degraded jusquau frontend (pas de fallback silencieux).
- **Acceptation testable**:
  - un run produit un verdict SLA auditable.
- **Commandes de test**:
  - `bash scripts/preflight_dispatch.sh`
  - `bash <freshness_sla_script>.sh`
- **Dependencies**: TV1-FRESH-02

### TV2-SIGNAL-01 - Decision signal schema v1 (P0)

- **Epic**: Epic 2 - Forecast Engine
- **Objectif**: figer le contrat de signal utilisé par backend+frontend.
- **Scope IN**:
  - contrat par actif/secteur:
    - `direction`, `confidence`, `action`, `horizon`, `why`, `risk_flag`, `updated_at`
  - mapping backend vers payload frontend.
- **Scope OUT**: algorithme avancé de scoring.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/api/schemas.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/platform/legacy/analytics/phases_adapter.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/core/ticker_normalization.py; apps/api/src/domains/forecasts/api/forecasts.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FORECAST-SIGNAL (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser le calcul des signaux dans un service core partage puis exposer via routes, sans dupliquer la logique metier par endpoint.
  - Garder une shape stable (why[], risk_flag, confidence, horizon) avec enums normalisees et fallback deterministe.
  - Brancher les controles de coverage/SLA dans le gate existant scripts/run_delivery_gate.sh plutot quun check parallele.
- **Acceptation testable**:
  - contrat stable et sans champ manquant.
- **Commandes de test**:
  - `cd apps/api && .venv/bin/pytest -q`
- **Dependencies**: TV1-FRESH-01

### TV2-SIGNAL-02 - Core asset signals (P0)

- **Epic**: Epic 2 - Forecast Engine
- **Objectif**: livrer un signal exploitable sur noyau d’actifs prioritaire.
- **Scope IN**:
  - actifs: `SPY, QQQ, GLD, SLV, NVDA, TSLA`
  - horizons: `1-3d` et `1-2w`
- **Scope OUT**: univers complet MVP.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/platform/legacy/analytics/phases_adapter.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/core/ticker_normalization.py; apps/api/src/domains/forecasts/api/forecasts.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FORECAST-SIGNAL (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser le calcul des signaux dans un service core partage puis exposer via routes, sans dupliquer la logique metier par endpoint.
  - Garder une shape stable (why[], risk_flag, confidence, horizon) avec enums normalisees et fallback deterministe.
  - Brancher les controles de coverage/SLA dans le gate existant scripts/run_delivery_gate.sh plutot quun check parallele.
- **Acceptation testable**:
  - chaque actif retourne direction+confidence+action+updated_at.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/stocks/prices?tickers=SPY,QQQ,GLD,SLV,NVDA,TSLA" | jq`
- **Dependencies**: TV2-SIGNAL-01

### TV2-SIGNAL-03 - Full MVP universe coverage (P0)

- **Epic**: Epic 2 - Forecast Engine
- **Objectif**: étendre la couverture au périmètre vision MVP.
- **Scope IN**:
  - indices: `SPY, QQQ, DIA, IWM`
  - metals: `GLD, SLV`
  - AI/mega-cap: `NVDA, MSFT, AMZN, GOOGL, META, TSLA, AAPL`
  - sectors: `XLK, XLE, XLF, XLV, XLI`
- **Scope OUT**: actifs hors univers MVP.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/data/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/platform/legacy/analytics/phases_adapter.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/core/ticker_normalization.py; apps/api/src/domains/forecasts/api/forecasts.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FORECAST-SIGNAL (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser le calcul des signaux dans un service core partage puis exposer via routes, sans dupliquer la logique metier par endpoint.
  - Garder une shape stable (why[], risk_flag, confidence, horizon) avec enums normalisees et fallback deterministe.
  - Brancher les controles de coverage/SLA dans le gate existant scripts/run_delivery_gate.sh plutot quun check parallele.
- **Acceptation testable**:
  - > =90% univers avec signal complet par cycle.
    >
- **Commandes de test**:
  - `cd apps/api && .venv/bin/pytest -q tests/test_stocks_prices_contract.py`
- **Dependencies**: TV2-SIGNAL-02

### TV4-UI-01 - Decision cards API adapter (P1 but sprint-committed)

- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: brancher frontend sur le contrat de signal backend.
- **Scope IN**:
  - adapter fetch unique pour signals/freshness
  - gestion loading/error claire
- **Scope OUT**: redesign UI complet.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js; apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/contracts/mockData.js (fallback visible)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Sappuyer sur les widgets et loaders existants (app.js, componentLoader.js, composants actuels) sans nouveau framework UI.
  - Creer un adaptateur API par surface (cards/brief/actions) avec etats loading/error/degraded explicites.
  - Preserver le flux 2-3 clics de bout en bout et eviter des chemins async concurrents qui cassent la coherence ecran.
- **Acceptation testable**:
  - appels API centralisés et traçables.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - test navigateur réel `http://localhost:5173` + snapshot du rendu decision cards.
- **Dependencies**: TV2-SIGNAL-01

### TV4-UI-02 - 2-3 click daily brief flow (P1 but sprint-committed)

- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: obtenir "quoi faire aujourd’hui" en 2-3 interactions.
- **Scope IN**:
  - vue synthèse avec action recommandée
  - navigation rapide actifs/secteurs prioritaires
- **Scope OUT**: navigation avancée multi-pages.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/index.html`
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js; apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/contracts/mockData.js (fallback visible)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Sappuyer sur les widgets et loaders existants (app.js, componentLoader.js, composants actuels) sans nouveau framework UI.
  - Creer un adaptateur API par surface (cards/brief/actions) avec etats loading/error/degraded explicites.
  - Preserver le flux 2-3 clics de bout en bout et eviter des chemins async concurrents qui cassent la coherence ecran.
- **Acceptation testable**:
  - flux complet <=3 clics vers briefing actionnable.
- **Commandes de test**:
  - test navigateur réel du parcours 2-3 clics + snapshots de chaque étape.
- **Dependencies**: TV4-UI-01

### TV4-UI-03 - Freshness and degraded-state badges (P1 but sprint-committed)

- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: rendre explicite l’état des données.
- **Scope IN**:
  - badge `fresh/stale/degraded`
  - affichage `updated_at` sur chaque carte
- **Scope OUT**: alerting mobile/push.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js; apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/contracts/mockData.js (fallback visible)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Sappuyer sur les widgets et loaders existants (app.js, componentLoader.js, composants actuels) sans nouveau framework UI.
  - Creer un adaptateur API par surface (cards/brief/actions) avec etats loading/error/degraded explicites.
  - Preserver le flux 2-3 clics de bout en bout et eviter des chemins async concurrents qui cassent la coherence ecran.
- **Acceptation testable**:
  - aucun état caché: stale/degraded toujours visible.
- **Commandes de test**:
  - Stop partiel backend/source + vérification navigateur du rendu degradé.
  - snapshot dédié par écran concerné (`fresh`, `stale`, `degraded`).
- **Dependencies**: TV1-FRESH-01, TV4-UI-01

### TV-QA-01 - Sprint W10 end-to-end gate (P0 release gate)

- **Epic**: Cross-epic quality gate
- **Objectif**: valider le sprint sur workflow utilisateur final.
- **Scope IN**:
  - test e2e backend+frontend via navigateur réel
  - mesure des métriques sprint (freshness/coverage/clicks)
  - artefact final PASS/BLOCKED
- **Scope OUT**: tests non-MVP.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- `docs/product/scrum/sprint-next.md`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Le gate doit verifier explicitement la chaine complete API forecast -> rendu UI -> evidence artefactee.
  - Le gate doit echouer si `source=model|fallback` et `model_version` ne sont pas tracables sur les surfaces core.
- **Acceptation testable**:
  - artefact final signé QA avec verdict et blocker_id.
- **Commandes de test**:
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/sprint-w10-<timestamp>.md`
- **Dependencies**:
  - TV1-FRESH-03
  - TV2-SIGNAL-03
  - TV4-UI-03

### Ready-next queue (after W10 commit)

- TV3-JUDGE-01 - Multi-provider opinion collector (g4f-first).
  - INTEGRATION-APP-EENGINEER-RECOMMENDATIONS:
    - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
    - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
    - Réutiliser le pattern `/api/judge` (cache TTL + debug bypass + Pydantic + JSON strict) comme squelette de l'endpoint.
    - g4f: réutiliser `services/g4f_client.call_g4f` + la liste `tested_g4f_models*_*.json` (pas d'appel g4f inline).
    - Réutiliser `agents/g4f_model_watcher.py` + `GET /api/llm/providers/working` pour piloter le choix des modèles/latences.
- TV3-JUDGE-02 - Judge arbitration output (`final_action`, `confidence_delta`, `conflict_mode`).
  - INTEGRATION-APP-EENGINEER-RECOMMENDATIONS:
    - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
    - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
    - Réutiliser `services/judge_builder.py` + `schemas/judge.py` pour figer un contrat canonique (et éviter une 2e shape "judge-like").
    - Conserver `source[]/warnings[]/generated_at` et exposer explicitement `fallback_used` quand une étape LLM échoue (pattern Judge).
- TV5-ASK-01 - Ask Copilot deep analysis with grounded context.
  - INTEGRATION-APP-EENGINEER-RECOMMENDATIONS:
    - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
    - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
    - Réutiliser `research/llm_client.ask_llm` (OpenAI->g4f->fallback) et aligner la réponse sur l'enveloppe Judge (`ok/data`, `sources[]`, `generated_at`, `source[]`).
    - Éviter d'introduire une nouvelle logique de RAG: s'appuyer sur `rag_store`/chunks existants et stabiliser le contrat + tests.

## Changelog (vision tasks)

- 2026-02-26 America/New_York - Added W10 vision-aligned task pack prioritized by P0 user-value and freshness constraints.

## Code-Audit Advance Pack (pre-W11)

Source audit (2026-02-26):

- frontend still relies heavily on `mockData.js` and simulated flows in `app.js`
- `/api/freshness` in `main.py` is currently placeholder/static
- `/api/copilot/history` currently returns mock conversations
- duplicate KPI logic exists between `main.py:/api/dashboard/kpis` and `routes/dashboard.py:/kpis`
- tests currently cover mainly `health`, `stocks/prices`, `news/feed`; several decision endpoints are untested
- backend has deprecation debt (`@app.on_event`, `datetime.utcnow`, pydantic v1 validators/max_items)

### UI Fast-Lane Priority (concrete user-visible results)

1. `TV-ADV-01-D2` - Runtime wiring of priority widgets
2. `TV-ADV-02` - Judge widget real wiring
3. `TV-ADV-03` - Real refresh behavior in UI
4. `TV-ADV-07` - Single decision-brief endpoint for 2-3 click flow
5. `TV-ADV-10` - Gate upgrade tied to UI workflow proof

### TV-ADV-01 - Frontend API bridge (remove mock-driven runtime path)

- **Epic**: Epic 4 - Decision Cockpit Frontend
- **Objectif**: remplacer le chemin principal mock par des appels backend réels.
- **Scope IN**:
  - créer un client API frontend centralisé (timeout + erreur + retry léger)
  - brancher widgets décision à API réelle (kpis, forecasts, news, recommendations)
- **Scope OUT**: suppression totale de tous les composants non-MVP.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/contracts/mockData.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les widgets existants (référence: `apps/web/src/domains/forecasts/components/`) et limiter le travail à "wiring + states" (pas de nouveaux composants).
  - Réutiliser le loader `componentLoader.js` et garder `index.html` comme inventaire de widgets chargés.
  - Propager des métadonnées backend standard vers l'UI (`source[]`, `freshness`, `warnings[]`) pour rendre le dégradé visible (pattern Judge).
- **Acceptation testable**:
  - le flux principal ne dépend plus de `mockData.js` en mode nominal backend up.
- **Dependencies**: TV4-UI-01

#### Breakdown for `TV-ADV-01` (ready to launch)

##### TV-ADV-01-P - Planner scope lock and widget map

- **Owner**: planner
- **Objectif**: verrouiller le mapping API -> widgets MVP à migrer en premier.
- **Scope IN**:
  - identifier widgets décision critiques (kpi, forecasts, news, recommendations, judge trigger)
  - définir pour chaque widget: endpoint, contrat requis, fallback explicite
- **Scope OUT**: implémentation JS.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
  - `docs/product/planning/tasks.md` (notes de dispatch si besoin)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un seul adaptateur frontend API (fetchJson) et mapper les widgets MVP existants sans nouveaux composants.
  - Supprimer la dependance mock en nominal, mais conserver un fallback explicite et visible par widget.
  - Aligner strictement les contrats avec les endpoints backend deja cibles (/api/dashboard/kpis, /api/forecasts, /api/news/feed).
- **Evidence attendue**:
  - table de mapping widget->endpoint->contrat->fallback.
- **Dependencies**: TV4-UI-01

##### TV-ADV-01-D1 - Dev API client layer

- **Owner**: dev
- **Objectif**: créer un client API frontend centralisé.
- **Scope IN**:
  - helper unique `fetchJson` (timeout, parse error, retry léger)
  - normalisation format retour (`ok`, `data`, `error`, `source`)
- **Scope OUT**: branchement de tous les widgets.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Normaliser strictement la shape `ok/data/error` et remonter les champs utiles sans les renommer (éviter des adapters widget-spécifiques).
  - Respecter le contrat backend "never-empty": si `ok=true` mais `data` partiel, l'UI doit afficher un état `degraded` plutôt que casser.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - test navigateur réel + console, `http://localhost:5173`, avec snapshot initial.
- **Dependencies**: TV-ADV-01-P

##### TV-ADV-01-D2 - Dev runtime wiring on priority widgets

- **Owner**: dev
- **Objectif**: brancher les widgets MVP prioritaires aux appels backend réels.
- **Scope IN**:
  - brancher au minimum:
    - KPI/dashboard (`/api/dashboard/kpis`)
    - forecasts (`/api/forecasts`)
    - news (`/api/news/feed`)
    - recommendations/brief (`/api/recommendations/daily` ou endpoint validé)
  - conserver fallback explicite quand endpoint indisponible
- **Scope OUT**: migration de tous les widgets secondaires.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
  - `apps/web/src/domains/forecasts/contracts/mockData.js` (désactivation partielle ciblée)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les widgets déjà présents: `kpi-cards-pro.html`, `forecast-scenarios.html`, `news-feed.html` (pas de nouveaux layouts).
  - Garder un fallback explicite par widget (badge + message) au lieu de masquer silencieusement les erreurs (pattern Judge: `warnings[]` + `source[]`).
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - test navigateur réel `http://localhost:5173` + snapshot widgets MVP branchés.
- **Dependencies**: TV-ADV-01-D1

##### TV-ADV-01-T1 - Tester contract and runtime checks

- **Owner**: tester
- **Objectif**: valider que le frontend n’est plus mock-driven sur le chemin principal.
- **Scope IN**:
  - vérifier appels réseau réels sur parcours principal
  - vérifier fallback explicite en cas endpoint down
  - vérifier absence de crash UI
- **Scope OUT**: tests e2e exhaustifs multi-pages.
- **Fichiers cibles**:
  - `apps/api/tests/` (si tests API supplémentaires nécessaires)
  - artefact de preuve dans `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un seul adaptateur frontend API (fetchJson) et mapper les widgets MVP existants sans nouveaux composants.
  - Supprimer la dependance mock en nominal, mais conserver un fallback explicite et visible par widget.
  - Aligner strictement les contrats avec les endpoints backend deja cibles (/api/dashboard/kpis, /api/forecasts, /api/news/feed).
- **Evidence attendue**:
  - capture réseau (endpoints réellement appelés),
  - liste erreurs console (attendu: aucune bloquante),
  - preuve fallback visible + screenshots UI (nominal + dégradé).
- **Dependencies**: TV-ADV-01-D2

##### TV-ADV-01-QA1 - QA signoff gate

- **Owner**: qa
- **Objectif**: signer PASS/BLOCKED de la migration `TV-ADV-01`.
- **Scope IN**:
  - valider DoD: chemin principal backend-driven + fallback explicite + stabilité UI
  - produire verdict avec blocker explicite si incomplet
- **Scope OUT**: optimisation UX/design.
- **Commandes de gate**:
  - `bash scripts/backend_regression_gate.sh --no-live`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/tv-adv-01-<timestamp>.md`
- **Sortie obligatoire**:
  - `VERDICT: PASS|BLOCKED`
  - `BLOCKER_ID: NONE|...`
  - `NEXT_ACTION_UNIQUE: ...`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UI-RUNTIME (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un seul adaptateur frontend API (fetchJson) et mapper les widgets MVP existants sans nouveaux composants.
  - Supprimer la dependance mock en nominal, mais conserver un fallback explicite et visible par widget.
  - Aligner strictement les contrats avec les endpoints backend deja cibles (/api/dashboard/kpis, /api/forecasts, /api/news/feed).
- **Dependencies**: TV-ADV-01-T1

### TV-ADV-02 - Judge widget real wiring

- **Epic**: Epic 3 - Multi-Model Consensus and Judge
- **Objectif**: connecter le widget Judge à des endpoints réels.
- **Scope IN**:
  - utiliser `/api/llm/judge/run` + `/api/llm/providers/working`
  - afficher consensus, modèles utilisés, confiance, conflit éventuel
- **Scope OUT**: redesign du widget.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/components/header.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser le backend existant plutôt que créer un nouvel endpoint: `/api/llm/judge/run` (run) + `/api/llm/providers/working` (inventaire g4f).
  - S'inspirer du contrat typé Judge (`schemas/judge.py` + `services/judge_builder.py`) si on doit stabiliser les champs affichés côté UI.
  - Remplacer les étapes statiques "GPT-5/Claude/Gemini" par un rendu data-driven (afficher `model/provider` réellement utilisés et la provenance `source[]/fallback`).
- **Acceptation testable**:
  - question judge déclenche un appel API réel et affiche la réponse runtime.
- **Dependencies**: TV-ADV-01

#### Breakdown for `TV-ADV-02` (UI impact first)

##### TV-ADV-02-P - Planner contract and UX states

- **Owner**: planner
- **Objectif**: verrouiller le contrat UI Judge et les états visuels.
- **Scope IN**:
  - définir les états obligatoires: `idle`, `loading`, `success`, `conflict`, `error`, `fallback`
  - mapper les champs API aux zones UI (consensus, confidence, model list, rationale)
- **Scope OUT**: implémentation JS.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/components/header.html`
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Calquer les états sur Judge API: `debug=false` nominal (cache/fast) vs `debug=true` (traces) et exposer `fallback_used` si présent.
  - Garder le contrat minimal: `consensus`, `confidence`, `models[]`, `reasons[]`, `warnings[]`, `source[]`.
- **Evidence attendue**:
  - table `field -> widget slot -> fallback`.
- **Dependencies**: TV-ADV-01-D2

##### TV-ADV-02-D1 - Dev API call integration

- **Owner**: dev
- **Objectif**: brancher le trigger Judge sur endpoints backend réels.
- **Scope IN**:
  - appel principal `/api/llm/judge/run`
  - appel secondaire `/api/llm/providers/working` pour afficher les providers actifs
  - timeout + erreur réseau + retry léger
- **Scope OUT**: optimisation scoring backend.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser `fetchJson` (TV-ADV-01-D1) pour tous les calls, sans exception.
  - Logger en debug uniquement (console) les champs `model/provider` et `source[]` pour faciliter le support sans bruit en nominal.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - test navigateur réel du widget Judge + capture réseau.
- **Dependencies**: TV-ADV-02-P

##### TV-ADV-02-D2 - Dev visual result rendering

- **Owner**: dev
- **Objectif**: rendre la sortie Judge clairement actionnable dans l’UI.
- **Scope IN**:
  - afficher: consensus, confidence, modèles consultés, raisons clés, conflits éventuels
  - afficher badge `runtime`/`fallback` visible
- **Scope OUT**: redesign du layout global.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/components/header.html`
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser la structure DOM existante (`#judgeQuestion`, `#judgeProcessing`, `#judgeResult`) et enrichir le rendu, pas de nouveau widget.
  - Afficher un badge explicite `runtime|fallback` en se basant sur `source[]` et/ou `warnings[]` (pattern Judge).
- **Commandes de test**:
  - test navigateur réel widget Judge: état vide, chargement, résultat, fallback.
  - snapshots avant/après exécution.
- **Dependencies**: TV-ADV-02-D1

##### TV-ADV-02-T1 - Tester runtime validation

- **Owner**: tester
- **Objectif**: valider le comportement réel du Judge côté UI.
- **Scope IN**:
  - vérification réseau: endpoint Judge réellement appelé
  - vérification UI states: loading/success/error/fallback
  - vérification absence de blocage JS
- **Scope OUT**: test cross-browser complet.
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le contrat /api/judge et le composant widget Judge existant comme source unique du verdict UI.
  - Eviter toute shape parallele de donnees Judge; ajouter seulement des champs compatibles en extension.
  - Valider le wiring runtime avec preuves reseau/console et fallback explicite en cas dindisponibilite provider.
- **Evidence attendue**:
  - capture réseau + captures UI des états critiques + snapshot UI de rendu final.
- **Dependencies**: TV-ADV-02-D2

##### TV-ADV-02-QA1 - QA signoff

- **Owner**: qa
- **Objectif**: valider que le Judge UI apporte un résultat concret utilisateur.
- **Scope IN**:
  - check actionnabilité: un verdict compréhensible + confiance + raison
  - check robustesse: erreur/fallback explicitement visibles
- **Commandes de gate**:
  - `bash scripts/backend_regression_gate.sh --no-live`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/tv-adv-02-<timestamp>.md`
- **Sortie obligatoire**:
  - `VERDICT: PASS|BLOCKED`
  - `BLOCKER_ID: NONE|...`
  - `NEXT_ACTION_UNIQUE: ...`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le contrat /api/judge et le composant widget Judge existant comme source unique du verdict UI.
  - Eviter toute shape parallele de donnees Judge; ajouter seulement des champs compatibles en extension.
  - Valider le wiring runtime avec preuves reseau/console et fallback explicite en cas dindisponibilite provider.
- **Dependencies**: TV-ADV-02-T1

### TV-ADV-03 - Refresh data real path

- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: faire de `refreshData()` un refresh réel (pas simulation).
- **Scope IN**:
  - exécuter des refresh fetch sur endpoints clés
  - mettre à jour `last-updated` avec timestamp backend
- **Scope OUT**: scheduler avancé.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver refreshData() comme orchestrateur unique du refresh global (pas de second declencheur concurrent).
  - Synchroniser refresh UI avec /api/freshness et etats degraded/stale affiches sans ambiguite.
  - Isoler la logique de refresh dans app.js et verifier le parcours complet via preuves de rechargement reel.
- **Acceptation testable**:
  - refresh déclenche des calls API et reflète l’état `fresh/stale/degraded`.
- **Dependencies**: TV1-FRESH-01, TV-ADV-01

#### Breakdown for `TV-ADV-03` (UI concrete refresh)

##### TV-ADV-03-P - Planner refresh scope lock

- **Owner**: planner
- **Objectif**: définir le périmètre refresh strict pour le flux principal.
- **Scope IN**:
  - lister endpoints minimum à rafraîchir:
    - `/api/dashboard/kpis`
    - `/api/forecasts`
    - `/api/news/feed`
    - endpoint décision principal validé
  - définir règles d’ordre/cadence (debounce/cooldown)
- **Scope OUT**: auto-refresh intelligent avancé.
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver refreshData() comme orchestrateur unique du refresh global (pas de second declencheur concurrent).
  - Synchroniser refresh UI avec /api/freshness et etats degraded/stale affiches sans ambiguite.
  - Isoler la logique de refresh dans app.js et verifier le parcours complet via preuves de rechargement reel.
- **Dependencies**: TV-ADV-01-D2

##### TV-ADV-03-D1 - Dev real refresh orchestration

- **Owner**: dev
- **Objectif**: remplacer la simulation `setTimeout` par un pipeline refresh réel.
- **Scope IN**:
  - refresh parallèle contrôlé des endpoints
  - gestion d’état bouton (loading/success/error)
  - arrêt propre des refresh concurrents
- **Scope OUT**: scheduler background permanent.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver refreshData() comme orchestrateur unique du refresh global (pas de second declencheur concurrent).
  - Synchroniser refresh UI avec /api/freshness et etats degraded/stale affiches sans ambiguite.
  - Isoler la logique de refresh dans app.js et verifier le parcours complet via preuves de rechargement reel.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - action manuelle bouton refresh.
- **Dependencies**: TV-ADV-03-P

##### TV-ADV-03-D2 - Dev freshness/degraded visual sync

- **Owner**: dev
- **Objectif**: synchroniser le rendu UI avec les métadonnées de fraîcheur.
- **Scope IN**:
  - mettre à jour `.last-updated` depuis timestamps backend
  - rendre explicite `fresh/stale/degraded` après refresh
- **Scope OUT**: système complet de notifications.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver refreshData() comme orchestrateur unique du refresh global (pas de second declencheur concurrent).
  - Synchroniser refresh UI avec /api/freshness et etats degraded/stale affiches sans ambiguite.
  - Isoler la logique de refresh dans app.js et verifier le parcours complet via preuves de rechargement reel.
- **Dependencies**: TV-ADV-03-D1, TV-ADV-04

##### TV-ADV-03-T1 - Tester refresh flow validation

- **Owner**: tester
- **Objectif**: valider le refresh réel et son impact visible UI.
- **Scope IN**:
  - vérifier appels réseau déclenchés au click
  - vérifier changement visible de timestamps
  - vérifier cas erreur endpoint (degraded visible)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver refreshData() comme orchestrateur unique du refresh global (pas de second declencheur concurrent).
  - Synchroniser refresh UI avec /api/freshness et etats degraded/stale affiches sans ambiguite.
  - Isoler la logique de refresh dans app.js et verifier le parcours complet via preuves de rechargement reel.
- **Evidence attendue**:
  - capture réseau + captures UI avant/après refresh (test navigateur réel requis) + snapshot(s) sur états nominal/degraded.
- **Dependencies**: TV-ADV-03-D2

##### TV-ADV-03-QA1 - QA signoff refresh

- **Owner**: qa
- **Objectif**: signer la fiabilité du refresh côté expérience utilisateur.
- **Scope IN**:
  - valider absence de faux “Data refreshed successfully”
  - valider cohérence entre données affichées et état fraîcheur
- **Commandes de gate**:
  - `bash scripts/backend_regression_gate.sh --no-live`
  - `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/tv-adv-03-<timestamp>.md`
- **Sortie obligatoire**:
  - `VERDICT: PASS|BLOCKED`
  - `BLOCKER_ID: NONE|...`
  - `NEXT_ACTION_UNIQUE: ...`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver refreshData() comme orchestrateur unique du refresh global (pas de second declencheur concurrent).
  - Synchroniser refresh UI avec /api/freshness et etats degraded/stale affiches sans ambiguite.
  - Isoler la logique de refresh dans app.js et verifier le parcours complet via preuves de rechargement reel.
- **Dependencies**: TV-ADV-03-T1

### TV-ADV-04 - Real `/api/freshness` computation

- **Epic**: Epic 1 - Data Freshness Foundation
- **Objectif**: remplacer le placeholder `/api/freshness` par un calcul réel.
- **Scope IN**:
  - calculer les âges depuis snapshots/stores (`forecasts`, `news_feed`, `stocks/prices`, `brief`)
  - retourner SLA verdict exploitable pour gate
- **Scope OUT**: observabilité externe cloud.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/services/snapshot_loader.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FRESHNESS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser `storage.io.load_json("<key>")` et les helpers timestamp (ex: `_to_utc_iso`) au lieu de chemins absolus.
  - Harmoniser les clés de fraîcheur avec Judge (`generated_at`, `freshness`, `last_update`, `data_timestamps`) pour que le frontend puisse afficher `fresh/stale/degraded` sans logique spéciale.
- **Acceptation testable**:
  - `/api/freshness` ne retourne plus de valeurs statiques codées en dur.
- **Dependencies**: TV1-FRESH-03

### TV-ADV-05 - Persisted copilot history

- **Epic**: Epic 5 - Ask Copilot Deep Analysis
- **Objectif**: supprimer le mock d’historique et persister les conversations.
- **Scope IN**:
  - stocker l’historique minimal des Q/A + métadonnées sources
  - `GET /api/copilot/history` renvoie données persistées
- **Scope OUT**: système complet de sessions multi-utilisateur.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/research/versioned_notes.py` (ou storage dédié)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil COPILOT-HISTORY (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser le pattern "never-empty + source[] + generated_at" (Judge) pour éviter de casser le frontend quand l'historique est vide.
  - Stockage: préférer une solution déjà présente (ex: `versioned_notes.py` ou `storage.io`) plutôt qu'une nouvelle DB.
- **Acceptation testable**:
  - plus de `mock_conv_*` dans la réponse normale.
- **Dependencies**: TV5-ASK-01

### TV-ADV-06 - KPI endpoint consolidation

- **Epic**: Tech quality enabler
- **Objectif**: éliminer la duplication de logique KPI.
- **Scope IN**:
  - choisir une source unique pour `/api/dashboard/kpis`
  - documenter et aligner le contrat payload
- **Scope OUT**: refonte complète des autres routes dashboard.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/market_data/api/dashboard.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil KPI-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser un seul module (source of truth) et faire pointer l'autre vers lui (import/adapter), plutôt que maintenir 2 implémentations divergentes.
  - Garder l'enveloppe `ok/data` et exposer `generated_at` + `source[]` pour que l'UI puisse tracer l'origine (pattern Judge).
  - Corriger explicitement la duplication de route `/api/dashboard/kpis` (priorite au chemin unique) et sécuriser la route modulaire avant activation (import `load_json` + contrat identique au chemin retenu).
- **Acceptation testable**:
  - un seul chemin de vérité pour KPI, sans divergence de contrat.
- **Dependencies**: TV-ADV-01

### TV-ADV-07 - Decision brief aggregator endpoint

- **Epic**: Epic 4 + Epic 3 bridge
- **Objectif**: exposer un endpoint unique “quoi faire aujourd’hui”.
- **Scope IN**:
  - créer `/api/decision/brief` (ou équivalent) combinant:
    - signaux
    - top risques
    - contexte
    - action résumée
- **Scope OUT**: moteur stratégique long-terme.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py` ou `apps/api/src/domains/forecasts/api/recommendations.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-BRIEF (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les briques existantes au lieu d'appeler des providers LLM directement:
    - signaux/forecasts existants,
    - `GET /api/news/feed` normalisé,
    - Judge (`GET /api/judge` ou `POST /api/llm/judge/run` selon contrat UI).
  - Structurer la réponse comme Judge: `action`, `confidence`, `why[]`, `risks[]`, `source[]`, `generated_at`, `freshness`, `warnings[]`.
  - Utiliser `core/ticker_normalization.py` pour toute liste de tickers (éviter des alias divergents entre modules).
  - Remplacer les chemins `brief` qui peuvent lever `HTTPException` par un endpoint agrégateur never-empty (`/api/decision/brief` + alias legacy si nécessaire) pour éviter une rupture UI.
- **Acceptation testable**:
  - réponse actionnable en un appel pour le frontend 2-3 clics.
- **Dependencies**: TV2-SIGNAL-03, TV3-JUDGE-02

### TV-ADV-08 - API test coverage expansion

- **Epic**: Cross-epic quality gate
- **Objectif**: couvrir endpoints décision non testés.
- **Scope IN**:
  - tests pour:
    - `/api/freshness`
    - `/api/copilot/ask` et `/api/copilot/history`
    - `/api/dashboard/kpis`
    - `/api/intelligence/snapshot`
    - `/api/context/current`
    - `/api/signals/composite`
    - `/api/forecasts`
- **Scope OUT**: test perf massif.
- **Fichiers cibles**:
  - `apps/api/tests/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil TEST-COVERAGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Standardiser les assertions shape via le pattern Judge: vérifier `ok`, `data`, `generated_at`, `source[]`, et accepter `warnings[]` sans fail.
  - Garder les tests offline-friendly (pas d'appels externes requis).
- **Acceptation testable**:
  - nouvelles suites passent et protègent les contrats principaux.
- **Dependencies**: TV-ADV-04, TV-ADV-05, TV-ADV-06, TV-ADV-07

### TV-ADV-09 - Deprecation cleanup pack

- **Epic**: Tech quality enabler
- **Objectif**: réduire warnings de dépréciation qui masquent les vrais risques.
- **Scope IN**:
  - migration `@app.on_event` -> lifespan
  - migration `datetime.utcnow()` -> timezone-aware UTC
  - migration pydantic v1 (`@validator`, `max_items`, `Field(...example=...)`)
- **Scope OUT**: migration framework majeure.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
  - `apps/api/src/schemas/judge.py`
  - `apps/api/src/domains/market_data/api/portfolios.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Préserver le contrat Judge (schémas + builder) pendant la migration: aucune rename de champs sans alias + tests.
  - Réutiliser les shims de compat déjà présents dans `schemas/judge.py` (v1/v2) et faire des changements incrémentaux pour éviter de casser l'environnement runtime.
- **Acceptation testable**:
  - forte baisse des warnings sur `backend_regression_gate --no-live`.
- **Dependencies**: TV-ADV-08

### TV-ADV-10 - Delivery gate upgrade for decision workflow

- **Epic**: Cross-epic quality gate
- **Objectif**: faire échouer la livraison si le workflow décision n’est pas démontré.
- **Scope IN**:
  - enrichir `run_delivery_gate.sh` avec checks:
    - freshness SLA
    - coverage SLA
    - evidence frontend parcours 2-3 clics
- **Scope OUT**: CI/CD cloud complet.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
- `docs/product/scrum/sprint-next.md`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/main.py (_response_cache_*); apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/ttl.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les mêmes métriques que les endpoints exposent déjà (`freshness`, `source[]`, `warnings[]`) plutôt que recalculer dans le gate.
  - Exiger une preuve UI liée aux endpoints réels (Judge/Signals/News/Forecasts), pas une capture d'un état mock.
- **Acceptation testable**:
  - gate bloque explicitement si métriques vision non atteintes.
- **Dependencies**: TV-QA-01, TV-ADV-08

## Changelog (advance tasks)

- 2026-02-26 America/New_York - Added code-audit advance task pack for missing runtime wiring, placeholder removal, tests, and tech debt cleanup.

## Full Epic Decomposition - All Epics (UI-first acceleration)

This section maintains the dispatch-ready task breakdown for Epic 1 to Epic 14.

Execution lens:

- Prioritize tasks that produce visible UI decision value first.
- Keep runtime cost low (g4f/free providers first, fallback explicit).
- Keep each task in 2-4h execution slices with evidence.

Task ID policy:

- One task = one unique ID.
- Headings that start with `T-` or `TV` are reserved for real tasks only.
- Delta/breakdown/notes headings must not start with a task ID.
- Validation command:
  - `sed -nE 's/^#{2,6}[[:space:]]+((T-[A-Z0-9.]+|TV[0-9A-Z-]+)).*/\1/p' docs/product/planning/tasks.md | sort | uniq -cd`
  - expected output: empty (no duplicate IDs).

Forecast-first mandatory overrides (all relevant tasks):

- API requirement:
  - forecast-bearing endpoints must return model/data provenance fields at minimum:
    - `source` (`model|fallback`)
    - `updated_at`
    - calibrated `confidence`
    - explicit degraded/fallback warning when model path is unavailable
- UI requirement:
  - decision cards/brief/ask/judge screens must display forecast values and provenance explicitly
  - hidden fallback behavior is forbidden
- Gate requirement:
  - if a core user flow returns only heuristic/non-data forecast without explicit degraded state -> `VERDICT: BLOCKED`

Forecast API/UI mandatory matrix (execution precision):

- API -> UI mapping (must stay aligned):
  - `/api/forecasts` -> decision cards + daily brief forecast block
  - `/api/decision/brief` -> homepage "quoi faire aujourd hui" panel
  - `/api/judge` -> judge verdict widget
  - `/api/copilot/ask` -> ask answer panel with forecast references
- Required fields (all decision-facing payloads):
  - `direction`, `confidence`, `action`, `horizon`, `why`, `risk_flag`, `updated_at`, `source`, `model_version` (or explicit fallback marker)
- UI rule:
  - each core surface must show forecast values and provenance from real API payload (no nominal mock path)
- QA/Gate rule:
  - any missing API->UI mapping evidence on one core flow = `VERDICT: BLOCKED`

Forecast-first rebaseline on existing tasks (no new IDs):

- `TV2-SIGNAL-01..06`: must output model/data forecast provenance and calibrated confidence
- `TV4-UI-01..07`: must render forecast output + provenance visibly in decision UI
- `TV-ADV-07`: decision brief endpoint must include a primary forecast block from data/model pipeline
- `TV5-ASK-01..06`: answers must reference current forecast payloads, not generic commentary only
- `TV14-SHIP-06`: final go/no-go must fail if forecast-first criteria are unmet
- `TV15-ML-01..06`: canonical data-driven forecasting pipeline track
- `TV16-FF-01..06`: canonical API->UI forecast delivery contract and proof track

UI-first dispatch lane (recommended order):

1. `TV-ADV-01-D2`
2. `TV-ADV-02-D1`
3. `TV-ADV-02-D2`
4. `TV-ADV-03-D1`
5. `TV-ADV-03-D2`
6. `TV-ADV-07`
7. `TV3-JUDGE-04`
8. `TV4-UI-04`
9. `TV5-ASK-03`
10. `TV6-PORT-04`

### Epic 1 - Data Freshness and Signal Reliability Foundation

#### TV1-FRESH-04 - Freshness reason contract

- **Epic**: Epic 1
- **Priority**: P0
- **Objectif**: exposer le `why stale` pour chaque surface clé.
- **Scope IN**:
  - ajouter `stale_reason` et `source_status` sur prices/news/forecasts
  - harmoniser les valeurs (`fresh`, `stale`, `degraded`)
- **Scope OUT**: monitoring externe.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/forecasts/api/forecasts.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/storage/ttl.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/core/path_resolver.py; apps/api/src/platform/main.py (_response_cache_* / _utc_now_iso)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FRESHNESS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser un helper commun de fraicheur (TTL + statut + raison) pour eviter une logique dupliquee entre endpoints et UI.
  - Imposer le contrat minimal commun: freshness_status, stale_reason, source_status, generated_at et warnings[].
  - Propager explicitement letat degraded jusquau frontend (pas de fallback silencieux).
- **Acceptation testable**:
  - aucun endpoint clé sans `freshness_status` + `stale_reason`.
- **Dependencies**: TV1-FRESH-02

#### TV1-FRESH-05 - Frontend freshness bar sync

- **Epic**: Epic 1
- **Priority**: P0
- **Objectif**: refléter la fraîcheur réelle dans la barre/tiles UI.
- **Scope IN**:
  - lier badges et timestamps aux champs backend
  - fallback visuel explicite si `degraded`
- **Scope OUT**: redesign global.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/storage/ttl.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/core/path_resolver.py; apps/api/src/platform/main.py (_response_cache_* / _utc_now_iso)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FRESHNESS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser un helper commun de fraicheur (TTL + statut + raison) pour eviter une logique dupliquee entre endpoints et UI.
  - Imposer le contrat minimal commun: freshness_status, stale_reason, source_status, generated_at et warnings[].
  - Propager explicitement letat degraded jusquau frontend (pas de fallback silencieux).
- **Acceptation testable**:
  - état visuel change correctement entre `fresh/stale/degraded`.
- **Dependencies**: TV1-FRESH-04, TV4-UI-03

#### TV1-FRESH-06 - Freshness regression tests

- **Epic**: Epic 1
- **Priority**: P0
- **Objectif**: verrouiller les contrats de fraîcheur par tests.
- **Scope IN**:
  - tests API pour champs freshness
  - cas stale simulé + cas degraded simulé
- **Scope OUT**: tests de charge.
- **Fichiers cibles**:
  - `apps/api/tests/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/storage/ttl.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/core/path_resolver.py; apps/api/src/platform/main.py (_response_cache_* / _utc_now_iso)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FRESHNESS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser un helper commun de fraicheur (TTL + statut + raison) pour eviter une logique dupliquee entre endpoints et UI.
  - Imposer le contrat minimal commun: freshness_status, stale_reason, source_status, generated_at et warnings[].
  - Propager explicitement letat degraded jusquau frontend (pas de fallback silencieux).
- **Acceptation testable**:
  - tests freshness passent dans le gate backend.
- **Dependencies**: TV1-FRESH-05

### Epic 2 - Forecast Engine (Asset/Sector)

#### TV2-SIGNAL-04 - Signal rationale enrichment

- **Epic**: Epic 2
- **Priority**: P0
- **Objectif**: fournir `why` (max 3 raisons) et `risk_flag` stables pour chaque signal.
- **Scope IN**:
  - enrichir payload signal avec raisons priorisées
  - normaliser `risk_flag` (`low|medium|high`)
- **Scope OUT**: moteur quant avancé.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/platform/legacy/analytics/phases_adapter.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/core/ticker_normalization.py; apps/api/src/domains/forecasts/api/forecasts.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FORECAST-SIGNAL (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser le calcul des signaux dans un service core partage puis exposer via routes, sans dupliquer la logique metier par endpoint.
  - Garder une shape stable (why[], risk_flag, confidence, horizon) avec enums normalisees et fallback deterministe.
  - Brancher les controles de coverage/SLA dans le gate existant scripts/run_delivery_gate.sh plutot quun check parallele.
- **Acceptation testable**:
  - 90%+ des actifs MVP ont `why` non vide et `risk_flag` valide.
- **Dependencies**: TV2-SIGNAL-03

#### TV2-SIGNAL-05 - Horizon calibration rules

- **Epic**: Epic 2
- **Priority**: P0
- **Objectif**: stabiliser short/swing horizon pour éviter signaux incohérents.
- **Scope IN**:
  - règles de cohérence horizon `1-3d` vs `1-2w`
  - fallback neutral explicite en cas conflit de données
- **Scope OUT**: backtesting long terme.
- **Fichiers cibles**:
  - `apps/api/src/platform/legacy/core/`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/platform/legacy/analytics/phases_adapter.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/core/ticker_normalization.py; apps/api/src/domains/forecasts/api/forecasts.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FORECAST-SIGNAL (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser le calcul des signaux dans un service core partage puis exposer via routes, sans dupliquer la logique metier par endpoint.
  - Garder une shape stable (why[], risk_flag, confidence, horizon) avec enums normalisees et fallback deterministe.
  - Brancher les controles de coverage/SLA dans le gate existant scripts/run_delivery_gate.sh plutot quun check parallele.
- **Acceptation testable**:
  - aucun actif sans horizon valide; conflit -> action fallback documentée.
- **Dependencies**: TV2-SIGNAL-04

#### TV2-SIGNAL-06 - Forecast coverage gate

- **Epic**: Epic 2
- **Priority**: P0
- **Objectif**: bloquer la livraison si `Coverage SLA < 90%`.
- **Scope IN**:
  - calcul coverage par cycle sur univers MVP
  - intégrer check coverage dans gate
- **Scope OUT**: dashboard BI externe.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/platform/legacy/analytics/phases_adapter.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/core/ticker_normalization.py; apps/api/src/domains/forecasts/api/forecasts.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FORECAST-SIGNAL (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser le calcul des signaux dans un service core partage puis exposer via routes, sans dupliquer la logique metier par endpoint.
  - Garder une shape stable (why[], risk_flag, confidence, horizon) avec enums normalisees et fallback deterministe.
  - Brancher les controles de coverage/SLA dans le gate existant scripts/run_delivery_gate.sh plutot quun check parallele.
- **Acceptation testable**:
  - gate fail explicite si couverture insuffisante.
- **Dependencies**: TV2-SIGNAL-05, TV-ADV-10

### Epic 3 - Multi-Model Consensus and Judge

#### TV3-JUDGE-01 - Multi-provider opinion collector

- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: collecter au moins 3 avis modèles à coût minimal.
- **Scope IN**:
  - g4f/free providers d’abord
  - format opinion normalisé (`direction`, `confidence`, `rationale`)
- **Scope OUT**: premium provider obligatoire.
- **Fichiers cibles**:
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/judge/application/judge_pipeline.py; apps/api/src/domains/judge/application/judge_builder.py + apps/api/src/schemas/judge.py; apps/api/src/domains/judge/application/g4f_client.py (+ codestral/groq); apps/api/src/platform/legacy/agents/g4f_model_watcher.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le modele Judge existant (services/judge_pipeline.py, judge_builder.py, schemas/judge.py) comme chemin unique.
  - Conserver la chaine de fallback providers et le JSON strict valide avant/apres parsing (aucune seconde shape judge-like).
  - Garantir le contrat frontend stable (final_action, confidence, conflict_mode, risk_note, source[], warnings[]).
- **Acceptation testable**:
  - endpoint Judge inclut liste des avis collectés.
- **Dependencies**: TV2-SIGNAL-03

#### TV3-JUDGE-02 - Judge arbitration contract

- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: produire un verdict unique stable pour le frontend.
- **Scope IN**:
  - contrat `final_action`, `confidence`, `conflict_mode`, `risk_note`
  - règles d’arbitrage déterministes
- **Scope OUT**: optimisation du modèle lui-même.
- **Fichiers cibles**:
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
  - `apps/api/src/schemas/judge.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/judge/application/judge_pipeline.py; apps/api/src/domains/judge/application/judge_builder.py + apps/api/src/schemas/judge.py; apps/api/src/domains/judge/application/g4f_client.py (+ codestral/groq); apps/api/src/platform/legacy/agents/g4f_model_watcher.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le modele Judge existant (services/judge_pipeline.py, judge_builder.py, schemas/judge.py) comme chemin unique.
  - Conserver la chaine de fallback providers et le JSON strict valide avant/apres parsing (aucune seconde shape judge-like).
  - Garantir le contrat frontend stable (final_action, confidence, conflict_mode, risk_note, source[], warnings[]).
- **Acceptation testable**:
  - shape Judge identique sur runs successifs.
- **Dependencies**: TV3-JUDGE-01

#### TV3-JUDGE-03 - Conflict penalty policy

- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: réduire la confiance quand les modèles divergent.
- **Scope IN**:
  - politique explicite de pénalité confiance
  - marquage `conflict_mode=true` quand divergence forte
- **Scope OUT**: calibration financière avancée.
- **Fichiers cibles**:
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/judge/application/judge_pipeline.py; apps/api/src/domains/judge/application/judge_builder.py + apps/api/src/schemas/judge.py; apps/api/src/domains/judge/application/g4f_client.py (+ codestral/groq); apps/api/src/platform/legacy/agents/g4f_model_watcher.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le modele Judge existant (services/judge_pipeline.py, judge_builder.py, schemas/judge.py) comme chemin unique.
  - Conserver la chaine de fallback providers et le JSON strict valide avant/apres parsing (aucune seconde shape judge-like).
  - Garantir le contrat frontend stable (final_action, confidence, conflict_mode, risk_note, source[], warnings[]).
- **Acceptation testable**:
  - cas de divergence testés avec baisse de confiance attendue.
- **Dependencies**: TV3-JUDGE-02

#### TV3-JUDGE-04 - Judge decision card integration

- **Epic**: Epic 3
- **Priority**: P0 (UI)
- **Objectif**: afficher le verdict Judge dans la carte décision principale.
- **Scope IN**:
  - afficher action finale + confiance + conflit + raisons
  - badge `runtime`/`fallback` visible
- **Scope OUT**: redesign de toutes les cartes.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/components/header.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/judge/application/judge_pipeline.py; apps/api/src/domains/judge/application/judge_builder.py + apps/api/src/schemas/judge.py; apps/api/src/domains/judge/application/g4f_client.py (+ codestral/groq); apps/api/src/platform/legacy/agents/g4f_model_watcher.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le modele Judge existant (services/judge_pipeline.py, judge_builder.py, schemas/judge.py) comme chemin unique.
  - Conserver la chaine de fallback providers et le JSON strict valide avant/apres parsing (aucune seconde shape judge-like).
  - Garantir le contrat frontend stable (final_action, confidence, conflict_mode, risk_note, source[], warnings[]).
- **Acceptation testable**:
  - utilisateur voit un verdict Judge actionnable sans ouvrir la console.
- **Dependencies**: TV-ADV-02-D2, TV3-JUDGE-03

#### TV3-JUDGE-05 - Cost guardrails and provider fallback

- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: garder un coût proche de zéro en cas de provider instable.
- **Scope IN**:
  - routage prioritaire providers gratuits
  - fallback provider chain + timeout budget
- **Scope OUT**: observabilité cloud des coûts.
- **Fichiers cibles**:
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/judge/application/judge_pipeline.py; apps/api/src/domains/judge/application/judge_builder.py + apps/api/src/schemas/judge.py; apps/api/src/domains/judge/application/g4f_client.py (+ codestral/groq); apps/api/src/platform/legacy/agents/g4f_model_watcher.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le modele Judge existant (services/judge_pipeline.py, judge_builder.py, schemas/judge.py) comme chemin unique.
  - Conserver la chaine de fallback providers et le JSON strict valide avant/apres parsing (aucune seconde shape judge-like).
  - Garantir le contrat frontend stable (final_action, confidence, conflict_mode, risk_note, source[], warnings[]).
- **Acceptation testable**:
  - Judge répond même avec providers partiellement indisponibles.
- **Dependencies**: TV3-JUDGE-03

#### TV3-JUDGE-06 - Judge quality gate pack

- **Epic**: Epic 3
- **Priority**: P0
- **Objectif**: couvrir Judge via tests et gate dédié.
- **Scope IN**:
  - tests contract + conflict + fallback provider
  - artefact QA PASS/BLOCKED dédié
- **Scope OUT**: benchmark massif.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/judge/application/judge_pipeline.py; apps/api/src/domains/judge/application/judge_builder.py + apps/api/src/schemas/judge.py; apps/api/src/domains/judge/application/g4f_client.py (+ codestral/groq); apps/api/src/platform/legacy/agents/g4f_model_watcher.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil JUDGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le modele Judge existant (services/judge_pipeline.py, judge_builder.py, schemas/judge.py) comme chemin unique.
  - Conserver la chaine de fallback providers et le JSON strict valide avant/apres parsing (aucune seconde shape judge-like).
  - Garantir le contrat frontend stable (final_action, confidence, conflict_mode, risk_note, source[], warnings[]).
- **Acceptation testable**:
  - suites Judge vertes + verdict QA explicite.
- **Dependencies**: TV3-JUDGE-05, TV3-JUDGE-04

### Epic 4 - Decision Cockpit Frontend (2-3 Click Workflow)

#### TV4-UI-04 - Today decision brief screen

- **Epic**: Epic 4
- **Priority**: P1 (UI)
- **Objectif**: écran unique "quoi faire aujourd’hui" en 2-3 clics.
- **Scope IN**:
  - regrouper top actions, risques, contexte, freshness
  - CTA rapides vers actif/secteur
- **Scope OUT**: navigation multi-pages avancée.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/index.html`
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js; apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/contracts/mockData.js (fallback visible)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Sappuyer sur les widgets et loaders existants (app.js, componentLoader.js, composants actuels) sans nouveau framework UI.
  - Creer un adaptateur API par surface (cards/brief/actions) avec etats loading/error/degraded explicites.
  - Preserver le flux 2-3 clics de bout en bout et eviter des chemins async concurrents qui cassent la coherence ecran.
- **Acceptation testable**:
  - flux quotidien complet <=3 clics.
- **Dependencies**: TV-ADV-07, TV-ADV-01-D2

#### TV4-UI-05 - Action panel and quick drill-down

- **Epic**: Epic 4
- **Priority**: P1 (UI)
- **Objectif**: permettre drill-down rapide depuis action globale vers actifs clés.
- **Scope IN**:
  - panneau d’actions priorisées
  - tri par confiance/risque/fraîcheur
- **Scope OUT**: screener avancé.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js; apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/contracts/mockData.js (fallback visible)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Sappuyer sur les widgets et loaders existants (app.js, componentLoader.js, composants actuels) sans nouveau framework UI.
  - Creer un adaptateur API par surface (cards/brief/actions) avec etats loading/error/degraded explicites.
  - Preserver le flux 2-3 clics de bout en bout et eviter des chemins async concurrents qui cassent la coherence ecran.
- **Acceptation testable**:
  - accès au détail d’un actif en 1 clic depuis le brief.
- **Dependencies**: TV4-UI-04

#### TV4-UI-06 - UI performance and caching polish

- **Epic**: Epic 4
- **Priority**: P1
- **Objectif**: rendre l’UI fluide sur refresh fréquent.
- **Scope IN**:
  - cache local léger côté frontend
  - éviter re-renders inutiles sur refresh
- **Scope OUT**: refonte framework.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js; apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/contracts/mockData.js (fallback visible)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Sappuyer sur les widgets et loaders existants (app.js, componentLoader.js, composants actuels) sans nouveau framework UI.
  - Creer un adaptateur API par surface (cards/brief/actions) avec etats loading/error/degraded explicites.
  - Preserver le flux 2-3 clics de bout en bout et eviter des chemins async concurrents qui cassent la coherence ecran.
- **Acceptation testable**:
  - temps perçu refresh UI réduit sans perte de cohérence.
- **Dependencies**: TV4-UI-05, TV-ADV-03-D1

#### TV4-UI-07 - Mobile sanity for daily flow

- **Epic**: Epic 4
- **Priority**: P1
- **Objectif**: garantir usage mobile basique pour brief quotidien.
- **Scope IN**:
  - vérification responsive des cartes décision
  - correction overflow et lisibilité
- **Scope OUT**: app mobile native.
- **Fichiers cibles**:
  - `apps/web/src/platform/style.css`
  - `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js; apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/contracts/mockData.js (fallback visible)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Sappuyer sur les widgets et loaders existants (app.js, componentLoader.js, composants actuels) sans nouveau framework UI.
  - Creer un adaptateur API par surface (cards/brief/actions) avec etats loading/error/degraded explicites.
  - Preserver le flux 2-3 clics de bout en bout et eviter des chemins async concurrents qui cassent la coherence ecran.
- **Acceptation testable**:
  - parcours quotidien complet sur viewport mobile sans blocage.
- **Dependencies**: TV4-UI-06

### Epic 5 - Ask Copilot Deep Analysis

#### TV5-ASK-01 - Ask contract and orchestrator

- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: stabiliser la réponse ask orientée décision.
- **Scope IN**:
  - contrat réponse: `answer`, `action`, `confidence`, `risk_caveat`, `sources`
  - orchestrer collecte signaux + contexte + judge
- **Scope OUT**: mémoire multi-utilisateur.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/copilot/api/copilot.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/copilot/api/copilot.py; apps/api/src/platform/legacy/research/rag_store.py; apps/api/src/platform/legacy/research/llm_client.py; apps/api/src/platform/legacy/research/web_navigator.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ASK (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Orchestrer Ask via les clients/services LLM existants et le contexte RAG en place (pas de pipeline parallele ad-hoc).
  - Standardiser la reponse avec preuves (sources[], evidence, generated_at, warnings[], cost/latency).
  - Relier continuity/history a un stockage unique versionne pour conserver le contexte multi-questions sans divergence.
- **Acceptation testable**:
  - aucune réponse ask sans action + caveat risque.
- **Dependencies**: TV3-JUDGE-02, TV2-SIGNAL-03

#### TV5-ASK-02 - Context pack builder

- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: construire un contexte marché compact et réutilisable.
- **Scope IN**:
  - assembler regime, risques, signaux top, events clés
  - timestamp et fraîcheur explicites dans le contexte
- **Scope OUT**: base vectorielle complète.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/copilot/api/context.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/copilot/api/copilot.py; apps/api/src/platform/legacy/research/rag_store.py; apps/api/src/platform/legacy/research/llm_client.py; apps/api/src/platform/legacy/research/web_navigator.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ASK (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Orchestrer Ask via les clients/services LLM existants et le contexte RAG en place (pas de pipeline parallele ad-hoc).
  - Standardiser la reponse avec preuves (sources[], evidence, generated_at, warnings[], cost/latency).
  - Relier continuity/history a un stockage unique versionne pour conserver le contexte multi-questions sans divergence.
- **Acceptation testable**:
  - contexte ask réutilisable et horodaté.
- **Dependencies**: TV5-ASK-01

#### TV5-ASK-03 - Ask UI panel with evidence slots

- **Epic**: Epic 5
- **Priority**: P1 (UI)
- **Objectif**: afficher réponse ask structurée et actionnable côté UI.
- **Scope IN**:
  - zones séparées: action, pourquoi, risques, sources
  - états loading/error/fallback explicites
- **Scope OUT**: chat complet multi-thread.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/copilot/api/copilot.py; apps/api/src/platform/legacy/research/rag_store.py; apps/api/src/platform/legacy/research/llm_client.py; apps/api/src/platform/legacy/research/web_navigator.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ASK (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Orchestrer Ask via les clients/services LLM existants et le contexte RAG en place (pas de pipeline parallele ad-hoc).
  - Standardiser la reponse avec preuves (sources[], evidence, generated_at, warnings[], cost/latency).
  - Relier continuity/history a un stockage unique versionne pour conserver le contexte multi-questions sans divergence.
- **Acceptation testable**:
  - réponse ask lisible sans ouvrir données brutes.
- **Dependencies**: TV5-ASK-02, TV-ADV-05

#### TV5-ASK-04 - Follow-up and history continuity

- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: garder continuité Q/A pour analyse quotidienne.
- **Scope IN**:
  - historique réel (pas mock)
  - follow-up sur la dernière réponse
- **Scope OUT**: auth multi-device.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/copilot/api/copilot.py; apps/api/src/platform/legacy/research/rag_store.py; apps/api/src/platform/legacy/research/llm_client.py; apps/api/src/platform/legacy/research/web_navigator.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ASK (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Orchestrer Ask via les clients/services LLM existants et le contexte RAG en place (pas de pipeline parallele ad-hoc).
  - Standardiser la reponse avec preuves (sources[], evidence, generated_at, warnings[], cost/latency).
  - Relier continuity/history a un stockage unique versionne pour conserver le contexte multi-questions sans divergence.
- **Acceptation testable**:
  - historique persistant visible en UI.
- **Dependencies**: TV5-ASK-03

#### TV5-ASK-05 - Ask latency and cost budget

- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: maintenir ask pratique en quasi temps réel.
- **Scope IN**:
  - timeout budget par étape
  - fallback réponse partielle si provider lent
- **Scope OUT**: infrastructure distribuée.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/copilot/api/copilot.py; apps/api/src/platform/legacy/research/rag_store.py; apps/api/src/platform/legacy/research/llm_client.py; apps/api/src/platform/legacy/research/web_navigator.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ASK (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Orchestrer Ask via les clients/services LLM existants et le contexte RAG en place (pas de pipeline parallele ad-hoc).
  - Standardiser la reponse avec preuves (sources[], evidence, generated_at, warnings[], cost/latency).
  - Relier continuity/history a un stockage unique versionne pour conserver le contexte multi-questions sans divergence.
- **Acceptation testable**:
  - ask retourne une réponse utile dans un délai acceptable.
- **Dependencies**: TV5-ASK-04

#### TV5-ASK-06 - Ask quality gate coverage

- **Epic**: Epic 5
- **Priority**: P1
- **Objectif**: verrouiller non-régression ask/history.
- **Scope IN**:
  - tests `/api/copilot/ask` + `/api/copilot/history`
  - gate QA avec blocker explicite
- **Scope OUT**: tests charge.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/copilot/api/copilot.py; apps/api/src/platform/legacy/research/rag_store.py; apps/api/src/platform/legacy/research/llm_client.py; apps/api/src/platform/legacy/research/web_navigator.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ASK (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Orchestrer Ask via les clients/services LLM existants et le contexte RAG en place (pas de pipeline parallele ad-hoc).
  - Standardiser la reponse avec preuves (sources[], evidence, generated_at, warnings[], cost/latency).
  - Relier continuity/history a un stockage unique versionne pour conserver le contexte multi-questions sans divergence.
- **Acceptation testable**:
  - tests ask/history verts + artefact gate.
- **Dependencies**: TV5-ASK-05

### Epic 6 - Portfolio Adaptation Layer

#### TV6-PORT-01 - Watchlist profile model

- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: créer un profil watchlist personnel exploitable par recommandations.
- **Scope IN**:
  - structure watchlist prioritaire
  - tags secteur/conviction par actif
- **Scope OUT**: multi-utilisateur.
- **Fichiers cibles**:
  - `apps/api/src/domains/market_data/api/portfolios.py`
  - `apps/api/src/schemas/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/portfolios.py; apps/api/services/portfolio_service.py; apps/api/services/portfolio_performance_service.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil PORTFOLIO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Definir un modele portefeuille canonique reutilise par reranking, digest et cartes UI (single source of truth).
  - Appliquer ladaptation portefeuille en couche post-signal pour eviter un fork du moteur forecast principal.
  - Versionner les parametres/profils persistes et garder des defaults surs pour compatibilite retroactive.
- **Acceptation testable**:
  - création/lecture watchlist fonctionnelle via API.
- **Dependencies**: none

#### TV6-PORT-02 - Risk posture settings

- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: ajouter profil `conservative|neutral|aggressive`.
- **Scope IN**:
  - persistance profil de risque
  - exposition API de lecture/écriture
- **Scope OUT**: optimisation quant sophistiquée.
- **Fichiers cibles**:
  - `apps/api/src/domains/market_data/api/portfolios.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/portfolios.py; apps/api/services/portfolio_service.py; apps/api/services/portfolio_performance_service.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil PORTFOLIO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Definir un modele portefeuille canonique reutilise par reranking, digest et cartes UI (single source of truth).
  - Appliquer ladaptation portefeuille en couche post-signal pour eviter un fork du moteur forecast principal.
  - Versionner les parametres/profils persistes et garder des defaults surs pour compatibilite retroactive.
- **Acceptation testable**:
  - changement de posture modifie les paramètres de décision.
- **Dependencies**: TV6-PORT-01

#### TV6-PORT-03 - Portfolio-aware reranking

- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: reclasser actions recommandées selon watchlist + risque.
- **Scope IN**:
  - score de priorité portfolio-aware
  - exposer top actions adaptées via endpoint
- **Scope OUT**: optimisation de position sizing.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/portfolios.py; apps/api/services/portfolio_service.py; apps/api/services/portfolio_performance_service.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil PORTFOLIO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Definir un modele portefeuille canonique reutilise par reranking, digest et cartes UI (single source of truth).
  - Appliquer ladaptation portefeuille en couche post-signal pour eviter un fork du moteur forecast principal.
  - Versionner les parametres/profils persistes et garder des defaults surs pour compatibilite retroactive.
- **Acceptation testable**:
  - deux profils de risque donnent un top actions différent.
- **Dependencies**: TV6-PORT-02, TV2-SIGNAL-06

#### TV6-PORT-04 - Portfolio action summary card

- **Epic**: Epic 6
- **Priority**: P2 (UI)
- **Objectif**: afficher "ce que je fais aujourd’hui sur mon portefeuille".
- **Scope IN**:
  - carte UI action portfolio (add/hold/reduce)
  - motifs et niveau de risque
- **Scope OUT**: exécution ordre broker.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/portfolios.py; apps/api/services/portfolio_service.py; apps/api/services/portfolio_performance_service.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil PORTFOLIO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Definir un modele portefeuille canonique reutilise par reranking, digest et cartes UI (single source of truth).
  - Appliquer ladaptation portefeuille en couche post-signal pour eviter un fork du moteur forecast principal.
  - Versionner les parametres/profils persistes et garder des defaults surs pour compatibilite retroactive.
- **Acceptation testable**:
  - carte visible et cohérente avec profil utilisateur.
- **Dependencies**: TV6-PORT-03, TV4-UI-05

#### TV6-PORT-05 - Daily portfolio digest

- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: générer un résumé quotidien portfolio compact.
- **Scope IN**:
  - endpoint digest quotidien
  - inclusion des variations critiques + actions proposées
- **Scope OUT**: reporting institutionnel.
- **Fichiers cibles**:
  - `apps/api/src/domains/market_data/api/portfolios.py`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/portfolios.py; apps/api/services/portfolio_service.py; apps/api/services/portfolio_performance_service.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil PORTFOLIO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Definir un modele portefeuille canonique reutilise par reranking, digest et cartes UI (single source of truth).
  - Appliquer ladaptation portefeuille en couche post-signal pour eviter un fork du moteur forecast principal.
  - Versionner les parametres/profils persistes et garder des defaults surs pour compatibilite retroactive.
- **Acceptation testable**:
  - digest disponible en un appel API.
- **Dependencies**: TV6-PORT-04

#### TV6-PORT-06 - Portfolio adaptation QA gate

- **Epic**: Epic 6
- **Priority**: P2
- **Objectif**: valider que l’adaptation portefeuille est stable et traçable.
- **Scope IN**:
  - tests API profil/watchlist/reranking/digest
  - gate QA PASS/BLOCKED dédié
- **Scope OUT**: test perfs massifs.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/portfolios.py; apps/api/services/portfolio_service.py; apps/api/services/portfolio_performance_service.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil PORTFOLIO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Definir un modele portefeuille canonique reutilise par reranking, digest et cartes UI (single source of truth).
  - Appliquer ladaptation portefeuille en couche post-signal pour eviter un fork du moteur forecast principal.
  - Versionner les parametres/profils persistes et garder des defaults surs pour compatibilite retroactive.
- **Acceptation testable**:
  - non-régression validée pour les flux portfolio.
- **Dependencies**: TV6-PORT-05

### Epic 7 - Geopolitical and Macro Impact Radar

#### TV7-MACRO-01 - Geopolitical event ingestion contract

- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: structurer l’entrée des événements géopolitiques impact marché.
- **Scope IN**:
  - contrat `event_type`, `region`, `severity`, `timestamp`, `sources`
  - endpoint d’ingestion/snapshot normalisé
- **Scope OUT**: moteur prédictif complexe.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/copilot/api/context.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/macro.py; apps/api/src/domains/market_data/application/macro_service.py; apps/api/src/platform/legacy/ingestion/macro_derivatives_client.py; apps/api/src/agents/macro_regime_agent.py; apps/api/src/agents/macro_forecast_agent.py; apps/api/src/platform/legacy/analytics/phase3_macro.py; apps/api/src/platform/legacy/core/market_data.py (get_fred_series)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil MACRO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le pipeline ingestion/news existant et normaliser les evenements macro avant impact mapping.
  - Garder un mapping impact deterministe et explicable (event -> assets/sectors -> weight/risk_flag).
  - Injecter loverlay macro comme couche additive de risque sur la recommandation, sans ecraser le signal coeur.
- **Acceptation testable**:
  - les événements critiques sont exposés via un format stable.
- **Dependencies**: TV1-FRESH-01

#### TV7-MACRO-02 - Event-to-asset impact mapping

- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: relier chaque événement aux actifs/secteurs concernés.
- **Scope IN**:
  - mapping impacts: indices, métaux, secteurs, mega-cap
  - score d’impact `low|medium|high`
- **Scope OUT**: corrélations causales avancées.
- **Fichiers cibles**:
  - `apps/api/src/platform/legacy/core/`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/macro.py; apps/api/src/domains/market_data/application/macro_service.py; apps/api/src/platform/legacy/ingestion/macro_derivatives_client.py; apps/api/src/agents/macro_regime_agent.py; apps/api/src/agents/macro_forecast_agent.py; apps/api/src/platform/legacy/analytics/phase3_macro.py; apps/api/src/platform/legacy/core/market_data.py (get_fred_series)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil MACRO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le pipeline ingestion/news existant et normaliser les evenements macro avant impact mapping.
  - Garder un mapping impact deterministe et explicable (event -> assets/sectors -> weight/risk_flag).
  - Injecter loverlay macro comme couche additive de risque sur la recommandation, sans ecraser le signal coeur.
- **Acceptation testable**:
  - un événement retourne une liste d’actifs/secteurs impactés.
- **Dependencies**: TV7-MACRO-01

#### TV7-MACRO-03 - Regime shift flags

- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: signaler rapidement un basculement risk-on/risk-off.
- **Scope IN**:
  - flags `regime_shift`, `risk_mode`, `confidence`
  - intégration au contexte courant (`/api/context/current`)
- **Scope OUT**: modèle macro complet.
- **Fichiers cibles**:
  - `apps/api/src/domains/copilot/api/context.py`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/macro.py; apps/api/src/domains/market_data/application/macro_service.py; apps/api/src/platform/legacy/ingestion/macro_derivatives_client.py; apps/api/src/agents/macro_regime_agent.py; apps/api/src/agents/macro_forecast_agent.py; apps/api/src/platform/legacy/analytics/phase3_macro.py; apps/api/src/platform/legacy/core/market_data.py (get_fred_series)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil MACRO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le pipeline ingestion/news existant et normaliser les evenements macro avant impact mapping.
  - Garder un mapping impact deterministe et explicable (event -> assets/sectors -> weight/risk_flag).
  - Injecter loverlay macro comme couche additive de risque sur la recommandation, sans ecraser le signal coeur.
- **Acceptation testable**:
  - présence d’un flag de régime exploitable par UI et Ask.
- **Dependencies**: TV7-MACRO-02

#### TV7-MACRO-04 - Macro risk strip in decision UI

- **Epic**: Epic 7
- **Priority**: P2 (UI)
- **Objectif**: afficher les 3 risques macro/géo dominants dans le cockpit.
- **Scope IN**:
  - bandeau risques avec sévérité + timestamp
  - lien direct vers actifs/secteurs impactés
- **Scope OUT**: page macro dédiée complète.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/macro.py; apps/api/src/domains/market_data/application/macro_service.py; apps/api/src/platform/legacy/ingestion/macro_derivatives_client.py; apps/api/src/agents/macro_regime_agent.py; apps/api/src/agents/macro_forecast_agent.py; apps/api/src/platform/legacy/analytics/phase3_macro.py; apps/api/src/platform/legacy/core/market_data.py (get_fred_series)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil MACRO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le pipeline ingestion/news existant et normaliser les evenements macro avant impact mapping.
  - Garder un mapping impact deterministe et explicable (event -> assets/sectors -> weight/risk_flag).
  - Injecter loverlay macro comme couche additive de risque sur la recommandation, sans ecraser le signal coeur.
- **Acceptation testable**:
  - l’utilisateur voit immédiatement les risques macro utiles à la décision.
- **Dependencies**: TV7-MACRO-03, TV4-UI-04

#### TV7-MACRO-05 - Macro-aware recommendation adjustments

- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: ajuster recommandations en fonction du risque macro actif.
- **Scope IN**:
  - pénaliser les actions agressives en mode risk-off
  - injecter caveat macro dans `decision brief`
- **Scope OUT**: allocation portefeuille automatique.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/macro.py; apps/api/src/domains/market_data/application/macro_service.py; apps/api/src/platform/legacy/ingestion/macro_derivatives_client.py; apps/api/src/agents/macro_regime_agent.py; apps/api/src/agents/macro_forecast_agent.py; apps/api/src/platform/legacy/analytics/phase3_macro.py; apps/api/src/platform/legacy/core/market_data.py (get_fred_series)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil MACRO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le pipeline ingestion/news existant et normaliser les evenements macro avant impact mapping.
  - Garder un mapping impact deterministe et explicable (event -> assets/sectors -> weight/risk_flag).
  - Injecter loverlay macro comme couche additive de risque sur la recommandation, sans ecraser le signal coeur.
- **Acceptation testable**:
  - changement de régime modifie action/confiance sur le brief.
- **Dependencies**: TV7-MACRO-04, TV-ADV-07

#### TV7-MACRO-06 - Macro radar QA gate

- **Epic**: Epic 7
- **Priority**: P2
- **Objectif**: verrouiller la fiabilité du radar macro/géo.
- **Scope IN**:
  - tests API ingestion/mapping/flags
  - gate QA avec preuves UI risk strip
- **Scope OUT**: test perfs large-scale.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/macro.py; apps/api/src/domains/market_data/application/macro_service.py; apps/api/src/platform/legacy/ingestion/macro_derivatives_client.py; apps/api/src/agents/macro_regime_agent.py; apps/api/src/agents/macro_forecast_agent.py; apps/api/src/platform/legacy/analytics/phase3_macro.py; apps/api/src/platform/legacy/core/market_data.py (get_fred_series)
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil MACRO (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Reutiliser le pipeline ingestion/news existant et normaliser les evenements macro avant impact mapping.
  - Garder un mapping impact deterministe et explicable (event -> assets/sectors -> weight/risk_flag).
  - Injecter loverlay macro comme couche additive de risque sur la recommandation, sans ecraser le signal coeur.
- **Acceptation testable**:
  - verdict PASS/BLOCKED explicite sur le flux macro.
- **Dependencies**: TV7-MACRO-05

### Epic 8 - Cost Governance and Runtime Efficiency

#### TV8-COST-01 - Provider routing policy (free-first)

- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: forcer un routage low-cost par défaut sur tout flux IA.
- **Scope IN**:
  - ordre de priorité providers gratuits
  - fallback contrôlé vers options payantes seulement si nécessaire
- **Scope OUT**: billing multi-tenant.
- **Fichiers cibles**:
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/application/g4f_client.py; apps/api/src/platform/legacy/agents/g4f_model_watcher.py; apps/api/src/platform/legacy/analytics/econ_llm_agent.py; apps/api/src/platform/legacy/research/llm_client.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil COST-GOV (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser routing providers, budget tokens et timeouts dans un service partage (politique free-first unique).
  - Appliquer la meme politique circuit-breaker a Judge/Ask pour eviter des comportements divergents par feature.
  - Exposer en UI des indicateurs cout/degrade alignes avec le contrat backend (source[], warnings[], fallback_used).
- **Acceptation testable**:
  - appels IA passent d’abord par la chaîne low-cost.
- **Dependencies**: TV3-JUDGE-05, TV5-ASK-05

#### TV8-COST-02 - Request/token budget metering

- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: mesurer le coût par endpoint critique (Judge/Ask/Brief).
- **Scope IN**:
  - métriques `requests`, `estimated_tokens`, `estimated_cost`
  - export local journalier
- **Scope OUT**: facturation provider réelle.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `scripts/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/application/g4f_client.py; apps/api/src/platform/legacy/agents/g4f_model_watcher.py; apps/api/src/platform/legacy/analytics/econ_llm_agent.py; apps/api/src/platform/legacy/research/llm_client.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil COST-GOV (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser routing providers, budget tokens et timeouts dans un service partage (politique free-first unique).
  - Appliquer la meme politique circuit-breaker a Judge/Ask pour eviter des comportements divergents par feature.
  - Exposer en UI des indicateurs cout/degrade alignes avec le contrat backend (source[], warnings[], fallback_used).
- **Acceptation testable**:
  - rapport coût journalier disponible localement.
- **Dependencies**: TV8-COST-01

#### TV8-COST-03 - Timeout and circuit-breaker policy

- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: éviter blocage UX si providers instables.
- **Scope IN**:
  - timeout budget par endpoint
  - circuit-breaker avec fallback réponse partielle
- **Scope OUT**: orchestration distribuée.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/judge/application/judge_pipeline.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/application/g4f_client.py; apps/api/src/platform/legacy/agents/g4f_model_watcher.py; apps/api/src/platform/legacy/analytics/econ_llm_agent.py; apps/api/src/platform/legacy/research/llm_client.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil COST-GOV (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser routing providers, budget tokens et timeouts dans un service partage (politique free-first unique).
  - Appliquer la meme politique circuit-breaker a Judge/Ask pour eviter des comportements divergents par feature.
  - Exposer en UI des indicateurs cout/degrade alignes avec le contrat backend (source[], warnings[], fallback_used).
- **Acceptation testable**:
  - UI reçoit toujours une réponse exploitable, même en dégradé.
- **Dependencies**: TV8-COST-02

#### TV8-COST-04 - Runtime cost/degraded badge in UI

- **Epic**: Epic 8
- **Priority**: P1 (UI)
- **Objectif**: rendre visible l’état runtime/cost pour éviter décisions aveugles.
- **Scope IN**:
  - badge global `runtime_ok | degraded | fallback`
  - indication coût relatif (`low/medium/high`) par réponse IA
- **Scope OUT**: dashboard finance complet.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/application/g4f_client.py; apps/api/src/platform/legacy/agents/g4f_model_watcher.py; apps/api/src/platform/legacy/analytics/econ_llm_agent.py; apps/api/src/platform/legacy/research/llm_client.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil COST-GOV (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser routing providers, budget tokens et timeouts dans un service partage (politique free-first unique).
  - Appliquer la meme politique circuit-breaker a Judge/Ask pour eviter des comportements divergents par feature.
  - Exposer en UI des indicateurs cout/degrade alignes avec le contrat backend (source[], warnings[], fallback_used).
- **Acceptation testable**:
  - état runtime et niveau coût visibles sans debug console.
- **Dependencies**: TV8-COST-03, TV5-ASK-03

#### TV8-COST-05 - Monthly cost guardrail report

- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: contrôler budget mensuel sans outils externes coûteux.
- **Scope IN**:
  - rapport mensuel local consolidé
  - seuils d’alerte (`soft_limit`, `hard_limit`)
- **Scope OUT**: intégration SaaS FinOps.
- **Fichiers cibles**:
  - `scripts/`
  - `docs/ops/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/application/g4f_client.py; apps/api/src/platform/legacy/agents/g4f_model_watcher.py; apps/api/src/platform/legacy/analytics/econ_llm_agent.py; apps/api/src/platform/legacy/research/llm_client.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil COST-GOV (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser routing providers, budget tokens et timeouts dans un service partage (politique free-first unique).
  - Appliquer la meme politique circuit-breaker a Judge/Ask pour eviter des comportements divergents par feature.
  - Exposer en UI des indicateurs cout/degrade alignes avec le contrat backend (source[], warnings[], fallback_used).
- **Acceptation testable**:
  - dépassement seuil remonte alerte explicite.
- **Dependencies**: TV8-COST-04

#### TV8-COST-06 - Cost governance gate

- **Epic**: Epic 8
- **Priority**: P1
- **Objectif**: bloquer livraison si contraintes coût/runtime non tenues.
- **Scope IN**:
  - checks coût, fallback rate, timeout rate
  - verdict PASS/BLOCKED dans gate final
- **Scope OUT**: arbitrage business long terme.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/judge/application/g4f_client.py; apps/api/src/platform/legacy/agents/g4f_model_watcher.py; apps/api/src/platform/legacy/analytics/econ_llm_agent.py; apps/api/src/platform/legacy/research/llm_client.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil COST-GOV (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser routing providers, budget tokens et timeouts dans un service partage (politique free-first unique).
  - Appliquer la meme politique circuit-breaker a Judge/Ask pour eviter des comportements divergents par feature.
  - Exposer en UI des indicateurs cout/degrade alignes avec le contrat backend (source[], warnings[], fallback_used).
- **Acceptation testable**:
  - gate échoue explicitement en cas de dérive coût.
- **Dependencies**: TV8-COST-05, TV-ADV-10

### Epic 9 - Decision Journal and Learning Loop

#### TV9-LOOP-01 - Decision journal schema

- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: définir le format de journal de décision quotidien.
- **Scope IN**:
  - champs `decision_id`, `date`, `action`, `confidence`, `why`, `risk`, `sources`
  - persistance locale simple
- **Scope OUT**: analytics avancées.
- **Fichiers cibles**:
  - `apps/api/src/domains/market_data/api/portfolios.py`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/research/versioned_notes.py; apps/api/src/platform/legacy/storage/io.py; apps/api/src/platform/legacy/core/path_resolver.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil LEARNING-LOOP (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un journal append-only avec snapshot decision immuable et mises a jour outcomes separees.
  - Brancher lauto-capture depuis le daily brief via une API decriture unique (pas decritures directes dispersees).
  - Calculer les ponderations de feedback sur agregats journalises, sans mutation destructive des payloads dorigine.
- **Acceptation testable**:
  - chaque daily brief peut être enregistré avec ID unique.
- **Dependencies**: TV-ADV-07

#### TV9-LOOP-02 - Auto-capture from daily brief

- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: créer l’entrée journal automatiquement après génération du brief.
- **Scope IN**:
  - hook sur endpoint décision
  - marquage de provenance (`manual` vs `auto`)
- **Scope OUT**: workflow multi-user.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/forecasts/api/recommendations.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/research/versioned_notes.py; apps/api/src/platform/legacy/storage/io.py; apps/api/src/platform/legacy/core/path_resolver.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil LEARNING-LOOP (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un journal append-only avec snapshot decision immuable et mises a jour outcomes separees.
  - Brancher lauto-capture depuis le daily brief via une API decriture unique (pas decritures directes dispersees).
  - Calculer les ponderations de feedback sur agregats journalises, sans mutation destructive des payloads dorigine.
- **Acceptation testable**:
  - une décision quotidienne crée une entrée journal sans action manuelle.
- **Dependencies**: TV9-LOOP-01

#### TV9-LOOP-03 - Outcome tracking (simple P/L proxy)

- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: mesurer ex-post la qualité des décisions.
- **Scope IN**:
  - suivi simple `outcome_1d`, `outcome_1w`
  - statut `good/neutral/bad` basé sur règle explicite
- **Scope OUT**: attribution factorielle complexe.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/research/versioned_notes.py; apps/api/src/platform/legacy/storage/io.py; apps/api/src/platform/legacy/core/path_resolver.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil LEARNING-LOOP (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un journal append-only avec snapshot decision immuable et mises a jour outcomes separees.
  - Brancher lauto-capture depuis le daily brief via une API decriture unique (pas decritures directes dispersees).
  - Calculer les ponderations de feedback sur agregats journalises, sans mutation destructive des payloads dorigine.
- **Acceptation testable**:
  - chaque entrée journal peut recevoir un outcome court terme.
- **Dependencies**: TV9-LOOP-02, TV2-SIGNAL-05

#### TV9-LOOP-04 - Journal timeline UI

- **Epic**: Epic 9
- **Priority**: P2 (UI)
- **Objectif**: rendre visible l’historique des décisions et outcomes.
- **Scope IN**:
  - timeline décisions (date/action/confiance/outcome)
  - filtre rapide actif/secteur
- **Scope OUT**: dashboard BI complet.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/index.html`
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/research/versioned_notes.py; apps/api/src/platform/legacy/storage/io.py; apps/api/src/platform/legacy/core/path_resolver.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil LEARNING-LOOP (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un journal append-only avec snapshot decision immuable et mises a jour outcomes separees.
  - Brancher lauto-capture depuis le daily brief via une API decriture unique (pas decritures directes dispersees).
  - Calculer les ponderations de feedback sur agregats journalises, sans mutation destructive des payloads dorigine.
- **Acceptation testable**:
  - l’utilisateur peut revoir ses décisions passées en 1-2 clics.
- **Dependencies**: TV9-LOOP-03

#### TV9-LOOP-05 - Feedback weighting for next recommendations

- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: ajuster légèrement la confiance future selon historique outcomes.
- **Scope IN**:
  - pondération simple positive/négative
  - trace de l’ajustement dans le brief
- **Scope OUT**: apprentissage ML full auto.
- **Fichiers cibles**:
  - `apps/api/src/platform/legacy/core/`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/research/versioned_notes.py; apps/api/src/platform/legacy/storage/io.py; apps/api/src/platform/legacy/core/path_resolver.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil LEARNING-LOOP (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un journal append-only avec snapshot decision immuable et mises a jour outcomes separees.
  - Brancher lauto-capture depuis le daily brief via une API decriture unique (pas decritures directes dispersees).
  - Calculer les ponderations de feedback sur agregats journalises, sans mutation destructive des payloads dorigine.
- **Acceptation testable**:
  - recommendations incluent un ajustement explicable lié au journal.
- **Dependencies**: TV9-LOOP-04

#### TV9-LOOP-06 - Learning loop QA gate

- **Epic**: Epic 9
- **Priority**: P2
- **Objectif**: valider la robustesse de la boucle apprentissage décisionnelle.
- **Scope IN**:
  - tests capture/outcome/feedback
  - gate QA avec preuve timeline UI
- **Scope OUT**: validation statistique avancée.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/research/versioned_notes.py; apps/api/src/platform/legacy/storage/io.py; apps/api/src/platform/legacy/core/path_resolver.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil LEARNING-LOOP (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Utiliser un journal append-only avec snapshot decision immuable et mises a jour outcomes separees.
  - Brancher lauto-capture depuis le daily brief via une API decriture unique (pas decritures directes dispersees).
  - Calculer les ponderations de feedback sur agregats journalises, sans mutation destructive des payloads dorigine.
- **Acceptation testable**:
  - gate PASS/BLOCKED explicite sur boucle de feedback.
- **Dependencies**: TV9-LOOP-05

## Continuous Delivery Loop (until app is basic-ready)

Loop rule:

1. Pick next highest-impact `P0/P1` task from this board only.
2. Execute planner -> dev -> tester -> qa with evidence contract.
3. Run gate and record `PASS|BLOCKED` + `NEXT_ACTION_UNIQUE`.
4. If `BLOCKED`, fix minimal blocker task immediately and rerun gate.
5. Repeat until readiness criteria are fully met.

Basic-ready criteria (minimum functional baseline):

- Mandatory epics PASS: 1, 2, 3, 4, 5, 8, 10, 11, 13, 14, 15, 16.
- Mandatory user flow PASS:
  - open app -> get daily brief in <=3 clicks,
  - forecasts returned by model/data pipeline (not only heuristic fallback),
  - forecast provenance (`source/model_version/updated_at`) visible in UI on core decision surfaces,
  - run Judge and Ask with grounded answers,
  - see freshness/degraded/runtime status clearly,
  - complete gate with no critical blockers.

### Epic 10 - Data Source Reliability and Ingestion Automation

- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil LEARNING-LOOP (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser le modèle Judge (section `Modèle de référence: Judge API`) pour standardiser `ok/data`, `generated_at`, `freshness`, `source[]`, `warnings[]` sur tous les endpoints d'ingestion/health.
  - Réutiliser les briques existantes avant d'ajouter du code:
    - loaders `storage.io.load_json(...)`,
    - normalisation tickers (`core/ticker_normalization.py`),
    - caches TTL déjà utilisés par `stocks/prices` et `news/feed`.
  - Scheduler: privilégier l'orchestration existante (OpenClaw cron + scripts) et garder un circuit-breaker (voir `scripts/orchestration_circuit_breaker.sh`) plutôt que d'introduire un nouveau daemon.

#### TV10-DATA-01 - Source inventory and SLA tiers

- **Epic**: Epic 10
- **Priority**: P1
- **Objectif**: lister les sources critiques et définir leurs SLA de fraîcheur.
- **Scope IN**:
  - inventaire sources prices/news/macro/signals
  - classification `tier1/tier2` + SLA cible
- **Scope OUT**: ajout de nouvelles sources premium.
- **Fichiers cibles**:
  - `docs/ops/`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/src/taxonomy/news_taxonomy.py; apps/api/src/ingestion/finnews.py; apps/api/src/agents/data_harvester.py; apps/api/src/ingestion/massive_client.py; apps/api/src/platform/legacy/storage/io.py; apps/api/services/cache_layer.py; apps/api/src/services/snapshot_loader.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Maintenir un inventaire de sources/SLA central (config unique) consomme par scheduler, ingestion et health endpoints.
  - Normaliser les schemas via adapters partages avant persistance pour eviter des formats par source non compatibles.
  - Faire consommer letat ingestion UI via endpoint dedie, pas via lectures directes de fichiers backend.
- **Acceptation testable**:
  - chaque endpoint critique a une source principale et un fallback identifié.
- **Dependencies**: TV1-FRESH-03

#### TV10-DATA-02 - Ingestion scheduler for core feeds

- **Epic**: Epic 10
- **Priority**: P1
- **Objectif**: automatiser le refresh des feeds core sans action manuelle.
- **Scope IN**:
  - scheduler local pour prices/news/context
  - cadence configurable avec garde-fou anti-thrashing
- **Scope OUT**: orchestration cloud distribuée.
- **Fichiers cibles**:
  - `scripts/`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/src/taxonomy/news_taxonomy.py; apps/api/src/ingestion/finnews.py; apps/api/src/agents/data_harvester.py; apps/api/src/ingestion/massive_client.py; apps/api/src/platform/legacy/storage/io.py; apps/api/services/cache_layer.py; apps/api/src/services/snapshot_loader.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Maintenir un inventaire de sources/SLA central (config unique) consomme par scheduler, ingestion et health endpoints.
  - Normaliser les schemas via adapters partages avant persistance pour eviter des formats par source non compatibles.
  - Faire consommer letat ingestion UI via endpoint dedie, pas via lectures directes de fichiers backend.
- **Acceptation testable**:
  - les feeds core se rafraîchissent automatiquement selon cadence définie.
- **Dependencies**: TV10-DATA-01

#### TV10-DATA-03 - Schema normalization and fallback adapters

- **Epic**: Epic 10
- **Priority**: P1
- **Objectif**: uniformiser les payloads malgré les variations de sources.
- **Scope IN**:
  - normalisation champs indispensables (`updated_at`, `source`, `warnings`)
  - adapters fallback explicites par type de feed
- **Scope OUT**: refonte complète des providers.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/src/taxonomy/news_taxonomy.py; apps/api/src/ingestion/finnews.py; apps/api/src/agents/data_harvester.py; apps/api/src/ingestion/massive_client.py; apps/api/src/platform/legacy/storage/io.py; apps/api/services/cache_layer.py; apps/api/src/services/snapshot_loader.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Maintenir un inventaire de sources/SLA central (config unique) consomme par scheduler, ingestion et health endpoints.
  - Normaliser les schemas via adapters partages avant persistance pour eviter des formats par source non compatibles.
  - Faire consommer letat ingestion UI via endpoint dedie, pas via lectures directes de fichiers backend.
- **Acceptation testable**:
  - aucun endpoint critique ne casse sur un changement mineur de schéma source.
- **Dependencies**: TV10-DATA-02

#### TV10-DATA-04 - Ingestion health endpoint

- **Epic**: Epic 10
- **Priority**: P1
- **Objectif**: exposer un état d’ingestion actionnable pour UI et gate.
- **Scope IN**:
  - endpoint santé ingestion (latence, stale count, erreurs)
  - contrat stable consommable par UI/gate
- **Scope OUT**: monitoring externe SaaS.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/tests/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/src/taxonomy/news_taxonomy.py; apps/api/src/ingestion/finnews.py; apps/api/src/agents/data_harvester.py; apps/api/src/ingestion/massive_client.py; apps/api/src/platform/legacy/storage/io.py; apps/api/services/cache_layer.py; apps/api/src/services/snapshot_loader.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Maintenir un inventaire de sources/SLA central (config unique) consomme par scheduler, ingestion et health endpoints.
  - Normaliser les schemas via adapters partages avant persistance pour eviter des formats par source non compatibles.
  - Faire consommer letat ingestion UI via endpoint dedie, pas via lectures directes de fichiers backend.
- **Acceptation testable**:
  - un appel API retourne l’état ingestion global et par feed.
- **Dependencies**: TV10-DATA-03

#### TV10-DATA-05 - Ingestion status chips in UI

- **Epic**: Epic 10
- **Priority**: P1 (UI)
- **Objectif**: rendre visible l’état des sources directement dans le cockpit.
- **Scope IN**:
  - chips `ok/stale/degraded` par bloc clé
  - détail léger des warnings source
- **Scope OUT**: dashboard observabilité dédié.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/src/taxonomy/news_taxonomy.py; apps/api/src/ingestion/finnews.py; apps/api/src/agents/data_harvester.py; apps/api/src/ingestion/massive_client.py; apps/api/src/platform/legacy/storage/io.py; apps/api/services/cache_layer.py; apps/api/src/services/snapshot_loader.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Maintenir un inventaire de sources/SLA central (config unique) consomme par scheduler, ingestion et health endpoints.
  - Normaliser les schemas via adapters partages avant persistance pour eviter des formats par source non compatibles.
  - Faire consommer letat ingestion UI via endpoint dedie, pas via lectures directes de fichiers backend.
- **Acceptation testable**:
  - l’utilisateur voit immédiatement si une source critique est dégradée.
- **Dependencies**: TV10-DATA-04, TV4-UI-03

#### TV10-DATA-06 - Ingestion reliability QA gate

- **Epic**: Epic 10
- **Priority**: P1
- **Objectif**: bloquer la livraison si l’ingestion n’est pas fiable.
- **Scope IN**:
  - tests ingestion scheduler/normalization/health
  - gate PASS/BLOCKED avec blocker explicite
- **Scope OUT**: tests charge massifs.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/src/taxonomy/news_taxonomy.py; apps/api/src/ingestion/finnews.py; apps/api/src/agents/data_harvester.py; apps/api/src/ingestion/massive_client.py; apps/api/src/platform/legacy/storage/io.py; apps/api/services/cache_layer.py; apps/api/src/services/snapshot_loader.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Maintenir un inventaire de sources/SLA central (config unique) consomme par scheduler, ingestion et health endpoints.
  - Normaliser les schemas via adapters partages avant persistance pour eviter des formats par source non compatibles.
  - Faire consommer letat ingestion UI via endpoint dedie, pas via lectures directes de fichiers backend.
- **Acceptation testable**:
  - gate échoue explicitement si ingestion critique non fiable.
- **Dependencies**: TV10-DATA-05

#### TV10-DATA-07 - Live quality telemetry (no static fixtures)

- **Epic**: Epic 10
- **Priority**: P1
- **Objectif**: remplacer le quality monitor statique par des mesures runtime réelles.
- **Scope IN**:
  - `/api/quality/checks` basé sur probes réels (`/api/health`, `/api/news/feed`, `/api/forecasts`, `/api/brief/daily`)
  - suppression des timestamps/latences hardcodés
  - statut qualité relié à la fraîcheur réelle des snapshots
- **Scope OUT**: observabilité SaaS externe.
- **Fichiers cibles**:
  - `apps/api/src/domains/judge/api/quality.py`
  - `apps/api/tests/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/services/snapshot_loader.py; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Mesurer en runtime et exposer `source`, `freshness`, `warnings[]` sur les checks qualité.
- **Acceptation testable**:
  - `/api/quality/checks` ne contient plus de dates/latences statiques et reflète l’état réel du backend.
- **Dependencies**: TV10-DATA-05, TV13-OPS-03

### Epic 11 - UX Workflow and Personal Settings Basics

- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/response.py; apps/api/src/services/snapshot_loader.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil INGESTION (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les widgets HTML existants (`apps/web/src/domains/forecasts/components/`) + le loader (`js/utils/componentLoader.js`) au lieu de créer de nouveaux composants.
  - Les features UX doivent se brancher sur les adaptateurs API (`fetchJson`) et afficher les métadonnées backend (`source[]`, `freshness`, `warnings[]`) pour éviter l'illusion "mock".
  - Toute nouvelle UI (drawer/actions/shortcuts) doit préserver les IDs DOM existants quand possible (éviter de casser `app.js`).

#### TV11-UX-01 - Home information architecture lock

- **Epic**: Epic 11
- **Priority**: P1
- **Objectif**: verrouiller la structure du home pour le flux quotidien.
- **Scope IN**:
  - ordre des blocs décision/freshness/risque/ask
  - hiérarchie claire pour usage en 2-3 clics
- **Scope OUT**: redesign visuel complet.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/index.html`
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/pages/index.html; apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UX-FLOW (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver larchitecture frontend existante (widgets + app.js) et limiter les changements a IA/navigation/etat.
  - Centraliser la persistance des preferences utilisateur avec schema versionne + fallback par defaut.
  - Brancher quick actions/raccourcis sur les adaptateurs API existants, sans dupliquer les chemins reseau.
- **Acceptation testable**:
  - parcours quotidien est lisible sans friction.
- **Dependencies**: TV4-UI-03

#### TV11-UX-02 - Watchlist quick filter strip

- **Epic**: Epic 11
- **Priority**: P1 (UI)
- **Objectif**: filtrer rapidement les cartes sur watchlist et secteurs prioritaires.
- **Scope IN**:
  - bande de filtres rapides watchlist/secteurs
  - interaction en un clic
- **Scope OUT**: screener avancé multi-critères.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/platform/style.css`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/pages/index.html; apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UX-FLOW (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver larchitecture frontend existante (widgets + app.js) et limiter les changements a IA/navigation/etat.
  - Centraliser la persistance des preferences utilisateur avec schema versionne + fallback par defaut.
  - Brancher quick actions/raccourcis sur les adaptateurs API existants, sans dupliquer les chemins reseau.
- **Acceptation testable**:
  - passage global -> watchlist en un clic.
- **Dependencies**: TV11-UX-01, TV6-PORT-01

#### TV11-UX-03 - Decision explanation drawer

- **Epic**: Epic 11
- **Priority**: P1 (UI)
- **Objectif**: montrer "pourquoi" sans surcharger la vue principale.
- **Scope IN**:
  - drawer par carte: `why`, `risk`, `sources`
  - états fallback explicites
- **Scope OUT**: documentation financière longue.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/pages/index.html; apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UX-FLOW (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver larchitecture frontend existante (widgets + app.js) et limiter les changements a IA/navigation/etat.
  - Centraliser la persistance des preferences utilisateur avec schema versionne + fallback par defaut.
  - Brancher quick actions/raccourcis sur les adaptateurs API existants, sans dupliquer les chemins reseau.
- **Acceptation testable**:
  - chaque recommandation est explicable en 1 interaction.
- **Dependencies**: TV11-UX-02, TV5-ASK-03

#### TV11-UX-04 - Quick actions and keyboard shortcuts

- **Epic**: Epic 11
- **Priority**: P1
- **Objectif**: accélérer les actions quotidiennes.
- **Scope IN**:
  - actions rapides: refresh, ask, judge, focus watchlist
  - raccourcis clavier basiques
- **Scope OUT**: personnalisation complète des shortcuts.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/pages/index.html; apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UX-FLOW (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver larchitecture frontend existante (widgets + app.js) et limiter les changements a IA/navigation/etat.
  - Centraliser la persistance des preferences utilisateur avec schema versionne + fallback par defaut.
  - Brancher quick actions/raccourcis sur les adaptateurs API existants, sans dupliquer les chemins reseau.
- **Acceptation testable**:
  - actions principales réalisables sans navigation longue.
- **Dependencies**: TV11-UX-03

#### TV11-UX-05 - Personal settings persistence

- **Epic**: Epic 11
- **Priority**: P1
- **Objectif**: mémoriser les préférences utilisateur essentielles.
- **Scope IN**:
  - persister filtres, densité UI, préférences horizon
  - restore automatique au chargement
- **Scope OUT**: comptes multi-utilisateurs.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/api/src/domains/market_data/api/portfolios.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/pages/index.html; apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UX-FLOW (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver larchitecture frontend existante (widgets + app.js) et limiter les changements a IA/navigation/etat.
  - Centraliser la persistance des preferences utilisateur avec schema versionne + fallback par defaut.
  - Brancher quick actions/raccourcis sur les adaptateurs API existants, sans dupliquer les chemins reseau.
- **Acceptation testable**:
  - préférences conservées entre sessions.
- **Dependencies**: TV11-UX-04

#### TV11-UX-06 - UX workflow QA gate

- **Epic**: Epic 11
- **Priority**: P1
- **Objectif**: valider que le flux UX quotidien est réellement rapide.
- **Scope IN**:
  - mesure clicks/time sur scénarios principaux
  - preuves UI avant/après + gate verdict
- **Scope OUT**: tests UX exploratoires étendus.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/domains/forecasts/pages/app.js; apps/web/src/domains/forecasts/pages/index.html; apps/web/src/domains/forecasts/components/*; apps/web/src/platform/js
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil UX-FLOW (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver larchitecture frontend existante (widgets + app.js) et limiter les changements a IA/navigation/etat.
  - Centraliser la persistance des preferences utilisateur avec schema versionne + fallback par defaut.
  - Brancher quick actions/raccourcis sur les adaptateurs API existants, sans dupliquer les chemins reseau.
- **Acceptation testable**:
  - test quotidien <=3 clics et temps cible respecté.
- **Dependencies**: TV11-UX-05

### Epic 12 - Alerts and Daily Automation

#### TV12-ALRT-01 - Alert rule schema v1

- **Epic**: Epic 12
- **Priority**: P1
- **Objectif**: définir des règles d’alerte simples mais robustes.
- **Scope IN**:
  - schéma règle: type, seuil, horizon, priorité, mute
  - stockage local des règles
- **Scope OUT**: alerting multi-canal externe.
- **Fichiers cibles**:
  - `apps/api/src/domains/market_data/api/alerts.py`
  - `apps/api/src/schemas/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/alerts.py; apps/api/src/domains/market_data/application/alert_rules.py; apps/api/services/alert_rules.py; apps/api/models/alert_configuration.py; apps/api/src/research/alerts.py; apps/web/src/domains/forecasts/components/alerts-timeline.html
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ALERTING (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Versionner et valider le schema de regles dalerte au backend avant execution moteur.
  - Utiliser des cles de deduplication deterministes communes (price/news/regime) pour eviter alert storms.
  - Partager un payload alerte unique entre moteur, digest quotidien et UI Alert Center.
- **Acceptation testable**:
  - création/édition/suppression de règles via API.
- **Dependencies**: TV2-SIGNAL-03

#### TV12-ALRT-02 - Trigger engine (price/news/regime)

- **Epic**: Epic 12
- **Priority**: P1
- **Objectif**: déclencher alertes sur signaux réellement utiles.
- **Scope IN**:
  - déclencheurs prix, news sentiment, regime shift
  - anti-spam simple (cooldown par règle)
- **Scope OUT**: scoring ML avancé.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/alerts.py; apps/api/src/domains/market_data/application/alert_rules.py; apps/api/services/alert_rules.py; apps/api/models/alert_configuration.py; apps/api/src/research/alerts.py; apps/web/src/domains/forecasts/components/alerts-timeline.html
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ALERTING (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Versionner et valider le schema de regles dalerte au backend avant execution moteur.
  - Utiliser des cles de deduplication deterministes communes (price/news/regime) pour eviter alert storms.
  - Partager un payload alerte unique entre moteur, digest quotidien et UI Alert Center.
- **Acceptation testable**:
  - règles pertinentes déclenchent des alertes observables.
- **Dependencies**: TV12-ALRT-01, TV7-MACRO-03

#### TV12-ALRT-03 - In-app alert center UI

- **Epic**: Epic 12
- **Priority**: P1 (UI)
- **Objectif**: afficher les alertes dans un centre visible et triable.
- **Scope IN**:
  - liste alertes avec priorité/âge/source
  - actions rapides: mark read, snooze
- **Scope OUT**: push mobile/email externe.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/alerts.py; apps/api/src/domains/market_data/application/alert_rules.py; apps/api/services/alert_rules.py; apps/api/models/alert_configuration.py; apps/api/src/research/alerts.py; apps/web/src/domains/forecasts/components/alerts-timeline.html
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ALERTING (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Versionner et valider le schema de regles dalerte au backend avant execution moteur.
  - Utiliser des cles de deduplication deterministes communes (price/news/regime) pour eviter alert storms.
  - Partager un payload alerte unique entre moteur, digest quotidien et UI Alert Center.
- **Acceptation testable**:
  - alertes consultables et actionnables en 1-2 clics.
- **Dependencies**: TV12-ALRT-02, TV11-UX-01

#### TV12-ALRT-04 - Daily digest generator

- **Epic**: Epic 12
- **Priority**: P1
- **Objectif**: générer automatiquement un digest quotidien synthétique.
- **Scope IN**:
  - résumé des alertes + actions proposées du jour
  - endpoint digest dédié
- **Scope OUT**: envoi externe automatique.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/forecasts/api/recommendations.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/alerts.py; apps/api/src/domains/market_data/application/alert_rules.py; apps/api/services/alert_rules.py; apps/api/models/alert_configuration.py; apps/api/src/research/alerts.py; apps/web/src/domains/forecasts/components/alerts-timeline.html
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ALERTING (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Versionner et valider le schema de regles dalerte au backend avant execution moteur.
  - Utiliser des cles de deduplication deterministes communes (price/news/regime) pour eviter alert storms.
  - Partager un payload alerte unique entre moteur, digest quotidien et UI Alert Center.
- **Acceptation testable**:
  - digest disponible quotidiennement via API/UI.
- **Dependencies**: TV12-ALRT-03, TV-ADV-07

#### TV12-ALRT-05 - Alert prioritization and dedupe

- **Epic**: Epic 12
- **Priority**: P1
- **Objectif**: réduire le bruit et remonter seulement l’actionnable.
- **Scope IN**:
  - déduplication règles similaires
  - ranking par urgence/confiance/coût d’inaction
- **Scope OUT**: assistant notification autonome.
- **Fichiers cibles**:
  - `apps/api/src/platform/legacy/core/`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/alerts.py; apps/api/src/domains/market_data/application/alert_rules.py; apps/api/services/alert_rules.py; apps/api/models/alert_configuration.py; apps/api/src/research/alerts.py; apps/web/src/domains/forecasts/components/alerts-timeline.html
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ALERTING (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Versionner et valider le schema de regles dalerte au backend avant execution moteur.
  - Utiliser des cles de deduplication deterministes communes (price/news/regime) pour eviter alert storms.
  - Partager un payload alerte unique entre moteur, digest quotidien et UI Alert Center.
- **Acceptation testable**:
  - baisse des alertes redondantes sans perte des critiques.
- **Dependencies**: TV12-ALRT-04, TV8-COST-03

#### TV12-ALRT-06 - Alerts QA gate

- **Epic**: Epic 12
- **Priority**: P1
- **Objectif**: garantir la fiabilité du système d’alertes.
- **Scope IN**:
  - tests règles/trigger/dedupe/digest
  - preuve UI center + verdict gate
- **Scope OUT**: test charge global.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/run_delivery_gate.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/market_data/api/alerts.py; apps/api/src/domains/market_data/application/alert_rules.py; apps/api/services/alert_rules.py; apps/api/models/alert_configuration.py; apps/api/src/research/alerts.py; apps/web/src/domains/forecasts/components/alerts-timeline.html
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ALERTING (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Versionner et valider le schema de regles dalerte au backend avant execution moteur.
  - Utiliser des cles de deduplication deterministes communes (price/news/regime) pour eviter alert storms.
  - Partager un payload alerte unique entre moteur, digest quotidien et UI Alert Center.
- **Acceptation testable**:
  - gate PASS/BLOCKED explicite pour alertes.
- **Dependencies**: TV12-ALRT-05

### Epic 13 - Reliability, Security, and Backup

#### TV13-OPS-01 - Error catalog and retry policy

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: standardiser la gestion des erreurs critiques.
- **Scope IN**:
  - catalogue erreurs (network/provider/schema/cache)
  - politique retry/backoff par type d’erreur
- **Scope OUT**: plateforme d’observabilité externe.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/sentry_runtime.py; scripts/backend_regression_gate.sh; scripts/run_delivery_gate.sh; docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser catalogue derreurs + politiques retry dans un module commun reutilise par API, jobs et scripts.
  - Imposer trace_id/correlation_id dans logs structures depuis les points dentree jusquaux appels externes.
  - Integrer backup/restore et drills au gate de livraison avec artefacts audites (pas doperations manuelles implicites).
- **Acceptation testable**:
  - erreurs majeures retournent des réponses cohérentes et actionnables.
- **Dependencies**: TV8-COST-03

#### TV13-OPS-02 - Structured logs and trace IDs

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: tracer chaque décision de bout en bout.
- **Scope IN**:
  - trace_id sur endpoints décision
  - logs structurés corrélables frontend/backend
- **Scope OUT**: SIEM enterprise.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `scripts/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/sentry_runtime.py; scripts/backend_regression_gate.sh; scripts/run_delivery_gate.sh; docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser catalogue derreurs + politiques retry dans un module commun reutilise par API, jobs et scripts.
  - Imposer trace_id/correlation_id dans logs structures depuis les points dentree jusquaux appels externes.
  - Integrer backup/restore et drills au gate de livraison avec artefacts audites (pas doperations manuelles implicites).
- **Acceptation testable**:
  - un incident est traçable par `trace_id`.
- **Dependencies**: TV13-OPS-01

#### TV13-OPS-03 - Local backup/restore for critical state

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: protéger l’état critique utilisateur (watchlist, journal, settings).
- **Scope IN**:
  - backup local versionné
  - restore simple par commande/script
- **Scope OUT**: backup cloud managé.
- **Fichiers cibles**:
  - `scripts/`
  - `apps/api/src/domains/market_data/api/portfolios.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/sentry_runtime.py; scripts/backend_regression_gate.sh; scripts/run_delivery_gate.sh; docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser catalogue derreurs + politiques retry dans un module commun reutilise par API, jobs et scripts.
  - Imposer trace_id/correlation_id dans logs structures depuis les points dentree jusquaux appels externes.
  - Integrer backup/restore et drills au gate de livraison avec artefacts audites (pas doperations manuelles implicites).
- **Acceptation testable**:
  - restauration valide après suppression simulée d’état.
- **Dependencies**: TV13-OPS-02

#### TV13-OPS-04 - Config and secrets hygiene

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: sécuriser la gestion des configs sensibles.
- **Scope IN**:
  - séparation claire config runtime vs secrets
  - vérification de variables critiques au boot
- **Scope OUT**: secret manager externe.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `docs/ops/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/sentry_runtime.py; scripts/backend_regression_gate.sh; scripts/run_delivery_gate.sh; docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser catalogue derreurs + politiques retry dans un module commun reutilise par API, jobs et scripts.
  - Imposer trace_id/correlation_id dans logs structures depuis les points dentree jusquaux appels externes.
  - Integrer backup/restore et drills au gate de livraison avec artefacts audites (pas doperations manuelles implicites).
- **Acceptation testable**:
  - boot fail explicite si secret critique manquant.
- **Dependencies**: TV13-OPS-02

#### TV13-OPS-05 - Recovery drill scripts and runbook

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: rendre la récupération opérationnelle et répétable.
- **Scope IN**:
  - scripts de drill (provider down, stale data, restore backup)
  - runbook recovery étape par étape
- **Scope OUT**: PRA multi-région.
- **Fichiers cibles**:
  - `scripts/`
  - `docs/ops/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/sentry_runtime.py; scripts/backend_regression_gate.sh; scripts/run_delivery_gate.sh; docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser catalogue derreurs + politiques retry dans un module commun reutilise par API, jobs et scripts.
  - Imposer trace_id/correlation_id dans logs structures depuis les points dentree jusquaux appels externes.
  - Integrer backup/restore et drills au gate de livraison avec artefacts audites (pas doperations manuelles implicites).
- **Acceptation testable**:
  - drills exécutables avec résultat PASS/BLOCKED.
- **Dependencies**: TV13-OPS-03, TV13-OPS-04

#### TV13-OPS-06 - Reliability/security QA gate

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: verrouiller la robustesse opérationnelle avant release.
- **Scope IN**:
  - gate basé sur drills + logs + backup/restore
  - blocker explicite sur fail critique
- **Scope OUT**: audit sécurité formel externe.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/sentry_runtime.py; scripts/backend_regression_gate.sh; scripts/run_delivery_gate.sh; docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Centraliser catalogue derreurs + politiques retry dans un module commun reutilise par API, jobs et scripts.
  - Imposer trace_id/correlation_id dans logs structures depuis les points dentree jusquaux appels externes.
  - Integrer backup/restore et drills au gate de livraison avec artefacts audites (pas doperations manuelles implicites).
- **Acceptation testable**:
  - gate bloque si récupération/traçabilité insuffisante.
- **Dependencies**: TV13-OPS-05

#### TV13-OPS-07 - Runtime/spec parity watchdog

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: détecter automatiquement les dérives entre la spec d’orchestration et le runtime effectif.
- **Scope IN**:
  - comparaison automatique `ORCHESTRATION_COORDINATION_SPEC` vs `openclaw cron list`
  - alerte BLOCKED si drift persistant (roles manquants, jobs en trop, map role->cron cassée)
- **Scope OUT**: auto-provision complet des jobs.
- **Fichiers cibles**:
  - `scripts/adminapp_codex_cron_tick.sh`
  - `scripts/validate_parallel_plumbing.sh`
  - `docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): docs/ops/ORCHESTRATION_COORDINATION_SPEC.yaml; scripts/validate_parallel_plumbing.sh; scripts/stale_cron_sweep.sh
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Ne pas se limiter au statut `ok`: vérifier aussi le nombre et le mapping des jobs attendus.
- **Acceptation testable**:
  - un drift runtime/spec est détecté automatiquement et remonté avec action de remédiation unique.
- **Dependencies**: TV13-OPS-06

#### TV13-OPS-08 - Stale in-progress auto-reclaim and hygiene

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: éviter les tâches `IN_PROGRESS` orphelines qui bloquent le flux réel.
- **Scope IN**:
  - reclaim/close automatique des `IN_PROGRESS` stale au-delà du SLA
  - publication explicite dans artifacts/gate des tâches reclaimées
- **Scope OUT**: arbitrage produit (reste piloté par PO/planner).
- **Fichiers cibles**:
  - `scripts/parallel_workstream.py`
  - `scripts/admin_agents_tmux_tick.sh`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/parallel_workstream.py; scripts/stale_cron_sweep.sh; docs/orchestrator-ops/parallel-workstreams.json
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Garder une piste d’audit claire (`who reclaimed`, `why`, `previous_state`).
- **Acceptation testable**:
  - plus aucune tâche stale > SLA sans statut explicite (`DONE|BLOCKED|RECLAIMED`).
- **Dependencies**: TV13-OPS-07

#### TV13-OPS-09 - Executable shortlist from mega-board

- **Epic**: Epic 13
- **Priority**: P1
- **Objectif**: réduire la charge cognitive en extrayant une shortlist exécutable quotidienne depuis le board massif.
- **Scope IN**:
  - génération automatique d’un top-15 tâches exécutables (priorité + deps + ready state)
  - publication compacte pour les rôles actifs (planner/dev/tester/qa)
- **Scope OUT**: refonte complète de `tasks.md`.
- **Fichiers cibles**:
  - `scripts/parallel_workstream.py`
  - `docs/orchestrator-ops/parallel-workstreams.json`
  - `docs/product/planning/tasks.md` (section référence shortlist)
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/parallel_workstream.py; docs/orchestrator-ops/priority-queue.json; docs/orchestrator-ops/parallel-workstreams.json
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELIABILITY-OPS (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - La shortlist doit être déterministe et traçable (version queue/workboard incluse).
- **Acceptation testable**:
  - production d’une shortlist stable et actionnable en < 5 secondes.
- **Dependencies**: TV13-OPS-08

### Epic 14 - MVP Release Readiness and Go-Live

#### TV14-SHIP-01 - MVP checklist matrix

- **Epic**: Epic 14
- **Priority**: P1
- **Objectif**: construire une matrice claire des fonctionnalités basiques requises.
- **Scope IN**:
  - checklist par flux (brief, judge, ask, portfolio, alerts)
  - critères pass/fail par flux
- **Scope OUT**: roadmap long terme.
- **Fichiers cibles**:
  - `docs/product/scrum/`
  - `docs/planning/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh; finance-app/openclaw-gates/
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Consolider la checklist release depuis les gates existants (fonctionnel, qualite, cout, perf) sans creer un second referentiel.
  - Executer les scenarios E2E sur le parcours MVP reel avec fixtures reproductibles et preuves versionnees.
  - Relier go/no-go au script de gate commun et pack rollback explicite (run_delivery_gate.sh + artefacts RC).
- **Acceptation testable**:
  - chaque flux basique a des critères mesurables validables.
- **Dependencies**: TV11-UX-06, TV12-ALRT-06

#### TV14-SHIP-02 - End-to-end scenario suite

- **Epic**: Epic 14
- **Priority**: P1
- **Objectif**: exécuter des scénarios complets utilisateur.
- **Scope IN**:
  - scénarios E2E journaliers principaux
  - capture des preuves standardisées
- **Scope OUT**: tests cross-browser exhaustifs.
- **Fichiers cibles**:
  - `scripts/`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh; finance-app/openclaw-gates/
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Consolider la checklist release depuis les gates existants (fonctionnel, qualite, cout, perf) sans creer un second referentiel.
  - Executer les scenarios E2E sur le parcours MVP reel avec fixtures reproductibles et preuves versionnees.
  - Relier go/no-go au script de gate commun et pack rollback explicite (run_delivery_gate.sh + artefacts RC).
- **Acceptation testable**:
  - scénarios E2E passants sur environnement local cible.
- **Dependencies**: TV14-SHIP-01

#### TV14-SHIP-03 - Performance baseline and budget

- **Epic**: Epic 14
- **Priority**: P1
- **Objectif**: garantir une expérience perçue fluide sur flux basiques.
- **Scope IN**:
  - budget latence API + render UI
  - mesures baseline documentées
- **Scope OUT**: optimisation micro benchmark.
- **Fichiers cibles**:
  - `scripts/`
  - `docs/ops/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh; finance-app/openclaw-gates/
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Consolider la checklist release depuis les gates existants (fonctionnel, qualite, cout, perf) sans creer un second referentiel.
  - Executer les scenarios E2E sur le parcours MVP reel avec fixtures reproductibles et preuves versionnees.
  - Relier go/no-go au script de gate commun et pack rollback explicite (run_delivery_gate.sh + artefacts RC).
- **Acceptation testable**:
  - respect budget perf défini pour flux critiques.
- **Dependencies**: TV14-SHIP-02

#### TV14-SHIP-04 - Defect burn-down sprint

- **Epic**: Epic 14
- **Priority**: P1
- **Objectif**: fermer les blockers avant release.
- **Scope IN**:
  - triage bugs critiques/majeurs
  - correction priorisée par impact utilisateur
- **Scope OUT**: refactors non bloquants.
- **Fichiers cibles**:
  - `docs/product/scrum/`
  - `apps/api/`
  - `apps/web/src/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh; finance-app/openclaw-gates/
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Consolider la checklist release depuis les gates existants (fonctionnel, qualite, cout, perf) sans creer un second referentiel.
  - Executer les scenarios E2E sur le parcours MVP reel avec fixtures reproductibles et preuves versionnees.
  - Relier go/no-go au script de gate commun et pack rollback explicite (run_delivery_gate.sh + artefacts RC).
- **Acceptation testable**:
  - aucun bug critique ouvert sur flux basiques.
- **Dependencies**: TV14-SHIP-03

#### TV14-SHIP-05 - Release candidate and rollback pack

- **Epic**: Epic 14
- **Priority**: P1
- **Objectif**: préparer une release candidate réversible rapidement.
- **Scope IN**:
  - paquet release candidate + notes
  - plan rollback en 1 procédure
- **Scope OUT**: déploiement multi-environnements complexe.
- **Fichiers cibles**:
  - `docs/ops/`
  - `scripts/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh; finance-app/openclaw-gates/
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Consolider la checklist release depuis les gates existants (fonctionnel, qualite, cout, perf) sans creer un second referentiel.
  - Executer les scenarios E2E sur le parcours MVP reel avec fixtures reproductibles et preuves versionnees.
  - Relier go/no-go au script de gate commun et pack rollback explicite (run_delivery_gate.sh + artefacts RC).
- **Acceptation testable**:
  - rollback drill exécuté avec succès.
- **Dependencies**: TV14-SHIP-04, TV13-OPS-06

#### TV14-SHIP-06 - Final MVP go/no-go gate

- **Epic**: Epic 14
- **Priority**: P1
- **Objectif**: décider formellement `GO` ou `NO-GO` sur MVP basique.
- **Scope IN**:
  - gate final consolidé (fonctionnel + qualité + coût + perf)
  - verdict signé avec blockers résiduels
- **Scope OUT**: roadmap post-MVP.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh; finance-app/openclaw-gates/
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Consolider la checklist release depuis les gates existants (fonctionnel, qualite, cout, perf) sans creer un second referentiel.
  - Executer les scenarios E2E sur le parcours MVP reel avec fixtures reproductibles et preuves versionnees.
  - Relier go/no-go au script de gate commun et pack rollback explicite (run_delivery_gate.sh + artefacts RC).
- **Acceptation testable**:
  - verdict final clair, auditable, reproductible.
- **Dependencies**: TV14-SHIP-05

#### TV14-SHIP-07 - Technical release gate (non-doc evidence)

- **Epic**: Epic 14
- **Priority**: P1
- **Objectif**: empêcher les faux PASS documentaires en imposant des preuves techniques exécutées.
- **Scope IN**:
  - gate exigeant checks techniques réels (API contract, forecast provenance, smoke backend)
  - blocage si seules preuves textuelles sans exécution
- **Scope OUT**: CI cloud avancée.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `scripts/backend_regression_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh; finance-app/openclaw-gates/
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Vérifier explicitement la présence runtime des champs forecast requis sur endpoints core.
  - Exiger au moins une preuve UI liée au payload API réel (pas seulement une mention narrative).
- **Acceptation testable**:
  - gate retourne `BLOCKED` si les checks techniques ne sont pas exécutés ou ne passent pas.
- **Dependencies**: TV14-SHIP-06, TV16-FF-10, TV13-OPS-07

### Epic 15 - Data-Driven Forecasting Core

#### TV15-ML-01 - Forecast dataset and feature contract

- **Epic**: Epic 15
- **Priority**: P0
- **Objectif**: définir un dataset d’entraînement stable pour prévisions basées sur data réelle.
- **Scope IN**:
  - schéma dataset: `timestamp`, `asset`, `target_horizon`, `label`, `features`
  - feature matrix minimale (price action, volume, volatility, regime, news/macro proxies)
- **Scope OUT**: feature engineering avancé non nécessaire MVP.
- **Fichiers cibles**:
  - `apps/api/src/platform/legacy/core/`
  - `apps/api/data/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/data_access.py; apps/api/src/platform/legacy/core/data_quality.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ML-FORECAST (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les flux ingestion normalisés (Epic 10) pour éviter des datasets ad hoc.
  - Versionner le schéma dataset pour empêcher les breaks silencieux.
  - Conserver le mapping direct vers le contrat signal (`direction/confidence/action`).
- **Acceptation testable**:
  - dataset généré avec schéma validé et coverage sur univers MVP.
- **Dependencies**: TV10-DATA-03, TV2-SIGNAL-01

#### TV15-ML-02 - Training pipeline baseline (reproducible)

- **Epic**: Epic 15
- **Priority**: P0
- **Objectif**: entraîner un modèle baseline reproductible à partir du dataset versionné.
- **Scope IN**:
  - script d’entraînement local reproductible
  - sortie modèle versionnée + métriques minimales
- **Scope OUT**: AutoML et tuning massif.
- **Fichiers cibles**:
  - `scripts/`
  - `apps/api/src/platform/legacy/core/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/data_access.py; apps/api/src/platform/legacy/core/data_quality.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ML-FORECAST (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Garder un pipeline déterministe (seed fixe, split explicite).
  - Produire un artefact modèle local simple (pas d’infra externe requise).
  - Tracer métriques clés utilisées ensuite pour le gate.
- **Acceptation testable**:
  - un run training produit un artefact modèle + métriques auditables.
- **Dependencies**: TV15-ML-01

#### TV15-ML-03 - Walk-forward backtest and robustness checks

- **Epic**: Epic 15
- **Priority**: P0
- **Objectif**: vérifier que les prévisions gardent une robustesse minimale en mode temporel réaliste.
- **Scope IN**:
  - backtest walk-forward sur horizons `1-3d` et `1-2w`
  - métriques robustesse (hit-rate direction, stabilité confidence)
- **Scope OUT**: framework backtest institutionnel complet.
- **Fichiers cibles**:
  - `apps/api/src/platform/legacy/core/`
  - `scripts/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/data_access.py; apps/api/src/platform/legacy/core/data_quality.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ML-FORECAST (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Éviter toute fuite temporelle (train < test strictement).
  - Utiliser les mêmes horizons et actifs que l’univers MVP.
  - Publier les résultats dans un format lisible par gate.
- **Acceptation testable**:
  - rapport backtest généré avec verdict PASS/BLOCKED selon seuils minimaux.
- **Dependencies**: TV15-ML-02

#### TV15-ML-04 - Data-driven inference service for forecasts

- **Epic**: Epic 15
- **Priority**: P0
- **Objectif**: servir des prévisions runtime issues du modèle (pas heuristique seule).
- **Scope IN**:
  - endpoint d’inférence branché au modèle entraîné
  - fallback explicite si modèle indisponible
- **Scope OUT**: serving distribué multi-cluster.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/forecasts/api/forecasts.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/data_access.py; apps/api/src/platform/legacy/core/data_quality.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil FORECAST-SIGNAL (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Conserver contrat API stable (`ok/data`, freshness, source[], warnings[]).
  - Exposer `source=model` vs `source=fallback` de manière explicite.
  - Réutiliser cache TTL existant sans masquer la fraîcheur d’inférence.
- **Acceptation testable**:
  - `/api/forecasts` retourne des sorties model-driven en nominal + fallback visible en dégradé.
- **Dependencies**: TV15-ML-03, TV1-FRESH-01

#### TV15-ML-05 - Confidence calibration and drift guardrails

- **Epic**: Epic 15
- **Priority**: P0
- **Objectif**: calibrer la confiance et détecter la dérive data/modèle.
- **Scope IN**:
  - calibration confidence vers `0-100`
  - checks drift simples (feature drift / degradation signal quality)
- **Scope OUT**: monitoring MLOps avancé externe.
- **Fichiers cibles**:
  - `apps/api/src/platform/legacy/core/`
  - `apps/api/src/platform/main.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/data_access.py; apps/api/src/platform/legacy/core/data_quality.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ML-FORECAST (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Appliquer des seuils simples et explicites pour réduire les faux niveaux de confiance.
  - Si drift détecté, réduire confidence et activer un warning utilisateur.
  - Aligner ces warnings avec les badges UI dégradés existants.
- **Acceptation testable**:
  - confidence calibrée et warnings drift visibles dans les payloads forecasts/signals.
- **Dependencies**: TV15-ML-04, TV8-COST-03

#### TV15-ML-06 - Data-driven forecasting QA gate

- **Epic**: Epic 15
- **Priority**: P0
- **Objectif**: empêcher la release si le forecast n’est pas réellement data-driven et robuste.
- **Scope IN**:
  - gate couvrant dataset/training/backtest/inference/calibration
  - critères PASS/BLOCKED explicites
- **Scope OUT**: benchmark académique étendu.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/core/data_access.py; apps/api/src/platform/legacy/core/data_quality.py; apps/api/src/platform/legacy/core/market_data.py; apps/api/src/platform/legacy/analytics/market_intel.py; apps/api/src/ingestion/news_schemas.py; apps/api/src/ingestion/bronze_pipeline.py; apps/api/src/ingestion/silver_pipeline.py; apps/api/src/ingestion/gold_features_pipeline.py; apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/storage/io.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Vérifier explicitement la provenance `source=model` sur un échantillon MVP.
  - Bloquer si backtest ou calibration est absent/invalide.
  - Inclure preuve lisible pour décision GO/NO-GO produit.
- **Acceptation testable**:
  - gate final bloque si forecasts non data-driven ou non calibrés.
- **Dependencies**: TV15-ML-05, TV14-SHIP-06

#### TV15-ML-07 - Runtime model artifact bridge and strict nominal path

- **Epic**: Epic 15
- **Priority**: P0
- **Objectif**: brancher le runtime sur des artefacts modèle réels et supprimer les chemins morts/ambiguës.
- **Scope IN**:
  - chargement artefact modèle versionné pour `/api/forecasts`
  - suppression du chemin nominal basé uniquement snapshot quand modèle indisponible
  - fallback explicite obligatoire (`source=fallback` + warning) si artefact absent
- **Scope OUT**: entraînement distribué/registry externe.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/forecasts/api/forecasts.py`
  - `apps/api/src/platform/legacy/analytics/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/models/forecast_hybrid_v1.py; apps/api/src/platform/legacy/analytics/forecaster.py; apps/api/src/platform/legacy/analytics/ml_baseline.py; apps/api/src/platform/legacy/core/data_quality.py; apps/api/src/platform/legacy/storage/io.py; apps/api/src/domains/forecasts/api/forecasts.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil ML-FORECAST (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Éviter les imports morts/non présents en runtime; forcer un chemin unique d’inférence.
- **Acceptation testable**:
  - en nominal, `/api/forecasts` renvoie `source=model` avec `model_version` non vide; en absence artefact, réponse `source=fallback` explicite.
- **Dependencies**: TV15-ML-04, TV15-ML-05

### Epic 16 - Forecast Delivery Contract (API -> UI)

#### TV16-FF-01 - Unified forecast response contract across core APIs

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: aligner le contrat forecast sur tous les endpoints décision.
- **Scope IN**:
  - contrat commun sur `/api/forecasts`, `/api/decision/brief`, `/api/judge`, `/api/copilot/ask`
  - champs obligatoires `direction/confidence/action/horizon/why/risk_flag/updated_at/source/model_version`
- **Scope OUT**: création de nouveaux endpoints hors scope MVP.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/{copilot|forecasts|judge|market_data}/api/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/forecasts/api/forecasts.py; apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/copilot/api/copilot.py; apps/api/src/domains/market_data/application/dashboard_ui_service.py; apps/web/src/domains/forecasts/components/*
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser un schéma partagé pour éviter des variantes endpoint par endpoint.
  - Conserver des marqueurs de provenance explicites (`source=model|fallback`, `model_version`).
  - Mettre `/api/forecasts` au niveau Judge-parity: `debug=true` (cache bypass), métadonnées complètes (`filters_applied`, `stats`, `warnings[]`), et contrat never-empty strict sans `HTTPException` remontée au frontend.
- **Acceptation testable**:
  - les 4 endpoints exposent le même bloc forecast obligatoire.
- **Dependencies**: TV2-SIGNAL-01, TV15-ML-04

#### TV16-FF-02 - Nominal model-path enforcement and degraded semantics

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: empêcher les faux "nominal" sans modèle data-driven.
- **Scope IN**:
  - règle backend: nominal => `source=model`
  - fallback obligatoire si modèle indisponible (`source=fallback` + warning explicite)
- **Scope OUT**: orchestration MLOps avancée.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/forecasts/api/forecasts.py`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/forecasts/api/forecasts.py; apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/copilot/api/copilot.py; apps/api/src/domains/market_data/application/dashboard_ui_service.py; apps/web/src/domains/forecasts/components/*
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil CORE-API-CONTRACT (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Ne jamais masquer un fallback derrière un état nominal.
  - Inclure un warning machine-readable quand le chemin modèle est indisponible.
- **Acceptation testable**:
  - aucun flux nominal ne retourne un forecast sans `source=model`.
- **Dependencies**: TV16-FF-01

#### TV16-FF-03 - Decision brief API assembly from forecast payloads

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: faire du daily brief un agrégat des prévisions API réelles.
- **Scope IN**:
  - `/api/decision/brief` assemble et expose explicitement les blocs forecast sources
  - traçabilité des actifs/secteurs utilisés pour le brief
- **Scope OUT**: personnalisation avancée du brief.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/{copilot|forecasts|judge|market_data}/api/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/forecasts/api/forecasts.py; apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/copilot/api/copilot.py; apps/api/src/domains/market_data/application/dashboard_ui_service.py; apps/web/src/domains/forecasts/components/*
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-BRIEF (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Réutiliser les payloads forecast existants au lieu de recalculer une logique parallèle.
  - Exposer provenance et fraîcheur du brief de façon compacte.
- **Acceptation testable**:
  - le brief contient des blocs forecast reliés à des payloads API vérifiables.
- **Dependencies**: TV16-FF-02, TV-ADV-07

#### TV16-FF-04 - UI rendering of forecast and provenance on core surfaces

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: afficher clairement les prévisions et leur provenance sur les écrans clés.
- **Scope IN**:
  - decision cards, daily brief, judge panel, ask panel
  - rendu explicite `source/model_version/updated_at/confidence`
- **Scope OUT**: refonte design complète.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/pages/index.html`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/forecasts/api/forecasts.py; apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/copilot/api/copilot.py; apps/api/src/domains/market_data/application/dashboard_ui_service.py; apps/web/src/domains/forecasts/components/*
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Interdire le chemin nominal mock pour ces surfaces.
  - Afficher un état dégradé explicite quand `source=fallback`.
- **Acceptation testable**:
  - les 4 surfaces UI affichent forecast + provenance sans ambiguïté.
- **Dependencies**: TV16-FF-03, TV4-UI-03

#### TV16-FF-05 - End-to-end tests for API->UI forecast chain

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: prouver automatiquement la chaîne API->UI des prévisions.
- **Scope IN**:
  - tests contrat API forecast
  - tests UI/functional sur rendu forecast et provenance
- **Scope OUT**: test perf massif.
- **Fichiers cibles**:
  - `apps/api/tests/`
  - `scripts/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/forecasts/api/forecasts.py; apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/copilot/api/copilot.py; apps/api/src/domains/market_data/application/dashboard_ui_service.py; apps/web/src/domains/forecasts/components/*
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil TEST-COVERAGE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Prioriser des tests stables sur le contrat et la visibilité UI (pas des assertions fragiles purement textuelles).
  - Inclure des cas nominal + degraded.
- **Commandes de test**:
  - `bash scripts/backend_regression_gate.sh --no-live` (contrat forecast)
  - test navigateur réel (Playwright/Cypress) du parcours `forecast -> source/model_version/updated_at` + snapshots des 4 surfaces principales.
- **Acceptation testable**:
  - suite E2E passe et détecte les régressions de provenance/affichage.
- **Dependencies**: TV16-FF-04, TV-ADV-08

#### TV16-FF-06 - Forecast-delivery release gate

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: bloquer la release si une surface core ne montre pas une prévision data-driven traçable.
- **Scope IN**:
  - règles gate explicites sur API->UI mapping
  - preuves artefactées GO/NO-GO
- **Scope OUT**: reporting BI avancé.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/domains/forecasts/api/forecasts.py; apps/api/src/domains/judge/api/judge.py; apps/api/src/domains/copilot/api/copilot.py; apps/api/src/domains/market_data/application/dashboard_ui_service.py; apps/web/src/domains/forecasts/components/*
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Bloquer si un seul flux core manque `source/model_version/updated_at` visible côté UI.
  - Publier une preuve lisible avec mapping endpoint->écran validé.
- **Acceptation testable**:
  - gate final retourne `BLOCKED` quand un flux core forecast n'est pas conforme.
- **Dependencies**: TV16-FF-05, TV14-SHIP-06

#### TV16-FF-07 - Frontend core API wiring (remove nominal mock path)

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: connecter réellement le frontend principal aux APIs core de prévision.
- **Scope IN**:
  - brancher `app.js` sur `/api/forecasts`, `/api/brief/daily` (ou `/api/decision/brief`), `/api/judge`, `/api/copilot/ask`
  - désactiver le chemin nominal basé mockData pour cards/brief/judge/ask
- **Scope OUT**: redesign UI global.
- **Fichiers cibles**:
  - `apps/web/src/domains/forecasts/pages/app.js`
  - `apps/web/src/domains/forecasts/contracts/mockData.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/web/src/platform/js; apps/api/src/domains/forecasts/api/forecasts.py; apps/api/src/domains/judge/api/judge.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Préserver un fallback dégradé explicite, mais interdire le fallback caché en nominal.
- **Acceptation testable**:
  - scan `app.js` montre des appels API core effectifs et le rendu nominal dépend des payloads backend.
- **Dependencies**: TV16-FF-04, TV-ADV-01, TV-ADV-03

#### TV16-FF-08 - Placeholder purge on core decision flow

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: éliminer les placeholders/mock sur les flux décisionnels core.
- **Scope IN**:
  - remplacer l’historique copilot mock par persistance réelle
  - remplacer les réponses brief placeholder par état dégradé explicite basé data réelle
- **Scope OUT**: historique conversationnel avancé multi-device.
- **Fichiers cibles**:
  - `apps/api/src/platform/main.py`
  - `apps/api/src/domains/{copilot|forecasts|judge|market_data}/api/`
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/platform/legacy/storage/io.py; apps/api/src/services/snapshot_loader.py; apps/api/src/domains/forecasts/api/brief_alias.py
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Les états dégradés doivent être machine-readable (`source=fallback`, `warnings[]`) et visibles en UI.
- **Acceptation testable**:
  - plus de payload mock/placeholder sur `copilot/history` et `brief` dans le parcours MVP nominal.
- **Dependencies**: TV16-FF-07, TV-ADV-05, TV16-FF-03

#### TV16-FF-09 - Quality signal parity (real probes to UI)

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: exposer des signaux qualité réels (pas statiques) et les afficher dans le cockpit.
- **Scope IN**:
  - alimenter la UI via checks qualité runtime réels
  - afficher statut de qualité/fraicheur cohérent avec les APIs core
- **Scope OUT**: dashboard observabilité séparé.
- **Fichiers cibles**:
  - `apps/api/src/domains/judge/api/quality.py`
  - `apps/web/src/domains/forecasts/pages/app.js`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): apps/api/src/services/snapshot_loader.py; scripts/backend_regression_gate.sh
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil DECISION-UI (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Harmoniser les labels UI (`fresh/stale/degraded`) avec les champs backend.
- **Acceptation testable**:
  - les indicateurs UI qualité/freshness correspondent aux probes runtime et non à des valeurs fixes.
- **Dependencies**: TV10-DATA-07, TV16-FF-07

#### TV16-FF-10 - Forecast technical gate pack (API->UI proof)

- **Epic**: Epic 16
- **Priority**: P0
- **Objectif**: transformer le gate forecast-first en contrôle technique exécutable de bout en bout.
- **Scope IN**:
  - vérification automatique des champs forecast requis sur endpoints core
  - vérification explicite de la provenance (`source/model_version/updated_at`) et états dégradés
  - preuve liée entre réponse API et rendu UI sur surfaces core
- **Scope OUT**: test visuel pixel-perfect.
- **Fichiers cibles**:
  - `scripts/run_delivery_gate.sh`
  - `scripts/backend_regression_gate.sh`
  - `finance-app/openclaw-gates/`
- **INTEGRATION-APP-EENGINEER-RECOMMENDATIONS**:
  - Modules à réutiliser (voir docs/ops/REUSE_MODULES_CATALOG.md): scripts/run_delivery_gate.sh; scripts/backend_regression_gate.sh; scripts/preflight_dispatch.sh
  - Forecast-first invariant: chaque livraison doit soit produire une prevision API data-driven (action/direction, confidence, horizon, why, risk_flag, freshness), soit prouver son rendu UI + evidence gate sur le flux decision principal.
  - Seuils par tache: appliquer le profil RELEASE-GATE (section Matrice de seuils dacceptation) ; tout seuil mandatory en echec => BLOCKED.
  - Échouer le gate si un endpoint/surface core manque un champ obligatoire ou cache un fallback.
- **Acceptation testable**:
  - gate retourne `PASS` seulement avec preuves techniques exécutées API->UI.
- **Dependencies**: TV16-FF-08, TV16-FF-09, TV16-FF-05

## Addendum (Audit 2026-03-03) — Architecture hardening pack P0/P1

### A26-ARCH-01 - Restore forecast/judge import viability (F-001/F-002/F-003)

- **Priority**: P0
- **Objectif**: rendre les modules critiques importables sans fallback fantôme.
- **Scope IN**:
  - créer `apps/api/src/services/cache_layer.py` ou re-router `forecast_service.py` vers cache layer existant et testable
  - corriger `_backend_root()` / `_src_root()` dans `apps/api/src/domains/judge/application/g4f_client.py`
  - retirer les imports ghost `backend.*` de `apps/api/src/domains/forecasts/application/forecast_service.py`
- **Acceptation testable**:
  - `python3 -c "import apps.api.src.domains.forecasts.application.forecast_service"` passe sans ModuleNotFoundError
  - `python3 -c "from apps.api.src.domains.judge.application.g4f_client import get_ranked_tested_models; print(bool(get_ranked_tested_models()))"` retourne vrai si fichiers présents

### A26-ARCH-02 - Purge fake RAG + unify runtime path (F-004/F-005/F-006/F-008)

- **Priority**: P0
- **Objectif**: supprimer les doubles datastores et réaligner vers `apps/api/runtime/data`.
- **Scope IN**:
  - purger `apps/api/src/runtime/data/rag/news.jsonl` fake puis regénérer via job réel
  - supprimer le dossier fantôme `apps/api/src/runtime/` après migration de son contenu utile
  - aligner `path_resolver.py` et les readers forecast sur un unique `DATA_DIR` canonique
- **Acceptation testable**:
  - `test ! -d apps/api/src/runtime`
  - `rg -n "test.com|fed.com" apps/api/runtime/data/rag/news.jsonl` retourne vide
  - les endpoints forecast/judge lisent la même source runtime (preuve logs + paths)

### A26-ARCH-03 - Layering cleanup and bridge reduction (F-007/F-010/F-011/F-012)

- **Priority**: P1
- **Objectif**: réduire la dette de couches et les bridges `sys.path` non déterministes.
- **Scope IN**:
  - sortir les schémas `market_data` de `api.schemas` vers `domains/market_data/contracts/*`
  - supprimer bridges `sys.path` créés le 2026-03-03 (`services/*`, `platform/legacy/research/llm_client.py`)
  - remplacer `api/main.py` private re-export shim par interface publique stable dans `platform/main.py`
  - documenter plan de retrait progressif des stubs racine et alias chain (sans big-bang)
- **Acceptation testable**:
  - `rg -n "sys.path.insert\\(" apps/api/src/services apps/api/src/platform/legacy/research` retourne vide
  - `rg -n "importlib.import_module\\(\"platform.main\"\\)" apps/api/src/api/main.py` retourne vide
  - tests domaine `market_data` passent sans dépendre de `api.schemas`

### A26-ARCH-04 - Legacy namespace migration plan (F-009)

- **Priority**: P1
- **Objectif**: planifier la migration de `platform/legacy` actif vers namespace cible sans casser runtime.
- **Scope IN**:
  - RFC court avec stratégie en 2 phases (alias compat + cutover)
  - inventaire des modules actifs dans `platform/legacy/*` et mapping destination (`platform/core/*`)
- **Scope OUT**:
  - renommage global immédiat (risque élevé) dans ce lot
- **Acceptation testable**:
  - document de migration signé dans `docs/ops/`
  - check-list de cutover et rollback prête avant exécution

## Changelog (all-epics decomposition)

- 2026-02-26 America/New_York - Added complete Epic 1-6 task decomposition with UI-first dispatch lane and explicit dependencies.
- 2026-02-26 America/New_York - Enforced unique task-ID heading policy and removed heading ID collisions in delta/breakdown sections.
- 2026-02-26 America/New_York - Added Epic 7/8/9 tasks: macro-geopolitical radar, cost governance, and decision learning loop.
- 2026-02-26 America/New_York - Added continuous delivery loop and Epic 10/11/12/13/14 task decomposition toward basic-ready MVP.
- 2026-02-26 America/New_York - Added INTEGRATION-APP-EENGINEER-RECOMMENDATIONS to all remaining task IDs (123/123 coverage) to detail architecture per existing task without creating new backlog items.
- 2026-02-26 America/New_York - Reoriented architecture to forecast-first value: global invariants now require data-driven forecast outputs from APIs and explicit UI/gate evidence; requirement propagated across all INTEGRATION-APP-EENGINEER-RECOMMENDATIONS blocks.
- 2026-02-26 America/New_York - Added Epic 15 data-driven forecasting core (dataset, training, backtest, inference, calibration, QA gate).
- 2026-02-26 America/New_York - Added Epic 16 forecast delivery contract (`TV16-FF-01..06`) to enforce API->UI mapping and release blocking evidence.
- 2026-02-26 America/New_York - Added architecture-owned threshold matrix (per task profile) and linked each task integration block to a mandatory threshold profile (`Seuils par tache`) to enforce objective PASS/BLOCKED decisions.
- 2026-02-26 America/New_York - Added Judge-parity architecture audit from code and re-prioritized existing tasks (`TV-ADV-04/05/06`, `TV16-FF-*`, `TV-ADV-08`, `TV-ADV-10`) to converge all core APIs to the Judge model.
- 2026-02-26 America/New_York - Added audit-coverage boost tasks to close detected global gaps: `TV10-DATA-07`, `TV13-OPS-07..09`, `TV14-SHIP-07`, `TV15-ML-07`, `TV16-FF-07..10`.
