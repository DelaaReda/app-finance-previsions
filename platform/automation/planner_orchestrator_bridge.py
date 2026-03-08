#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from parallel_workstream import (
    DEFAULT_PROOF_ROOT,
    STATE_DONE,
    STATE_IN_PROGRESS,
    STATE_BLOCKED,
    STATE_READY,
    STATE_READY_DEV,
    append_event,
    board_lock,
    claim_task,
    complete_task,
    load_board,
    now_iso,
    priority_rank,
    reconcile_state,
    recompute_states,
    save_board,
    set_block_state,
    task_index,
)
from planner_subagent_manager import (
    ACTIVE_STATUSES,
    _load_config as load_subagent_config,
    collect_subagent,
    run_subagent,
)
from worker_manager import _load_config as load_worker_config
from worker_manager import collect_worker


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
SUCCESS_SUBAGENT_STATUSES = {"completed", "done", "pass", "ok", "success", "merged"}
DEV_CAPABILITY_TIMEOUT_SECONDS = max(300, int(os.environ.get("FC_PLANNER_DEV_CAPABILITY_TIMEOUT_SECONDS", "900")))
ADMIN_CAPABILITY_TIMEOUT_SECONDS = max(180, int(os.environ.get("FC_PLANNER_ADMIN_CAPABILITY_TIMEOUT_SECONDS", "600")))
STALE_SUBAGENT_GRACE_SECONDS = max(15, int(os.environ.get("FC_PLANNER_SUBAGENT_STALE_GRACE_SECONDS", "30")))
QA_REVIEW_TIMEOUT_SECONDS = max(180, int(os.environ.get("FC_PLANNER_QA_WORKER_TIMEOUT_SECONDS", "900")))


def _parse_iso_utc(raw: str) -> datetime | None:
    token = str(raw or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        try:
            return datetime.strptime(token, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except Exception:
            return None
    try:
        parsed = datetime.fromisoformat(token)
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_contract(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().upper()
        if key in CONTRACT_KEYS and key not in values:
            values[key] = value.strip()
    for key in CONTRACT_KEYS:
        values.setdefault(key, "")
    return values


def _render_contract(values: dict[str, str]) -> str:
    return "\n".join(f"{key}: {values.get(key, '').strip()}" for key in CONTRACT_KEYS) + "\n"


def _parse_pairs(raw: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    previous_key = ""
    for frag in str(raw or "").split(";"):
        item = frag.strip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key:
            continue
        if key in {"after", "test"} and previous_key == "verify" and pairs.get("verify"):
            pairs["verify"] = f"{pairs['verify']}; {key}={value}"
            continue
        if key in {"imports_ok", "path_target"} and previous_key == "architecture_check" and pairs.get("architecture_check"):
            pairs["architecture_check"] = f"{pairs['architecture_check']}; {key}={value}"
            continue
        if key in {"target", "impact"} and previous_key == "vision_alignment" and pairs.get("vision_alignment"):
            pairs["vision_alignment"] = f"{pairs['vision_alignment']}; {key}={value}"
            continue
        if key not in pairs:
            pairs[key] = value
        previous_key = key
    return pairs


def _serialize_pairs(pairs: dict[str, str]) -> str:
    preferred = [
        "task_update",
        "lock_check",
        "run_note",
        "issues",
        "issue_count",
        "issue_severity",
        "stream_id",
        "task_id",
        "root_cause",
        "fix_applied",
        "artifact",
        "planner_artifact",
        "verify",
        "tests_run",
        "cmd",
        "files_touched",
        "commit_sha",
        "architecture_check",
        "vision_alignment",
        "bridge_actions",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for key in preferred:
        if key in pairs and str(pairs[key]).strip():
            out.append(f"{key}={pairs[key]}")
            seen.add(key)
    for key in sorted(pairs.keys()):
        if key in seen:
            continue
        value = str(pairs[key]).strip()
        if value:
            out.append(f"{key}={value}")
    return "; ".join(out)


def _append_bridge_actions(contract: dict[str, str], actions: list[str]) -> dict[str, str]:
    if not actions:
        return contract
    pairs = _parse_pairs(contract.get("EVIDENCE", ""))
    existing = [item for item in str(pairs.get("bridge_actions", "")).split(",") if item]
    merged = existing + [item for item in actions if item]
    pairs["planner_orchestrator_bridge"] = "1"
    pairs["bridge_actions"] = ",".join(dict.fromkeys(merged))
    contract["EVIDENCE"] = _serialize_pairs(pairs)
    return contract


def _task_stream_id(task_id_value: str) -> str:
    parts = str(task_id_value or "").strip().split("-")
    if len(parts) >= 2:
        return "-".join(parts[:2])
    return str(task_id_value or "").strip()


def _evidence_artifact(evidence: dict[str, str]) -> str:
    for key in ("planner_artifact", "artifact", "proof_manifest", "raw_output_ref"):
        value = str(evidence.get(key, "")).strip()
        if value and value.lower() not in {"none", "n/a", "na"}:
            return value
    return ""


def _apply_task_metadata(task: dict[str, Any], evidence: dict[str, str], extra: dict[str, str] | None = None) -> None:
    fields = {
        "root_cause": evidence.get("root_cause", ""),
        "fix_applied": evidence.get("fix_applied", ""),
        "verify": evidence.get("verify", ""),
        "artifact": _evidence_artifact(evidence),
        "tests_run": evidence.get("tests_run", ""),
        "commit_sha": evidence.get("commit_sha", ""),
        "files_touched": evidence.get("files_touched", ""),
        "architecture_check": evidence.get("architecture_check", ""),
        "vision_alignment": evidence.get("vision_alignment", ""),
    }
    if extra:
        fields.update(extra)
    for key, value in fields.items():
        token = str(value or "").strip()
        if token:
            task[key] = token
    task["last_progress_at"] = now_iso()
    task["updated_at"] = now_iso()


def _auto_change_plan(task: dict[str, Any]) -> str:
    title = str(task.get("title", "")).strip() or str(task.get("id", "")).strip()
    return "\n".join(
        [
            f"scope {title} minimal patch",
            "dependency impact on downstream tasks",
            "risk containment before code changes",
            "verification via targeted tests",
            "rollback path if regression appears",
        ]
    )


def _auto_architecture_checks(task: dict[str, Any]) -> str:
    title = str(task.get("title", "")).strip() or str(task.get("id", "")).strip()
    return "\n".join(
        [
            f"service boundaries for {title}",
            "imports and data flow remain stable",
            "patch stays inside intended module path",
        ]
    )


def _task_notes(task: dict[str, Any], limit: int = 4) -> list[str]:
    notes = task.get("notes", [])
    if not isinstance(notes, list):
        return []
    out: list[str] = []
    for item in notes:
        text = " ".join(str(item or "").split())
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _build_dev_dispatch_message(task: dict[str, Any]) -> str:
    task_id_value = str(task.get("id", "")).strip()
    title = str(task.get("title", "")).strip() or task_id_value
    priority = str(task.get("priority", "P9")).strip() or "P9"
    stream_id = str(task.get("stream_id", "")).strip() or _task_stream_id(task_id_value)
    depends_on = [str(dep).strip() for dep in task.get("depends_on", []) if str(dep).strip()]
    notes = _task_notes(task)
    lines = [
        f"Take ownership of {task_id_value}.",
        f"Task title: {title}",
        f"Stream: {stream_id}",
        f"Priority: {priority}",
        f"Dependencies already satisfied: {', '.join(depends_on) if depends_on else 'none'}",
        "Execution policy:",
        "- Implement one minimal, verifiable slice only.",
        "- Stay inside files implied by the task notes; do not widen into a repo audit.",
        "- Do not inspect monitor/doctor unless you hit a runtime blocker.",
        "- Run targeted tests only.",
        "- If you change code or config, commit it and return the real commit_sha.",
        "- Return delivery evidence precise enough for planner merge: artifact, verify, files_touched, tests_run, commit_sha, architecture_check, vision_alignment.",
    ]
    if notes:
        lines.append("Task notes:")
        for note in notes:
            lines.append(f"- {note}")
    return "\n".join(lines)


def _build_admin_dispatch_message(task: dict[str, Any]) -> str:
    task_id_value = str(task.get("id", "")).strip()
    title = str(task.get("title", "")).strip() or task_id_value
    priority = str(task.get("priority", "P9")).strip() or "P9"
    stream_id = str(task.get("stream_id", "")).strip() or _task_stream_id(task_id_value)
    depends_on = [str(dep).strip() for dep in task.get("depends_on", []) if str(dep).strip()]
    notes = _task_notes(task)
    lines = [
        f"Take ownership of {task_id_value}.",
        f"Task title: {title}",
        f"Stream: {stream_id}",
        f"Priority: {priority}",
        f"Dependencies already satisfied: {', '.join(depends_on) if depends_on else 'none'}",
        "Execution policy:",
        "- Validate runtime truth and observability only for this task scope.",
        "- Prefer reversible fixes or precise evidence capture; do not broaden into planning.",
        "- If no code/config change is needed, still return artifact + verify and use SKIP(...) fields explicitly.",
        "- If you change code or config, commit it and return the real commit_sha.",
        "- Return planner-mergeable evidence: artifact, verify, files_touched, tests_run, commit_sha, architecture_check, vision_alignment.",
    ]
    if notes:
        lines.append("Task notes:")
        for note in notes:
            lines.append(f"- {note}")
    return "\n".join(lines)


def _build_qa_review_message(task: dict[str, Any]) -> str:
    task_id_value = str(task.get("id", "")).strip()
    title = str(task.get("title", "")).strip() or task_id_value
    stream_id = str(task.get("stream_id", "")).strip() or _task_stream_id(task_id_value)
    notes = _task_notes(task)
    lines = [
        f"Run QA review for {task_id_value}.",
        f"Task title: {title}",
        f"Stream: {stream_id}",
        "Execution policy:",
        "- Validate the delivered slice with targeted checks only.",
        "- If you discover a local, bounded defect, fix it directly and verify it.",
        "- Preserve the existing frontend theme; do not refactor UI styling broadly.",
        "- Return concise proof: summary, artifact, verify, raw_output_ref.",
    ]
    if notes:
        lines.append("Task notes:")
        for note in notes:
            lines.append(f"- {note}")
    return "\n".join(lines)


def _load_worker_rows(root: Path) -> tuple[Any, list[dict[str, Any]]]:
    config = load_worker_config(root)
    payload: dict[str, Any] = {}
    if config.registry_path.exists():
        try:
            payload = json.loads(config.registry_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            payload = {}
    rows = payload.get("workers", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    return config, [row for row in rows if isinstance(row, dict)]


def _qa_worker_active(root: Path, task_id_value: str) -> bool:
    _, rows = _load_worker_rows(root)
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if str(row.get("worker_type", "")).strip() != "qa_review_worker":
            continue
        if str(row.get("owner_task_id", "")).strip() != task_id_value:
            continue
        if str(row.get("status", "")).strip().lower() in ACTIVE_STATUSES:
            return True
    return False


def _qa_review_already_done(task: dict[str, Any]) -> bool:
    token = str(task.get("qa_status", "")).strip().lower()
    return token in SUCCESS_SUBAGENT_STATUSES or token == "merged"


def _launch_qa_review_worker(root: Path, task: dict[str, Any], source: str) -> dict[str, Any]:
    task_id_value = str(task.get("id", "")).strip()
    if not task_id_value:
        return {"dispatched": False, "reason": "invalid_task"}
    if _qa_review_already_done(task):
        return {"dispatched": False, "reason": "qa_already_done", "task_id": task_id_value}
    if _qa_worker_active(root, task_id_value):
        return {"dispatched": False, "reason": "qa_already_active", "task_id": task_id_value}
    launcher_log = root / "docs" / "operations" / "orchestrator" / "dynamic-workers-results" / f"{task_id_value}.qa.launcher.log"
    cmd = [
        sys.executable,
        str(root / "platform" / "automation" / "worker_manager.py"),
        "--root",
        str(root),
        "run",
        "--role",
        "planner",
        "--worker-type",
        "qa_review_worker",
        "--owner-task-id",
        task_id_value,
        "--task-kind",
        "qa_review",
        "--message",
        _build_qa_review_message(task),
        "--ttl-min",
        "30",
        "--backend",
        "openclaw",
        "--timeout-seconds",
        str(QA_REVIEW_TIMEOUT_SECONDS),
        "--thinking",
        "high",
        "--result-kind",
        "qa_fix_result",
    ]
    try:
        launcher_log.parent.mkdir(parents=True, exist_ok=True)
        with launcher_log.open("w", encoding="utf-8") as handle:
            subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except Exception as exc:
        return {"dispatched": False, "reason": f"qa_spawn_failed:{exc}", "task_id": task_id_value}
    return {
        "dispatched": True,
        "task_id": task_id_value,
        "reason": "qa_running",
        "launcher_log": str(launcher_log.relative_to(root)),
    }


def _payload_status(payload: dict[str, Any]) -> str:
    return str(payload.get("status", "")).strip().lower()


def _payload_has_delivery_evidence(payload: dict[str, Any], target_role: str = "dev") -> bool:
    required = ("artifact", "verify")
    for key in required:
        value = str(payload.get(key, "")).strip().lower()
        if not value or value in {"none", "n/a", "na"}:
            return False
    if str(target_role or "").strip().lower() == "dev":
        tests_run = str(payload.get("tests_run", "")).strip().lower()
        if not tests_run or tests_run in {"none", "n/a", "na"}:
            return False
        commit = str(payload.get("commit_sha", "")).strip().lower()
        if not commit or commit in {"none", "n/a", "na"}:
            return False
    return True


def _select_dispatchable_dev_task(board: dict[str, Any]) -> dict[str, Any] | None:
    index = task_index(board)
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    retry_candidates: list[tuple[int, int, dict[str, Any]]] = []
    in_progress_candidates: list[tuple[int, int, dict[str, Any]]] = []
    for idx, task in enumerate(board.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        state = str(task.get("state", "")).strip().upper()
        if str(task.get("role", "")).strip().lower() != "dev":
            continue
        deps = [dep for dep in task.get("depends_on", []) if dep]
        if any(str(index.get(dep, {}).get("state", "")).upper() != STATE_DONE for dep in deps):
            continue
        row = (priority_rank(str(task.get("priority", "P9"))), idx, task)
        if state in {STATE_READY, STATE_READY_DEV}:
            candidates.append(row)
            continue
        if state == STATE_IN_PROGRESS:
            in_progress_candidates.append(row)
            continue
        blocked_reason = str(task.get("blocked_reason", "")).strip().lower()
        if state == STATE_BLOCKED and blocked_reason.startswith("planner_dev_capability_failed:"):
            retry_candidates.append(row)
    if retry_candidates:
        retry_candidates.sort(key=lambda row: (row[0], row[1]))
        return retry_candidates[0][2]
    if not candidates:
        if not in_progress_candidates:
            return None
        in_progress_candidates.sort(key=lambda row: (row[0], row[1]))
        return in_progress_candidates[0][2]
    candidates.sort(key=lambda row: (row[0], row[1]))
    return candidates[0][2]


def _select_dispatchable_admin_task(board: dict[str, Any]) -> dict[str, Any] | None:
    index = task_index(board)
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    retry_candidates: list[tuple[int, int, dict[str, Any]]] = []
    in_progress_candidates: list[tuple[int, int, dict[str, Any]]] = []
    for idx, task in enumerate(board.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        state = str(task.get("state", "")).strip().upper()
        if str(task.get("role", "")).strip().lower() != "admin":
            continue
        deps = [dep for dep in task.get("depends_on", []) if dep]
        if any(str(index.get(dep, {}).get("state", "")).upper() != STATE_DONE for dep in deps):
            continue
        row = (priority_rank(str(task.get("priority", "P9"))), idx, task)
        if state in {STATE_READY, "READY_PLANNER"}:
            candidates.append(row)
            continue
        if state == STATE_IN_PROGRESS:
            in_progress_candidates.append(row)
            continue
        blocked_reason = str(task.get("blocked_reason", "")).strip().lower()
        if state == STATE_BLOCKED and blocked_reason.startswith("planner_admin_capability_failed:"):
            retry_candidates.append(row)
    if retry_candidates:
        retry_candidates.sort(key=lambda row: (row[0], row[1]))
        return retry_candidates[0][2]
    if not candidates:
        if not in_progress_candidates:
            return None
        in_progress_candidates.sort(key=lambda row: (row[0], row[1]))
        return in_progress_candidates[0][2]
    candidates.sort(key=lambda row: (row[0], row[1]))
    return candidates[0][2]


def _complete_task_from_evidence(
    *,
    root: Path,
    board_path: Path,
    role: str,
    task_id_value: str,
    evidence: dict[str, str],
    source: str,
    board: dict[str, Any] | None = None,
) -> bool:
    artifact = _evidence_artifact(evidence)
    if not artifact:
        return False
    if board is None:
        board = load_board(board_path)
    queue_path = board_path.parent / "priority-queue.json"
    tasks = task_index(board)
    task = tasks.get(task_id_value)
    if not isinstance(task, dict):
        return False
    if str(task.get("state", "")).strip().upper() == STATE_DONE:
        _apply_task_metadata(task, evidence)
        append_event(board, "planner_orchestrator_complete_skip", {"role": role, "task_id": task_id_value, "source": source, "reason": "already_done"})
        recompute_states(board)
        reconcile_state(board, queue_path)
        save_board(board_path, board)
        return True
    note = " | ".join(
        [
            f"source={source}",
            f"root_cause={evidence.get('root_cause', 'none')}",
            f"fix_applied={evidence.get('fix_applied', 'none')}",
            f"verify={evidence.get('verify', 'none')}",
            f"architecture_check={evidence.get('architecture_check', 'none')}",
            f"vision_alignment={evidence.get('vision_alignment', 'none')}",
        ]
    )
    _apply_task_metadata(task, evidence)
    proof_root = DEFAULT_PROOF_ROOT
    if not proof_root.is_absolute():
        proof_root = (root / proof_root).resolve()
    complete_task(
        board,
        role=role,
        task_id_value=task_id_value,
        artifact=artifact,
        note=note,
        handoff_to="",
        proof_root=proof_root,
        cmd=str(evidence.get("cmd", "")).strip() or ("SKIP(planner_doc_only)" if role == "planner" else "SKIP(subagent_no_cmd)"),
        tests_run=str(evidence.get("tests_run", "")).strip() or ("SKIP(planner_doc_only)" if role == "planner" else "SKIP(subagent_no_tests)"),
        review_ref=f"{source}:{task_id_value}",
        reviewer_role="planner",
        review_verdict="PASS",
        change_plan="" if role == "planner" else _auto_change_plan(task),
        architecture_checks="" if role == "planner" else _auto_architecture_checks(task),
        idempotency_key=str(evidence.get("next_action_unique", "")).strip(),
    )
    append_event(board, "planner_orchestrator_complete", {"role": role, "task_id": task_id_value, "source": source, "artifact": artifact})
    recompute_states(board)
    reconcile_state(board, queue_path)
    save_board(board_path, board)
    return True


def _claim_task(
    *,
    board_path: Path,
    role: str,
    task_id_value: str,
    source: str,
    board: dict[str, Any] | None = None,
) -> bool:
    if board is None:
        board = load_board(board_path)
    queue_path = board_path.parent / "priority-queue.json"
    tasks = task_index(board)
    task = tasks.get(task_id_value)
    if not isinstance(task, dict):
        return False
    state = str(task.get("state", "")).strip().upper()
    if state == STATE_IN_PROGRESS:
        return True
    task["blocked_reason"] = ""
    task["stalled_reason"] = ""
    task["ready_starvation"] = False
    task["ready_starved_at"] = ""
    claim_task(
        board,
        role=role,
        task_id_override=task_id_value,
        change_plan=_auto_change_plan(task) if role != "planner" else "",
        architecture_checks=_auto_architecture_checks(task) if role != "planner" else "",
    )
    append_event(board, "planner_orchestrator_claim", {"role": role, "task_id": task_id_value, "source": source})
    recompute_states(board)
    reconcile_state(board, queue_path)
    save_board(board_path, board)
    return True


def _dispatch_dev_capability(root: Path, source: str, backend: str) -> dict[str, Any]:
    config = load_subagent_config(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    with board_lock(board_path):
        board = load_board(board_path)
        candidate = _select_dispatchable_dev_task(board)
        if candidate is None:
            return {"dispatched": False, "reason": "no_ready_dev"}
        task_id_value = str(candidate.get("id", "")).strip()
        if str(candidate.get("state", "")).strip().upper() == STATE_BLOCKED:
            candidate["state"] = STATE_READY_DEV
            candidate["blocked_reason"] = ""
            candidate["updated_at"] = now_iso()
            append_event(
                    board,
                    "planner_orchestrator_retry_ready",
                    {"task_id": task_id_value, "source": source, "reason": "recoverable_capability_failure"},
                )
        elif str(candidate.get("state", "")).strip().upper() == STATE_IN_PROGRESS:
            candidate["blocked_reason"] = ""
            candidate["stalled_reason"] = ""
            candidate["updated_at"] = now_iso()
            append_event(
                board,
                "planner_orchestrator_resume_in_progress",
                {"task_id": task_id_value, "source": source, "reason": "no_active_dev_capability"},
            )
        _claim_task(board_path=board_path, role="dev", task_id_value=task_id_value, source=source, board=board)

    message = _build_dev_dispatch_message(candidate)
    chosen_backend = str(backend or "auto").strip().lower() or "auto"
    if chosen_backend in {"openclaw", "codex_exec", "auto"}:
        subagent_id = f"planner_dev_{os.urandom(5).hex()}"
        launcher_log = config.results_dir / f"{subagent_id}.launcher.log"
        cmd = [
            sys.executable,
            str(root / "platform" / "automation" / "planner_subagent_manager.py"),
            "--root",
            str(root),
            "run",
            "--role",
            "planner",
            "--target-role",
            "dev",
            "--owner-task-id",
            task_id_value,
            "--task-kind",
            "delivery",
            "--message",
            message,
            "--ttl-min",
            str(config.default_ttl_min),
            "--backend",
            chosen_backend,
            "--timeout-seconds",
            str(DEV_CAPABILITY_TIMEOUT_SECONDS),
            "--subagent-id",
            subagent_id,
        ]
        try:
            launcher_log.parent.mkdir(parents=True, exist_ok=True)
            with launcher_log.open("w", encoding="utf-8") as handle:
                subprocess.Popen(
                    cmd,
                    cwd=str(root),
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except Exception as exc:
            with board_lock(board_path):
                board = load_board(board_path)
                set_block_state(board, task_id_value=task_id_value, reason=f"planner_dev_capability_failed:dispatch_spawn_failed:{exc}", blocked=True)
                append_event(board, "planner_orchestrator_dev_dispatch_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id})
                reconcile_state(board, board_path.parent / "priority-queue.json")
                save_board(board_path, board)
            return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "dispatch_spawn_failed", "subagent_id": subagent_id, "backend": chosen_backend}
        return {
            "dispatched": True,
            "completed": False,
            "task_id": task_id_value,
            "reason": "subagent_running",
            "subagent_id": subagent_id,
            "backend": chosen_backend,
            "launcher_log": str(launcher_log.relative_to(root)),
        }
    rc, payload = run_subagent(
        config,
        role="planner",
        target_role="dev",
        owner_task_id=task_id_value,
        task_kind="delivery",
        message=message,
        ttl_min=config.default_ttl_min,
        backend=chosen_backend,
        timeout_seconds=DEV_CAPABILITY_TIMEOUT_SECONDS,
    )
    subagent_id = str(payload.get("subagent_id", "")).strip()
    if rc != 0 or not payload.get("ok"):
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason=f"planner_dev_capability_failed:{payload.get('blocking_issue') or payload.get('stderr') or 'unknown'}", blocked=True)
            append_event(board, "planner_orchestrator_dev_dispatch_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"})
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        if subagent_id:
            collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "subagent_failed", "subagent_id": subagent_id, "backend": chosen_backend}

    status_token = _payload_status(payload)
    if status_token not in SUCCESS_SUBAGENT_STATUSES:
        blocking_issue = str(payload.get("blocking_issue") or payload.get("recommended_next") or status_token or "subagent_not_ready")
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason=f"planner_dev_capability_failed:{blocking_issue}", blocked=True)
            append_event(
                board,
                "planner_orchestrator_dev_dispatch_blocked",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none", "status": status_token or "unknown"},
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        if subagent_id:
            collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "subagent_blocked", "subagent_id": subagent_id or "none", "backend": chosen_backend}

    evidence = {
        "root_cause": str(payload.get("root_cause", "none")),
        "fix_applied": str(payload.get("fix_applied", "none")),
        "artifact": str(payload.get("artifact", "none")),
        "verify": str(payload.get("verify", "none")),
        "files_touched": str(payload.get("files_touched", "none")),
        "tests_run": str(payload.get("tests_run", "SKIP(no_tests)")),
        "commit_sha": str(payload.get("commit_sha", "none")),
        "architecture_check": str(payload.get("architecture_check", "none")),
        "vision_alignment": str(payload.get("vision_alignment", "none")),
        "cmd": "SKIP(subagent_exec_internal)",
        "next_action_unique": f"PLANNER_MERGE_{task_id_value}",
    }
    if not _payload_has_delivery_evidence(payload, target_role="dev"):
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason="planner_dev_capability_failed:delivery_evidence_incomplete", blocked=True)
            append_event(
                board,
                "planner_orchestrator_dev_dispatch_incomplete",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"},
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        if subagent_id:
            collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "delivery_evidence_incomplete", "subagent_id": subagent_id or "none", "backend": chosen_backend}

    with board_lock(board_path):
        board = load_board(board_path)
        completed = _complete_task_from_evidence(
            root=root,
            board_path=board_path,
            role="dev",
            task_id_value=task_id_value,
            evidence=evidence,
            source=source,
            board=board,
        )
        if not completed:
            set_block_state(board, task_id_value=task_id_value, reason="planner_dev_capability_failed:complete_merge_failed", blocked=True)
            append_event(
                board,
                "planner_orchestrator_dev_complete_failed",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"},
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
    if subagent_id:
        collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
    if completed:
        with board_lock(board_path):
            board = load_board(board_path)
            task = task_index(board).get(task_id_value, {})
            qa_dispatch = _launch_qa_review_worker(root, task if isinstance(task, dict) else {"id": task_id_value}, source)
            if qa_dispatch.get("dispatched"):
                append_event(board, "planner_orchestrator_qa_review_dispatched", {"task_id": task_id_value, "source": source})
                reconcile_state(board, board_path.parent / "priority-queue.json")
                save_board(board_path, board)
    return {"dispatched": True, "completed": completed, "task_id": task_id_value, "subagent_id": subagent_id or "none", "backend": chosen_backend}


def _dispatch_admin_capability(root: Path, source: str, backend: str) -> dict[str, Any]:
    config = load_subagent_config(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    with board_lock(board_path):
        board = load_board(board_path)
        candidate = _select_dispatchable_admin_task(board)
        if candidate is None:
            return {"dispatched": False, "reason": "no_ready_admin"}
        task_id_value = str(candidate.get("id", "")).strip()
        if not task_id_value:
            return {"dispatched": False, "reason": "invalid_admin_task"}
        candidate_state = str(candidate.get("state", "")).strip().upper()
        if candidate_state == STATE_BLOCKED:
            candidate["state"] = STATE_READY
            candidate["blocked_reason"] = ""
            candidate["updated_at"] = now_iso()
            append_event(
                board,
                "planner_orchestrator_admin_retry_ready",
                {"task_id": task_id_value, "source": source, "reason": "recoverable_capability_failure"},
            )
        elif candidate_state == STATE_IN_PROGRESS:
            candidate["blocked_reason"] = ""
            candidate["stalled_reason"] = ""
            candidate["updated_at"] = now_iso()
            append_event(
                board,
                "planner_orchestrator_admin_resume_in_progress",
                {"task_id": task_id_value, "source": source, "reason": "no_active_admin_capability"},
            )
        _claim_task(board_path=board_path, role="admin", task_id_value=task_id_value, source=source, board=board)
    chosen_backend = str(backend or "auto").strip() or "auto"
    message = _build_admin_dispatch_message(candidate)
    if chosen_backend in {"openclaw", "codex_exec", "auto"}:
        subagent_id = f"planner_admin_{os.urandom(5).hex()}"
        launcher_log = config.results_dir / f"{subagent_id}.launcher.log"
        cmd = [
            sys.executable,
            str(root / "platform" / "automation" / "planner_subagent_manager.py"),
            "--root",
            str(root),
            "run",
            "--role",
            "planner",
            "--target-role",
            "admin",
            "--owner-task-id",
            task_id_value,
            "--task-kind",
            "runtime",
            "--message",
            message,
            "--ttl-min",
            str(config.default_ttl_min),
            "--backend",
            chosen_backend,
            "--timeout-seconds",
            str(ADMIN_CAPABILITY_TIMEOUT_SECONDS),
            "--subagent-id",
            subagent_id,
        ]
        try:
            launcher_log.parent.mkdir(parents=True, exist_ok=True)
            with launcher_log.open("w", encoding="utf-8") as handle:
                subprocess.Popen(
                    cmd,
                    cwd=str(root),
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
        except Exception as exc:
            with board_lock(board_path):
                board = load_board(board_path)
                set_block_state(board, task_id_value=task_id_value, reason=f"planner_admin_capability_failed:dispatch_spawn_failed:{exc}", blocked=True)
                append_event(board, "planner_orchestrator_admin_dispatch_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id})
                reconcile_state(board, board_path.parent / "priority-queue.json")
                save_board(board_path, board)
            return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "dispatch_spawn_failed", "subagent_id": subagent_id, "backend": chosen_backend}
        return {
            "dispatched": True,
            "completed": False,
            "task_id": task_id_value,
            "reason": "subagent_running",
            "subagent_id": subagent_id,
            "backend": chosen_backend,
            "launcher_log": str(launcher_log.relative_to(root)),
        }
    rc, payload = run_subagent(
        config,
        role="planner",
        target_role="admin",
        owner_task_id=task_id_value,
        task_kind="runtime",
        message=message,
        ttl_min=config.default_ttl_min,
        backend=chosen_backend,
        timeout_seconds=ADMIN_CAPABILITY_TIMEOUT_SECONDS,
    )
    subagent_id = str(payload.get("subagent_id", "")).strip()
    if rc != 0 or not payload.get("ok"):
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason=f"planner_admin_capability_failed:{payload.get('blocking_issue') or payload.get('stderr') or 'unknown'}", blocked=True)
            append_event(board, "planner_orchestrator_admin_dispatch_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"})
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        if subagent_id:
            collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "subagent_failed", "subagent_id": subagent_id, "backend": chosen_backend}

    status_token = _payload_status(payload)
    if status_token not in SUCCESS_SUBAGENT_STATUSES:
        blocking_issue = str(payload.get("blocking_issue") or payload.get("recommended_next") or status_token or "subagent_not_ready")
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason=f"planner_admin_capability_failed:{blocking_issue}", blocked=True)
            append_event(
                board,
                "planner_orchestrator_admin_dispatch_blocked",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none", "status": status_token or "unknown"},
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        if subagent_id:
            collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "subagent_blocked", "subagent_id": subagent_id or "none", "backend": chosen_backend}

    evidence = {
        "root_cause": str(payload.get("root_cause", "none")),
        "fix_applied": str(payload.get("fix_applied", "none")),
        "artifact": str(payload.get("artifact", "none")),
        "verify": str(payload.get("verify", "none")),
        "files_touched": str(payload.get("files_touched", "none")),
        "tests_run": str(payload.get("tests_run", "SKIP(no_tests)")),
        "commit_sha": str(payload.get("commit_sha", "none")),
        "architecture_check": str(payload.get("architecture_check", "none")),
        "vision_alignment": str(payload.get("vision_alignment", "none")),
        "cmd": "SKIP(subagent_exec_internal)",
        "next_action_unique": f"PLANNER_MERGE_{task_id_value}",
    }
    if not _payload_has_delivery_evidence(payload, target_role="admin"):
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason="planner_admin_capability_failed:delivery_evidence_incomplete", blocked=True)
            append_event(
                board,
                "planner_orchestrator_admin_dispatch_incomplete",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"},
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        if subagent_id:
            collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "delivery_evidence_incomplete", "subagent_id": subagent_id or "none", "backend": chosen_backend}

    with board_lock(board_path):
        board = load_board(board_path)
        completed = _complete_task_from_evidence(
            root=root,
            board_path=board_path,
            role="admin",
            task_id_value=task_id_value,
            evidence=evidence,
            source=source,
            board=board,
        )
        if not completed:
            set_block_state(board, task_id_value=task_id_value, reason="planner_admin_capability_failed:complete_merge_failed", blocked=True)
            append_event(
                board,
                "planner_orchestrator_admin_complete_failed",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"},
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
    if subagent_id:
        collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
    return {"dispatched": True, "completed": completed, "task_id": task_id_value, "subagent_id": subagent_id or "none", "backend": chosen_backend}


def _planner_registry_rows(root: Path) -> tuple[Any, list[dict[str, Any]]]:
    config = load_subagent_config(root)
    payload = {}
    try:
        payload = json.loads(config.registry_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        payload = {}
    rows = payload.get("subagents", [])
    if not isinstance(rows, list):
        rows = []
    return config, [row for row in rows if isinstance(row, dict)]


def _write_planner_registry_rows(config: Any, rows: list[dict[str, Any]]) -> None:
    payload = {"updated_at": now_iso(), "subagents": rows}
    config.registry_path.parent.mkdir(parents=True, exist_ok=True)
    config.registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _mark_stale_dev_subagents(root: Path, source: str) -> list[str]:
    config, rows = _planner_registry_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    threshold_seconds = DEV_CAPABILITY_TIMEOUT_SECONDS + STALE_SUBAGENT_GRACE_SECONDS
    now_text = now_iso()
    changed = False
    actions: list[str] = []
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if str(row.get("target_role", "")).strip().lower() != "dev":
            continue
        if str(row.get("status", "")).strip().lower() not in ACTIVE_STATUSES:
            continue
        subagent_id = str(row.get("subagent_id", "")).strip()
        if not subagent_id:
            continue
        result_path = config.results_dir / f"{subagent_id}.result.json"
        if result_path.exists():
            continue
        created_raw = str(row.get("created_at", "")).strip() or str(row.get("last_update_at", "")).strip()
        created_at = _parse_iso_utc(created_raw)
        if created_at is None:
            continue
        age_seconds = max(0, int((datetime.now(timezone.utc) - created_at).total_seconds()))
        if age_seconds < threshold_seconds:
            continue
        task_id_value = str(row.get("owner_task_id", "")).strip()
        if task_id_value:
            with board_lock(board_path):
                board = load_board(board_path)
                task = task_index(board).get(task_id_value)
                if isinstance(task, dict):
                    task["state"] = STATE_READY_DEV
                    task["blocked_reason"] = ""
                    task["stalled_reason"] = "planner_capability_stale_no_result"
                    task["updated_at"] = now_text
                    task["last_progress_at"] = now_text
                    append_event(
                        board,
                        "planner_orchestrator_dev_dispatch_stale",
                        {"task_id": task_id_value, "source": source, "subagent_id": subagent_id, "age_s": age_seconds},
                    )
                    reconcile_state(board, board_path.parent / "priority-queue.json")
                    save_board(board_path, board)
                    actions.append(f"dev_stale_reset:{task_id_value}")
        row["status"] = "merged"
        row["merged_at"] = now_text
        row["summary"] = "stale planner capability with no result requeued"
        row["blocking_issue"] = "stale_no_result"
        row["last_update_at"] = now_text
        changed = True
    if changed:
        _write_planner_registry_rows(config, rows)
    return actions


def _mark_stale_admin_subagents(root: Path, source: str) -> list[str]:
    config, rows = _planner_registry_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    threshold_seconds = ADMIN_CAPABILITY_TIMEOUT_SECONDS + STALE_SUBAGENT_GRACE_SECONDS
    now_text = now_iso()
    changed = False
    actions: list[str] = []
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if str(row.get("target_role", "")).strip().lower() != "admin":
            continue
        if str(row.get("status", "")).strip().lower() not in ACTIVE_STATUSES:
            continue
        subagent_id = str(row.get("subagent_id", "")).strip()
        if not subagent_id:
            continue
        result_path = config.results_dir / f"{subagent_id}.result.json"
        if result_path.exists():
            continue
        created_raw = str(row.get("created_at", "")).strip() or str(row.get("last_update_at", "")).strip()
        created_at = _parse_iso_utc(created_raw)
        if created_at is None:
            continue
        age_seconds = max(0, int((datetime.now(timezone.utc) - created_at).total_seconds()))
        if age_seconds < threshold_seconds:
            continue
        task_id_value = str(row.get("owner_task_id", "")).strip()
        if task_id_value:
            with board_lock(board_path):
                board = load_board(board_path)
                task = task_index(board).get(task_id_value)
                if isinstance(task, dict):
                    task["state"] = STATE_READY
                    task["blocked_reason"] = ""
                    task["stalled_reason"] = "planner_capability_stale_no_result"
                    task["updated_at"] = now_text
                    task["last_progress_at"] = now_text
                    append_event(
                        board,
                        "planner_orchestrator_admin_dispatch_stale",
                        {"task_id": task_id_value, "source": source, "subagent_id": subagent_id, "age_s": age_seconds},
                    )
                    reconcile_state(board, board_path.parent / "priority-queue.json")
                    save_board(board_path, board)
                    actions.append(f"admin_stale_reset:{task_id_value}")
        row["status"] = "merged"
        row["merged_at"] = now_text
        row["summary"] = "stale planner capability with no result requeued"
        row["blocking_issue"] = "stale_no_result"
        row["last_update_at"] = now_text
        changed = True
    if changed:
        _write_planner_registry_rows(config, rows)
    return actions


def _has_active_subagent(root: Path, target_role: str = "") -> bool:
    _, rows = _planner_registry_rows(root)
    target = str(target_role or "").strip().lower()
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if target and str(row.get("target_role", "")).strip().lower() != target:
            continue
        if str(row.get("status", "")).strip().lower() in ACTIVE_STATUSES:
            return True
    return False


def _collect_finished_dev_subagents(root: Path, source: str) -> list[str]:
    config, rows = _planner_registry_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if str(row.get("target_role", "")).strip().lower() != "dev":
            continue
        subagent_id = str(row.get("subagent_id", "")).strip()
        if not subagent_id:
            continue
        if str(row.get("status", "")).strip().lower() == "merged":
            continue
        result_path = config.results_dir / f"{subagent_id}.result.json"
        if not result_path.exists() and str(row.get("status", "")).strip().lower() in ACTIVE_STATUSES:
            continue
        rc, payload = collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        if rc != 0 or not isinstance(payload, dict):
            continue
        task_id_value = str(payload.get("owner_task_id") or row.get("owner_task_id", "")).strip()
        if not task_id_value:
            continue
        actions.append(f"dev_collect:{task_id_value}")
        status_token = _payload_status(payload)
        if status_token in SUCCESS_SUBAGENT_STATUSES and _payload_has_delivery_evidence(payload):
            evidence = {
                "root_cause": str(payload.get("root_cause", "none")),
                "fix_applied": str(payload.get("fix_applied", "none")),
                "artifact": str(payload.get("artifact", "none")),
                "verify": str(payload.get("verify", "none")),
                "files_touched": str(payload.get("files_touched", "none")),
                "tests_run": str(payload.get("tests_run", "SKIP(no_tests)")),
                "commit_sha": str(payload.get("commit_sha", "none")),
                "architecture_check": str(payload.get("architecture_check", "none")),
                "vision_alignment": str(payload.get("vision_alignment", "none")),
                "cmd": "SKIP(subagent_exec_internal)",
                "next_action_unique": f"PLANNER_MERGE_{task_id_value}",
            }
            with board_lock(board_path):
                board = load_board(board_path)
                completed = _complete_task_from_evidence(
                    root=root,
                    board_path=board_path,
                    role="dev",
                    task_id_value=task_id_value,
                    evidence=evidence,
                    source=source,
                    board=board,
                )
                if completed:
                    actions.append(f"dev_complete:{task_id_value}")
                    task = task_index(board).get(task_id_value, {})
                    qa_dispatch = _launch_qa_review_worker(
                        root,
                        task if isinstance(task, dict) else {"id": task_id_value},
                        source,
                    )
                    if qa_dispatch.get("dispatched"):
                        append_event(
                            board,
                            "planner_orchestrator_qa_review_dispatched",
                            {"task_id": task_id_value, "source": source},
                        )
                        reconcile_state(board, board_path.parent / "priority-queue.json")
                        save_board(board_path, board)
                        actions.append(f"qa_dispatch:{task_id_value}")
                else:
                    set_block_state(board, task_id_value=task_id_value, reason="planner_dev_capability_failed:complete_merge_failed", blocked=True)
                    append_event(board, "planner_orchestrator_dev_complete_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id})
                    reconcile_state(board, board_path.parent / "priority-queue.json")
                    save_board(board_path, board)
            continue
        blocking_issue = str(payload.get("blocking_issue") or payload.get("recommended_next") or status_token or "subagent_not_ready")
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason=f"planner_dev_capability_failed:{blocking_issue}", blocked=True)
            append_event(board, "planner_orchestrator_dev_dispatch_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id})
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        actions.append(f"dev_block:{task_id_value}")
    return actions


def _collect_finished_admin_subagents(root: Path, source: str) -> list[str]:
    config, rows = _planner_registry_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if str(row.get("target_role", "")).strip().lower() != "admin":
            continue
        subagent_id = str(row.get("subagent_id", "")).strip()
        if not subagent_id:
            continue
        if str(row.get("status", "")).strip().lower() == "merged":
            continue
        result_path = config.results_dir / f"{subagent_id}.result.json"
        if not result_path.exists() and str(row.get("status", "")).strip().lower() in ACTIVE_STATUSES:
            continue
        rc, payload = collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        if rc != 0 or not isinstance(payload, dict):
            continue
        task_id_value = str(payload.get("owner_task_id") or row.get("owner_task_id", "")).strip()
        if not task_id_value:
            continue
        actions.append(f"admin_collect:{task_id_value}")
        status_token = _payload_status(payload)
        if status_token in SUCCESS_SUBAGENT_STATUSES and _payload_has_delivery_evidence(payload, target_role="admin"):
            evidence = {
                "root_cause": str(payload.get("root_cause", "none")),
                "fix_applied": str(payload.get("fix_applied", "none")),
                "artifact": str(payload.get("artifact", "none")),
                "verify": str(payload.get("verify", "none")),
                "files_touched": str(payload.get("files_touched", "none")),
                "tests_run": str(payload.get("tests_run", "SKIP(no_tests)")),
                "commit_sha": str(payload.get("commit_sha", "none")),
                "architecture_check": str(payload.get("architecture_check", "none")),
                "vision_alignment": str(payload.get("vision_alignment", "none")),
                "cmd": "SKIP(subagent_exec_internal)",
                "next_action_unique": f"PLANNER_MERGE_{task_id_value}",
            }
            with board_lock(board_path):
                board = load_board(board_path)
                completed = _complete_task_from_evidence(
                    root=root,
                    board_path=board_path,
                    role="admin",
                    task_id_value=task_id_value,
                    evidence=evidence,
                    source=source,
                    board=board,
                )
                if completed:
                    actions.append(f"admin_complete:{task_id_value}")
                else:
                    set_block_state(board, task_id_value=task_id_value, reason="planner_admin_capability_failed:complete_merge_failed", blocked=True)
                    append_event(board, "planner_orchestrator_admin_complete_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id})
                    reconcile_state(board, board_path.parent / "priority-queue.json")
                    save_board(board_path, board)
            continue
        blocking_issue = str(payload.get("blocking_issue") or payload.get("recommended_next") or status_token or "subagent_not_ready")
        with board_lock(board_path):
            board = load_board(board_path)
            set_block_state(board, task_id_value=task_id_value, reason=f"planner_admin_capability_failed:{blocking_issue}", blocked=True)
            append_event(board, "planner_orchestrator_admin_dispatch_failed", {"task_id": task_id_value, "source": source, "subagent_id": subagent_id})
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        actions.append(f"admin_block:{task_id_value}")
    return actions


def _collect_finished_qa_workers(root: Path, source: str) -> list[str]:
    config, rows = _load_worker_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if str(row.get("worker_type", "")).strip() != "qa_review_worker":
            continue
        worker_id = str(row.get("worker_id", "")).strip()
        if not worker_id:
            continue
        if str(row.get("status", "")).strip().lower() == "merged":
            continue
        result_path = config.results_dir / f"{worker_id}.result.json"
        if not result_path.exists() and str(row.get("status", "")).strip().lower() in ACTIVE_STATUSES:
            continue
        rc, payload = collect_worker(config, "planner", worker_id, "", mark_merged=True)
        if rc != 0 or not isinstance(payload, dict):
            continue
        task_id_value = str(payload.get("owner_task_id") or row.get("owner_task_id", "")).strip()
        if not task_id_value:
            continue
        actions.append(f"qa_collect:{task_id_value}")
        with board_lock(board_path):
            board = load_board(board_path)
            index = task_index(board)
            task = index.get(task_id_value)
            if not isinstance(task, dict):
                continue
            task["qa_status"] = str(payload.get("status", "unknown")).strip() or "unknown"
            task["qa_summary"] = str(payload.get("summary", "none")).strip() or "none"
            task["qa_artifact"] = str(payload.get("artifact", "none")).strip() or "none"
            task["qa_verify"] = str(payload.get("verify", "none")).strip() or "none"
            task["qa_last_update_at"] = now_iso()
            if str(payload.get("status", "")).strip().lower() == "completed":
                append_event(board, "planner_orchestrator_qa_review_completed", {"task_id": task_id_value, "source": source, "worker_id": worker_id})
                actions.append(f"qa_complete:{task_id_value}")
            else:
                append_event(board, "planner_orchestrator_qa_review_failed", {"task_id": task_id_value, "source": source, "worker_id": worker_id})
                actions.append(f"qa_failed:{task_id_value}")
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
    return actions


def apply_bridge(root: Path, role: str, contract_text: str, source: str, backend: str = "auto") -> tuple[str, dict[str, Any]]:
    role_token = str(role or "").strip().lower()
    if role_token != "planner":
        return contract_text, {"ok": True, "actions": []}

    contract = _parse_contract(contract_text)
    evidence = _parse_pairs(contract.get("EVIDENCE", ""))
    evidence["next_action_unique"] = contract.get("NEXT_ACTION_UNIQUE", "")
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    actions.extend(_mark_stale_dev_subagents(root, source))
    actions.extend(_mark_stale_admin_subagents(root, source))
    actions.extend(_collect_finished_dev_subagents(root, source))
    actions.extend(_collect_finished_admin_subagents(root, source))
    actions.extend(_collect_finished_qa_workers(root, source))

    task_update = str(evidence.get("task_update", "")).strip().lower()
    task_id_value = str(evidence.get("task_id", "")).strip()
    if task_update == "complete" and task_id_value:
        with board_lock(board_path):
            board = load_board(board_path)
            if _complete_task_from_evidence(
                root=root,
                board_path=board_path,
                role="planner",
                task_id_value=task_id_value,
                evidence=evidence,
                source=source,
                board=board,
            ):
                actions.append(f"planner_complete:{task_id_value}")
    elif task_update == "claim" and task_id_value:
        with board_lock(board_path):
            board = load_board(board_path)
            if _claim_task(
                board_path=board_path,
                role="planner",
                task_id_value=task_id_value,
                source=source,
                board=board,
            ):
                actions.append(f"planner_claim:{task_id_value}")

    dispatch: dict[str, Any] = {"dispatched": False, "reason": "active_subagent_present" if _has_active_subagent(root, "dev") else "not_needed"}
    if not _has_active_subagent(root, "dev"):
        dispatch = _dispatch_dev_capability(root, source=source, backend=backend)
        if dispatch.get("dispatched"):
            actions.append(f"dev_dispatch:{dispatch.get('task_id', 'unknown')}")
            if dispatch.get("completed"):
                actions.append(f"dev_complete:{dispatch.get('task_id', 'unknown')}")
    if not dispatch.get("dispatched") and not _has_active_subagent(root, "admin"):
        dispatch = _dispatch_admin_capability(root, source=source, backend=backend)
        if dispatch.get("dispatched"):
            actions.append(f"admin_dispatch:{dispatch.get('task_id', 'unknown')}")
            if dispatch.get("completed"):
                actions.append(f"admin_complete:{dispatch.get('task_id', 'unknown')}")
    contract = _append_bridge_actions(contract, actions)
    return _render_contract(contract), {"ok": True, "actions": actions, "dispatch": dispatch}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Planner orchestrator execution bridge")
    parser.add_argument("--root", default=str(Path.cwd()))
    parser.add_argument("--role", default="planner")
    parser.add_argument("--source", default="runner")
    parser.add_argument("--backend", default="auto", choices=["auto", "openclaw", "codex_exec", "mock"])
    parser.add_argument("--contract-file", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    contract_path = Path(args.contract_file).expanduser().resolve()
    text = contract_path.read_text(encoding="utf-8", errors="ignore")
    updated, payload = apply_bridge(root=root, role=args.role, contract_text=text, source=args.source, backend=args.backend)
    contract_path.write_text(updated, encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
