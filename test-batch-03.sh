#!/usr/bin/env bash
set -euo pipefail

echo "=================================="
echo "🧪 TEST BATCH-03 END-TO-END (LOCAL)"
echo "=================================="
echo ""

API_BASE="http://localhost:8050"
BOARD_FILE="docs/orchestrator-ops/parallel-workstreams.json"
QUEUE_FILE="docs/orchestrator-ops/priority-queue.json"

fail() {
  echo "❌ $1"
  exit 1
}

ok() {
  echo "✅ $1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 n'est pas installé (ou pas dans le PATH)."
}

require_cmd jq
require_cmd curl

echo "1) Vérification des endpoints API..."
endpoints=(
  "/api/news/feed?limit=50"
  "/api/forecasts?limit=20"
  "/api/dashboard/kpis"
  "/api/stocks/top?limit=10"
  "/api/health"
)
for ep in "${endpoints[@]}"; do
  code=$(curl -sS -o /tmp/batch03_ep.json -w "%{http_code}" "${API_BASE}${ep}" || echo "000")
  if [[ "$code" != "200" ]]; then
    fail "Endpoint ${API_BASE}${ep} répond ${code} (attendu 200)"
  fi
done
ok "Endpoints API répondent en 200"

echo ""
echo "2) Vérifier la source de vérité: docs/orchestrator-ops/"
if [[ ! -f "$QUEUE_FILE" ]]; then
  fail "Fichier queue manquant: $QUEUE_FILE"
fi
if [[ ! -f "$BOARD_FILE" ]]; then
  fail "Fichier workboard manquant: $BOARD_FILE"
fi
ok "Sources queue/workboard présentes"

echo ""
echo "3) Vérifier BATCH-03 dans priority-queue.json..."
if ! jq -e '.items[] | select(.id=="BATCH-03")' "$QUEUE_FILE" >/dev/null; then
  fail "BATCH-03 absent de $QUEUE_FILE"
fi
queue_state=$(jq -r '.items[] | select(.id=="BATCH-03").state' "$QUEUE_FILE")
if [[ "$queue_state" != "READY" ]]; then
  fail "BATCH-03 a l'état '$queue_state' (attendu: READY)"
fi
ok "BATCH-03 est READY dans la priority queue"

echo ""
echo "4) Vérifier BATCH-03 dans parallel-workstreams.json..."
if ! jq -e '.streams[] | select(.id=="BATCH-03")' "$BOARD_FILE" >/dev/null; then
  fail "BATCH-03 absent de $BOARD_FILE"
fi
stream_state=$(jq -r '.streams[] | select(.id=="BATCH-03").state' "$BOARD_FILE")
if [[ "$stream_state" != "IN_PROGRESS" ]]; then
  fail "BATCH-03 stream a l'état '$stream_state' (attendu: IN_PROGRESS)"
fi
ok "BATCH-03 stream est IN_PROGRESS"

echo ""
echo "5) Vérifier les tâches BATCH-03 assignées et non bloquées..."
for t in BATCH-03-FRONTEND BATCH-03-BACKEND BATCH-03-DATA; do
  if ! jq -e --arg id "$t" '.tasks[] | select(.id==$id)' "$BOARD_FILE" >/dev/null; then
    fail "Tâche $t absente de $BOARD_FILE"
  fi
  task_state=$(jq -r --arg id "$t" '.tasks[] | select(.id==$id).state' "$BOARD_FILE")
  if [[ "$task_state" == "WAITING_DEP" || "$task_state" == "BLOCKED" ]]; then
    fail "Tâche $t est bloquée: $task_state"
  fi
done

plan_state=$(jq -r '.tasks[] | select(.id=="BATCH-03-PLAN").state' "$BOARD_FILE")
if [[ "$plan_state" != "IN_PROGRESS" && "$plan_state" != "READY" ]]; then
  fail "Tâche BATCH-03-PLAN est '$plan_state' (attendu READY ou IN_PROGRESS)"
fi
ok "Tâches BATCH-03 prêtes"

echo ""
echo "6) Vérifier apiConnector.js"
if grep -q 'apiConnector.js' apps/web/src/domains/forecasts/pages/index.html; then
  ok "apiConnector.js est importé dans index.html"
else
  fail "apiConnector.js n'est pas importé dans index.html"
fi
if node -v >/dev/null 2>&1; then
  if node -c apps/web/src/domains/forecasts/contracts/apiConnector.js; then
    ok "apiConnector.js est valide"
  else
    fail "Erreur de syntaxe JS dans apiConnector.js"
  fi
else
  echo "⚠️ node indisponible: vérification syntaxique ignorée"
fi

echo ""
echo "7) Vérifier PRODUCT_VISION.md..."
if [[ -f "docs/product/planning/PRODUCT_VISION.md" ]]; then
  lines=$(wc -l < docs/product/planning/PRODUCT_VISION.md)
  if [[ "$lines" -lt 80 ]]; then
    fail "PRODUCT_VISION.md trop court ($lines lignes), probablement incomplet"
  fi
  ok "PRODUCT_VISION.md existe ($lines lignes)"
else
  fail "PRODUCT_VISION.md introuvable"
fi

echo ""
echo "8) Vérifier que les rôles connaissent BATCH-03..."
for agent in frontend_engineer backend_engineer data_analyst planner; do
  if grep -q 'BATCH-03' "memory/agents/$agent.md" 2>/dev/null; then
    ok "$agent mentions BATCH-03"
  else
    fail "memory/agents/$agent.md ne mentionne pas BATCH-03"
  fi
done

echo ""
echo "=================================="
echo "✅ TESTS OK - BATCH-03 prêt à être livrable"
echo "=================================="
