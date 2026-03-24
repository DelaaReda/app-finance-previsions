#!/usr/bin/env python3
"""Detect and remediate stale IN_PROGRESS tasks in the parallel workboard.

Default mode is dry-run. Use --apply to persist changes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import compat.projections.parallel_workstream as pw


def parse_utc(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def state_after_reclaim(task: dict, tasks_by_id: Dict[str, dict]) -> str:
    deps = [str(dep) for dep in task.get("depends_on", []) if str(dep).strip()]
    if not deps:
        return pw.STATE_READY
    all_done = all(str(tasks_by_id.get(dep, {}).get("state", "")) == pw.STATE_DONE for dep in deps)
    return pw.STATE_READY if all_done else pw.STATE_WAITING_DEP


def remediation_line(task: dict, age_s: int, action: str, target_state: str) -> str:
    return (
        "STALE_SWEEP:"
        f"at={pw.now_iso()};task={task.get('id')};"
        f"age_s={age_s};action={action};to_state={target_state}"
    )


def run(args: argparse.Namespace) -> int:
    board_path = Path(args.board)
    threshold = max(1, int(args.threshold_seconds))
    mode = str(args.mode).strip().lower()
    role_filter = str(args.role or "").strip()
    apply_changes = bool(args.apply)

    if mode not in {"reclaim", "block"}:
        raise SystemExit(f"MODE_INVALID: {mode} (allowed: reclaim|block)")

    with pw.board_lock(board_path):
        board = pw.load_board(board_path)
        pw.recompute_states(board)
        tasks_by_id = pw.task_index(board)
        now = now_utc()

        matched = 0
        stale = 0
        changed = 0
        skipped_missing_time = 0
        changed_ids: List[str] = []

        for task in board.get("tasks", []):
            if str(task.get("state", "")) != pw.STATE_IN_PROGRESS:
                continue
            role = str(task.get("role", ""))
            if role_filter and role != role_filter:
                continue
            matched += 1

            ref = (
                parse_utc(str(task.get("last_delivery_delta_at", "")))
                or parse_utc(str(task.get("last_delivery_at", "")))
                or parse_utc(str(task.get("last_artifact_at", "")))
                or parse_utc(str(task.get("last_code_delta_at", "")))
                or parse_utc(str(task.get("last_test_delta_at", "")))
                or parse_utc(str(task.get("last_verify_delta_at", "")))
                or parse_utc(str(task.get("started_at", "")))
                or parse_utc(str(task.get("claimed_at", "")))
                or parse_utc(str(task.get("created_at", "")))
                or parse_utc(str(task.get("updated_at", "")))
            )
            if ref is None:
                skipped_missing_time += 1
                print(f"STALE_TASK task={task.get('id')} role={role} age_s=unknown stale=0 action=skip_missing_time")
                continue

            age_s = int((now - ref).total_seconds())
            if age_s <= threshold:
                print(f"STALE_TASK task={task.get('id')} role={role} age_s={age_s} stale=0 action=none")
                continue

            stale += 1
            if mode == "reclaim":
                target_state = state_after_reclaim(task, tasks_by_id)
                action = "reclaim"
            else:
                target_state = pw.STATE_BLOCKED
                action = "block"

            print(
                "STALE_TASK "
                f"task={task.get('id')} role={role} age_s={age_s} stale=1 "
                f"action={action} target_state={target_state}"
            )

            if not apply_changes:
                continue

            prev_state = str(task.get("state", ""))
            task["state"] = target_state
            task["updated_at"] = pw.now_iso()
            task["assignee"] = ""
            if action == "reclaim":
                task["blocked_reason"] = ""
                task["stalled_reason"] = "stalled_delivery"
                task["delivery_stalled_at"] = pw.now_iso()
                task["started_at"] = ""
            else:
                task["blocked_reason"] = f"stalled_delivery_age_exceeded:{age_s}s"
                task["stalled_reason"] = "stalled_delivery"
                task["delivery_stalled_at"] = pw.now_iso()
            task.setdefault("notes", []).append(remediation_line(task, age_s, action, target_state))

            pw.append_event(
                board,
                "stale_task_sweep",
                {
                    "task_id": str(task.get("id", "")),
                    "role": role,
                    "age_seconds": age_s,
                    "from_state": prev_state,
                    "to_state": target_state,
                    "mode": action,
                },
            )
            changed += 1
            changed_ids.append(str(task.get("id", "")))

        if apply_changes and changed > 0:
            pw.recompute_states(board)
            pw.save_board(board_path, board)

        print(
            "STALE_TASK_SUMMARY "
            f"board={board_path} "
            f"matched={matched} "
            f"stale={stale} "
            f"changed={changed} "
            f"skipped_missing_time={skipped_missing_time} "
            f"threshold_s={threshold} "
            f"mode={mode} "
            f"apply={1 if apply_changes else 0} "
            f"changed_ids={','.join(changed_ids) if changed_ids else 'none'}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stale IN_PROGRESS sweep for parallel workboard")
    parser.add_argument("--board", default=str(pw.DEFAULT_BOARD), help="Path to workboard JSON")
    parser.add_argument("--threshold-seconds", type=int, default=14400, help="Mark stale above this age (seconds)")
    parser.add_argument("--mode", default="reclaim", choices=["reclaim", "block"], help="How to remediate stale tasks")
    parser.add_argument("--role", default="", help="Optional role filter")
    parser.add_argument("--apply", action="store_true", help="Persist changes")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
