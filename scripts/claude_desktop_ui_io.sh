#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UI_SCRIPT="${ROOT_DIR}/scripts/claude_desktop_ui_send_and_capture.sh"
DEFAULT_OUT_DIR="${ROOT_DIR}/logs-codex-runs"

INPUT_TEXT=""
INPUT_FILE=""
CHAT_MODE_VALUE="${CHAT_MODE:-same}"
MAX_WAIT_SECONDS_VALUE="${MAX_WAIT_SECONDS:-${WAIT_SECONDS:-180}}"
POLL_SECONDS_VALUE="${POLL_SECONDS:-10}"
STABLE_POLLS_VALUE="${STABLE_POLLS:-2}"
DEBUG_OCR_ON_ERROR_VALUE="${DEBUG_OCR_ON_ERROR:-0}"
AUTO_ALWAYS_ALLOW_VALUE="${AUTO_ALWAYS_ALLOW:-1}"
AUTO_ALLOW_COOLDOWN_SECONDS_VALUE="${AUTO_ALLOW_COOLDOWN_SECONDS:-4}"
OUT_DIR="${OUT_DIR:-$DEFAULT_OUT_DIR}"
PRINT_OUTPUT=0

usage() {
  cat <<'EOF'
Usage:
  claude_desktop_ui_io.sh --input "prompt text" [--chat-mode same|new] [--max-wait 180] [--poll 10] [--stable-polls 2] [--out-dir path] [--print-output]
  claude_desktop_ui_io.sh --input-file path/to/prompt.txt [same options...]

Options:
  --input "text"      Required. Message to send in Claude Desktop UI.
  --input-file PATH   Alternative to --input for long prompts.
  --chat-mode MODE    Optional. `same` (reuse current chat) or `new` (start new chat). Default: same.
  --same-chat         Alias for --chat-mode same.
  --new-chat          Alias for --chat-mode new.
  --max-wait N        Optional. Max wait time in seconds (default: 180).
  --wait N            Compatibility alias for --max-wait.
  --poll N            Optional. Poll interval in seconds for progressive extraction (default: 10).
  --stable-polls N    Optional. Stop after N unchanged polls (default: 2).
  --debug-ocr-on-error Optional. Enable OCR debug dump only when extraction/error state is bad.
  --auto-always-allow Optional. Try to auto-click "Always allow" prompts while polling (default: enabled).
  --no-auto-always-allow Disable auto-click handler for authorization prompts.
  --auto-allow-cooldown N Cooldown in seconds between auto-click attempts (default: 4).
  --out-dir PATH      Optional. Output directory (default: logs-codex-runs).
  --print-output      Optional. Print extracted response text to stdout.
  -h, --help          Show this help.

Output files:
  <out-dir>/claude-ui-io-YYYYMMDD-HHMMSS.input.txt
  <out-dir>/claude-ui-io-YYYYMMDD-HHMMSS.response.txt
  <out-dir>/claude-ui-io-YYYYMMDD-HHMMSS.actions.txt
  <out-dir>/claude-ui-io-YYYYMMDD-HHMMSS.meta.env
EOF
}

while (($#)); do
  case "$1" in
    --input)
      shift
      if (($# == 0)); then
        echo "Missing value for --input" >&2
        exit 2
      fi
      INPUT_TEXT="$1"
      ;;
    --input-file)
      shift
      if (($# == 0)); then
        echo "Missing value for --input-file" >&2
        exit 2
      fi
      INPUT_FILE="$1"
      ;;
    --chat-mode)
      shift
      if (($# == 0)); then
        echo "Missing value for --chat-mode" >&2
        exit 2
      fi
      CHAT_MODE_VALUE="$1"
      ;;
    --same-chat)
      CHAT_MODE_VALUE="same"
      ;;
    --new-chat)
      CHAT_MODE_VALUE="new"
      ;;
    --max-wait|--wait)
      shift
      if (($# == 0)); then
        echo "Missing value for --max-wait/--wait" >&2
        exit 2
      fi
      MAX_WAIT_SECONDS_VALUE="$1"
      ;;
    --poll)
      shift
      if (($# == 0)); then
        echo "Missing value for --poll" >&2
        exit 2
      fi
      POLL_SECONDS_VALUE="$1"
      ;;
    --stable-polls)
      shift
      if (($# == 0)); then
        echo "Missing value for --stable-polls" >&2
        exit 2
      fi
      STABLE_POLLS_VALUE="$1"
      ;;
    --debug-ocr-on-error)
      DEBUG_OCR_ON_ERROR_VALUE=1
      ;;
    --auto-always-allow)
      AUTO_ALWAYS_ALLOW_VALUE=1
      ;;
    --no-auto-always-allow)
      AUTO_ALWAYS_ALLOW_VALUE=0
      ;;
    --auto-allow-cooldown)
      shift
      if (($# == 0)); then
        echo "Missing value for --auto-allow-cooldown" >&2
        exit 2
      fi
      AUTO_ALLOW_COOLDOWN_SECONDS_VALUE="$1"
      ;;
    --out-dir)
      shift
      if (($# == 0)); then
        echo "Missing value for --out-dir" >&2
        exit 2
      fi
      OUT_DIR="$1"
      ;;
    --print-output)
      PRINT_OUTPUT=1
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
  shift
done

if [[ -n "${INPUT_TEXT}" && -n "${INPUT_FILE}" ]]; then
  echo "Use only one of --input or --input-file" >&2
  usage >&2
  exit 2
fi

if [[ -n "${INPUT_FILE}" ]]; then
  if [[ ! -f "${INPUT_FILE}" ]]; then
    echo "Input file not found: ${INPUT_FILE}" >&2
    exit 2
  fi
  INPUT_TEXT="$(cat "${INPUT_FILE}")"
fi

if [[ -z "${INPUT_TEXT}" ]]; then
  echo "--input or --input-file is required" >&2
  usage >&2
  exit 2
fi

if [[ ! -x "${UI_SCRIPT}" ]]; then
  echo "UI script missing or not executable: ${UI_SCRIPT}" >&2
  exit 127
fi

if [[ "${CHAT_MODE_VALUE}" != "same" && "${CHAT_MODE_VALUE}" != "new" ]]; then
  echo "Invalid --chat-mode: ${CHAT_MODE_VALUE}. Allowed: same|new" >&2
  exit 2
fi

mkdir -p "${OUT_DIR}"

RUN_LOG="$(mktemp /tmp/claude-ui-io-run.XXXXXX.log)"
cleanup() {
  rm -f "${RUN_LOG}"
}
trap cleanup EXIT

CHAT_MODE="${CHAT_MODE_VALUE}" \
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS_VALUE}" \
POLL_SECONDS="${POLL_SECONDS_VALUE}" \
STABLE_POLLS="${STABLE_POLLS_VALUE}" \
DEBUG_OCR_ON_ERROR="${DEBUG_OCR_ON_ERROR_VALUE}" \
AUTO_ALWAYS_ALLOW="${AUTO_ALWAYS_ALLOW_VALUE}" \
AUTO_ALLOW_COOLDOWN_SECONDS="${AUTO_ALLOW_COOLDOWN_SECONDS_VALUE}" \
OUT_DIR="${OUT_DIR}" \
"${UI_SCRIPT}" "${INPUT_TEXT}" | tee "${RUN_LOG}"

get_key() {
  local key="$1"
  sed -n "s/^${key}=//p" "${RUN_LOG}" | tail -n 1
}

STAMP="$(date +%Y%m%d-%H%M%S)"
PREFIX="${OUT_DIR}/claude-ui-io-${STAMP}"

SCREENSHOT_PATH="$(get_key screenshot)"
CHAT_MODE_USED="$(get_key chat_mode)"
EXTRACTION_SOURCE="$(get_key extraction_source)"
DIRECT_RESPONSE_PATH="$(get_key direct_response)"
DIRECT_ACTIONS_PATH="$(get_key direct_actions)"
BASELINE_RAW_PATH="$(get_key baseline_raw)"
BASELINE_RESPONSE_PATH="$(get_key baseline_response)"
MESSAGE_NORMALIZED_PATH="$(get_key message_normalized)"
PROGRESS_LOG_PATH="$(get_key progress_log)"
SNAPSHOTS_DIR_PATH="$(get_key snapshots_dir)"
POLLS_TOTAL="$(get_key polls_total)"
ELAPSED_SECONDS="$(get_key elapsed_seconds)"
STOP_REASON="$(get_key stop_reason)"
ERROR_DETECTED="$(get_key error_detected)"
DEBUG_OCR_PATH="$(get_key debug_ocr)"
INPUT_INJECTION_METHOD="$(get_key input_injection_method)"
AUTO_ALLOW_DETECTED="$(get_key auto_allow_detected)"
AUTO_ALLOW_ATTEMPTS="$(get_key auto_allow_attempts)"
AUTO_ALWAYS_ALLOW_USED="$(get_key auto_always_allow)"

RESPONSE_SRC=""
ACTIONS_SRC=""

if [[ -n "${DIRECT_RESPONSE_PATH}" && -s "${DIRECT_RESPONSE_PATH}" ]]; then
  RESPONSE_SRC="${DIRECT_RESPONSE_PATH}"
fi

if [[ -n "${DIRECT_ACTIONS_PATH}" && -s "${DIRECT_ACTIONS_PATH}" ]]; then
  ACTIONS_SRC="${DIRECT_ACTIONS_PATH}"
fi

INPUT_OUT="${PREFIX}.input.txt"
RESPONSE_OUT="${PREFIX}.response.txt"
ACTIONS_OUT="${PREFIX}.actions.txt"
META_OUT="${PREFIX}.meta.env"

printf '%s\n' "${INPUT_TEXT}" > "${INPUT_OUT}"

if [[ -n "${RESPONSE_SRC}" ]]; then
  cp "${RESPONSE_SRC}" "${RESPONSE_OUT}"
else
  : > "${RESPONSE_OUT}"
fi

if [[ -n "${ACTIONS_SRC}" ]]; then
  cp "${ACTIONS_SRC}" "${ACTIONS_OUT}"
else
  : > "${ACTIONS_OUT}"
fi

{
  echo "timestamp=$(date '+%Y-%m-%d %H:%M:%S')"
  echo "input_file=${INPUT_OUT}"
  echo "response_file=${RESPONSE_OUT}"
  echo "actions_file=${ACTIONS_OUT}"
  echo "screenshot_file=${SCREENSHOT_PATH}"
  echo "chat_mode=${CHAT_MODE_USED:-${CHAT_MODE_VALUE}}"
  echo "extraction_source=${EXTRACTION_SOURCE:-unknown}"
  echo "response_source=${RESPONSE_SRC}"
  echo "actions_source=${ACTIONS_SRC}"
  echo "baseline_raw=${BASELINE_RAW_PATH}"
  echo "baseline_response=${BASELINE_RESPONSE_PATH}"
  echo "message_normalized=${MESSAGE_NORMALIZED_PATH}"
  echo "progress_log=${PROGRESS_LOG_PATH}"
  echo "snapshots_dir=${SNAPSHOTS_DIR_PATH}"
  echo "polls_total=${POLLS_TOTAL}"
  echo "elapsed_seconds=${ELAPSED_SECONDS}"
  echo "stop_reason=${STOP_REASON}"
  echo "error_detected=${ERROR_DETECTED}"
  echo "debug_ocr=${DEBUG_OCR_PATH}"
  echo "input_injection_method=${INPUT_INJECTION_METHOD}"
  echo "auto_always_allow=${AUTO_ALWAYS_ALLOW_USED:-${AUTO_ALWAYS_ALLOW_VALUE}}"
  echo "auto_allow_detected=${AUTO_ALLOW_DETECTED}"
  echo "auto_allow_attempts=${AUTO_ALLOW_ATTEMPTS}"
} > "${META_OUT}"

echo
echo "io_input=${INPUT_OUT}"
echo "io_output=${RESPONSE_OUT}"
echo "io_actions=${ACTIONS_OUT}"
echo "io_meta=${META_OUT}"
echo "io_screenshot=${SCREENSHOT_PATH}"
echo "io_chat_mode=${CHAT_MODE_USED:-${CHAT_MODE_VALUE}}"
echo "io_progress_log=${PROGRESS_LOG_PATH}"
echo "io_snapshots_dir=${SNAPSHOTS_DIR_PATH}"
echo "io_stop_reason=${STOP_REASON}"
echo "io_error_detected=${ERROR_DETECTED}"
echo "io_input_injection=${INPUT_INJECTION_METHOD}"
echo "io_auto_always_allow=${AUTO_ALWAYS_ALLOW_USED:-${AUTO_ALWAYS_ALLOW_VALUE}}"
echo "io_auto_allow_detected=${AUTO_ALLOW_DETECTED}"
echo "io_auto_allow_attempts=${AUTO_ALLOW_ATTEMPTS}"

if (( PRINT_OUTPUT == 1 )); then
  echo
  echo "--- extracted response ---"
  cat "${RESPONSE_OUT}"
fi
