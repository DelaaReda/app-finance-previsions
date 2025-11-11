#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
APP_DIR="${ROOT_DIR}"
NGROK_CFG="${APP_DIR}/copilot-app/scripts/ngrok.yml"
FRONT_DIR="${APP_DIR}/copilot-app/frontend/webapp"
ENV_LOCAL="${FRONT_DIR}/.env.local"

echo "[share] Checking ngrok…"
if ! command -v ngrok >/dev/null 2>&1; then
  echo "Error: ngrok is not installed."
  echo "Install: https://ngrok.com/download and run: ngrok config add-authtoken <token>"
  exit 1
fi

if ! ngrok config check >/dev/null 2>&1; then
  echo "Warning: ngrok config not initialized. Run: ngrok config add-authtoken <token>"
fi

echo "[share] Starting Finance Copilot (backend + frontend)…"
"${APP_DIR}/finance-copilot.sh" start >/dev/null 2>&1 || true

echo "[share] Launching single ngrok tunnel for backend:8050 (serves UI too)…"
NGROK_LOG="/tmp/ngrok_share.log"
ngrok http 8050 --log=stdout >"${NGROK_LOG}" 2>&1 &
NGROK_PID=$!
echo "[share] ngrok PID: ${NGROK_PID} (log: ${NGROK_LOG})"

echo "[share] Waiting for ngrok to initialize…"
sleep 3

echo "[share] Fetching public URL from ngrok API…"
API_JSON="$(curl -sS http://127.0.0.1:4040/api/tunnels || true)"
if [[ -z "${API_JSON}" ]]; then
  echo "[share] ngrok API not responding yet. Waiting a bit more…"
  sleep 3
  API_JSON="$(curl -sS http://127.0.0.1:4040/api/tunnels || true)"
fi

if [[ -z "${API_JSON}" ]]; then
  echo "Error: Unable to query ngrok API (http://127.0.0.1:4040). Check ${NGROK_LOG} for details."
  exit 1
fi

PUBLIC_URL=$(python3 - <<'PY'
import json,sys
d=json.load(sys.stdin)
urls=[t.get('public_url','') for t in d.get('tunnels',[]) if t.get('public_url')]
print(urls[0] if urls else '')
PY
<<<"${API_JSON}")

if [[ -z "${PUBLIC_URL}" ]]; then
  echo "Error: Could not detect ngrok public URL. Raw: ${API_JSON}"
  exit 1
fi

echo "[share] Public URL: ${PUBLIC_URL}"

echo "[share] Configuring frontend to call same-origin /api and rebuilding…"
mkdir -p "${FRONT_DIR}"
cp -f "${ENV_LOCAL}" "${ENV_LOCAL}.bak" 2>/dev/null || true

tmpfile="${ENV_LOCAL}.tmp"
awk 'BEGIN{changed=0} 
     /^VITE_API_BASE_URL=/{print "VITE_API_BASE_URL=/api"; changed=1; next}
     {print}
     END{if(!changed) print "VITE_API_BASE_URL=/api"}
     ' "${ENV_LOCAL}" >"${tmpfile}" && mv "${tmpfile}" "${ENV_LOCAL}"

pushd "${FRONT_DIR}" >/dev/null
npm run build >/dev/null 2>&1 || { echo "Error: frontend build failed"; exit 1; }
popd >/dev/null

echo "[share] Restarting app to serve fresh build…"
"${APP_DIR}/finance-copilot.sh" restart >/dev/null 2>&1 || true

cat <<EOF

✅ Public share ready

- URL: ${PUBLIC_URL}

Share this URL with your friends. The backend serves the UI at '/'. The frontend calls '/api' on the same origin.

To stop sharing:
  1) kill ngrok: kill ${NGROK_PID}  # or run copilot-app/scripts/stop_ngrok.sh
  2) ./finance-copilot.sh stop

Note: ngrok free sessions are temporary. For stable links, use Cloudflare Tunnel or Nginx.
EOF
