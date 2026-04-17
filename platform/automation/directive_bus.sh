#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
WORKSPACE_HELPER="${SCRIPT_DIR}/lib/workspace_paths.sh"
if [[ -n "${FINANCE_COPILOT_ROOT:-}" ]]; then
  ROOT="${FINANCE_COPILOT_ROOT}"
elif [[ -f "$WORKSPACE_HELPER" ]]; then
  # shellcheck source=/dev/null
  source "$WORKSPACE_HELPER"
  ROOT="$(fc_prefer_writable_workspace "$(fc_resolve_workspace_root "$SCRIPT_DIR")")"
else
  ROOT="$SOURCE_ROOT"
fi
cd "$ROOT"

BUS_FILE="${DIRECTIVE_BUS_FILE:-$ROOT/docs/ops/DIRECTIVE_BUS.jsonl}"

usage() {
  cat <<'EOF'
Usage: directive_bus.sh <cmd> [args]

Commands:
  post --targets <all|csv_roles> --msg <text> [--kind <policy|delivery|emergency>] [--ttl-min <n>]
  active --role <role> [--limit <n>]
  tail [--limit <n>]

Notes:
- Records are JSONL objects.
- targets is either "all" or comma-separated roles.
EOF
}

now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

sanitize_msg() {
  # single-line, no pipes
  printf '%s' "$1" \
    | tr '\r\n\t' '   ' \
    | sed 's/[|]/\//g' \
    | sed 's/  */ /g' \
    | sed 's/^ *//; s/ *$//'
}

post_cmd() {
  local targets=""
  local msg=""
  local kind="policy"
  local ttl_min=60

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --targets) targets="$2"; shift 2 ;;
      --msg) msg="$2"; shift 2 ;;
      --kind) kind="$2"; shift 2 ;;
      --ttl-min) ttl_min="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "Unknown arg: $1"; usage; exit 2 ;;
    esac
  done

  if [[ -z "$targets" || -z "$msg" ]]; then
    echo "ERROR: --targets and --msg are required" >&2
    exit 2
  fi

  case "$kind" in
    policy|delivery|emergency) ;;
    *) echo "ERROR: invalid --kind (policy|delivery|emergency)" >&2; exit 2 ;;
  esac
  if ! [[ "$ttl_min" =~ ^[0-9]+$ ]] || [[ "$ttl_min" -lt 1 ]]; then
    echo "ERROR: invalid --ttl-min" >&2
    exit 2
  fi

  local ts
  ts="$(now_iso)"
  local id
  id="DIR_$(printf '%s' "$ts" | tr -d ':-' | tr -d 'T' | tr -d 'Z')_$$"

  local exp
  exp="$(date -u -d "+${ttl_min} minutes" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || python3 - <<PY
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc)+timedelta(minutes=${ttl_min})).strftime('%Y-%m-%dT%H:%M:%SZ'))
PY
)"

  local from
  from="${ADMIN_ROLE:-main}"

  local msg_s
  msg_s="$(sanitize_msg "$msg")"

  local targets_json
  if [[ "$targets" == "all" ]]; then
    targets_json='["all"]'
  else
    # csv -> json array
    targets_json="$(python3 - <<PY
import json
raw="""$targets"""
arr=[s.strip() for s in raw.split(',') if s.strip()]
print(json.dumps(arr))
PY
)"
  fi

  mkdir -p "$(dirname "$BUS_FILE")"
  printf '%s\n' "$(jq -nc \
    --arg id "$id" \
    --arg ts "$ts" \
    --arg expires_at "$exp" \
    --arg from "$from" \
    --arg kind "$kind" \
    --arg msg "$msg_s" \
    --argjson targets "$targets_json" \
    '{id:$id,ts:$ts,expires_at:$expires_at,from:$from,kind:$kind,targets:$targets,msg:$msg}'
  )" >> "$BUS_FILE"

  echo "OK id=$id expires_at=$exp targets=$targets kind=$kind"
}

active_cmd() {
  local role=""
  local limit=5
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --role) role="$2"; shift 2 ;;
      --limit) limit="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "Unknown arg: $1"; usage; exit 2 ;;
    esac
  done
  if [[ -z "$role" ]]; then
    echo "ERROR: --role required" >&2
    exit 2
  fi
  local now
  now="$(now_iso)"
  if [[ ! -f "$BUS_FILE" ]]; then
    echo "none"
    exit 0
  fi
  tail -n 200 "$BUS_FILE" \
    | jq -s -r --arg role "$role" --arg now "$now" --argjson limit "$limit" '
        map(select(type=="object"))
      | map(select((.expires_at // "")=="" or .expires_at > $now))
      | map(select((.targets|index("all")) or (.targets|index($role))))
      | sort_by(.ts) | reverse
      | .[0:$limit]
      | map("\(.ts) \(.id) from=\(.from) kind=\(.kind) msg=\(.msg)")
      | .[]
    ' 2>/dev/null || echo "none"
}

tail_cmd() {
  local limit=10
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --limit) limit="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "Unknown arg: $1"; usage; exit 2 ;;
    esac
  done
  if [[ ! -f "$BUS_FILE" ]]; then
    echo "none"
    exit 0
  fi
  tail -n "$limit" "$BUS_FILE"
}

cmd="${1:-}"
shift || true
case "$cmd" in
  post) post_cmd "$@" ;;
  active) active_cmd "$@" ;;
  tail) tail_cmd "$@" ;;
  -h|--help|help|"") usage ;;
  *) echo "Unknown command: $cmd"; usage; exit 2 ;;
esac
{"ts_utc": "2026-04-15T19:44:46Z", "kind": "policy", "source": "planner_guardian", "targets": ["planner"], "ttl_min": 180, "message": "planner_guardian escalation: score=40; issues=projection_not_decision_capable,dependency_policy_not_enforced,missing_architecture_plan_ref,missing_vision_alignment,missing_architecture_audit; ready_idle_streak=0; low_score_streak=1; runway_no_batch_streak=9. Action attendue: claim READY ou creation batch top-level aligne vision+architecture.", "meta": {"score": 40, "issues": ["projection_not_decision_capable", "dependency_policy_not_enforced", "missing_architecture_plan_ref", "missing_vision_alignment", "missing_architecture_audit"], "source_contract": "admin_unblock_refresh"}}
