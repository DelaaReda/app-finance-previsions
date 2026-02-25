# CRON STRATEGY v1

## Current baseline
- Planning cron is active at high frequency (currently every 5 minutes).

## Recommended operating cadence

### 1) Planning Incremental Loop
- Frequency: every 5–15 minutes (5 for active delivery windows, 15 for normal mode)
- Goal: update planning deltas only, never reset.
- Inputs:
  - `docs/planning/WORKSTATE.md`
  - `docs/planning/mvp-plan.md`
  - `docs/planning/epics.md`
  - `docs/planning/stories.md`
  - `docs/planning/tasks.md`
- Output: delta updates + checkpoint + changelog.

### 2) Health + Smoke Loop
- Frequency: every 30 minutes
- Goal: catch runtime regressions early.
- Checks:
  - `/api/health`
  - minimal endpoint smoke set

### 3) Skill Security + AV Loop
- Frequency: 2 times/day
- Goal: detect malicious drift in installed skills.
- Checks:
  - obfuscation scan
  - AV scan (`scripts/skill_av_scan.sh`)

### 4) Daily Executive Synthesis
- Frequency: once daily (evening)
- Goal: top 3 priorities for next day + top blockers + KPI snapshot.

---

## Guardrails for all cron jobs
- Incremental only (no restart from zero)
- No-op protection (`NO_DELTA` behavior)
- Commit only when real changes exist
- Structured output required:
  - `STATUS`
  - `DELTA`
  - `EVIDENCE`
  - `RISKS`
  - `NEXT`

---

## Failure handling
- 1st failure: retry next cycle
- 2nd consecutive failure: mark run degraded
- 3rd consecutive failure: open blocker note in planning + require manual inspection
