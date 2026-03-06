#!/usr/bin/env bash
# Rebuild queue from PRODUCT_VISION in strict-order mode.
# Default: dry-run. Use --apply to persist changes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

CMD=(
  python3 platform/automation/rebuild_priority_queue_from_product_vision.py
  --vision docs/product/planning/PRODUCT_VISION.md
  --queue docs/operations/orchestrator/priority-queue.json
  --workboard docs/operations/orchestrator/parallel-workstreams.json
)

if [[ "$APPLY" == "1" ]]; then
  CMD+=(--apply)
fi

"${CMD[@]}"
