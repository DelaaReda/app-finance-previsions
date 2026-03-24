#!/usr/bin/env bash
# Basic smoke test for pre-push: ensure backend judge API responds.
set -euo pipefail

JUDGE_URL="${FC_SMOKE_JUDGE_URL:-http://127.0.0.1:8050/api/judge?limit=1}"
CONNECT_TIMEOUT="${FC_SMOKE_CONNECT_TIMEOUT:-1}"
MAX_TIME="${FC_SMOKE_MAX_TIME:-3}"

# Quick health already checked by hook; here hit judge endpoint to ensure main path works.
curl -fsS --connect-timeout "$CONNECT_TIMEOUT" --max-time "$MAX_TIME" "$JUDGE_URL" >/dev/null

echo "smoke: ${JUDGE_URL} responsive"
