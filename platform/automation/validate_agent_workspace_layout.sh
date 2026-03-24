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

date_utc_with_offset_days() {
  local offset_days="${1:-0}"
  if [[ "$offset_days" == "0" ]]; then
    date -u +%F
    return
  fi
  if date -u -d "${offset_days} day" +%F >/dev/null 2>&1; then
    date -u -d "${offset_days} day" +%F
    return
  fi
  if [[ "$offset_days" == -* ]]; then
    date -u -v"${offset_days}"d +%F
  else
    date -u -v+"${offset_days}"d +%F
  fi
}

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
  "docs/operations/orchestrator"
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

if [[ -d "apps/api/src/runtime" ]]; then
  fail "runtime ghost directory detected: apps/api/src/runtime (canonical path is apps/api/runtime)"
else
  pass "no runtime ghost directory under apps/api/src"
fi

if [[ -f "apps/api/src/runtime/data/rag/news.jsonl" ]]; then
  fail "ghost RAG file detected: apps/api/src/runtime/data/rag/news.jsonl"
else
  pass "no ghost RAG file under apps/api/src/runtime/data/rag"
fi

canonical_rag="apps/api/runtime/data/rag/news.jsonl"
if [[ -f "$canonical_rag" ]]; then
  if rg -q "http://test.com|http://fed.com" "$canonical_rag"; then
    fail "fake RAG markers detected in canonical runtime file: $canonical_rag"
  else
    pass "canonical RAG file has no known fake markers"
  fi
else
  pass "canonical RAG file absent (acceptable)"
fi

src_bak_count="$(find apps/api/src -type f \( -name '*.bak' -o -name '*.bak-*' -o -name '*.bak*' \) 2>/dev/null | wc -l | tr -d ' ')"
scripts_bak_count="$(find scripts -type f \( -name '*.bak' -o -name '*.bak-*' -o -name '*.bak*' \) 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$src_bak_count" -eq 0 && "$scripts_bak_count" -eq 0 ]]; then
  pass "no backup artifacts (*.bak*) in src/scripts"
else
  warn "backup artifacts found (*.bak*): src=${src_bak_count}, scripts=${scripts_bak_count}"
fi

for clutter in \
  "apps/api/src/api.log" \
  "apps/api/src/juge-appel.json" \
  "apps/api/src/juge-appel2.json" \
  "apps/api/src/tested_g4f_models.json" \
  "apps/api/src/tested_g4f_models_ok.json" \
  "apps/api/src/tested_g4f_models_categorized.json"
do
  if [[ -f "$clutter" ]]; then
    warn "src root clutter file present: $clutter"
  fi
done

for bridge in \
  "apps/api/src/services/g4f_client.py" \
  "apps/api/src/services/copilot_service.py" \
  "apps/api/src/research/llm_client.py"
do
  if [[ -f "$bridge" ]]; then
    warn "bridge module still present (sys.path debt candidate): $bridge"
  fi
done

legacy_stub_dirs=(
  "apps/api/src/backend"
  "apps/api/src/core"
  "apps/api/src/agents"
  "apps/api/src/analytics"
  "apps/api/src/ingestion"
  "apps/api/src/jobs"
  "apps/api/src/models"
  "apps/api/src/runners"
  "apps/api/src/storage"
  "apps/api/src/taxonomy"
  "apps/api/src/schemas"
)
stub_present=0
for d in "${legacy_stub_dirs[@]}"; do
  if [[ -d "$d" ]]; then
    stub_present=$((stub_present + 1))
  fi
done
if [[ "$stub_present" -gt 0 ]]; then
  warn "legacy alias stub dirs present: $stub_present (track for migration cleanup)"
else
  pass "no legacy alias stub directories"
fi

today_utc="$(date_utc_with_offset_days 0)"
yesterday_utc="$(date_utc_with_offset_days -1)"

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
