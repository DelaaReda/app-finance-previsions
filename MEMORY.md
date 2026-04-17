# MEMORY

## Owner profile
- Owner: venom (Reda).
- Main language in chat: French.
- Project: analyse-financiere.
- Working preference: operate in "dev exemplaire" mode (strict scope, tests, proof-first reporting, explicit blockers).
- Product collaboration preference: assistant should act as a "VISION PRODUCT CLARIFIER":
  - analyze current product artifacts first,
  - then ask targeted clarification questions to lock the final product goal,
  - then derive epics/priorities/sprint goals from that clarified vision.
- Product intent clarified (2026-02-26):
  - personal-first finance copilot for daily portfolio decisions,
  - low runtime cost target (free/low-cost model providers for backend inference),
  - OpenAI Pro budget used for development acceleration more than runtime serving,
  - decision workflow target: 2-3 clicks with near-real-time freshness (~10 min gap acceptable).

## Admin agents ownership
- Active tri-admin identities:
  - `adminapp-codex` (runtime governance owner)
  - `admin-agents` (delivery productivity owner)
  - `clawsentinel` (safety/quality owner)
  - `inspecteur` (codebase audit & reporting owner) - **ENGAGÉ 2026-02-27**
- Operational command chain:
  - `main` on WhatsApp acts as Operational Director.
  - `main` gives directives to admins only.
  - admins translate directives into delivery process and task routing.
  - communication flow: `main -> admins -> delivery`, and escalation flow: `delivery -> admins -> main`.
- Shared responsibility scope:
  - cron governance and anti-drift enforcement (`runner-only` payload, no direct orchestrator call in payload),
  - runtime stability for role jobs,
  - logging hygiene and traceability,
  - shared MVP delivery progress per iteration.
- Execution standard for admin interventions:
  - `lock -> backup -> minimal edit -> force-run validation -> journal`.

## OpenClaw runtime truth
- OpenClaw runs in UTM Ubuntu VM, not on the Mac host.
- Workspace root: /home/venom/analyse-financiere
- Service: openclaw-gateway.service (systemd --user), enabled with auto-restart.
- Linger is enabled for user venom (service survives reboots without interactive login).
- Runtime pinned on current user-global install path (not `/usr/lib/node_modules`):
  - `/home/venom/.npm-global/lib/node_modules/openclaw`
- Current validated runtime version: `2026.2.24`.

## SSH MCP Architecture (2026-03-01)
- **Socket Server Infrastructure:**
  - Persistent Unix socket server at `~/.ssh/mcp.sock` (zero-churn design)
  - LaunchAgent `com.venom.ssh-mcp` keeps server alive with `KeepAlive=true`
  - Wrapper proxy `/Users/venom/ssh_mcp_wrapper.sh` relays Claude stdin/stdout → socket
  - Claude Desktop config: `mcpServers.ssh` calls wrapper (not socket directly)
  - Auto-restart on crash, persists across reboot (`RunAtLoad=true`)

- **File Sharing Between Mac & VM:**
  - SSH MCP can pull files from VM to Mac for image/data analysis
  - **Workflow:** VM → scp/ssh → `/Users/venom/Documents/analyse-financiere` (shared sync'd path)
  - This folder is mounted in VM as `/home/venom/analyse-financiere`
  - For Claude to view/analyze images: copy to analyse-financière workspace first, then upload to chat
  - **Example:** `scp /vm/path/image.png venom@mac:/Users/venom/Documents/analyse-financiere/evidence/` then reference in chat
  - Canonical location for images: `evidence/gates/*` (gates evidence), `evidence/proofs/*` (validation proofs), `evidence/runtime/*` (runtime artifacts)

- Persistent role-agent baseline is now formalized:
  - catalog: `docs/orchestrator-ops/openclaw-agent-catalog.json`
  - bootstrap: `scripts/bootstrap_openclaw_agents.sh`
  - per-agent notes: `memory/agents/<agent_id>.md`
  - admin crons are bound to explicit `agentId` values (`adminapp-codex`, `admin-agents`) instead of null/default.
- Parallel role crons now run with wake-up context hydration:
  - each tick loads role memory, last role contract, peer contracts, admin chat tail, and workboard role context,
  - each role persists `last_contract` in `/home/venom/.openclaw/cron/role-state/<role>.last_contract` for resume-after-stop behavior,
  - workboard writes are file-locked in `parallel_workstream.py` to avoid race conditions under concurrent cron runs.

## Security and channel policy
- WhatsApp is enabled with strict allowlist mode.
- Allowed direct number: +14389799898 only.
- Group policy: allowlist.
- Do not send pairing or outbound messages to unknown contacts.
- For this VM test environment, permissive execution policy is accepted:
  - `agents.defaults.sandbox.mode=off`
  - exec approvals allowlist includes `"/home/venom/**"` and `"/**"` for agent `*`.
- Tavily skill (`tavily-search`) is approved for use after manual integrity check:
  - local hashes match ClawHub registry v1.0.0;
  - expected behavior is API-key read + outbound calls to `api.tavily.com` only.

## Memory policy
- Durable facts and decisions must be written in this file (MEMORY.md).
- Short-term work logs go to memory/YYYY-MM-DD.md.
- On /new or /reset, save key context before reset.

## Technical constraints
- Do not use Docker in this VM for project workflow.
- Keep operations scoped to this repository.
- Runtime policy is codex-only for orchestration; legacy qwen scripts are archived/renamed `*_not_used`.

## AWS app runtime migration (2026-04-16)
- The public app-serving stack now runs on AWS EC2, not on the local UTM VM.
- Canonical public endpoints:
  - frontend: `http://3.98.20.77/`
  - api: `http://3.98.20.77/api/...`
  - monitor: `http://3.98.20.77:8080/`
- The UTM VM remains the orchestration host only. Do not run backend/frontend/monitor locally there for normal team work.
- VM-side app control must use `scripts/aws_remote_app_control.sh`.
- Mac and the UTM VM share the same workspace view.
- Mac <-> UTM VM share the same workspace view; AWS publication is a separate shared-workspace -> EC2 step.
- Canonical operator path is Mac-side publication; an explicit UTM-triggered publication still ships the same shared workspace snapshot, not VM-local orchestration state.
- VM agents must not assume that local repo edits are already reflected on AWS until a real sync has been triggered.
- Public API changes usually appear in about 5 seconds after sync; full sync + restart + verification can take about 20 to 30 seconds.
- The EC2 app host auto-stops after 10 minutes without HTTP traffic; SSH does not keep it alive.

## Orchestration runbook note (2026-02-28)
- Stabilisation de la plomberie d’orchestration: création du lien `docs/orchestrator-ops` -> `docs/operations/orchestrator`, correction des checks pour utiliser un board de plomberie dédié (`parallel-workstreams-plumbing.json`) et passage des validations `dev_qa_tooling_check` / `validate_parallel_plumbing` en PASS.
- Verrous legacy `.json.lock` obsolètes retirés pour réduire les faux blocages de rôles (archivés dans `archive/obsolete-locks`).
- Role cron provisioning standard includes `--no-deliver` to avoid WhatsApp delivery target errors on isolated role jobs.
- `scripts/qwen_orchestrator.py` now supports cron-friendly watchdog checks:
  - `--tmux-cmd status --status-format text|compact|json`
  - `--tmux-cmd health` (strict fail with exit code 22 if required roles are down)
  - `--status-core-roles` for required role contract override.
- Orchestrator supports multi-role specialist teams for delivery depth:
  - flags: `--team-profile core|architecture|engineering|full` + `--specialists ...`
  - specialist roles: `analyst`, `architect`, `backend_engineer`, `frontend_engineer`, `data_engineer`, `security_engineer`, `devops_engineer`
  - legacy `--with-architect` remains compatible.
- OpenClaw tmux watchdog checks are driven by `admin-agents-supervisor-15m`; admin validation uses `python3 scripts/qwen_orchestrator.py --tmux-cmd health --status-format compact --status-core-roles planner,dev,tester,qa`.
- `qwen_orchestrator.py` health/status alias resolver now accepts both `qwen_*` and `codex_*` session families.
- Readiness detection now includes tmux child-process checks (not only `pane_current_command`), avoiding false BLOCKED when Qwen runs as `node ... qwen-code/cli.js`.
- Current OpenClaw cron profile (parallel specialist lanes + admins + utility):
  - 17 jobs total:
    - 14 role loops (`planner`, `analyst`, `architect`, `backend_engineer`, `frontend_engineer`, `integrator`, `data_analyst`, `infra_engineer`, `dev`, `tester`, `qa`, `po`, `scrum_master`, `clawsentinel`)
    - admin jobs: `adminapp-codex-sync-10m`, `admin-agents-supervisor-15m`
    - utility job: `stale-sweep-autoheal-7m`
  - each role cron calls `bash scripts/cron_tmux_role_runner.sh <role>` with env baseline:
    - `TMUX_ROLE_AGENT_BIN=codex`
    - `TMUX_ROLE_RETRY_ENGINE_DEFAULT=sdk`
    - `TMUX_ROLE_CODEX_EXEC_RESUME=1`
    - `PROMPT_TIMEOUT_SECONDS=55` (runner codex-exec floor `70s`)
    - `RETRY_PROMPT_TIMEOUT_SECONDS=30` (runner codex-exec floor `20s`)
    - `TMUX_ROLE_RECOVERY_THRESHOLD=2`
    - `TMUX_ROLE_NO_DELTA_THRESHOLD=12`
    - `SKIP_RETRY_ON_TIMEOUT=1`
    - `TMUX_ROLE_CODEX_EXEC_FALLBACK=1`
    - `TMUX_ROLE_CODEX_MODEL=gpt-5.3-codex`
    - `thinking=high`, `timeoutSeconds=480`, delivery `none`.
  - queue-first delivery gate:
    - no `READY` queue item => editable roles auto-fallback to analysis mode,
    - override only if explicitly needed: `TMUX_ROLE_ALLOW_WORKBOARD_ONLY_DELIVERY=1`.
  - current healthy runtime target:
    - `CRON_HEALTH_SUMMARY total=17 ok=17 blocked_signals=0 slow_over_180s=0`.
  - codex-only runtime policy:
    - role runner enforces `codex` CLI (no `qwen` fallback),
    - role sessions are codex-named (`codex_*_cron`) + `clawsentinel`,
    - recovery loop is tmux/codex-native (`scripts/auto_recover_tmux_roles.sh`) without orchestrator dependency.
  - near-real-time troubleshooting monitor:
    - `bash scripts/tmux_codex_live_monitor.sh --mode follow --engine capture`
    - persistent helper: `bash scripts/tmux_live_watchdog.sh start|status|stop` (tmux session `tmux_live_monitor`)
    - session logs in `logs-codex-runs/tmux-live/<session>.log` now include runner trace lines (`[trace:<role>]`) for low-latency debugging even when pane output is empty.
    - runner execution traces remain in `logs-codex-runs/role-runner/<role>.live.log`.
  - runner now uses robust parser paths (fixed stdin parse bug), strict 8-key normalization, and deterministic checkpoint fallback (`IN_PROGRESS/GO_WITH_CAUTION`) when output is non-parseable.
  - tri-admin shared iteration source is `docs/ops/ADMIN_TEAM_ITERATIONS.md` with mandatory signed entries from all 3 identities every iteration.
- `BATCH01_ARTIFACT_MISSING` was resolved on 2026-02-25 by publishing:
  - `finance-app/openclaw-gates/batch-01-20260225-000127.md` with `VERDICT: PASS`.
  - Priority queue now aligned: `BATCH-01=PASS`, `BATCH-02=READY`.
- Stale-running recovery is now a first-class admin path:
  - `admin-agents` detects `stale_running_jobs` when cron state shows `runningAtMs` but no live role-runner process.
  - `adminapp-codex` can auto-heal via `reset_stale_running_role_jobs_then_force_run_*` (disable/enable stale role jobs + targeted probes).
  - stale-reset actions bypass cooldown and do not trigger false repeat escalation when execution result is `done`.
- Role fallback contract was hardened:
  - `cron_tmux_role_runner.sh` now injects role-specific artifact markers in checkpoint fallback (`*_ARTIFACT=<source>`), reducing false `ROLE_CONTRACT_MISSING` for specialist lanes.
- Parallel role cron timeout baseline was raised from `300` to `480` seconds in provisioning scripts to absorb gateway + agent dispatch overhead on heavy turns.
- Dedicated stale-state utility exists:
  - `scripts/stale_cron_sweep.sh` provides dry-run/apply recovery for cron `runningAtMs` ghosts.
  - `adminapp-codex` now calls this sweep proactively when stale jobs are detected, then refreshes cron state and continues orchestration.
- Dedicated periodic stale-heal cron is now part of baseline provisioning:
  - job name: `stale-sweep-autoheal-7m`
  - agent: `adminapp-codex`
  - behavior: executes `scripts/stale_cron_tick.sh` -> `scripts/stale_cron_sweep.sh --apply`.
  - orchestration mode script (`set_orchestration_mode.sh`) now treats this as admin governance job (enable in admins-only/parallel, disable in paused).

## 3-Day Memory Strategy (2026-02-28)

Role agents now auto-load 3-day memory window to prevent architecture regression:
- Function: `load_3day_memory_context()` in `scripts/cron_tmux_role_runner.sh`
- Loads: last 3 daily logs (`memory/YYYY-MM-DD.md`, 150 lines/day) + role-specific history (`memory/agents/${ROLE}.md`, 50 lines)
- Token cost: ~770/session vs 3000+ with full MEMORY.md
- Injection: Prepended to SYSTEM_PROMPT with ANTI-REGRESSION guards (blocks copilot-app/*, backend/src/backend/src/*, legacy imports)
- Benefit: Recent architecture decisions visible; prevents regression to old paths
- Reference: `docs/ops/ROLE_MEMORY_STRATEGY_3DAY.md`
- Policy: Role sessions never load full MEMORY.md; use `memory_search()` on demand for older context
