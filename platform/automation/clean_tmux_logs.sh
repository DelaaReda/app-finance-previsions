#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  clean_tmux_logs.sh [--mode compact|full] [--purge-raw] <log_file_or_dir>

Behavior:
  - If target is a .log file: writes <file>.clean.log
  - If target is a directory: processes every */tmux/*.log (excluding *.clean.log)

Modes:
  compact (default): keeps only debug-relevant lines (STATUS/DELTA/errors/recovery)
  full: keeps most readable lines, only strips terminal noise + obvious UI clutter

Flags:
  --purge-raw: remove source *.log after writing corresponding *.clean.log
EOF
}

MODE="compact"
PURGE_RAW=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --purge-raw)
      PURGE_RAW=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

if [[ "$MODE" != "compact" && "$MODE" != "full" ]]; then
  echo "Invalid mode: $MODE (expected compact|full)" >&2
  exit 3
fi

TARGET="$1"
PROCESSED=0

clean_one() {
  local in_file="$1"
  local out_file="${in_file%.log}.clean.log"
  local tmp_file
  tmp_file="$(mktemp)"

  # 1) Remove ANSI/control noise and normalize line breaks.
  perl -pe '
    s/\e\][^\a]*(?:\a|\e\\)//g;      # OSC sequences
    s/\e\[[0-?]*[ -\/]*[@-~]//g;     # CSI
    s/\e[@-Z\\-_]//g;                # Other ESC sequences
    s/\r/\n/g;
  ' "$in_file" |
    sed -E 's/[[:cntrl:]]//g' |
    sed -E 's/[[:space:]]+$//' |
    sed -E 's/[[:space:]]+/ /g' > "$tmp_file"

  # 2) Split packed key-value replies into separate lines.
  sed -E -i \
    's/(STATUS:|DELTA:|EVIDENCE:|RISKS:|NEXT:|VERDICT:|BLOCKER_ID:|NEXT_ACTION_UNIQUE:)/\
\1/g' "$tmp_file"

  if [[ "$MODE" == "compact" ]]; then
    awk '
      function is_key_line(s) {
        if (s ~ /^(STATUS|DELTA|EVIDENCE|RISKS|NEXT|VERDICT|BLOCKER_ID|NEXT_ACTION_UNIQUE):[[:space:]]*[^ ,]/) return 1
        return 0
      }
      function is_prompt_scaffold(s, l) {
        l = tolower(s)
        if (l ~ /^\[system\]/) return 1
        if (l ~ /^role=/) return 1
        if (index(l, "role=") > 0) return 1
        if (l ~ /^read /) return 1
        if (index(l, "readdocs/") > 0) return 1
        if (l ~ /^do not modify files/) return 1
        if (index(l, "donotmodifyfiles") > 0) return 1
        if (l ~ /^return at most/) return 1
        if (index(l, "returnatmost") > 0) return 1
        if (l ~ /^if nothing changed/) return 1
        if (index(l, "ifnothingchanged") > 0) return 1
        if (l ~ /^ignore l/) return 1
        if (index(l, "[system]ignore") > 0) return 1
        if (l ~ /^regles:/) return 1
        if (l ~ /^r.gles:/) return 1
        if (l ~ /ne recopie pas le prompt/) return 1
        if (l ~ /donne des etapes concretes/) return 1
        if (l ~ /si bloque/) return 1
        if (l ~ /exactement 8 lignes/) return 1
        if (index(l, "exactement8lignes") > 0) return 1
        if (l ~ /format strict/) return 1
        if (l ~ /najoute rien d autre/) return 1
        if (index(l, "najouteriendautre") > 0) return 1
        return 0
      }
      function has_debug_signal(s, l) {
        l = tolower(s)
        return (l ~ /(traceback|error|exception|timed out|fallback_mode|tmux_unparseable|rc_primary|rc_retry|retry_mode|startup_rc|startup_err|auto_recovery|required_missing|health=\[verdict)/)
      }
      {
        line=$0
        if (line == "") next
        if (line ~ /^[-=]{3,}$/) next
        if (line ~ /^[[:punct:][:space:]]+$/) next
        if (line ~ /OpenAI Codex/) next
        if (line ~ /100% context left/) next
        if (line ~ /\/model to change/) next
        if (line ~ /Tip:/) next
        if (tolower(line) == "clear") next
        if (line ~ /(STATUS:.*DELTA:|DELTA:.*EVIDENCE:|EVIDENCE:.*RISKS:|RISKS:.*NEXT:|VERDICT:.*BLOCKER_ID:|BLOCKER_ID:.*NEXT_ACTION_UNIQUE:)/) next
        if (is_prompt_scaffold(line)) next
        if (!(is_key_line(line) || has_debug_signal(line))) next
        if (line == prev) next
        print line
        prev=line
      }
    ' "$tmp_file" > "$out_file"
  else
    awk '
      {
        line=$0
        if (line == "") next
        if (line ~ /^[-=]{3,}$/) next
        if (line ~ /^[[:punct:][:space:]]+$/) next
        if (line ~ /OpenAI Codex/) next
        if (line ~ /100% context left/) next
        if (line ~ /\/model to change/) next
        if (line ~ /Tip:/) next
        if (tolower(line) == "clear") next
        if (line == prev) next
        print line
        prev=line
      }
    ' "$tmp_file" > "$out_file"
  fi

  if [[ ! -s "$out_file" ]]; then
    printf '%s\n' "NO_DEBUG_SIGNAL: only TUI/banner/prompt noise detected; inspect raw log if needed." > "$out_file"
  fi

  if [[ "$PURGE_RAW" -eq 1 ]]; then
    rm -f "$in_file"
  fi

  rm -f "$tmp_file"
  PROCESSED=$((PROCESSED + 1))
  echo "cleaned: $out_file"
}

if [[ -f "$TARGET" ]]; then
  clean_one "$TARGET"
elif [[ -d "$TARGET" ]]; then
  while IFS= read -r file; do
    clean_one "$file"
  done < <(find "$TARGET" -type f -path "*/tmux/*.log" ! -name "*.clean.log" | sort)
else
  echo "Target not found: $TARGET" >&2
  exit 4
fi

echo "processed=$PROCESSED mode=$MODE purge_raw=$PURGE_RAW"
