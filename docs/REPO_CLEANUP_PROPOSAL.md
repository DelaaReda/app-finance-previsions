# Repo cleanup proposal (non-destructive)

This file lists low-risk cleanup actions proposed for the repository. This is a non-destructive plan: every change must be done via a PR that moves files into `archive/` and includes test runs, screenshots (if relevant), and owner approvals.

Proposed categories and candidate files

- Backups and local copies (move to `archive/backups/`):
  - `AGENTS_MESSAGES.md.backup`, `AGENTS_MESSAGES.md.bak`, any `*.backup` or `*.bak` at repo root

- Old drafts and exports (move to `archive/drafts/`):
  - `markdowns/CONTEXT_EXPORT*.md` (if older than 6 months and already captured elsewhere)

- Non-product demo/training folders (move to `archive/untracked/`):
  - `folder-not-part-of-project-agent-stack-oss/` — contains demos and training scripts; keep if actively used, otherwise archive.

- Temporary artifacts (archive or remove after review):
  - `proofs/FC-HOTFIX-*` — review contents and move older proofs to `archive/proofs/`.

Files already handled or removed

- `copilot-app/frontend/webapp/src/App-with-ErrorBoundary.tsx` — legacy; already deleted in prior step.

Proposed process for each cleanup candidate

1. Create a branch `chore/archive-<category>-<short>`.
2. Move files into `archive/<category>/` preserving directory structure (git mv).
3. Update `docs/REPO_CLEANUP_PROPOSAL.md` to note the PR and list moved files.
4. Run frontend `pnpm run -s typecheck` and `pnpm exec eslint --ext .ts,.tsx src` and attach outputs to PR.
5. Request review from affected owners and wait 48 hours for objections.

Example shell snippet (to include in PR description):

```bash
# move backups
mkdir -p archive/backups
git mv AGENTS_MESSAGES.md.backup archive/backups/ || true
git mv AGENTS_MESSAGES.md.bak archive/backups/ || true

# move untracked folder
mkdir -p archive/untracked
git mv folder-not-part-of-project-agent-stack-oss archive/untracked/ || true

git commit -m "chore(archive): move backups & demos to archive/backups & archive/untracked"
git push --set-upstream origin chore/archive-backups
```

Approval & roll-back

- If any archived files are needed after the archive PR merges, they can be restored with `git mv archive/... <original-path>` and a small revert PR.

Next steps

- Please review this proposal and add or remove candidate files. Once approved, I can create a single PR that moves the approved files to `archive/` and runs the checks.
