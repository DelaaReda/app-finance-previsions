#!/usr/bin/env bash
set -euo pipefail

DISPLAY_VALUE="${DISPLAY:-:0}"
MAIN_LOG="${HOME}/.config/Claude/logs/main.log"
WEB_LOG="${HOME}/.config/Claude/logs/claude.ai-web.log"
WAIT_SECONDS="${WAIT_SECONDS:-25}"
MESSAGE="${1:-ui-normal-user-$(date +%s)}"

if ! command -v claude-desktop >/dev/null 2>&1; then
  echo "claude-desktop not found in PATH" >&2
  exit 127
fi
if ! command -v xdotool >/dev/null 2>&1; then
  echo "xdotool not found in PATH" >&2
  exit 127
fi

before_main=0
before_web=0
if [[ -f "${MAIN_LOG}" ]]; then
  before_main="$(wc -l < "${MAIN_LOG}")"
fi
if [[ -f "${WEB_LOG}" ]]; then
  before_web="$(wc -l < "${WEB_LOG}")"
fi

echo "display: ${DISPLAY_VALUE}"
echo "message: ${MESSAGE}"

DISPLAY="${DISPLAY_VALUE}" nohup claude-desktop "claude://claude.ai/new" >/tmp/claude_ui_send.launcher.log 2>&1 &

wid=""
for _ in $(seq 1 "${WAIT_SECONDS}"); do
  wid="$(DISPLAY="${DISPLAY_VALUE}" xdotool search --name "Claude" 2>/dev/null | tail -n 1 || true)"
  if [[ -n "${wid}" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "${wid}" ]]; then
  echo "window_not_found: Claude window did not appear" >&2
  exit 11
fi

echo "window_id: ${wid}"
DISPLAY="${DISPLAY_VALUE}" xdotool windowactivate --sync "${wid}"
sleep 1

eval "$(DISPLAY="${DISPLAY_VALUE}" xdotool getwindowgeometry --shell "${wid}")"
input_x=$((X + WIDTH / 2))
input_y=$((Y + HEIGHT - 90))
send_x=$((X + WIDTH - 65))
send_y=$((Y + HEIGHT - 35))

DISPLAY="${DISPLAY_VALUE}" xdotool mousemove --sync "${input_x}" "${input_y}"
DISPLAY="${DISPLAY_VALUE}" xdotool click 1
sleep 1
DISPLAY="${DISPLAY_VALUE}" xdotool type --delay 1 "${MESSAGE}"
sleep 1
DISPLAY="${DISPLAY_VALUE}" xdotool key Return
sleep 2
DISPLAY="${DISPLAY_VALUE}" xdotool mousemove --sync "${send_x}" "${send_y}"
DISPLAY="${DISPLAY_VALUE}" xdotool click 1 || true
sleep 6

main_delta="/tmp/claude_ui_send.main.delta.log"
web_delta="/tmp/claude_ui_send.web.delta.log"

if [[ -f "${MAIN_LOG}" ]]; then
  awk -v s="$((before_main + 1))" 'NR>=s { print }' "${MAIN_LOG}" > "${main_delta}" || true
else
  : > "${main_delta}"
fi

if [[ -f "${WEB_LOG}" ]]; then
  awk -v s="$((before_web + 1))" 'NR>=s { print }' "${WEB_LOG}" > "${web_delta}" || true
else
  : > "${web_delta}"
fi

echo "--- main.log delta signals ---"
grep -inE \
  -e "oauth failed" \
  -e "permission_error" \
  -e "status code 500" \
  -e "account active and logged in" \
  -e "Navigation to https://claude.ai/new" \
  -e "Cannot get base query config" \
  -e "Rate limited" \
  -e "Service temporarily unavailable" \
  -e "Sign in complete" \
  "${main_delta}" || echo "(none)"

echo "--- claude.ai-web.log delta signals ---"
grep -inE \
  -e "rate limited" \
  -e "service temporarily unavailable" \
  -e "internal server error" \
  -e "fatal error boundary" \
  -e "conversation" \
  -e "message" \
  -e "queryclient error" \
  "${web_delta}" || echo "(none)"

echo "delta_main: ${main_delta}"
echo "delta_web: ${web_delta}"
