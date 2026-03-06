#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
RUNNER="${ROOT}/platform/automation/cron_tmux_role_runner.sh"
MONITOR="${ROOT}/apps/monitor/server.py"

# Contract/source autoheal markers must exist in runner.
grep -q "FC_ADMIN_RUNTIME_STALE_AUTOHEAL" "${RUNNER}"
grep -q "admin_runtime_stale_autohealed" "${RUNNER}"
grep -q "runtime_probe_8050_7779_ok" "${RUNNER}"

# Monitor should not expose stale runtime blocker when probes are healthy.
python3 - <<PY
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from unittest import mock

root = Path(tempfile.mkdtemp(prefix="fc-admin-autoheal-"))
state = root / "state"
state.mkdir(parents=True, exist_ok=True)
orch = root / "docs" / "operations" / "orchestrator"
orch.mkdir(parents=True, exist_ok=True)
(orch / "priority-queue.json").write_text(json.dumps({"items": [{"id": "BATCH-01", "state": "READY"}]}), encoding="utf-8")
(orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
(orch / "agent-iteration-issues.jsonl").write_text("", encoding="utf-8")
(root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
(root / "docs" / "ops" / "AGENT_MESSAGE_BUS.jsonl").write_text("", encoding="utf-8")
(root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
(root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)

os.environ["FC_MONITOR_ROOT"] = str(root)
os.environ["FC_MONITOR_STATE_DIR"] = str(state)
spec = importlib.util.spec_from_file_location("fc_monitor_autoheal_e2e", Path("/home/venom/analyse-financiere/apps/monitor/server.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

contracts = {
    "planner": {"STATUS": "IN_PROGRESS", "VERDICT": "GO_WITH_CAUTION", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=claim"},
    "dev": {"STATUS": "WAIT", "VERDICT": "PASS", "DELTA": "DEV_WAIT_NO_READY_TASK", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=none_no_ready"},
    "admin": {
        "STATUS": "BLOCKED",
        "VERDICT": "BLOCKED",
        "DELTA": "RUNTIME_DOWN_BLOCKS_READY_QUEUE",
        "BLOCKER_ID": "RUNTIME_DOWN",
        "EVIDENCE": "task_update=blocked",
    },
}
doctor = {
    "status": "ok",
    "checks": {
        "providers": {
            "status": "ok",
            "detail": {"api_health_ok": True, "monitor_status_ok": True},
        }
    },
}

with mock.patch.object(module, "active_roles", lambda: ("planner", "dev", "admin")), \
     mock.patch.object(module, "contract", lambda role: contracts.get(role, {})), \
     mock.patch.object(module, "tick_age", lambda role: 1), \
     mock.patch.object(module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}), \
     mock.patch.object(module, "rate_limits", lambda: []), \
     mock.patch.object(module, "doctor_snapshot", lambda force_refresh=False: doctor), \
     mock.patch.object(module, "_probe_http_ok", lambda url: True):
    payload = module.status()

admin = payload.get("agents", {}).get("admin", {})
assert admin.get("status") == "PASS", admin
assert admin.get("verdict") == "PASS", admin
assert admin.get("blocker") == "NONE", admin
assert str(admin.get("delta", "")).upper() == "RUNTIME_VERIFIED_OK", admin
PY

echo "PASS test_admin_runtime_stale_autoheal_e2e"
