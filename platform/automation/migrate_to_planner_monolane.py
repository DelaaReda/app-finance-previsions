#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parallel_workstream import (
    ADMIN_GROUP_ROLES,
    DEV_GROUP_ROLES,
    PLANNER_GROUP_ROLES,
    STATE_BLOCKED,
    STATE_DONE,
    STATE_IN_PROGRESS,
    STATE_READY,
    STATE_READY_DEV,
    STATE_READY_PLANNER,
    STATE_REVIEW,
    append_event,
    board_lock,
    load_board,
    recompute_states,
    save_board,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOARD_PATH = ROOT / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
DEFAULT_QUEUE_PATH = ROOT / "docs" / "operations" / "orchestrator" / "priority-queue.json"
DEFAULT_REPORT_DIR = ROOT / "evidence" / "runtime-gates"
ROLE_CANONICAL_TARGETS = {"planner", "dev", "admin", "scrum_master"}
OPEN_QUEUE_STATES = {"BACKLOG", "PLANNED", "WAITING_DEP", "READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW", "BLOCKED"}
OPEN_TASK_STATES = {"BACKLOG", "WAITING_DEP", "READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW", "BLOCKED"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_role(value: Any) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if not token:
        return ""
    if token in PLANNER_GROUP_ROLES:
        return "planner"
    if token in DEV_GROUP_ROLES:
        return "dev"
    if token in ADMIN_GROUP_ROLES:
        return "admin"
    if token in {"scrum_master", "po_scrum_master", "scrum"}:
        return "scrum_master"
    return token if token in ROLE_CANONICAL_TARGETS else ""


def normalize_state(value: Any) -> str:
    token = str(value or "").strip().upper()
    if token in {"READY", "READY_PLANNER"}:
        return STATE_READY
    if token == "READY_DEV":
        return STATE_READY_DEV
    if token == "CLOSED":
        return STATE_DONE
    return token


def is_open_task(task: dict[str, Any]) -> bool:
    return normalize_state(task.get("state")) in OPEN_TASK_STATES


def is_open_queue_item(item: dict[str, Any]) -> bool:
    return normalize_state(item.get("state")) in OPEN_QUEUE_STATES


def target_subagent_role(original_role: str) -> str:
    if original_role in {"dev", "admin", "scrum_master"}:
        return original_role
    return ""


def report_path_for(root: Path, mode: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / "evidence" / "runtime-gates" / f"planner-monolane-migration-{mode}-{stamp}.json"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"items": [], "updated_at": now_iso()}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"QUEUE_SCHEMA_ERROR: {path} root must be object")
    items = payload.get("items")
    if not isinstance(items, list):
        payload["items"] = []
    return payload


def save_queue(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = now_iso()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


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
    meta = task.get("meta") if isinstance(task.get("meta"), dict) else {}
    return {
        "id": str(task.get("id", "")).strip(),
        "role": str(task.get("role", "")).strip(),
        "assignee": task.get("assignee", ""),
        "state": str(task.get("state", "")).strip(),
        "meta": deepcopy(meta),
    }


def _queue_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    return {
        "id": str(item.get("id", "")).strip(),
        "owner_role": str(item.get("owner_role", "")).strip(),
        "state": str(item.get("state", "")).strip(),
        "meta": deepcopy(meta),
    }


def migrate_board(board: dict[str, Any], migrated_at: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = {
        "tasks_role_reassigned": 0,
        "tasks_ready_normalized": 0,
        "tasks_requeued_from_active": 0,
        "tasks_assignee_cleared": 0,
        "tasks_target_preserved": 0,
    }
    changes: list[dict[str, Any]] = []

    for task in board.get("tasks", []):
        if not isinstance(task, dict) or not is_open_task(task):
            continue

        original = _task_snapshot(task)
        original_role = canonical_role(task.get("role") or task.get("assignee"))
        original_state = normalize_state(task.get("state"))
        meta = task.get("meta") if isinstance(task.get("meta"), dict) else {}
        migration_meta = meta.get("planner_monolane") if isinstance(meta.get("planner_monolane"), dict) else {}
        changed = False

        if original_role and original_role != "planner":
            task["role"] = "planner"
            counts["tasks_role_reassigned"] += 1
            changed = True
            target_role = target_subagent_role(original_role)
            if target_role and migration_meta.get("planner_subagent_target_role") != target_role:
                migration_meta["planner_subagent_target_role"] = target_role
                counts["tasks_target_preserved"] += 1

        if original_state in {STATE_READY_DEV, STATE_READY_PLANNER, STATE_READY}:
            if task.get("state") != STATE_READY:
                task["state"] = STATE_READY
                counts["tasks_ready_normalized"] += 1
                changed = True

        if original_role != "planner" and original_state in {STATE_IN_PROGRESS, STATE_REVIEW}:
            task["state"] = STATE_READY
            counts["tasks_requeued_from_active"] += 1
            changed = True

        assignee_role = canonical_role(task.get("assignee"))
        if assignee_role and assignee_role != "planner":
            task["assignee"] = ""
            counts["tasks_assignee_cleared"] += 1
            changed = True

        if changed:
            migration_meta["migrated_at"] = migrated_at
            migration_meta.setdefault("migrated_from_role", original_role or original["role"])
            migration_meta.setdefault("migrated_from_state", original["state"] or original_state)
            meta["planner_monolane"] = migration_meta
            task["meta"] = meta
            task["updated_at"] = migrated_at
            changes.append({"id": original["id"], "before": original, "after": _task_snapshot(task)})

    recompute_states(board)
    append_event(
        board,
        "planner_monolane_migration",
        {
            "at": migrated_at,
            "tasks_role_reassigned": str(counts["tasks_role_reassigned"]),
            "tasks_ready_normalized": str(counts["tasks_ready_normalized"]),
            "tasks_requeued_from_active": str(counts["tasks_requeued_from_active"]),
            "tasks_assignee_cleared": str(counts["tasks_assignee_cleared"]),
            "tasks_target_preserved": str(counts["tasks_target_preserved"]),
        },
    )
    return counts, changes


def migrate_queue(queue: dict[str, Any], migrated_at: str) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts = {
        "queue_owner_reassigned": 0,
        "queue_ready_normalized": 0,
        "queue_target_preserved": 0,
    }
    changes: list[dict[str, Any]] = []

    for item in queue.get("items", []):
        if not isinstance(item, dict) or not is_open_queue_item(item):
            continue

        original = _queue_snapshot(item)
        original_role = canonical_role(item.get("owner_role"))
        original_state = normalize_state(item.get("state"))
        meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
        migration_meta = meta.get("planner_monolane") if isinstance(meta.get("planner_monolane"), dict) else {}
        changed = False

        if original_role != "planner":
            item["owner_role"] = "planner"
            counts["queue_owner_reassigned"] += 1
            changed = True
            target_role = target_subagent_role(original_role)
            if target_role and migration_meta.get("planner_subagent_target_role") != target_role:
                migration_meta["planner_subagent_target_role"] = target_role
                counts["queue_target_preserved"] += 1

        if original_state in {STATE_READY_DEV, STATE_READY_PLANNER, STATE_READY}:
            if item.get("state") != STATE_READY:
                item["state"] = STATE_READY
                counts["queue_ready_normalized"] += 1
                changed = True

        if changed:
            migration_meta["migrated_at"] = migrated_at
            migration_meta.setdefault("migrated_from_role", original_role or original["owner_role"])
            migration_meta.setdefault("migrated_from_state", original["state"] or original_state)
            meta["planner_monolane"] = migration_meta
            item["meta"] = meta
            item["updated_at"] = migrated_at
            changes.append({"id": original["id"], "before": original, "after": _queue_snapshot(item)})

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
        "report_kind": "planner_monolane_migration",
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
            if not before:
                continue
            task_id = str(before.get("id", "")).strip()
            if not task_id:
                continue
            target = tasks_by_id.get(task_id)
            if target is None:
                board.setdefault("tasks", []).append(deepcopy(before))
                continue
            target.clear()
            target.update(deepcopy(before))

        queue_by_id = {str(item.get("id", "")).strip(): item for item in queue.get("items", []) if isinstance(item, dict)}
        for change in queue_changes:
            if not isinstance(change, dict):
                continue
            before = change.get("before") if isinstance(change.get("before"), dict) else None
            if not before:
                continue
            item_id = str(before.get("id", "")).strip()
            if not item_id:
                continue
            target = queue_by_id.get(item_id)
            if target is None:
                queue.setdefault("items", []).append(deepcopy(before))
                continue
            target.clear()
            target.update(deepcopy(before))

        recompute_states(board)
        append_event(board, "planner_monolane_migration_rollback", {"at": now_iso(), "report": display_path(report_path)})
        save_board(board_path, board)
        save_queue(queue_path, queue)

    print(json.dumps({"ok": True, "mode": "rollback", "report": display_path(report_path)}, ensure_ascii=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate queue/workboard to planner-owned mono-lane mode")
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
