# Admin Post-Restart Runbook

## Goal
Standardize what admin agents must verify right after a machine restart so the VM stays awake and cron automation stays healthy.

## Scope
- Host: Ubuntu VM (`/home/venom/analyse-financiere`)
- Runtime: OpenClaw gateway + tmux role cron jobs
- Safety: run commands via `scripts/exec_safe.sh`
- Codex baseline policy:
  - `docs/ops/ADMIN_CODEX_BASELINE.md`

## 0) Mandatory Snapshot Before VM Restart

Always capture a restart snapshot before changing VM CPU/RAM or rebooting:

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/admin_vm_snapshot.sh --note 'pre-vm-restart cpu/ram'"
```

The snapshot contains:
- OpenClaw status/config + cron state
- role-state files (`~/.openclaw/cron/role-state`)
- tmux pane scrollback captures
- recent OpenClaw session files
- admin continuity docs (`chat/iterations/watchdog/handoffs`)

After reboot, restore from latest snapshot:

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/admin_vm_restore.sh"
```

Optional explicit snapshot path:

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/admin_vm_restore.sh --snapshot /home/venom/.openclaw/snapshots/vm-restart-<timestamp>"
```

Operational note:
- `admin_vm_snapshot.sh` updates `/home/venom/.openclaw/snapshots/vm-restart-latest`.
- restore does not resurrect a Codex conversation byte-for-byte; it recreates admin sessions and reinjects context (resume packet + handoffs + role-state) for fast continuity.

## 1) Quick Health Check (mandatory)
Run these commands in order.

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "systemctl --user is-active openclaw-gateway.service && systemctl --user is-enabled openclaw-gateway.service"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw status"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw cron list --all"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "tmux ls"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/validate_parallel_plumbing.sh"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/tmux_live_watchdog.sh status || true"
```

Expected:
- gateway: `active` and `enabled`
- cron scheduler reachable and jobs listed (including admin continuity jobs)
- tmux lists admin sessions (`adminapp_codex_sync`, `admin-agents-*`, `clawsentinel`)
- plumbing validator: `failed=0`
- optional watchdog status is `status=yes` (if enabled)

If one or more admin sessions are missing after restore:

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/adminapp_codex_cron_tick.sh"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/admin_agents_tmux_tick.sh"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "bash scripts/validate_parallel_plumbing.sh"
```

## 2) Verify Sleep Is Still Disabled

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "systemctl is-enabled sleep.target suspend.target hibernate.target hybrid-sleep.target"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "sudo cat /etc/systemd/logind.conf.d/99-disable-sleep.conf"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type; gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout; gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type; gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "sudo journalctl -b --no-pager | rg -i 'suspend|hibernate|hybrid-sleep|PM: suspend|Suspending system|System resumed|sleep.target'"
```

Expected:
- all 4 targets are `masked`
- `/etc/systemd/logind.conf.d/99-disable-sleep.conf` contains:
  - `HandleLidSwitch=ignore`
  - `HandleLidSwitchExternalPower=ignore`
  - `HandleLidSwitchDocked=ignore`
  - `HandleSuspendKey=ignore`
  - `HandleHibernateKey=ignore`
  - `IdleAction=ignore`
- gsettings values:
  - AC type: `'nothing'`
  - AC timeout: `0`
  - Battery type: `'nothing'`
  - Battery timeout: `0`
- no real suspend/resume event in boot logs

## 3) Remediation If Drift Is Detected

### Sleep drift fix
```bash
cat >/tmp/99-disable-sleep.conf <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
HandleSuspendKey=ignore
HandleHibernateKey=ignore
IdleAction=ignore
EOF
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "sudo install -D -m 0644 /tmp/99-disable-sleep.conf /etc/systemd/logind.conf.d/99-disable-sleep.conf"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "sudo systemctl kill -s HUP systemd-logind"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 0"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0"
```

### Cron runtime drift fix
```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "cp /home/venom/.openclaw/cron/jobs.json /home/venom/.openclaw/cron/jobs.json.backup-$(date +%Y%m%d-%H%M%S)-post-restart-fix"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw cron list --all"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw cron runs --id <job-id> --limit 3"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw cron edit <job-id> --timeout-seconds 480 --thinking high"
```

Important:
- never assume IDs are stable across concurrent sessions
- refresh IDs from `openclaw cron list --all` before editing
- follow edit-window protocol in `docs/ops/TMUX_CRON_OPERATIONS.md`

## 4) Post-Fix Validation

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw cron run <job-id> --expect-final --timeout 480000"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw cron runs --id <job-id> --limit 1"
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "openclaw cron list --all"
```

## 5) Required Logging for Team Continuity
After checks/fixes:
1. Add timestamped note to `docs/orchestrator-ops/agent-watchdog.md`.
2. Add summary to `memory/YYYY-MM-DD.md`.
3. If runtime changed, update `docs/ops/TMUX_CRON_OPERATIONS.md`.

## 6) Optional Log Hygiene (anti-confusion)
When investigation logs become noisy:

```bash
scripts/exec_safe.sh --workdir /home/venom/analyse-financiere -- "KEEP_RUN_DIRS=15 KEEP_CRON_LINES=120 scripts/cleanup_runtime_logs.sh"
```

Effect:
- keeps only recent run folders in `finance-app/orchestrator-runs`
- archives older runs to `finance-app/orchestrator-runs-archive/<timestamp>/`
- trims cron run ledgers only if they exceed retention line count
