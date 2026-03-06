# Architecture Batches — Runtime Autonomy + Strangler (2026-03-05)

Superseded for current target architecture.

This file is a historical planning document from the parallel-lane period.
Current canonical execution roadmap is:
- `docs/ops/PLANNER_ORCHESTRATOR_TARGET_SPEC.md`
- `docs/product/planning/PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md`

## Contexte cible
- Runtime canonique: `/home/venom/analyse-financiere`
- Démarrage canonique: `./finance-copilot.sh start`
- Topologie core: `planner/dev/admin`
- Advisory: `po_scrum_master` (non bloquant)
- Règle structurelle: **zéro dépendance inter-batch bloquante**

---

## BATCH A1 — Batch autonome (P0)
### Objectif
Supprimer durablement les dépendances inter-batches bloquantes.

### Implémentation
- Fichier: `platform/automation/parallel_workstream.py`
- Pipeline appliqué:
  1. `sync-priority` exécute `_decouple_inter_batch_dependencies(...)`.
  2. Tous les `depends_on` queue inter-batch sont migrés vers `legacy_depends_on`.
  3. `depends_on` queue est vidé pour les items actifs/planned.
  4. `WAITING_DEP` legacy queue est reclassé vers `PLANNED`.
  5. `_sanitize_task_dependencies(...)` garde uniquement les deps intra-stream.
  6. Alias legacy (`GOV-REVIEW` vs `GOV_REVIEW`) normalisés via token resolver.

### Contrat
- `legacy_depends_on`: audit only, non-bloquant.
- Invariant runtime: `cross_dep_count=0` attendu.

### Tests
- `platform/automation/tests/test_parallel_workstream_queue_sync.py`
- `platform/automation/tests/test_parallel_workstream_dependency_alias.py`

### Rollout
```bash
python3 scripts/parallel_workstream.py sync-priority --queue docs/operations/orchestrator/priority-queue.json
```

### Rollback
- Revenir sur `_decouple_inter_batch_dependencies` + `_sanitize_task_dependencies`.
- Option compatible: mode legacy via variable policy dédiée si nécessaire.

---

## BATCH A2 — Scheduling local DAG + fairness (P0)
### Objectif
Éviter les plateaux `READY=0`/`WAITING_DEP` en gardant un dispatch déterministe et non-famine.

### Implémentation
- Fichier: `platform/automation/admin_agents_auto_dispatch_ready.sh`
- Algorithme:
  1. extraction des batches READY,
  2. ordering pondéré par priorité (séquence pondérée),
  3. anti-famine par `ready_wait_cycles` + seuil `ADMIN_DISPATCHER_FAIRNESS_MAX_STARVE_CYCLES`,
  4. sélection task locale par stream selon template order,
  5. cooldown/soft-fail conservés.
- Traces additifs:
  - `dispatch_reason_code`
  - `stream_fairness_slot`

### Contrat
- Raisons standard supportées:
  - `READY_ITEM_AVAILABLE`
  - `LANE_IDLE_WITH_READY`
  - `OPEN_HANDOFF_STALE`
  - `COOLDOWN_ACTIVE`
  - `NO_ACTIONABLE_READY`
  - `CLAIM_FAILED_SOFT`
  - `FAIRNESS_STARVATION_RELIEF`

### Tests
- `platform/automation/tests/test_admin_dispatcher_flow.py`
  - multi-ready déterministe,
  - stale handoff,
  - cooldown,
  - no-op deps,
  - starvation relief.

### Rollout
```bash
ADMIN_DISPATCHER_ENABLED=1 ADMIN_DISPATCHER_MODE=active \
ADMIN_DISPATCHER_FAIRNESS_MAX_STARVE_CYCLES=3 \
bash platform/automation/admin_agents_auto_dispatch_ready.sh
```

### Rollback
- `ADMIN_DISPATCHER_ENABLED=0` (désactivation immédiate)
- ou retour code dispatcher précédent.

---

## BATCH A3 — Runner déterministe anti-stall (P0)
### Objectif
Réduire les boucles passives (`none_no_signal`) et tracer précisément les fallbacks.

### Implémentation
- Fichier: `platform/automation/cron_tmux_role_runner.sh`
- Ajouts:
  1. `TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD` (défaut 3).
  2. Enrichissement fallback evidence:
     - `fallback_reason`
     - `fallback_count_window`
     - `actionability_state`
  3. Reconcile runtime:
     - si lane active + `task_update in {none_no_ready, none_no_signal}` + seuil atteint,
     - forcer `DELTA=READY_ITEM_AVAILABLE_RUNTIME_CONTEXT`,
     - injecter `NEXT` actionnable par rôle,
     - garder `BLOCKER_ID=NONE` quand applicable.

### Contrat
- Contrat 8 lignes inchangé.
- Champs evidence additifs seulement (non-breaking).

### Tests
- `platform/automation/tests/test_role_runtime_context.py`
- `platform/automation/tests/test_runner_message_receipts.py`
- `platform/automation/tests/test_session_not_ready_fallback.sh`

### Rollout
```bash
TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD=3 bash scripts/fc_agent_tick.sh dev
TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD=3 bash scripts/fc_agent_tick.sh planner
TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD=3 bash scripts/fc_agent_tick.sh admin
```

### Rollback
- remettre `TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD` à une valeur haute,
- retirer les clés evidence additifs si nécessaire.

---

## BATCH A4 — Monitor split 3 couches (P1)
### Statut
Partiellement livré.

### Existant
- Dossiers: `apps/monitor/src/{collectors,aggregators,api}`
- Router doctor extrait: `apps/monitor/src/api/doctor_router.py`

### Reste à faire
- Extraire totalement `/api/status` et `/api/runtime-diagnostics` dans `api/`.
- Déplacer toute logique de collecte/normalisation depuis `apps/monitor/server.py` vers `collectors/` et `aggregators/`.

### Invariant
- `agents` never-null.
- `health` core-only.

---

## BATCH A5 — API bootstrap pur + routers domaine (P1)
### Statut
Extraction partielle.

### Existant
- Routers présents dans `apps/api/src/platform/routers/*`.
- `create_app()` inclut déjà des routers critiques/additifs.

### Reste à faire
- Réduire `apps/api/src/platform/main.py` vers bootstrap + include_router.
- Déplacer helpers/handlers restants vers modules route/service dédiés.
- Garantir contrat additif `status|error|meta` pour endpoints critiques.

---

## BATCH A6 — Doctor unique + gate E2E (P1)
### Statut
Livré (base).

### Existant
- CLI: `scripts/fc_doctor.sh --json`
- Engine: `platform/automation/fc_doctor.py`
- API monitor: `/api/doctor`, `/api/doctor/latest`

### Schéma
- `status`, `checks`, `meta`, `generated_at`

### Gate recommandé
```bash
./finance-copilot.sh start
bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779
bash scripts/critical_endpoints_smoke.sh
bash scripts/runtime_e2e_gate.sh
```

---

## BATCH A7 — Documentation opérable (P0 transversal)
### Objectif
Aligner docs ↔ runtime réel, VM-only, sans ambiguïté.

### Documents mis à jour dans ce cycle
- `docs/ops/ORCHESTRATION_RELIABILITY_SPEC.md`
- `docs/ops/RUNNER_MODULAR_ARCHITECTURE.md`
- `docs/ops/MONITOR_ARCHITECTURE_SPEC.md`
- `docs/ops/API_EDGE_ROUTING_TABLE.md`
- `docs/ops/PO_SCRUM_MASTER_CRON_RUNBOOK.md`
- `docs/ops/DOCTOR_JSON_SPEC.md`

### Format runbook exigé
- start
- validate
- recover
- rollback
- evidence path

---

## Validation consolidée (VM)
```bash
python3 -m pytest -q \
  platform/automation/tests/test_parallel_workstream_queue_sync.py \
  platform/automation/tests/test_parallel_workstream_dependency_alias.py \
  platform/automation/tests/test_admin_dispatcher_flow.py \
  platform/automation/tests/test_role_runtime_context.py \
  platform/automation/tests/test_runner_message_receipts.py
```

Résultat attendu: suite verte.

---

## Règles d’architecture à respecter pour les prochains batches
1. Un batch ne bloque jamais un autre batch via `depends_on` queue.
2. Les dépendances autorisées sont locales au stream (task DAG intra-batch).
3. Coordination inter-batch = handoff/events/artifacts, jamais verrou dur.
4. Toute migration est additive + rollbackable par flag/env.
5. Chaque changement runtime doit livrer tests + runbook + preuve.
