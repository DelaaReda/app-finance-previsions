#!/usr/bin/env bash
set -euo pipefail
# Simple smoke test: check backend health
API_URL="${API_URL:-http://localhost:8050}"
RES=$(curl -s -m 10 "$API_URL/api/health" || true)
if ! echo "$RES" | grep -q '"ok":true'; then
  echo "Smoke: backend health failed: $RES" >&2
  exit 1
fi
echo "Smoke: backend health OK"
exit 0
