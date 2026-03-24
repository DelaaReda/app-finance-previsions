#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parallel_workstream import (
    STATE_DONE,
    STATE_READY,
    STATE_READY_DEV,
    append_event,
    board_lock,
    load_board,
    recompute_states,
    save_board,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD_PATH = ROOT / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
DEFAULT_QUEUE_PATH = ROOT / "docs" / "operations" / "orchestrator" / "priority-queue.json"
LEGACY_PLANNER_CODES = {"PLAN", "ANALYSIS", "ARCH", "GOV_REVIEW"}
OPEN_QUEUE_STATES = {"BACKLOG", "PLANNED", "WAITING_DEP", "READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW", "BLOCKED"}
OPEN_TASK_STATES = {"BACKLOG", "WAITING_DEP", "READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW", "BLOCKED"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_state(value: Any) -> str:
    token = str(value or "").strip().upper()
    if token in {"READY", "READY_PLANNER"}:
        return STATE_READY
    if token == "READY_DEV":
        return STATE_READY_DEV
    if token == "CLOSED":
        return STATE_DONE
    return token


def load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"items": [], "updated_at": now_iso()}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"QUEUE_SCHEMA_ERROR: {path} root must be object")
    if not isinstance(payload.get("items"), list):
        payload["items"] = []
    return payload


def save_queue(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = now_iso()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def report_path_for(root: Path, mode: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / "evidence" / "runtime-gates" / f"planner-monolane-migration-{mode}-{stamp}.json"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def summarize_board(board: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in board.get("tasks", []):
        state = normalize_state(task.get("state")) or "UNKNOWN"
        counts[state] = counts.get(state, 0) + 1
    return counts


def summarize_queue(queue: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in queue.get("items", []):
        state = normalize_state(item.get("state")) or "UNKNOWN"
        counts[state] = counts.get(state, 0) + 1
    return counts


def _task_snapshot(task: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(task)


def _queue_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(item)


def _change_record(change_id: str, before: dict[str, Any], after: dict[str, Any] | None) -> dict[str, Any]:
    return {"id": change_id, "before": before, "after": after}


def is_open_task(task: dict[str, Any]) -> bool:
    return normalize_state(task.get("state")) in OPEN_TASK_STATES


def is_open_queue_item(item: dict[str, Any]) -> bool:
    return normalize_state(item.get("state")) in OPEN_QUEUE_STATES


def migrate_board(board: dict[str, Any], migrated_at: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = {
        "legacy_planner_tasks_removed": 0,
        "task_states_normalized": 0,
        "task_dependencies_pruned": 0,
        "stream_task_refs_pruned": 0,
    }
    changes: list[dict[str, Any]] = []
    removed_ids: set[str] = set()
    kept_tasks: list[dict[str, Any]] = []

    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        before = _task_snapshot(task)
        task_id = str(task.get("id", "")).strip()
        role = str(task.get("role", "")).strip().lower()
        code = str(task.get("code", "")).strip().upper()
        state = normalize_state(task.get("state"))
        if state and state != str(task.get("state", "")).strip().upper():
            task["state"] = state
            task["updated_at"] = migrated_at
            counts["task_states_normalized"] += 1
        if role == "planner" and code in LEGACY_PLANNER_CODES and normalize_state(task.get("state")) != STATE_DONE:
            removed_ids.add(task_id)
            counts["legacy_planner_tasks_removed"] += 1
            changes.append(_change_record(task_id, before, None))
            continue
        kept_tasks.append(task)
        if before != task:
            changes.append(_change_record(task_id, before, _task_snapshot(task)))

    board["tasks"] = kept_tasks

    if removed_ids:
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            before = _task_snapshot(task)
            deps = [str(dep).strip() for dep in (task.get("depends_on") or []) if str(dep).strip()]
            filtered = [dep for dep in deps if dep not in removed_ids]
            if filtered != deps:
                task["depends_on"] = filtered
                task["updated_at"] = migrated_at
                counts["task_dependencies_pruned"] += 1
                changes.append(_change_record(str(task.get("id", "")).strip(), before, _task_snapshot(task)))
        for stream in board.get("streams", []):
            if not isinstance(stream, dict):
                continue
            task_ids = stream.get("task_ids")
            if not isinstance(task_ids, list):
                continue
            before = deepcopy(stream)
            filtered = [task_id for task_id in task_ids if str(task_id).strip() not in removed_ids]
            if filtered != task_ids:
                stream["task_ids"] = filtered
                stream["updated_at"] = migrated_at
                counts["stream_task_refs_pruned"] += 1
                changes.append(_change_record(str(stream.get("id", "")).strip(), before, deepcopy(stream)))

    recompute_states(board)
    append_event(
        board,
        "planner_control_plane_normalization",
        {
            "at": migrated_at,
            "legacy_planner_tasks_removed": str(counts["legacy_planner_tasks_removed"]),
            "task_states_normalized": str(counts["task_states_normalized"]),
            "task_dependencies_pruned": str(counts["task_dependencies_pruned"]),
            "stream_task_refs_pruned": str(counts["stream_task_refs_pruned"]),
        },
    )
    return counts, changes


def migrate_queue(queue: dict[str, Any], migrated_at: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = {"queue_states_normalized": 0}
    changes: list[dict[str, Any]] = []
    for item in queue.get("items", []):
        if not isinstance(item, dict) or not is_open_queue_item(item):
            continue
        before = _queue_snapshot(item)
        state = normalize_state(item.get("state"))
        if state and state != str(item.get("state", "")).strip().upper():
            item["state"] = state
            item["updated_at"] = migrated_at
            counts["queue_states_normalized"] += 1
            changes.append(_change_record(str(item.get("id", "")).strip(), before, _queue_snapshot(item)))
    return counts, changes


def build_report(
    *,
    mode: str,
    board_path: Path,
    queue_path: Path,
    migrated_at: str,
    board_before: dict[str, Any],
    board_after: dict[str, Any],
    queue_before: dict[str, Any],
    queue_after: dict[str, Any],
    board_counts: dict[str, int],
    queue_counts: dict[str, int],
    task_changes: list[dict[str, Any]],
    queue_changes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "report_kind": "planner_control_plane_normalization",
        "mode": mode,
        "at": migrated_at,
        "board_path": display_path(board_path),
        "queue_path": display_path(queue_path),
        "counts": {
            **board_counts,
            **queue_counts,
            "task_changes": len(task_changes),
            "queue_changes": len(queue_changes),
        },
        "before": {
            "board_state_counts": summarize_board(board_before),
            "queue_state_counts": summarize_queue(queue_before),
        },
        "after": {
            "board_state_counts": summarize_board(board_after),
            "queue_state_counts": summarize_queue(queue_after),
        },
        "task_changes": task_changes,
        "queue_changes": queue_changes,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def apply_migration(board_path: Path, queue_path: Path, report_path: Path, dry_run: bool) -> int:
    migrated_at = now_iso()
    with board_lock(board_path, write=not dry_run):
        board = load_board(board_path)
        queue = load_queue(queue_path)
        board_before = deepcopy(board)
        queue_before = deepcopy(queue)

        board_counts, task_changes = migrate_board(board, migrated_at)
        queue_counts, queue_changes = migrate_queue(queue, migrated_at)
        report = build_report(
            mode="dry_run" if dry_run else "apply",
            board_path=board_path,
            queue_path=queue_path,
            migrated_at=migrated_at,
            board_before=board_before,
            board_after=board,
            queue_before=queue_before,
            queue_after=queue,
            board_counts=board_counts,
            queue_counts=queue_counts,
            task_changes=task_changes,
            queue_changes=queue_changes,
        )
        write_report(report_path, report)

        if not dry_run:
            save_board(board_path, board)
            save_queue(queue_path, queue)

    print(json.dumps({"ok": True, "mode": report["mode"], "report": display_path(report_path), "counts": report["counts"]}, ensure_ascii=True))
    return 0


def rollback_migration(board_path: Path, queue_path: Path, report_path: Path) -> int:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise SystemExit(f"REPORT_SCHEMA_ERROR: {report_path}")

    task_changes = report.get("task_changes", [])
    queue_changes = report.get("queue_changes", [])
    if not isinstance(task_changes, list) or not isinstance(queue_changes, list):
        raise SystemExit(f"REPORT_SCHEMA_ERROR: missing changes arrays in {report_path}")

    with board_lock(board_path, write=True):
        board = load_board(board_path)
        queue = load_queue(queue_path)

        tasks_by_id = {str(task.get("id", "")).strip(): task for task in board.get("tasks", []) if isinstance(task, dict)}
        for change in task_changes:
            if not isinstance(change, dict):
                continue
            before = change.get("before") if isinstance(change.get("before"), dict) else None
            after = change.get("after") if isinstance(change.get("after"), dict) else None
            item_id = str(change.get("id", "")).strip()
            if not item_id or before is None:
                continue
            if after is None:
                if item_id not in tasks_by_id:
                    board.setdefault("tasks", []).append(deepcopy(before))
                    tasks_by_id[item_id] = board["tasks"][-1]
                continue
            target = tasks_by_id.get(item_id)
            if target is None:
                board.setdefault("tasks", []).append(deepcopy(before))
                tasks_by_id[item_id] = board["tasks"][-1]
                continue
            target.clear()
            target.update(deepcopy(before))

        queue_by_id = {str(item.get("id", "")).strip(): item for item in queue.get("items", []) if isinstance(item, dict)}
        for change in queue_changes:
            if not isinstance(change, dict):
                continue
            before = change.get("before") if isinstance(change.get("before"), dict) else None
            item_id = str(change.get("id", "")).strip()
            if not item_id or before is None:
                continue
            target = queue_by_id.get(item_id)
            if target is None:
                queue.setdefault("items", []).append(deepcopy(before))
                continue
            target.clear()
            target.update(deepcopy(before))

        recompute_states(board)
        append_event(board, "planner_control_plane_normalization_rollback", {"at": now_iso(), "report": display_path(report_path)})
        save_board(board_path, board)
        save_queue(queue_path, queue)

    print(json.dumps({"ok": True, "mode": "rollback", "report": display_path(report_path)}, ensure_ascii=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize queue/workboard away from planner-worker legacy")
    parser.add_argument("--board", default=str(DEFAULT_BOARD_PATH))
    parser.add_argument("--queue", default=str(DEFAULT_QUEUE_PATH))
    parser.add_argument("--report", default="")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    board_path = Path(args.board).expanduser().resolve()
    queue_path = Path(args.queue).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve() if args.report else report_path_for(ROOT, "rollback" if args.rollback else ("apply" if args.apply else "dry-run"))

    if args.rollback:
        if not report_path.exists():
            raise SystemExit(f"REPORT_MISSING: {report_path}")
        return rollback_migration(board_path, queue_path, report_path)

    return apply_migration(board_path, queue_path, report_path, dry_run=not args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
