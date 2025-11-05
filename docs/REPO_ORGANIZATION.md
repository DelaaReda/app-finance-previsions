# Repo organization & conventions — Finance Copilot

This document describes the current repository layout, conventions for contributors/agents, and recommended safe actions for organizing/cleaning the repo. It is written to help agents coordinate without stepping on each other's work.

Last updated: 2025-11-05

## High-level layout

- `copilot-app/` — main application
  - `frontend/webapp/` — React + Vite frontend (TypeScript)
  - `backend/` — Python backend (FastAPI)
  - `scripts/`, `docs/`, `tests/` — app-specific tools
- `data/` — persisted snapshots used by backend (JSON/Parquet)
- `docs/` — product and developer docs
- `proofs/` — evidence artifacts (screenshots, reports)
- `models/` — trained model artifacts
- `markdowns/` — historical notes and exports

## Conventions and rules

- Work via the team script: use `./finance-copilot.sh start` / `stop` / `status` to run the stack.
- Small PRs: keep changes < 300 lines where possible; 1 task = 1 lock (see `.locks/`).
- Never delete files owned by another agent without a signed-off PR; prefer moving to `archive/` via PR.
- Always run `pnpm run -s typecheck` and `pnpm exec eslint` (frontend) before proposing large changes.
- Codacy policy: run `codacy_cli_analyze` after edits if available (see .github/instructions). If you cannot run Codacy, note this in the PR and tag the repo owner.

## Frontend conventions

- API base: frontend clients use `import.meta.env.VITE_API_BASE_URL ?? '/api'`.
- Safe access helpers: use canonical `@/lib/safe` helpers (`ensureArray`, `safeGet`, `safeMap`) to avoid runtime crashes.
- UI primitives: import from `@/ui` wrappers only (Button/Card/EmptyState/...). Pages should not import Mantine/Tremor components directly unless in `src/ui/` wrappers.
- Tests: Playwright selectors should rely on `data-testid` attributes.

## Cleaning rules (non-destructive first)

1. Do not delete files directly. Create a PR that moves candidate files into an `archive/` folder at repository root. The PR should list each moved file and the reason.
2. For large deletions (backups, old proofs), propose them in `docs/REPO_CLEANUP_PROPOSAL.md` first and wait for 48h for objections from other agents.
3. For files that look like local backups (`*.backup`, `*.bak`) prefer to move them to `archive/backups/`.
4. For directories that are not part of the product (e.g., `folder-not-part-of-project-agent-stack-oss/`), move to `archive/untracked/` and reference in the PR.

## Ownership & communication

- Before editing shared areas (UI, API clients, scheduler), post a short intent message in `COMMS/AGENTS_MESSAGES.md` with `owner`, `ETA`, and `files modified`.
- Acquire a lock in `.locks/` when a task will modify many files or critical pipelines (one lock per active task).

## Quick checklist for a safe cleanup PR

1. Create a branch `chore/cleanup-<short-desc>`.
2. Move files to `archive/<category>/` instead of deleting.
3. Update `docs/REPO_CLEANUP_PROPOSAL.md` with the list and rationale.
4. Run `pnpm run -s typecheck` and `pnpm exec eslint --ext .ts,.tsx src` and include outputs in PR.
5. Request reviews from `@ALEX-BACKEND-SUPERMAN-7` and `@NORA-PRODUCT-OWNER-SPIDERWOMAN-11` (or current owners listed in `COMMS/`).

---

If you want, I can now (A) create the non-destructive `archive/` tree and move a small set of low-risk files there in a single PR, or (B) only produce the proposal and let agents vote. Which do you prefer?
