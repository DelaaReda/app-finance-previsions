#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${RUNTIME_GIT_HYGIENE_MANIFEST:-$ROOT/platform/config/runtime_git_hygiene_patterns.txt}"
MODE="${1:-status}"

if ! command -v git >/dev/null 2>&1; then
  echo "git not found" >&2
  exit 1
fi

cd "$ROOT"

if [ ! -f "$MANIFEST" ]; then
  echo "manifest not found: $MANIFEST" >&2
  exit 1
fi

mapfile -t PATTERNS < <(grep -v '^[[:space:]]*#' "$MANIFEST" | sed '/^[[:space:]]*$/d')

resolve_tracked_files() {
  local tmp
  tmp="$(mktemp)"
  : >"$tmp"
  local pattern
  for pattern in "${PATTERNS[@]}"; do
    git ls-files -- "$pattern" >>"$tmp"
  done
  sort -u "$tmp"
  rm -f "$tmp"
}

ensure_info_exclude_block() {
  local exclude_file block_start block_end
  exclude_file="$(git rev-parse --git-path info/exclude)"
  block_start="# BEGIN runtime_git_hygiene"
  block_end="# END runtime_git_hygiene"
  mkdir -p "$(dirname "$exclude_file")"
  touch "$exclude_file"
  if grep -Fq "$block_start" "$exclude_file"; then
    return 0
  fi
  {
    printf '\n%s\n' "$block_start"
    printf '%s\n' "logs-codex-runs/orchestrator-state/legacy/planner-subagents-results/*.raw.txt"
    printf '%s\n' "logs-codex-runs/orchestrator-state/legacy/planner-subagents-results/*.result.json"
    printf '%s\n' "logs-codex-runs/orchestrator-state/legacy/dynamic-workers-results/*.launcher.log"
    printf '%s\n' "logs-codex-runs/orchestrator-state/legacy/dynamic-workers-results/*.result.json"
    printf '%s\n' "$block_end"
  } >>"$exclude_file"
}

apply_skip_worktree() {
  ensure_info_exclude_block
  local files
  files="$(resolve_tracked_files)"
  if [ -z "$files" ]; then
    echo "No tracked runtime-generated files matched."
    return 0
  fi
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    git update-index --skip-worktree -- "$file"
  done <<<"$files"
  echo "Applied skip-worktree to runtime-generated tracked files."
}

clear_skip_worktree() {
  local files
  files="$(resolve_tracked_files)"
  if [ -z "$files" ]; then
    echo "No tracked runtime-generated files matched."
    return 0
  fi
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    git update-index --no-skip-worktree -- "$file"
  done <<<"$files"
  echo "Cleared skip-worktree from runtime-generated tracked files."
}

print_status() {
  local files
  files="$(resolve_tracked_files)"
  if [ -z "$files" ]; then
    echo "No tracked runtime-generated files matched."
    return 0
  fi
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    git ls-files -v -- "$file"
  done <<<"$files"
}

case "$MODE" in
  apply)
    apply_skip_worktree
    ;;
  clear)
    clear_skip_worktree
    ;;
  status)
    print_status
    ;;
  *)
    echo "Usage: $0 [apply|clear|status]" >&2
    exit 2
    ;;
esac
