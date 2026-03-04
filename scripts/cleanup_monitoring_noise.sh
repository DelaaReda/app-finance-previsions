#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LOG_DIR="${ROOT}/logs-codex-runs"
ARCHIVE_ROOT="${LOG_DIR}/archive"
TS="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_DIR="${ARCHIVE_ROOT}/noise-${TS}"

KEEP_LIVE_LINES="${KEEP_LIVE_LINES:-1500}"
KEEP_TICK_LINES="${KEEP_TICK_LINES:-1200}"
KEEP_CRON_LINES="${KEEP_CRON_LINES:-600}"
KEEP_GENERIC_LINES="${KEEP_GENERIC_LINES:-900}"
KEEP_HEALTH_LINES="${KEEP_HEALTH_LINES:-700}"
MOVE_UI_OLDER_DAYS="${MOVE_UI_OLDER_DAYS:-2}"
MAX_SINGLE_FILE_MB="${MAX_SINGLE_FILE_MB:-25}"

trim_number() {
  printf '%s' "$1" | tr -d '[:space:]'
}

normalize_positive_int() {
  local raw
  raw="$(trim_number "$1")"
  local fallback="$2"
  if ! [[ "$raw" =~ ^[0-9]+$ ]] || [[ "$raw" -lt 1 ]]; then
    printf '%s\n' "$fallback"
    return 0
  fi
  printf '%s\n' "$raw"
}

KEEP_LIVE_LINES="$(normalize_positive_int "$KEEP_LIVE_LINES" 1500)"
KEEP_TICK_LINES="$(normalize_positive_int "$KEEP_TICK_LINES" 1200)"
KEEP_CRON_LINES="$(normalize_positive_int "$KEEP_CRON_LINES" 600)"
KEEP_GENERIC_LINES="$(normalize_positive_int "$KEEP_GENERIC_LINES" 900)"
KEEP_HEALTH_LINES="$(normalize_positive_int "$KEEP_HEALTH_LINES" 700)"
MOVE_UI_OLDER_DAYS="$(normalize_positive_int "$MOVE_UI_OLDER_DAYS" 2)"
MAX_SINGLE_FILE_MB="$(normalize_positive_int "$MAX_SINGLE_FILE_MB" 25)"

mkdir -p "$ARCHIVE_DIR"

file_size_bytes() {
  local f="$1"
  if stat -c %s "$f" >/dev/null 2>&1; then
    stat -c %s "$f"
  else
    stat -f %z "$f"
  fi
}

trim_file_to_lines() {
  local f="$1"
  local keep_lines="$2"
  [[ -f "$f" ]] || return 0

  local total_lines
  total_lines="$(wc -l < "$f" 2>/dev/null || echo 0)"
  total_lines="$(trim_number "$total_lines")"
  [[ -n "$total_lines" ]] || total_lines=0
  if [[ "$total_lines" -le "$keep_lines" ]]; then
    return 0
  fi

  local old_count=$((total_lines - keep_lines))
  local base
  base="$(basename "$f")"

  head -n "$old_count" "$f" > "${ARCHIVE_DIR}/${base}.head-${old_count}.log"
  tail -n "$keep_lines" "$f" > "${f}.tmp"
  mv "${f}.tmp" "$f"
  echo "trimmed file=${f} lines=${total_lines}->${keep_lines} archived_head=${old_count}"
}

rotate_large_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  local max_bytes=$((MAX_SINGLE_FILE_MB * 1024 * 1024))
  local bytes
  bytes="$(file_size_bytes "$f" 2>/dev/null || echo 0)"
  bytes="$(trim_number "$bytes")"
  [[ -n "$bytes" ]] || bytes=0
  if [[ "$bytes" -le "$max_bytes" ]]; then
    return 0
  fi

  local base
  base="$(basename "$f")"
  mv "$f" "${ARCHIVE_DIR}/${base}.full-${bytes}b.log"
  : > "$f"
  echo "rotated file=${f} size_bytes=${bytes} threshold_bytes=${max_bytes}"
}

move_old_ui_noise() {
  local moved=0

  while IFS= read -r -d '' file; do
    mv "$file" "$ARCHIVE_DIR/"
    moved=$((moved + 1))
  done < <(
    find "$LOG_DIR" -maxdepth 1 -type f \
      \( -name 'claude-ui-*' -o -name 'claude-deep-troubleshoot-*' \) \
      -mtime +"$MOVE_UI_OLDER_DAYS" -print0 2>/dev/null || true
  )

  while IFS= read -r -d '' dir; do
    mv "$dir" "$ARCHIVE_DIR/"
    moved=$((moved + 1))
  done < <(
    find "$LOG_DIR" -maxdepth 1 -type d -name 'claude-ui-send-*.snapshots' \
      -mtime +"$MOVE_UI_OLDER_DAYS" -print0 2>/dev/null || true
  )

  echo "ui_noise_moved=${moved} older_than_days=${MOVE_UI_OLDER_DAYS}"
}

compact_role_recovery_permission_noise() {
  local f="$LOG_DIR/role-recovery.log"
  [[ -f "$f" ]] || return 0
  python3 - "$f" <<'PY'
import pathlib, sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
needle = "/home/venom/shared/logs-codex-runs"
marker = "cannot create directory"
max_keep = 4
out = []
burst = 0
for line in lines:
    low = line.lower()
    noisy = (marker in low and needle in low) or ("operation not permitted" in low and needle in low)
    if noisy:
        burst += 1
        if burst <= max_keep:
            out.append(line)
        continue
    if burst > max_keep:
        out.append(f"[noise-trim] suppressed {burst - max_keep} repeated permission-denied lines for {needle}")
    burst = 0
    out.append(line)
if burst > max_keep:
    out.append(f"[noise-trim] suppressed {burst - max_keep} repeated permission-denied lines for {needle}")
path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
PY
  echo "compacted_role_recovery_permission_noise=1"
}

compact_role_recovery_permission_noise

for f in "$LOG_DIR"/role-runner/*.live.log; do
  [[ -f "$f" ]] || continue
  trim_file_to_lines "$f" "$KEEP_LIVE_LINES"
  rotate_large_file "$f"
done

for f in "$LOG_DIR"/fc-ticks/*.tick.log; do
  [[ -f "$f" ]] || continue
  trim_file_to_lines "$f" "$KEEP_TICK_LINES"
  rotate_large_file "$f"
done

for f in "$LOG_DIR"/fc-ticks/*.cron.log; do
  [[ -f "$f" ]] || continue
  trim_file_to_lines "$f" "$KEEP_CRON_LINES"
  rotate_large_file "$f"
done

for f in "$LOG_DIR"/monitor-guard.cron.log; do
  [[ -f "$f" ]] || continue
  trim_file_to_lines "$f" "$KEEP_CRON_LINES"
  rotate_large_file "$f"
done

for f in \
  "$LOG_DIR"/health-snapshot.log \
  "$LOG_DIR"/vm-resume.log \
  "$LOG_DIR"/watchdog_chromium.log \
  "$LOG_DIR"/role-recovery.log \
  "$LOG_DIR"/auto-batch-close.log \
  "$LOG_DIR"/qwen-monitor.log \
  "$LOG_DIR"/monitor-guard.log \
  "$LOG_DIR"/monitor-server.log \
  "$LOG_DIR"/monitor-tunnel.log; do
  [[ -f "$f" ]] || continue
  if [[ "$(basename "$f")" == "health-snapshot.log" ]]; then
    trim_file_to_lines "$f" "$KEEP_HEALTH_LINES"
  else
    trim_file_to_lines "$f" "$KEEP_GENERIC_LINES"
  fi
  rotate_large_file "$f"
done

move_old_ui_noise

if [[ -z "$(find "$ARCHIVE_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
  rmdir "$ARCHIVE_DIR" 2>/dev/null || true
  echo "cleanup_monitoring_noise: no archive content created"
else
  echo "cleanup_monitoring_noise: archive_dir=${ARCHIVE_DIR}"
fi
