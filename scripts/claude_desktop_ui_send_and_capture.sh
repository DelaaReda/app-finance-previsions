#!/usr/bin/env bash
set -euo pipefail

DISPLAY_VALUE="${DISPLAY:-:0}"
MESSAGE="${1:-ping}"
CHAT_MODE="${CHAT_MODE:-same}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-${WAIT_SECONDS:-180}}"
POLL_SECONDS="${POLL_SECONDS:-10}"
MIN_WAIT_SECONDS="${MIN_WAIT_SECONDS:-10}"
STABLE_POLLS="${STABLE_POLLS:-2}"
DEBUG_OCR_ON_ERROR="${DEBUG_OCR_ON_ERROR:-0}"
AUTO_ALWAYS_ALLOW="${AUTO_ALWAYS_ALLOW:-1}"
AUTO_ALLOW_COOLDOWN_SECONDS="${AUTO_ALLOW_COOLDOWN_SECONDS:-4}"

OUT_DIR="${OUT_DIR:-$HOME/analyse-financiere/logs-codex-runs}"
STAMP="$(date +%Y%m%d-%H%M%S)"

SHOT_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.png"
DIRECT_RAW_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.direct.txt"
DIRECT_RESPONSE_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.direct.response.txt"
DIRECT_ACTIONS_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.direct.actions.txt"
BASELINE_RAW_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.baseline.raw.txt"
BASELINE_RESPONSE_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.baseline.response.txt"
MESSAGE_NORMALIZED_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.message.normalized.txt"
PROGRESS_LOG="${OUT_DIR}/claude-ui-send-${STAMP}.progress.log"
SNAPSHOTS_DIR="${OUT_DIR}/claude-ui-send-${STAMP}.snapshots"
DEBUG_OCR_PATH="${OUT_DIR}/claude-ui-send-${STAMP}.debug-ocr.txt"

MAIN_LOG="${HOME}/.config/Claude/logs/main.log"
WEB_LOG="${HOME}/.config/Claude/logs/claude.ai-web.log"
INJECT_MESSAGE="$(printf '%s' "${MESSAGE}" | tr '\n' ' ' | sed 's/[[:space:]]\\+/ /g' | sed 's/^ //; s/ $//')"

mkdir -p "${OUT_DIR}" "${SNAPSHOTS_DIR}"

need_bin() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing dependency: $1" >&2
    exit 127
  fi
}

extract_actions() {
  local in_file="$1"
  local out_file="$2"

  grep -inE \
    -e '(^[0-9]+[.)])' \
    -e '(^- )' \
    -e '\b(action|actions|opened|open|clicked|click|sent|send|ran|run|executed|execute|checked|check|verified|verify|installed|install|created|create|updated|update|patched|patch|tested|test|ouvrir|ouvert|cliquer|clique|envoyer|envoye|lancer|lance|executer|execute|verifier|verifie|installer|installe|creer|cree|mettre a jour|mis a jour|tester|teste|renvoyer|marquer|gagner)\b' \
    "${in_file}" > "${out_file}" || true

  if [[ ! -s "${out_file}" ]]; then
    awk '
      /^[0-9]{1,2}:[0-9]{2}[[:space:]]*([AaPp][Mm])$/ { next }
      /^Pong/ { next }
      /^Ping/ { next }
      /^Claude$/ { next }
      /^Reply\.\.\./ { next }
      /^[[:space:]]*$/ { next }
      { print NR ":" $0 }
    ' "${in_file}" > "${out_file}" || true
  fi
}

normalize_response() {
  local in_file="$1"
  local out_file="$2"

  awk -v msg="${INJECT_MESSAGE}" '
    {
      line=$0
      gsub(/\r/, "", line)
      gsub(/[[:space:]]+/, " ", line)
      if (line ~ /^[[:space:]]*$/) next
      if (line == msg) next
      if (line ~ /^Claude$/) next
      if (line ~ /^Reply\.\.\./) next
      if (line ~ /Sonnet/) next
      if (line ~ /Claude is AI and can make mistakes/) next
      if (line ~ /^Ping pong response$/) next
      if (line ~ /^Show more$/) next
      print line
    }
  ' "${in_file}" > "${out_file}"
}

strip_prefix_file() {
  local prefix_file="$1"
  local current_file="$2"
  local out_file="$3"

  if [[ ! -s "${prefix_file}" ]]; then
    cp "${current_file}" "${out_file}"
    return
  fi

  awk '
    NR==FNR { pre[++pn]=$0; next }
    { cur[++cn]=$0 }
    END {
      start=1
      max=(pn<cn?pn:cn)
      for (i=1; i<=max; i++) {
        if (pre[i]==cur[i]) {
          start=i+1
        } else {
          break
        }
      }
      for (i=start; i<=cn; i++) print cur[i]
    }
  ' "${prefix_file}" "${current_file}" > "${out_file}"
}

read_clipboard_text() {
  local txt=""
  if command -v wl-paste >/dev/null 2>&1; then
    txt="$(wl-paste -n 2>/dev/null || true)"
  fi
  if [[ -z "${txt//[[:space:]]/}" ]] && command -v xclip >/dev/null 2>&1; then
    txt="$(DISPLAY="${DISPLAY_VALUE}" xclip -selection clipboard -o 2>/dev/null || true)"
  fi
  printf '%s\n' "${txt}"
}

set_clipboard_text() {
  local txt="$1"
  if command -v wl-copy >/dev/null 2>&1; then
    printf '%s' "${txt}" | wl-copy >/dev/null 2>&1 && return 0
  fi
  if command -v xclip >/dev/null 2>&1; then
    printf '%s' "${txt}" | DISPLAY="${DISPLAY_VALUE}" xclip -selection clipboard >/dev/null 2>&1 && return 0
  fi
  return 1
}

detect_permission_prompt() {
  local txt="${1:-}"
  local lower
  lower="$(printf '%s' "${txt}" | tr '[:upper:]' '[:lower:]')"
  printf '%s\n' "${lower}" | grep -qE \
    'always allow|always trust|allow once|toujours autoriser|autoriser toujours|run tool|use tool|permission request|approve tool' \
    || return 1
}

auto_click_always_allow() {
  local now_epoch="$1"

  if (( AUTO_ALWAYS_ALLOW != 1 )); then
    return
  fi
  if (( now_epoch - last_auto_allow_epoch < AUTO_ALLOW_COOLDOWN_SECONDS )); then
    return
  fi

  local click_x=$((X + WIDTH / 2 + 170))
  local click_y=$((Y + HEIGHT / 2 + 150))
  if (( click_x > X + WIDTH - 20 )); then
    click_x=$((X + WIDTH - 40))
  fi
  if (( click_y > Y + HEIGHT - 20 )); then
    click_y=$((Y + HEIGHT - 40))
  fi

  DISPLAY="${DISPLAY_VALUE}" xdotool windowactivate --sync "${wid}" || true
  sleep 1
  DISPLAY="${DISPLAY_VALUE}" xdotool mousemove --sync "${click_x}" "${click_y}" || true
  DISPLAY="${DISPLAY_VALUE}" xdotool click 1 || true
  sleep 1
  # Keyboard fallback: if focus is on the dialog, this confirms the selected action.
  DISPLAY="${DISPLAY_VALUE}" xdotool key --window "${wid}" --clearmodifiers Tab Tab Return || true
  sleep 1

  last_auto_allow_epoch="${now_epoch}"
  auto_allow_attempts=$((auto_allow_attempts + 1))
  echo "$(date '+%Y-%m-%d %H:%M:%S') auto_allow_attempt=${auto_allow_attempts} click_x=${click_x} click_y=${click_y}" | tee -a "${PROGRESS_LOG}"
}

copy_chat_region_to_clipboard() {
  DISPLAY="${DISPLAY_VALUE}" xdotool windowactivate --sync "${wid}" || true
  sleep 1
  # Avoid drag gestures: drag can trigger Claude's "drop files" overlay.
  DISPLAY="${DISPLAY_VALUE}" xdotool mousemove --sync "${select_from_x}" "${select_from_y}"
  DISPLAY="${DISPLAY_VALUE}" xdotool click 1
  sleep 1
  DISPLAY="${DISPLAY_VALUE}" xdotool key --window "${wid}" --clearmodifiers ctrl+a || true
  sleep 1
  DISPLAY="${DISPLAY_VALUE}" xdotool key --window "${wid}" --clearmodifiers ctrl+c || true
  sleep 1
}

need_bin claude-desktop
need_bin xdotool
need_bin gnome-screenshot

main_before=0
web_before=0
[[ -f "${MAIN_LOG}" ]] && main_before="$(wc -l < "${MAIN_LOG}")"
[[ -f "${WEB_LOG}" ]] && web_before="$(wc -l < "${WEB_LOG}")"

echo "display=${DISPLAY_VALUE}"
echo "message=${MESSAGE}"
echo "inject_message_chars=$(printf '%s' "${INJECT_MESSAGE}" | wc -c | tr -d ' ')"
echo "chat_mode=${CHAT_MODE}"
echo "max_wait_seconds=${MAX_WAIT_SECONDS}"
echo "poll_seconds=${POLL_SECONDS}"
echo "stable_polls=${STABLE_POLLS}"
echo "auto_always_allow=${AUTO_ALWAYS_ALLOW}"
echo "auto_allow_cooldown_seconds=${AUTO_ALLOW_COOLDOWN_SECONDS}"

if [[ "${CHAT_MODE}" != "same" && "${CHAT_MODE}" != "new" ]]; then
  echo "Invalid CHAT_MODE=${CHAT_MODE}. Use: same|new" >&2
  exit 2
fi

if [[ "${CHAT_MODE}" == "new" ]]; then
  DISPLAY="${DISPLAY_VALUE}" nohup claude-desktop "claude://claude.ai/new" >/tmp/claude-ui-send-launch.log 2>&1 &
  sleep 2
elif ! pgrep -af '/usr/lib/claude-desktop/node_modules/electron/dist/electron' >/dev/null 2>&1; then
  DISPLAY="${DISPLAY_VALUE}" nohup claude-desktop >/tmp/claude-ui-send-launch.log 2>&1 &
  sleep 2
fi

wid=""
for _ in $(seq 1 30); do
  wid="$(DISPLAY="${DISPLAY_VALUE}" xdotool search --onlyvisible --name 'Claude' 2>/dev/null | tail -n 1 || true)"
  if [[ -n "${wid}" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "${wid}" ]]; then
  echo "Claude window not found" >&2
  exit 11
fi

echo "window_id=${wid}"
DISPLAY="${DISPLAY_VALUE}" xdotool windowactivate --sync "${wid}"
sleep 1

if [[ "${CHAT_MODE}" == "new" ]]; then
  # Reinforce new conversation request for desktop UI mode.
  DISPLAY="${DISPLAY_VALUE}" xdotool key --window "${wid}" --clearmodifiers ctrl+n || true
  sleep 1
fi

eval "$(DISPLAY="${DISPLAY_VALUE}" xdotool getwindowgeometry --shell "${wid}")"

input_x=$((X + WIDTH / 2))
input_y=$((Y + HEIGHT - 92))
send_x=$((X + WIDTH - 62))
send_y=$((Y + HEIGHT - 36))

select_from_x=$((X + 36))
select_from_y=$((Y + 120))
select_to_x=$((X + WIDTH - 80))
select_to_y=$((Y + HEIGHT - 150))
if (( select_to_y <= select_from_y )); then
  select_to_y=$((Y + HEIGHT - 120))
fi
if (( select_to_x <= select_from_x )); then
  select_to_x=$((X + WIDTH - 40))
fi

# Baseline capture before sending the new prompt (important for same-chat mode).
copy_chat_region_to_clipboard
baseline_text="$(read_clipboard_text)"
printf '%s\n' "${baseline_text}" > "${BASELINE_RAW_PATH}"
normalize_response "${BASELINE_RAW_PATH}" "${BASELINE_RESPONSE_PATH}"

# Normalize sent message for post-send prefix stripping.
printf '%s\n' "${INJECT_MESSAGE}" > "${MESSAGE_NORMALIZED_PATH}.tmp"
normalize_response "${MESSAGE_NORMALIZED_PATH}.tmp" "${MESSAGE_NORMALIZED_PATH}"
rm -f "${MESSAGE_NORMALIZED_PATH}.tmp"

DISPLAY="${DISPLAY_VALUE}" xdotool mousemove --sync "${input_x}" "${input_y}"
DISPLAY="${DISPLAY_VALUE}" xdotool click 1
sleep 1
DISPLAY="${DISPLAY_VALUE}" xdotool key --clearmodifiers ctrl+a BackSpace
sleep 1
input_injection_method="typing"
if set_clipboard_text "${INJECT_MESSAGE}"; then
  DISPLAY="${DISPLAY_VALUE}" xdotool key --window "${wid}" --clearmodifiers ctrl+v || true
  sleep 1
  input_injection_method="clipboard"
else
  DISPLAY="${DISPLAY_VALUE}" xdotool type --delay 1 "${INJECT_MESSAGE}"
  sleep 1
fi

# Real user-like send: click send button, then Enter fallback.
DISPLAY="${DISPLAY_VALUE}" xdotool mousemove --sync "${send_x}" "${send_y}"
DISPLAY="${DISPLAY_VALUE}" xdotool click 1
sleep 1
DISPLAY="${DISPLAY_VALUE}" xdotool key Return || true

start_epoch="$(date +%s)"
last_hash=""
stable_count=0
poll_index=0
stop_reason="max_wait"

: > "${PROGRESS_LOG}"
: > "${DIRECT_RAW_PATH}"
: > "${DIRECT_RESPONSE_PATH}"
: > "${DIRECT_ACTIONS_PATH}"

last_auto_allow_epoch=0
auto_allow_attempts=0
auto_allow_detected=0

while true; do
  poll_index=$((poll_index + 1))
  poll_id="$(printf '%03d' "${poll_index}")"

  copy_chat_region_to_clipboard
  raw_text="$(read_clipboard_text)"
  now_epoch="$(date +%s)"

  if detect_permission_prompt "${raw_text}"; then
    auto_allow_detected=1
    auto_click_always_allow "${now_epoch}"
    copy_chat_region_to_clipboard
    raw_text="$(read_clipboard_text)"
  fi

  raw_snapshot="${SNAPSHOTS_DIR}/poll-${poll_id}.raw.txt"
  response_all_snapshot="${SNAPSHOTS_DIR}/poll-${poll_id}.response.all.txt"
  response_no_base_snapshot="${SNAPSHOTS_DIR}/poll-${poll_id}.response.nobase.txt"
  response_snapshot="${SNAPSHOTS_DIR}/poll-${poll_id}.response.txt"
  printf '%s\n' "${raw_text}" > "${raw_snapshot}"
  normalize_response "${raw_snapshot}" "${response_all_snapshot}"
  strip_prefix_file "${BASELINE_RESPONSE_PATH}" "${response_all_snapshot}" "${response_no_base_snapshot}"
  strip_prefix_file "${MESSAGE_NORMALIZED_PATH}" "${response_no_base_snapshot}" "${response_snapshot}"

  cp "${raw_snapshot}" "${DIRECT_RAW_PATH}"
  cp "${response_snapshot}" "${DIRECT_RESPONSE_PATH}"
  extract_actions "${DIRECT_RESPONSE_PATH}" "${DIRECT_ACTIONS_PATH}"

  chars="$(wc -m < "${DIRECT_RESPONSE_PATH}" | tr -d ' ')"
  changed="empty"

  if [[ -s "${DIRECT_RESPONSE_PATH}" ]]; then
    current_hash="$(sha256sum "${DIRECT_RESPONSE_PATH}" | awk '{print $1}')"
    if [[ -n "${last_hash}" && "${current_hash}" == "${last_hash}" ]]; then
      stable_count=$((stable_count + 1))
      changed="no"
    else
      stable_count=0
      changed="yes"
      last_hash="${current_hash}"
    fi
  else
    stable_count=0
  fi

  elapsed="$((now_epoch - start_epoch))"
  preview="$(head -n 1 "${DIRECT_RESPONSE_PATH}" | tr -s ' ' | cut -c1-120)"
  progress_line="$(date '+%Y-%m-%d %H:%M:%S') poll=${poll_index} elapsed=${elapsed}s chars=${chars} changed=${changed} stable=${stable_count} preview=\"${preview}\""
  echo "${progress_line}" | tee -a "${PROGRESS_LOG}"

  if (( elapsed >= MIN_WAIT_SECONDS )) && [[ -s "${DIRECT_RESPONSE_PATH}" ]] && (( stable_count >= STABLE_POLLS )); then
    stop_reason="stabilized"
    break
  fi

  if (( elapsed >= MAX_WAIT_SECONDS )); then
    stop_reason="max_wait"
    break
  fi

  sleep "${POLL_SECONDS}"
done

elapsed_total="$(( $(date +%s) - start_epoch ))"

DISPLAY="${DISPLAY_VALUE}" xdotool windowactivate --sync "${wid}" || true
sleep 1
DISPLAY="${DISPLAY_VALUE}" gnome-screenshot -w -f "${SHOT_PATH}" >/dev/null 2>&1 || true
echo "screenshot=${SHOT_PATH}"

main_delta="/tmp/claude-ui-main-delta-${STAMP}.log"
web_delta="/tmp/claude-ui-web-delta-${STAMP}.log"

if [[ -f "${MAIN_LOG}" ]]; then
  awk -v s="$((main_before + 1))" 'NR>=s {print}' "${MAIN_LOG}" > "${main_delta}"
else
  : > "${main_delta}"
fi
if [[ -f "${WEB_LOG}" ]]; then
  awk -v s="$((web_before + 1))" 'NR>=s {print}' "${WEB_LOG}" > "${web_delta}"
else
  : > "${web_delta}"
fi

error_detected=0
if [[ ! -s "${DIRECT_RESPONSE_PATH}" ]]; then
  error_detected=1
fi
if grep -qiE 'oauth failed|permission_error|Cannot get base query config|status code 500|Rate limited|Service temporarily unavailable' "${main_delta}" "${web_delta}" 2>/dev/null; then
  error_detected=1
fi
if [[ "${stop_reason}" == "max_wait" ]]; then
  error_detected=1
fi

debug_ocr_path=""
if (( DEBUG_OCR_ON_ERROR == 1 && error_detected == 1 )) && command -v tesseract >/dev/null 2>&1 && [[ -f "${SHOT_PATH}" ]]; then
  ocr_base="/tmp/claude-ui-ocr-${STAMP}"
  tesseract "${SHOT_PATH}" "${ocr_base}" -l eng --psm 6 >/dev/null 2>&1 || true
  if [[ -f "${ocr_base}.txt" ]]; then
    sed -e 's/\r$//' "${ocr_base}.txt" > "${DEBUG_OCR_PATH}"
    debug_ocr_path="${DEBUG_OCR_PATH}"
  fi
fi

echo "--- main delta signals ---"
grep -inE \
  -e 'account active and logged in' \
  -e 'oauth failed' \
  -e 'permission_error' \
  -e 'Cannot get base query config' \
  -e 'Navigation to https://claude.ai/new' \
  -e 'status code 500' \
  "${main_delta}" || echo "(none)"

echo "--- web delta signals ---"
grep -inE \
  -e 'Rate limited' \
  -e 'Service temporarily unavailable' \
  -e 'Internal server error' \
  -e 'Fatal error boundary' \
  -e 'conversation' \
  -e 'message' \
  "${web_delta}" || echo "(none)"

echo "main_delta=${main_delta}"
echo "web_delta=${web_delta}"
echo "extraction_source=direct"
echo "direct_raw=${DIRECT_RAW_PATH}"
echo "direct_response=${DIRECT_RESPONSE_PATH}"
echo "direct_actions=${DIRECT_ACTIONS_PATH}"
echo "baseline_raw=${BASELINE_RAW_PATH}"
echo "baseline_response=${BASELINE_RESPONSE_PATH}"
echo "message_normalized=${MESSAGE_NORMALIZED_PATH}"
echo "progress_log=${PROGRESS_LOG}"
echo "snapshots_dir=${SNAPSHOTS_DIR}"
echo "polls_total=${poll_index}"
echo "elapsed_seconds=${elapsed_total}"
echo "stop_reason=${stop_reason}"
echo "error_detected=${error_detected}"
echo "debug_ocr=${debug_ocr_path}"
echo "input_injection_method=${input_injection_method}"
echo "auto_allow_detected=${auto_allow_detected}"
echo "auto_allow_attempts=${auto_allow_attempts}"
