#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd -P)"
cd "$ROOT"
GATES_DIR_CANONICAL="${ROOT}/evidence/gates/openclaw-gates"
GATES_DIR="${GATES_DIR_CANONICAL}"
if [[ ! -d "$GATES_DIR" ]]; then
  echo "BLOCKER: gates directory missing: $GATES_DIR"
  exit 11
fi

echo "== PREFLIGHT DISPATCH =="

# 1) state machine validation
python3 scripts/validate_batch_state.py --file docs/orchestrator-ops/priority-queue.json

# 2) health check (soft)
if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 3 http://localhost:8050/api/health >/dev/null 2>&1; then
    echo "health=UP"
  else
    echo "health=DOWN (soft warning)"
  fi
fi

# 3) gate artifact requirement for Batch-02
if rg -n '"id"\s*:\s*"BATCH-02"[\s\S]*"state"\s*:\s*"(IN_SPRINT|RUNNING|QA_REVIEW|PASS|CLOSED)"' docs/orchestrator-ops/priority-queue.json -U >/dev/null 2>&1; then
  latest_batch01="$(ls -1t "$GATES_DIR"/batch-01-*.md 2>/dev/null | head -n 1 || true)"
  if [[ -z "$latest_batch01" ]]; then
    echo "BLOCKED: Batch-02 cannot start without batch-01 PASS artifact"
    exit 20
  fi
  if ! rg -n 'VERDICT\s*:\s*PASS' "$latest_batch01" -i >/dev/null 2>&1; then
    echo "BLOCKED: Batch-01 artifact exists but not PASS"
    exit 21
  fi
fi

echo "VERDICT: PASS"
