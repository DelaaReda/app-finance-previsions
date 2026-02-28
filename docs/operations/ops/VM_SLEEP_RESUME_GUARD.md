# VM Sleep/Resume Guard

## Problem

When the VM sleeps (host suspend or VM pause), timers drift and on resume you can see:
- cron gateway timeouts
- bursts of delayed cron runs
- stale runningAtMs states (ghost running jobs)
- missing tmux sessions

## Goal

Minimize impact when sleep/resume happens:
- detect resume quickly
- auto-heal stale cron state
- re-warm essential tmux sessions (admins + core roles)
- re-run deterministic health/triage

## Implementation

- Script: `scripts/vm_resume_guard.sh`
- Cron: `vm-resume-guard-2m` (delivery none)

### Resume detection heuristic

Store last tick epoch in `~/.openclaw/state/vm_resume_guard/last_epoch.txt`.
If gap > `VM_RESUME_GUARD_GAP_SECONDS` (default 420s), treat as resume.

### Actions on resume

1. Ensure OpenClaw gateway is active (restart if needed).
2. Run stale sweep apply (`scripts/stale_cron_tick.sh`).
3. Ensure tmux sessions exist for:
   - `adminapp_codex_sync`, `admin-agents-sync-cron`, `clawsentinel`
   - core role sessions `codex_planner_cron`, `codex_dev_cron`, `codex_tester_cron`, `codex_qa_cron`
4. Print a compact triage summary (`scripts/triage_now.sh`).

### Notes

- The guard avoids expensive LLM work. It does not dispatch product tasks; it only heals infra.
- For fully preventing sleep, see `docs/ops/ADMIN_POST_RESTART_RUNBOOK.md` (requires sudo).
