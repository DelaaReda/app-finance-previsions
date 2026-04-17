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


def _write_api_wave_stub(path: Path) -> None:
    path.write_text(
        """from __future__ import annotations

import json
from pathlib import Path
from typing import Any

API_WAVE_BATCH_ID = "API-WAVE"


def _state_path(root: Path) -> Path:
    return Path(root) / "logs-codex-runs" / "orchestrator-state" / "api_wave_state.json"


def api_wave_proof_path(root: Path, endpoint_id: str) -> Path:
    endpoint_token = str(endpoint_id or "").strip().replace(".", "__").replace("-", "_").lower()
    return Path(root) / "logs-codex-runs" / "orchestrator-state" / "api-wave-proofs" / f"{endpoint_token}.json"


def load_api_wave_manifest(root: Path, persist_defaults: bool = False) -> dict[str, Any]:
    manifest_path = Path(root) / "platform" / "automation" / "config" / "api_wave_manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_api_wave_state(root: Path, persist_defaults: bool = False) -> dict[str, Any]:
    path = _state_path(Path(root))
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_api_wave_proof(root: Path, endpoint_id: str) -> dict[str, Any]:
    path = api_wave_proof_path(Path(root), endpoint_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def persist_api_wave_proof(root: Path, endpoint_id: str, payload: dict[str, Any]) -> Path:
    path = api_wave_proof_path(Path(root), endpoint_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\\n", encoding="utf-8")
    return path


def api_wave_manifest_path(root: Path) -> Path:
    return Path(root) / "platform" / "automation" / "config" / "api_wave_manifest.json"


def api_wave_owner_task_id(endpoint_id: str) -> str:
    token = str(endpoint_id or '').strip().upper().replace('.', '_').replace('-', '_')
    return f"API-WAVE-DEV-{token}"


def build_api_wave_snapshot(root: Path, *, delivery_state: dict[str, Any] | None = None, normalized_states: list[dict[str, Any]] | None = None, prior_state: dict[str, Any] | None = None, now: Any = None) -> dict[str, Any]:
    root = Path(root)
    manifest_path = root / "platform" / "automation" / "config" / "api_wave_manifest.json"
    if not manifest_path.exists():
        return {
            "enabled": False,
            "dispatch_ready": False,
            "current_endpoint": None,
            "next_endpoint": None,
            "current_task_id": None,
            "state": {"schema_version": "api_wave_state.v1", "current_endpoint_id": "", "current_task_id": "", "completed_endpoint_ids": [], "deferred_endpoint_ids": []},
            "reason": "disabled",
        }
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    endpoints = payload.get("endpoints", payload.get("items", []))
    endpoint = endpoints[0] if isinstance(endpoints, list) and endpoints else {}
    endpoint_id = str(endpoint.get("endpoint_id") or "copilot_search").strip()
    task_id = f"API-WAVE-DEV-{endpoint_id.upper().replace('.', '_').replace('-', '_')}"
    delivery_state = delivery_state if isinstance(delivery_state, dict) else {}
    dispatch_ready = bool(delivery_state.get("ec2_reachable", False)) and not str(delivery_state.get("active_batch_id") or "").strip()
    endpoint_payload = dict(endpoint)
    endpoint_payload["owner_task_id"] = task_id
    state = {
        "schema_version": "api_wave_state.v1",
        "wave_batch_id": API_WAVE_BATCH_ID,
        "current_endpoint_id": endpoint_id,
        "current_task_id": task_id,
        "completed_endpoint_ids": [],
        "deferred_endpoint_ids": [],
    }
    return {
        "enabled": True,
        "mode": "api_autonomy_mode",
        "stream_id": API_WAVE_BATCH_ID,
        "batch_id": API_WAVE_BATCH_ID,
        "wave_batch_id": API_WAVE_BATCH_ID,
        "dispatch_ready": dispatch_ready,
        "current_endpoint": endpoint_payload,
        "next_endpoint": None,
        "current_task_id": task_id,
        "current_status": "ready",
        "completed_endpoint_ids": [],
        "deferred_endpoint_ids": [],
        "last_public_proof_ref": "none",
        "state": state,
        "reason": "dispatch_ready" if dispatch_ready else "waiting_active_batch",
    }


def persist_api_wave_state(root: Path, payload: dict[str, Any]) -> Path:
    path = _state_path(Path(root))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\\n", encoding="utf-8")
    return path
""",
        encoding="utf-8",
    )


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
    allow_active_queued = "--allow-active-queued" in args
    active_cycle_ids = []
    active_cycle = queue.get("active_cycle")
    if isinstance(active_cycle, dict) and isinstance(active_cycle.get("active_batch_ids"), list):
        active_cycle_ids = [str(item).strip().upper() for item in active_cycle.get("active_batch_ids", []) if str(item).strip()]
    if active_cycle_ids and not allow_active_queued:
        print(f"AUTOBATCH_SKIP reason=active_cycle_pinned batch_id={active_cycle_ids[0]}")
        raise SystemExit(0)
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

if sub == "api-wave-dispatch":
    print("API_WAVE_DISPATCH endpoint_id=copilot_search task_id=API-WAVE-DEV-COPILOT_SEARCH reason=subagent_running backend=mock completed=0")
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
    (td / "platform" / "automation" / "runtime" / "truth").mkdir(parents=True, exist_ok=True)
    (td / "docs" / "operations" / "orchestrator").mkdir(parents=True, exist_ok=True)
    (td / "logs-codex-runs" / "orchestrator-state").mkdir(parents=True, exist_ok=True)
    (td / "state").mkdir(parents=True, exist_ok=True)

    _write_exec_safe(td / "platform" / "policies" / "exec_safe.sh")
    (td / "platform" / "automation" / "runtime" / "__init__.py").write_text("", encoding="utf-8")
    (td / "platform" / "automation" / "runtime" / "truth" / "__init__.py").write_text("", encoding="utf-8")
    (td / "platform" / "automation" / "runtime" / "planner" / "__init__.py").write_text("", encoding="utf-8")
    (td / "platform" / "automation" / "compat" / "__init__.py").write_text("", encoding="utf-8")
    (td / "platform" / "automation" / "compat" / "projections" / "__init__.py").write_text("", encoding="utf-8")
    _write_api_wave_stub(td / "platform" / "automation" / "runtime" / "truth" / "api_wave.py")
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


def _enable_api_wave(workspace: Path) -> None:
    manifest_dir = workspace / "platform" / "automation" / "config"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "api_wave_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "api_wave_manifest.v1",
                "mode": "api_autonomy_mode",
                "enabled": True,
                "wave_batch_id": "API-WAVE",
                "stream_id": "API-WAVE",
                "items": [
                    {
                        "endpoint_id": "copilot_search",
                        "domain": "copilot",
                        "route_path": "/api/search/tickers",
                        "public_smoke_path": "/api/search/tickers?q=NVDA",
                        "route_module": "apps/api/src/domains/copilot/api/search.py",
                        "priority": "P1",
                        "product_surface": "copilot",
                        "shared_contract": "packages/contracts/copilot_search_v1.py",
                        "endpoint_service": "apps/api/src/domains/copilot/application/copilot_search_endpoint_service.py",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _run_script(workspace: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["FC_WORKSPACE_ROOT"] = str(workspace)
    env["FC_ROLE_STATE_DIR"] = str(workspace / "state")
    env["FC_PLANNER_AUTONOMY_ENABLED"] = "1"
    env["FC_PLANNER_AUTO_CREATE_ON_EMPTY"] = "1"
    env["FC_PLANNER_WAIT_FORBIDDEN"] = "1"
    env["FC_PLANNER_AUTONOMY_EC2_REACHABLE"] = "1"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class PlannerAutonomyTickTests(unittest.TestCase):
    def test_api_wave_dispatch_preempts_autobatch_when_manifest_is_present(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))
        _enable_api_wave(ws)

        cp = _run_script(ws)
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=dispatch_api_wave", cp.stdout)
        self.assertIn("endpoint_id=copilot_search", cp.stdout)
        self.assertNotIn("action=create_and_claim", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_action"), "dispatch_api_wave")
        self.assertEqual(state.get("last_outcome"), "resolved")

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

        queue_path = ws / STATE_ROOT / "priority-queue.json"
        board_path = ws / STATE_ROOT / "parallel-workstreams.json"
        queue_path.write_text(
            json.dumps(
                {
                    "active_cycle": {"active_batch_ids": ["BATCH-10"], "cycle_id": "cycle-10"},
                    "items": [{"id": "BATCH-10", "state": "IN_PROGRESS"}],
                }
            ),
            encoding="utf-8",
        )
        board_path.write_text(
            json.dumps(
                {
                    "active_cycle": {"active_batch_ids": ["BATCH-10"], "cycle_id": "cycle-10"},
                    "tasks": [{"id": "BATCH-10-ADMIN-01", "stream_id": "BATCH-10", "role": "admin", "state": "BLOCKED"}],
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

    def test_external_outage_defers_planner_activity(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))

        cp = _run_script(ws, extra_env={"FC_PLANNER_AUTONOMY_EC2_REACHABLE": "0"})
        self.assertEqual(cp.returncode, 0, msg=cp.stderr)
        self.assertIn("action=delivery_governor", cp.stdout)
        self.assertIn("issue=external_outage", cp.stdout)

        state = json.loads((ws / "state" / "planner_autonomy_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("last_action"), "delivery_governor")
        self.assertEqual(state.get("issue_code"), "external_outage")

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

    def test_active_cycle_keeps_repair_path_while_delivery_is_active(self) -> None:
        ws = _setup_workspace()
        self.addCleanup(lambda: shutil.rmtree(ws, ignore_errors=True))

        queue_path = ws / STATE_ROOT / "priority-queue.json"
        board_path = ws / STATE_ROOT / "parallel-workstreams.json"
        queue_path.write_text(
            json.dumps(
                {
                    "active_cycle": {"active_batch_ids": ["BATCH-10"], "cycle_id": "cycle-10"},
                    "items": [{"id": "BATCH-10", "state": "IN_PROGRESS"}],
                }
            ),
            encoding="utf-8",
        )
        board_path.write_text(
            json.dumps(
                {
                    "active_cycle": {"active_batch_ids": ["BATCH-10"], "cycle_id": "cycle-10"},
                    "tasks": [{"id": "BATCH-10-DEV-01", "stream_id": "BATCH-10", "role": "dev", "state": "IN_PROGRESS"}],
                    "streams": [{"id": "BATCH-10", "state": "IN_PROGRESS"}],
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


if __name__ == "__main__":
    unittest.main()
