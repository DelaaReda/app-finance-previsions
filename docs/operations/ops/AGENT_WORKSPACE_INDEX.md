# Agent Workspace Index

Canonical locations to keep the multi-agent workspace easy to navigate.

## 1) Root (identity + startup)

- `AGENTS.md` (global operating rules)
- `SOUL.md` (assistant identity)
- `USER.md` (owner profile)
- `MEMORY.md` (long-term memory, main session only)
- `TOOLS.md` (local tools and credentials map)
- `HEARTBEAT.md` (proactive checklist)
- `README.md` (project overview)
- `finance-copilot.sh` (entrypoint wrapper)
- `docs/WORKSPACE_MAP.md` (central docs map)

## 2) Memory (single source)

- Daily logs only in `memory/YYYY-MM-DD.md`
- Agent-specific logs in `memory/agents/*.md`
- Chat transcripts in `memory/chat-journal/`
- Agent mémoire hub (Vue consolidée) : `docs/memory-hub`
- Imported legacy notes in `memory/imported-from-openclaw-workspace/`
- Archived non-standard memory files in `memory/archive/`
- Quick links:
  - `memory/today.md` -> current day log
  - `memory/yesterday.md` -> previous day log

## 3) Planning and delivery

- Product and backlog: `docs/planning/`
- Sprint docs: `docs/scrum/`
- Product backlog and tasks hub: `docs/tasks-hub/` (alias vers `docs/product/planning`)
- Ops runbooks and architecture: `docs/ops/`, `docs/orchestrator-ops/`
- Orchestrator state and locks: `docs/orchestrator-ops/`
- Security docs: `docs/safety/`

## 3b) Architecture centre de référence

- `docs/architecture/AGENT_ONBOARDING.md`
- `docs/architecture/ARCHITECTURE_MAP.md`
- `docs/architecture/ARCHITECTURE_STYLE_GUIDE.md`
- `docs/architecture/TARGET_ARCHITECTURE_LAYOUT.md`
- `docs/architecture/LARGE_MODULE_REUSE_INDEX.md`
- `docs/architecture/REUSE_MODULES_CATALOG.md`
- `docs/architecture/APP_SRC_UNIFICATION.md`

## 4) Application code

- App root: `apps/`
- Backend: `apps/api/src/`
- Frontend: `apps/web/src/`
- Runtime: `apps/api/runtime/data`, `apps/api/runtime/cache`

## 5) Runtime and heavy technical artifacts

- Runtime technical dirs: `apps/api/runtime/`, `archive/`
- Archived migrations/cleanup artifacts: `archive/`

## 7) Navigation post-migration

- Central workspace map: `docs/operations/AGENT_WORKSPACE_INDEX.md`
- Post-migration and architecture recovery docs:
  - `docs/operations/MIGRATION_SUMMARY.md`
  - `docs/operations/STABILISATION_POST_MIGRATION.md`
  - `docs/operations/POST_MIGRATION_RECOVERY.md`

## 6) Validation

Run:

```bash
bash scripts/validate_agent_workspace_layout.sh
```

This checks required files and updates `memory/today.md` + `memory/yesterday.md`.
