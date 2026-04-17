---
status: active
last_verified: 2026-04-16
---

# EC2 App Runtime Quick Reference

Purpose:
- tell VM agents where the app actually runs
- prevent accidental local app runtime on the UTM VM
- keep app checks and restarts consistent across the team

## Hard rules
- The public app-serving stack lives on AWS EC2, not on the local UTM VM.
- Do not run backend, frontend, or monitor servers on the UTM VM for normal team work.
- From the UTM VM, use public HTTP endpoints for app validation.
- From the UTM VM, use the AWS remote control wrapper for app start/stop/restart.
- Local loopback app URLs (`127.0.0.1:8050`, `127.0.0.1:5173`, `127.0.0.1:7779`) are not valid on the UTM VM.
- If another doc still shows `localhost:*` as the normal app path, this quick reference wins. Treat those older examples as historical evidence unless they explicitly say host-local debug or VM control-plane only.

## Canonical public endpoints
- Frontend: `http://3.98.20.77/`
- API base: `http://3.98.20.77/api/`
- API health: `http://3.98.20.77/api/health`
- Monitor UI: `http://3.98.20.77:8080/`
- Monitor status: `http://3.98.20.77:8080/api/status?lite=1`

## Canonical control path
- Wrapper: `scripts/aws_remote_app_control.sh`

From the UTM VM:
```bash
/home/venom/analyse-financiere/scripts/aws_remote_app_control.sh instance-status
/home/venom/analyse-financiere/scripts/aws_remote_app_control.sh status
/home/venom/analyse-financiere/scripts/aws_remote_app_control.sh restart
/home/venom/analyse-financiere/scripts/aws_remote_app_control.sh public-status
```

Behavior:
- the wrapper can start the EC2 instance if it was auto-stopped
- the wrapper waits for the instance to be reachable before app control
- runtime restart is serialized on the EC2 host to avoid concurrent restarts
- during a real publication/restart window, the wrapper may return `MAINTENANCE` instead of raw app JSON
- public smokes can return `DEFER reason=runtime_restart_in_progress`; that is transient, not a durable outage

## Validation from the UTM VM
```bash
curl -fsS http://3.98.20.77/api/health
curl -fsS http://3.98.20.77:8080/api/status?lite=1
```

## Maintenance semantics
- `MAINTENANCE` or `DEFER reason=runtime_restart_in_progress` means the EC2 host is being restarted/published right now.
- Do not classify that state as `external_outage`, `sync failed`, or `delivery blocked by EC2` on its own.
- Wait roughly 20 to 30 seconds, then retry the same public proof.

## Sync ownership
- Mac <-> UTM VM = shared workspace view of the same repo.
- This local Mac/VM sync is not app publication.
- App publication to EC2 is a second, separate layer: shared workspace -> AWS.
- Canonical operator path is Mac-side publication. If the operator intentionally launches the same wrapper from the UTM VM, it still publishes the same shared workspace snapshot, not VM-local orchestration state.
- Publication is manual by default.
- `scripts/aws_app_sync_and_restart.sh watch` is allowed only when intentionally launched on a workspace host under operator control.
- VM agents should not invent their own publish path.
- VM agents must not assume that local repo edits are already reflected on AWS.
- Use the shared repo and the canonical AWS wrapper/control path.

## What sync actually pushes
- Sync scope is intentionally limited to the app-serving workspace, not the full orchestration workspace.
- Main synced paths:
  - `apps/api`
  - `apps/web`
  - `apps/monitor`
  - `packages`
  - `platform`
  - `finance-copilot.sh`
  - `scripts/monitor_stack_guard.sh`
  - `scripts/critical_endpoints_smoke.sh`
  - `scripts/fc_health_check.sh`
- Main excluded paths/artifacts:
  - `logs-codex-runs/`
  - `memory/`
  - `docs/operations/orchestrator/`
  - `apps/api/runtime/data/`
  - `apps/api/runtime/cache/`
  - local DB/runtime artifacts (`*.sqlite`, `*.sqlite3`, `*.db`)
  - local virtualenvs / caches / `node_modules`
- Consequence:
  - EC2 receives app code + required support code
  - EC2 does not receive local orchestration state/history
  - absence of orchestration artifacts on EC2 is normal

## Expected propagation after sync or restart
- Public API changes can appear in about 5 seconds.
- Full sync + restart + public verification can take about 20 to 30 seconds.
- After a sync or restart, do not declare the app broken immediately.
- Wait for the wrapper or verification step to finish before escalating.

## Auto-stop
- EC2 app host auto-stops after 10 minutes without HTTP traffic.
- SSH activity does not keep the host alive.
- If the host was stopped, use `scripts/aws_remote_app_control.sh` and let it wake the instance first.
