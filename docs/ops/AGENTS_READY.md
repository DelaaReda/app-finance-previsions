# État prêt pour agents – 2026-02-28

**Validé par:** admin principal  
**Date:** 2026-02-28  
**Derniere mise a jour operationnelle:** 2026-03-03

---

## 🔄 Mise a Jour Operationnelle 2026-03-03

- Resync effectue entre queue/workboard:
  - `BATCH-05=IN_PROGRESS`
  - `BATCH-06=WAITING_DEP` (`depends_on=BATCH-05`)
  - `BATCH-07=WAITING_DEP` (`depends_on=BATCH-06`)
- Correction backend appliquee sur les forecasts:
  - fallback directionnel base sur `price` vs `previous_close` si historique indisponible.
  - tests forecasts simples maintenant passants.
- Hygiene workspace:
  - artefacts racine malformes deplaces vers `.trash/root-garbage-20260303/`.
- Clarification cron critique:
  - la normalisation par lanes (`planner/dev/admin`) ne doit pas masquer l'absence des rôles delivery spécialisés.
  - en phase delivery, le crontab doit inclure explicitement: `planner`, `backend_engineer`, `frontend_engineer`, `data_analyst` (stagger recommandé dans `docs/ops/ORCHESTRATION_AGENTS_READY.md`).

---

## ✅ Validations passées

| Gate | Résultat | Notes |
|------|----------|-------|
| `validate_agent_workspace_layout.sh` | 21/21 pass | Structure racine, memory, docs |
| `validate_parallel_plumbing.sh` | 18/18 ok | Board, cron, rôle policy |
| `backend_regression_gate.sh` | 39 tests + live endpoints | health, stocks_prices, news_feed OK |
| `dev_qa_tooling_check.sh` | 23/23 ok | OpenClaw, skills, scripts |

---

## Structure active (post-migration)

- **Backend:** `apps/api/src/` (domains: forecasts, judge, market_data, copilot)
- **Frontend:** `apps/web/src/domains/`
- **Runtime:** `apps/api/runtime/` (data, cache, api.log)
- **Jobs:** `apps/api/src/platform/legacy/jobs/`
- **Archive:** `archive/structure-migrations/` (copilot-app résiduel archivé)
- **Gates:** `evidence/gates/openclaw-gates/` (alias: `finance-app/openclaw-gates` → symlink)

**Symlinks:** Catalogue complet et chemins canoniques → `docs/ops/SYMLINKS_CATALOG.md`  
**Orchestration:** Validation et blocages connus → `docs/ops/ORCHESTRATION_AGENTS_READY.md`

---

## Mémoire & Contexte (3-Day Continuity)

**Strategy:** Agents chargent une fenêtre 3 jours, profilée par rôle, pour limiter les tokens sans perdre la continuité utile.

- **Default mode:** `TMUX_ROLE_CONTEXT_MODE=lean`
- **Role profiles:** `coordination`, `analysis`, `delivery` (auto par rôle dans le runner)
- **Memory budgets (lean):**
  - coordination: daily=24, role_history=18
  - analysis: daily=14, role_history=12
  - delivery: daily=8, role_history=8
- **Retry compaction:** dispatch `retry` utilise un protocole orchestration compact (moins de token burn/timeouts)
- **Daily logs:** `memory/YYYY-MM-DD.md` (ou `memory/summaries/YYYY-MM-DD.summary.md` si présent)
- **Role history source:** `memory/agents/summaries/${ROLE}.summary.md` (sinon fallback `memory/agents/${ROLE}.md`)
- **Auto role summary:** `scripts/role_memory_append.py` génère `memory/agents/summaries/${ROLE}.summary.md` (fenêtre 14 entrées)
- **Injection point:** `scripts/cron_tmux_role_runner.sh` fonction `load_3day_memory_context()`
- **Anti-regression guards:** Inclus dans SYSTEM_PROMPT (références copilot-app/ → archive/, backend/src/backend/src → apps/api/src/)
- **Monitoring traces:** `dispatch_prompt scope=primary|retry ... bytes=<n>` + `prompt_memory_context ... bytes=<n>`

**Archit benefit:** Continuity conservée avec coût token fortement réduit, surtout pour rôles delivery.

**Reference:** `docs/ops/ROLE_MEMORY_STRATEGY_3DAY.md`

---

## Références obligatoires avant de travailler

1. **AGENTS.md** – règles, mémoire, sécurité, heartbeats
2. **docs/ops/AGENT_WORKSPACE_INDEX.md** – index rapide
3. **docs/ops/AGENT_ONBOARDING.md** – onboarding architecture
4. **docs/product/planning/tasks.md** – tâches en cours
5. **docs/ops/API_ENDPOINTS.md** – endpoints backend frontend
6. **docs/ops/OPENCLAW_BROWSER_QA.md** – validation frontend avec navigateur OpenClaw
7. **docs/ops/DEV_AGENT_AUTONOMY_PROTOCOL.md** – protocole autonomie dev (architecture-first, reuse-first, QA proofs)

---

## Règles pour les agents

- **Judge template:** `apps/api/src/domains/judge/api/judge.py` est **immutable** (template de référence)
- **Chemins:** utiliser `apps/api/`, `apps/web/`, pas `copilot-app/`
- **Symlinks:** privilégier les chemins canoniques (voir `docs/ops/SYMLINKS_CATALOG.md`) ; ne pas en créer sans les documenter
- **Gate avant commit:** `bash scripts/backend_regression_gate.sh`
- **Command safety:** `platform/policies/exec_safe.sh` pour commandes shell

---

## Services

- Backend: http://localhost:8050 (docs: /docs)
- Frontend: http://localhost:5173

---

## Pre-flight rapide (avant de commencer)

```bash
# Vérifier structure
bash scripts/validate_agent_workspace_layout.sh

# Vérifier backend + tests (backend doit tourner)
bash scripts/backend_regression_gate.sh --no-live   # ou sans --no-live pour live endpoints
```

---

## Fichiers modifiés récemment (2026-02-28)

Voir `memory/2026-02-28.md` et `docs/ops/REMPISE_ORDRE_POST_MIGRATION.md` pour l'historique des corrections post-migration.

---

*Ce document peut être lu en premier par tout agent qui reprend le travail.*
