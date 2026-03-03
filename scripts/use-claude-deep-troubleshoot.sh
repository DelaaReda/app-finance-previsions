#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN_LOG="${HOME}/.config/Claude/logs/main.log"
WEB_LOG="${HOME}/.config/Claude/logs/claude.ai-web.log"
LAUNCHER_LOG="${HOME}/.cache/claude-desktop-debian/launcher.log"
NEW_CHAT_WRAPPER="${ROOT_DIR}/scripts/claude_desktop_new_chat.sh"

OPEN_CHAT_PROMPT=""
FORCE_OPEN_CHAT=0
NO_NETWORK=0

timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

usage() {
  cat <<'EOF'
Usage:
  use-claude-deep-troubleshoot.sh [--open-chat "prompt"] [--force-open-chat] [--no-network]

Options:
  --open-chat "prompt"   Open a new Claude Desktop chat when checks are healthy.
  --force-open-chat      Force chat opening even if checks report degraded state.
  --no-network           Skip HTTP probes and status-page checks.
  -h, --help             Show this help.

Examples:
  scripts/use-claude-deep-troubleshoot.sh
  scripts/use-claude-deep-troubleshoot.sh --open-chat "post-recovery-smoke-test"
  scripts/use-claude-deep-troubleshoot.sh --no-network
EOF
}

while (($#)); do
  case "$1" in
    --open-chat)
      shift
      if (($# == 0)); then
        echo "Missing value for --open-chat" >&2
        exit 2
      fi
      OPEN_CHAT_PROMPT="$1"
      ;;
    --force-open-chat)
      FORCE_OPEN_CHAT=1
      ;;
    --no-network)
      NO_NETWORK=1
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

mkdir -p "${ROOT_DIR}/logs-codex-runs"
REPORT_PATH="${ROOT_DIR}/logs-codex-runs/claude-deep-troubleshoot-$(date +%Y%m%d-%H%M%S).txt"
exec > >(tee -a "${REPORT_PATH}") 2>&1

TMP_DIR="$(mktemp -d /tmp/claude-deep-troubleshoot.XXXXXX)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

section() {
  echo
  echo "== $1 =="
}

kv() {
  printf "%-30s %s\n" "$1" "$2"
}

safe_count_pattern() {
  local file="$1"
  local pattern="$2"
  if [[ ! -f "${file}" ]]; then
    echo 0
    return
  fi
  rg -c "${pattern}" "${file}" 2>/dev/null || echo 0
}

probe_post_json() {
  local label="$1"
  local url="$2"
  local data="$3"
  local headers_file="${TMP_DIR}/${label}.headers"
  local body_file="${TMP_DIR}/${label}.body"
  local code

  code="$(curl -sS -o "${body_file}" -D "${headers_file}" -w "%{http_code}" -X POST "${url}" \
    -H "anthropic-version: 2023-06-01" \
    -H "Content-Type: application/json" \
    --data "${data}" || true)"
  if [[ -z "${code}" ]]; then
    code="000"
  fi

  local body_head
  body_head="$(head -c 160 "${body_file}" 2>/dev/null | tr '\n' ' ' || true)"
  local cf_mitigated
  cf_mitigated="$(rg -i '^cf-mitigated:' "${headers_file}" | awk -F': ' '{print $2}' | tr -d '\r' || true)"
  echo "${code}|${body_head}|${cf_mitigated}"
}

probe_head() {
  local label="$1"
  local url="$2"
  local headers_file="${TMP_DIR}/${label}.headers"
  local code

  code="$(curl -sS -I -o /dev/null -D "${headers_file}" -w "%{http_code}" "${url}" || true)"
  if [[ -z "${code}" ]]; then
    code="000"
  fi
  local cf_mitigated
  cf_mitigated="$(rg -i '^cf-mitigated:' "${headers_file}" | awk -F': ' '{print $2}' | tr -d '\r' || true)"
  echo "${code}|${cf_mitigated}"
}

echo "Claude Desktop Deep Troubleshoot"
echo "Generated at: $(timestamp)"
echo "Report path : ${REPORT_PATH}"

section "Local Environment"
kv "Root directory" "${ROOT_DIR}"
kv "Script path" "${BASH_SOURCE[0]}"
kv "Hostname" "$(hostname)"
kv "Kernel" "$(uname -srmo)"

CLAUDE_BIN_PATH="$(command -v claude-desktop || true)"
if [[ -n "${CLAUDE_BIN_PATH}" ]]; then
  kv "claude-desktop" "${CLAUDE_BIN_PATH}"
else
  kv "claude-desktop" "NOT_FOUND"
fi

for f in "${MAIN_LOG}" "${WEB_LOG}" "${LAUNCHER_LOG}" "${NEW_CHAT_WRAPPER}"; do
  if [[ -f "${f}" ]]; then
    kv "exists: ${f}" "yes"
  else
    kv "exists: ${f}" "no"
  fi
done

section "Runtime State"
PROCESS_LIST="$(pgrep -af '/usr/lib/claude-desktop/node_modules/electron/dist/electron' || true)"
if [[ -n "${PROCESS_LIST}" ]]; then
  echo "${PROCESS_LIST}" | sed 's/^/  /'
else
  echo "  No running Claude electron process detected."
fi

section "Log Signals"
RECENT_MAIN="${TMP_DIR}/recent-main.log"
RECENT_WEB="${TMP_DIR}/recent-web.log"
tail -n 3000 "${MAIN_LOG}" > "${RECENT_MAIN}" 2>/dev/null || true
tail -n 1500 "${WEB_LOG}" > "${RECENT_WEB}" 2>/dev/null || true

COUNT_ACCOUNT_ACTIVE="$(safe_count_pattern "${RECENT_MAIN}" 'account active and logged in')"
COUNT_BOOTSTRAP_NO_ACCOUNT="$(safe_count_pattern "${RECENT_MAIN}" 'Bootstrap response has no account')"
COUNT_OAUTH_503="$(safe_count_pattern "${RECENT_MAIN}" 'oauth failed: authorize returned 503|server error 503|no healthy upstream|upstream connect error')"
COUNT_NAV_500="$(safe_count_pattern "${RECENT_MAIN}" 'Navigation to https://claude.ai.*failed with status code 500')"
COUNT_WEB_INTERNAL="$(safe_count_pattern "${RECENT_WEB}" 'Internal server error|Fatal error boundary|Server Components render')"

kv "account_active_logged_in" "${COUNT_ACCOUNT_ACTIVE}"
kv "bootstrap_no_account" "${COUNT_BOOTSTRAP_NO_ACCOUNT}"
kv "oauth_upstream_errors" "${COUNT_OAUTH_503}"
kv "navigation_500_errors" "${COUNT_NAV_500}"
kv "web_internal_errors" "${COUNT_WEB_INTERNAL}"

echo "Recent critical lines (main.log):"
rg -n 'oauth failed|no healthy upstream|upstream connect error|failed with status code 500|account active and logged in|Bootstrap response has no account' "${RECENT_MAIN}" | tail -n 30 | sed 's/^/  /' || true

VERDICT_REMOTE=0
VERDICT_LOCAL=0
REMOTE_REASON=""
LOCAL_REASON=""

if [[ -z "${CLAUDE_BIN_PATH}" ]]; then
  VERDICT_LOCAL=1
  LOCAL_REASON="${LOCAL_REASON}claude-desktop binary missing; "
fi
if [[ ! -f "${NEW_CHAT_WRAPPER}" ]]; then
  VERDICT_LOCAL=1
  LOCAL_REASON="${LOCAL_REASON}new-chat wrapper missing; "
fi
if [[ "${COUNT_OAUTH_503}" -gt 0 ]]; then
  VERDICT_REMOTE=1
  REMOTE_REASON="${REMOTE_REASON}oauth upstream errors in logs; "
fi
if [[ "${COUNT_NAV_500}" -gt 0 ]]; then
  VERDICT_REMOTE=1
  REMOTE_REASON="${REMOTE_REASON}claude.ai navigation 500 in logs; "
fi

STATUS_INDICATOR="unknown"
STATUS_DESCRIPTION="unknown"
STATUS_INCIDENT_COUNT="unknown"
TOKEN_PROBE_CODE="skipped"
TOKEN_PROBE_SNIPPET="skipped"
AUTHORIZE_PROBE_CODE="skipped"
AUTHORIZE_PROBE_SNIPPET="skipped"
CLAUDE_AI_HEAD_CODE="skipped"
CLAUDE_AI_CF="skipped"

if (( NO_NETWORK == 0 )); then
  section "Network Probes"

  STATUS_JSON="${TMP_DIR}/status.json"
  curl -sSL "https://status.claude.com/api/v2/status.json" -o "${STATUS_JSON}" || true
  if [[ -s "${STATUS_JSON}" ]] && command -v jq >/dev/null 2>&1; then
    STATUS_INDICATOR="$(jq -r '.status.indicator // "unknown"' "${STATUS_JSON}" 2>/dev/null || echo unknown)"
    STATUS_DESCRIPTION="$(jq -r '.status.description // "unknown"' "${STATUS_JSON}" 2>/dev/null || echo unknown)"
  fi

  INCIDENTS_JSON="${TMP_DIR}/incidents.json"
  curl -sSL "https://status.claude.com/api/v2/incidents/unresolved.json" -o "${INCIDENTS_JSON}" || true
  if [[ -s "${INCIDENTS_JSON}" ]] && command -v jq >/dev/null 2>&1; then
    STATUS_INCIDENT_COUNT="$(jq -r '.incidents | length' "${INCIDENTS_JSON}" 2>/dev/null || echo unknown)"
  fi

  probe_token="$(probe_post_json "oauth_token" "https://api.anthropic.com/v1/oauth/token" '{}')"
  TOKEN_PROBE_CODE="$(echo "${probe_token}" | cut -d'|' -f1)"
  TOKEN_PROBE_SNIPPET="$(echo "${probe_token}" | cut -d'|' -f2)"

  ORG_ID="5c462b30-197e-426b-8d79-be1b0e16147e"
  authorize_payload='{"response_type":"code","client_id":"9d1c250a-e61b-44d9-88ed-5944d1962f5e","organization_uuid":"5c462b30-197e-426b-8d79-be1b0e16147e","redirect_uri":"https://console.anthropic.com/oauth/code/callback","scope":"user:inference user:sessions:claude_code","state":"x","code_challenge":"x","code_challenge_method":"S256"}'
  probe_authorize="$(probe_post_json "oauth_authorize" "https://api.anthropic.com/v1/oauth/${ORG_ID}/authorize" "${authorize_payload}")"
  AUTHORIZE_PROBE_CODE="$(echo "${probe_authorize}" | cut -d'|' -f1)"
  AUTHORIZE_PROBE_SNIPPET="$(echo "${probe_authorize}" | cut -d'|' -f2)"

  probe_claude="$(probe_head "claude_ai_head" "https://claude.ai")"
  CLAUDE_AI_HEAD_CODE="$(echo "${probe_claude}" | cut -d'|' -f1)"
  CLAUDE_AI_CF="$(echo "${probe_claude}" | cut -d'|' -f2)"

  kv "status.indicator" "${STATUS_INDICATOR}"
  kv "status.description" "${STATUS_DESCRIPTION}"
  kv "unresolved.incidents" "${STATUS_INCIDENT_COUNT}"
  kv "oauth token probe code" "${TOKEN_PROBE_CODE}"
  kv "oauth token probe body" "${TOKEN_PROBE_SNIPPET}"
  kv "oauth authorize code" "${AUTHORIZE_PROBE_CODE}"
  kv "oauth authorize body" "${AUTHORIZE_PROBE_SNIPPET}"
  kv "claude.ai HEAD code" "${CLAUDE_AI_HEAD_CODE}"
  kv "claude.ai cf-mitigated" "${CLAUDE_AI_CF:-none}"

  if [[ "${STATUS_INDICATOR}" == "minor" || "${STATUS_INDICATOR}" == "major" || "${STATUS_INDICATOR}" == "critical" ]]; then
    VERDICT_REMOTE=1
    REMOTE_REASON="${REMOTE_REASON}status page indicator=${STATUS_INDICATOR}; "
  fi
  if [[ "${TOKEN_PROBE_CODE}" == "503" || "${AUTHORIZE_PROBE_CODE}" == "503" ]]; then
    VERDICT_REMOTE=1
    REMOTE_REASON="${REMOTE_REASON}oauth endpoint returns 503; "
  fi
fi

section "Verdict"
VERDICT="HEALTHY"
EXIT_CODE=0

if (( VERDICT_REMOTE == 1 && VERDICT_LOCAL == 1 )); then
  VERDICT="DEGRADED_REMOTE_AND_LOCAL"
  EXIT_CODE=30
elif (( VERDICT_REMOTE == 1 )); then
  VERDICT="DEGRADED_REMOTE"
  EXIT_CODE=10
elif (( VERDICT_LOCAL == 1 )); then
  VERDICT="LOCAL_CONFIG_ISSUE"
  EXIT_CODE=20
fi

kv "verdict" "${VERDICT}"
if [[ -n "${REMOTE_REASON}" ]]; then
  kv "remote_reason" "${REMOTE_REASON}"
fi
if [[ -n "${LOCAL_REASON}" ]]; then
  kv "local_reason" "${LOCAL_REASON}"
fi

section "Next Actions"
if [[ "${VERDICT}" == "HEALTHY" ]]; then
  echo "  1) Open a new chat test:"
  echo "     ${NEW_CHAT_WRAPPER} --prompt \"post-recovery-smoke-test\""
  echo "  2) If successful, continue normal Claude Desktop usage."
elif [[ "${VERDICT}" == "DEGRADED_REMOTE" || "${VERDICT}" == "DEGRADED_REMOTE_AND_LOCAL" ]]; then
  echo "  1) This currently looks remote/upstream (service-side) and may be transient."
  echo "  2) Re-run this command every few minutes:"
  echo "     ${ROOT_DIR}/scripts/use-claude-deep-troubleshoot.sh"
  echo "  3) Wait for status indicator to return to normal and OAuth probes to stop returning 503."
fi
if [[ "${VERDICT}" == "LOCAL_CONFIG_ISSUE" || "${VERDICT}" == "DEGRADED_REMOTE_AND_LOCAL" ]]; then
  echo "  4) Fix local blockers first (missing binary/wrapper/log paths), then re-run checks."
fi

if [[ -n "${OPEN_CHAT_PROMPT}" ]]; then
  section "Open Chat Request"
  if [[ ! -x "${NEW_CHAT_WRAPPER}" ]]; then
    echo "  Cannot open chat: wrapper not executable at ${NEW_CHAT_WRAPPER}"
  elif [[ "${VERDICT}" == "HEALTHY" || "${FORCE_OPEN_CHAT}" -eq 1 ]]; then
    echo "  Attempting to open chat with prompt: ${OPEN_CHAT_PROMPT}"
    # Detach from this diagnostic run so desktop launch does not block completion.
    nohup "${NEW_CHAT_WRAPPER}" --prompt "${OPEN_CHAT_PROMPT}" >/dev/null 2>&1 &
    OPEN_CHAT_PID="$!"
    if kill -0 "${OPEN_CHAT_PID}" 2>/dev/null; then
      echo "  Open-chat dispatched in background (pid=${OPEN_CHAT_PID})."
    else
      echo "  Open-chat command exited quickly; check desktop logs if no window appears."
    fi
  else
    echo "  Skipped open-chat: verdict is ${VERDICT}. Use --force-open-chat to override."
  fi
fi

echo
echo "Done. Report saved to: ${REPORT_PATH}"
exit "${EXIT_CODE}"
