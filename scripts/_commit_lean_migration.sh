#!/usr/bin/env bash
# Commit de la migration lean team
# Lance depuis la VM: bash scripts/_commit_lean_migration.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

git add \
  docs/ORCHESTRATION_LEAN.md \
  docs/operations/orchestrator/parallel-role-cron-map.json \
  memory/agents/dev.md \
  memory/agents/planner.md \
  memory/agents/admin.md \
  scripts/fc_agent_tick.sh \
  scripts/cron_tmux_role_runner.sh \
  scripts/install_lean_crontab.sh \
  scripts/setup_lean_team.sh \
  scripts/migrate_workboard_lean.py \
  apps/api/src/platform/legacy/jobs/forecasts_simple.py

git commit -m "refactor(orchestration): lean team 3 rôles + forecasts multi-signal v2

- 10 rôles → 3: dev (builds+QA) | planner (vision+specs) | admin (ops+health)
- fc_agent_tick.sh: mapping consolidation + seuls dev/planner/admin acceptés
- cron-map: cadences anti-collision (dev:20m, planner:35m, admin:15m)
- memory/agents: dev.md + planner.md (épuré) + admin.md (nouveau)
- forecasts_simple.py: confidence multi-signal v2 (1d 50% + 5d 30% + updays 20%)
  → confidence 40-85% au lieu de 45-55% fixe
- docs/ORCHESTRATION_LEAN.md: guide complet pour agents et owner
- scripts: setup_lean_team.sh + install_lean_crontab.sh + migrate_workboard_lean.py

Impact: -70% appels Codex, zéro boucle planner, forecasts réalistes"
