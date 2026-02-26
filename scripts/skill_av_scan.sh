#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_DIR="${1:-/home/venom/.openclaw/workspace/skills}"
OUT_DIR="${WORKDIR}/security-reports"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$OUT_DIR/skills-av-scan-$STAMP.txt"

{
  echo "skill_av_scan"
  echo "target=$TARGET_DIR"
  echo "timestamp=$STAMP"

  if command -v clamscan >/dev/null 2>&1; then
    echo "engine=clamav"
    clamscan -r --infected --no-summary "$TARGET_DIR" || true
  elif command -v yara >/dev/null 2>&1; then
    echo "engine=yara"
    echo "yara available but no default rules configured; skipping rule run"
  else
    echo "engine=none"
    echo "no av engine installed (clamav/yara missing)"
  fi
} | tee "$OUT"

echo "result_file=$OUT"
