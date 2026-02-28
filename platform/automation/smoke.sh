#!/usr/bin/env bash
# Basic smoke test for pre-push: ensure backend judge API responds.
set -euo pipefail

# Quick health already checked by hook; here hit judge endpoint to ensure main path works.
curl -fsS "http://localhost:8050/api/judge?limit=1" >/dev/null

echo "smoke: /api/judge responsive"
