#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DEFAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
VM_SHARED_ROOT="/home/venom/shared/analyse-financiere"
ROOT="${FINANCE_COPILOT_ROOT:-$DEFAULT_ROOT}"
if [[ -z "${FINANCE_COPILOT_ROOT:-}" && -d "$VM_SHARED_ROOT" ]]; then
  ROOT="$VM_SHARED_ROOT"
fi
cd "$ROOT"

STATE_DIR="${ADMIN_AGENTS_REFRESH_STATE_DIR:-$HOME/.openclaw/cron/admin-state}"
mkdir -p "$STATE_DIR"

EXEC_LATEST_FILE="${EXEC_LATEST_FILE:-docs/orchestrator-ops/executors-monitoring-latest.json}"
CHAT_FILE="${ADMIN_AGENTS_CHAT_FILE:-docs/ops/ADMIN_TEAM_CHAT.md}"

LIMIT="${1:-4}"
if ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || [[ "$LIMIT" -lt 1 ]]; then
  LIMIT=4
fi

now_local="$(TZ=America/New_York date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %Z')"

log_chat() {
  local type="$1"; shift
  local msg="$*"
  [[ -f "$CHAT_FILE" ]] || return 0
  printf -- "- [%s] [admin-agents] TYPE: %s MSG: %s\n" "$now_local" "$type" "$msg" >> "$CHAT_FILE"
}

if [[ ! -f "$EXEC_LATEST_FILE" ]]; then
  echo "REFRESH status=NOOP reason=exec_latest_missing"
  exit 0
fi

# Process issues only (not product evidence gaps)
python3 - "$EXEC_LATEST_FILE" "$LIMIT" "$STATE_DIR" <<'PY'
import json, sys, os, re
from pathlib import Path

path=Path(sys.argv[1])
limit=int(sys.argv[2])
state_dir=Path(sys.argv[3])
state_dir.mkdir(parents=True, exist_ok=True)
idx_file=state_dir/'refresh_idx.txt'

j=json.loads(path.read_text(encoding='utf-8',errors='ignore'))
roles=j.get('roles',{})

process_patterns=[
    r'permission_denied',
    r'no_slot|absence_slot|slot_.*absent',
    r'channels_probe_.*permission_denied',
    r'publicat.*channels.*none',
    r'no_usable_tmpdir_pytest',
    r'role_contract_errors',
]
proc_re=re.compile('|'.join(process_patterns), re.I)

# roles with process issues
candidates=[]
for role,data in roles.items():
    issues=str(data.get('issues') or '')
    if issues and issues!='none' and proc_re.search(issues):
        candidates.append(role)

candidates=sorted(set(candidates))

idx=0
if idx_file.exists():
    try:
        idx=int(idx_file.read_text().strip() or '0')
    except:
        idx=0

picked=[]
if candidates:
    for _ in range(min(limit, len(candidates))):
        picked.append(candidates[idx % len(candidates)])
        idx += 1

idx_file.write_text(str(idx))

print('\n'.join(picked))
PY

# If no candidates, stop.
mapfile -t roles_to_refresh < <(python3 - "$EXEC_LATEST_FILE" "$LIMIT" "$STATE_DIR" <<'PY'
import json, sys, os, re
from pathlib import Path
path=Path(sys.argv[1]); limit=int(sys.argv[2]); state_dir=Path(sys.argv[3])
idx_file=state_dir/'refresh_idx.txt'
j=json.loads(path.read_text(encoding='utf-8',errors='ignore'))
roles=j.get('roles',{})
proc_re=re.compile(r'permission_denied|no_slot|absence_slot|slot_.*absent|channels_probe_.*permission_denied|publicat.*channels.*none|no_usable_tmpdir_pytest|role_contract_errors', re.I)
candidates=sorted({r for r,d in roles.items() if (d.get('issues') and str(d.get('issues'))!='none' and proc_re.search(str(d.get('issues'))))})
idx=0
if idx_file.exists():
  try: idx=int(idx_file.read_text().strip() or '0')
  except: idx=0
picked=[]
for _ in range(min(limit,len(candidates))):
  if not candidates: break
  picked.append(candidates[idx % len(candidates)])
  idx+=1
idx_file.write_text(str(idx))
print('\n'.join(picked))
PY
)

if [[ "${#roles_to_refresh[@]}" -eq 0 ]]; then
  echo "REFRESH status=NOOP reason=no_process_issues"
  exit 0
fi

ok=0
fail=0
refreshed=()

for role in "${roles_to_refresh[@]}"; do
  [[ -z "$role" ]] && continue
  # Probe channels to confirm locks are accessible now.
  if python3 scripts/parallel_workstream.py channels --role "$role" --limit 2 >/dev/null 2>&1; then
    # Force a role tick to refresh last_contract/issues.
    if bash scripts/cron_run_manager.sh run-now --job "$role" --timeout 180000 >/dev/null 2>&1; then
      ok=$((ok+1))
      refreshed+=("$role")
    else
      fail=$((fail+1))
    fi
  else
    fail=$((fail+1))
  fi
done

if [[ "$ok" -gt 0 ]]; then
  log_chat "INFO" "process_issue_refresh roles=$(IFS=,; echo "${refreshed[*]}") ok=${ok} fail=${fail}"
fi

echo "REFRESH status=OK ok=${ok} fail=${fail} roles=$(IFS=,; echo "${refreshed[*]}")"
