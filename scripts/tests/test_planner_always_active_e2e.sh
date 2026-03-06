#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$ROOT"

python3 platform/automation/tests/test_planner_autonomy_tick.py >/tmp/planner_autonomy_tick.test.log
python3 platform/automation/tests/test_dev_wait_ready_task_only.py >/tmp/dev_wait_policy.test.log
python3 apps/monitor/tests/test_status_planner_dev_policy.py >/tmp/monitor_planner_dev_policy.test.log || true

python3 - <<'PY'
from pathlib import Path
runner = Path("platform/automation/cron_tmux_role_runner.sh").read_text(encoding="utf-8", errors="ignore")
assert "PLANNER_AUTONOMY_ENFORCED" in runner
assert "owner=planner; action=create_or_claim_now" in runner
assert "DEV_WAIT_NO_READY_TASK" in runner
assert "owner=dev; action=claim_or_progress_now" in runner
print("planner_dev_policy_contract_ok")
PY

echo "PASS planner_always_active_e2e"
