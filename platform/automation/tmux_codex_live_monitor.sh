#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
LOG_DIR="${TMUX_LIVE_LOG_DIR:-$ROOT/logs-codex-runs/tmux-live}"
FOLLOW_LINES="${TMUX_LIVE_FOLLOW_LINES:-80}"
CAPTURE_LINES="${TMUX_LIVE_CAPTURE_LINES:-2600}"
POLL_INTERVAL="${TMUX_LIVE_POLL_INTERVAL_SEC:-1}"
MODE="follow"
ENGINE="capture"
SESSIONS_ARG=""
ATTACH_PIPES=1
FORCE_REPIPE=0
INCLUDE_ADMIN=0
WITH_RUNNER_TRACE="${TMUX_LIVE_WITH_RUNNER_TRACE:-1}"

usage() {
  cat <<'EOF'
Usage: tmux_codex_live_monitor.sh [options]

Near-real-time tmux monitoring for cron codex sessions.

Options:
  --mode <follow|start|stop|status>  Action (default: follow)
  --engine <capture|pipe>            follow engine (default: capture)
  --sessions <csv>                   Explicit sessions list (comma or space separated)
  --log-dir <path>                   Output directory for live logs
  --lines <n>                        Initial tail lines per session (pipe follow mode)
  --capture-lines <n>                tmux capture window (capture engine)
  --poll-interval <sec>              capture poll interval in seconds (capture engine)
  --no-attach                        In follow/pipe mode, do not call tmux pipe-pane
  --force-repipe                     Detach existing pipe then attach new cleaner pipe
  --include-admin                    Add admin sessions (adminapp/admin-agents/clawsentinel)
  --no-runner-trace                 Do not tail role runner trace logs in follow mode
  -h, --help                         Show this help

Examples:
  bash scripts/tmux_codex_live_monitor.sh --mode follow
  bash scripts/tmux_codex_live_monitor.sh --mode follow --engine pipe --lines 120
  bash scripts/tmux_codex_live_monitor.sh --mode start --force-repipe
  bash scripts/tmux_codex_live_monitor.sh --mode stop
EOF
}

role_session_name() {
  local role="${1:-}"
  case "$role" in
    clawsentinel) echo "clawsentinel" ;;
    "") return 1 ;;
    *) echo "codex_${role}_cron" ;;
  esac
}

discover_roles_from_cron() {
  if ! command -v openclaw >/dev/null 2>&1; then
    return 0
  fi
  openclaw cron list --json 2>/dev/null | python3 - <<'PY'
import json
import re
import sys

roles = []
try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}
for job in payload.get("jobs", []):
    message = (((job or {}).get("payload") or {}).get("message") or "")
    m = re.search(r"cron_tmux_role_runner\.sh\s+([a-z_]+)", message)
    if not m:
        continue
    role = m.group(1).strip().lower()
    if role and role not in roles:
        roles.append(role)
for role in roles:
    print(role)
PY
}

default_roles() {
  local topology_file="${TMUX_LIVE_TOPOLOGY_FILE:-$ROOT/docs/orchestrator-ops/parallel-role-topology.json}"
  local topo_roles=""

  if [[ -f "$topology_file" ]] && command -v jq >/dev/null 2>&1; then
    topo_roles="$(jq -r '.roles[]? | .role // empty' "$topology_file" 2>/dev/null | awk 'NF')"
    if [[ -n "$topo_roles" ]]; then
      printf '%s\n' $topo_roles
      return 0
    fi
  fi

  printf '%s\n' \
    planner analyst architect backend_engineer frontend_engineer integrator data_analyst infra_engineer \
    dev tester qa po scrum_master clawsentinel
}

parse_sessions_arg() {
  local raw="$1"
  printf '%s' "$raw" | tr ',;' '\n' | tr ' ' '\n' | sed '/^$/d'
}

collect_sessions() {
  local seen=""
  local role=""
  local sess=""
  local roles=""

  if [[ -n "$SESSIONS_ARG" ]]; then
    parse_sessions_arg "$SESSIONS_ARG"
    return 0
  fi

  roles="$(discover_roles_from_cron || true)"
  if [[ -z "$roles" ]]; then
    roles="$(default_roles)"
  fi

  while IFS= read -r role; do
    [[ -z "$role" ]] && continue
    sess="$(role_session_name "$role" || true)"
    [[ -z "$sess" ]] && continue
    if ! printf '%s\n' "$seen" | grep -qx "$sess"; then
      printf '%s\n' "$sess"
      seen="${seen}"$'\n'"${sess}"
    fi
  done <<< "$roles"

  if [[ "$INCLUDE_ADMIN" -eq 1 ]]; then
    for sess in adminapp_codex_sync admin-agents-sync-cron clawsentinel; do
      if ! printf '%s\n' "$seen" | grep -qx "$sess"; then
        printf '%s\n' "$sess"
        seen="${seen}"$'\n'"${sess}"
      fi
    done
  fi
}

log_file_for_session() {
  local session="$1"
  printf '%s/%s.log\n' "$LOG_DIR" "$session"
}

session_to_role() {
  local session="${1:-}"
  if [[ "$session" == "clawsentinel" ]]; then
    echo "clawsentinel"
    return 0
  fi
  if [[ "$session" =~ ^codex_(.+)_cron$ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  return 1
}

trace_file_for_role() {
  local role="$1"
  printf '%s/logs-codex-runs/role-runner/%s.live.log\n' "$ROOT" "$role"
}

attach_pipe_for_session() {
  local session="$1"
  local target="${session}:0.0"
  local log_file=""
  local cleaner=""
  local pipe_cmd=""

  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "session_missing session=${session}"
    return 1
  fi

  mkdir -p "$LOG_DIR"
  log_file="$(log_file_for_session "$session")"
  touch "$log_file"

  if [[ "$FORCE_REPIPE" -eq 1 ]]; then
    tmux pipe-pane -t "$target" >/dev/null 2>&1 || true
  fi

  cleaner="$ROOT/scripts/tmux_log_clean_stream.py"
  if [[ -f "$cleaner" ]]; then
    printf -v pipe_cmd 'python3 -u %q >> %q' "$cleaner" "$log_file"
  else
    printf -v pipe_cmd 'cat >> %q' "$log_file"
  fi
  tmux pipe-pane -o -t "$target" "$pipe_cmd"
  echo "pipe_attached session=${session} log=${log_file}"
}

detach_pipe_for_session() {
  local session="$1"
  local target="${session}:0.0"
  if ! tmux has-session -t "$session" 2>/dev/null; then
    echo "session_missing session=${session}"
    return 1
  fi
  tmux pipe-pane -t "$target" >/dev/null 2>&1 || true
  echo "pipe_detached session=${session}"
}

pane_current_command() {
  local target="$1"
  tmux display-message -p -t "$target" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]'
}

capture_session_text() {
  local session="$1"
  local target="${session}:0.0"
  tmux capture-pane -p -J -S "-${CAPTURE_LINES}" -E -1 -t "$target" 2>/dev/null || true
}

clean_text_chunk() {
  local text="$1"
  local cleaner="$ROOT/scripts/tmux_log_clean_stream.py"
  if [[ -f "$cleaner" ]]; then
    printf '%s\n' "$text" | python3 "$cleaner" 2>/dev/null || true
  else
    printf '%s\n' "$text"
  fi
}

log_mtime() {
  local path="$1"
  if stat -c %Y "$path" >/dev/null 2>&1; then
    stat -c %Y "$path"
    return
  fi
  if stat -f %m "$path" >/dev/null 2>&1; then
    stat -f %m "$path"
    return
  fi
  echo 0
}

print_status_for_session() {
  local session="$1"
  local target="${session}:0.0"
  local log_file=""
  local cmd="missing"
  local exists="no"
  local size="0"
  local mtime="0"

  log_file="$(log_file_for_session "$session")"
  if tmux has-session -t "$session" 2>/dev/null; then
    exists="yes"
    cmd="$(pane_current_command "$target" || true)"
    [[ -z "$cmd" ]] && cmd="unknown"
  fi
  if [[ -f "$log_file" ]]; then
    size="$(wc -c < "$log_file" | tr -d '[:space:]')"
    mtime="$(log_mtime "$log_file")"
  fi
  printf 'session=%s exists=%s pane_cmd=%s log=%s bytes=%s mtime=%s\n' \
    "$session" "$exists" "$cmd" "$log_file" "$size" "$mtime"
}

follow_session_file_pipe() {
  local session="$1"
  local file_path="$2"
  touch "$file_path"
  tail -n "$FOLLOW_LINES" -F "$file_path" 2>/dev/null | sed -u "s/^/[${session}] /" &
  FOLLOW_PIDS+=("$!")
}

follow_trace_file() {
  local role="$1"
  local log_file="${2:-}"
  local file_path=""
  file_path="$(trace_file_for_role "$role")"
  mkdir -p "$(dirname "$file_path")"
  touch "$file_path"
  tail -n 40 -F "$file_path" 2>/dev/null | while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    printf '[trace:%s] %s\n' "$role" "$line"
    if [[ -n "$log_file" ]]; then
      printf '[trace:%s] %s\n' "$role" "$line" >> "$log_file"
    fi
  done &
  FOLLOW_PIDS+=("$!")
}

capture_follow_session() {
  local session="$1"
  local log_file="$2"
  local target="${session}:0.0"
  local prev=""
  local current=""
  local delta=""
  local cleaned=""
  local last_line=""
  local last_diag=""
  local cmd=""
  local ts=""

  touch "$log_file"

  while true; do
    if ! tmux has-session -t "$session" 2>/dev/null; then
      if [[ "$last_diag" != "missing" ]]; then
        printf '[%s] session_missing\n' "$session"
        last_diag="missing"
      fi
      sleep "$POLL_INTERVAL"
      continue
    fi

    if [[ "$last_diag" == "missing" ]]; then
      printf '[%s] session_back\n' "$session"
    fi
    last_diag="up"

    current="$(capture_session_text "$session")"
    if [[ -z "$current" ]]; then
      sleep "$POLL_INTERVAL"
      continue
    fi

    if [[ "$current" == "$prev" ]]; then
      sleep "$POLL_INTERVAL"
      continue
    fi

    if [[ -n "$prev" ]] && [[ "${current:0:${#prev}}" == "$prev" ]]; then
      delta="${current:${#prev}}"
    else
      delta="$(printf '%s\n' "$current" | tail -n 160)"
    fi
    prev="$current"

    if [[ -z "$delta" ]]; then
      sleep "$POLL_INTERVAL"
      continue
    fi

    cleaned="$(clean_text_chunk "$delta")"
    if [[ -z "$cleaned" ]]; then
      cmd="$(pane_current_command "$target" || true)"
      ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf '%s frame_update_no_clean_text cmd=%s delta_chars=%s\n' "$ts" "${cmd:-unknown}" "${#delta}" >> "$log_file"
      printf '[%s] frame_update_no_clean_text cmd=%s delta_chars=%s\n' "$session" "${cmd:-unknown}" "${#delta}"
      sleep "$POLL_INTERVAL"
      continue
    fi

    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      if [[ "$line" == "$last_line" ]]; then
        continue
      fi
      printf '%s\n' "$line" >> "$log_file"
      printf '[%s] %s\n' "$session" "$line"
      last_line="$line"
    done <<< "$cleaned"

    sleep "$POLL_INTERVAL"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:?missing value for --mode}"
      shift 2
      ;;
    --engine)
      ENGINE="${2:?missing value for --engine}"
      shift 2
      ;;
    --sessions)
      SESSIONS_ARG="${2:?missing value for --sessions}"
      shift 2
      ;;
    --log-dir)
      LOG_DIR="${2:?missing value for --log-dir}"
      shift 2
      ;;
    --lines)
      FOLLOW_LINES="${2:?missing value for --lines}"
      shift 2
      ;;
    --capture-lines)
      CAPTURE_LINES="${2:?missing value for --capture-lines}"
      shift 2
      ;;
    --poll-interval)
      POLL_INTERVAL="${2:?missing value for --poll-interval}"
      shift 2
      ;;
    --no-attach)
      ATTACH_PIPES=0
      shift
      ;;
    --force-repipe)
      FORCE_REPIPE=1
      shift
      ;;
    --include-admin)
      INCLUDE_ADMIN=1
      shift
      ;;
    --no-runner-trace)
      WITH_RUNNER_TRACE=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! [[ "$FOLLOW_LINES" =~ ^[0-9]+$ ]] || [[ "$FOLLOW_LINES" -lt 0 ]]; then
  FOLLOW_LINES=80
fi
if ! [[ "$CAPTURE_LINES" =~ ^[0-9]+$ ]] || [[ "$CAPTURE_LINES" -lt 200 ]]; then
  CAPTURE_LINES=2600
fi
if ! [[ "$POLL_INTERVAL" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  POLL_INTERVAL=1
fi
if ! [[ "$WITH_RUNNER_TRACE" =~ ^[01]$ ]]; then
  WITH_RUNNER_TRACE=1
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is not available in PATH" >&2
  exit 3
fi

mapfile -t SESSIONS < <(collect_sessions)
if [[ ${#SESSIONS[@]} -eq 0 ]]; then
  echo "no sessions resolved"
  exit 0
fi

case "$MODE" in
  start)
    for session in "${SESSIONS[@]}"; do
      attach_pipe_for_session "$session" || true
    done
    ;;
  stop)
    for session in "${SESSIONS[@]}"; do
      detach_pipe_for_session "$session" || true
    done
    ;;
  status)
    for session in "${SESSIONS[@]}"; do
      print_status_for_session "$session"
    done
    ;;
  follow)
    mkdir -p "$LOG_DIR"
    case "$ENGINE" in
      capture)
        FOLLOW_PIDS=()
        for session in "${SESSIONS[@]}"; do
          capture_follow_session "$session" "$(log_file_for_session "$session")" &
          FOLLOW_PIDS+=("$!")
        done
        if [[ "$WITH_RUNNER_TRACE" -eq 1 ]]; then
          seen_roles=""
          for session in "${SESSIONS[@]}"; do
            role="$(session_to_role "$session" || true)"
            [[ -z "$role" ]] && continue
            if ! printf '%s\n' "$seen_roles" | grep -qx "$role"; then
              follow_trace_file "$role" "$(log_file_for_session "$session")"
              seen_roles="${seen_roles}"$'\n'"${role}"
            fi
          done
        fi
        trap 'for pid in "${FOLLOW_PIDS[@]:-}"; do kill "$pid" >/dev/null 2>&1 || true; done' EXIT INT TERM
        echo "following engine=capture sessions=${SESSIONS[*]} log_dir=${LOG_DIR} capture_lines=${CAPTURE_LINES} poll_interval=${POLL_INTERVAL}s runner_trace=${WITH_RUNNER_TRACE}"
        wait
        ;;
      pipe)
        if [[ "$ATTACH_PIPES" -eq 1 ]]; then
          for session in "${SESSIONS[@]}"; do
            attach_pipe_for_session "$session" || true
          done
        fi
        FOLLOW_PIDS=()
        for session in "${SESSIONS[@]}"; do
          follow_session_file_pipe "$session" "$(log_file_for_session "$session")"
        done
        trap 'for pid in "${FOLLOW_PIDS[@]:-}"; do kill "$pid" >/dev/null 2>&1 || true; done' EXIT INT TERM
        echo "following engine=pipe sessions=${SESSIONS[*]} log_dir=${LOG_DIR} lines=${FOLLOW_LINES}"
        wait
        ;;
      *)
        echo "Unsupported --engine: $ENGINE" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    echo "Unsupported --mode: $MODE" >&2
    exit 2
    ;;
esac
