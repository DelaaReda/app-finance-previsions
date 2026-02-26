#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

OPENCLAW_BIN="${CRON_CLEANUP_OPENCLAW_BIN:-}"
NAME_REGEX="${CRON_CLEANUP_NAME_REGEX:-.*}"
APPLY=0

usage() {
  cat <<'EOF'
Usage: cron_cleanup_duplicates.sh [--apply] [--dry-run] [--regex <jq_regex>] [--openclaw-bin <path>]

Detect duplicate cron jobs by name and remove disabled duplicates.

Policy:
  - Keep one canonical job per name:
      1) prefer enabled job(s),
      2) then most recently updated.
  - Remove only disabled duplicates by default.

Output:
  DUP_GROUP ...
  DUP_ITEM ...
  CLEANUP_ITEM ...
  CLEANUP_SUMMARY groups=<n> duplicate_names=<n> candidates=<n> removed=<n> failed=<n> apply=<0|1>
EOF
}

resolve_openclaw_bin() {
  local candidate=""
  if [[ -n "$OPENCLAW_BIN" && -x "$OPENCLAW_BIN" ]]; then
    printf '%s\n' "$OPENCLAW_BIN"
    return 0
  fi
  for candidate in \
    "/home/venom/.npm-global/bin/openclaw" \
    "${HOME}/.npm-global/bin/openclaw" \
    "$(command -v openclaw 2>/dev/null || true)" \
    "/usr/local/bin/openclaw" \
    "/usr/bin/openclaw" \
    "/bin/openclaw"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --dry-run)
      APPLY=0
      shift
      ;;
    --regex)
      NAME_REGEX="${2:-}"
      shift 2
      ;;
    --openclaw-bin)
      OPENCLAW_BIN="${2:-}"
      shift 2
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

if ! command -v jq >/dev/null 2>&1; then
  echo "CLEANUP_SUMMARY groups=0 duplicate_names=0 candidates=0 removed=0 failed=0 apply=${APPLY} error=jq_missing"
  exit 5
fi

if ! OPENCLAW_BIN="$(resolve_openclaw_bin)"; then
  echo "CLEANUP_SUMMARY groups=0 duplicate_names=0 candidates=0 removed=0 failed=0 apply=${APPLY} error=openclaw_missing"
  exit 5
fi

jobs_json="$("$OPENCLAW_BIN" cron list --all --json 2>/dev/null || echo '{"jobs":[]}')"

groups=0
duplicate_names=0
candidates=0
removed=0
failed=0

while IFS=$'\t' read -r name total enabled_count keep_id; do
  [[ -z "$name" ]] && continue
  groups=$((groups + 1))
  if [[ "$total" -lt 2 ]]; then
    continue
  fi
  duplicate_names=$((duplicate_names + 1))

  echo "DUP_GROUP name=${name} total=${total} enabled=${enabled_count} keep_id=${keep_id}"

  while IFS=$'\t' read -r id enabled updated created agent status; do
    [[ -z "$id" ]] && continue
    echo "DUP_ITEM name=${name} id=${id} enabled=${enabled} updated_at_ms=${updated} created_at_ms=${created} agent=${agent} status=${status}"

    if [[ "$id" == "$keep_id" ]]; then
      continue
    fi
    if [[ "$enabled" == "true" ]]; then
      continue
    fi

    candidates=$((candidates + 1))
    if [[ "$APPLY" -eq 1 ]]; then
      if "$OPENCLAW_BIN" cron rm "$id" >/dev/null 2>&1; then
        removed=$((removed + 1))
        echo "CLEANUP_ITEM name=${name} id=${id} action=removed"
      else
        failed=$((failed + 1))
        echo "CLEANUP_ITEM name=${name} id=${id} action=remove_failed"
      fi
    else
      echo "CLEANUP_ITEM name=${name} id=${id} action=would_remove"
    fi
  done < <(
    printf '%s' "$jobs_json" | jq -r --arg name "$name" '
      .jobs[]?
      | select((.name // "") == $name)
      | [
          .id,
          (.enabled // false),
          (.updatedAtMs // 0),
          (.createdAtMs // 0),
          (.agentId // "none"),
          (.state.lastStatus // "none")
        ] | @tsv
    '
  )
done < <(
  printf '%s' "$jobs_json" | jq -r --arg re "$NAME_REGEX" '
    [
      .jobs[]?
      | select((.name // "") | test($re))
      | {
          name: (.name // ""),
          id: .id,
          enabled: (.enabled // false),
          updated: (.updatedAtMs // 0),
          created: (.createdAtMs // 0)
        }
    ]
    | group_by(.name)
    | .[]
    | sort_by((if .enabled then 1 else 0 end), .updated, .created)
    | reverse
    | [
        (.[0].name // ""),
        (length),
        ([.[] | select(.enabled == true)] | length),
        (.[0].id // "")
      ]
    | @tsv
  '
)

echo "CLEANUP_SUMMARY groups=${groups} duplicate_names=${duplicate_names} candidates=${candidates} removed=${removed} failed=${failed} apply=${APPLY}"

if [[ "$APPLY" -eq 1 && "$failed" -gt 0 ]]; then
  exit 9
fi
exit 0
