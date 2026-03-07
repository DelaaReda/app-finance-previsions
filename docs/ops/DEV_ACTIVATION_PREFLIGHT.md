status: canonical
last_verified: 2026-03-07

# Dev Activation Preflight

Use this before re-enabling planner-driven development.

Command:

```bash
bash scripts/dev_activation_preflight.sh
```

What it checks:

- local monitor `/api/status`
- local doctor `/api/doctor?refresh=1`
- runtime lifecycle is `running`
- execution mode is `planner_experimental`
- delivery integrity is `ok`
- product priority guard is not blocking
- planner dispatch is not stalled/degraded
- OpenClaw/Codex bridge validates cleanly for planner

What blocks activation:

- `product_priority_guard` blocked, for example `news_stale`
- `planner_dispatch_needed`
- `ready_dev_stalled`
- recent dispatch fallback-like signals
- bridge validation failure
- monitor or doctor unavailable

Output:

- JSON to stdout
- persisted report in runtime state as `dev-activation-readiness.json`

Use the report as the cutover gate. Do not enable development when it returns `ready=false`.
