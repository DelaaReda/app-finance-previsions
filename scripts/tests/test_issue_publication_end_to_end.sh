#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
REPORT_SCRIPT="${ROOT}/scripts/iteration_issue_report.py"

tmpdir="$(mktemp -d)"
trap 'rm -rf "${tmpdir}"' EXIT

payload() {
  cat <<'EOF'
STATUS: IN_PROGRESS
DELTA: NO_DELTA
EVIDENCE: issues=none; task_update=none_no_signal
RISKS: none
NEXT: continue
VERDICT: GO_WITH_CAUTION
BLOCKER_ID: NONE
NEXT_ACTION_UNIQUE: E2E_NEXT
EOF
}

run_case() {
  local role="$1"
  local source="$2"
  local tick="$3"
  local rc_primary="$4"
  local rc_retry="$5"
  local rc_final="$6"
  local rc_codex="$7"
  local raw_primary="${8:-}"
  local raw_retry="${9:-}"
  local raw_codex="${10:-}"
  local trace="${11:-}"

  local payload_file="${tmpdir}/${tick}.payload.txt"
  local raw_primary_file="${tmpdir}/${tick}.raw.primary.txt"
  local raw_retry_file="${tmpdir}/${tick}.raw.retry.txt"
  local raw_codex_file="${tmpdir}/${tick}.raw.codex.txt"
  local trace_file="${tmpdir}/${tick}.trace.log"
  local latest_file="${tmpdir}/agent-iteration-issues-latest.json"
  local events_file="${tmpdir}/agent-iteration-issues.jsonl"
  local state_dir="${tmpdir}/state"

  payload >"${payload_file}"
  printf '%s\n' "${raw_primary}" >"${raw_primary_file}"
  printf '%s\n' "${raw_retry}" >"${raw_retry_file}"
  printf '%s\n' "${raw_codex}" >"${raw_codex_file}"
  printf '%s\n' "${trace}" >"${trace_file}"

  python3 "${REPORT_SCRIPT}" \
    "${role}" \
    "${source}" \
    "${payload_file}" \
    "${latest_file}" \
    "${events_file}" \
    "${state_dir}" \
    "${tick}" \
    "codex" \
    "tmux" \
    "${rc_primary}" \
    "${rc_retry}" \
    "${rc_final}" \
    "${rc_codex}" \
    "${raw_primary_file}" \
    "${raw_retry_file}" \
    "${raw_codex_file}" \
    "${trace_file}" \
    "queue_test" \
    "workboard_test"
}

# tick normal
run_case "planner" "primary_structured" "E2E-OK" "0" "0" "0" "-1" "" "" "" ""
# timeout
run_case "planner" "retry_structured" "E2E-TO" "124" "124" "124" "-1" "timeout reached" "" "" ""
# session_not_ready
run_case "admin" "primary_structured" "E2E-S43" "43" "0" "43" "-1" "session_not_ready role=admin" "" "" ""
# fallback loop / broken pipe
run_case "dev" "fallback_checkpoint" "E2E-FB" "65" "124" "124" "65" "tick_mismatch" "printf: write error: Broken pipe" "" ""
# permission denied
run_case "admin" "primary_structured" "E2E-PERM" "1" "0" "1" "-1" "mkdir: cannot create directory '/home/venom/shared/logs-codex-runs': Operation not permitted" "" "" ""

python3 - "${tmpdir}/agent-iteration-issues.jsonl" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
rows = []
for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
    if ln.strip():
        rows.append(json.loads(ln))

assert len(rows) >= 5, f"expected >=5 rows, got {len(rows)}"

def has_code(code: str) -> bool:
    for row in rows:
        for issue in row.get("issues", []):
            if isinstance(issue, dict) and issue.get("code") == code:
                return True
    return False

# normal tick
ok_rows = [r for r in rows if r.get("tick_id") == "E2E-OK"]
assert ok_rows, "missing E2E-OK row"
assert ok_rows[0].get("issue_status") == "none", ok_rows[0]

assert has_code("TIMEOUT_124"), "missing TIMEOUT_124"
assert has_code("SESSION_NOT_READY_43"), "missing SESSION_NOT_READY_43"
assert has_code("CHECKPOINT_FALLBACK"), "missing CHECKPOINT_FALLBACK"
assert has_code("BROKEN_PIPE"), "missing BROKEN_PIPE"
assert has_code("PERMISSION_OP_NOT_PERMITTED"), "missing PERMISSION_OP_NOT_PERMITTED"

print("PASS issue publication e2e")
PY
