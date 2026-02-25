# WORKSTATE (MVP Planner Continuity)

Use this file to continue work between cron runs without restarting from zero.

## Last run checkpoint
- last_run_at:
- status: IN_PROGRESS | DONE | BLOCKED
- current_phase: repo-analysis | mvp-plan | epics | stories | tasks | validation
- next_action:

## Progress ledger
- [ ] Repo analysis baseline completed
- [ ] MVP scope stabilized
- [ ] Epics drafted and prioritized
- [ ] Stories drafted with acceptance criteria
- [ ] Tasks drafted with test commands and evidence expectations

## Resume protocol
1. Read `docs/planning/WORKSTATE.md` first.
2. Read existing artifacts:
   - `docs/planning/mvp-plan.md`
   - `docs/planning/epics.md`
   - `docs/planning/stories.md`
   - `docs/planning/tasks.md`
3. Apply only delta updates; never rewrite from scratch unless corruption is detected.
4. Update checkpoint fields (`last_run_at`, `current_phase`, `next_action`).
5. Append a short changelog section at end of each planning file with timestamp.
