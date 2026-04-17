#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path
from runtime.truth.dispatch_snapshot import build_stable_planner_dispatch_snapshot
from runtime.truth.runtime_truth_reader import (
    build_runtime_truth_snapshot,
    load_product_delivery_state,
    product_delivery_state_path,
)


DONE_STATES = {"DONE", "CLOSED", "PASS", "MERGED", "COMPLETED", "SUCCESS", "OK", "CANCELLED", "CANCELED"}
ACTIVE_SUBAGENT_TERMINAL = {"done", "completed", "failed", "cancelled", "canceled", "closed", "merged", "none"}
CAPABILITY_ROLES = {"dev", "admin", "scrum_master"}


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_first(root: Path, candidates: list[str]) -> Path | None:
    for rel in candidates:
        path = root / rel
        if path.exists():
            return path
    return None


def _state_age_s(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    return max(0, int(time.time()) - int(path.stat().st_mtime))


def _iso_age_s(raw: Any) -> int | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()))


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tokens: list[str] = []
    for item in value:
        token = str(item or "").strip()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _normalize_active_cycle(payload: dict[str, Any]) -> dict[str, Any]:
    active_cycle = payload.get("active_cycle")
    if not isinstance(active_cycle, dict):
        return {}
    return {
        "cycle_id": str(active_cycle.get("cycle_id") or "").strip(),
        "doc_ref": str(active_cycle.get("doc_ref") or "").strip(),
        "dispatch_namespace": str(active_cycle.get("dispatch_namespace") or "").strip().upper(),
        "active_batch_ids": _normalize_string_list(active_cycle.get("active_batch_ids")),
        "recent_completed_batch_ids": _normalize_string_list(active_cycle.get("recent_completed_batch_ids")),
    }


def _payload_open_batch_ids(payload: dict[str, Any]) -> set[str]:
    if not isinstance(payload, dict):
        return set()
    closed_states = {"DONE", "CLOSED", "CANCELLED", "ARCHIVED"}
    open_ids: set[str] = set()

    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "")).strip().upper()
        if state in closed_states:
            continue
        batch_id = str(item.get("batch_id") or item.get("id") or "").strip().upper()
        if batch_id:
            open_ids.add(batch_id)

    for stream in payload.get("streams", []):
        if not isinstance(stream, dict):
            continue
        state = str(stream.get("state", "")).strip().upper()
        if state in closed_states:
            continue
        batch_id = str(stream.get("stream_id") or stream.get("batch_id") or stream.get("id") or "").strip().upper()
        if batch_id:
            open_ids.add(batch_id)

    for task in payload.get("tasks", []):
        if not isinstance(task, dict):
            continue
        state = str(task.get("state", "")).strip().upper()
        if state in closed_states:
            continue
        batch_id = str(task.get("stream_id") or task.get("batch_id") or "").strip().upper()
        if batch_id:
            open_ids.add(batch_id)

    return open_ids


def _planning_alignment(
    root: Path,
    board_payload: dict[str, Any],
    queue_payload: dict[str, Any],
    board_active_cycle: dict[str, Any],
    queue_active_cycle: dict[str, Any],
) -> tuple[dict[str, Any], str, str]:
    if bool(board_active_cycle) != bool(queue_active_cycle):
        active_cycle = board_active_cycle or queue_active_cycle
        return active_cycle, "board_doc_mismatch", "board_queue_active_cycle_presence_mismatch"

    if board_active_cycle and queue_active_cycle and board_active_cycle != queue_active_cycle:
        return board_active_cycle, "board_doc_mismatch", "board_queue_active_cycle_mismatch"

    active_cycle = board_active_cycle or queue_active_cycle
    if not active_cycle:
        return {}, "board_doc_mismatch", "active_cycle_missing"

    doc_ref = str(active_cycle.get("doc_ref") or "").strip()
    if not doc_ref:
        return active_cycle, "stale_cycle_doc", "active_cycle_doc_ref_missing"
    if not (root / doc_ref).exists():
        return active_cycle, "stale_cycle_doc", "active_cycle_doc_ref_unreadable"

    dispatch_namespace = str(active_cycle.get("dispatch_namespace") or "").strip().upper()
    if dispatch_namespace != "BATCH":
        token = dispatch_namespace or "missing"
        return active_cycle, "namespace_drift", f"dispatch_namespace={token}"

    active_batch_ids = _normalize_string_list(active_cycle.get("active_batch_ids"))
    recent_completed_batch_ids = _normalize_string_list(active_cycle.get("recent_completed_batch_ids"))
    if not active_batch_ids:
        return active_cycle, "board_doc_mismatch", "active_batch_ids_missing"

    open_batch_ids = _payload_open_batch_ids(board_payload) | _payload_open_batch_ids(queue_payload)
    if open_batch_ids and not any(batch_id in open_batch_ids for batch_id in active_batch_ids):
        return {}, "stale_cycle_state", "active_batch_ids_not_open"

    prefix = f"{dispatch_namespace}-"
    all_batch_ids = active_batch_ids + recent_completed_batch_ids
    if any(not batch_id.startswith(prefix) for batch_id in all_batch_ids):
        return active_cycle, "namespace_drift", "active_cycle_batch_ids_cross_namespace"

    cycle_id = str(active_cycle.get("cycle_id") or "").strip() or "unknown_cycle"
    return active_cycle, "aligned", f"cycle={cycle_id};active_batch={active_batch_ids[0]}"


def _canonical_role(value: Any) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if token in {"po_scrum_master", "scrum"}:
        return "scrum_master"
    return token


def _detect_task_kind(task: dict[str, Any]) -> str:
    raw = str(task.get("task_kind") or task.get("kind") or task.get("type") or "").strip().upper()
    if raw:
        return raw
    task_id = str(task.get("id") or "").upper()
    for token in ("GOV_REVIEW", "PLAN", "ANALYSIS", "ARCH"):
        if token in task_id:
            return token
    return "PLANNER"


def _task_done(task: dict[str, Any] | None) -> bool:
    if not isinstance(task, dict):
        return False
    state = str(task.get("state") or "").strip().upper()
    if state in DONE_STATES:
        return True
    return bool(str(task.get("completed_at") or "").strip())


def _deps_satisfied(task: dict[str, Any], task_index: dict[str, dict[str, Any]]) -> bool:
    deps = task.get("depends_on") or []
    if not isinstance(deps, list):
        return True
    for dep in deps:
        dep_id = str(dep or "").strip()
        if not dep_id:
            continue
        if not _task_done(task_index.get(dep_id)):
            return False
    return True


def _extract_active_subagent_ids(payload: dict[str, Any]) -> list[str]:
    rows = payload.get("subagents") if isinstance(payload.get("subagents"), list) else []
    active_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or row.get("state") or row.get("lifecycle") or "").strip().lower()
        if status in ACTIVE_SUBAGENT_TERMINAL:
            continue
        ident = str(row.get("subagent_id") or row.get("id") or "").strip()
        if ident and ident not in active_ids:
            active_ids.append(ident)
    return active_ids


def _build_contract(board: dict[str, Any], task: dict[str, Any]) -> dict[str, str]:
    task_id = str(task.get("id") or "none")
    stream_id = str(task.get("stream_id") or "none")
    task_kind = _detect_task_kind(task)
    metadata = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
    depends_on = [str(dep).strip() for dep in task.get("depends_on") or [] if str(dep).strip()]
    index = {
        str(item.get("id") or ""): item
        for item in board.get("tasks", [])
        if isinstance(item, dict)
    }
    unresolved = [
        dep
        for dep in depends_on
        if str(index.get(dep, {}).get("state", "")).upper() != "DONE"
    ]
    explicit_target_raw = str(
        task.get("dispatch_target")
        or task.get("target_role")
        or metadata.get("dispatch_target")
        or metadata.get("target_role")
        or ""
    ).strip()
    explicit_target = _canonical_role(explicit_target_raw) if explicit_target_raw else ""
    dispatch_target = explicit_target if explicit_target in CAPABILITY_ROLES else ""
    if not dispatch_target:
        pending_roles: list[str] = []
        for candidate in board.get("tasks", []):
            if not isinstance(candidate, dict):
                continue
            if str(candidate.get("stream_id") or "") != stream_id:
                continue
            candidate_id = str(candidate.get("id") or "").strip()
            if not candidate_id or candidate_id == task_id:
                continue
            role = _canonical_role(candidate.get("role"))
            if role not in CAPABILITY_ROLES:
                continue
            if _task_done(candidate):
                continue
            if role not in pending_roles:
                pending_roles.append(role)
        if task_kind != "GOV_REVIEW":
            if pending_roles:
                dispatch_target = pending_roles[0]
            elif task_kind in {"PLAN", "ANALYSIS", "ARCH"}:
                dispatch_target = "dev"
    explicit_dispatch_kind = str(
        task.get("dispatch_task_kind") or metadata.get("dispatch_task_kind") or ""
    ).strip().lower()
    if explicit_dispatch_kind:
        dispatch_task_kind = explicit_dispatch_kind
    elif dispatch_target == "dev":
        dispatch_task_kind = "delivery" if task_kind in {"PLAN", "ANALYSIS", "ARCH"} else "implementation"
    elif dispatch_target == "admin":
        dispatch_task_kind = "runtime" if task_kind in {"PLAN", "ANALYSIS", "ARCH"} else "repair"
    elif dispatch_target == "scrum_master":
        dispatch_task_kind = "coordination"
    else:
        dispatch_task_kind = "none"
    if unresolved:
        suggested_next = "repair"
    elif dispatch_target != "none":
        suggested_next = "run"
    else:
        suggested_next = "complete"
    artifact_path = str(
        task.get("complete_artifact")
        or task.get("artifact_path")
        or task.get("artifact")
        or metadata.get("complete_artifact")
        or metadata.get("artifact_path")
        or f"docs/operations/orchestrator/proofs/{stream_id}/{task_id}.md"
    ).strip()
    return {
        "task_id": task_id,
        "stream_id": stream_id,
        "task_kind": task_kind,
        "dispatch_target": dispatch_target or "none",
        "dispatch_task_kind": dispatch_task_kind,
        "artifact_path": artifact_path,
        "suggested_next": suggested_next,
    }


def snapshot(root: Path, *, persist_delivery_state: bool = False) -> dict[str, Any]:
    queue_path = resolve_orchestrator_read_path(root, "priority-queue.json")
    board_path = resolve_orchestrator_read_path(root, "parallel-workstreams.json")
    queue = _read_json(queue_path)
    board = _read_json(board_path)
    queue_meta = queue.get("meta", {}) if isinstance(queue.get("meta"), dict) else {}
    board_meta = board.get("meta", {}) if isinstance(board.get("meta"), dict) else {}
    runtime_truth = build_runtime_truth_snapshot(
        root,
        state_limit=64,
        event_limit=64,
        persist_delivery_state=persist_delivery_state,
    )
    dispatch_snapshot = build_stable_planner_dispatch_snapshot(root, recent_limit=8)
    event_store_primary = bool(runtime_truth.get("event_store_primary", False))
    runtime_truth_source = str(runtime_truth.get("runtime_truth_source", "sqlite" if event_store_primary else "fallback"))
    registry_path: Path | None = None
    events_path: Path | None = None
    worker_registry_path: Path | None = None
    board_active_cycle = _normalize_active_cycle(board)
    queue_active_cycle = _normalize_active_cycle(queue)
    active_cycle, planning_alignment_status, planning_alignment_reason = _planning_alignment(
        root,
        board,
        queue,
        board_active_cycle,
        queue_active_cycle,
    )
    delivery_state = load_product_delivery_state(root)
    if not isinstance(delivery_state, dict) or not delivery_state:
        delivery_state = (
            runtime_truth.get("product_delivery_state", {})
            if isinstance(runtime_truth.get("product_delivery_state"), dict)
            else {}
        )
    delivery_active_batch_id = str(delivery_state.get("active_batch_id") or "").strip().upper()
    delivery_phase = str(delivery_state.get("phase") or "").strip()
    normalized_active_cycle = dict(active_cycle) if isinstance(active_cycle, dict) else {}
    if delivery_active_batch_id:
        normalized_active_cycle["active_batch_ids"] = [delivery_active_batch_id]
        active_cycle = normalized_active_cycle
        if planning_alignment_status == "aligned":
            planning_alignment_reason = f"runtime_truth_active_batch={delivery_active_batch_id}"
    elif delivery_phase in {"product_done_ops_dirty", "idle_ready_for_next_batch"}:
        normalized_active_cycle["active_batch_ids"] = []
        active_cycle = normalized_active_cycle
        planning_alignment_status = "runtime_truth_idle"
        planning_alignment_reason = (
            "delivery_state_product_done_ops_dirty"
            if delivery_phase == "product_done_ops_dirty"
            else "delivery_state_idle_ready_for_next_batch"
        )
    active_cycle_ids = {str(batch_id).strip().upper() for batch_id in active_cycle.get("active_batch_ids", []) if str(batch_id).strip()}
    planner_hard_guard = queue_meta.get("planner_hard_guard", {}) if isinstance(queue_meta.get("planner_hard_guard"), dict) else {}
    novelty_target_workflow = queue_meta.get("novelty_target_workflow", {}) if isinstance(queue_meta.get("novelty_target_workflow"), dict) else {}
    workboard_decision_capable = board_meta.get("decision_capable")
    if workboard_decision_capable is None:
        workboard_decision_capable = queue_meta.get("workboard_decision_capable")
    workboard_decision_reason = str(
        board_meta.get("decision_capability_reason")
        or queue_meta.get("workboard_decision_capability_reason")
        or ""
    ).strip()
    tasks = board.get("tasks") if isinstance(board.get("tasks"), list) else []
    index = {
        str(task.get("id") or "").strip(): task
        for task in tasks
        if isinstance(task, dict) and str(task.get("id") or "").strip()
    }

    planner_tasks = [
        task for task in tasks
        if isinstance(task, dict) and _canonical_role(task.get("role")) == "planner"
    ]
    active_planner_tasks = [
        task for task in planner_tasks
        if str(task.get("state") or "").strip().upper() in {"IN_PROGRESS", "REVIEW"}
    ]
    active_task = next(
        (
            task for task in active_planner_tasks
            if _detect_task_kind(task) in {"GOV_REVIEW", "PLAN", "ANALYSIS", "ARCH"}
        ),
        active_planner_tasks[0] if active_planner_tasks else None,
    )
    active_canonical_tasks = [
        task for task in tasks
        if isinstance(task, dict)
        and not _task_done(task)
        and (not active_cycle_ids or str(task.get("stream_id") or task.get("batch_id") or "").strip().upper() in active_cycle_ids)
        and str(task.get("state") or "").strip().upper() in {"IN_PROGRESS", "REVIEW", "BLOCKED"}
    ]
    active_canonical_task = next(
        (
            task for task in active_canonical_tasks
            if _canonical_role(task.get("role")) in CAPABILITY_ROLES
        ),
        active_canonical_tasks[0] if active_canonical_tasks else None,
    )
    ready_planner_tasks = [
        task for task in planner_tasks
        if str(task.get("state") or "").strip().upper() in {"PLANNED", "READY", "READY_PLANNER"}
    ]
    ready_task = ready_planner_tasks[0] if ready_planner_tasks else None

    ready_dev_count = 0
    ready_planner_count = len(ready_planner_tasks)
    ready_admin_count = 0
    ready_scrum_count = 0
    runnable_task_ids: list[str] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id") or "").strip()
        if not task_id or _task_done(task):
            continue
        role = _canonical_role(task.get("role"))
        state = str(task.get("state") or "").strip().upper()
        if role == "dev" and state in {"READY_DEV", "READY"} and _deps_satisfied(task, index):
            ready_dev_count += 1
        elif role == "admin" and state in {"PLANNED", "READY"} and _deps_satisfied(task, index):
            ready_admin_count += 1
        elif role == "scrum_master" and state in {"PLANNED", "READY"} and _deps_satisfied(task, index):
            ready_scrum_count += 1
        if role not in {"planner", "dev", "admin", "scrum_master"}:
            continue
        if state not in {"PLANNED", "READY", "READY_DEV", "IN_PROGRESS"}:
            continue
        if not _deps_satisfied(task, index):
            continue
        runnable_task_ids.append(task_id)

    runtime_states = runtime_truth.get("latest_states", []) if isinstance(runtime_truth.get("latest_states"), list) else []
    dispatch_active_rows = dispatch_snapshot.get("active", []) if isinstance(dispatch_snapshot.get("active"), list) else []
    planner_graph_active = (
        dispatch_snapshot.get("planner_graph_active", [])
        if isinstance(dispatch_snapshot.get("planner_graph_active"), list)
        else []
    )
    active_subagent_ids = []
    for row in dispatch_active_rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "")).strip().lower()
        ident = str(row.get("subagent_id", "")).strip()
        if status in {"running", "pending"} and ident and ident not in active_subagent_ids:
            active_subagent_ids.append(ident)
    subagent_progress_age_candidates = [
        age
        for age in (_iso_age_s(row.get("last_update_at") or row.get("updated_at")) for row in dispatch_active_rows if isinstance(row, dict))
        if age is not None
    ]
    subagent_progress_age = min(subagent_progress_age_candidates) if subagent_progress_age_candidates else -1

    qa_collect_pending_compat = False
    subagent_collect_pending_compat = False
    subagent_collect_pending_runtime = any(
        str(row.get("status", "")).strip().lower() == "ready_to_merge"
        for row in planner_graph_active
        if isinstance(row, dict)
    )
    qa_collect_pending = False
    subagent_collect_pending = subagent_collect_pending_runtime

    if not novelty_target_workflow and bool(planner_hard_guard.get("active")):
        hard_guard_reason = str(planner_hard_guard.get("reason") or "").strip().lower()
        stagnation_alert = queue_meta.get("stagnation_alert", {}) if isinstance(queue_meta.get("stagnation_alert"), dict) else {}
        if hard_guard_reason == "stagnation_requires_novelty_target":
            novelty_target_workflow = {
                "status": "required",
                "owner_role": "planner",
                "batch_id": str(stagnation_alert.get("batch_id") or "").strip().upper(),
                "scope_key": str(stagnation_alert.get("scope_key") or "").strip().lower(),
                "reason": hard_guard_reason,
                "next_action": "define_novelty_target",
                "policy": "no_new_downstream_work",
                "required_fields": [
                    "novelty_target",
                    "user_value_delta",
                    "scope_delta",
                    "success_metric",
                ],
                "clear_when": "novelty_target_present",
                "recent_classes": [
                    str(item).strip().lower()
                    for item in (stagnation_alert.get("recent_classes") or [])
                    if str(item).strip()
                ],
            }

    next_action = "none"
    if bool(planner_hard_guard.get("active")):
        next_action = str(novelty_target_workflow.get("next_action") or "define_novelty_target").strip().lower() or "define_novelty_target"
    elif isinstance(active_canonical_task, dict):
        active_task_id = str(active_canonical_task.get("id") or "").strip()
        next_action = (f"advance {active_task_id}" if active_task_id else "advance_active_cycle_task").lower()
    elif qa_collect_pending:
        next_action = "collect_qa_results"
    elif subagent_collect_pending:
        next_action = "collect_subagent_results"
    elif runnable_task_ids:
        next_action = f"unblock {runnable_task_ids[0]}".lower()

    return {
        "queue_file": str(queue_path) if queue_path else "none",
        "workboard_file": str(board_path) if board_path else "none",
        "registry_file": "secondary_compat_only",
        "events_file": "secondary_compat_only",
        "worker_registry_file": "secondary_compat_only",
        "delivery_state_file": str(product_delivery_state_path(root)),
        "runtime_truth_source": runtime_truth_source,
        "primary_source": str(runtime_truth.get("source", "event_store" if event_store_primary else "projection_fallback")),
        "event_store_primary": event_store_primary,
        "legacy_registry_secondary_only": True,
        "registry_compat_only": True,
        "registry_scan_skipped": True,
        "compat_registry_present": False if event_store_primary else bool(registry_path and registry_path.exists()),
        "compat_events_present": False if event_store_primary else bool(events_path and events_path.exists()),
        "compat_worker_registry_present": False if event_store_primary else bool(worker_registry_path and worker_registry_path.exists()),
        "active_cycle": active_cycle,
        "delivery_scoreboard": (queue_meta.get("delivery_scoreboard", {}) if isinstance(queue_meta, dict) else {}),
        "stagnation_alert": (queue_meta.get("stagnation_alert", {}) if isinstance(queue_meta, dict) else {}),
        "planner_hard_guard": planner_hard_guard,
        "novelty_target_workflow": novelty_target_workflow,
        "workboard_decision_capable": workboard_decision_capable,
        "workboard_decision_capability_reason": workboard_decision_reason or "none",
        "planning_alignment_status": planning_alignment_status,
        "planning_alignment_reason": planning_alignment_reason,
        "active_subagent_ids": active_subagent_ids,
        "active_subagents_count": len(active_subagent_ids),
        "subagent_progress_age_s": subagent_progress_age,
        "ready_dev_count": ready_dev_count,
        "ready_planner_count": ready_planner_count,
        "ready_admin_count": ready_admin_count,
        "ready_scrum_count": ready_scrum_count,
        "runnable_task_ids": runnable_task_ids,
        "runnable_task_count": len(runnable_task_ids),
        "qa_collect_pending": qa_collect_pending,
        "qa_collect_pending_compat": qa_collect_pending_compat,
        "subagent_collect_pending": subagent_collect_pending,
        "subagent_collect_pending_runtime": subagent_collect_pending_runtime,
        "subagent_collect_pending_compat": subagent_collect_pending_compat,
        "runtime_actionable": bool(qa_collect_pending or subagent_collect_pending or runnable_task_ids),
        "next_action": next_action,
        "active_canonical_task": _build_contract(board, active_canonical_task) if isinstance(active_canonical_task, dict) else {},
        "active_planner_task": _build_contract(board, active_task) if isinstance(active_task, dict) else {},
        "ready_planner_task": _build_contract(board, ready_task) if isinstance(ready_task, dict) else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical planner board runtime snapshot")
    parser.add_argument("--root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("snapshot")
    args = parser.parse_args()
    root = Path(str(args.root)).expanduser().resolve()
    if args.command == "snapshot":
        print(json.dumps(snapshot(root, persist_delivery_state=True), ensure_ascii=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
