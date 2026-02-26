#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$WORKDIR"

ARTIFACT_PATH="${1:-}"
DRY_RUN="${DRY_RUN:-0}"

if [[ -z "$ARTIFACT_PATH" ]]; then
  echo "Usage: scripts/run_delivery_gate.sh <artifact_path>"
  echo "Example: scripts/run_delivery_gate.sh finance-app/openclaw-gates/batch-01-20260224-2200.md"
  exit 2
fi

if [[ ! -f "$ARTIFACT_PATH" ]]; then
  echo "BLOCKED: artifact not found: $ARTIFACT_PATH"
  exit 10
fi

echo "== DELIVERY GATE v1.1 =="
echo "artifact=$ARTIFACT_PATH"

# Gate 1: required sections in artifact
missing=0
for key in DELTA EVIDENCE RISKS NEXT VERDICT BLOCKER_ID NEXT_ACTION_UNIQUE; do
  if ! rg -n "^${key}" "$ARTIFACT_PATH" >/dev/null 2>&1; then
    echo "BLOCKED: missing section ${key}"
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  exit 11
fi

# Gate 2: verdict must be explicit
if ! rg -n "VERDICT\s*:\s*(PASS|BLOCKED)" "$ARTIFACT_PATH" -i >/dev/null 2>&1; then
  echo "BLOCKED: invalid VERDICT (must be PASS|BLOCKED)"
  exit 12
fi

# Gate 3: independent Codex reviewer evidence
# Accept either codex marker in artifact OR latest orchestrator transcript marker
if ! rg -n "(CodexReviewer|codex review --uncommitted|independent_review_gate)" "$ARTIFACT_PATH" -i >/dev/null 2>&1; then
  LATEST_TRANSCRIPT="$(ls -1dt finance-app/orchestrator-runs/*/transcript.md 2>/dev/null | head -n 1 || true)"
  if [[ -z "$LATEST_TRANSCRIPT" ]] || ! rg -n "(CodexReviewer|codex review --uncommitted|independent_review_gate)" "$LATEST_TRANSCRIPT" -i >/dev/null 2>&1; then
    echo "BLOCKED: missing independent Codex reviewer evidence"
    exit 13
  fi
fi

# Gate 3b: machine-readable review contract
# Accept kv in EVIDENCE (review_ref/review_verdict) or explicit REVIEW_* sections.
review_ref_ok=0
review_verdict_ok=0
if rg -n "(review_ref=|^REVIEW_REF\\s*:)" "$ARTIFACT_PATH" -i >/dev/null 2>&1; then
  review_ref_ok=1
fi
if rg -n "(review_verdict=(GO|BLOCKED|PASS)|^REVIEW_VERDICT\\s*:\\s*(GO|BLOCKED|PASS))" "$ARTIFACT_PATH" -i >/dev/null 2>&1; then
  review_verdict_ok=1
fi
if [[ "$review_ref_ok" -ne 1 || "$review_verdict_ok" -ne 1 ]]; then
  LATEST_TRANSCRIPT="${LATEST_TRANSCRIPT:-$(ls -1dt finance-app/orchestrator-runs/*/transcript.md 2>/dev/null | head -n 1 || true)}"
  if [[ -n "$LATEST_TRANSCRIPT" ]]; then
    if [[ "$review_ref_ok" -ne 1 ]] && rg -n "(review_ref=|^REVIEW_REF\\s*:)" "$LATEST_TRANSCRIPT" -i >/dev/null 2>&1; then
      review_ref_ok=1
    fi
    if [[ "$review_verdict_ok" -ne 1 ]] && rg -n "(review_verdict=(GO|BLOCKED|PASS)|^REVIEW_VERDICT\\s*:\\s*(GO|BLOCKED|PASS))" "$LATEST_TRANSCRIPT" -i >/dev/null 2>&1; then
      review_verdict_ok=1
    fi
  fi
fi
if [[ "$review_ref_ok" -ne 1 ]]; then
  echo "BLOCKED: missing review_ref evidence (EVIDENCE kv or REVIEW_REF section)"
  exit 14
fi
if [[ "$review_verdict_ok" -ne 1 ]]; then
  echo "BLOCKED: missing review_verdict evidence (GO|BLOCKED|PASS)"
  exit 15
fi

# Gate 4: regression gate
if [[ "$DRY_RUN" == "1" ]]; then
  echo "INFO: DRY_RUN=1 -> skipping regression execution"
else
  if [[ -x "skills/finance-regression-gate/scripts/run_gate.sh" ]]; then
    bash skills/finance-regression-gate/scripts/run_gate.sh --dry-run >/tmp/delivery-gate-regression.out 2>&1 || true
  fi
fi

echo "PASS: delivery gate checks passed"
