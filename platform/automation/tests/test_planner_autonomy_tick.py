#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "automation" / "planner_autonomy_tick.sh"
STATE_ROOT = Path("logs-codex-runs") / "orchestrator-state"


def _write_exec_safe(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
workdir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      workdir="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      shift
      ;;
  esac
done
cmd="$*"
[[ -n "$workdir" ]] || workdir="$PWD"
cd "$workdir"
bash -lc "$cmd"
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_planner_runtime_actions_stub(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path.cwd()
queue_path = ROOT / "logs-codex-runs" / "orchestrator-state" / "priority-queue.json"
board_path = ROOT / "logs-codex-runs" / "orchestrator-state" / "parallel-workstreams.json"
force_claim_fail = ROOT / "force_claim_fail"
force_bridge_dispatch = ROOT / "force_bridge_dispatch"


def load(path: Path, fallback: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except Exception:
        return fallback


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\\n", encoding="utf-8")


args = sys.argv[1:]
sub = ""
i = 0
options_with_value = {
    "--root",
    "--board",
    "--queue",
    "--role",
    "--source",
    "--backend",
    "--contract-file",
    "--reason",
    "--cooldown-s",
    "--task",
    "--artifact",
    "--note",
    "--notes",
    "--summary",
    "--handoff-to",
    "--exec-cmd",
    "--tests-run",
    "--review-ref",
    "--reviewer-role",
    "--review-verdict",
    "--change-plan",
    "--architecture-checks",
    "--idempotency-key",
    "--proof-root",
}
while i < len(args):
    token = args[i]
    if token in options_with_value:
        i += 2
        continue
    if token.startswith("--"):
        i += 1
        continue
    sub = token
    break

if not sub and force_bridge_dispatch.exists():
    print(json.dumps({"ok": True, "actions": ["dev_dispatch:BATCH-10-DEV-01"], "dispatch": {"dispatched": True, "task_id": "BATCH-10-DEV-01", "reason": "ready_dev_dispatched"}}))
    raise SystemExit(0)
if not sub:
    print(json.dumps({"ok": True, "actions": [], "dispatch": {"dispatched": False, "reason": "not_needed"}}))
    raise SystemExit(0)

queue = load(queue_path, {"items": []})
board = load(board_path, {"tasks": []})
queue.setdefault("items", [])
board.setdefault("tasks", [])

if sub == "sanitize-dependencies":
    print("SANITIZE_OK")
    raise SystemExit(0)

if sub == "sync-priority":
    print("SYNC_OK")
    raise SystemExit(0)

if sub == "reconcile-state":
    print("RECONCILE_OK queue_synced=0 waiting_dep_reclassified=0")
    raise SystemExit(0)

if sub == "planner-autobatch":
    if (ROOT / "force_autobatch_duplicate").exists():
        print("AUTOBATCH_SKIP reason=duplicate_title batch_id=none")
        raise SystemExit(0)
    batch_id = "BATCH-99"
    if not any(str(it.get("id", "")) == batch_id for it in queue["items"]):
        queue["items"].append({"id": batch_id, "state": "READY", "next_action": "OPEN_PLAN"})
    if not any(str(t.get("id", "")) == f"{batch_id}-ANALYSIS" for t in board["tasks"]):
        board["tasks"].append({"id": f"{batch_id}-ANALYSIS", "role": "planner", "state": "READY", "title": "Analyze batch"})
    dump(queue_path, queue)
    dump(board_path, board)
    print(f"AUTOBATCH_OK batch_id={batch_id}")
    raise SystemExit(0)

if sub == "claim":
    task_id = ""
    change_plan = ""
    architecture_checks = ""
    for idx, arg in enumerate(args):
        if arg == "--task" and idx + 1 < len(args):
            task_id = args[idx + 1]
        if arg == "--change-plan" and idx + 1 < len(args):
            change_plan = args[idx + 1]
        if arg == "--architecture-checks" and idx + 1 < len(args):
            architecture_checks = args[idx + 1]
    if not change_plan or not architecture_checks:
        print("PRECHANGE_PLAN_INVALID", file=sys.stderr)
        raise SystemExit(8)
    if force_claim_fail.exists() and not task_id:
        print("CLAIM_FAIL forced", file=sys.stderr)
        raise SystemExit(9)
    for task in board["tasks"]:
        if str(task.get("role", "")).strip().lower() == "planner" and str(task.get("state", "")).upper() == "READY":
            if task_id and str(task.get("id", "")) != task_id:
                continue
            task["state"] = "IN_PROGRESS"
            dump(board_path, board)
            print(f"CLAIM_OK task_id={task.get('id', 'unknown')}")
            raise SystemExit(0)
    print("CLAIM_NO_READY", file=sys.stderr)
    raise SystemExit(7)

print(f"UNSUPPORTED:{sub}", file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _setup_workspace() -> Path:
    td = Path(tempfile.mkdtemp(prefix="planner-autonomy-"))
    (td / "scripts").mkdir(parents=True, exist_ok=True)
    (td / "platform" / "automation" / "compat" / "projections").mkdir(parents=True, exist_ok=True)
    (td / "platform" / "policies").mkdir(parents=True, exist_ok=True)
    (td / "docs" / "operations" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (td / "logs-codex-runs" / "orchestrator-state").mkdir(parents=True, exist_ok=True)
    (td / "state").mkdir(parents=True, exist_ok=True)

    _write_exec_safe(td / "platform" / "policies" / "exec_safe.sh")
    (td / "platform" / "automation" / "runtime" / "planner").mkdir(parents=True, exist_ok=True)
    _write_planner_runtime_actions_stub(td / "platform" / "automation" / "runtime" / "planner" / "planner_runtime_actions.py")
    _write_planner_runtime_actions_stub(td / "platform" / "automation" / "compat" / "projections" / "parallel_workstream.py")

    (td / STATE_ROOT / "priority-queue.json").write_text(
        json.dumps({"items": []}), encoding="utf-8"
    )
    (td / STATE_ROOT / "parallel-workstreams.json").write_text(
        json.dumps({"tasks": []}), encoding="utf-8"
    )
    return td


def _run_script(workspace: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["FC_WORKSPACE_ROOT"] = str(workspace)
    env["FC_ROLE_STATE_DIR"] = str(workspace / "state")
    env["FC_PLANNER_AUTONOMY_ENABLED"] = "1"
    env["FC_PLANNER_AUTO_CREATE_ON_EMPTY"] = "1"
    env["FC_PLANNER_WAIT_FORBIDDEN"] = "1"
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class PlannerAutonomyTickTests(unittest.TestCase):
    def test_create_and_claim_when_no_ready_and_no_in_progress(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=create_and_claim", cp.stdout)
        self.assertIn("outcome=resolved", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_action"), "create_and_claim")
        self.assertEqual(state.get("last_outcome"), "resolved")

    def test_no_create_when_planner_has_in_progress(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))

        board_path = ws / STATE_ROOT / "parallel-workstreams.json"
        board = {"tasks": [{"id": "BATCH-10-PLAN", "role": "planner", "state": "IN_PROGRESS"}]}
        board_path.write_text(json.dumps(board), encoding="utf-8")

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=resume_in_progress", cp.stdout)
        self.assertIn("outcome=no_create", cp.stdout)

    def test_direct_claim_recovers_after_generic_claim_failure(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))
        (ws / "force_claim_fail").write_text("1\n", encoding="utf-8")

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=create_and_claim", cp.stdout)
        self.assertIn("outcome=resolved", cp.stdout)
        self.assertIn("direct_task=BATCH-99-ANALYSIS", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_outcome"), "resolved")
        self.assertEqual(state.get("target_task"), "BATCH-99-ANALYSIS")

    def test_create_and_claim_hard_fails_when_all_claim_paths_fail(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))
        stub = ws / "platform" / "automation" / "runtime" / "planner" / "planner_runtime_actions.py"
        original = stub.read_text(encoding="utf-8")
        stub.write_text(
            original.replace(
                'if force_claim_fail.exists() and not task_id:\n        print("CLAIM_FAIL forced", file=sys.stderr)\n        raise SystemExit(9)\n',
                'if force_claim_fail.exists():\n        print("CLAIM_FAIL forced", file=sys.stderr)\n        raise SystemExit(9)\n',
            ),
            encoding="utf-8",
        )
        (ws / "force_claim_fail").write_text("1\n", encoding="utf-8")

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=create_and_claim", cp.stdout)
        self.assertIn("outcome=failed", cp.stdout)
        self.assertIn("planner_claim_after_create_failed_hard", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_outcome"), "failed")
        self.assertEqual(state.get("issue_code"), "planner_claim_after_create_failed_hard")

    def test_repair_only_when_runway_not_empty_and_no_ready(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))

        board_path = ws / STATE_ROOT / "parallel-workstreams.json"
        board_path.write_text(
            json.dumps(
                {
                    "tasks": [{"id": "BATCH-10-ADMIN-01", "role": "admin", "state": "BLOCKED"}],
                    "streams": [{"id": "BATCH-10", "state": "BLOCKED"}],
                }
            ),
            encoding="utf-8",
        )

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=repair_only", cp.stdout)
        self.assertIn("issue=planner_ready_runtime_dispatch_missing", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_action"), "repair_only")
        self.assertEqual(state.get("issue_code"), "planner_ready_runtime_dispatch_missing")

    def test_repair_only_dispatches_bridge_when_runway_not_empty(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))

        board_path = ws / STATE_ROOT / "parallel-workstreams.json"
        board_path.write_text(
            json.dumps(
                {
                    "tasks": [{"id": "BATCH-10-DEV-01", "role": "dev", "state": "READY_DEV"}],
                    "streams": [{"id": "BATCH-10", "state": "READY_DEV"}],
                }
            ),
            encoding="utf-8",
        )
        (ws / "force_bridge_dispatch").write_text("1\n", encoding="utf-8")

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=repair_runtime_dispatch", cp.stdout)
        self.assertIn("outcome=resolved", cp.stdout)
        self.assertIn("task_id=BATCH-10-DEV-01", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_action"), "repair_runtime_dispatch")
        self.assertEqual(state.get("last_outcome"), "resolved")
        self.assertEqual(state.get("target_task"), "BATCH-10-DEV-01")

    def test_duplicate_autobatch_skip_is_nonfatal(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))
        (ws / "force_autobatch_duplicate").write_text("1\n", encoding="utf-8")

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=autobatch_skip", cp.stdout)
        self.assertIn("issue=autobatch_duplicate_nonfatal", cp.stdout)
        self.assertNotIn("planner_claim_after_create_failed", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_action"), "autobatch_skip")
        self.assertEqual(state.get("issue_code"), "autobatch_duplicate_nonfatal")


if __name__ == "__main__":
    unittest.main()
