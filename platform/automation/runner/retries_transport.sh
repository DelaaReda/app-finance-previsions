#!/usr/bin/env bash

tmux_target() {
  printf '%s:0.0' "$1"
}

tmux_has_session() {
  tmux has-session -t "$1" >/dev/null 2>&1
}

tmux_pane_current_command() {
  tmux display-message -p -t "$(tmux_target "$1")" "#{pane_current_command}" 2>/dev/null | tr '[:upper:]' '[:lower:]'
}

tmux_pane_current_path() {
  tmux display-message -p -t "$(tmux_target "$1")" "#{pane_current_path}" 2>/dev/null
}

tmux_pane_pid() {
  tmux display-message -p -t "$(tmux_target "$1")" "#{pane_pid}" 2>/dev/null | tr -d '[:space:]'
}

tmux_capture() {
  local session="$1"
  local lines="${2:-$TMUX_CAPTURE_LINES}"
  tmux capture-pane -p -J -S "-${lines}" -E -1 -t "$(tmux_target "$session")" 2>/dev/null || true
}

tmux_send_multiline() {
  local session="$1"
  local text="$2"
  local buffer_name="role_runner_$(date +%s)_$$"
  local tmp_path
  tmp_path="$(mktemp)"
  printf '%s' "$text" > "$tmp_path"
  tmux load-buffer -b "$buffer_name" "$tmp_path"
  tmux paste-buffer -d -b "$buffer_name" -t "$(tmux_target "$session")"
  tmux send-keys -t "$(tmux_target "$session")" C-m
  rm -f "$tmp_path"
}

tmux_session_workdir_valid() {
  local session="$1"
  local pane_path=""
  pane_path="$(tmux_pane_current_path "$session" || true)"
  [[ -n "$pane_path" ]] || return 1
  [[ "$pane_path" != *"(deleted)"* ]] || return 1
  case "$pane_path" in
    "$ROOT"|"$ROOT"/*)
      return 0
      ;;
  esac
  return 1
}

tmux_capture_has_blocking_prompt() {
  local capture="${1:-}"
  [[ -n "$capture" ]] || return 1
  grep -qiE \
    '(update available|would you like to update|codex update|trust this project|allow all file|press enter to confirm or esc|switch to .*lower credit|approaching rate limits|continue setup|get started|welcome to codex)' \
    <<<"$capture"
}

tmux_role_launch_command() {
  local agent_cmd=""
  local launch_cmd=""
  agent_cmd="$(agent_launch_command)"
  printf -v launch_cmd 'cd %q && unset NO_COLOR && if [ "${TERM:-dumb}" = "dumb" ]; then export TERM=xterm-256color; fi; export COLORTERM="${COLORTERM:-truecolor}"; export FORCE_COLOR="${FORCE_COLOR:-1}"; exec %s' "$ROOT" "$agent_cmd"
  printf '%s\n' "$launch_cmd"
}

tmux_agent_ready() {
  local session="$1"
  local cmd=""
  local pane_pid=""
  local children=""
  local child_regex=""
  local capture=""
  if ! tmux_session_workdir_valid "$session"; then
    return 1
  fi
  cmd="$(tmux_pane_current_command "$session" || true)"
  if [[ -n "$cmd" ]]; then
    if [[ "$cmd" == *"${AGENT_BIN_NAME}"* ]]; then
      capture="$(tmux_capture "$session" 120)"
      if tmux_capture_has_blocking_prompt "$capture"; then
        return 1
      fi
      return 0
    fi
  fi
  pane_pid="$(tmux_pane_pid "$session" || true)"
  if [[ "$pane_pid" =~ ^[0-9]+$ ]] && command -v pgrep >/dev/null 2>&1; then
    children="$(pgrep -P "$pane_pid" -af 2>/dev/null || true)"
    case "$AGENT_BIN_NAME" in
      codex) child_regex='(codex|openai.*codex|node.*codex)' ;;
      qwen) child_regex='(qwen|qwen-code|@qwen-code|node.*qwen)' ;;
      *) child_regex="(${AGENT_BIN_NAME}|node.*${AGENT_BIN_NAME})" ;;
    esac
    if rg -qi "$child_regex" <<<"$children"; then
      return 0
    fi
  fi
  return 1
}

start_role_session() {
  local session="$1"
  local launch_cmd=""
  local capture=""
  tmux start-server >/dev/null 2>&1 || true
  launch_cmd="$(tmux_role_launch_command)"
  if ! tmux_has_session "$session"; then
    tmux new-session -d -s "$session" "bash -lc $(printf '%q' "$launch_cmd")"
    sleep 1
  fi
  tmux set-option -t "$session" history-limit 200000 >/dev/null 2>&1 || true
  capture="$(tmux_capture "$session" 120)"
  if ! tmux_session_workdir_valid "$session" || tmux_capture_has_blocking_prompt "$capture"; then
    tmux kill-session -t "$session" >/dev/null 2>&1 || true
    tmux new-session -d -s "$session" "bash -lc $(printf '%q' "$launch_cmd")"
    sleep 1
  fi
  if ! tmux_agent_ready "$session"; then
    tmux send-keys -t "$(tmux_target "$session")" C-c >/dev/null 2>&1 || true
    sleep 1
    tmux_send_multiline "$session" "$launch_cmd"
  fi
}

ensure_role_session_ready() {
  local role="$1"
  local session=""
  local i=0
  session="$(target_session_name "$role")"
  if [[ -z "$session" ]]; then
    return 1
  fi
  start_role_session "$session"
  for ((i=0; i<TMUX_READY_WAIT_SECONDS; i++)); do
    if tmux_agent_ready "$session"; then
      return 0
    fi
    sleep 1
  done
  return 1
}
