# Root Cleanup Report

Scope: workspace root cleanup to reduce top-level clutter and relocate files to domain folders.

## Files moved from root

- `AGENT_WORKFLOW.md` -> `docs/ops/AGENT_WORKFLOW.md`
- `ARCHITECTURE_MAP.md` -> `docs/ops/ARCHITECTURE_MAP.md`
- `LEGACY_POLICY.md` -> `docs/ops/LEGACY_POLICY.md`
- `MVP_SCOPE.md` -> `docs/planning/MVP_SCOPE.md`
- `PROJECT_BOARD.md` -> `docs/planning/PROJECT_BOARD.md`
- `SECURITY_ALLOWLIST.md` -> `docs/safety/SECURITY_ALLOWLIST.md`
- `SECURITY_AUDIT_REPORT.md` -> `docs/safety/SECURITY_AUDIT_REPORT.md`
- `SECURITY_REPORT.md` -> `docs/safety/SECURITY_REPORT.md`
- `analyse_nora.txt` -> `docs/planning/raw-inputs/analyse_nora.txt`
- `consignes.txt` -> `docs/planning/raw-inputs/consignes.txt`
- `equity_snapshot_step1_meta_core.md` -> `docs/planning/raw-inputs/equity_snapshot_step1_meta_core.md`
- `modules.txt` -> `docs/planning/raw-inputs/modules.txt`
- `resultat.json` -> `archive/root-artifacts/resultat.json`
- `.DS_Store` -> removed

## Follow-up compatibility update

- `scripts/update_direct_crons.sh` now references:
  - `docs/ops/AGENT_WORKFLOW.md` (instead of root `AGENT_WORKFLOW.md`)

## Root policy after cleanup

- Keep only high-signal control files at root (`AGENTS.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, `README.md`, tooling wrappers).
- Store planning/security/operations documents under `docs/`.
- Store raw one-off artifacts under `archive/` or `docs/planning/raw-inputs/`.
