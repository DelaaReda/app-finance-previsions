# Architecture Batches VM — Deep Diagnostic (P0→P2)

Date: 2026-03-04  
Scope: Orchestration runtime + monitor + contracts API frontend  
Execution target: VM (`/home/venom/analyse-financiere`)

## Baseline validée

- Monitor contract: `PASS` (`/api/status`, `/api/runtime-diagnostics`).
- Runtime monitor data visible: `health=OK`, `roles=[planner,dev,admin]`, queue/workboard non vides.
- Backend/frontend up via launcher officiel.
- Legacy scheduler ownership corrigé (pas de `qwen_*` actif côté scheduler canonique).

## Statut d'exécution (mise à jour)

- `DONE` `BATCH-27-P0-00` Reasoning enum guard (`xhigh` neutralisé en `high` sur chaîne cron/runner/config).
- `DONE` `BATCH-27-P0-05` VM resume lock policy (`openclaw.json` lock immuable devenu opt-in).
- `IN_PROGRESS` `BATCH-27-P0-04` session fallback (`session_not_ready` tmux => fallback `codex_exec` activé, observation 24h requise).
- `IN_PROGRESS` `BATCH-27-P0-02` trilock unification (implémentation faite, validation 24h en cours).
- `OPEN` `BATCH-27-P0-01` startup contract hardening.
- `OPEN` `BATCH-27-P0-03` planner guard + batch integrity.
- `OPEN` `BATCH-27-P1-*` et `BATCH-27-P2-*`.

---

## BATCH-27-P0-00 — Reasoning Enum Guard

Owner: `admin`  
Status: `DONE`
Goal: empêcher définitivement les erreurs runtime `unknown variant xhigh`.

### Scope

- `scripts/fc_agent_tick.sh`
- `platform/config/lm_used_model_config.sh`
- `platform/automation/configure_parallel_team_crons.sh`
- `platform/automation/configure_tmux_role_crons.sh`
- `platform/automation/update_direct_crons.sh`
- `docs/operations/orchestrator/parallel-role-cron-map.json`

### Résultat

- Tous les chemins de configuration normalisent désormais vers `minimal|low|medium|high`.
- `xhigh` est converti automatiquement en `high`.
- Plus de panne hard-fail liée à `model_reasoning_effort`.

### Validation

```bash
cd /home/venom/analyse-financiere
rg -n "xhigh" platform/config platform/automation scripts docs/operations/orchestrator/parallel-role-cron-map.json
tail -n 200 logs-codex-runs/role-runner/admin.events.log | rg "unknown variant|model_reasoning_effort"
```

---

## BATCH-27-P0-05 — VM Resume Lock Policy

Owner: `dev`  
Status: `DONE`
Goal: éviter le re-lock automatique de `~/.openclaw/openclaw.json` après reprise VM.

### Scope

- `platform/automation/vm_resume_guard.sh`
- `scripts/vm_resume_guard.sh`

### Résultat

- Nouveau flag: `VM_RESUME_GUARD_IMMUTABLE_LOCK_ENABLED` (défaut `0`).
- Politique par défaut: `config_lock=unlocked_by_policy`.
- Les mises à jour runtime OpenClaw ne sont plus bloquées par `chattr +i` implicite.

### Validation

```bash
cd /home/venom/analyse-financiere
VM_RESUME_GUARD_FORCE=1 bash platform/automation/vm_resume_guard.sh
lsattr ~/.openclaw/openclaw.json
```

---

## BATCH-27-P0-04 — Session Not Ready Fast Fallback

Owner: `dev`  
Status: `IN_PROGRESS`
Goal: réduire les `rc=43` en basculant immédiatement vers `codex_exec` quand le canal tmux n'est pas prêt.

### Scope

- `platform/automation/cron_tmux_role_runner.sh`

### Actions

1. Ajouter `TMUX_ROLE_SESSION_NOT_READY_FALLBACK_CODEX` (défaut `1`).
2. Sur `ensure_role_session_ready` KO en canal tmux + codex disponible:
   - tracer `session_not_ready_fallback_codex`
   - exécuter `codex_exec_prompt_once`
   - éviter `return 43` immédiat.
3. Mesurer baisse `session_not_ready` sur 3 fenêtres monitor.

### Acceptance

- Diminution stable de `session_not_ready` dans `runtime-diagnostics`.
- Moins de `rc=43` dans `admin.events.log` / `planner.events.log`.
- Pas de régression sur validité contract (8 lignes strictes).

### Validation

```bash
cd /home/venom/analyse-financiere
curl -sS http://127.0.0.1:7779/api/runtime-diagnostics | jq '.signals.session_not_ready_recent'
tail -n 300 logs-codex-runs/role-runner/admin.events.log | rg "session_not_ready|session_not_ready_fallback_codex|rc=43"
```

## Diagnostic profond (causes prioritaires restantes)

1. `session_not_ready` reste élevé dans la fenêtre qualité (bruit historique + redémarrages non alignés).
2. Le démarrage officiel n’assurait pas systématiquement le monitor (`:7779`) dans toutes les sessions.
3. Risque de régression silencieuse sur locks (run/memory/global) si plusieurs lanes redémarrent ensemble.
4. Risque de drift planner (batch id/guard) si queue/workboard/docs divergent pendant transition de batch.
5. Contrats API frontend sensibles au routage et au fallback (404 perçu côté UI même si backend vivant).

---

## BATCH-27-P0-01 — Startup Contract Hardening

Owner: `dev`  
Goal: garantir que `./finance-copilot.sh start` expose systématiquement backend + frontend + monitor.

### Scope

- `apps/api/runtime/copilot.sh`
- `scripts/monitor_stack_guard.sh`

### Actions

1. Démarrage monitor intégré au flux `start`.
2. Vérification explicite `:7779/api/status` après démarrage.
3. Affichage monitor dans `status` et dans les URLs de sortie.
4. Arrêt monitor intégré au flux `stop` (clean shutdown).

### Acceptance

- `./finance-copilot.sh start` affiche les 3 services UP.
- `./finance-copilot.sh status` montre backend/frontend/monitor.
- `curl -sS http://127.0.0.1:7779/api/status` retourne JSON valide.

### Proof commands

```bash
cd /home/venom/analyse-financiere
./finance-copilot.sh start
./finance-copilot.sh status
curl -sS http://127.0.0.1:7779/api/status | jq '.health,.queue.total,.workboard.total'
./finance-copilot.sh stop
```

---

## BATCH-27-P0-02 — Lock Model Unification (TRILOCK Guard)

Owner: `architect`  
Status: `IN_PROGRESS`
Goal: éliminer toute contention lock entre rôles et éviter les faux blocages.

### Scope

- `scripts/fc_agent_tick.sh`
- `platform/automation/cron_tmux_role_runner.sh`
- `scripts/cleanup_stale_role_locks.sh`
- `platform/automation/auto_recover_tmux_roles.sh`

### Actions

1. Formaliser 3 couches de lock:
   - `tick lock` (`/tmp/fc-agent-locks/*.lock`)
   - `run lock` (`~/.openclaw/cron/role-state/*.run.lock`)
   - `memory lock` (`*.memory.lock`)
2. Imposer un ordre de prise et de release unique (documenté).
3. Ajouter cleanup idempotent toutes les 10 min sur les 3 couches.
4. Ajouter trace explicite lock owner + age + release reason.

### Implémenté

- `scripts/fc_agent_tick.sh`
  - Meta lock `tick` (`*.lock.meta`) avec `pid/host/start_epoch/layer/order`.
  - Traces explicites:
    - `TRILOCK_ACQUIRE` (layer=tick)
    - `TRILOCK_SKIP` (busy + holder + age)
    - `TRILOCK_RELEASE` (hold_s + release_reason)
- `platform/automation/cron_tmux_role_runner.sh`
  - Meta lock `run` enrichie (`start_epoch`, `order=tick>run>memory`).
  - Traces `trilock_busy|trilock_acquired|trilock_release` dans `*.events.log`.
  - Evidence enrichie quand lock occupé (`holder_age_s`, `lock_order`).
- `platform/automation/role_memory_append.py`
  - Meta lock `memory` sidecar (`*.memory.lock.meta`).
  - Traces `trilock_acquired|trilock_release` pour la couche `memory`.
- `scripts/cleanup_stale_role_locks.sh`
  - Cleanup idempotent sur les 3 couches (`tick/run/memory`).
  - Nettoyage sécurisé: skip si PID vivant ou FD ouvert.
  - Logs structurés: `layer/role/age_s/owner/reason/order`.
- `platform/automation/auto_recover_tmux_roles.sh`
  - Utilise désormais le cleanup unifié avant recovery.

### Acceptance

- Plus de stale lock > seuil pendant 24h.
- Pas de double run simultané pour un rôle.
- `session_not_ready` baisse durablement sur 3 fenêtres consécutives.

### Proof commands

```bash
cd /home/venom/analyse-financiere
bash scripts/cleanup_stale_role_locks.sh
bash scripts/fc_health_check.sh
find /tmp/fc-agent-locks ~/.openclaw/cron/role-state -name '*.lock' -mmin +30
```

---

## BATCH-27-P0-03 — Planner Guard and Batch Integrity

Owner: `planner`  
Goal: supprimer les blocages `PLANNER_BATCH_ID_INVALID` et références batch fantômes.

### Scope

- `platform/automation/cron_tmux_role_runner.sh`
- `scripts/auto_batch_close.sh`
- `docs/operations/orchestrator/priority-queue.json`
- `docs/operations/orchestrator/parallel-workstreams.json`

### Actions

1. Vérifier intégrité de chaîne batch active (ids exacts, pas d’alias fantôme).
2. Validation stricte queue↔workboard avant close de batch.
3. Reject explicite des ids non conformes, avec corrective action automatique.
4. Ajout d’un check “single active chain” côté admin/planner.

### Acceptance

- `planner_guard_blocked=false` sur runtime diagnostics.
- Aucun `BLOCKER_ID=PLANNER_BATCH_ID_INVALID` sur la fenêtre récente.
- Close batch uniquement quand toutes tâches chainées sont closes.

### Proof commands

```bash
cd /home/venom/analyse-financiere
curl -sS http://127.0.0.1:7779/api/runtime-diagnostics | jq '.signals.planner_guard_blocked,.signals.planner_blocker_id'
python3 scripts/parallel_workstream.py validate --queue docs/operations/orchestrator/priority-queue.json --proof-root docs/operations/orchestrator/proofs --require-proof-manifest
```

---

## BATCH-27-P1-01 — Resume Continuity and Token Efficiency

Owner: `admin`  
Goal: garder `resume=1` sur lanes canoniques et réduire les timeouts.

### Scope

- `scripts/fc_agent_tick.sh`
- `platform/automation/cron_tmux_role_runner.sh`
- `docs/operations/orchestrator/kpi-history.jsonl`

### Actions

1. Verrouiller defaults:
   - planner/admin/dev: `TMUX_ROLE_CODEX_EXEC_RESUME=1`
   - admin prompt timeout `>=300`
   - admin retry timeout `>=120`
2. Garder mémoire admin minimale active (pas forcée à `none`).
3. Mesurer avant/après sur:
   - timeout rc=124
   - tokens consommés (proxy via durée/runs)
   - stabilité verdict/delta.

### Acceptance

- `admin_timeout_events_recent=0` sur fenêtre récente.
- Diminution `rc=124` et `session_not_ready`.
- Pas de baisse de qualité contract (`DELTA` utile maintenu).

### Proof commands

```bash
cd /home/venom/analyse-financiere
curl -sS http://127.0.0.1:7779/api/runtime-diagnostics | jq '.signals.admin_timeout_events_recent'
bash scripts/fc_health_check.sh
```

---

## BATCH-27-P1-02 — Frontend/API Contract Recovery

Owner: `dev`  
Goal: éliminer les erreurs 404 visibles sur “Prévisions (cartes)” et widgets critiques.

### Scope

- `apps/api/src/platform/main.py`
- `apps/api/src/domains/forecasts/api/*.py`
- `apps/api/src/domains/market_data/api/*.py`
- `apps/web/src/apiConnector.js`

### Actions

1. Stabiliser endpoints critiques:
   - `/api/forecasts`
   - `/api/recommendations/daily`
   - `/api/stocks/{ticker}/sheet`
2. Garantir payload cohérent (`ok/data/error/freshness`).
3. Fallback frontend explicite et lisible (pas de JSON brut d’erreur).

### Acceptance

- Les 3 endpoints répondent `200` sur dataset nominal.
- Pas de bannière 404 brute dans UI.
- Widgets forecasts + top stocks affichent au moins état vide stylé + retry.

### Proof commands

```bash
cd /home/venom/analyse-financiere
curl -sS "http://127.0.0.1:8050/api/forecasts?horizon=short&limit=24" | jq '.ok,.data'
curl -sS "http://127.0.0.1:8050/api/recommendations/daily?limit=3" | jq '.ok,.data'
curl -sS "http://127.0.0.1:8050/api/stocks/SPY/sheet" | jq '.ok,.data.ticker'
```

---

## BATCH-27-P2-01 — Monitor UX Reliability Gates

Owner: `dev`  
Goal: rendre le monitor actionnable même en erreurs partielles.

### Scope

- `apps/monitor/server.py`
- `scripts/monitor_contract_smoke.sh`
- `scripts/fc_health_check.sh`

### Actions

1. Maintenir rendu partiel explicite si une source tombe.
2. Dédoublonner alertes runtime (severity + source + timestamp bucket).
3. Ajouter gate CI/runtime: fail si contrat monitor cassé.
4. Ajouter panneau “data source freshness” par source.

### Acceptance

- Monitor reste lisible si un endpoint secondaire échoue.
- `monitor_contract_smoke` intégré aux checks de release.
- Alertes dedupe visibles dans `runtime-diagnostics`.

### Proof commands

```bash
cd /home/venom/analyse-financiere
bash scripts/monitor_contract_smoke.sh --base-url http://127.0.0.1:7779
bash scripts/fc_health_check.sh
```

---

## Ordre recommandé

1. `BATCH-27-P0-01`
2. `BATCH-27-P0-02`
3. `BATCH-27-P0-03`
4. `BATCH-27-P1-01`
5. `BATCH-27-P1-02`
6. `BATCH-27-P2-01`

## Definition of Done (globale)

- Health check: backend/frontend/monitor tous `UP`.
- Monitor contract: `PASS`.
- Aucun blocker planner/admin actif sur fenêtre récente.
- Endpoints frontend critiques sans 404 fonctionnel.
- Preuve batch stockée dans `docs/operations/orchestrator/proofs/<BATCH-ID>/`.
