#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
BUS_SCRIPT="${ROOT}/platform/automation/agent_message_bus.sh"
MSG_TO_DEV="${ROOT}/scripts/message_to_dev.sh"
MSG_CLOSE="${ROOT}/scripts/message_close.sh"
PO_RUN_NOW="${ROOT}/scripts/po_scrum_master_run_now.sh"
FC_AGENT_TICK="${ROOT}/scripts/fc_agent_tick.sh"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

export AGENT_MESSAGE_BUS_FILE="${tmp_dir}/AGENT_MESSAGE_BUS.jsonl"
export AGENT_MESSAGE_BUS_ENABLED=1

echo "[e2e] scenario-1 post -> visible once -> delivered"
msg_id="MSG_20260304T120000Z_01ARZ3NDEKTSV4RRFFQ69G5FAV"
bash "${MSG_TO_DEV}" "check endpoint health" --priority high --ttl-min 60 --id "${msg_id}" >/dev/null

active_json="$(bash "${BUS_SCRIPT}" active --role dev --json)"
python3 - "$active_json" "${msg_id}" <<'PY'
import json
import sys
rows = json.loads(sys.argv[1] or "[]")
mid = sys.argv[2]
assert any(str(r.get("message_id")) == mid for r in rows), "message not visible for dev"
PY

bash "${BUS_SCRIPT}" deliver --id "${msg_id}" --role dev --tick TICK-E2E >/dev/null
active_after="$(bash "${BUS_SCRIPT}" active --role dev --json)"
python3 - "$active_after" "${msg_id}" <<'PY'
import json
import sys
rows = json.loads(sys.argv[1] or "[]")
mid = sys.argv[2]
assert not any(str(r.get("message_id")) == mid for r in rows), "message should be hidden after delivery for role dev"
PY

echo "[e2e] scenario-2 close removes active immediately"
bash "${MSG_CLOSE}" "${msg_id}" --reason resolved >/dev/null
active_closed="$(bash "${BUS_SCRIPT}" active --role dev --json)"
python3 - "$active_closed" "${msg_id}" <<'PY'
import json
import sys
rows = json.loads(sys.argv[1] or "[]")
mid = sys.argv[2]
assert not any(str(r.get("message_id")) == mid for r in rows), "closed message still active"
PY

echo "[e2e] scenario-3 po_scrum_master run-now contract smoke (manual advisory lane)"
grep -q "TMUX_ROLE_ENABLE_PO_SCRUM_MASTER=1" "${PO_RUN_NOW}"
grep -q "PO_SCRUM_MASTER_REPORTS.md" "${PO_RUN_NOW}"

echo "[e2e] scenario-4 core lanes unchanged (scrum_master remains non-cron lane)"
grep -q "analyst|architect|po|scrum_master" "${FC_AGENT_TICK}"
grep -q "ROLE=\"planner\"" "${FC_AGENT_TICK}"

echo "PASS test_message_bus_e2e"
