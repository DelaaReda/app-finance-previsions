#!/usr/bin/env python3
"""Parallel workstream board for multi-role delivery orchestration.

This script keeps a local task mesh so specialized roles can work in parallel
while preserving explicit dependencies, handoffs, and validation ownership.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import random
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DEFAULT_BOARD = Path("docs/orchestrator-ops/parallel-workstreams.json")
DEFAULT_PRIORITY_QUEUE = Path("docs/orchestrator-ops/priority-queue.json")
DEFAULT_PROOF_ROOT = Path("docs/orchestrator-ops/proofs")


@contextmanager
def board_lock(board_path: Path):
    """Global board lock to keep multi-role writes deterministic."""
    board_text = str(board_path or "").strip()
    # Defensive: avoid creating weird "..lock" when board_path is empty (Path("") -> ".").
    if board_text in {"", ".", "./"}:
        board_path = DEFAULT_BOARD
        board_text = str(board_path)
    lock_path = Path(f"{board_text}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

STATE_BACKLOG = "BACKLOG"
STATE_WAITING_DEP = "WAITING_DEP"
STATE_READY = "READY"
STATE_IN_PROGRESS = "IN_PROGRESS"
STATE_REVIEW = "REVIEW"
STATE_DONE = "DONE"
STATE_BLOCKED = "BLOCKED"

ACTIVE_STATES = {STATE_IN_PROGRESS, STATE_REVIEW}
READY_LIKE_STATES = {STATE_BACKLOG, STATE_WAITING_DEP, STATE_READY}

ROLE_CATALOG: Dict[str, Dict[str, object]] = {
    "planner": {"wip_limit": 2, "can_edit": False, "focus": "vision conformance mentoring and dispatch hygiene"},
    "analyst": {"wip_limit": 3, "can_edit": False, "focus": "requirements and assumptions"},
    "architect": {"wip_limit": 2, "can_edit": False, "focus": "constraints and design"},
    "backend_engineer": {"wip_limit": 3, "can_edit": True, "focus": "api and backend impl"},
    "frontend_engineer": {"wip_limit": 3, "can_edit": True, "focus": "ui and frontend impl"},
    "data_analyst": {"wip_limit": 2, "can_edit": True, "focus": "data quality and metrics"},
    "infra_engineer": {"wip_limit": 2, "can_edit": True, "focus": "infra and ci/cd"},
    "integrator": {"wip_limit": 2, "can_edit": True, "focus": "cross-team integration"},
    "dev": {"wip_limit": 2, "can_edit": True, "focus": "cross-cutting implementation and debt"},
    "tester": {"wip_limit": 3, "can_edit": True, "focus": "test automation and checks"},
    "qa": {"wip_limit": 3, "can_edit": True, "focus": "quality gate and validation"},
    "po": {"wip_limit": 2, "can_edit": False, "focus": "scope and value"},
    "scrum_master": {"wip_limit": 2, "can_edit": False, "focus": "flow and blockers"},
    "clawsentinel": {"wip_limit": 2, "can_edit": False, "focus": "anti-drift and safety"},
}


@dataclass(frozen=True)
class TemplateStep:
    code: str
    role: str
    deps: Tuple[str, ...]


STREAM_TEMPLATE: Tuple[TemplateStep, ...] = (
    TemplateStep("PLAN", "planner", tuple()),
    TemplateStep("ANALYSIS", "analyst", ("PLAN",)),
    TemplateStep("ARCH", "architect", ("ANALYSIS",)),
    TemplateStep("QA_PREP", "qa", ("PLAN",)),
    TemplateStep("TEST_PLAN", "tester", ("PLAN",)),
    TemplateStep("DATA", "data_analyst", ("ANALYSIS",)),
    TemplateStep("INFRA", "infra_engineer", ("ARCH",)),
    TemplateStep("BACKEND", "backend_engineer", ("ARCH",)),
    TemplateStep("FRONTEND", "frontend_engineer", ("ARCH",)),
    TemplateStep("INTEGRATION", "integrator", ("BACKEND", "FRONTEND", "INFRA", "DATA")),
    TemplateStep("QA_EXEC", "qa", ("INTEGRATION", "QA_PREP", "TEST_PLAN")),
    TemplateStep("SENTINEL_CHECK", "clawsentinel", ("QA_EXEC",)),
    TemplateStep("SCRUM_REVIEW", "scrum_master", ("PLAN",)),
    TemplateStep("PO_REVIEW", "po", ("QA_EXEC", "SENTINEL_CHECK")),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def priority_rank(value: str) -> int:
    value = (value or "").strip().upper()
    ranks = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return ranks.get(value, 9)


def task_id(stream_id: str, code: str) -> str:
    return f"{stream_id}-{code}"


def _normalize_verdict(value: str) -> str:
    token = (value or "").strip().upper()
    if token in {"GO", "PASS"}:
        return "PASS"
    if token in {"BLOCKED", "FAIL"}:
        return "BLOCKED"
    if token == "GO_WITH_CAUTION":
        return "GO_WITH_CAUTION"
    return "GO_WITH_CAUTION"


def _tests_result(value: str) -> str:
    token = (value or "").strip().upper()
    if "FAIL" in token:
        return "FAIL"
    if token.startswith("SKIP(") or token.startswith("SKIP"):
        return "SKIP"
    return "PASS"


def _yaml_quote(value: str) -> str:
    text = str(value or "")
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return f"\"{text}\""


def _auto_idempotency_key(role: str, task_id_value: str, handoff_to: str) -> str:
    seed = f"{role}|{task_id_value}|{handoff_to}|{now_iso()}|{random.randint(1000,9999)}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"IK-{digest}"


def _write_proof_manifest(
    proof_root: Path,
    task: dict,
    role: str,
    artifact: str,
    note: str,
    handoff_to: str,
    handoff_id: str,
    cmd: str,
    tests_run: str,
    review_ref: str,
    reviewer_role: str,
    review_verdict: str,
    idempotency_key: str,
) -> str:
    stream_id_value = str(task.get("stream_id", "UNSET")).strip() or "UNSET"
    task_id_value = str(task.get("id", "UNKNOWN")).strip() or "UNKNOWN"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = random.randint(100, 999)
    manifest_dir = proof_root / stream_id_value / task_id_value
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{stamp}-{suffix}.yaml"

    cmd_value = (cmd or "").strip() or "SKIP(no_cmd_recorded)"
    tests_value = (tests_run or "").strip() or "SKIP(no_tests_recorded)"
    rc_value = "0" if not cmd_value.upper().startswith("SKIP(") else "SKIP(reasoned)"
    review_ref_value = (review_ref or "").strip() or "none"
    reviewer_value = (reviewer_role or "").strip() or "none"
    verdict_value = _normalize_verdict(review_verdict)
    tests_result = _tests_result(tests_value)
    artifact_value = (artifact or "").strip() or "none"
    note_value = (note or "").strip() or "none"
    proof_id = f"PRF-{stream_id_value}-{task_id_value}-{stamp}-{suffix}"
    produced = now_iso()
    handoff_to_value = (handoff_to or "").strip() or "none"
    handoff_id_value = (handoff_id or "").strip() or "none"

    lines = [
        f"proof_id: {_yaml_quote(proof_id)}",
        f"stream_id: {_yaml_quote(stream_id_value)}",
        f"task_id: {_yaml_quote(task_id_value)}",
        f"role: {_yaml_quote(role)}",
        f"produced_at_utc: {_yaml_quote(produced)}",
        "inputs:",
        f"  queue_snapshot_ref: {_yaml_quote(str(DEFAULT_PRIORITY_QUEUE))}",
        f"  workboard_snapshot_ref: {_yaml_quote(str(DEFAULT_BOARD))}",
        f"  prior_contract_ref: {_yaml_quote(f'/home/venom/.openclaw/cron/role-state/{role}.last_contract')}",
        "execution:",
        "  commands:",
        f"    - cmd: {_yaml_quote(cmd_value)}",
        f"      rc: {_yaml_quote(rc_value)}",
        f"      started_at_utc: {_yaml_quote(produced)}",
        f"      ended_at_utc: {_yaml_quote(produced)}",
        "validations:",
        "  tests:",
        f"    - name: {_yaml_quote('targeted')}",
        f"      result: {_yaml_quote(tests_result)}",
        f"      evidence: {_yaml_quote(tests_value)}",
        "outputs:",
        f"  role_contract_ref: {_yaml_quote(f'/home/venom/.openclaw/cron/role-state/{role}.last_contract')}",
        "  artifacts:",
        f"    - {_yaml_quote(artifact_value)}",
        "handoff:",
        f"  to_role: {_yaml_quote(handoff_to_value)}",
        f"  handoff_id: {_yaml_quote(handoff_id_value)}",
        "signoff:",
        f"  producer_agent: {_yaml_quote(role)}",
        f"  reviewer_agent: {_yaml_quote(reviewer_value)}",
        f"  qa_verdict: {_yaml_quote(verdict_value)}",
        "meta:",
        f"  idempotency_key: {_yaml_quote(idempotency_key)}",
        f"  review_ref: {_yaml_quote(review_ref_value)}",
        f"  note: {_yaml_quote(note_value)}",
    ]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(manifest_path)


def load_board(path: Path) -> dict:
    if not path.exists():
        return default_board()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"BOARD_READ_ERROR: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"BOARD_SCHEMA_ERROR: {path} root must be object")
    data.setdefault("version", 1)
    data.setdefault("updated_at", now_iso())
    data.setdefault("sprint", {"id": "S-UNSET", "goal": ""})
    data.setdefault("roles", ROLE_CATALOG)
    data.setdefault("streams", [])
    data.setdefault("tasks", [])
    data.setdefault("handoffs", [])
    data.setdefault("events", [])
    return data


def save_board(path: Path, board: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    board["updated_at"] = now_iso()
    path.write_text(json.dumps(board, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def default_board() -> dict:
    return {
        "version": 1,
        "updated_at": now_iso(),
        "sprint": {
            "id": "S-BOOTSTRAP",
            "goal": "Accélérer la livraison parallèle sans désordre",
            "cadence_days": 14,
        },
        "roles": ROLE_CATALOG,
        "streams": [],
        "tasks": [],
        "handoffs": [],
        "events": [],
    }


def append_event(board: dict, kind: str, details: dict) -> None:
    board.setdefault("events", []).append({
        "at": now_iso(),
        "kind": kind,
        "details": details,
    })


def task_index(board: dict) -> Dict[str, dict]:
    return {str(task.get("id")): task for task in board.get("tasks", [])}


def stream_index(board: dict) -> Dict[str, dict]:
    return {str(stream.get("id")): stream for stream in board.get("streams", [])}


def ensure_stream(board: dict, stream_id: str, title: str, priority: str, source_state: str) -> int:
    streams = stream_index(board)
    tasks = task_index(board)
    created = 0
    if stream_id not in streams:
        board.setdefault("streams", []).append(
            {
                "id": stream_id,
                "title": title,
                "priority": priority,
                "source_state": source_state,
                "state": STATE_READY,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
    else:
        stream = streams[stream_id]
        stream["title"] = title
        stream["priority"] = priority
        stream["source_state"] = source_state
        stream["updated_at"] = now_iso()

    for step in STREAM_TEMPLATE:
        tid = task_id(stream_id, step.code)
        if tid in tasks:
            continue
        deps = [task_id(stream_id, dep) for dep in step.deps]
        init_state = STATE_READY if not deps else STATE_WAITING_DEP
        board.setdefault("tasks", []).append(
            {
                "id": tid,
                "stream_id": stream_id,
                "code": step.code,
                "title": f"{title} [{step.code}]",
                "role": step.role,
                "state": init_state,
                "priority": priority,
                "depends_on": deps,
                "assignee": "",
                "blocked_reason": "",
                "artifacts": [],
                "notes": [],
                "handoff_to": "",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "started_at": "",
                "completed_at": "",
            }
        )
        created += 1
    return created


def recompute_states(board: dict) -> None:
    tasks_by_id = task_index(board)
    for task in board.get("tasks", []):
        state = str(task.get("state", ""))
        if state in {STATE_DONE, STATE_BLOCKED, STATE_IN_PROGRESS, STATE_REVIEW}:
            continue
        deps = [dep for dep in task.get("depends_on", []) if dep]
        deps_done = all(tasks_by_id.get(dep, {}).get("state") == STATE_DONE for dep in deps)
        new_state = task.get("state", STATE_BACKLOG)
        if deps_done:
            if state in READY_LIKE_STATES:
                new_state = STATE_READY
        else:
            if state in READY_LIKE_STATES:
                new_state = STATE_WAITING_DEP
        if new_state != state:
            task["state"] = new_state
            task["updated_at"] = now_iso()

    tasks_by_stream: Dict[str, List[dict]] = {}
    for task in board.get("tasks", []):
        stream_id = str(task.get("stream_id", ""))
        tasks_by_stream.setdefault(stream_id, []).append(task)

    for stream in board.get("streams", []):
        stream_id = str(stream.get("id", ""))
        stream_tasks = tasks_by_stream.get(stream_id, [])
        states = {str(task.get("state", "")) for task in stream_tasks}
        if stream_tasks and states == {STATE_DONE}:
            stream_state = STATE_DONE
        elif STATE_BLOCKED in states:
            stream_state = STATE_BLOCKED
        elif STATE_IN_PROGRESS in states or STATE_REVIEW in states:
            stream_state = STATE_IN_PROGRESS
        elif STATE_READY in states:
            stream_state = STATE_READY
        else:
            stream_state = STATE_WAITING_DEP
        if stream.get("state") != stream_state:
            stream["state"] = stream_state
            stream["updated_at"] = now_iso()


def sync_from_priority_queue(board: dict, queue_path: Path, include_pass: bool = False) -> Tuple[int, int]:
    if not queue_path.exists():
        raise SystemExit(f"QUEUE_MISSING: {queue_path}")
    try:
        queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"QUEUE_READ_ERROR: {queue_path}: {exc}") from exc

    eligible = {"READY", "IN_PROGRESS"}
    if include_pass:
        eligible.add("PASS")

    created_streams = 0
    created_tasks = 0
    existing_streams = stream_index(board)
    for item in queue_obj.get("items", []):
        stream_id = str(item.get("id", "")).strip().upper()
        state = str(item.get("state", "")).strip().upper()
        if not stream_id or state not in eligible:
            continue
        title = str(item.get("title", stream_id)).strip() or stream_id
        priority = str(item.get("priority", "P2")).strip().upper() or "P2"
        if stream_id not in existing_streams:
            created_streams += 1
        created_tasks += ensure_stream(board, stream_id, title, priority, state)
        existing_streams = stream_index(board)

    recompute_states(board)
    if created_streams > 0 or created_tasks > 0:
        append_event(
            board,
            "sync_priority_queue",
            {
                "queue": str(queue_path),
                "created_streams": created_streams,
                "created_tasks": created_tasks,
            },
        )
    return created_streams, created_tasks


def iter_tasks_for_role(board: dict, role: str) -> Iterable[dict]:
    return (task for task in board.get("tasks", []) if str(task.get("role", "")) == role)


def role_wip_count(board: dict, role: str) -> int:
    return sum(1 for task in iter_tasks_for_role(board, role) if str(task.get("state", "")) in ACTIVE_STATES)


def claim_task(board: dict, role: str, task_id_override: str | None = None) -> dict:
    tasks = list(iter_tasks_for_role(board, role))
    candidates = [task for task in tasks if str(task.get("state", "")) == STATE_READY]
    candidates.sort(key=lambda t: (priority_rank(str(t.get("priority", "P9"))), str(t.get("stream_id", "")), str(t.get("code", ""))))

    if task_id_override:
        match = next((task for task in candidates if str(task.get("id", "")) == task_id_override), None)
        if match is None:
            raise SystemExit(f"CLAIM_ERROR: task {task_id_override} not READY for role {role}")
        chosen = match
    else:
        if not candidates:
            raise SystemExit(f"NO_READY_TASK: role={role}")
        chosen = candidates[0]

    role_conf = board.get("roles", {}).get(role, {})
    wip_limit = int(role_conf.get("wip_limit", 2))
    if role_wip_count(board, role) >= wip_limit:
        raise SystemExit(f"WIP_LIMIT_REACHED: role={role} limit={wip_limit}")

    chosen["state"] = STATE_IN_PROGRESS
    chosen["assignee"] = role
    chosen["started_at"] = chosen.get("started_at") or now_iso()
    chosen["updated_at"] = now_iso()
    append_event(board, "claim", {"role": role, "task_id": chosen.get("id")})
    recompute_states(board)
    return chosen


def complete_task(
    board: dict,
    role: str,
    task_id_value: str,
    artifact: str,
    note: str,
    handoff_to: str,
    proof_root: Path,
    cmd: str,
    tests_run: str,
    review_ref: str,
    reviewer_role: str,
    review_verdict: str,
    idempotency_key: str,
) -> dict:
    tasks = task_index(board)
    task = tasks.get(task_id_value)
    if task is None:
        raise SystemExit(f"COMPLETE_ERROR: task_not_found={task_id_value}")
    task_role = str(task.get("role", ""))
    if task_role != role:
        raise SystemExit(f"COMPLETE_ERROR: role_mismatch task_role={task_role} caller_role={role}")

    if str(task.get("state", "")) not in {STATE_IN_PROGRESS, STATE_READY, STATE_REVIEW}:
        raise SystemExit(f"COMPLETE_ERROR: invalid_state={task.get('state')} task={task_id_value}")

    deps = [dep for dep in task.get("depends_on", []) if dep]
    not_done = [dep for dep in deps if str(tasks.get(dep, {}).get("state", "")) != STATE_DONE]
    if not_done:
        raise SystemExit(f"COMPLETE_ERROR: deps_not_done={','.join(not_done)} task={task_id_value}")

    effective_idempotency = (idempotency_key or "").strip() or _auto_idempotency_key(role, task_id_value, handoff_to)
    task["last_idempotency_key"] = effective_idempotency

    task["state"] = STATE_DONE
    task["completed_at"] = now_iso()
    task["updated_at"] = now_iso()
    task["blocked_reason"] = ""
    if artifact:
        task.setdefault("artifacts", []).append(artifact)
    if note:
        task.setdefault("notes", []).append(note)

    handoff_id = ""
    if handoff_to:
        handoff_id = f"HO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
        board.setdefault("handoffs", []).append(
            {
                "id": handoff_id,
                "task_id": task_id_value,
                "stream_id": task.get("stream_id"),
                "from_role": role,
                "to_role": handoff_to,
                "status": "OPEN",
                "note": note,
                "idempotency_key": effective_idempotency,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
        task["handoff_to"] = handoff_to

    manifest_path = _write_proof_manifest(
        proof_root=proof_root,
        task=task,
        role=role,
        artifact=artifact,
        note=note,
        handoff_to=handoff_to,
        handoff_id=handoff_id,
        cmd=cmd,
        tests_run=tests_run,
        review_ref=review_ref,
        reviewer_role=reviewer_role,
        review_verdict=review_verdict,
        idempotency_key=effective_idempotency,
    )
    task.setdefault("proof_manifests", []).append(manifest_path)
    note_kv = (
        f"cmd={(cmd or '').strip() or 'SKIP(no_cmd_recorded)'};"
        f"tests_run={(tests_run or '').strip() or 'SKIP(no_tests_recorded)'};"
        f"review_ref={(review_ref or '').strip() or 'none'};"
        f"review_verdict={_normalize_verdict(review_verdict)};"
        f"proof_manifest={manifest_path}"
    )
    task.setdefault("notes", []).append(note_kv)

    append_event(
        board,
        "complete",
        {
            "role": role,
            "task_id": task_id_value,
            "artifact": artifact,
            "handoff_to": handoff_to or "none",
            "handoff_id": handoff_id or "none",
            "proof_manifest": manifest_path,
            "idempotency_key": effective_idempotency,
        },
    )
    recompute_states(board)
    return task


def set_block_state(board: dict, task_id_value: str, reason: str, blocked: bool) -> dict:
    tasks = task_index(board)
    task = tasks.get(task_id_value)
    if task is None:
        raise SystemExit(f"TASK_NOT_FOUND: {task_id_value}")
    if blocked:
        task["state"] = STATE_BLOCKED
        task["blocked_reason"] = reason or "blocked_without_reason"
    else:
        if str(task.get("state", "")) == STATE_BLOCKED:
            task["state"] = STATE_WAITING_DEP
        task["blocked_reason"] = ""
    task["updated_at"] = now_iso()
    append_event(board, "block" if blocked else "unblock", {"task_id": task_id_value, "reason": reason})
    recompute_states(board)
    return task


def handoff_update(board: dict, handoff_id: str, status: str, actor_role: str) -> dict:
    handoffs = [h for h in board.get("handoffs", []) if str(h.get("id", "")) == handoff_id]
    if not handoffs:
        raise SystemExit(f"HANDOFF_NOT_FOUND: {handoff_id}")
    handoff = handoffs[0]
    to_role = str(handoff.get("to_role", ""))
    if status == "ACK" and actor_role and actor_role != to_role:
        raise SystemExit(f"HANDOFF_ACK_ROLE_MISMATCH: expected={to_role} got={actor_role}")
    handoff["status"] = status
    handoff["updated_at"] = now_iso()
    append_event(board, "handoff_update", {"handoff_id": handoff_id, "status": status, "actor": actor_role})
    return handoff


def enforce_handoff_sla(board: dict, ack_sla_seconds: int, close_sla_seconds: int, apply: bool) -> dict:
    now = datetime.now(timezone.utc)
    tasks = task_index(board)
    summary = {
        "open_total": 0,
        "ack_total": 0,
        "ack_overdue": 0,
        "close_overdue": 0,
        "escalated": 0,
        "blocked_tasks": 0,
    }

    for handoff in board.get("handoffs", []):
        status = str(handoff.get("status", "")).upper()
        if status not in {"OPEN", "ACK"}:
            continue
        created = _parse_utc(str(handoff.get("created_at", ""))) or _parse_utc(str(handoff.get("updated_at", "")))
        if created is None:
            continue
        age_seconds = int((now - created).total_seconds())
        hid = str(handoff.get("id", ""))
        task_ref = str(handoff.get("task_id", ""))

        if status == "OPEN":
            summary["open_total"] += 1
            if age_seconds > ack_sla_seconds:
                summary["ack_overdue"] += 1
                if apply:
                    handoff["sla_state"] = "ACK_OVERDUE"
                    handoff["owner"] = "scrum_master"
                    handoff["updated_at"] = now_iso()
                    append_event(
                        board,
                        "handoff_sla_escalation",
                        {"handoff_id": hid, "severity": "WARN", "reason": "ACK_OVERDUE", "owner": "scrum_master"},
                    )
                    summary["escalated"] += 1
            if age_seconds > close_sla_seconds:
                summary["close_overdue"] += 1
                if apply:
                    handoff["sla_state"] = "CLOSE_OVERDUE"
                    handoff["owner"] = "scrum_master"
                    handoff["updated_at"] = now_iso()
                    append_event(
                        board,
                        "handoff_sla_escalation",
                        {"handoff_id": hid, "severity": "BLOCKED", "reason": "CLOSE_OVERDUE", "owner": "scrum_master"},
                    )
                    summary["escalated"] += 1
                    task = tasks.get(task_ref)
                    if task is not None and str(task.get("state", "")) in {STATE_READY, STATE_IN_PROGRESS, STATE_REVIEW}:
                        task["state"] = STATE_BLOCKED
                        task["blocked_reason"] = f"handoff_close_sla_exceeded:{hid}"
                        task["updated_at"] = now_iso()
                        summary["blocked_tasks"] += 1
        elif status == "ACK":
            summary["ack_total"] += 1
            ack_at = _parse_utc(str(handoff.get("updated_at", ""))) or created
            ack_age = int((now - ack_at).total_seconds())
            if ack_age > close_sla_seconds:
                summary["close_overdue"] += 1
                if apply:
                    handoff["sla_state"] = "CLOSE_OVERDUE_AFTER_ACK"
                    handoff["owner"] = "scrum_master"
                    handoff["updated_at"] = now_iso()
                    append_event(
                        board,
                        "handoff_sla_escalation",
                        {"handoff_id": hid, "severity": "BLOCKED", "reason": "CLOSE_OVERDUE_AFTER_ACK", "owner": "scrum_master"},
                    )
                    summary["escalated"] += 1
    if apply:
        recompute_states(board)
    return summary


def _parse_utc(value: str) -> datetime | None:
    raw = (value or "").strip()
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


def _queue_ready_count(queue_path: Path) -> int:
    if not queue_path.exists():
        return 0
    try:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    return sum(1 for item in payload.get("items", []) if str(item.get("state", "")).upper() == STATE_READY)


def _queue_state_map(queue_path: Path) -> Dict[str, str]:
    if not queue_path.exists():
        return {}
    try:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    states: Dict[str, str] = {}
    for item in payload.get("items", []):
        sid = str(item.get("id", "")).strip().upper()
        if not sid:
            continue
        states[sid] = str(item.get("state", "")).strip().upper()
    return states


def _artifact_ref_exists(raw: str) -> bool:
    value = (raw or "").strip()
    if not value:
        return False
    lower = value.lower()
    if lower.startswith(("http://", "https://", "proof:", "inline:")):
        return True
    path = Path(value).expanduser()
    return path.exists()


def _manifest_required_keys_present(text: str) -> List[str]:
    required = [
        "proof_id:",
        "stream_id:",
        "task_id:",
        "role:",
        "produced_at_utc:",
        "execution:",
        "outputs:",
        "signoff:",
    ]
    upper = text.upper()
    missing = []
    for key in required:
        if key.upper() not in upper:
            missing.append(key.rstrip(":"))
    return missing


def _validate_manifest_file(manifest_path: Path) -> List[str]:
    issues: List[str] = []
    if not manifest_path.exists():
        issues.append(f"MANIFEST_NOT_FOUND:{manifest_path}")
        return issues
    try:
        text = manifest_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        issues.append(f"MANIFEST_READ_ERROR:{manifest_path}:{exc}")
        return issues
    missing = _manifest_required_keys_present(text)
    if missing:
        issues.append(f"MANIFEST_MISSING_KEYS:{manifest_path}:{','.join(missing)}")
    verdict_match = "QA_VERDICT:" in text.upper()
    if not verdict_match:
        issues.append(f"MANIFEST_MISSING_QA_VERDICT:{manifest_path}")
    return issues


def validate_board(
    board: dict,
    queue_path: Path,
    ack_sla_seconds: int,
    close_sla_seconds: int,
    proof_root: Path,
    require_proof_manifest: bool,
    in_progress_stale_seconds: int,
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    tasks = board.get("tasks", [])
    seen = set()
    idx = task_index(board)
    done_roles_need_test_evidence = {
        "dev",
        "backend_engineer",
        "frontend_engineer",
        "integrator",
        "data_analyst",
        "infra_engineer",
        "tester",
        "qa",
    }

    for task in tasks:
        tid = str(task.get("id", ""))
        if not tid:
            errors.append("TASK_WITHOUT_ID")
            continue
        if tid in seen:
            errors.append(f"DUPLICATE_TASK_ID:{tid}")
        seen.add(tid)
        role = str(task.get("role", ""))
        if role not in ROLE_CATALOG:
            errors.append(f"UNKNOWN_ROLE:{tid}:{role}")
        for dep in task.get("depends_on", []):
            if dep not in idx:
                errors.append(f"MISSING_DEP:{tid}:{dep}")
        state = str(task.get("state", ""))
        if state == STATE_READY:
            deps = task.get("depends_on", [])
            not_done = [dep for dep in deps if idx.get(dep, {}).get("state") != STATE_DONE]
            if not_done:
                errors.append(f"READY_WITH_OPEN_DEPS:{tid}:{','.join(not_done)}")
        if state == STATE_DONE:
            artifacts = [str(a).strip() for a in task.get("artifacts", []) if str(a).strip()]
            if not artifacts:
                errors.append(f"INV-DONE-PROOF:NO_ARTIFACT:task={tid}:owner=qa:remediation=done_to_review")
            else:
                existing = [a for a in artifacts if _artifact_ref_exists(a)]
                if not existing:
                    refs = ",".join(artifacts[:3])
                    errors.append(f"INV-DONE-PROOF:ARTIFACT_NOT_FOUND:task={tid}:refs={refs}:owner=qa:remediation=fix_artifact_ref")
            if role in done_roles_need_test_evidence:
                notes_blob = " ".join(str(n) for n in task.get("notes", [])).upper()
                if "CMD=" not in notes_blob and "TESTS_RUN=" not in notes_blob and "SKIP(" not in notes_blob:
                    warnings.append(
                        f"INV-DONE-PROOF-WARN:MISSING_CMD_TEST_EVIDENCE:task={tid}:owner=qa:remediation=add_cmd_tests_or_skip_reason"
                    )
            manifests = [str(p).strip() for p in task.get("proof_manifests", []) if str(p).strip()]
            if not manifests:
                msg = f"INV-DONE-PROOF-MANIFEST:task={tid}:owner=qa:remediation=attach_proof_manifest"
                if require_proof_manifest:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            else:
                for manifest_raw in manifests:
                    manifest_path = Path(manifest_raw)
                    if not manifest_path.is_absolute():
                        candidate = (Path(".") / manifest_path).resolve()
                        if candidate.exists():
                            manifest_path = candidate
                        else:
                            manifest_path = (proof_root / manifest_path.name).resolve()
                    for issue in _validate_manifest_file(manifest_path):
                        if "MISSING_KEYS" in issue or "MISSING_QA_VERDICT" in issue:
                            errors.append(f"INV-DONE-PROOF:{tid}:{issue}")
                        else:
                            warnings.append(f"INV-DONE-PROOF-WARN:{tid}:{issue}")

    # INV-READY-SYNC (WARN): queue/workboard drift signal.
    queue_states = _queue_state_map(queue_path)
    ready_tasks = []
    for task in tasks:
        if str(task.get("state", "")) != STATE_READY:
            continue
        stream_id = str(task.get("stream_id", "")).strip().upper()
        # Ignore READY tasks belonging to streams already marked PASS in the queue.
        if stream_id and queue_states.get(stream_id, "") == "PASS":
            continue
        ready_tasks.append(str(task.get("id", "")))
    queue_ready = _queue_ready_count(queue_path)
    if queue_ready == 0 and ready_tasks:
        sample = ",".join([tid for tid in ready_tasks if tid][:5]) or "none"
        warnings.append(
            f"INV-READY-SYNC:owner=scrum_master:queue_ready=0:board_ready={len(ready_tasks)}:sample={sample}:remediation=sync-priority"
        )

    # INV-QUEUE-CLOSED-WITH-OPEN-TASKS (WARN): stream marked PASS/CLOSED in queue while actionable tasks remain.
    actionable_states = {STATE_READY, STATE_IN_PROGRESS, STATE_REVIEW, STATE_BLOCKED}
    stream_open_tasks: Dict[str, List[str]] = {}
    for task in tasks:
        state = str(task.get("state", ""))
        if state not in actionable_states:
            continue
        stream_id = str(task.get("stream_id", "")).strip().upper()
        if not stream_id:
            continue
        stream_open_tasks.setdefault(stream_id, []).append(str(task.get("id", "")))

    for stream_id, task_ids in sorted(stream_open_tasks.items()):
        queue_state = queue_states.get(stream_id, "")
        if queue_state not in {"PASS", "CLOSED"}:
            continue
        sample = ",".join([tid for tid in task_ids if tid][:5]) or "none"
        warnings.append(
            "INV-QUEUE-CLOSED-WITH-OPEN-TASKS:"
            f"stream={stream_id}:queue_state={queue_state}:open_tasks={len(task_ids)}:sample={sample}:"
            "owner=scrum_master:remediation=reopen_queue_or_close_workboard_tasks"
        )

    now = datetime.now(timezone.utc)
    for handoff in board.get("handoffs", []):
        task_ref = str(handoff.get("task_id", ""))
        hid = str(handoff.get("id", ""))
        if task_ref and task_ref not in idx:
            errors.append(f"HANDOFF_TASK_MISSING:{hid}:{task_ref}")
        if not str(handoff.get("idempotency_key", "")).strip():
            warnings.append(f"HANDOFF_IDEMPOTENCY_MISSING:handoff={hid}:owner=scrum_master:remediation=attach_idempotency_key")
        status = str(handoff.get("status", "")).upper()
        created_at = _parse_utc(str(handoff.get("created_at", ""))) or _parse_utc(str(handoff.get("updated_at", "")))
        if created_at is None:
            if status in {"OPEN", "ACK"}:
                warnings.append(f"INV-HANDOFF-SLA:INVALID_TIMESTAMP:handoff={hid}:owner=scrum_master:remediation=repair_timestamps")
            continue
        age_seconds = int((now - created_at).total_seconds())
        if status == "OPEN":
            if age_seconds > close_sla_seconds:
                errors.append(
                    f"INV-HANDOFF-SLA:CLOSE_OVERDUE:handoff={hid}:age={age_seconds}s:owner=scrum_master:remediation=escalate_and_reduce_wip"
                )
            elif age_seconds > ack_sla_seconds:
                warnings.append(
                    f"INV-HANDOFF-SLA:ACK_OVERDUE:handoff={hid}:age={age_seconds}s:owner=scrum_master:remediation=handoff-ack_or_reassign"
                )
        elif status == "ACK":
            ack_at = _parse_utc(str(handoff.get("updated_at", ""))) or created_at
            ack_age = int((now - ack_at).total_seconds())
            if ack_age > close_sla_seconds:
                warnings.append(
                    f"INV-HANDOFF-SLA:CLOSE_OVERDUE_AFTER_ACK:handoff={hid}:age={ack_age}s:owner=scrum_master:remediation=handoff-close_or_reassign"
                )

    for task in tasks:
        if str(task.get("state", "")) != STATE_IN_PROGRESS:
            continue
        tid = str(task.get("id", ""))
        ref_time = _parse_utc(str(task.get("updated_at", ""))) or _parse_utc(str(task.get("started_at", "")))
        if ref_time is None:
            continue
        age_seconds = int((now - ref_time).total_seconds())
        if age_seconds > in_progress_stale_seconds:
            warnings.append(
                f"INV-INPROGRESS-STALE:task={tid}:age={age_seconds}s:owner=scrum_master:remediation=reclaim_or_close"
            )

    return errors, warnings


def print_status(board: dict, role: str, compact: bool, limit: int) -> None:
    tasks = board.get("tasks", [])
    summary = {
        "total": len(tasks),
        "ready": sum(1 for t in tasks if t.get("state") == STATE_READY),
        "in_progress": sum(1 for t in tasks if t.get("state") == STATE_IN_PROGRESS),
        "blocked": sum(1 for t in tasks if t.get("state") == STATE_BLOCKED),
        "done": sum(1 for t in tasks if t.get("state") == STATE_DONE),
        "open_handoffs": sum(1 for h in board.get("handoffs", []) if h.get("status") == "OPEN"),
    }

    if compact:
        if role:
            r_tasks = list(iter_tasks_for_role(board, role))
            r_ready = [t for t in r_tasks if t.get("state") == STATE_READY]
            r_active = [t for t in r_tasks if t.get("state") in ACTIVE_STATES]
            r_blocked = [t for t in r_tasks if t.get("state") == STATE_BLOCKED]
            head = (
                f"ROLE={role} total={len(r_tasks)} ready={len(r_ready)} in_progress={len(r_active)} "
                f"blocked={len(r_blocked)} open_handoffs={summary['open_handoffs']}"
            )
            lines = [head]
            for task in sorted(r_ready, key=lambda t: (priority_rank(str(t.get("priority", "P9"))), str(t.get("id", ""))))[:limit]:
                lines.append(
                    f"READY task={task.get('id')} prio={task.get('priority')} stream={task.get('stream_id')} deps={len(task.get('depends_on', []))}"
                )
            print("\n".join(lines))
            return

        print(
            f"SUMMARY total={summary['total']} ready={summary['ready']} in_progress={summary['in_progress']} "
            f"blocked={summary['blocked']} done={summary['done']} open_handoffs={summary['open_handoffs']}"
        )
        return

    out = {
        "summary": summary,
        "by_role": {},
        "open_handoffs": [h for h in board.get("handoffs", []) if h.get("status") == "OPEN"],
    }
    for role_name in ROLE_CATALOG:
        role_tasks = list(iter_tasks_for_role(board, role_name))
        out["by_role"][role_name] = {
            "total": len(role_tasks),
            "ready": [t for t in role_tasks if t.get("state") == STATE_READY][:limit],
            "in_progress": [t for t in role_tasks if t.get("state") in ACTIVE_STATES][:limit],
            "blocked": [t for t in role_tasks if t.get("state") == STATE_BLOCKED][:limit],
        }
    if role:
        out = {
            "role": role,
            "summary": out["by_role"].get(role, {"total": 0, "ready": [], "in_progress": [], "blocked": []}),
            "open_handoffs": [h for h in out["open_handoffs"] if h.get("to_role") == role or h.get("from_role") == role],
        }
    print(json.dumps(out, ensure_ascii=True, indent=2))


def print_role_context(board: dict, role: str, limit: int) -> None:
    if role not in ROLE_CATALOG:
        raise SystemExit(f"UNKNOWN_ROLE: {role}")
    recompute_states(board)
    role_tasks = list(iter_tasks_for_role(board, role))
    ready_tasks = sorted(
        [t for t in role_tasks if str(t.get("state", "")) == STATE_READY],
        key=lambda t: (priority_rank(str(t.get("priority", "P9"))), str(t.get("id", ""))),
    )
    active_tasks = [t for t in role_tasks if str(t.get("state", "")) in ACTIVE_STATES]
    blocked_tasks = [t for t in role_tasks if str(t.get("state", "")) == STATE_BLOCKED]

    open_handoffs = [h for h in board.get("handoffs", []) if str(h.get("status", "")) == "OPEN"]
    open_to = [h for h in open_handoffs if str(h.get("to_role", "")) == role]
    open_from = [h for h in open_handoffs if str(h.get("from_role", "")) == role]

    recent_peer_events: List[str] = []
    for event in reversed(board.get("events", [])):
        kind = str(event.get("kind", "")).strip()
        if not kind:
            continue
        details = event.get("details", {}) if isinstance(event.get("details", {}), dict) else {}
        actor = str(details.get("role") or details.get("from_role") or details.get("actor") or "").strip()
        if actor == role:
            continue
        ref = str(details.get("task_id") or details.get("handoff_id") or details.get("stream_id") or actor or "none").strip()
        recent_peer_events.append(f"{kind}:{ref}")
        if len(recent_peer_events) >= max(1, limit):
            break

    def csv(values: List[str]) -> str:
        cleaned = [v for v in values if v]
        return ",".join(cleaned[: max(1, limit)]) if cleaned else "none"

    next_task = str(ready_tasks[0].get("id", "none")) if ready_tasks else "none"
    ready_ids = [str(t.get("id", "")) for t in ready_tasks]
    active_ids = [str(t.get("id", "")) for t in active_tasks]
    blocked_ids = [str(t.get("id", "")) for t in blocked_tasks]
    to_ids = [str(h.get("id", "")) for h in open_to]
    from_ids = [str(h.get("id", "")) for h in open_from]

    print(
        "ROLE_CONTEXT "
        f"role={role} "
        f"total={len(role_tasks)} "
        f"ready={len(ready_tasks)} "
        f"in_progress={len(active_tasks)} "
        f"blocked={len(blocked_tasks)} "
        f"next_task={next_task} "
        f"ready_tasks={csv(ready_ids)} "
        f"in_progress_tasks={csv(active_ids)} "
        f"blocked_tasks={csv(blocked_ids)} "
        f"open_handoffs_to={len(open_to)} "
        f"open_handoffs_from={len(open_from)} "
        f"handoffs_to_ids={csv(to_ids)} "
        f"handoffs_from_ids={csv(from_ids)} "
        f"peer_events={csv(recent_peer_events)}"
    )


def replay_events(board: dict, limit: int, kind_filter: str, role_filter: str) -> None:
    events = board.get("events", [])
    if not isinstance(events, list):
        print("REPLAY_EMPTY reason=events_not_list")
        return
    selected: List[dict] = []
    for event in events:
        kind = str(event.get("kind", "")).strip()
        if kind_filter and kind_filter != kind:
            continue
        details = event.get("details", {}) if isinstance(event.get("details", {}), dict) else {}
        actor = str(details.get("role") or details.get("from_role") or details.get("actor") or "").strip()
        if role_filter and role_filter != actor:
            continue
        selected.append(event)
    if limit > 0:
        selected = selected[-limit:]
    for idx, event in enumerate(selected, start=1):
        at = str(event.get("at", "unknown"))
        kind = str(event.get("kind", "unknown"))
        details = event.get("details", {}) if isinstance(event.get("details", {}), dict) else {}
        ref = str(details.get("task_id") or details.get("handoff_id") or details.get("stream_id") or "none")
        actor = str(details.get("role") or details.get("from_role") or details.get("actor") or "none")
        print(f"REPLAY idx={idx} at={at} kind={kind} actor={actor} ref={ref} details={json.dumps(details, ensure_ascii=True, separators=(',',':'))}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parallel workstream plumbing for multi-role delivery")
    parser.add_argument("--board", default=str(DEFAULT_BOARD), help="Path to board JSON file")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create board if missing (or overwrite with --force)").add_argument(
        "--force", action="store_true", help="Overwrite existing board"
    )

    sync_p = sub.add_parser("sync-priority", help="Create/refresh stream tasks from priority queue")
    sync_p.add_argument("--queue", default=str(DEFAULT_PRIORITY_QUEUE), help="Priority queue JSON path")
    sync_p.add_argument("--include-pass", action="store_true", help="Also sync PASS streams")

    status_p = sub.add_parser("status", help="Print board status")
    status_p.add_argument("--role", default="", help="Filter by role")
    status_p.add_argument("--compact", action="store_true", help="Compact text output")
    status_p.add_argument("--limit", type=int, default=5, help="Per-list output limit")

    claim_p = sub.add_parser("claim", help="Claim one READY task for a role")
    claim_p.add_argument("--role", required=True)
    claim_p.add_argument("--task", default="", help="Optional explicit task id")

    done_p = sub.add_parser("complete", help="Mark task DONE")
    done_p.add_argument("--role", required=True)
    done_p.add_argument("--task", required=True)
    done_p.add_argument("--artifact", default="")
    done_p.add_argument("--note", default="")
    done_p.add_argument("--handoff-to", default="")
    done_p.add_argument("--exec-cmd", dest="exec_cmd", default="", help="Executed command evidence or SKIP(reason)")
    done_p.add_argument("--tests-run", default="", help="Test evidence or SKIP(reason)")
    done_p.add_argument("--review-ref", default="", help="Independent review reference")
    done_p.add_argument("--reviewer-role", default="", help="Independent reviewer role/agent")
    done_p.add_argument("--review-verdict", default="GO_WITH_CAUTION", help="Review verdict GO|BLOCKED|PASS")
    done_p.add_argument("--idempotency-key", default="", help="Stable idempotency key for completion/handoff")
    done_p.add_argument("--proof-root", default=str(DEFAULT_PROOF_ROOT), help="Proof manifest root directory")

    block_p = sub.add_parser("block", help="Mark task BLOCKED")
    block_p.add_argument("--task", required=True)
    block_p.add_argument("--reason", required=True)

    unblock_p = sub.add_parser("unblock", help="Clear task BLOCKED state")
    unblock_p.add_argument("--task", required=True)

    ack_p = sub.add_parser("handoff-ack", help="ACK an OPEN handoff")
    ack_p.add_argument("--handoff", required=True)
    ack_p.add_argument("--role", required=True)

    close_p = sub.add_parser("handoff-close", help="Close a handoff")
    close_p.add_argument("--handoff", required=True)
    close_p.add_argument("--role", default="")

    context_p = sub.add_parser("context", help="Compact role context for cron wake-up")
    context_p.add_argument("--role", required=True)
    context_p.add_argument("--limit", type=int, default=3, help="Max ids/events in context")

    replay_p = sub.add_parser("replay", help="Deterministic replay of board events for audit/postmortem")
    replay_p.add_argument("--limit", type=int, default=50, help="Max events to print (tail)")
    replay_p.add_argument("--kind", default="", help="Filter by event kind")
    replay_p.add_argument("--role", default="", help="Filter by role/actor")

    validate_p = sub.add_parser("validate", help="Validate board consistency + coordination invariants")
    validate_p.add_argument("--queue", default=str(DEFAULT_PRIORITY_QUEUE), help="Priority queue JSON path for drift checks")
    validate_p.add_argument("--ack-sla-seconds", type=int, default=900, help="SLA for OPEN handoff ACK")
    validate_p.add_argument("--close-sla-seconds", type=int, default=3600, help="SLA for OPEN handoff CLOSE")
    validate_p.add_argument("--proof-root", default=str(DEFAULT_PROOF_ROOT), help="Proof manifest root directory")
    validate_p.add_argument("--require-proof-manifest", action="store_true", help="Block when DONE tasks have no proof manifest")
    validate_p.add_argument("--strict-warn", action="store_true", help="Treat warnings as blocking")
    validate_p.add_argument("--in-progress-stale-seconds", type=int, default=14400, help="Warn on stale IN_PROGRESS tasks")

    sla_p = sub.add_parser("enforce-sla", help="Evaluate/apply handoff SLA ownership and escalation")
    sla_p.add_argument("--ack-sla-seconds", type=int, default=900)
    sla_p.add_argument("--close-sla-seconds", type=int, default=3600)
    sla_p.add_argument("--apply", action="store_true", help="Persist SLA escalation fields on handoffs/tasks")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    board_path = Path(args.board)

    if args.cmd == "init":
        with board_lock(board_path):
            if board_path.exists() and not args.force:
                print(f"INIT_SKIP board_exists={board_path}")
                return 0
            board = default_board()
            save_board(board_path, board)
            print(f"INIT_OK board={board_path}")
            return 0

    with board_lock(board_path):
        board = load_board(board_path)

        if args.cmd == "sync-priority":
            created_streams, created_tasks = sync_from_priority_queue(
                board,
                Path(args.queue),
                include_pass=bool(args.include_pass),
            )
            save_board(board_path, board)
            print(f"SYNC_OK streams_created={created_streams} tasks_created={created_tasks} board={board_path}")
            return 0

        if args.cmd == "status":
            recompute_states(board)
            print_status(board, role=str(args.role or ""), compact=bool(args.compact), limit=max(1, int(args.limit)))
            return 0

        if args.cmd == "context":
            role = str(args.role).strip()
            print_role_context(board, role=role, limit=max(1, int(args.limit)))
            return 0

        if args.cmd == "replay":
            replay_events(
                board,
                limit=max(1, int(args.limit)),
                kind_filter=str(args.kind or "").strip(),
                role_filter=str(args.role or "").strip(),
            )
            return 0

        if args.cmd == "claim":
            role = str(args.role).strip()
            if role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {role}")
            task = claim_task(board, role=role, task_id_override=str(args.task or "") or None)
            save_board(board_path, board)
            print(
                f"CLAIM_OK role={role} task={task.get('id')} stream={task.get('stream_id')} priority={task.get('priority')} state={task.get('state')}"
            )
            return 0

        if args.cmd == "complete":
            role = str(args.role).strip()
            if role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {role}")
            handoff_to = str(args.handoff_to or "").strip()
            if handoff_to and handoff_to not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_HANDOFF_ROLE: {handoff_to}")
            task = complete_task(
                board,
                role=role,
                task_id_value=str(args.task).strip(),
                artifact=str(args.artifact or "").strip(),
                note=str(args.note or "").strip(),
                handoff_to=handoff_to,
                proof_root=Path(str(args.proof_root)),
                cmd=str(args.exec_cmd or "").strip(),
                tests_run=str(args.tests_run or "").strip(),
                review_ref=str(args.review_ref or "").strip(),
                reviewer_role=str(args.reviewer_role or "").strip(),
                review_verdict=str(args.review_verdict or "").strip(),
                idempotency_key=str(args.idempotency_key or "").strip(),
            )
            save_board(board_path, board)
            print(
                f"COMPLETE_OK role={role} task={task.get('id')} stream={task.get('stream_id')} handoff_to={handoff_to or 'none'}"
            )
            return 0

        if args.cmd == "block":
            task = set_block_state(board, task_id_value=str(args.task).strip(), reason=str(args.reason).strip(), blocked=True)
            save_board(board_path, board)
            print(f"BLOCK_OK task={task.get('id')} reason={task.get('blocked_reason')}")
            return 0

        if args.cmd == "unblock":
            task = set_block_state(board, task_id_value=str(args.task).strip(), reason="", blocked=False)
            save_board(board_path, board)
            print(f"UNBLOCK_OK task={task.get('id')} state={task.get('state')}")
            return 0

        if args.cmd == "handoff-ack":
            handoff = handoff_update(board, handoff_id=str(args.handoff).strip(), status="ACK", actor_role=str(args.role).strip())
            save_board(board_path, board)
            print(f"HANDOFF_ACK_OK handoff={handoff.get('id')} task={handoff.get('task_id')} to={handoff.get('to_role')}")
            return 0

        if args.cmd == "handoff-close":
            handoff = handoff_update(board, handoff_id=str(args.handoff).strip(), status="CLOSED", actor_role=str(args.role or "").strip())
            save_board(board_path, board)
            print(f"HANDOFF_CLOSE_OK handoff={handoff.get('id')} task={handoff.get('task_id')}")
            return 0

        if args.cmd == "enforce-sla":
            summary = enforce_handoff_sla(
                board,
                ack_sla_seconds=max(1, int(args.ack_sla_seconds)),
                close_sla_seconds=max(1, int(args.close_sla_seconds)),
                apply=bool(args.apply),
            )
            if bool(args.apply):
                save_board(board_path, board)
            print(
                "HANDOFF_SLA_SUMMARY "
                f"open_total={summary['open_total']} "
                f"ack_total={summary['ack_total']} "
                f"ack_overdue={summary['ack_overdue']} "
                f"close_overdue={summary['close_overdue']} "
                f"escalated={summary['escalated']} "
                f"blocked_tasks={summary['blocked_tasks']} "
                f"apply={1 if bool(args.apply) else 0}"
            )
            if summary["close_overdue"] > 0:
                return 2
            return 0

        if args.cmd == "validate":
            recompute_states(board)
            errors, warnings = validate_board(
                board,
                queue_path=Path(str(args.queue)),
                ack_sla_seconds=max(1, int(args.ack_sla_seconds)),
                close_sla_seconds=max(1, int(args.close_sla_seconds)),
                proof_root=Path(str(args.proof_root)),
                require_proof_manifest=bool(args.require_proof_manifest),
                in_progress_stale_seconds=max(1, int(args.in_progress_stale_seconds)),
            )
            if errors or (warnings and bool(args.strict_warn)):
                print("VALIDATE_BLOCKED")
                for err in errors:
                    print(f"- {err}")
                for warn in warnings:
                    print(f"! {warn}")
                return 2
            if warnings:
                print("VALIDATE_PASS_WITH_WARN")
                for warn in warnings:
                    print(f"! {warn}")
            else:
                print("VALIDATE_PASS")
            print(
                f"EVIDENCE tasks={len(board.get('tasks', []))} streams={len(board.get('streams', []))} "
                f"handoffs_open={sum(1 for h in board.get('handoffs', []) if h.get('status') == 'OPEN')} "
                f"warnings={len(warnings)} errors={len(errors)}"
            )
            return 0

    parser.error(f"Unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
