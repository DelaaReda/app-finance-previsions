# État prêt pour agents – 2026-02-28

**Validé par:** admin principal  
**Date:** 2026-02-28  

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

**Strategy:** Agents chargent les 3 derniers jours de memory pour éviter régression architecturale.

- **Daily logs:** `memory/YYYY-MM-DD.md` (assemblés automatiquement, 150 lignes max/jour)
- **Role history:** `memory/agents/${ROLE}.md` (50 lignes dernières décisions)
- **Injection point:** `scripts/cron_tmux_role_runner.sh` fonction `load_3day_memory_context()`
- **Anti-regression guards:** Inclus dans SYSTEM_PROMPT (références copilot-app/ → archive/, backend/src/backend/src → apps/api/src/)

**Archit benefit:** Agents comprennent les 3 derniers jours de décisions sans charger full MEMORY.md.

**Reference:** `docs/ops/ROLE_MEMORY_STRATEGY_3DAY.md`

---

## Références obligatoires avant de travailler

1. **AGENTS.md** – règles, mémoire, sécurité, heartbeats
2. **docs/ops/AGENT_WORKSPACE_INDEX.md** – index rapide
3. **docs/operations/AGENT_ONBOARDING.md** – onboarding architecture
4. **docs/product/planning/tasks.md** – tâches en cours

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
