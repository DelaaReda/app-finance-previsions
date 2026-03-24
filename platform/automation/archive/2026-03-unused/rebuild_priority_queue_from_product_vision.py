#!/usr/bin/env python3
"""Rebuild priority queue from PRODUCT_VISION using strict canonical order.

Rules:
- Preserve CLOSED/PASS/DONE batches.
- Promote the first non-closed canonical batch to READY.
- Set only its immediate successor to WAITING_DEP.
- Keep all subsequent batches as PLANNED.
- Park out-of-order active batches (e.g. BATCH-27 IN_PROGRESS -> PLANNED).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BATCH_ID_RE = re.compile(r"^BATCH-(\d{2})$")
VISION_HEADER_RE = re.compile(r"^###\s+.*?(BATCH-(\d{2}))\s*[—-]\s*(.+?)\s*(?:\(|$)")
TERMINAL_STATES = {"CLOSED", "DONE", "PASS"}
ACTIVE_STATES = {"IN_PROGRESS", "READY", "WAITING_DEP"}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def _state_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        token = str(item.get("state", "")).strip().upper() or "UNKNOWN"
        out[token] = out.get(token, 0) + 1
    return out


def parse_vision_batches(vision_path: Path) -> list[tuple[str, str]]:
    batches: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in vision_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = VISION_HEADER_RE.match(line.strip())
        if not m:
            continue
        batch_id = m.group(1).upper()
        title = " ".join(m.group(3).strip().split())
        if batch_id in seen:
            continue
        seen.add(batch_id)
        batches.append((batch_id, title))
    batches.sort(key=lambda x: int(x[0].split("-")[1]))
    return batches


def rebuild_queue(
    queue_obj: dict[str, Any],
    vision_batches: list[tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[str], list[str], str]:
    existing_items = [i for i in queue_obj.get("items", []) if isinstance(i, dict)]
    existing_by_id = {str(i.get("id", "")).strip().upper(): i for i in existing_items}

    closed_batches = {
        batch_id
        for batch_id, _ in vision_batches
        if str(existing_by_id.get(batch_id, {}).get("state", "")).strip().upper() in TERMINAL_STATES
    }

    first_open_index = -1
    for idx, (batch_id, _title) in enumerate(vision_batches):
        if batch_id not in closed_batches:
            first_open_index = idx
            break

    first_open_batch = vision_batches[first_open_index][0] if first_open_index >= 0 else ""
    waiting_batch = vision_batches[first_open_index + 1][0] if first_open_index >= 0 and first_open_index + 1 < len(vision_batches) else ""

    now = now_iso()
    rebuilt: list[dict[str, Any]] = []
    parked_batches: list[str] = []
    planned_batches: list[str] = []

    for idx, (batch_id, title) in enumerate(vision_batches):
        existing = existing_by_id.get(batch_id, {})
        prev_batch = vision_batches[idx - 1][0] if idx > 0 else ""
        depends_on = [prev_batch] if prev_batch else []

        existing_state = str(existing.get("state", "")).strip().upper()
        if batch_id in closed_batches:
            new_state = "CLOSED"
        elif batch_id == first_open_batch:
            new_state = "READY"
        elif batch_id == waiting_batch:
            new_state = "WAITING_DEP"
        else:
            new_state = "PLANNED"

        item = dict(existing)
        item["id"] = batch_id
        item["title"] = title or str(existing.get("title", batch_id))
        item["state"] = new_state
        item["depends_on"] = depends_on
        item["updated_at"] = now
        item["created_at"] = str(existing.get("created_at", now))
        item["priority"] = str(existing.get("priority", "P2")).strip().upper() or "P2"

        if new_state == "READY":
            item["dispatch_authorized"] = True
            item["ready_at"] = str(existing.get("ready_at", now))
        else:
            item.pop("dispatch_authorized", None)
            if new_state != "WAITING_DEP":
                item.pop("ready_at", None)

        if new_state == "CLOSED":
            item["closed_at"] = str(existing.get("closed_at", now))

        if new_state == "PLANNED":
            planned_batches.append(batch_id)
        if existing_state in ACTIVE_STATES and new_state == "PLANNED":
            item["parked_by_rebuild"] = True
            item["parked_reason"] = "strict_order_rebuild"
            item["parked_at"] = now
            item["origin_state"] = existing_state
            parked_batches.append(batch_id)

        rebuilt.append(item)

    # Preserve non-canonical queue items (non BATCH-XX) without modification.
    for existing in existing_items:
        bid = str(existing.get("id", "")).strip().upper()
        if not BATCH_ID_RE.fullmatch(bid):
            rebuilt.append(existing)

    return rebuilt, sorted(set(parked_batches)), sorted(set(planned_batches)), first_open_batch


def sync_workboard_for_planned(workboard_obj: dict[str, Any], planned_batches: list[str], parked_batches: list[str]) -> tuple[int, int]:
    planned_set = set(planned_batches)
    parked_set = set(parked_batches)
    if not planned_set:
        return 0, 0

    now = now_iso()
    streams_updated = 0
    tasks_updated = 0

    for stream in workboard_obj.get("streams", []):
        if not isinstance(stream, dict):
            continue
        sid = str(stream.get("id", "")).strip().upper()
        if sid not in planned_set:
            continue
        state = str(stream.get("state", "")).strip().upper()
        if state not in {"DONE", "CLOSED"}:
            stream["state"] = "WAITING_DEP"
            stream["updated_at"] = now
            stream["parked_by_rebuild"] = True
            stream["parked_reason"] = "strict_order_rebuild"
            stream["parked_at"] = now
            stream["parked_from_state"] = state or "UNKNOWN"
            streams_updated += 1

    for task in workboard_obj.get("tasks", []):
        if not isinstance(task, dict):
            continue
        sid = str(task.get("stream_id", "")).strip().upper()
        if sid not in planned_set:
            continue
        state = str(task.get("state", "")).strip().upper()
        if state not in {"DONE", "CLOSED", "PASS"}:
            task["state"] = "WAITING_DEP"
            task["updated_at"] = now
            task["parked_by_rebuild"] = True
            task["parked_reason"] = "strict_order_rebuild"
            task["parked_at"] = now
            task["parked_from_state"] = state or "UNKNOWN"
            task["assignee"] = ""
            tasks_updated += 1

    if streams_updated or tasks_updated:
        workboard_obj.setdefault("events", []).append(
            {
                "at": now,
                "kind": "strict_order_queue_rebuild",
                "details": {
                    "planned_batches": sorted(planned_set),
                    "parked_batches": sorted(parked_set),
                    "streams_updated": str(streams_updated),
                    "tasks_updated": str(tasks_updated),
                },
            }
        )
        workboard_obj["updated_at"] = now

    return streams_updated, tasks_updated


def main(argv: list[str] | None = None) -> int:
    raise SystemExit(
        "DEPRECATED: rebuild_priority_queue_from_product_vision.py is non-canonical. "
        "Planning truth = Plane sync; runtime truth = SQLite plus logs-codex-runs/orchestrator-state projections."
    )
    parser = argparse.ArgumentParser(description="Rebuild priority queue from PRODUCT_VISION.")
    parser.add_argument("--vision", default="docs/product/planning/PRODUCT_VISION.md")
    parser.add_argument("--queue", default="logs-codex-runs/orchestrator-state/priority-queue.json")
    parser.add_argument("--workboard", default="logs-codex-runs/orchestrator-state/parallel-workstreams.json")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    vision_path = Path(args.vision)
    queue_path = Path(args.queue)
    workboard_path = Path(args.workboard)

    if not vision_path.exists():
        raise SystemExit(f"VISION_MISSING: {vision_path}")
    if not queue_path.exists():
        raise SystemExit(f"QUEUE_MISSING: {queue_path}")
    if not workboard_path.exists():
        raise SystemExit(f"WORKBOARD_MISSING: {workboard_path}")

    vision_batches = parse_vision_batches(vision_path)
    if not vision_batches:
        raise SystemExit("VISION_PARSE_EMPTY: no BATCH-XX headings found")

    queue_obj = _read_json(queue_path)
    workboard_obj = _read_json(workboard_path)
    if not isinstance(queue_obj, dict):
        queue_obj = {}
    if not isinstance(workboard_obj, dict):
        workboard_obj = {}

    before_items = [i for i in queue_obj.get("items", []) if isinstance(i, dict)]
    before_counts = _state_counts(before_items)

    rebuilt_items, parked_batches, planned_batches, first_open_batch = rebuild_queue(queue_obj, vision_batches)
    queue_obj["items"] = rebuilt_items
    queue_obj["updated_at"] = now_iso()
    queue_obj.setdefault("meta", {})
    if isinstance(queue_obj["meta"], dict):
        queue_obj["meta"]["strict_order_rebuild"] = {
            "at": now_iso(),
            "source": str(vision_path),
            "parked_batches": parked_batches,
            "first_open_batch": first_open_batch,
        }

    streams_updated, tasks_updated = sync_workboard_for_planned(workboard_obj, planned_batches, parked_batches)

    after_counts = _state_counts([i for i in queue_obj.get("items", []) if isinstance(i, dict)])
    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "vision": str(vision_path),
        "queue": str(queue_path),
        "workboard": str(workboard_path),
        "first_open_batch": first_open_batch,
        "parked_batches": parked_batches,
        "workboard_streams_updated": streams_updated,
        "workboard_tasks_updated": tasks_updated,
        "before": before_counts,
        "after": after_counts,
    }

    if args.apply:
        queue_path.write_text(json.dumps(queue_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        workboard_path.write_text(json.dumps(workboard_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
