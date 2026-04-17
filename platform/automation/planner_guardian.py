#!/usr/bin/env python3
"""Continuous quality monitor for planner role outputs.

Inputs:
  planner_guardian.py <role> <source> <payload_file> <runtime_context_file> \
    <latest_file> <events_file> <state_dir> <directive_bus_file>

Behavior:
  - Parse planner contract + evidence keys.
  - Score autonomy/alignment quality.
  - Track streaks (ready-but-idle, low score, no batch while runway short).
  - Persist latest/events artifacts for observability.
  - Emit a directive on repeated drift (deduplicated by fingerprint).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot, load_product_delivery_state

CONTRACT_KEYS = (
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "RISKS",
    "NEXT",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
)
GUARDIAN_VERSION = "2026-03-03.v1"
PROMPT_PATCHES_VERSION = "2026-04-16.v1"
TERMINAL_TASK_STATES = {"DONE", "PASS", "CLOSED"}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def one_line(text: str, limit: int = 320) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) > limit:
        return value[:limit]
    return value


def parse_contract(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in text.splitlines():
        m = re.match(r"^\s*([A-Z_]+)\s*:\s*(.*)$", raw.strip())
        if not m:
            continue
        key = m.group(1).upper()
        if key in CONTRACT_KEYS and key not in out:
            out[key] = m.group(2).strip()
    return out


def parse_evidence_kv(raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for frag in raw.split(";"):
        if "=" not in frag:
            continue
        k, v = frag.split("=", 1)
        key = k.strip().lower()
        if not key or key in out:
            continue
        out[key] = v.strip()
    return out


def parse_runtime_flag(text: str, key: str, default: int = 0) -> int:
    m = re.search(rf"\b{re.escape(key)}=([01])\b", text)
    if not m:
        return default
    try:
        return int(m.group(1))
    except Exception:
        return default


def parse_runtime_int(text: str, key: str, default: int = 0) -> int:
    m = re.search(rf"\b{re.escape(key)}=(-?\d+)\b", text)
    if not m:
        return default
    try:
        return int(m.group(1))
    except Exception:
        return default


def parse_runtime_context(text: str) -> Dict[str, int]:
    return {
        "queue_has_ready": parse_runtime_flag(text, "queue_has_ready", 0),
        "workboard_role_has_work": parse_runtime_flag(text, "workboard_role_has_work", 0),
        "workboard_role_has_ready": parse_runtime_flag(text, "workboard_role_has_ready", 0),
        "workboard_role_has_in_progress": parse_runtime_flag(
            text, "workboard_role_has_in_progress", 0
        ),
        "top_level_total": parse_runtime_int(text, "top_level_total", 0),
        "top_level_non_closed": parse_runtime_int(text, "top_level_non_closed", 0),
        "top_level_ready": parse_runtime_int(text, "top_level_ready", 0),
        "planner_batch_runway_short": parse_runtime_flag(
            text, "planner_batch_runway_short", 0
        ),
    }


def load_json_dict(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(read_text(path))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _api_wave_payload(canonical: Dict[str, object] | None) -> Dict[str, object]:
    canonical = canonical or {}
    product_delivery_state = canonical.get("product_delivery_state")
    if isinstance(product_delivery_state, dict):
        api_wave = product_delivery_state.get("api_wave")
        if isinstance(api_wave, dict):
            return api_wave
    api_wave = canonical.get("api_wave_state")
    return api_wave if isinstance(api_wave, dict) else {}


def _canonical_role(value: str) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if token in {
        "planner",
        "analyst",
        "architect",
        "po",
        "scrum_master",
        "vision_architect_tasks_planner",
        "vision-architect-tasks-planner",
    }:
        return "planner"
    if token in {
        "dev",
        "backend_engineer",
        "frontend_engineer",
        "data_analyst",
        "integrator",
        "tester",
        "qa",
    }:
        return "dev"
    if token in {"admin", "clawsentinel", "infra"}:
        return "admin"
    return token


def _task_batch_id(task: Dict[str, object]) -> str:
    stream_id = str(task.get("stream_id") or task.get("batch_id") or "").strip().upper()
    if stream_id:
        return stream_id
    task_id = str(task.get("id") or task.get("task_id") or "").strip().upper()
    if task_id.startswith("BATCH-"):
        parts = task_id.split("-")
        if len(parts) >= 2:
            return "-".join(parts[:2])
    return ""


def _workspace_root_from_latest(latest_file: Path) -> Path | None:
    for candidate in [latest_file.parent, *latest_file.parents]:
        if candidate.name == "orchestrator-state" and candidate.parent.name == "logs-codex-runs":
            return candidate.parent.parent
    return None


def canonical_active_snapshot(latest_file: Path) -> Dict[str, object]:
    root = _workspace_root_from_latest(latest_file)
    if root is None:
        return {
            "active_batch_ids": [],
            "active_task_id": "",
            "active_task_state": "",
            "active_task_role": "",
            "active_task_owner": "",
            "active_task_blocked_reason": "",
            "active_task_next_action": "",
            "projection_decision_capable": False,
            "projection_secondary_only": True,
        }

    state_dir = root / "logs-codex-runs" / "orchestrator-state"
    queue_payload = load_json_dict(state_dir / "priority-queue.json")
    board_payload = load_json_dict(state_dir / "parallel-workstreams.json")
    queue_meta = queue_payload.get("meta") if isinstance(queue_payload.get("meta"), dict) else {}
    board_meta = board_payload.get("meta") if isinstance(board_payload.get("meta"), dict) else {}
    active_cycle = queue_payload.get("active_cycle")
    if not isinstance(active_cycle, dict):
        active_cycle = board_payload.get("active_cycle")
    if not isinstance(active_cycle, dict):
        active_cycle = {}
    active_batch_ids = [
        str(value).strip().upper()
        for value in active_cycle.get("active_batch_ids", [])
        if str(value).strip()
    ]

    runtime_truth = build_runtime_truth_snapshot(root, state_limit=24, event_limit=24)
    product_delivery_state = load_product_delivery_state(root)
    if not isinstance(product_delivery_state, dict) or not product_delivery_state:
        product_delivery_state = (
            runtime_truth.get("product_delivery_state", {})
            if isinstance(runtime_truth.get("product_delivery_state"), dict)
            else {}
        )
    delivery_active_batch_id = str(product_delivery_state.get("active_batch_id") or "").strip().upper()
    delivery_phase = str(product_delivery_state.get("phase") or "").strip()
    event_store_primary = bool(runtime_truth.get("event_store_primary", False))
    graph_state_count = int(runtime_truth.get("graph_state_count", 0) or 0)
    recent_event_count = int(runtime_truth.get("recent_event_count", 0) or 0)
    tasks = board_payload.get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
    projection_decision_capable = board_meta.get("decision_capable")
    if projection_decision_capable is None:
        projection_decision_capable = queue_meta.get("workboard_decision_capable")

    if (
        (
            not delivery_active_batch_id
            and delivery_phase in {"product_done_ops_dirty", "idle_ready_for_next_batch"}
        )
        or (
            event_store_primary
            and graph_state_count == 0
            and recent_event_count == 0
        )
    ):
        api_wave = product_delivery_state.get("api_wave") if isinstance(product_delivery_state.get("api_wave"), dict) else {}
        current_endpoint = api_wave.get("current_endpoint") if isinstance(api_wave.get("current_endpoint"), dict) else None
        next_endpoint = api_wave.get("next_endpoint") if isinstance(api_wave.get("next_endpoint"), dict) else None
        if bool(api_wave.get("enabled")) and (current_endpoint or next_endpoint):
            endpoint = current_endpoint or next_endpoint or {}
            current_status = str(api_wave.get("current_status") or "").strip().lower()
            active_task_role = "dev"
            active_task_next_action = "api_wave_dispatch"
            active_task_blocked_reason = str(api_wave.get("reason") or "").strip()
            if current_status in {"running", "active_delivery", "verifying_public_proof"}:
                task_state = "IN_PROGRESS"
            elif current_status == "blocked_route_admin":
                task_state = "READY"
                active_task_role = "admin"
                active_task_next_action = "api_wave_route_admin"
            elif current_status == "blocked_escalate_scrum":
                task_state = "READY"
                active_task_role = "scrum_master"
                active_task_next_action = "api_wave_route_scrum"
            elif current_status in {"blocked", "blocked_runtime"}:
                task_state = "BLOCKED"
                active_task_next_action = "api_wave_backoff"
            else:
                task_state = "READY_DEV" if bool(api_wave.get("dispatch_ready")) else "READY"
            active_task_id = (
                str(api_wave.get("current_task_id") or "").strip()
                or str((endpoint or {}).get("owner_task_id") or "").strip()
            )
            return {
                "active_batch_ids": [str(api_wave.get("batch_id") or api_wave.get("stream_id") or "BATCH-900").strip()],
                "active_task_id": active_task_id,
                "active_task_state": task_state,
                "active_task_role": active_task_role,
                "active_task_owner": "planner",
                "active_task_blocked_reason": active_task_blocked_reason,
                "active_task_next_action": active_task_next_action,
                "projection_decision_capable": True,
                "projection_decision_reason": "api_wave_autonomy",
                "product_delivery_state": product_delivery_state,
                "planner_hard_guard_active": bool(isinstance(queue_meta.get("planner_hard_guard"), dict) and queue_meta.get("planner_hard_guard", {}).get("active")),
                "planner_hard_guard_reason": str(queue_meta.get("planner_hard_guard", {}).get("reason") or "").strip() if isinstance(queue_meta.get("planner_hard_guard"), dict) else "",
                "stagnation_alert": queue_meta.get("stagnation_alert") if isinstance(queue_meta.get("stagnation_alert"), dict) else {},
                "novelty_target_workflow": queue_meta.get("novelty_target_workflow") if isinstance(queue_meta.get("novelty_target_workflow"), dict) else {},
                "novelty_target_audit": queue_meta.get("novelty_target_audit") if isinstance(queue_meta.get("novelty_target_audit"), dict) else {},
                "projection_secondary_only": False,
            }
        return {
            "active_batch_ids": [],
            "active_task_id": "",
            "active_task_state": "",
            "active_task_role": "",
            "active_task_owner": "",
            "active_task_blocked_reason": "",
            "active_task_next_action": "",
            "projection_decision_capable": projection_decision_capable,
            "projection_decision_reason": "runtime_idle_no_active_cycle",
            "product_delivery_state": product_delivery_state,
            "planner_hard_guard_active": bool(isinstance(queue_meta.get("planner_hard_guard"), dict) and queue_meta.get("planner_hard_guard", {}).get("active")),
            "planner_hard_guard_reason": str(queue_meta.get("planner_hard_guard", {}).get("reason") or "").strip() if isinstance(queue_meta.get("planner_hard_guard"), dict) else "",
            "stagnation_alert": queue_meta.get("stagnation_alert") if isinstance(queue_meta.get("stagnation_alert"), dict) else {},
            "novelty_target_workflow": queue_meta.get("novelty_target_workflow") if isinstance(queue_meta.get("novelty_target_workflow"), dict) else {},
            "novelty_target_audit": queue_meta.get("novelty_target_audit") if isinstance(queue_meta.get("novelty_target_audit"), dict) else {},
            "projection_secondary_only": False,
        }

    if delivery_active_batch_id:
        active_batch_ids = [delivery_active_batch_id]

    state_rank = {
        "BLOCKED": 0,
        "IN_PROGRESS": 1,
        "REVIEW": 2,
        "READY": 3,
        "READY_PLANNER": 4,
        "READY_DEV": 5,
        "WAITING_DEP": 6,
    }
    candidates: list[tuple[int, str, Dict[str, object]]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        batch_id = _task_batch_id(task)
        if active_batch_ids and batch_id not in active_batch_ids:
            continue
        state = str(task.get("state") or "").strip().upper()
        if state in TERMINAL_TASK_STATES or not state:
            continue
        task_id = str(task.get("id") or task.get("task_id") or "").strip()
        if not task_id:
            continue
        role = _canonical_role(str(task.get("role") or task.get("owner") or task.get("assignee") or ""))
        role_rank = 0 if role not in {"", "planner"} else 1
        candidates.append((state_rank.get(state, 99), role_rank, task_id, task))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    task = candidates[0][3] if candidates else {}
    task_id = str(task.get("id") or task.get("task_id") or "").strip()
    task_state = str(task.get("state") or "").strip().upper()
    task_role = _canonical_role(str(task.get("role") or task.get("assignee") or ""))
    task_owner = _canonical_role(str(task.get("owner") or task.get("assignee") or task.get("role") or ""))
    blocked_reason = str(task.get("blocked_reason") or "").strip()
    next_action = str(task.get("next_action") or "").strip()
    planner_hard_guard = queue_meta.get("planner_hard_guard") if isinstance(queue_meta.get("planner_hard_guard"), dict) else {}
    stagnation_alert = queue_meta.get("stagnation_alert") if isinstance(queue_meta.get("stagnation_alert"), dict) else {}
    novelty_target_workflow = queue_meta.get("novelty_target_workflow") if isinstance(queue_meta.get("novelty_target_workflow"), dict) else {}
    novelty_target_audit = queue_meta.get("novelty_target_audit") if isinstance(queue_meta.get("novelty_target_audit"), dict) else {}
    if not novelty_target_workflow and bool(isinstance(planner_hard_guard, dict) and planner_hard_guard.get("active")):
        guard_reason = str(planner_hard_guard.get("reason") or "").strip().lower()
        if guard_reason == "stagnation_requires_novelty_target":
            novelty_target_workflow = {
                "status": "required",
                "owner_role": "planner",
                "batch_id": str((stagnation_alert or {}).get("batch_id") or "").strip().upper(),
                "scope_key": str((stagnation_alert or {}).get("scope_key") or "").strip().lower(),
                "reason": guard_reason,
                "next_action": "define_novelty_target",
                "policy": "no_new_downstream_work",
                "required_fields": ["novelty_target", "user_value_delta", "scope_delta", "success_metric"],
                "clear_when": "novelty_target_present",
                "recent_classes": [
                    str(item).strip().lower()
                    for item in ((stagnation_alert or {}).get("recent_classes") or [])
                    if str(item).strip()
                ],
            }

    # If SQLite is primary and reports no active state or events for the active cycle,
    # a non-decision-capable projection must not anchor planner on a stale projected task.
    if event_store_primary and projection_decision_capable is False and graph_state_count == 0 and recent_event_count == 0:
        return {
            "active_batch_ids": active_batch_ids,
            "active_task_id": "",
            "active_task_state": "",
            "active_task_role": "",
            "active_task_owner": "",
            "active_task_blocked_reason": "",
            "active_task_next_action": "",
            "projection_decision_capable": False,
            "projection_decision_reason": str(
                board_meta.get("decision_capability_reason")
                or queue_meta.get("workboard_decision_capability_reason")
                or "projection_missing_operational_fields"
            ).strip(),
            "product_delivery_state": product_delivery_state,
            "planner_hard_guard_active": bool(isinstance(planner_hard_guard, dict) and planner_hard_guard.get("active")),
            "planner_hard_guard_reason": str(planner_hard_guard.get("reason") or "").strip() if isinstance(planner_hard_guard, dict) else "",
            "stagnation_alert": stagnation_alert if isinstance(stagnation_alert, dict) else {},
            "novelty_target_workflow": novelty_target_workflow if isinstance(novelty_target_workflow, dict) else {},
            "novelty_target_audit": novelty_target_audit if isinstance(novelty_target_audit, dict) else {},
            "projection_secondary_only": False,
        }

    return {
        "active_batch_ids": active_batch_ids,
        "active_task_id": task_id,
        "active_task_state": task_state,
        "active_task_role": task_role,
        "active_task_owner": task_owner,
        "active_task_blocked_reason": blocked_reason,
        "active_task_next_action": next_action,
        "projection_decision_capable": projection_decision_capable,
        "projection_decision_reason": str(
            board_meta.get("decision_capability_reason")
            or queue_meta.get("workboard_decision_capability_reason")
            or ""
        ).strip(),
        "planner_hard_guard_active": bool(isinstance(planner_hard_guard, dict) and planner_hard_guard.get("active")),
        "planner_hard_guard_reason": str(planner_hard_guard.get("reason") or "").strip() if isinstance(planner_hard_guard, dict) else "",
        "stagnation_alert": stagnation_alert if isinstance(stagnation_alert, dict) else {},
        "novelty_target_workflow": novelty_target_workflow if isinstance(novelty_target_workflow, dict) else {},
        "novelty_target_audit": novelty_target_audit if isinstance(novelty_target_audit, dict) else {},
        "product_delivery_state": product_delivery_state,
        "projection_secondary_only": projection_decision_capable is False,
    }


def truthy(value: str) -> bool:
    token = str(value or "").strip().lower()
    return token in {"1", "true", "yes", "on", "ok", "created", "done"}


def planner_traceability_required(task_update: str, batch_created: bool) -> bool:
    token = str(task_update or "").strip().lower()
    if batch_created:
        return True
    return token in {"claim", "complete", "handoff"}


def summarize_contract_for_publication(
    contract: Dict[str, str], evidence: Dict[str, str], runtime: Dict[str, int], canonical: Dict[str, object]
) -> Dict[str, str]:
    summary = {
        "status": one_line(contract.get("STATUS", "")),
        "delta": one_line(contract.get("DELTA", "")),
        "verdict": one_line(contract.get("VERDICT", "")),
        "blocker_id": one_line(contract.get("BLOCKER_ID", "")),
        "next_action_unique": one_line(contract.get("NEXT_ACTION_UNIQUE", "")),
        "task_update": one_line(evidence.get("task_update", "")),
        "planner_artifact": one_line(evidence.get("planner_artifact", "")),
        "batch_created": one_line(evidence.get("batch_created", "")),
        "architecture_plan_ref": one_line(evidence.get("architecture_plan_ref", "")),
        "vision_alignment": one_line(evidence.get("vision_alignment", "")),
        "architecture_audit": one_line(evidence.get("architecture_audit", "")),
        "canonical_active_task_id": one_line(str(canonical.get("active_task_id") or "")),
        "canonical_active_task_state": one_line(str(canonical.get("active_task_state") or "")),
        "canonical_active_task_role": one_line(str(canonical.get("active_task_role") or "")),
        "planner_hard_guard_active": one_line(str(canonical.get("planner_hard_guard_active") or "")),
        "planner_hard_guard_reason": one_line(str(canonical.get("planner_hard_guard_reason") or "")),
        "projection_decision_capable": one_line(str(canonical.get("projection_decision_capable") or "")),
        "projection_decision_reason": one_line(str(canonical.get("projection_decision_reason") or "")),
    }

    no_canonical_work = _no_canonical_work(runtime, canonical)
    if no_canonical_work:
        summary.update(
            {
                "status": "IDLE",
                "delta": "NO_ACTIVE_CANONICAL_WORK",
                "verdict": "PASS",
                "blocker_id": "NONE",
                "next_action_unique": "none",
                "task_update": "none_no_ready",
                "planner_artifact": "canonical_runtime_truth_idle",
            }
        )
    return summary


def compute_score(
    contract: Dict[str, str],
    evidence: Dict[str, str],
    runtime: Dict[str, int],
    canonical: Dict[str, object],
) -> Dict[str, object]:
    score = 100
    issues: List[str] = []

    status = contract.get("STATUS", "")
    delta = contract.get("DELTA", "")
    blocker = contract.get("BLOCKER_ID", "")
    task_update = evidence.get("task_update", "")
    has_stream = bool(evidence.get("stream_id"))
    has_task = bool(evidence.get("task_id"))

    has_planner_artifact = bool(evidence.get("planner_artifact"))
    architecture_check_value = str(evidence.get("architecture_check", "")).lower()
    has_arch_ref = bool(evidence.get("architecture_plan_ref")) or any(
        token in architecture_check_value
        for token in ("docs/architecture", "apps/api", "apps/web", "path_target=")
    )
    has_vision_alignment = bool(evidence.get("vision_alignment"))
    has_arch_audit = bool(evidence.get("architecture_audit")) or any(
        token in architecture_check_value for token in ("apps/api", "apps/web", "platform/automation", "path_target=")
    )
    planner_runtime_exception = truthy(evidence.get("planner_runtime_exception", "0"))
    planner_autobatch_attempted = truthy(evidence.get("planner_autobatch_attempted", "0"))
    batch_created = truthy(evidence.get("batch_created", ""))
    batch_dependency_policy = str(evidence.get("batch_dependency_policy", "")).strip().lower()
    inter_batch_dep_raw = str(evidence.get("inter_batch_dep", "")).strip().lower()
    batch_depends_on = str(evidence.get("batch_depends_on", "")).strip().lower()
    depends_on_batch = str(evidence.get("depends_on_batch", "")).strip().lower()
    arch_ref_value = str(evidence.get("architecture_plan_ref", "")).lower() or architecture_check_value
    vision_alignment_value = str(evidence.get("vision_alignment", "")).lower()
    arch_audit_value = str(evidence.get("architecture_audit", "")).lower() or architecture_check_value
    inter_batch_dependency_detected = False
    canonical_active_batch_ids = canonical.get("active_batch_ids", [])
    if not isinstance(canonical_active_batch_ids, list):
        canonical_active_batch_ids = []
    canonical_active_task_id = str(canonical.get("active_task_id") or "").strip()
    canonical_active_task_role = str(canonical.get("active_task_role") or "").strip()
    canonical_active_task_state = str(canonical.get("active_task_state") or "").strip().upper()
    canonical_active_task_blocked_reason = str(
        canonical.get("active_task_blocked_reason") or ""
    ).strip()
    canonical_projection_decision_capable = canonical.get("projection_decision_capable")
    canonical_projection_reason = str(canonical.get("projection_decision_reason") or "").strip()
    canonical_hard_guard_active = bool(canonical.get("planner_hard_guard_active"))
    canonical_hard_guard_reason = str(canonical.get("planner_hard_guard_reason") or "").strip()
    canonical_novelty_target_audit = canonical.get("novelty_target_audit", {})
    if not isinstance(canonical_novelty_target_audit, dict):
        canonical_novelty_target_audit = {}
    runtime_has_open_batch_runway = int(runtime.get("top_level_non_closed", 0) or 0) > 0
    runtime_projection_noise = bool(
        int(runtime.get("queue_has_ready", 0) or 0) > 0
        or int(runtime.get("workboard_role_has_work", 0) or 0) > 0
        or int(runtime.get("workboard_role_has_in_progress", 0) or 0) > 0
        or runtime_has_open_batch_runway
    )
    canonical_cycle_active = bool(canonical_active_batch_ids)
    no_canonical_work = _no_canonical_work(runtime, canonical)
    canonical_downstream_active = (
        canonical_cycle_active
        and bool(canonical_active_task_id)
        and canonical_active_task_role not in {"", "planner"}
        and canonical_active_task_state not in TERMINAL_TASK_STATES
    )
    if canonical_hard_guard_active:
        score -= 40
        issues.append(canonical_hard_guard_reason or "planner_hard_guard_active")
    if str(canonical_novelty_target_audit.get("status") or "").strip().lower() == "overdue":
        score -= 15
        issues.append("novelty_target_overdue")
    if canonical_projection_decision_capable is False:
        score -= 15
        issues.append("projection_not_decision_capable")
    if inter_batch_dep_raw in {"1", "true", "yes", "on"}:
        inter_batch_dependency_detected = True
    for token in (batch_depends_on, depends_on_batch):
        if token and token not in {"none", "n/a", "null", "-"}:
            inter_batch_dependency_detected = True
            break

    if not task_update:
        score -= 25
        issues.append("missing_task_update")
    if not has_planner_artifact and not no_canonical_work:
        score -= 20
        issues.append("missing_planner_artifact")
    if no_canonical_work and runtime_projection_noise:
        issues.append("residue_detected")

    if runtime.get("queue_has_ready", 0) == 1 and not no_canonical_work:
        if delta.upper() == "NO_DELTA":
            score -= 30
            issues.append("ready_but_no_delta")
        if task_update in {"none_no_ready", "none_no_signal"}:
            score -= 35
            issues.append("ready_but_none_task_update")

    if (
        task_update in {"none_no_ready", "none_no_signal"}
        and not planner_runtime_exception
        and not canonical_downstream_active
        and not no_canonical_work
    ):
        score -= 40
        issues.append("planner_passive_forbidden_violation")

    if (
        runtime.get("queue_has_ready", 0) == 0
        and runtime.get("workboard_role_has_work", 0) == 0
        and runtime.get("workboard_role_has_in_progress", 0) == 0
        and runtime_has_open_batch_runway
        and task_update in {"none_no_ready", "none_no_signal"}
        and not planner_autobatch_attempted
        and not canonical_downstream_active
    ):
        score -= 20
        issues.append("planner_autobatch_missing_when_idle")

    if status.upper() == "BLOCKED" and blocker.strip().upper() in {"", "NONE"}:
        score -= 20
        issues.append("blocked_without_blocker_id")

    if task_update in {"claim", "complete", "handoff"} and (not has_stream or not has_task):
        score -= 25
        issues.append("missing_stream_task_on_delivery_update")

    if (
        runtime.get("planner_batch_runway_short", 0) == 1
        and runtime_has_open_batch_runway
        and not batch_created
        and not canonical_cycle_active
        and not canonical_hard_guard_active
    ):
        score -= 15
        issues.append("runway_short_without_batch_creation")

    if canonical_active_task_state == "BLOCKED" and canonical_active_task_blocked_reason:
        score -= 10
        issues.append("canonical_active_handoff_blocked")

    if inter_batch_dependency_detected:
        score -= 25
        issues.append("inter_batch_dependency_detected")

    dependency_policy_required = bool(
        inter_batch_dependency_detected
        or runtime_has_open_batch_runway
        or batch_created
        or has_stream
        or has_task
    )
    if not no_canonical_work and dependency_policy_required and (
        not batch_dependency_policy or batch_dependency_policy != "single_batch"
    ):
        score -= 15
        issues.append("dependency_policy_not_enforced")

    # Demand architecture/vision traceability only when planner claims/completes/handoffs
    # its own work or creates a new batch. Collect/repair/ack ticks for downstream-active
    # work should not be penalized for missing planner-close proof fields.
    if planner_traceability_required(task_update, batch_created):
        if not has_arch_ref:
            score -= 10
            issues.append("missing_architecture_plan_ref")
        if not has_vision_alignment:
            score -= 10
            issues.append("missing_vision_alignment")
        if not has_arch_audit:
            score -= 10
            issues.append("missing_architecture_audit")
        if has_arch_ref and not any(
            token in arch_ref_value
            for token in ("architecture_map", "docs/architecture", "apps/api", "apps/web")
        ):
            score -= 8
            issues.append("architecture_ref_not_canonical")
        if has_vision_alignment and not any(
            token in vision_alignment_value
            for token in ("product_vision", "batch-", "workstate", "roadmap")
        ):
            score -= 8
            issues.append("vision_alignment_not_traceable")
        if has_arch_audit and not any(
            token in arch_audit_value
            for token in ("apps/api", "apps/web", "platform/automation")
        ):
            score -= 8
            issues.append("architecture_audit_missing_paths")

    score = max(0, min(100, score))
    level = "green" if score >= 85 else ("yellow" if score >= 70 else "red")
    return {"score": score, "level": level, "issues": issues}


def load_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(read_text(path))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(path: Path, data: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def update_streaks(
    state: Dict[str, object],
    runtime: Dict[str, int],
    contract: Dict[str, str],
    evidence: Dict[str, str],
    canonical: Dict[str, object],
    score: int,
) -> Dict[str, int]:
    streaks = state.get("streaks")
    if not isinstance(streaks, dict):
        streaks = {}

    no_canonical_work = _no_canonical_work(runtime, canonical)
    ready_idle = (
        not no_canonical_work
        and runtime.get("queue_has_ready", 0) == 1
        and (
            contract.get("DELTA", "").upper() == "NO_DELTA"
            or evidence.get("task_update", "") in {"none_no_ready", "none_no_signal"}
        )
    )
    runway_no_batch = (
        runtime.get("planner_batch_runway_short", 0) == 1
        and int(runtime.get("top_level_non_closed", 0) or 0) > 0
        and not truthy(evidence.get("batch_created", ""))
    )

    streaks["ready_idle_streak"] = int(streaks.get("ready_idle_streak", 0)) + 1 if ready_idle else 0
    streaks["low_score_streak"] = int(streaks.get("low_score_streak", 0)) + 1 if score < 70 else 0
    streaks["runway_no_batch_streak"] = (
        int(streaks.get("runway_no_batch_streak", 0)) + 1 if runway_no_batch else 0
    )

    # Detect planner handoff-loop: same task_id handoffed repeatedly without progress.
    # Triggers when task_update=handoff on the same task >=3 consecutive ticks.
    current_task = evidence.get("task_id", "").strip()
    last_handoff_task = str(streaks.get("_last_handoff_task", "")).strip()
    is_handoff = evidence.get("task_update", "").strip().lower() == "handoff"
    if is_handoff and current_task and current_task == last_handoff_task:
        streaks["handoff_same_task_streak"] = int(streaks.get("handoff_same_task_streak", 0)) + 1
    else:
        streaks["handoff_same_task_streak"] = 0
    streaks["_last_handoff_task"] = current_task if is_handoff else ""

    return {k: int(v) for k, v in streaks.items() if not k.startswith("_")}, \
           {"_last_handoff_task": streaks.get("_last_handoff_task", "")}


def recommendations(issues: List[str], canonical: Dict[str, object] | None = None) -> List[str]:
    canonical = canonical or {}
    active_batch_ids = canonical.get("active_batch_ids")
    if not isinstance(active_batch_ids, list):
        active_batch_ids = []
    active_task_id = str(canonical.get("active_task_id") or "").strip()
    active_task_role = str(canonical.get("active_task_role") or "").strip()
    active_task_state = str(canonical.get("active_task_state") or "").strip().upper()
    active_task_blocked_reason = str(canonical.get("active_task_blocked_reason") or "").strip()
    hard_guard_active = bool(canonical.get("planner_hard_guard_active"))
    hard_guard_reason = str(canonical.get("planner_hard_guard_reason") or "").strip()
    projection_decision_capable = canonical.get("projection_decision_capable")
    projection_decision_reason = str(canonical.get("projection_decision_reason") or "").strip()
    novelty_target_workflow = canonical.get("novelty_target_workflow") if isinstance(canonical.get("novelty_target_workflow"), dict) else {}
    novelty_target_audit = canonical.get("novelty_target_audit") if isinstance(canonical.get("novelty_target_audit"), dict) else {}
    product_delivery_state = canonical.get("product_delivery_state") if isinstance(canonical.get("product_delivery_state"), dict) else {}
    delivery_phase = str(product_delivery_state.get("phase") or "").strip()
    next_batch_eligible = bool(product_delivery_state.get("next_batch_eligible", False))
    api_wave = _api_wave_payload(canonical)
    api_wave_target = api_wave.get("current_endpoint") if isinstance(api_wave.get("current_endpoint"), dict) else None
    if api_wave_target is None:
        api_wave_target = api_wave.get("next_endpoint") if isinstance(api_wave.get("next_endpoint"), dict) else None
    api_wave_reason = str(api_wave.get("reason") or "").strip().lower()
    out: List[str] = []
    if not active_batch_ids and not active_task_id:
        if bool(api_wave.get("enabled")) and isinstance(api_wave_target, dict) and bool(api_wave.get("dispatch_ready")):
            out.append(
                "Aucun batch canonique actif: lancer l'API wave maintenant via planner_runtime_actions.py api-wave-dispatch "
                f"sur {str(api_wave_target.get('endpoint_id') or 'endpoint').strip()}."
            )
            return out
        if bool(api_wave.get("enabled")) and api_wave_reason == "route_admin":
            out.append("Aucun batch classique actif mais incident API wave runtime/public-proof: router admin, pas planner-autobatch.")
            return out
        if delivery_phase in {"product_done_ops_dirty", "idle_ready_for_next_batch"} and next_batch_eligible:
            out.append("Aucun batch canonique actif: ouvrir le prochain batch eligible maintenant via sync-priority + planner-autobatch + claim.")
        elif "residue_detected" in issues and projection_decision_reason == "runtime_idle_no_active_cycle":
            out.append("Résidu de projection detecte sans batch canonique reel: publier advisory_mismatch seulement et ne pas reclamer de tache.")
        return out
    if hard_guard_active:
        workflow_scope = str(novelty_target_workflow.get("scope_key") or "").strip()
        required_fields = novelty_target_workflow.get("required_fields")
        required_fields_text = ", ".join(str(item).strip() for item in required_fields if str(item).strip()) if isinstance(required_fields, list) else ""
        missing_fields = novelty_target_audit.get("missing_fields") if isinstance(novelty_target_audit.get("missing_fields"), list) else novelty_target_workflow.get("missing_fields")
        missing_fields_text = ", ".join(str(item).strip() for item in missing_fields if str(item).strip()) if isinstance(missing_fields, list) else ""
        audit_status = str(novelty_target_audit.get("status") or "").strip().lower()
        audit_age_s = str(novelty_target_audit.get("age_s") or "").strip()
        out.append(
            f"Hard guard canonique actif ({hard_guard_reason or 'planner_hard_guard_active'}): ne pas creer de batch ni relancer ANALYSIS tant qu'une novelty target n'est pas definie."
        )
        if workflow_scope or required_fields_text:
            out.append(
                "Workflow de sortie: "
                f"planner doit definir novelty_target sur scope={workflow_scope or 'active_scope'} "
                f"avec champs [{required_fields_text or 'novelty_target, user_value_delta, scope_delta, success_metric'}]."
            )
        if audit_status == "overdue" or missing_fields_text:
            out.append(
                f"Dette de stagnation {'overdue' if audit_status == 'overdue' else 'active'}: champs manquants [{missing_fields_text or 'novelty_target, user_visible_delta'}]"
                + (f" depuis {audit_age_s}s." if audit_age_s else ".")
            )
        if active_task_id:
            out.append(
                f"Le cycle actif reste ancre sur {active_task_id} ({active_task_role}/{active_task_state or 'UNKNOWN'}); toute supervision doit suivre cette tache."
            )
        if projection_decision_capable is False:
            out.append(
                f"Projection workboard non decisionnelle ({projection_decision_reason or 'projection_missing_operational_fields'}): s'appuyer sur runtime truth/queue avant toute recommandation."
            )
        return out[:3]
    if active_task_id and active_task_role and active_task_role != "planner":
        out.append(
            f"Cycle canonique actif sur {active_task_id} ({active_task_role}/{active_task_state or 'UNKNOWN'}): "
            "ne pas creer de nouveau batch ni relancer ANALYSIS."
        )
        if active_task_blocked_reason:
            out.append(
                f"Traiter explicitement le blocage canonique {active_task_blocked_reason} sur {active_task_id}."
            )
        out.append(
            f"Attendre une transition canonique sur {active_task_id} avant tout nouvel autobatch planner."
        )
        return out[:3]
    if "planner_passive_forbidden_violation" in issues:
        if bool(api_wave.get("enabled")) and isinstance(api_wave_target, dict):
            out.append("Planner non-passive policy violee: utiliser api-wave-dispatch maintenant au lieu d'un planner-autobatch.")
        else:
            out.append("Planner non-passive policy violee: claim une tache planner READY ou creer un autobatch immediatement.")
    if "planner_autobatch_missing_when_idle" in issues:
        if bool(api_wave.get("enabled")) and isinstance(api_wave_target, dict):
            out.append("Lane planner idle sans READY batch: passer par api-wave-dispatch et continuer la migration Judge-parity de l'endpoint courant.")
        else:
            out.append("Lane planner idle sans READY: executer planner-autobatch puis claim la tache ANALYSIS.")
    if bool(api_wave.get("enabled")) and api_wave_reason == "route_admin":
        out.append("API wave: incident runtime/control-plane/public-proof => admin seulement, jamais defer provider ni planner-autobatch.")
    if bool(api_wave.get("enabled")) and api_wave_reason == "route_scrum":
        out.append("API wave: deux blocages non runtime consecutifs => un seul passage scrum_master puis defer si toujours sterile.")
    if bool(api_wave.get("enabled")) and api_wave_reason == "defer_current_endpoint":
        out.append("API wave: endpoint courant a differer puis passer au suivant sans reveiller admin.")
    if bool(api_wave.get("enabled")) and api_wave_reason == "backoff":
        out.append("API wave: lane sterile => backoff explicite, pas de retry/takeover decoratif.")
    if "ready_but_no_delta" in issues or "ready_but_none_task_update" in issues:
        out.append("Claim une tache READY et fournir un dispatch concret vers role delivery.")
    if "missing_architecture_plan_ref" in issues or "missing_architecture_audit" in issues:
        out.append("Ajouter architecture_plan_ref + architecture_audit relies aux chemins apps/api|apps/web.")
    if "missing_vision_alignment" in issues:
        out.append("Lier explicitement le batch cree au target de PRODUCT_VISION.")
    if "vision_alignment_not_traceable" in issues:
        out.append("Rendre vision_alignment tracable avec PRODUCT_VISION + id BATCH explicite.")
    if "architecture_ref_not_canonical" in issues:
        out.append("Pointer architecture_plan_ref vers docs/architecture/ARCHITECTURE_MAP.md ou chemins apps/api|apps/web.")
    if "architecture_audit_missing_paths" in issues:
        out.append("Ajouter dans architecture_audit les chemins impactes (apps/api, apps/web, platform/automation).")
    if "runway_short_without_batch_creation" in issues:
        out.append("Creer un batch top-level BATCH-XX pour maintenir la runway planner.")
    if "missing_stream_task_on_delivery_update" in issues:
        out.append("Completer stream_id et task_id pour tout task_update claim|complete|handoff.")
    if "inter_batch_dependency_detected" in issues or "dependency_policy_not_enforced" in issues:
        out.append("Regrouper dependances dans le meme batch (taches intra-stream), puis relancer sanitize-dependencies + sync-priority.")
    if not out:
        out.append("Maintenir cadence actuelle et poursuivre fermeture IN_PROGRESS avant nouveaux claims.")
    return out[:3]


def planner_prompt_patches_file(latest_file: Path) -> Path:
    return latest_file.with_name("planner-prompt-patches.json")


def _ordered_unique(values: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for raw in values:
        token = str(raw or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _no_canonical_work(runtime: Dict[str, object] | None, canonical: Dict[str, object] | None) -> bool:
    runtime = runtime or {}
    canonical = canonical or {}
    canonical_active_batch_ids = canonical.get("active_batch_ids", [])
    if not isinstance(canonical_active_batch_ids, list):
        canonical_active_batch_ids = []
    canonical_active_task_id = str(canonical.get("active_task_id") or "").strip()
    projection_decision_reason = str(canonical.get("projection_decision_reason") or "").strip()
    product_delivery_state = canonical.get("product_delivery_state") if isinstance(canonical.get("product_delivery_state"), dict) else {}
    delivery_phase = str(product_delivery_state.get("phase") or "").strip()
    api_wave = _api_wave_payload(canonical)
    if bool(api_wave.get("enabled")) and (
        isinstance(api_wave.get("current_endpoint"), dict)
        or isinstance(api_wave.get("next_endpoint"), dict)
        or str(api_wave.get("current_task_id") or "").strip()
    ):
        return False
    if (
        not canonical_active_batch_ids
        and not canonical_active_task_id
        and projection_decision_reason == "runtime_idle_no_active_cycle"
    ):
        return True
    if (
        not canonical_active_batch_ids
        and not canonical_active_task_id
        and delivery_phase in {"product_done_ops_dirty", "idle_ready_for_next_batch"}
    ):
        return True
    return (
        not canonical_active_batch_ids
        and not canonical_active_task_id
        and int(runtime.get("queue_has_ready", 0) or 0) == 0
        and int(runtime.get("workboard_role_has_work", 0) or 0) == 0
        and int(runtime.get("workboard_role_has_in_progress", 0) or 0) == 0
        and int(runtime.get("top_level_non_closed", 0) or 0) == 0
    )


def build_prompt_patches(
    issues: List[str],
    canonical: Dict[str, object] | None = None,
    streaks: Dict[str, int] | None = None,
    evidence: Dict[str, str] | None = None,
    runtime: Dict[str, object] | None = None,
) -> List[Dict[str, object]]:
    canonical = canonical or {}
    streaks = streaks or {}
    evidence = evidence or {}
    runtime = runtime or {}
    ordered_issues = _ordered_unique(issues)
    patches: List[Dict[str, object]] = []
    active_task_id = str(canonical.get("active_task_id") or "").strip()
    active_task_role = str(canonical.get("active_task_role") or "").strip().lower()
    active_task_state = str(canonical.get("active_task_state") or "").strip().upper()
    task_update = str(evidence.get("task_update") or "").strip().lower()
    batch_created = truthy(evidence.get("batch_created", ""))
    downstream_ready = bool(
        active_task_id
        and active_task_role not in {"", "planner"}
        and active_task_state.startswith("READY")
    )
    downstream_active = bool(
        active_task_id
        and active_task_role not in {"", "planner"}
        and active_task_state not in TERMINAL_TASK_STATES
        and not downstream_ready
    )
    no_canonical_work = _no_canonical_work(runtime, canonical)
    product_delivery_state = canonical.get("product_delivery_state") if isinstance(canonical.get("product_delivery_state"), dict) else {}
    delivery_phase = str(product_delivery_state.get("phase") or "").strip()
    next_batch_eligible = bool(product_delivery_state.get("next_batch_eligible", False))
    api_wave = _api_wave_payload(canonical)
    api_wave_target = api_wave.get("current_endpoint") if isinstance(api_wave.get("current_endpoint"), dict) else None
    if api_wave_target is None:
        api_wave_target = api_wave.get("next_endpoint") if isinstance(api_wave.get("next_endpoint"), dict) else None
    api_wave_enabled = bool(api_wave.get("enabled"))
    api_wave_dispatch_ready = bool(api_wave.get("dispatch_ready"))
    api_wave_reason = str(api_wave.get("reason") or "").strip().lower()
    api_wave_status = str(api_wave.get("current_status") or "").strip().lower()
    hard_guard_active = bool(canonical.get("planner_hard_guard_active"))
    hard_guard_reason = str(canonical.get("planner_hard_guard_reason") or "").strip().lower()
    novelty_audit = canonical.get("novelty_target_audit", {})
    novelty_workflow = canonical.get("novelty_target_workflow", {})
    if not isinstance(novelty_audit, dict):
        novelty_audit = {}
    if not isinstance(novelty_workflow, dict):
        novelty_workflow = {}

    def add_patch(
        patch_id: str,
        *,
        priority: int,
        issue_codes: List[str],
        instruction: str,
        why: str,
        when_to_apply: str,
        exit_condition: str,
        ttl_runs: int,
    ) -> None:
        if any(existing.get("id") == patch_id for existing in patches):
            return
        patches.append(
            {
                "id": patch_id,
                "priority": priority,
                "issue_codes": _ordered_unique(issue_codes),
                "instruction": one_line(instruction, 420),
                "why": one_line(why, 220),
                "when_to_apply": one_line(when_to_apply, 220),
                "exit_condition": one_line(exit_condition, 220),
                "ttl_runs": max(1, int(ttl_runs)),
            }
        )

    if (
        hard_guard_active
        or "delivery_value_insufficient" in ordered_issues
        or "novelty_target_overdue" in ordered_issues
    ):
        missing_fields = novelty_audit.get("missing_fields")
        if not isinstance(missing_fields, list):
            missing_fields = novelty_workflow.get("required_fields")
        missing_fields_text = ", ".join(
            str(item).strip() for item in missing_fields or [] if str(item).strip()
        ) or "novelty_target, user_visible_delta"
        add_patch(
            "novelty_target_first",
            priority=100,
            issue_codes=[
                hard_guard_reason or "planner_hard_guard_active",
                "delivery_value_insufficient",
                "novelty_target_overdue",
            ],
            instruction=(
                "Hard guard/stagnation novelty actif: pas de relance ANALYSIS, planner-autobatch, ni api-wave-dispatch. "
                "Termine la tache planner en cours ou execute planner_runtime_actions.py "
                f"novelty-target avec [{missing_fields_text}] avant tout nouveau downstream work."
            ),
            why=(
                "Arrete les boucles validation/reuse_only et force un delta utilisateur explicite "
                "avant de recreer du travail."
            ),
            when_to_apply=(
                "planner_hard_guard_active=1 ou issue_codes contiennent "
                "delivery_value_insufficient/novelty_target_overdue"
            ),
            exit_condition=(
                "novelty_target_workflow.status != required et le batch actif expose un "
                "user_visible_delta clair"
            ),
            ttl_runs=8,
        )

    proof_issue_codes = [
        code
        for code in ordered_issues
        if code
        in {
            "planner_quality_autofill_missing",
            "planner_evidence_incomplete_soft",
            "missing_architecture_plan_ref",
            "missing_architecture_audit",
            "missing_vision_alignment",
            "architecture_ref_not_canonical",
            "vision_alignment_not_traceable",
            "architecture_audit_missing_paths",
        }
    ]
    proof_patch_requires_close_phase = batch_created or task_update in {"complete", "handoff"}
    proof_patch_has_strong_quality_signal = any(
        code in ordered_issues
        for code in {"planner_quality_autofill_missing", "planner_evidence_incomplete_soft"}
    )
    if (
        proof_issue_codes
        and not downstream_active
        and not downstream_ready
        and (proof_patch_requires_close_phase or proof_patch_has_strong_quality_signal)
    ):
        add_patch(
            "planner_delivery_proof_complete",
            priority=90,
            issue_codes=proof_issue_codes,
            instruction=(
                "Avant complete sur PLAN/ANALYSIS/ARCH/GOV_REVIEW, backfill la preuve planner: "
                "planner_artifact, architecture_plan_ref, architecture_audit, vision_alignment, "
                "architecture_check, root_cause, fix_applied et verify(before/after/test). "
                "Si la tache planner active est READY/IN_PROGRESS et que seuls ces champs "
                "manquent, fais le backfill puis relance complete dans le meme tick; pas de "
                "sortie analysis_only/none_no_signal. Si un subagent a rendu une preuve "
                "partielle, merge-la avant tout redispatch."
            ),
            why=(
                "Empêche les clôtures incomplètes qui recyclent les mêmes tâches planner sans "
                "apprentissage durable."
            ),
            when_to_apply=(
                "issue_codes contiennent planner_quality_autofill_missing ou planner_evidence_incomplete_soft"
            ),
            exit_condition=(
                "Deux ticks consécutifs sans issue de qualité de preuve planner sur la tâche active"
            ),
            ttl_runs=6,
        )

    follow_canonical_issue_codes = [
        code
        for code in ordered_issues
        if code
        in {
            "planner_orchestrator_admin_route_mismatch",
            "planner_admin_takeover_required",
            "subagent_ack_pending",
            "admin_dispatch_ack_pending",
            "canonical_active_handoff_blocked",
        }
    ]
    if (active_task_id and active_task_role not in {"", "planner"}) or follow_canonical_issue_codes:
        if downstream_ready:
            follow_instruction = (
                "Priorité: lancer la lane downstream prête "
                f"{active_task_id or '<ready_task>'} ({active_task_role or 'downstream'}/{active_task_state or 'READY'}). "
                "Utilise planner_subagent_manager.py run avec un scope ciblé; pas de collect ni "
                "handoff-ack/handoff-close tant qu'aucun subagent n'a réellement démarré. "
                "Aucun nouveau batch ni ANALYSIS tant que cette lane READY n'a pas reçu son exécution utile."
            )
            follow_why = (
                "Empêche planner de traiter une lane READY comme une lane déjà active, ce qui "
                "produit des waits ou collect impossibles au lieu d'un dispatch utile."
            )
            follow_when = (
                "canonical.active_task_role != planner et canonical.active_task_state commence par READY"
            )
            follow_exit = (
                "La lane READY reçoit un run utile, transitionne hors READY, ou repasse à planner"
            )
        else:
            follow_instruction = (
                "Priorité: faire avancer la tache canonique active "
                f"{active_task_id or '<active_task>'} ({active_task_role or 'downstream'}/{active_task_state or 'UNKNOWN'}). "
                "Collect via planner_subagent_manager.py collect; si handoff ack pending, utilise "
                "planner_runtime_actions.py handoff-ack|handoff-close; sinon debloque la lane active. "
                "Aucun nouveau batch, ANALYSIS ou redispatch avant transition."
            )
            follow_why = (
                "Réduit les boucles de redispatch planner quand le vrai travail utile est déjà en "
                "cours sur une lane downstream."
            )
            follow_when = (
                "canonical.active_task_role != planner ou issue_codes contiennent route_mismatch/takeover/ack_pending"
            )
            follow_exit = (
                "La tâche canonique active transitionne hors de IN_PROGRESS/BLOCKED ou repasse à planner"
            )
        follow_patch_id = (
            "follow_api_wave_endpoint"
            if api_wave_enabled and (
                str(active_task_id or "").strip().upper().startswith("BATCH-900-")
                or str(active_task_id or "").strip().upper().startswith("API-WAVE-")
                or str(active_task_id or "").strip().upper().startswith("BATCH-API-")
                or str(active_task_id or "").strip().upper().startswith("APIWAVE-")
            )
            else "follow_canonical_active_task"
        )
        add_patch(
            follow_patch_id,
            priority=80,
            issue_codes=follow_canonical_issue_codes
            + ([f"canonical_active_{active_task_role}"] if active_task_id and active_task_role not in {"", "planner"} else []),
            instruction=follow_instruction,
            why=follow_why,
            when_to_apply=follow_when,
            exit_condition=follow_exit,
            ttl_runs=6,
        )

    if (
        api_wave_enabled
        and isinstance(api_wave_target, dict)
        and api_wave_reason == "route_admin"
    ):
        add_patch(
            "follow_api_wave_endpoint",
            priority=78,
            issue_codes=["api_wave_route_admin"],
            instruction=(
                "API wave bloquee sur un incident runtime/control-plane/public-proof: route vers admin maintenant "
                f"pour {str(api_wave_target.get('endpoint_id') or 'endpoint').strip()}. "
                "Pas de planner-autobatch, pas d'ANALYSIS, pas de micro-batch."
            ),
            why="Les incidents runtime/public-proof doivent etre traites par admin, pas par churn planner.",
            when_to_apply="api_autonomy_mode=1 et api_wave.reason=route_admin",
            exit_condition="La lane admin traite le blocage ou l'endpoint repasse dispatch_ready/deferred",
            ttl_runs=4,
        )

    if (
        api_wave_enabled
        and isinstance(api_wave_target, dict)
        and api_wave_reason == "route_scrum"
    ):
        add_patch(
            "follow_api_wave_endpoint",
            priority=77,
            issue_codes=["api_wave_route_scrum"],
            instruction=(
                "API wave sur deux blocages non runtime consecutifs: route scrum_master maintenant pour "
                f"{str(api_wave_target.get('endpoint_id') or 'endpoint').strip()}, puis reviens au dev ou defer. "
                "Pas d'admin ni de planner-autobatch pour ce cas."
            ),
            why="Scrum sert au debloquage d'acceptance/coordination apres repetition sterile, pas admin.",
            when_to_apply="api_autonomy_mode=1 et api_wave.reason=route_scrum",
            exit_condition="scrum_master debloque l'endpoint ou l'endpoint devient deferred",
            ttl_runs=4,
        )

    if (
        api_wave_enabled
        and isinstance(api_wave_target, dict)
        and api_wave_reason == "defer_current_endpoint"
    ):
        add_patch(
            "defer_api_wave_endpoint",
            priority=76,
            issue_codes=["api_wave_defer_current_endpoint"],
            instruction=(
                "Endpoint API wave non runtime/provider bloque: marque-le deferred et passe au suivant; "
                "pas de reveil admin, pas de planner-autobatch, pas de reouverture batch."
            ),
            why="Maintient la continuité delivery sur la wave sans stopper toute la machine.",
            when_to_apply="api_autonomy_mode=1 et api_wave.reason=defer_current_endpoint",
            exit_condition="Le runtime selectionne l'endpoint suivant eligible",
            ttl_runs=4,
        )

    if (
        api_wave_enabled
        and isinstance(api_wave_target, dict)
        and api_wave_reason == "backoff"
    ):
        add_patch(
            "follow_api_wave_endpoint",
            priority=75,
            issue_codes=["api_wave_backoff"],
            instruction=(
                "Lane API wave sterile: applique un backoff explicite sur "
                f"{str(api_wave_target.get('endpoint_id') or 'endpoint').strip()} et n'ouvre rien de nouveau tant "
                "qu'il n'y a pas de delta runtime/proof."
            ),
            why="Evite le burn none_no_signal/retry/takeover sans effet canonique.",
            when_to_apply="api_autonomy_mode=1 et api_wave.reason=backoff",
            exit_condition="Nouvelle preuve runtime, defer, ou reroute scrum/admin",
            ttl_runs=4,
        )

    if (
        not downstream_active
        and not downstream_ready
        and not hard_guard_active
        and not no_canonical_work
        and (
        "planner_passive_forbidden_violation" in ordered_issues
        or "planner_autobatch_missing_when_idle" in ordered_issues
        or "ready_but_no_delta" in ordered_issues
        or "ready_but_none_task_update" in ordered_issues
        or int(streaks.get("ready_idle_streak", 0) or 0) >= 2
        )
    ):
        if api_wave_enabled and api_wave_dispatch_ready and isinstance(api_wave_target, dict):
            add_patch(
                "dispatch_api_wave_endpoint_now",
                priority=70,
                issue_codes=[
                    "planner_passive_forbidden_violation",
                    "planner_autobatch_missing_when_idle",
                    "ready_but_no_delta",
                    "ready_but_none_task_update",
                ],
                instruction=(
                    "Pas de passivite planner: execute planner_runtime_actions.py api-wave-dispatch maintenant pour "
                    f"{str(api_wave_target.get('endpoint_id') or 'endpoint').strip()}, puis laisse app-dev livrer "
                    "le slice endpoint complet Judge-parity. Pas de planner-autobatch ni tick analysis_only."
                ),
                why=(
                    "Remplace le churn batch-first par une progression directe sur l'endpoint produit prioritaire."
                ),
                when_to_apply=(
                    "api_autonomy_mode=1 et issue_codes contiennent passive/autobatch/ready_but_no_delta"
                ),
                exit_condition=(
                    "Une lane API wave active utile apparaît ou l'endpoint courant est différé"
                ),
                ttl_runs=4,
            )
        elif not api_wave_enabled:
            add_patch(
                "claim_or_autobatch_now",
                priority=70,
                issue_codes=[
                    "planner_passive_forbidden_violation",
                    "planner_autobatch_missing_when_idle",
                    "ready_but_no_delta",
                    "ready_but_none_task_update",
                ],
                instruction=(
                    "Pas de passivite planner: si un READY utile existe, claim-le maintenant. "
                    "Choisis d'abord le slice le plus proche d'un delta visible ou d'un contrat/API livrable "
                    "sur l'app publique EC2. Sinon execute sync-priority, planner-autobatch, puis claim "
                    "immediatement; pas de tick analysis_only ni de maintenance sans impact user."
                ),
                why=(
                    "Remplace les ticks sans delta par une livraison utile ou une création canonique de runway."
                ),
                when_to_apply=(
                    "ready_idle_streak >= 2 ou issue_codes contiennent passive/autobatch/ready_but_no_delta"
                ),
                exit_condition=(
                    "Un claim planner valide ou une tâche downstream active utile apparaît"
                ),
                ttl_runs=4,
            )

    if (
        no_canonical_work
        and delivery_phase in {"product_done_ops_dirty", "idle_ready_for_next_batch"}
        and next_batch_eligible
    ):
        if api_wave_enabled and isinstance(api_wave_target, dict):
            add_patch(
                "idle_ready_for_next_endpoint",
                priority=75,
                issue_codes=[
                    "delivery_phase_product_done_ops_dirty"
                    if delivery_phase == "product_done_ops_dirty"
                    else "delivery_phase_idle_ready_for_next_batch"
                ],
                instruction=(
                    "Runtime canonique idle mais l'API wave est eligible: execute planner_runtime_actions.py "
                    f"api-wave-dispatch pour {str(api_wave_target.get('endpoint_id') or 'endpoint').strip()} "
                    "au lieu d'ouvrir un nouveau batch. Ne reste pas en wait tant que l'app publique EC2 est joignable."
                ),
                why=(
                    "Maintient la continuité delivery en mode API autonomy sans recréer de chaîne ANALYSIS/ARCH/DEV."
                ),
                when_to_apply=(
                    "product_delivery_state.phase=idle_ready_for_next_batch et api_autonomy_mode=1"
                ),
                exit_condition=(
                    "Une lane API wave active apparaît ou l'EC2 publique passe en outage"
                ),
                ttl_runs=4,
            )
        else:
            add_patch(
                "open_next_batch_now",
                priority=75,
                issue_codes=[
                    "delivery_phase_product_done_ops_dirty"
                    if delivery_phase == "product_done_ops_dirty"
                    else "delivery_phase_idle_ready_for_next_batch"
                ],
                instruction=(
                    "Runtime canonique idle mais batch suivant eligible: execute sync-priority, "
                    "planner-autobatch, puis claim immediatement le prochain batch dans ce meme cycle. "
                    "Ne reste pas en wait tant que l'app publique EC2 est joignable."
                ),
                why=(
                    "Evite l'arret a vide apres une livraison publique validee et force la reprise delivery-first."
                ),
                when_to_apply=(
                    "product_delivery_state.phase=idle_ready_for_next_batch et next_batch_eligible=true"
                ),
                exit_condition=(
                    "Un nouveau batch canonique actif apparait ou l'EC2 publique passe en outage"
                ),
                ttl_runs=4,
            )

    if api_wave_enabled and isinstance(api_wave_target, dict) and delivery_phase == "verifying_public_proof":
        add_patch(
            "verify_api_wave_public_proof",
            priority=78,
            issue_codes=["delivery_phase_verifying_public_proof"],
            instruction=(
                "L'endpoint API wave attend sa preuve publique: lance la lane verifier ou planner_runtime_actions.py "
                f"public-proof sur {str(api_wave_target.get('endpoint_id') or 'endpoint').strip()} sans re-dispatch dev/admin."
            ),
            why=(
                "Ferme monotoniquement l'endpoint courant dès que la preuve API publique EC2 est disponible."
            ),
            when_to_apply=(
                "product_delivery_state.phase=verifying_public_proof et api_autonomy_mode=1"
            ),
            exit_condition=(
                "La preuve publique devient ok, l'endpoint est différé, ou la lane verifier repart en active_delivery"
            ),
            ttl_runs=3,
        )

    patches.sort(key=lambda item: (-int(item.get("priority", 0)), str(item.get("id") or "")))
    return patches[:3]


def maybe_emit_directive(
    role: str,
    source: str,
    streaks: Dict[str, int],
    issues: List[str],
    score: int,
    canonical: Dict[str, object],
    runtime: Dict[str, object] | None,
    bus_file: Path,
    state_dir: Path,
) -> None:
    immediate_issues = {"planner_passive_forbidden_violation", "planner_autobatch_missing_when_idle"}
    canonical_task_id = str(canonical.get("active_task_id") or "").strip()
    canonical_task_role = str(canonical.get("active_task_role") or "").strip()
    canonical_task_state = str(canonical.get("active_task_state") or "").strip().upper()
    canonical_task_blocked_reason = str(canonical.get("active_task_blocked_reason") or "").strip()
    canonical_downstream_active = bool(canonical_task_id and canonical_task_role and canonical_task_role != "planner")
    if _no_canonical_work(runtime, canonical):
        immediate_issues.discard("planner_passive_forbidden_violation")
        immediate_issues.discard("planner_autobatch_missing_when_idle")
    if canonical_downstream_active:
        immediate_issues.discard("planner_passive_forbidden_violation")
        immediate_issues.discard("planner_autobatch_missing_when_idle")
    immediate_escalation = any(issue in immediate_issues for issue in issues)
    handoff_loop = streaks.get("handoff_same_task_streak", 0) >= 3
    need_directive = (
        immediate_escalation
        or
        streaks.get("ready_idle_streak", 0) >= 3
        or streaks.get("low_score_streak", 0) >= 3
        or streaks.get("runway_no_batch_streak", 0) >= 3
        or handoff_loop
    )
    if not need_directive:
        return

    if handoff_loop:
        last_task = streaks.get("_last_handoff_task", "unknown")
        message = (
            f"planner_guardian HANDOFF_LOOP: tache '{last_task}' handoffee {streaks['handoff_same_task_streak']} fois sans cloture. "
            "Si la tache est de type GOV_REVIEW ou role=planner, completer toi-meme via task_update=complete. "
            "Ne pas handoff une tache dont tu es l assignee. "
            "Verifier que tous les depends_on sont DONE, puis marquer complete."
        )
    elif canonical_downstream_active:
        blocker_suffix = (
            f" blocker={canonical_task_blocked_reason}."
            if canonical_task_blocked_reason
            else "."
        )
        message = (
            f"planner_guardian canonical_active_task: suivre {canonical_task_id} "
            f"({canonical_task_role}/{canonical_task_state or 'UNKNOWN'}){blocker_suffix} "
            "Ne pas creer de nouveau batch ni relancer ANALYSIS tant que la tache canonique active n a pas transitionne."
        )
    else:
        message = (
            f"planner_guardian escalation: score={score}; issues={','.join(issues) or 'none'}; "
            f"ready_idle_streak={streaks.get('ready_idle_streak', 0)}; "
            f"low_score_streak={streaks.get('low_score_streak', 0)}; "
            f"runway_no_batch_streak={streaks.get('runway_no_batch_streak', 0)}. "
            "Action attendue: claim READY ou creation batch top-level aligne vision+architecture."
        )
    fp = hashlib.sha256(message.encode("utf-8")).hexdigest()
    fp_file = state_dir / f"{role}.planner_guardian.last_directive_fp"
    prev = read_text(fp_file).strip()
    if prev == fp:
        return

    payload = {
        "ts_utc": now_utc(),
        "kind": "policy",
        "source": "planner_guardian",
        "targets": [role],
        "ttl_min": 180,
        "message": one_line(message, 600),
        "meta": {
            "score": score,
            "issues": issues[:8],
            "source_contract": source,
        },
    }
    bus_file.parent.mkdir(parents=True, exist_ok=True)
    with bus_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
    fp_file.write_text(fp + "\n", encoding="utf-8")


def write_latest(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def append_event(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


def write_prompt_patches(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 9:
        print(
            "usage: planner_guardian.py <role> <source> <payload_file> <runtime_context_file> "
            "<latest_file> <events_file> <state_dir> <directive_bus_file>",
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1].strip()
    source = sys.argv[2].strip()
    payload_file = Path(sys.argv[3])
    runtime_context_file = Path(sys.argv[4])
    latest_file = Path(sys.argv[5])
    events_file = Path(sys.argv[6])
    state_dir = Path(sys.argv[7])
    directive_bus_file = Path(sys.argv[8])

    if role != "planner":
        return 0

    contract = parse_contract(read_text(payload_file))
    evidence = parse_evidence_kv(contract.get("EVIDENCE", ""))
    runtime = parse_runtime_context(read_text(runtime_context_file))

    canonical = canonical_active_snapshot(latest_file)
    score_info = compute_score(contract, evidence, runtime, canonical)
    score = int(score_info["score"])
    level = str(score_info["level"])
    issues = [str(item) for item in score_info["issues"]]

    state_file = state_dir / "planner_guardian_state.json"
    state = load_state(state_file)
    streaks_result = update_streaks(state, runtime, contract, evidence, canonical, score)
    streaks, meta = streaks_result if isinstance(streaks_result, tuple) else (streaks_result, {})
    recos = recommendations(issues, canonical)
    patches = build_prompt_patches(issues, canonical, streaks, evidence, runtime)

    payload: Dict[str, object] = {
        "ts_utc": now_utc(),
        "guardian_version": GUARDIAN_VERSION,
        "role": role,
        "source": source,
        "score": score,
        "level": level,
        "issues": issues,
        "recommendations": recos,
        "streaks": streaks,
        "runtime": runtime,
        "canonical": canonical,
        "summary": summarize_contract_for_publication(contract, evidence, runtime, canonical),
    }
    prompt_patches_payload: Dict[str, object] = {
        "ts_utc": payload["ts_utc"],
        "version": PROMPT_PATCHES_VERSION,
        "source": "planner_guardian",
        "score": score,
        "level": level,
        "active": patches,
    }

    state["updated_at_utc"] = payload["ts_utc"]
    state["streaks"] = {**streaks, **meta}  # persist _last_handoff_task alongside streak counts
    state["last_score"] = score
    state["last_level"] = level
    state["last_issues"] = issues[:12]
    save_state(state_file, state)

    write_latest(latest_file, payload)
    write_prompt_patches(planner_prompt_patches_file(latest_file), prompt_patches_payload)
    append_event(events_file, payload)
    maybe_emit_directive(
        role=role,
        source=source,
        streaks=streaks,
        issues=issues,
        score=score,
        canonical=canonical,
        runtime=runtime,
        bus_file=directive_bus_file,
        state_dir=state_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
