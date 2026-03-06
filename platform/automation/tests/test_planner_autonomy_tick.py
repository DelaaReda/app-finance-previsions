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


def _write_parallel_workstream_stub(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path.cwd()
queue_path = ROOT / "docs" / "operations" / "orchestrator" / "priority-queue.json"
board_path = ROOT / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
force_claim_fail = ROOT / "force_claim_fail"


def load(path: Path, fallback: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except Exception:
        return fallback


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\\n", encoding="utf-8")


sub = sys.argv[1] if len(sys.argv) > 1 else ""
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

if sub == "planner-autobatch":
    batch_id = "BATCH-99"
    if not any(str(it.get("id", "")) == batch_id for it in queue["items"]):
        queue["items"].append({"id": batch_id, "state": "READY", "next_action": "OPEN_PLAN"})
    if not any(str(t.get("id", "")) == f"{batch_id}-PLAN" for t in board["tasks"]):
        board["tasks"].append({"id": f"{batch_id}-PLAN", "role": "planner", "state": "READY", "title": "Plan batch"})
    dump(queue_path, queue)
    dump(board_path, board)
    print(f"AUTOBATCH_OK batch_id={batch_id}")
    raise SystemExit(0)

if sub == "claim":
    if force_claim_fail.exists():
        print("CLAIM_FAIL forced", file=sys.stderr)
        raise SystemExit(9)
    for task in board["tasks"]:
        if str(task.get("role", "")).strip().lower() == "planner" and str(task.get("state", "")).upper() == "READY":
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
    (td / "platform" / "automation").mkdir(parents=True, exist_ok=True)
    (td / "platform" / "policies").mkdir(parents=True, exist_ok=True)
    (td / "docs" / "operations" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (td / "logs-codex-runs").mkdir(parents=True, exist_ok=True)
    (td / "state").mkdir(parents=True, exist_ok=True)

    _write_exec_safe(td / "platform" / "policies" / "exec_safe.sh")
    _write_parallel_workstream_stub(td / "platform" / "automation" / "parallel_workstream.py")

    (td / "docs" / "operations" / "orchestrator" / "priority-queue.json").write_text(
        json.dumps({"items": []}), encoding="utf-8"
    )
    (td / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json").write_text(
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

        board_path = ws / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
        board = {"tasks": [{"id": "BATCH-10-PLAN", "role": "planner", "state": "IN_PROGRESS"}]}
        board_path.write_text(json.dumps(board), encoding="utf-8")

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=resume_in_progress", cp.stdout)
        self.assertIn("outcome=no_create", cp.stdout)

    def test_issue_when_claim_fails_after_create(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))
        (ws / "force_claim_fail").write_text("1\n", encoding="utf-8")

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("issue=planner_claim_after_create_failed", cp.stdout)
        self.assertIn("outcome=deferred", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("issue_code"), "planner_claim_after_create_failed")


if __name__ == "__main__":
    unittest.main()
