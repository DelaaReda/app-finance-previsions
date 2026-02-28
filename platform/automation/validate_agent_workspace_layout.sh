#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT_DIR="$(readlink -f "$SCRIPT_DIR")"
if [[ "$SCRIPT_DIR" == */platform/automation ]]; then
  ROOT="${SCRIPT_DIR%/platform/automation}"
elif [[ "$SCRIPT_DIR" == */platform ]]; then
  ROOT="${SCRIPT_DIR%/platform}"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi
cd "$ROOT"

pass_count=0
warn_count=0
fail_count=0

pass() { echo "PASS: $*"; pass_count=$((pass_count + 1)); }
warn() { echo "WARN: $*"; warn_count=$((warn_count + 1)); }
fail() { echo "FAIL: $*"; fail_count=$((fail_count + 1)); }

required_root_files=(
  "AGENTS.md"
  "SOUL.md"
  "USER.md"
  "MEMORY.md"
  "TOOLS.md"
  "HEARTBEAT.md"
  "README.md"
)

for f in "${required_root_files[@]}"; do
  if [[ -f "$f" ]]; then
    pass "root file present: $f"
  else
    fail "missing root file: $f"
  fi
done

required_dirs=(
  "memory"
  "memory/agents"
  "memory/chat-journal"
  "memory/imported-from-openclaw-workspace"
  "docs/operations"
  "docs/ops"
  "docs/planning"
  "docs/orchestrator-ops"
  "apps/api/src"
  "apps/web/src"
)

for d in "${required_dirs[@]}"; do
  if [[ -d "$d" ]]; then
    pass "directory present: $d"
  else
    fail "missing directory: $d"
  fi
done

today_utc="$(date -u +%F)"
yesterday_utc="$(date -u -d 'yesterday' +%F)"

if [[ -f "memory/${today_utc}.md" ]]; then
  pass "today memory exists: memory/${today_utc}.md"
else
  warn "today memory missing: memory/${today_utc}.md"
fi

if [[ -f "memory/${yesterday_utc}.md" ]]; then
  pass "yesterday memory exists: memory/${yesterday_utc}.md"
else
  warn "yesterday memory missing: memory/${yesterday_utc}.md"
fi

mkdir -p memory
ln -sfn "${today_utc}.md" memory/today.md
ln -sfn "${yesterday_utc}.md" memory/yesterday.md
pass "memory symlinks updated: memory/today.md, memory/yesterday.md"

non_standard=()
while IFS= read -r fname; do
  base="$(basename "$fname")"
  if [[ "$base" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$ ]]; then
    continue
  fi
  if [[ "$base" == "today.md" || "$base" == "yesterday.md" ]]; then
    continue
  fi
  non_standard+=("$base")
done < <(find memory -maxdepth 1 -type f | sort)

if [[ ${#non_standard[@]} -eq 0 ]]; then
  pass "memory root only contains canonical files"
else
  warn "non-standard files in memory root: ${non_standard[*]}"
fi

echo "SUMMARY: pass=$pass_count warn=$warn_count fail=$fail_count"
if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi

exit 0
