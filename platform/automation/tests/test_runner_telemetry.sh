#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd -P)"
MOD="${ROOT}/platform/automation/runner/telemetry.sh"

# shellcheck source=/dev/null
source "$MOD"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
out="$tmpdir/events.jsonl"

runner_emit_telemetry_jsonl "$out" "dispatch_start" "dev" "tick=t123" "source=runner"

if [[ ! -s "$out" ]]; then
  echo "assert_fail:telemetry_empty" >&2
  exit 1
fi

python3 - "$out" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
assert row["event"] == "dispatch_start", row
assert row["role"] == "dev", row
assert row["tick"] == "t123", row
assert row["source"] == "runner", row
print("runner_telemetry:PASS")
PY
