# ENGINEERING PLAYBOOK v1 (analyse-financiere)

## Objective
Ship fast **without** shipping garbage.

## Reference Example (API)
- Endpoint/API reference guide:
  - `docs/ops/API_ENDPOINT_BEST_PRACTICES.md`
- Usage rule:
  - Any endpoint change should align with this guide (contract, cache, fallback, tests).

## Backend LLM Config
- Source of truth for default model/provider switches:
  - `configs/llm-models.json` (shared repo-level config)
- Runtime override env:
  - `LLM_SETTINGS_FILE` (optional absolute/relative path)
- `g4f` reste le default par conception via :
  - `LLM_G4F_PROVIDER / G4F_PROVIDER`
  - `LLM_G4F_MODEL / G4F_MODEL`
- Appel LLM canonique (obligatoire pour les nouveaux modules):
  - `apps/api/src/services/g4f_client.py::call_llm(...)` (ou domains/judge)
  - modes:
    - `LLM_MODEL_MODE=dev` (tests rapides, coûts/latence réduits)
    - `LLM_MODEL_MODE=best` (meilleurs modèles testés + fallbacks)
  - réglages d'exécution:
    - `LLM_DEV_MODELS`, `LLM_DEV_TIMEOUT_SECONDS`, `LLM_DEV_MAX_ATTEMPTS`
    - `LLM_BEST_TIMEOUT_SECONDS`, `LLM_BEST_MAX_ATTEMPTS`
- Recommended change method:
  1. edit `configs/llm-models.json`
  2. avoid hardcoded model values in Python for routine model tuning
  3. dans les services/routes, n'appeler que `call_llm(...)` (pas de provider direct inline)

## Mandatory 4-Gate Pipeline
No batch can be marked DONE unless all gates pass.

### Gate 1 — Command Safety Precheck
- Every shell command must pass `scripts/command_safety_gate.py` via `scripts/exec_safe.sh`.
- Decisions:
  - `ALLOW` → run
  - `CONFIRM` → run with risk logged (policy: no wait)
  - `BLOCK` → stop

### Gate 2 — Implementation + Targeted Tests
Per task, require:
- clear scope (IN/OUT)
- minimal code change
- targeted tests run
- evidence captured

### Gate 3 — Independent Codex Review
- Run independent reviewer with Codex (separate from the delivery role that authored the change).
- Required output: `GO` or `BLOCKED` + minimal fix list.
- Machine-readable evidence required in artifact `EVIDENCE`:
  - `review_ref=<path_or_run_id>`
  - `review_verdict=<GO|BLOCKED|PASS>`
- If `BLOCKED`, task cannot move forward.

### Gate 4 — Regression Gate
- Run finance regression gate before release verdict.
- Output must contain `PASS` or `BLOCKED`.
  - Recommended wrapper: `bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-<id>-<timestamp>.md`

## OpenClaw Tooling Fast-Lane (Dev/QA)
Use tooling aggressively to reduce cycle time, but keep proofs in `EVIDENCE`.

### Web + Browser (research and QA reproduction)
- Runtime availability (current baseline):
  - `browser.enabled=true`
  - `tools.web.search.enabled=true`
  - `tools.web.fetch.enabled=true`
- Verification commands:
  - `openclaw config get browser.enabled`
  - `openclaw config get tools.web.search.enabled`
  - `openclaw config get tools.web.fetch.enabled`
  - `openclaw config get browser.cdpUrl`
- Expected usage:
  - `analyst`/`architect`: spec & dependency research
  - `dev`/`backend_engineer`/`frontend_engineer`: doc lookup + implementation validation
  - `tester`/`qa`: browser-based repro and verification
- Référence outil: https://docs.openclaw.ai/tools/browser

### Procédure browser standard (copier-coller pour tous les agents)
- Précondition (obligatoire avant toute activité UI/QA qui dépend du navigateur):
  - `bash scripts/dev_qa_tooling_check.sh`  (`VERDICT: PASS`)
  - `openclaw browser status`
- Checklist exécution (5 minutes max):
  1. `openclaw browser start`
  2. `openclaw browser open <URL_CIBLE>` (ex: `https://docs.openclaw.ai/tools/browser` ou `http://localhost:5173`)
  3. `openclaw browser wait --load domcontentloaded`
  4. `openclaw browser snapshot --labels` (capture d’accessibilité + vérification visuelle logique)
  5. `openclaw browser screenshot [--full-page]` (capture écran)
  6. `openclaw browser requests | head -n 80` (preuves réseau/contrats)
  7. Scénario dégradé si besoin (`openclaw browser stop`, `start`, répéter sur chemin alternatif)
  8. `openclaw browser stop`
- Données à remonter dans `EVIDENCE`:
  - `tools_used=web,web.fetch,web.search,playwright-mcp` (selon ce qui est réellement employé)
  - `tooling_check=PASS|BLOCKED`
  - `tooling_ref=<chemin_ou_id_run_dev_qa_tooling_check>`
  - `browser_ref=MEDIA:...` (chemin retour screenshot/snapshot)
  - `web_ref=<ex:  URL + timestamp>`
  - `tests_run=<suite>:PASS|FAIL|SKIP(reason)`
- Interprétation rapide des échecs:
  - `openclaw browser status` != `running: true` -> fixer infra browser avant de lancer QA
  - `openclaw browser open` OK mais `snapshot` vide ou incohérent -> re-run avec `openclaw browser stop && openclaw browser start`
  - `requests` vide sur page qui doit faire des appels -> confirmer route/retries avant de fermer la tâche

### Attribution par rôle (référent)
- `analyst` / `architect`: recherche/benchmark, vérifier API docs + références, produire `doc_ref` dans evidence.
- `dev` / `frontend_engineer` / `backend_engineer`: vérifier flux d’implémentation, reproduire bug UI/API, fournir `snapshot` + `browser_ref`.
- `tester` / `qa`: exécuter `snapshot + screenshot + requests` sur happy path + degraded path, décider PASS/BLOCKED sur visibilité UI.
- `po` / `scrum_master`: valider la présence d’évidence (preuve de preuve), pas l’assertion technique.

### High-value skills/tools for delivery
- `api-tester`: API checks and contract probes
- `test-runner`: targeted test execution loops
- `playwright-mcp`: browser regression/smoke
- `finance-regression-gate`: release-grade regression proof
- `debug-pro`: root-cause acceleration
- `tmux` + `codex-orchestration`: role-runner and orchestration support

Check availability quickly:
- `openclaw skills check`
- `bash scripts/dev_qa_tooling_check.sh` (preflight unique tooling+gates rapides)

Preflight policy:
- Avant d'activer un nouveau role cron ou de lancer un cycle QA complet, exiger `VERDICT: PASS` sur `scripts/dev_qa_tooling_check.sh`.
- Si `DEV_QA_TOOLING_BLOCKERS` contient `workboard_validate=queue_closed_with_open_tasks`, corriger d'abord la coherence queue/workboard (reopen stream ou fermer les tasks residuelles).

### Evidence requirement when tools are used
When web/browser/skills are used in a task, add at minimum:
- `tools_used=<comma_list>`
- `cmd=<executed_command_or_SKIP(reason)>`
- `tests_run=<suite:PASS|FAIL|SKIP(reason)>`
- `review_ref=<independent_review_ref>`
- If blocked by missing tooling/skill:
  - `tool_request=<none_or_required_tool>`
  - `skill_request=<none_or_required_skill>`

### Effortless monitoring surfaces (no raw log digging)
- Role-level latest status:
  - `docs/orchestrator-ops/executors-monitoring-latest.json`
- Role-level monitoring events:
  - `logs-codex-runs/executor-monitoring/events.jsonl`
- Tool/skill requests surfaced automatically:
  - `docs/ops/AGENT_TOOL_REQUESTS.md`
  - `docs/orchestrator-ops/agent-tool-requests.jsonl`
- Continuous digest:
  - `bash scripts/dg_alert_15m.sh`

---

## Agent Roles (minimum set)
- Planner
- Architect
- Dev
- Tester
- QA
- Security Analyst
- Release Manager
- Codex Reviewer (independent)

Rule: More agents without governance = chaos. Keep strict role boundaries.

---

## Mandatory Task Output Template
Every task/batch response must include:
- `DELTA`
- `EVIDENCE`
- `RISKS`
- `NEXT`
- `VERDICT: PASS|BLOCKED`
- `BLOCKER_ID: <id|NONE>`
- `NEXT_ACTION_UNIQUE`

Evidence schema reference (recommended):
- `docs/ops/ROLE_CONTRACT_EVIDENCE_SCHEMA.md`

---

## Batching Policy
- **Batch-01**: small, critical, contract stabilization.
- **Batch-02+**: only opens when previous batch has QA-signed `VERDICT: PASS` artifact.
- No parallel work on tightly coupled files/contracts.

### Immutable Template Zone
- `apps/api/src/domains/judge/api/judge.py` is the canonical, protected Judge template.
- No agent may edit this file directly unless a formal template revision is approved by the owner.
- All new endpoint work must reuse the template pattern via:
  - `/api/routes/*` new endpoints using contract/reliability reuse modules
  - tests and UI adapters that consume the template contract, not duplicate it
- Violations are BLOCKED and must be logged in `ADMIN_TEAM_CHAT.md` + role handoff.

---

## KPI Dashboard (process efficiency)
Track weekly:
1. Lead time per task (start → PASS)
2. First-pass success rate (%)
3. BLOCKED recurrence by cause
4. No-op edit rate (%)
5. Reopen rate after "DONE" (%)

---

## Orchestration Commands (Qwen-first, recommended)
```bash
# 1) Preflight (queue + health + batch prerequisites)
bash scripts/preflight_dispatch.sh

# 2) Controlled chain (planner -> dev -> tester -> qa) for a given batch id
# Example:
# bash scripts/validate_roles_sequential.sh --roles planner,dev,tester,qa --strict-ready-chain --chain-target BATCH-02

# 3) Final artifact gate (verifies required sections + review evidence)
# Example:
# bash scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-02-<timestamp>.md
```

Artifact path required:
- `finance-app/openclaw-gates/batch-<id>-<timestamp>.md`
