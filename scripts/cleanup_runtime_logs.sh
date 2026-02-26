#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
RUNS_DIR="${ROOT}/finance-app/orchestrator-runs"
RUNS_ARCHIVE_ROOT="${ROOT}/finance-app/orchestrator-runs-archive"
CRON_RUNS_DIR="/home/venom/.openclaw/cron/runs"
CRON_RUNS_ARCHIVE_ROOT="/home/venom/.openclaw/cron/runs-archive"
ROLE_RECOVERY_LOG="${ROLE_RECOVERY_LOG:-${ROOT}/logs-codex-runs/role-recovery.log}"
LEGACY_ROLE_RECOVERY_LOG="${ROOT}/logs-qwen-runs/role-recovery.log"

KEEP_RUN_DIRS="${KEEP_RUN_DIRS:-15}"
KEEP_CRON_LINES="${KEEP_CRON_LINES:-120}"
ROTATE_ROLE_RECOVERY_MAX_MB="${ROTATE_ROLE_RECOVERY_MAX_MB:-5}"

if ! [[ "$KEEP_RUN_DIRS" =~ ^[0-9]+$ ]] || [[ "$KEEP_RUN_DIRS" -lt 1 ]]; then
  KEEP_RUN_DIRS=15
fi
if ! [[ "$KEEP_CRON_LINES" =~ ^[0-9]+$ ]] || [[ "$KEEP_CRON_LINES" -lt 1 ]]; then
  KEEP_CRON_LINES=120
fi
if ! [[ "$ROTATE_ROLE_RECOVERY_MAX_MB" =~ ^[0-9]+$ ]] || [[ "$ROTATE_ROLE_RECOVERY_MAX_MB" -lt 1 ]]; then
  ROTATE_ROLE_RECOVERY_MAX_MB=5
fi

TS="$(date +%Y%m%d-%H%M%S)"

archive_orchestrator_runs() {
  [[ -d "$RUNS_DIR" ]] || return 0

  local latest_target=""
  if [[ -L "$RUNS_DIR/latest" ]]; then
    latest_target="$(readlink "$RUNS_DIR/latest")"
  fi

  mapfile -t run_dirs < <(find "$RUNS_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -r)
  if [[ ${#run_dirs[@]} -le $KEEP_RUN_DIRS ]]; then
    echo "orchestrator_runs: nothing to archive (count=${#run_dirs[@]}, keep=${KEEP_RUN_DIRS})"
    return 0
  fi

  local archive_dir="${RUNS_ARCHIVE_ROOT}/${TS}"
  mkdir -p "$archive_dir"
  local keep_file="/tmp/keep-runs-${TS}.txt"
  printf '%s\n' "${run_dirs[@]:0:$KEEP_RUN_DIRS}" > "$keep_file"
  if [[ -n "$latest_target" ]]; then
    grep -qxF "$latest_target" "$keep_file" || echo "$latest_target" >> "$keep_file"
  fi

  local moved=0
  while IFS= read -r d; do
    [[ -z "$d" ]] && continue
    if ! grep -qxF "$d" "$keep_file"; then
      mv "$RUNS_DIR/$d" "$archive_dir/"
      moved=$((moved + 1))
    fi
  done < <(printf '%s\n' "${run_dirs[@]}")

  echo "orchestrator_runs: archived_to=$archive_dir moved_count=$moved keep_count=$(wc -l < "$keep_file") latest_target=${latest_target:-none}"
}

trim_cron_runs() {
  [[ -d "$CRON_RUNS_DIR" ]] || return 0
  local archive_dir="${CRON_RUNS_ARCHIVE_ROOT}/${TS}"
  mkdir -p "$archive_dir"
  local trimmed=0

  for f in "$CRON_RUNS_DIR"/*.jsonl; do
    [[ -f "$f" ]] || continue
    local base total old_count
    base="$(basename "$f")"
    total="$(wc -l < "$f")"
    if [[ "$total" -le "$KEEP_CRON_LINES" ]]; then
      continue
    fi
    old_count=$((total - KEEP_CRON_LINES))
    head -n "$old_count" "$f" > "$archive_dir/$base.old"
    tail -n "$KEEP_CRON_LINES" "$f" > "$f.tmp"
    mv "$f.tmp" "$f"
    trimmed=$((trimmed + 1))
    echo "cron_runs: trimmed $base ($total -> $KEEP_CRON_LINES, archived=$old_count)"
  done

  if [[ "$trimmed" -eq 0 ]]; then
    rmdir "$archive_dir" 2>/dev/null || true
    echo "cron_runs: nothing to trim"
  else
    echo "cron_runs: archive_dir=$archive_dir trimmed_files=$trimmed"
  fi
}

rotate_role_recovery_log_one() {
  local log_file="$1"
  [[ -f "$log_file" ]] || return 0
  local size_mb=$(( $(stat -c %s "$log_file") / 1024 / 1024 ))
  if [[ "$size_mb" -lt "$ROTATE_ROLE_RECOVERY_MAX_MB" ]]; then
    echo "role_recovery_log: no rotation (file=$log_file size_mb=${size_mb}, threshold_mb=${ROTATE_ROLE_RECOVERY_MAX_MB})"
    return 0
  fi
  local rotated="${log_file}.${TS}.old"
  mv "$log_file" "$rotated"
  : > "$log_file"
  echo "role_recovery_log: rotated_to=$rotated"
}

rotate_role_recovery_log() {
  rotate_role_recovery_log_one "$ROLE_RECOVERY_LOG"
  if [[ "$LEGACY_ROLE_RECOVERY_LOG" != "$ROLE_RECOVERY_LOG" ]]; then
    rotate_role_recovery_log_one "$LEGACY_ROLE_RECOVERY_LOG"
  fi
}

archive_orchestrator_runs
trim_cron_runs
rotate_role_recovery_log

echo "done"
