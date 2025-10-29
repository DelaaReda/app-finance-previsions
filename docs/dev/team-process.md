# Team Process — Multi‑Agents (Dev / Architect / QA)

This repo is set up for collaborative work between profiles (senior/junior devs, architect, QA) with clear guardrails and shared visibility.

Key Files
- CODEOWNERS: `.github/CODEOWNERS` — routes reviews to owners
- PR template: `.github/PULL_REQUEST_TEMPLATE.md` — DoD, risks, tests, PROGRESS.md updates
- Issue templates: `.github/ISSUE_TEMPLATE/{story,bug}.md` — standardize backlog items
- pre‑commit: `.pre-commit-config.yaml` — ruff / format / yaml / secrets
- CI: `.github/workflows/ci.yml` — lint/type/tests on 3.11/3.12

Working Agreement
- Branching: feature branches per unit of work: `feat/<scope>`, `fix/<scope>`, `chore/<scope>`
- Commits: prefix with sprint and scope (e.g., `Sprint-5: feat(dash): …`)
- Reviews: CODEOWNERS auto‑requested; at least 1 owner approval
- Docs cadence: update `docs/PROGRESS.md` on every meaningful PR (Delivered / Next / How‑to‑Run)
- UI discipline: no network calls in UI; read latest partitions; empty states in FR; logs helpful

Roles
- Architect
  - ADRs in `docs/architecture/adr/*`, data contracts, page specs, test strategy
  - Ensures reuse (no duplication), schedules in Makefile, idempotence for agents
- Dev
  - Implements features against page specs, adds tests; keeps pre‑commit clean
  - Updates `docs/PROGRESS.md`; adds screenshots if UI
- QA
  - Uses tester pages and Playwright smoke to verify routes/components
  - Files bug issues with reproduction & severity; pushes test fixes

Pre‑commit
- One‑time: `pre-commit install`; then `pre-commit run -a`
- Optional secret baseline: `detect-secrets scan > .secrets.baseline`

CI
- Lint + format (ruff) and mypy (best effort)
- Tests on Python 3.11 & 3.12; upload coverage

Backlog hygiene
- Create Story issues for features; create Bug issues for regressions
- Link issues in PRs; validate DoD checkboxes

Notes
- Keep Makefile targets cohesive; no hardcoded secrets in repo
- Prefer explicit IDs in Dash pages for reliable UI tests
- If in doubt, reference `docs/dev/engineering_rules.md`
