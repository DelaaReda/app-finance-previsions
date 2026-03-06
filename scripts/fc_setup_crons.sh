#!/usr/bin/env bash
# ============================================================
# fc_setup_crons.sh — Configure tous les crons du Finance Copilot
# SAFE: idempotent, supprime les vieux et recrée proprement
# Usage: bash scripts/fc_setup_crons.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/../platform/automation/lib/workspace_paths.sh"
RUNTIME_HOST_GUARD="${SCRIPT_DIR}/../platform/automation/lib/runtime_host_guard.sh"
if [[ ! -f "$WORKSPACE_HELPER" ]]; then
  echo "Missing workspace helper: $WORKSPACE_HELPER" >&2
  exit 2
fi
if [[ ! -f "$RUNTIME_HOST_GUARD" ]]; then
  echo "Missing runtime host guard: $RUNTIME_HOST_GUARD" >&2
  exit 2
fi
# shellcheck source=/dev/null
source "$WORKSPACE_HELPER"
# shellcheck source=/dev/null
source "$RUNTIME_HOST_GUARD"
fc_runtime_assert_vm_or_exit "fc_setup_crons"

ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
BASH_BIN="$(which bash)"
CRON_PROFILE="${FC_CRON_PROFILE:-full}"
if [[ -z "${RUNNER_CONFIG_FILE:-}" ]]; then
  if [[ -f "${ROOT}/platform/config/runner/runner.v1.yaml" ]]; then
    RUNNER_CONFIG_FILE="${ROOT}/platform/config/runner/runner.v1.yaml"
  elif [[ -f "${ROOT}/platform/config/runner/runner_config.v1.yaml" ]]; then
    RUNNER_CONFIG_FILE="${ROOT}/platform/config/runner/runner_config.v1.yaml"
  else
    RUNNER_CONFIG_FILE="${ROOT}/platform/automation/config/runner.v1.yaml"
  fi
fi
RUNNER_CONFIG_FALLBACK_ENV="${RUNNER_CONFIG_FALLBACK_ENV:-1}"
RUNNER_CONFIG_LOADER="${ROOT}/platform/automation/runner_config.py"
# Admin lane should run frequently to unblock runtime quickly.
# Override with FC_ADMIN_CRON_EXPR if a different cadence is needed.
ADMIN_CRON_EXPR="${FC_ADMIN_CRON_EXPR:-*/5}"
ADMIN_PROMPT_TIMEOUT_SECONDS="${FC_ADMIN_PROMPT_TIMEOUT_SECONDS:-360}"
ADMIN_RETRY_TIMEOUT_SECONDS="${FC_ADMIN_RETRY_TIMEOUT_SECONDS:-150}"
ADMIN_TICK_TIMEOUT_SECONDS="${FC_ADMIN_TICK_TIMEOUT_SECONDS:-540}"
ADMIN_DISPATCH_ENABLED="${FC_ADMIN_DISPATCH_ENABLED:-1}"
ADMIN_DISPATCH_COOLDOWN_SECONDS="${FC_ADMIN_DISPATCH_COOLDOWN_SECONDS:-180}"
ADMIN_DISPATCH_MAX_ACTIONS="${FC_ADMIN_DISPATCH_MAX_ACTIONS:-2}"
ADMIN_DISPATCH_SYNC_PRIORITY="${FC_ADMIN_DISPATCH_SYNC_PRIORITY:-1}"
ADMIN_DISPATCH_BYPASS_COOLDOWN_ON_HANDOFF="${FC_ADMIN_DISPATCH_BYPASS_COOLDOWN_ON_HANDOFF:-1}"
ADMIN_TSHAPE_ENABLED="${FC_ADMIN_TSHAPE_ENABLED:-1}"
ADMIN_TSHAPE_TRIGGER="${FC_ADMIN_TSHAPE_TRIGGER:-blocked}"
ADMIN_TSHAPE_BLOCKED_THRESHOLD="${FC_ADMIN_TSHAPE_BLOCKED_THRESHOLD:-1}"
ADMIN_TSHAPE_SCOPE="${FC_ADMIN_TSHAPE_SCOPE:-full_takeover}"
ADMIN_TSHAPE_EXIT_POLICY="${FC_ADMIN_TSHAPE_EXIT_POLICY:-resolved_only}"
ADMIN_TSHAPE_ALLOWED_TARGETS="${FC_ADMIN_TSHAPE_ALLOWED_TARGETS:-planner,dev}"
ADMIN_TSHAPE_SYNC_TIMEOUT_SECONDS="${FC_ADMIN_TSHAPE_SYNC_TIMEOUT_SECONDS:-20}"
ADMIN_TSHAPE_ENFORCE_SLA="${FC_ADMIN_TSHAPE_ENFORCE_SLA:-1}"
ADMIN_TSHAPE_SLA_TIMEOUT_SECONDS="${FC_ADMIN_TSHAPE_SLA_TIMEOUT_SECONDS:-15}"
ADMIN_TSHAPE_COOLDOWN_SECONDS="${FC_ADMIN_TSHAPE_COOLDOWN_SECONDS:-0}"
# Scrum master lane (every 5 minutes in full profile, operational by default).
SCRUM_MASTER_CRON_EXPR="${FC_SCRUM_MASTER_CRON_EXPR:-${FC_PO_SCRUM_MASTER_CRON_EXPR:-3-58/5}}"
SCRUM_MASTER_CRON_ENABLED="${FC_SCRUM_MASTER_CRON_ENABLED:-${FC_PO_SCRUM_MASTER_CRON_ENABLED:-}}"
FC_SCRUM_MASTER_MODE="${FC_SCRUM_MASTER_MODE:-operational}"
FC_SCRUM_MASTER_FULL_REMEDIATION="${FC_SCRUM_MASTER_FULL_REMEDIATION:-1}"
FC_SCRUM_MASTER_ESCALATE_AFTER_CYCLES="${FC_SCRUM_MASTER_ESCALATE_AFTER_CYCLES:-2}"
PLANNER_ORCHESTRATOR_ENABLED="${FC_PLANNER_ORCHESTRATOR_ENABLED:-}"
PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY="${FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY:-}"
EXPERIMENTAL_PLANNER_ONLY="${FC_EXPERIMENTAL_PLANNER_ONLY:-}"
ROLE_RECOVERY_LOG_DIR="${FC_ROLE_RECOVERY_LOG_DIR:-${ROOT}/logs-codex-runs}"
if [[ "$ROOT" == /Users/* ]]; then
  MONITOR_AUTO_START_STACK="${FC_MONITOR_AUTO_START_STACK:-0}"
else
  MONITOR_AUTO_START_STACK="${FC_MONITOR_AUTO_START_STACK:-1}"
fi
MONITOR_AUTO_START_COOLDOWN_SECONDS="${FC_MONITOR_AUTO_START_COOLDOWN_SECONDS:-600}"

disable_legacy_qwen_units() {
  if ! command -v systemctl >/dev/null 2>&1; then
    return 0
  fi
  if ! systemctl --user show-environment >/dev/null 2>&1; then
    return 0
  fi
  local units=(
    "fc-planner-qwen.timer"
    "fc-dev-qwen.timer"
    "fc-admin-qwen.timer"
    "fc-planner-qwen.service"
    "fc-dev-qwen.service"
    "fc-admin-qwen.service"
  )
  systemctl --user stop "${units[@]}" >/dev/null 2>&1 || true
  systemctl --user disable "${units[@]}" >/dev/null 2>&1 || true
  systemctl --user reset-failed "${units[@]}" >/dev/null 2>&1 || true
  echo "✅ Disabled legacy qwen systemd units (fc-*-qwen)"
}

disable_vm_resume_guard_timer() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "SCHED_AUTHORITY vm_resume_guard=cron_only timer_disabled=1 reason=systemctl_missing"
    return 0
  fi
  if ! systemctl --user show-environment >/dev/null 2>&1; then
    echo "SCHED_AUTHORITY vm_resume_guard=cron_only timer_disabled=1 reason=systemd_user_unavailable"
    return 0
  fi

  local timer_before timer_after timer_disabled
  timer_before="$(systemctl --user is-enabled vm-resume-guard.timer 2>/dev/null || echo "unknown")"
  systemctl --user stop vm-resume-guard.timer vm-resume-guard.service >/dev/null 2>&1 || true
  systemctl --user disable vm-resume-guard.timer vm-resume-guard.service >/dev/null 2>&1 || true
  systemctl --user reset-failed vm-resume-guard.timer vm-resume-guard.service >/dev/null 2>&1 || true
  timer_after="$(systemctl --user is-enabled vm-resume-guard.timer 2>/dev/null || echo "disabled")"
  timer_disabled=0
  if [[ "$timer_after" != "enabled" ]]; then
    timer_disabled=1
  fi
  echo "SCHED_AUTHORITY vm_resume_guard=cron_only timer_disabled=${timer_disabled} timer_before=${timer_before} timer_after=${timer_after}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      CRON_PROFILE="${2:-full}"
      shift 2
      ;;
    --planner-experimental)
      CRON_PROFILE="planner-experimental"
      shift
      ;;
    --canary)
      CRON_PROFILE="canary"
      shift
      ;;
    --full)
      CRON_PROFILE="full"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: bash scripts/fc_setup_crons.sh [--profile full|canary|planner-experimental|--planner-experimental|--canary|--full]" >&2
      exit 2
      ;;
  esac
done

case "$CRON_PROFILE" in
  full|canary|planner-experimental) ;;
  *)
    echo "Invalid profile: $CRON_PROFILE (expected: full|canary|planner-experimental)" >&2
    exit 2
    ;;
esac

if [[ -z "${SCRUM_MASTER_CRON_ENABLED}" ]]; then
  if [[ "$CRON_PROFILE" == "canary" || "$CRON_PROFILE" == "planner-experimental" ]]; then
    SCRUM_MASTER_CRON_ENABLED=0
  else
    SCRUM_MASTER_CRON_ENABLED=1
  fi
fi

# Advisory cron is full-profile only by policy.
if [[ "$CRON_PROFILE" != "full" ]]; then
  SCRUM_MASTER_CRON_ENABLED=0
fi

if [[ -f "$RUNNER_CONFIG_FILE" && -f "$RUNNER_CONFIG_LOADER" ]] && command -v python3 >/dev/null 2>&1; then
  if ! python3 "$RUNNER_CONFIG_LOADER" --config "$RUNNER_CONFIG_FILE" validate >/tmp/fc_runner_cfg_validate.out 2>/tmp/fc_runner_cfg_validate.err; then
    echo "❌ runner.v1 invalid: $RUNNER_CONFIG_FILE" >&2
    echo "   detail: $(tr '\n' ' ' </tmp/fc_runner_cfg_validate.err | sed 's/  */ /g' | cut -c1-240)" >&2
    rm -f /tmp/fc_runner_cfg_validate.out /tmp/fc_runner_cfg_validate.err
    exit 2
  fi
  rm -f /tmp/fc_runner_cfg_validate.out /tmp/fc_runner_cfg_validate.err
fi

if [[ -f "$RUNNER_CONFIG_FILE" ]] && command -v python3 >/dev/null 2>&1; then
  if [[ -z "$PLANNER_ORCHESTRATOR_ENABLED" || -z "$PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY" ]]; then
    planner_flags="$(
      python3 - "$RUNNER_CONFIG_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    cfg = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
except Exception:
    cfg = {}
features = cfg.get("features", {}) if isinstance(cfg, dict) else {}
planner = features.get("planner_orchestrator", {}) if isinstance(features, dict) else {}
enabled = 1 if str(planner.get("enabled", 0)).strip() not in {"0", "false", "False", ""} else 0
cron_only = 1 if str(planner.get("cron_planner_only", 0)).strip() not in {"0", "false", "False", ""} else 0
print(f"{enabled} {cron_only}")
PY
    )"
    if [[ -n "$planner_flags" ]]; then
      read -r cfg_planner_enabled cfg_planner_cron_only <<<"$planner_flags"
      [[ -n "$PLANNER_ORCHESTRATOR_ENABLED" ]] || PLANNER_ORCHESTRATOR_ENABLED="${cfg_planner_enabled:-0}"
      [[ -n "$PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY" ]] || PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY="${cfg_planner_cron_only:-0}"
    fi
  fi
fi
if [[ "$EXPERIMENTAL_PLANNER_ONLY" == "1" ]]; then
  PLANNER_ORCHESTRATOR_ENABLED="1"
  PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY="1"
fi
if [[ "$CRON_PROFILE" == "planner-experimental" ]]; then
  PLANNER_ORCHESTRATOR_ENABLED="1"
  PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY="1"
fi
PLANNER_ORCHESTRATOR_ENABLED="${PLANNER_ORCHESTRATOR_ENABLED:-0}"
PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY="${PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY:-0}"
PLANNER_ORCHESTRATOR_ACTIVE=0
if [[ "$PLANNER_ORCHESTRATOR_ENABLED" == "1" && "$PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY" == "1" ]]; then
  PLANNER_ORCHESTRATOR_ACTIVE=1
fi

echo "📋 Configuring Finance Copilot cron jobs..."
echo "   Root: $ROOT"
echo "   Profile: $CRON_PROFILE"
echo "   Planner orchestrator: $PLANNER_ORCHESTRATOR_ACTIVE"
echo ""

# ── Backup existing crontab ───────────────────────────────
crontab -l 2>/dev/null > /tmp/crontab_backup_$(date +%Y%m%d%H%M%S).txt || true
echo "✅ Backed up existing crontab"
disable_legacy_qwen_units
disable_vm_resume_guard_timer

# ── Build new crontab ─────────────────────────────────────
CRON_CONTENT=$(
  crontab -l 2>/dev/null \
    | grep -v "fc_agent_tick\|auto_recover_tmux\|fc_setup\|cron_tmux_role_runner\|vm_resume_guard\|fc_resume\|watchdog_chromium\|cleanup_monitoring_noise\|cleanup_stale_role_locks\|monitor_stack_guard\|health_snapshot\|auto_batch_close\|dependency_recompute\|cron_admin_tick\.sh\|cron_po_scrum_master_tick\.sh\|cron_scrum_master_tick\.sh\|Finance Copilot" \
    | grep -v "fc_agent_tick\.sh[[:space:]]\+scrum_master\|cron_tmux_role_runner\.sh[[:space:]]\+scrum_master\|cron_po_scrum_master_tick\.sh\|cron_scrum_master_tick\.sh" \
    || true
)

ROLE_CRON_BLOCK=""
if [[ "$PLANNER_ORCHESTRATOR_ACTIVE" == "1" ]]; then
  PLANNER_ORCHESTRATOR_CRON_EXPR="0,22,44"
  if [[ "$CRON_PROFILE" == "canary" ]]; then
    PLANNER_ORCHESTRATOR_CRON_EXPR="0,30"
  fi
  ROLE_CRON_BLOCK=$(cat <<EOF
# [finance-copilot] PLANNER — sole scheduled orchestrator (Codex multi-agent experimental)
${PLANNER_ORCHESTRATOR_CRON_EXPR} * * * * ${BASH_BIN} -lc 'cd ${ROOT} && RUNNER_CONFIG_FILE=${RUNNER_CONFIG_FILE} RUNNER_CONFIG_LOADER=${RUNNER_CONFIG_LOADER} RUNNER_CONFIG_FALLBACK_ENV=${RUNNER_CONFIG_FALLBACK_ENV} FC_PLANNER_ORCHESTRATOR_ENABLED=1 FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY=1 bash scripts/fc_agent_tick.sh planner' >> ${ROOT}/logs-codex-runs/fc-ticks/planner.cron.log 2>&1

# Managed lanes are no longer independently scheduled in planner_orchestrator mode.
# dev/admin/scrum_master execute as planner-owned Codex subagents via planner_subagent_manager.py
EOF
)
elif [[ "$CRON_PROFILE" == "canary" ]]; then
  ROLE_CRON_BLOCK=$(cat <<EOF
# [finance-copilot] PLANNER (lean canary) — cadence réduite
0,30 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && RUNNER_CONFIG_FILE=${RUNNER_CONFIG_FILE} RUNNER_CONFIG_LOADER=${RUNNER_CONFIG_LOADER} RUNNER_CONFIG_FALLBACK_ENV=${RUNNER_CONFIG_FALLBACK_ENV} bash scripts/fc_agent_tick.sh planner' >> ${ROOT}/logs-codex-runs/fc-ticks/planner.cron.log 2>&1

# [finance-copilot] DEV (lean canary) — lane delivery consolidée
10,40 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && RUNNER_CONFIG_FILE=${RUNNER_CONFIG_FILE} RUNNER_CONFIG_LOADER=${RUNNER_CONFIG_LOADER} RUNNER_CONFIG_FALLBACK_ENV=${RUNNER_CONFIG_FALLBACK_ENV} bash scripts/fc_agent_tick.sh dev' >> ${ROOT}/logs-codex-runs/fc-ticks/dev.cron.log 2>&1

# ADMIN — volontairement désactivé en canary
EOF
)
else
  ROLE_CRON_BLOCK=$(cat <<EOF
# [finance-copilot] PLANNER — orchestration et dispatch
0,22,44 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && RUNNER_CONFIG_FILE=${RUNNER_CONFIG_FILE} RUNNER_CONFIG_LOADER=${RUNNER_CONFIG_LOADER} RUNNER_CONFIG_FALLBACK_ENV=${RUNNER_CONFIG_FALLBACK_ENV} bash scripts/fc_agent_tick.sh planner' >> ${ROOT}/logs-codex-runs/fc-ticks/planner.cron.log 2>&1

# [finance-copilot] DEV — lane delivery consolidée (backend/frontend/data/tests)
6,28,50 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && RUNNER_CONFIG_FILE=${RUNNER_CONFIG_FILE} RUNNER_CONFIG_LOADER=${RUNNER_CONFIG_LOADER} RUNNER_CONFIG_FALLBACK_ENV=${RUNNER_CONFIG_FALLBACK_ENV} FC_DEV_RATE_LIMIT_PRECHECK=0 bash scripts/fc_agent_tick.sh dev' >> ${ROOT}/logs-codex-runs/fc-ticks/dev.cron.log 2>&1

# [finance-copilot] ADMIN — santé runtime, déblocage, hygiene
${ADMIN_CRON_EXPR} * * * * ${BASH_BIN} -lc 'cd ${ROOT} && RUNNER_CONFIG_FILE=${RUNNER_CONFIG_FILE} RUNNER_CONFIG_LOADER=${RUNNER_CONFIG_LOADER} RUNNER_CONFIG_FALLBACK_ENV=${RUNNER_CONFIG_FALLBACK_ENV} bash scripts/cron_admin_tick.sh' >> ${ROOT}/logs-codex-runs/fc-ticks/admin.cron.log 2>&1

# [finance-copilot] Scrum Master (operational) — scheduled lane (5m, full profile only)
${SCRUM_MASTER_CRON_EXPR} * * * * ${BASH_BIN} -lc 'if [[ "${SCRUM_MASTER_CRON_ENABLED}" == "1" ]]; then cd ${ROOT} && RUNNER_CONFIG_FILE=${RUNNER_CONFIG_FILE} RUNNER_CONFIG_LOADER=${RUNNER_CONFIG_LOADER} RUNNER_CONFIG_FALLBACK_ENV=${RUNNER_CONFIG_FALLBACK_ENV} FC_SCRUM_MASTER_MODE=${FC_SCRUM_MASTER_MODE} FC_SCRUM_MASTER_FULL_REMEDIATION=${FC_SCRUM_MASTER_FULL_REMEDIATION} FC_SCRUM_MASTER_ESCALATE_AFTER_CYCLES=${FC_SCRUM_MASTER_ESCALATE_AFTER_CYCLES} bash scripts/cron_scrum_master_tick.sh; fi' >> ${ROOT}/logs-codex-runs/fc-ticks/scrum_master.cron.log 2>&1
EOF
)
fi

: > /tmp/fc_new_crontab
cat >> /tmp/fc_new_crontab << EOF
${CRON_CONTENT}

# ============================================================
# Finance Copilot Agent Orchestration
# Generated: $(date)
# ============================================================

# [finance-copilot] VM Resume guard — détecte le réveil et tue les sessions stales
*/2 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/vm_resume_guard.sh' >> ${ROOT}/logs-codex-runs/vm-resume.log 2>&1

# [finance-copilot] Auto-recovery sessions (garde les sessions tmux vivantes)
*/10 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && FC_ROLE_RECOVERY_LOG_DIR=${ROLE_RECOVERY_LOG_DIR} bash scripts/auto_recover_tmux_roles.sh' >> ${ROOT}/logs-codex-runs/role-recovery.log 2>&1

# [finance-copilot] Watchdog Chromium zombies + stale runtime locks
*/15 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/watchdog_chromium.sh' >> ${ROOT}/logs-codex-runs/watchdog_chromium.log 2>&1

# [finance-copilot] Stale role locks cleanup (memory + run locks >15min)
*/10 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/cleanup_stale_role_locks.sh' >> /tmp/fc-stale-lock-cleanup.log 2>&1

# [finance-copilot] Monitor guard (api 7779 + tunnel fc-monitor.loca.lt)
*/1 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && FC_MONITOR_AUTO_START_STACK=${MONITOR_AUTO_START_STACK} FC_MONITOR_AUTO_START_COOLDOWN_SECONDS=${MONITOR_AUTO_START_COOLDOWN_SECONDS} bash scripts/monitor_stack_guard.sh' >> ${ROOT}/logs-codex-runs/monitor-guard.cron.log 2>&1

# [finance-copilot] Runtime logs cleanup (bruit historique + archives)
17 */4 * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/cleanup_monitoring_noise.sh' >> ${ROOT}/logs-codex-runs/log-cleanup.log 2>&1

# [finance-copilot] Health snapshot (toutes les 30min)
8,38 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/health_snapshot.sh' >> ${ROOT}/logs-codex-runs/health-snapshot.log 2>&1

# [finance-copilot] Auto batch close — ferme batches DONE (3x/heure, offsets anti-collision)
2,22,42 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/auto_batch_close.sh' >> ${ROOT}/logs-codex-runs/auto-batch-close.log 2>&1

# [finance-copilot] Dependency recompute — réduit les plateaux WAITING_DEP et resynchronise queue/workboard
4,9,14,19,24,29,34,39,44,49,54,59 * * * * ${BASH_BIN} -lc 'cd ${ROOT} && bash scripts/dependency_recompute.sh' >> ${ROOT}/logs-codex-runs/dependency-recompute.log 2>&1

${ROLE_CRON_BLOCK}

# ============================================================
EOF

crontab /tmp/fc_new_crontab
rm -f /tmp/fc_new_crontab

echo ""
echo "✅ Cron jobs installed!"
echo ""
echo "📅 Schedule:"
echo "   - vm_resume_guard     : every 2 min  (détecte réveil VM)"
echo "   - auto_recover        : every 10 min (garde sessions vivantes)"
echo "   - log_cleanup         : minute 17 every 4h"
echo "   - monitor_guard       : every 1 min  (api+tunnel health)"
echo "   - dependency_recompute: every 5 min  (queue/workboard dep refresh)"
if [[ "$PLANNER_ORCHESTRATOR_ACTIVE" == "1" ]]; then
  if [[ "$CRON_PROFILE" == "canary" ]]; then
    echo "   - planner             : 0,30 (sole orchestrator, canary)"
  else
    echo "   - planner             : 0,22,44 (sole orchestrator)"
  fi
  echo "   - dev/admin/scrum     : planner-owned Codex subagents"
elif [[ "$CRON_PROFILE" == "canary" ]]; then
  echo "   - planner             : 0,30  (canary)"
  echo "   - dev                 : 10,40 (canary)"
  echo "   - admin               : paused (canary)"
else
  echo "   - planner             : 0,22,44"
  echo "   - dev                 : 6,28,50"
  echo "   - admin               : ${ADMIN_CRON_EXPR}"
  if [[ "${SCRUM_MASTER_CRON_ENABLED}" == "1" ]]; then
    echo "   - scrum_master       : ${SCRUM_MASTER_CRON_EXPR} (operational)"
  else
    echo "   - scrum_master       : disabled"
  fi
fi
echo ""
echo "📋 Current crontab:"
crontab -l 2>/dev/null | grep -v "^#\|^$"
