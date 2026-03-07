#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from parallel_workstream import append_event, board_lock, load_board, now_iso, recompute_states, reconcile_state, save_board

RUNTIME_BLOCKERS = {
    "API_UNREACHABLE",
    "BACKEND_API_UNREACHABLE",
    "BACKEND_API_HEALTHCHECK_FAIL",
    "MONITOR_API_UNREACHABLE",
    "BACKEND_AND_MONITOR_UNREACHABLE",
    "RUNTIME_DOWN",
    "RUNTIME_DOWN_BLOCKS_READY_QUEUE",
    "RUNTIME_DEGRADED",
    "RUNTIME_RECOVERED_SOFT",
}
READY_STATES = {"READY", "READY_PLANNER", "READY_DEV"}
ACTIVE_IN_PROGRESS_STATES = {"IN_PROGRESS", "REVIEW"}
CORE_ROLES = ("planner", "dev", "admin", "scrum_master")


@dataclass
class ReconcileConfig:
    root: Path
    role: str
    queue_path: Path
    board_path: Path
    state_dir: Path
    report_path: Path
    lock_dir: Path
    stale_lock_seconds: int = 1800
    stale_in_progress_seconds: int = 14400
    ready_starvation_seconds: int = 1800


def _canonical_role(role: str) -> str:
    token = (role or "").strip().lower()
    if token in {"backend_engineer", "frontend_engineer", "data_analyst", "integrator"}:
        return "dev"
    if token in {"qa", "tester", "infra_engineer", "clawsentinel"}:
        return "admin"
    if token in {"analyst", "architect", "po", "vision-architect-tasks-planner", "vision_architect_tasks_planner"}:
        return "planner"
    return token


def _load_json(path: Path, default: dict | list) -> dict | list:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _parse_iso_epoch(value: str) -> int:
    raw = (value or "").strip()
    if not raw:
        return 0
    try:
        if raw.endswith("Z"):
            from datetime import datetime, timezone

            return int(datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
        from datetime import datetime, timezone

        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except Exception:
        return 0


def _preferred_ready_state_for_role(role: str) -> str:
    return "READY_DEV" if _canonical_role(role) == "dev" else "READY"


def _preferred_ready_state_for_stream(board: dict, stream_id: str, fallback_role: str = "") -> str:
    task_roles = []
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if str(task.get("stream_id", "")).strip().upper() != stream_id.upper():
            continue
        state = str(task.get("state", "")).strip().upper()
        if state in {"DONE", "CLOSED"}:
            continue
        task_roles.append(_canonical_role(str(task.get("role") or task.get("assignee") or "").strip()))
    if "dev" in task_roles:
        return "READY_DEV"
    if task_roles:
        return "READY"
    return _preferred_ready_state_for_role(fallback_role)


def _extract_meta_field(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    m = re.search(rf"\b{re.escape(key)}=(\S+)", text)
    return m.group(1) if m else ""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _runtime_probes_ok() -> bool:
    try:
        import urllib.request

        for url in ("http://127.0.0.1:8050/api/health", "http://127.0.0.1:7779/api/status"):
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                status = int(getattr(resp, "status", 0) or 0)
                if not (200 <= status < 300):
                    return False
        return True
    except Exception:
        return False


def _active_planner_subagent_owner_tasks(root: Path) -> set[str]:
    registry_path = root / "docs" / "operations" / "orchestrator" / "planner-subagents-registry.json"
    raw = _load_json(registry_path, [])
    rows: list[dict] = []
    if isinstance(raw, list):
        rows = [item for item in raw if isinstance(item, dict)]
    elif isinstance(raw, dict):
        items = raw.get("items")
        if isinstance(items, list):
            rows = [item for item in items if isinstance(item, dict)]
    owners: set[str] = set()
    for item in rows:
        status = str(item.get("status", "")).strip().lower()
        owner_task_id = str(item.get("owner_task_id", "")).strip()
        if status in ACTIVE_IN_PROGRESS_STATES or status in {"spawned", "running"}:
            if owner_task_id:
                owners.add(owner_task_id)
    return owners


def _task_has_delivery_evidence(task: dict) -> bool:
    for key in ("artifact", "verify", "commit_sha", "files_touched"):
        token = str(task.get(key, "") or "").strip().lower()
        if token and token not in {"none", "n/a", "na"}:
            return True
    return False


def _parse_contract(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().upper()
        if key and key not in values:
            values[key] = value.strip()
    return values


def _render_contract(values: dict[str, str]) -> str:
    ordered = ["STATUS", "DELTA", "EVIDENCE", "RISKS", "NEXT", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE"]
    return "\n".join(f"{key}: {values.get(key, ).strip()}" for key in ordered) + "\n"


def _evidence_pairs(raw: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for frag in str(raw or "").split(";"):
        item = frag.strip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key and key not in pairs:
            pairs[key] = value.strip()
    return pairs


def _upsert_evidence(raw: str, key: str, value: str) -> str:
    pairs = _evidence_pairs(raw)
    pairs[key.strip().lower()] = value
    preferred = [
        "task_update",
        "lock_check",
        "run_note",
        "issues",
        "issue_count",
        "issue_severity",
    ]
    parts: list[str] = []
    seen: set[str] = set()
    for item in preferred:
        if item in pairs:
            parts.append(f"{item}={pairs[item]}")
            seen.add(item)
    for item in sorted(pairs.keys()):
        if item in seen:
            continue
        parts.append(f"{item}={pairs[item]}")
    return "; ".join(parts)


def _contract_has_runtime_blocker(values: dict[str, str]) -> bool:
    blocker = str(values.get("BLOCKER_ID", "") or "").strip().upper()
    return blocker in RUNTIME_BLOCKERS or blocker.startswith("RUNTIME_")


def _clear_runtime_blocker_in_contract(path: Path, role: str, now: str) -> bool:
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    values = _parse_contract(text)
    if not _contract_has_runtime_blocker(values):
        return False
    if values.get("STATUS", "").strip().upper() not in {"BLOCKED", "WAIT", "FAIL"}:
        return False
    values["STATUS"] = "WAIT"
    values["DELTA"] = "RUNTIME_RECOVERED_SOFT"
    values["VERDICT"] = "PASS"
    values["BLOCKER_ID"] = "NONE"
    values["RISKS"] = "runtime blocker stale auto-cleared after healthy probes"
    values["NEXT"] = f"owner={role}; action=resume normal execution after runtime recovery"
    values["NEXT_ACTION_UNIQUE"] = f"RUNTIME_RECOVERED_SOFT_{role.upper()}_{int(time.time())}"
    evidence = values.get("EVIDENCE", "")
    evidence = _upsert_evidence(evidence, "runtime_recovered_live_probe", "1")
    evidence = _upsert_evidence(evidence, "runtime_recovered_at", now)
    values["EVIDENCE"] = evidence
    path.write_text(_render_contract(values), encoding="utf-8")
    return True


def run_reconciler(config: ReconcileConfig, probe_runtime_ok: Callable[[], bool] | None = None, now_epoch: int | None = None) -> dict[str, int | str]:
    probe_runtime_ok = probe_runtime_ok or _runtime_probes_ok
    now_epoch = int(now_epoch or time.time())
    now = now_iso()
    queue_obj = _load_json(config.queue_path, {"items": []})
    if not isinstance(queue_obj, dict):
        queue_obj = {"items": []}

    report: dict[str, int | str] = {
        "at": now,
        "fixes_applied": 0,
        "parked_inprogress_fixed": 0,
        "runtime_blockers_cleared": 0,
        "stale_locks_removed": 0,
        "stale_inprogress_marked": 0,
        "ready_starvation_detected": 0,
        "dependency_starvation_detected": 0,
    }
    active_subagent_owner_tasks = _active_planner_subagent_owner_tasks(config.root)
    capability_stall_seconds = max(60, int(os.environ.get("FC_RECONCILE_CAPABILITY_STALL_SECONDS", "300")))

    with board_lock(config.board_path):
        board = load_board(config.board_path)
        if not isinstance(board, dict):
            board = {"tasks": [], "streams": [], "events": []}

        # 1) parked + in_progress contradictions
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            if not task.get("parked_by_rebuild"):
                continue
            state = str(task.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            task["state"] = _preferred_ready_state_for_role(str(task.get("role") or task.get("assignee") or ""))
            task["stalled_reason"] = "parked_by_rebuild_cannot_stay_in_progress"
            task["reconciled_at"] = now
            task["updated_at"] = now
            report["parked_inprogress_fixed"] = int(report["parked_inprogress_fixed"]) + 1

        for stream in board.get("streams", []):
            if not isinstance(stream, dict):
                continue
            if not stream.get("parked_by_rebuild"):
                continue
            state = str(stream.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            stream_id = str(stream.get("id", "")).strip()
            stream["state"] = _preferred_ready_state_for_stream(board, stream_id, str(stream.get("owner_role") or ""))
            stream["stalled_reason"] = "parked_by_rebuild_cannot_stay_in_progress"
            stream["reconciled_at"] = now
            stream["updated_at"] = now
            report["parked_inprogress_fixed"] = int(report["parked_inprogress_fixed"]) + 1

        for item in queue_obj.get("items", []):
            if not isinstance(item, dict):
                continue
            if not item.get("parked_by_rebuild"):
                continue
            state = str(item.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            stream_id = str(item.get("id", "")).strip()
            item["state"] = _preferred_ready_state_for_stream(board, stream_id, str(item.get("owner_role") or ""))
            item["stalled_reason"] = "parked_by_rebuild_cannot_stay_in_progress"
            item["reconciled_at"] = now
            item["updated_at"] = now
            report["parked_inprogress_fixed"] = int(report["parked_inprogress_fixed"]) + 1

        # 2) stale in-progress -> downgrade to READY/READY_DEV
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            state = str(task.get("state", "")).strip().upper()
            if state not in ACTIVE_IN_PROGRESS_STATES:
                continue
            updated_epoch = _parse_iso_epoch(str(task.get("updated_at", "")))
            task_id_value = str(task.get("id", "")).strip()
            task_role = _canonical_role(str(task.get("role") or task.get("assignee") or ""))
            if (
                task_role == "dev"
                and updated_epoch > 0
                and (now_epoch - updated_epoch) >= capability_stall_seconds
                and task_id_value not in active_subagent_owner_tasks
                and not _task_has_delivery_evidence(task)
            ):
                task["state"] = _preferred_ready_state_for_role(task_role)
                task["stalled_reason"] = "planner_capability_stall_no_active_subagent"
                task["last_progress_at"] = str(updated_epoch)
                task["reconciled_at"] = now
                task["updated_at"] = now
                report["stale_inprogress_marked"] = int(report["stale_inprogress_marked"]) + 1
                continue
            if updated_epoch <= 0 or (now_epoch - updated_epoch) < config.stale_in_progress_seconds:
                continue
            task["state"] = _preferred_ready_state_for_role(str(task.get("role") or task.get("assignee") or ""))
            task["stalled_reason"] = f"stale_in_progress>{config.stale_in_progress_seconds}s"
            task["last_progress_at"] = str(updated_epoch)
            task["reconciled_at"] = now
            task["updated_at"] = now
            report["stale_inprogress_marked"] = int(report["stale_inprogress_marked"]) + 1

        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            state = str(task.get("state", "")).strip().upper()
            updated_epoch = _parse_iso_epoch(str(task.get("updated_at", ""))) or _parse_iso_epoch(str(task.get("ready_at", "")))
            if state in READY_STATES and updated_epoch > 0 and (now_epoch - updated_epoch) >= config.ready_starvation_seconds:
                if not task.get("ready_starvation"):
                    task["ready_starvation"] = True
                    task["ready_starved_at"] = now
                    task["stalled_reason"] = task.get("stalled_reason") or f"ready_starvation>{config.ready_starvation_seconds}s"
                    task["reconciled_at"] = now
                    report["ready_starvation_detected"] = int(report["ready_starvation_detected"]) + 1
            if state == "WAITING_DEP" and updated_epoch > 0 and (now_epoch - updated_epoch) >= max(config.ready_starvation_seconds * 2, 600):
                if not task.get("dependency_starvation"):
                    task["dependency_starvation"] = True
                    task["dependency_starved_at"] = now
                    task["stalled_reason"] = task.get("stalled_reason") or "dependency_starvation"
                    task["reconciled_at"] = now
                    report["dependency_starvation_detected"] = int(report["dependency_starvation_detected"]) + 1

        for stream in board.get("streams", []):
            if not isinstance(stream, dict):
                continue
            state = str(stream.get("state", "")).strip().upper()
            updated_epoch = _parse_iso_epoch(str(stream.get("updated_at", ""))) or _parse_iso_epoch(str(stream.get("ready_at", "")))
            if state in READY_STATES and updated_epoch > 0 and (now_epoch - updated_epoch) >= config.ready_starvation_seconds:
                if not stream.get("ready_starvation"):
                    stream["ready_starvation"] = True
                    stream["ready_starved_at"] = now
                    stream["stalled_reason"] = stream.get("stalled_reason") or f"ready_starvation>{config.ready_starvation_seconds}s"
                    stream["reconciled_at"] = now

        _write_json(config.queue_path, queue_obj)
        recompute_states(board)
        queue_sync = reconcile_state(board, config.queue_path)
        save_board(config.board_path, board)
        report["fixes_applied"] = int(report["fixes_applied"]) + int(queue_sync.get("queue_synced", 0))
        if (
            int(report["parked_inprogress_fixed"])
            or int(report["stale_inprogress_marked"])
            or int(report["ready_starvation_detected"])
            or int(report["dependency_starvation_detected"])
        ):
            append_event(
                board,
                "state_reconcile",
                {
                    "role": config.role,
                    "parked_inprogress_fixed": str(report["parked_inprogress_fixed"]),
                    "stale_inprogress_marked": str(report["stale_inprogress_marked"]),
                    "ready_starvation_detected": str(report["ready_starvation_detected"]),
                    "dependency_starvation_detected": str(report["dependency_starvation_detected"]),
                },
            )
            save_board(config.board_path, board)

    # Reload queue after reconcile_state persisted canonical truth.
    queue_obj = _load_json(config.queue_path, {"items": []})
    if not isinstance(queue_obj, dict):
        queue_obj = {"items": []}

    # 3) ready starvation markers
    for item in queue_obj.get("items", []):
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "")).strip().upper()
        if state not in READY_STATES:
            continue
        updated_epoch = _parse_iso_epoch(str(item.get("updated_at", ""))) or _parse_iso_epoch(str(item.get("ready_at", "")))
        if updated_epoch <= 0 or (now_epoch - updated_epoch) < config.ready_starvation_seconds:
            continue
        if not item.get("ready_starvation"):
            item["ready_starvation"] = True
            item["ready_starved_at"] = now
            item["reconciled_at"] = now
            report["ready_starvation_detected"] = int(report["ready_starvation_detected"]) + 1
    _write_json(config.queue_path, queue_obj)

    # 4) stale runtime blockers
    if probe_runtime_ok():
        for role in CORE_ROLES:
            contract_path = config.state_dir / f"{role}.last_contract"
            if _clear_runtime_blocker_in_contract(contract_path, role, now):
                report["runtime_blockers_cleared"] = int(report["runtime_blockers_cleared"]) + 1

    # 5) stale lock cleanup
    if config.lock_dir.exists():
        for lock_path in config.lock_dir.glob("*.lock"):
            meta_path = Path(str(lock_path) + ".meta")
            pid_raw = _extract_meta_field(meta_path, "pid")
            start_raw = _extract_meta_field(meta_path, "start_epoch")
            pid = int(pid_raw) if pid_raw.isdigit() else 0
            start_epoch = int(start_raw) if start_raw.isdigit() else 0
            age = now_epoch - start_epoch if start_epoch > 0 else config.stale_lock_seconds + 1
            if pid and _pid_alive(pid):
                continue
            if age < config.stale_lock_seconds:
                continue
            try:
                lock_path.unlink(missing_ok=True)
            except TypeError:
                if lock_path.exists():
                    lock_path.unlink()
            except Exception:
                pass
            try:
                meta_path.unlink(missing_ok=True)
            except TypeError:
                if meta_path.exists():
                    meta_path.unlink()
            except Exception:
                pass
            report["stale_locks_removed"] = int(report["stale_locks_removed"]) + 1

    report["fixes_applied"] = (
        int(report["parked_inprogress_fixed"])
        + int(report["runtime_blockers_cleared"])
        + int(report["stale_locks_removed"])
        + int(report["stale_inprogress_marked"])
        + int(report["ready_starvation_detected"])
        + int(report["dependency_starvation_detected"])
    )
    _write_json(config.report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pre-tick runtime truth reconciler")
    parser.add_argument("--role", default="system")
    parser.add_argument("--root", default=str(Path.cwd()))
    parser.add_argument("--queue", default="docs/operations/orchestrator/priority-queue.json")
    parser.add_argument("--board", default="docs/operations/orchestrator/parallel-workstreams.json")
    parser.add_argument("--state-dir", default=str(Path.home() / ".openclaw" / "cron" / "role-state"))
    parser.add_argument("--report", default="docs/operations/orchestrator/state-reconcile-report.json")
    parser.add_argument("--lock-dir", default="/tmp/fc-agent-locks")
    parser.add_argument("--stale-lock-seconds", type=int, default=int(os.environ.get("FC_RECONCILE_STALE_LOCK_SECONDS", "1800")))
    parser.add_argument("--stale-in-progress-seconds", type=int, default=int(os.environ.get("FC_RECONCILE_STALE_IN_PROGRESS_SECONDS", "14400")))
    parser.add_argument("--ready-starvation-seconds", type=int, default=int(os.environ.get("FC_RECONCILE_READY_STARVATION_SECONDS", "1800")))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    config = ReconcileConfig(
        root=root,
        role=_canonical_role(args.role),
        queue_path=(root / args.queue).resolve() if not str(args.queue).startswith("/") else Path(args.queue).resolve(),
        board_path=(root / args.board).resolve() if not str(args.board).startswith("/") else Path(args.board).resolve(),
        state_dir=Path(args.state_dir).expanduser().resolve(),
        report_path=(root / args.report).resolve() if not str(args.report).startswith("/") else Path(args.report).resolve(),
        lock_dir=Path(args.lock_dir).expanduser().resolve(),
        stale_lock_seconds=max(60, int(args.stale_lock_seconds)),
        stale_in_progress_seconds=max(300, int(args.stale_in_progress_seconds)),
        ready_starvation_seconds=max(300, int(args.ready_starvation_seconds)),
    )
    report = run_reconciler(config)
    print(json.dumps(report, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
