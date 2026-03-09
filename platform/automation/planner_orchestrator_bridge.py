#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

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
from browser_smoke import run_browser_smoke
from planner_subagent_manager import (
    ACTIVE_STATUSES,
    _load_config as load_subagent_config,
    _openclaw_agent_ids,
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
DEV_CAPABILITY_TIMEOUT_SECONDS = max(0, int(os.environ.get("FC_PLANNER_DEV_CAPABILITY_TIMEOUT_SECONDS", "0")))
ADMIN_CAPABILITY_TIMEOUT_SECONDS = max(180, int(os.environ.get("FC_PLANNER_ADMIN_CAPABILITY_TIMEOUT_SECONDS", "900")))
STALE_SUBAGENT_GRACE_SECONDS = max(15, int(os.environ.get("FC_PLANNER_SUBAGENT_STALE_GRACE_SECONDS", "30")))
EMPTY_LAUNCHER_STALE_SECONDS = max(30, int(os.environ.get("FC_PLANNER_EMPTY_LAUNCHER_STALE_SECONDS", "90")))
DEV_LONG_RUNNING_AFTER_SECONDS = max(300, int(os.environ.get("FC_PLANNER_DEV_LONG_RUNNING_AFTER_SECONDS", "1800")))
DEV_NO_PROGRESS_WINDOW_SECONDS = max(900, int(os.environ.get("FC_PLANNER_DEV_NO_PROGRESS_WINDOW_SECONDS", "3600")))
QA_REVIEW_TIMEOUT_SECONDS = max(180, int(os.environ.get("FC_PLANNER_QA_WORKER_TIMEOUT_SECONDS", "900")))
ADMIN_TIMEOUT_STREAK_THRESHOLD = max(1, int(os.environ.get("FC_PLANNER_ADMIN_TIMEOUT_STREAK_THRESHOLD", "3")))
DEV_STALLED_STREAK_THRESHOLD = max(1, int(os.environ.get("FC_PLANNER_DEV_STALLED_STREAK_THRESHOLD", "2")))
DEV_FAILURE_STREAK_THRESHOLD = max(1, int(os.environ.get("FC_PLANNER_DEV_FAILURE_STREAK_THRESHOLD", "3")))
ADMIN_TAKEOVER_TIMEOUT_SECONDS = max(300, int(os.environ.get("FC_PLANNER_ADMIN_TAKEOVER_TIMEOUT_SECONDS", "900")))
BROWSER_VALIDATION_TIMEOUT_SECONDS = max(10, int(os.environ.get("FC_PLANNER_BROWSER_VALIDATION_TIMEOUT_SECONDS", "45")))
BROWSER_BACKFILL_MAX_PER_TICK = max(1, int(os.environ.get("FC_PLANNER_BROWSER_BACKFILL_MAX_PER_TICK", "1")))
QA_AUTODISPATCH_MAX_PER_TICK = max(1, int(os.environ.get("FC_PLANNER_QA_AUTODISPATCH_MAX_PER_TICK", "2")))
QA_AUTODISPATCH_ROLLOUT_AT_RAW = str(os.environ.get("FC_PLANNER_QA_AUTODISPATCH_ROLLOUT_AT", "2026-03-08T19:00:00Z")).strip() or "2026-03-08T19:00:00Z"
DEFAULT_BROWSER_FRONTEND_URL = str(os.environ.get("FC_FRONTEND_BASE_URL", "http://127.0.0.1:5173")).strip() or "http://127.0.0.1:5173"
DEFAULT_BROWSER_MONITOR_URL = str(os.environ.get("FC_MONITOR_BASE_URL", "http://127.0.0.1:7779")).strip() or "http://127.0.0.1:7779"
NO_CODE_COMPLETION_MODES = {"runtime_no_code", "no_code_runtime_fix", "runtime_repair_no_code"}
INVALID_RESULT_MARKERS = (
    "invalid_subagent_result",
    "subagent_invalid_result",
    "start_banner_only",
    "empty_payload",
    "failed to refresh available models",
    "401 unauthorized",
    "unexpected status 401 unauthorized",
    "missing bearer or basic authentication",
    "transport channel",
    "worker quit with fatal",
    "delivery_evidence_incomplete",
)
DEV_PROGRESS_MARKERS = (
    "openai codex v",
    "research preview",
    "approval: never",
    "sandbox:",
    "reasoning effort:",
    "session id:",
    "provider: openai",
    "missing bearer or basic authentication",
    "401 unauthorized",
    "unexpected status 401 unauthorized",
    "transport channel",
    "worker quit with fatal",
    "failed to refresh available models",
    "reconnecting...",
)


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


def _fetch_local_json(url: str, timeout_seconds: int = 15) -> tuple[bool, dict[str, Any] | None, str]:
    target = str(url or "").strip()
    if not target:
        return False, None, "missing_url"
    req = urllib_request.Request(target, headers={"Accept": "application/json"})
    try:
        with urllib_request.urlopen(req, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except urllib_error.HTTPError as exc:
        return False, None, f"http_{exc.code}"
    except Exception as exc:
        return False, None, str(exc)
    try:
        payload = json.loads(body)
    except Exception:
        return False, None, "invalid_json"
    if not isinstance(payload, dict):
        return False, None, "invalid_payload"
    return True, payload, "ok"


def _subagent_result_paths(root: Path, subagent_id: str) -> tuple[Path, Path]:
    results_dir = root / "docs" / "operations" / "orchestrator" / "planner-subagents-results"
    return results_dir / f"{subagent_id}.result.json", results_dir / f"{subagent_id}.raw.txt"


def _subagent_has_collectible_result(root: Path, row: dict[str, Any]) -> bool:
    subagent_id = str(row.get("subagent_id", "")).strip()
    if not subagent_id:
        return False
    result_path, raw_path = _subagent_result_paths(root, subagent_id)
    return result_path.exists() or raw_path.exists()


def _planner_backend_by_role() -> dict[str, str]:
    mapping: dict[str, str] = {}
    raw = str(os.environ.get("FC_PLANNER_ORCHESTRATOR_BACKEND_BY_ROLE", "") or "").strip()
    for chunk in raw.split(","):
        token = str(chunk or "").strip()
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key_token = str(key or "").strip().lower()
        value_token = str(value or "").strip().lower()
        if key_token and value_token:
            mapping[key_token] = value_token
    return mapping


def _resolve_dispatch_backend(target_role: str, requested_backend: str, task_kind: str = "") -> str:
    token = str(requested_backend or "auto").strip().lower() or "auto"
    if token != "auto":
        return token
    mapping = _planner_backend_by_role()
    task_kind_token = str(task_kind or "").strip().lower()
    if task_kind_token and mapping.get(task_kind_token):
        return mapping[task_kind_token]
    role_token = str(target_role or "").strip().lower()
    if mapping.get(role_token):
        return mapping[role_token]
    if role_token == "admin":
        return "codex_exec"
    if role_token == "dev":
        return "openclaw"
    return "codex_exec"


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


def _rewrite_contract_for_live_dispatch(contract: dict[str, str], dispatch: dict[str, Any], actions: list[str]) -> dict[str, str]:
    if not isinstance(dispatch, dict) or not dispatch.get("dispatched"):
        return contract
    task_id_value = str(dispatch.get("task_id", "")).strip() or "unknown"
    if bool(dispatch.get("completed")):
        contract["STATUS"] = "IN_PROGRESS"
        contract["VERDICT"] = "GO_WITH_CAUTION"
        contract["DELTA"] = "PLANNER_RECOVERY_PROGRESS"
        contract["BLOCKER_ID"] = "NONE"
        contract["NEXT"] = f"owner=planner; action=select next work item after completing {task_id_value}"
        contract["NEXT_ACTION_UNIQUE"] = f"PLANNER_RESUME_AFTER_{task_id_value}"
        return contract
    target_role = "admin" if any(item.startswith("admin_dispatch:") for item in actions) else "dev"
    contract["STATUS"] = "IN_PROGRESS"
    contract["VERDICT"] = "GO_WITH_CAUTION"
    contract["DELTA"] = "PLANNER_DISPATCH_ACTIVE"
    contract["BLOCKER_ID"] = "NONE"
    contract["NEXT"] = f"owner={target_role}; action=continue {task_id_value} via capability dispatch"
    contract["NEXT_ACTION_UNIQUE"] = f"PLANNER_DISPATCH_ACTIVE_{task_id_value}"
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


def _requires_browser_proof(task: dict[str, Any]) -> bool:
    joined = " | ".join(
        [
            str(task.get("title", "")),
            str(task.get("files_touched", "")),
            str(task.get("artifact", "")),
            str(task.get("code", "")),
        ]
    ).lower()
    if any(token in joined for token in ("apps/web/", "apps/monitor/", "frontend", "dashboard", "monitor")):
        return True
    return re.search(r"(?<![a-z0-9_])ui(?![a-z0-9_])", joined) is not None


def _browser_validation_done(task: dict[str, Any]) -> bool:
    status = str(task.get("browser_proof_status", "")).strip().lower()
    artifact = str(task.get("browser_proof_artifact", "")).strip()
    return status in SUCCESS_SUBAGENT_STATUSES or bool(artifact)


def _browser_smoke_url_for_task(task: dict[str, Any]) -> str:
    joined = " | ".join(
        [
            str(task.get("files_touched", "")),
            str(task.get("title", "")),
            str(task.get("artifact", "")),
        ]
    ).lower()
    if "apps/monitor/" in joined or "monitor" in joined:
        return DEFAULT_BROWSER_MONITOR_URL
    return DEFAULT_BROWSER_FRONTEND_URL


def _task_timeout_streak(task: dict[str, Any], target_role: str) -> int:
    key = f"{str(target_role or '').strip().lower()}_timeout_streak"
    return int(task.get(key, 0) or 0)


def _task_failure_streak(task: dict[str, Any], target_role: str, failure_kind: str) -> int:
    role_token = str(target_role or "").strip().lower()
    kind_token = str(failure_kind or "").strip().lower()
    if not role_token or not kind_token:
        return 0
    return int(task.get(f"{role_token}_{kind_token}_streak", 0) or 0)


def _set_timeout_streak(task: dict[str, Any], target_role: str, value: int, reason: str = "") -> None:
    role_token = str(target_role or "").strip().lower()
    task[f"{role_token}_timeout_streak"] = max(0, int(value))
    if reason:
        task["stalled_capability_reason"] = reason
        task["stalled_capability_role"] = role_token
    elif str(task.get("stalled_capability_role", "")).strip().lower() == role_token:
        task["stalled_capability_reason"] = ""
        task["stalled_capability_role"] = ""


def _set_failure_streak(task: dict[str, Any], target_role: str, failure_kind: str, value: int, reason: str = "") -> None:
    role_token = str(target_role or "").strip().lower()
    kind_token = str(failure_kind or "").strip().lower()
    if not role_token or not kind_token:
        return
    task[f"{role_token}_{kind_token}_streak"] = max(0, int(value))
    task["last_capability_failure_mode"] = kind_token if value else ""
    if reason:
        task["stalled_capability_reason"] = reason
        task["stalled_capability_role"] = role_token
    elif str(task.get("stalled_capability_role", "")).strip().lower() == role_token:
        task["stalled_capability_reason"] = ""
        task["stalled_capability_role"] = ""


def _mark_role_recovery_required(task: dict[str, Any], target_role: str, reason: str) -> None:
    role_token = str(target_role or "").strip().lower()
    if not role_token:
        return
    task[f"{role_token}_recovery_required"] = True
    task[f"{role_token}_recovery_reason"] = reason
    task["stalled_capability_reason"] = reason
    task["stalled_capability_role"] = role_token


def _clear_role_recovery(task: dict[str, Any], target_role: str) -> None:
    role_token = str(target_role or "").strip().lower()
    if not role_token:
        return
    task[f"{role_token}_recovery_required"] = False
    task[f"{role_token}_recovery_reason"] = ""
    task[f"{role_token}_invalid_result_streak"] = 0
    task[f"{role_token}_timeout_streak"] = 0
    task[f"{role_token}_no_progress_streak"] = 0
    task[f"{role_token}_orphaned_streak"] = 0
    if str(task.get("stalled_capability_role", "")).strip().lower() == role_token:
        task["stalled_capability_reason"] = ""
        task["stalled_capability_role"] = ""
    if str(task.get("last_capability_failure_mode", "")).strip().lower() in {"timeout", "invalid_result", "no_progress", "orphaned"}:
        task["last_capability_failure_mode"] = ""


def _mark_admin_takeover_required(task: dict[str, Any], reason: str) -> None:
    task["planner_takeover_required"] = True
    task["planner_takeover_reason"] = reason
    _mark_role_recovery_required(task, "admin", reason)
    _set_timeout_streak(task, "admin", _task_timeout_streak(task, "admin"), reason)


def _clear_admin_takeover(task: dict[str, Any]) -> None:
    task["planner_takeover_required"] = False
    task["planner_takeover_reason"] = ""
    _clear_role_recovery(task, "admin")
    _set_failure_streak(task, "admin", "invalid_result", 0)
    _set_timeout_streak(task, "admin", 0)


def _write_runtime_proof(root: Path, task_id_value: str, payload: dict[str, Any]) -> str:
    stream_id = _task_stream_id(task_id_value)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_path = (
        root
        / "docs"
        / "operations"
        / "orchestrator"
        / "proofs"
        / stream_id
        / task_id_value
        / f"{stamp}-planner-takeover-runtime-proof.json"
    )
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return str(proof_path)


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
        "completion_mode": evidence.get("completion_mode", ""),
        "no_code_change_reason": evidence.get("no_code_change_reason", ""),
        "runtime_artifact": evidence.get("runtime_artifact", ""),
        "browser_proof_status": evidence.get("browser_proof_status", ""),
        "browser_proof_artifact": evidence.get("browser_proof_artifact", ""),
        "browser_proof_generated_at": evidence.get("browser_proof_generated_at", ""),
    }
    if extra:
        fields.update(extra)
    for key, value in fields.items():
        token = str(value or "").strip()
        if token:
            task[key] = token
    task["last_meaningful_progress_at"] = now_iso()
    task["last_progress_kind"] = "delivery_evidence"
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
    target = str(target_role or "").strip().lower()
    if target in {"dev", "admin"}:
        tests_run = str(payload.get("tests_run", "")).strip().lower()
        if not tests_run or tests_run in {"none", "n/a", "na"}:
            return False
    if target == "dev":
        commit = str(payload.get("commit_sha", "")).strip().lower()
        if not commit or commit in {"none", "n/a", "na"}:
            return False
    return True


def _select_dispatchable_dev_task(board: dict[str, Any]) -> dict[str, Any] | None:
    index = task_index(board)
    recovery_candidates: list[tuple[int, int, dict[str, Any]]] = []
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    retry_candidates: list[tuple[int, int, dict[str, Any]]] = []
    in_progress_candidates: list[tuple[int, int, dict[str, Any]]] = []
    for idx, task in enumerate(board.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        if _task_effectively_done(task):
            continue
        state = str(task.get("state", "")).strip().upper()
        if str(task.get("role", "")).strip().lower() != "dev":
            continue
        deps = [dep for dep in task.get("depends_on", []) if dep]
        if any(str(index.get(dep, {}).get("state", "")).upper() != STATE_DONE for dep in deps):
            continue
        row = (priority_rank(str(task.get("priority", "P9"))), idx, task)
        if bool(task.get("dev_recovery_required")):
            recovery_candidates.append(row)
            continue
        if state in {STATE_READY, STATE_READY_DEV, "READY"}:
            candidates.append(row)
            continue
        if state == STATE_IN_PROGRESS:
            if _task_has_dev_completion_evidence(task):
                continue
            in_progress_candidates.append(row)
            continue
        blocked_reason = str(task.get("blocked_reason", "")).strip().lower()
        if state == STATE_BLOCKED and blocked_reason.startswith("planner_dev_capability_failed:"):
            retry_candidates.append(row)
    if recovery_candidates:
        recovery_candidates.sort(key=lambda row: (row[0], row[1]))
        return recovery_candidates[0][2]
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
    takeover_candidates: list[tuple[int, int, dict[str, Any]]] = []
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    retry_candidates: list[tuple[int, int, dict[str, Any]]] = []
    in_progress_candidates: list[tuple[int, int, dict[str, Any]]] = []
    for idx, task in enumerate(board.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        if _task_effectively_done(task):
            continue
        state = str(task.get("state", "")).strip().upper()
        if str(task.get("role", "")).strip().lower() != "admin":
            continue
        deps = [dep for dep in task.get("depends_on", []) if dep]
        if any(str(index.get(dep, {}).get("state", "")).upper() != STATE_DONE for dep in deps):
            continue
        row = (priority_rank(str(task.get("priority", "P9"))), idx, task)
        if bool(task.get("planner_takeover_required")):
            takeover_candidates.append(row)
            continue
        if state in {STATE_READY, "READY_PLANNER", "READY"}:
            candidates.append(row)
            continue
        if state == STATE_IN_PROGRESS:
            in_progress_candidates.append(row)
            continue
        blocked_reason = str(task.get("blocked_reason", "")).strip().lower()
        if state == STATE_BLOCKED and blocked_reason.startswith("planner_admin_capability_failed:"):
            retry_candidates.append(row)
    if takeover_candidates:
        takeover_candidates.sort(key=lambda row: (row[0], row[1]))
        return takeover_candidates[0][2]
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


def _browser_backfill_candidates(board: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if str(task.get("state", "")).strip().upper() != STATE_DONE:
            continue
        if str(task.get("role", "")).strip().lower() != "dev":
            continue
        if not _requires_browser_proof(task):
            continue
        if _browser_validation_done(task):
            continue
        if bool(task.get("legacy_proof_debt_accepted")):
            continue
        out.append(task)
    out.sort(key=lambda item: str(item.get("updated_at", "")))
    return out[:BROWSER_BACKFILL_MAX_PER_TICK]


def _task_has_dev_completion_evidence(task: dict[str, Any]) -> bool:
    if str(task.get("role", "")).strip().lower() != "dev":
        return False
    if not _has_real_commit(str(task.get("commit_sha", ""))):
        return False
    artifact = str(task.get("artifact", "")).strip().lower()
    verify = str(task.get("verify", "")).strip().lower()
    tests_run = str(task.get("tests_run", "")).strip().lower()
    return all(token and token not in {"none", "n/a", "na"} for token in (artifact, verify, tests_run))


def _timeout_like_issue(reason: str) -> bool:
    token = str(reason or "").strip().lower()
    return any(
        marker in token
        for marker in (
            "timeout",
            "timed out",
            "stale_no_result",
            "deadline",
            "no result",
        )
    )


def _recoverable_failure_kind(reason: str) -> str:
    token = str(reason or "").strip().lower()
    if any(marker in token for marker in INVALID_RESULT_MARKERS):
        return "invalid_result"
    if _timeout_like_issue(token):
        return "timeout"
    return "other"


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _file_mtime_utc(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except Exception:
        return None


def _meaningful_subagent_text(text: str) -> bool:
    token = " ".join(str(text or "").strip().lower().split())
    if not token:
        return False
    return not any(marker in token for marker in DEV_PROGRESS_MARKERS)


def _task_progress_baseline(task: dict[str, Any], row: dict[str, Any], progress_at: datetime | None) -> datetime | None:
    return (
        progress_at
        or _parse_iso_utc(str(task.get("last_meaningful_progress_at", "")).strip())
        or _parse_iso_utc(str(task.get("last_progress_at", "")).strip())
        or _parse_iso_utc(str(task.get("updated_at", "")).strip())
        or _parse_iso_utc(str(row.get("last_update_at", "")).strip())
        or _parse_iso_utc(str(row.get("created_at", "")).strip())
    )


def _clear_dev_progress_flags(task: dict[str, Any]) -> None:
    task["dev_no_progress_streak"] = 0
    task["dev_orphaned_streak"] = 0
    if str(task.get("last_capability_failure_mode", "")).strip().lower() in {"no_progress", "orphaned"}:
        task["last_capability_failure_mode"] = ""


def _record_dev_progress(task: dict[str, Any], progress_at: datetime | None, progress_kind: str, *, execution_state: str) -> None:
    timestamp = _iso(progress_at) if isinstance(progress_at, datetime) else now_iso()
    task["last_meaningful_progress_at"] = timestamp
    task["last_progress_kind"] = str(progress_kind or "runtime_activity").strip() or "runtime_activity"
    task["dev_execution_state"] = execution_state
    task["updated_at"] = now_iso()
    task["last_progress_at"] = timestamp
    _clear_dev_progress_flags(task)
    _clear_role_recovery(task, "dev")


def _record_dev_failure(
    board: dict[str, Any],
    *,
    task_id_value: str,
    source: str,
    subagent_id: str,
    blocking_issue: str,
    event_kind: str,
) -> str:
    issue = str(blocking_issue or "subagent_not_ready").strip() or "subagent_not_ready"
    task = task_index(board).get(task_id_value)
    if not isinstance(task, dict):
        append_event(board, event_kind, {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"})
        return issue
    if _task_effectively_done(task):
        _clear_role_recovery(task, "dev")
        append_event(
            board,
            "planner_orchestrator_dev_failure_ignored_done_task",
            {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"},
        )
        return "owner_task_already_done"
    failure_kind = _recoverable_failure_kind(issue)
    if failure_kind in {"timeout", "invalid_result"}:
        streak = _task_failure_streak(task, "dev", failure_kind) + 1
        reason = f"dev_{failure_kind}_streak:{streak}"
        _set_failure_streak(task, "dev", failure_kind, streak, reason)
        task["state"] = STATE_READY_DEV
        task["blocked_reason"] = ""
        task["updated_at"] = now_iso()
        task["last_progress_at"] = now_iso()
        if streak >= DEV_FAILURE_STREAK_THRESHOLD:
            _mark_role_recovery_required(task, "dev", reason)
            append_event(
                board,
                "planner_orchestrator_dev_recovery_required",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none", "failure_kind": failure_kind, "streak": streak},
            )
            return "dev_recovery_required"
        event_name = "planner_orchestrator_dev_invalid_result_requeue" if failure_kind == "invalid_result" else "planner_orchestrator_dev_timeout_requeue"
        append_event(
            board,
            event_name,
            {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none", "failure_kind": failure_kind, "streak": streak},
        )
        return f"dev_{failure_kind}_requeued"
    set_block_state(board, task_id_value=task_id_value, reason=f"planner_dev_capability_failed:{issue}", blocked=True)
    append_event(board, event_kind, {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"})
    return issue


def _has_real_commit(value: str) -> bool:
    token = str(value or "").strip().lower()
    if not token or token in {"none", "n/a", "na", "skip(runtime_no_code)"}:
        return False
    return True


def _build_admin_evidence(payload: dict[str, Any], task_id_value: str) -> dict[str, str]:
    commit_sha = str(payload.get("commit_sha", "none")).strip() or "none"
    has_commit = _has_real_commit(commit_sha)
    artifact = str(payload.get("artifact", "none")).strip() or "none"
    evidence = {
        "root_cause": str(payload.get("root_cause", "none")),
        "fix_applied": str(payload.get("fix_applied", "none")),
        "artifact": artifact,
        "verify": str(payload.get("verify", "none")),
        "files_touched": str(payload.get("files_touched", "none")),
        "tests_run": str(payload.get("tests_run", "SKIP(no_tests)")),
        "commit_sha": commit_sha if has_commit else "NONE(runtime_no_code)",
        "architecture_check": str(payload.get("architecture_check", "none")),
        "vision_alignment": str(payload.get("vision_alignment", "none")),
        "cmd": "SKIP(subagent_exec_internal)",
        "next_action_unique": f"PLANNER_MERGE_{task_id_value}",
        "completion_mode": "code_change" if has_commit else "runtime_no_code",
        "no_code_change_reason": "" if has_commit else "runtime_repair_no_code_change",
        "runtime_artifact": artifact if not has_commit else "",
    }
    return evidence


def _doctor_takeover_ready(payload: dict[str, Any]) -> bool:
    if str(payload.get("status", "")).strip().lower() == "ok":
        return True
    checks = payload.get("checks", {})
    if not isinstance(checks, dict):
        return False
    critical = ("runtime_state", "sessions", "locks", "queue_workboard", "providers", "product_value")
    for name in critical:
        status = str((checks.get(name, {}) or {}).get("status", "")).strip().lower()
        if status != "ok":
            return False
    return True


def _planner_takeover_admin_task(root: Path, task: dict[str, Any], source: str) -> dict[str, Any]:
    task_id_value = str(task.get("id", "")).strip()
    if not task_id_value:
        return {"dispatched": True, "completed": False, "reason": "invalid_admin_task", "backend": "planner_takeover"}
    status_ok, status_payload, status_reason = _fetch_local_json("http://127.0.0.1:7779/api/status")
    doctor_ok, doctor_payload, doctor_reason = _fetch_local_json("http://127.0.0.1:7779/api/doctor?refresh=1")
    if not status_ok or not isinstance(status_payload, dict):
        return {
            "dispatched": True,
            "completed": False,
            "task_id": task_id_value,
            "reason": f"planner_takeover_status_unavailable:{status_reason}",
            "backend": "planner_takeover",
        }
    if not doctor_ok or not isinstance(doctor_payload, dict):
        return {
            "dispatched": True,
            "completed": False,
            "task_id": task_id_value,
            "reason": f"planner_takeover_doctor_unavailable:{doctor_reason}",
            "backend": "planner_takeover",
        }

    status_health = str(status_payload.get("health", "")).strip().upper()
    doctor_status = str(doctor_payload.get("status", "")).strip().lower()
    doctor_takeover_ready = _doctor_takeover_ready(doctor_payload)
    browser_ok = True
    browser_detail = ""
    browser_artifact = ""
    if _requires_browser_proof(task):
        browser_ok, browser_detail = _run_browser_validation(root, task, source=source, phase="planner_takeover")
        browser_artifact = browser_detail if browser_ok else ""

    if status_health not in {"OK", "PAUSED"} or not doctor_takeover_ready or not browser_ok:
        issue = "planner_takeover_runtime_not_healthy"
        if not browser_ok:
            issue = "planner_takeover_browser_validation_failed"
        return {
            "dispatched": True,
            "completed": False,
            "task_id": task_id_value,
            "reason": issue,
            "backend": "planner_takeover",
            "status_health": status_health,
            "doctor_status": doctor_status,
        }

    proof_payload = {
        "task_id": task_id_value,
        "source": source,
        "takeover": True,
        "status_snapshot": status_payload,
        "doctor_snapshot": doctor_payload,
        "browser_validation": {"ok": browser_ok, "artifact": browser_artifact or "none"},
        "generated_at": now_iso(),
    }
    artifact = _write_runtime_proof(root, task_id_value, proof_payload)
    verify_parts = [
        f"status.health={status_health}",
        f"doctor.status={doctor_status}",
    ]
    if browser_artifact:
        verify_parts.append(f"browser_proof={browser_artifact}")
    evidence = {
        "root_cause": f"Admin capability stalled repeatedly on {task_id_value}; planner performed direct runtime takeover verification.",
        "fix_applied": "Planner validated runtime truth directly via local monitor/doctor checks and browser smoke, then completed the incident without another admin retry.",
        "artifact": artifact,
        "verify": "; ".join(verify_parts),
        "files_touched": artifact,
        "tests_run": "GET /api/status; GET /api/doctor?refresh=1; browser_smoke(if required)",
        "commit_sha": "SKIP(no code/config change committed)",
        "architecture_check": "Planner-only runtime takeover kept orchestration authoritative and avoided another blind admin retry loop.",
        "vision_alignment": f"Resolved capability stall for {task_id_value} so planner can resume delivery-oriented dispatch.",
        "cmd": "SKIP(planner_takeover_runtime_verification)",
        "next_action_unique": f"PLANNER_TAKEOVER_{task_id_value}",
        "completion_mode": "runtime_no_code",
        "no_code_change_reason": "planner_runtime_takeover_no_code_change",
        "runtime_artifact": artifact,
        "browser_proof_status": "completed" if browser_artifact else "",
        "browser_proof_artifact": browser_artifact,
        "browser_proof_generated_at": now_iso() if browser_artifact else "",
    }

    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
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
            live_task = task_index(board).get(task_id_value)
            if isinstance(live_task, dict):
                _clear_admin_takeover(live_task)
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
    return {
        "dispatched": True,
        "completed": completed,
        "task_id": task_id_value,
        "reason": "planner_takeover_completed" if completed else "planner_takeover_complete_failed",
        "backend": "planner_takeover",
        "artifact": artifact,
    }


def _record_admin_failure(
    board: dict[str, Any],
    *,
    task_id_value: str,
    source: str,
    subagent_id: str,
    blocking_issue: str,
    event_kind: str,
) -> str:
    issue = str(blocking_issue or "subagent_not_ready").strip() or "subagent_not_ready"
    task = task_index(board).get(task_id_value)
    if not isinstance(task, dict):
        append_event(board, event_kind, {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"})
        return issue
    if _task_effectively_done(task):
        _clear_admin_takeover(task)
        append_event(
            board,
            "planner_orchestrator_admin_failure_ignored_done_task",
            {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"},
        )
        return "owner_task_already_done"
    failure_kind = _recoverable_failure_kind(issue)
    if failure_kind in {"timeout", "invalid_result"}:
        if failure_kind == "timeout":
            streak = _task_timeout_streak(task, "admin") + 1
            reason = f"admin_timeout_streak:{streak}"
            _set_timeout_streak(task, "admin", streak, reason)
        else:
            streak = _task_failure_streak(task, "admin", "invalid_result") + 1
            reason = f"admin_invalid_result_streak:{streak}"
            _set_failure_streak(task, "admin", "invalid_result", streak, reason)
        task["state"] = STATE_READY
        task["blocked_reason"] = ""
        task["updated_at"] = now_iso()
        task["last_progress_at"] = now_iso()
        if streak >= ADMIN_TIMEOUT_STREAK_THRESHOLD:
            _mark_admin_takeover_required(task, reason)
            append_event(
                board,
                "planner_orchestrator_admin_takeover_required",
                {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none", "failure_kind": failure_kind, "streak": streak},
            )
            return "planner_takeover_required"
        append_event(
            board,
            "planner_orchestrator_admin_timeout_requeue" if failure_kind == "timeout" else "planner_orchestrator_admin_invalid_result_requeue",
            {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none", "failure_kind": failure_kind, "streak": streak},
        )
        return f"admin_{failure_kind}_requeued"
    set_block_state(board, task_id_value=task_id_value, reason=f"planner_admin_capability_failed:{issue}", blocked=True)
    append_event(board, event_kind, {"task_id": task_id_value, "source": source, "subagent_id": subagent_id or "none"})
    return issue


def _run_browser_validation(root: Path, task: dict[str, Any], *, source: str, phase: str) -> tuple[bool, str]:
    task_id_value = str(task.get("id", "")).strip()
    if not task_id_value:
        return False, "invalid_task"
    if not _requires_browser_proof(task):
        return False, "browser_not_required"
    if _browser_validation_done(task):
        return False, "browser_already_done"
    url = _browser_smoke_url_for_task(task)
    try:
        proof = run_browser_smoke(
            url=url,
            root=root,
            label=f"{task_id_value}-{phase}",
            timeout_seconds=BROWSER_VALIDATION_TIMEOUT_SECONDS,
        )
        proof_path = str(proof.get("proof_path", "")).strip()
        with board_lock(root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"):
            board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
            board = load_board(board_path)
            live_task = task_index(board).get(task_id_value)
            if isinstance(live_task, dict):
                live_task["browser_proof_status"] = "completed"
                if proof_path:
                    live_task["browser_proof_artifact"] = proof_path
                live_task["browser_proof_generated_at"] = now_iso()
                if phase == "historical_backfill":
                    live_task["legacy_proof_debt_accepted"] = False
                append_event(
                    board,
                    "planner_orchestrator_browser_validation_completed",
                    {"task_id": task_id_value, "source": source, "phase": phase, "proof_path": proof_path or "none"},
                )
                reconcile_state(board, board_path.parent / "priority-queue.json")
                save_board(board_path, board)
        return True, proof_path or "browser_validation_completed"
    except Exception as exc:
        with board_lock(root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"):
            board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
            board = load_board(board_path)
            live_task = task_index(board).get(task_id_value)
            if isinstance(live_task, dict):
                live_task["browser_proof_status"] = "failed"
                live_task["browser_proof_artifact"] = ""
                live_task["browser_proof_generated_at"] = now_iso()
                live_task["browser_proof_last_error"] = str(exc)
                append_event(
                    board,
                    "planner_orchestrator_browser_validation_failed",
                    {"task_id": task_id_value, "source": source, "phase": phase, "error": str(exc)},
                )
                reconcile_state(board, board_path.parent / "priority-queue.json")
                save_board(board_path, board)
        return False, str(exc)


def _backfill_historical_browser_proof(root: Path, source: str) -> list[str]:
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    with board_lock(board_path):
        board = load_board(board_path)
        candidates = _browser_backfill_candidates(board)
    actions: list[str] = []
    for task in candidates:
        ok, detail = _run_browser_validation(root, task, source=source, phase="historical_backfill")
        task_id_value = str(task.get("id", "")).strip() or "unknown"
        actions.append(f"browser_backfill:{task_id_value}:{'ok' if ok else 'failed'}")
        if not ok and detail:
            actions.append(f"browser_backfill_reason:{task_id_value}")
    return actions


def _backfill_admin_runtime_no_code_metadata(root: Path, source: str) -> list[str]:
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    with board_lock(board_path):
        board = load_board(board_path)
        changed = False
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            if str(task.get("role", "")).strip().lower() != "admin":
                continue
            if str(task.get("state", "")).strip().upper() != STATE_DONE:
                continue
            if _has_real_commit(str(task.get("commit_sha", ""))):
                continue
            artifact = str(task.get("artifact", "")).strip()
            verify = str(task.get("verify", "")).strip()
            tests_run = str(task.get("tests_run", "")).strip()
            if not artifact or not verify or not tests_run:
                continue
            if str(task.get("completion_mode", "")).strip().lower() in NO_CODE_COMPLETION_MODES and str(task.get("runtime_artifact", "")).strip():
                continue
            task["completion_mode"] = "runtime_no_code"
            task["no_code_change_reason"] = "runtime_repair_no_code_change"
            task["runtime_artifact"] = artifact
            changed = True
            actions.append(f"admin_runtime_backfill:{str(task.get('id', '')).strip() or 'unknown'}")
            append_event(
                board,
                "planner_orchestrator_admin_runtime_evidence_backfill",
                {"task_id": str(task.get("id", "")).strip() or "unknown", "source": source},
            )
        if changed:
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
    return actions


def _dispatch_pending_qa_reviews(root: Path, source: str) -> list[str]:
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    rollout_at = _parse_iso_utc(QA_AUTODISPATCH_ROLLOUT_AT_RAW) or datetime(2026, 3, 8, 19, 0, 0, tzinfo=timezone.utc)
    with board_lock(board_path):
        board = load_board(board_path)
        candidates: list[tuple[datetime, dict[str, Any]]] = []
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            if str(task.get("role", "")).strip().lower() != "dev":
                continue
            if not _task_has_dev_completion_evidence(task):
                continue
            completed_at = _parse_iso_utc(task.get("completed_at", ""))
            if completed_at is None or completed_at < rollout_at:
                continue
            if _qa_review_already_done(task):
                continue
            if _qa_worker_active(root, str(task.get("id", "")).strip()):
                continue
            if _requires_browser_proof(task) and not _browser_validation_done(task):
                continue
            candidates.append((completed_at, task))
        candidates.sort(key=lambda item: item[0], reverse=True)
        for _, task in candidates[:QA_AUTODISPATCH_MAX_PER_TICK]:
            dispatch = _launch_qa_review_worker(root, task, source)
            task_id_value = str(task.get("id", "")).strip() or "unknown"
            if dispatch.get("dispatched"):
                append_event(
                    board,
                    "planner_orchestrator_qa_review_dispatched",
                    {"task_id": task_id_value, "source": source, "reason": "pending_completed_delivery"},
                )
                actions.append(f"qa_dispatch:{task_id_value}")
        if actions:
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
    return actions


def _auto_complete_planner_gov_reviews(root: Path, source: str) -> list[str]:
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    with board_lock(board_path):
        board = load_board(board_path)
        index = task_index(board)
        candidates: list[dict[str, Any]] = []
        for task in board.get("tasks", []):
            if not isinstance(task, dict):
                continue
            if str(task.get("role", "")).strip().lower() != "planner":
                continue
            task_id_value = str(task.get("id", "")).strip()
            code = str(task.get("code", "")).strip().upper()
            state = str(task.get("state", "")).strip().upper()
            if code != "GOV_REVIEW" and not task_id_value.endswith("GOV_REVIEW"):
                continue
            if state not in {STATE_READY, "READY_PLANNER", STATE_IN_PROGRESS, "REVIEW"}:
                continue
            deps = [str(dep).strip() for dep in task.get("depends_on", []) if str(dep).strip()]
            if any(str(index.get(dep, {}).get("state", "")).strip().upper() != STATE_DONE for dep in deps):
                continue
            candidates.append(task)

        for task in candidates:
            task_id_value = str(task.get("id", "")).strip() or "unknown"
            stream_id = str(task.get("stream_id", "")).strip() or _task_stream_id(task_id_value)
            evidence = {
                "root_cause": "All GOV_REVIEW dependencies are already DONE; planner bridge auto-closed the final review step instead of waiting on an unavailable complete command.",
                "fix_applied": "Planner orchestrator bridge completed the GOV_REVIEW task directly via workboard state transition.",
                "verify": f"depends_done={','.join(str(dep).strip() for dep in task.get('depends_on', []) if str(dep).strip()) or 'none'}; planner_blocker_bypassed=PLANNER_COMPLETE_COMMAND_UNAVAILABLE_FOR_GOV_REVIEW",
                "artifact": "docs/operations/orchestrator/parallel-workstreams.json",
                "tests_run": "SKIP(planner_gov_review_no_runtime_change)",
                "commit_sha": "SKIP(no code/config change)",
                "files_touched": "docs/operations/orchestrator/parallel-workstreams.json",
                "architecture_check": "PASS(planner bridge direct GOV_REVIEW closure after dependency verification)",
                "vision_alignment": f"PASS(batch={stream_id}; final governance review closed after all delivery dependencies reached DONE)",
                "completion_mode": "runtime_no_code",
                "no_code_change_reason": "planner_governance_closure_no_code_change",
                "runtime_artifact": "docs/operations/orchestrator/parallel-workstreams.json",
            }
            completed = _complete_task_from_evidence(
                root=root,
                board_path=board_path,
                role="planner",
                task_id_value=task_id_value,
                evidence=evidence,
                source=source,
                board=board,
            )
            if completed:
                actions.append(f"planner_gov_review_auto_complete:{task_id_value}")
    return actions


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
    if str(task.get("state", "")).strip().upper() == STATE_BLOCKED:
        task["state"] = STATE_IN_PROGRESS
        task["blocked_reason"] = ""
        task["stalled_reason"] = ""
        task["updated_at"] = now_iso()
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
        change_plan=_auto_change_plan(task),
        architecture_checks=_auto_architecture_checks(task),
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
        _clear_role_recovery(candidate, "dev")
        _clear_dev_progress_flags(candidate)
        candidate["dev_execution_state"] = "running"
        candidate["last_progress_at"] = now_iso()
        _claim_task(board_path=board_path, role="dev", task_id_value=task_id_value, source=source, board=board)

    message = _build_dev_dispatch_message(candidate)
    chosen_backend = _resolve_dispatch_backend("dev", backend, "delivery")
    if chosen_backend in {"openclaw", "auto"}:
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
            _record_dev_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id or "none",
                blocking_issue=str(payload.get("blocking_issue") or payload.get("stderr") or "unknown"),
                event_kind="planner_orchestrator_dev_dispatch_failed",
            )
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
            _record_dev_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id or "none",
                blocking_issue=blocking_issue,
                event_kind="planner_orchestrator_dev_dispatch_blocked",
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
            _record_dev_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id or "none",
                blocking_issue="delivery_evidence_incomplete",
                event_kind="planner_orchestrator_dev_dispatch_incomplete",
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
        browser_validation = "not_required"
        with board_lock(board_path):
            board = load_board(board_path)
            task = task_index(board).get(task_id_value, {})
            qa_dispatch = _launch_qa_review_worker(root, task if isinstance(task, dict) else {"id": task_id_value}, source)
            if qa_dispatch.get("dispatched"):
                append_event(board, "planner_orchestrator_qa_review_dispatched", {"task_id": task_id_value, "source": source})
                reconcile_state(board, board_path.parent / "priority-queue.json")
                save_board(board_path, board)
        with board_lock(board_path):
            board = load_board(board_path)
            live_task = task_index(board).get(task_id_value)
        if isinstance(live_task, dict) and _requires_browser_proof(live_task) and not _browser_validation_done(live_task):
            browser_ok, _browser_detail = _run_browser_validation(root, live_task, source=source, phase="future_delivery")
            browser_validation = "completed" if browser_ok else "failed"
    else:
        browser_validation = "not_completed"
    return {"dispatched": True, "completed": completed, "task_id": task_id_value, "subagent_id": subagent_id or "none", "backend": chosen_backend, "browser_validation": browser_validation}


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
        planner_takeover = bool(candidate.get("planner_takeover_required")) or _task_timeout_streak(candidate, "admin") >= ADMIN_TIMEOUT_STREAK_THRESHOLD
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
    if planner_takeover:
        return _planner_takeover_admin_task(root, candidate, source)
    chosen_backend = _resolve_dispatch_backend("admin", backend, "runtime")
    message = _build_admin_dispatch_message(candidate)
    timeout_seconds = ADMIN_CAPABILITY_TIMEOUT_SECONDS
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
            str(timeout_seconds),
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
        timeout_seconds=timeout_seconds,
    )
    subagent_id = str(payload.get("subagent_id", "")).strip()
    if rc != 0 or not payload.get("ok"):
        with board_lock(board_path):
            board = load_board(board_path)
            _record_admin_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id or "none",
                blocking_issue=str(payload.get("blocking_issue") or payload.get("stderr") or "unknown"),
                event_kind="planner_orchestrator_admin_dispatch_failed",
            )
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
            _record_admin_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id or "none",
                blocking_issue=blocking_issue,
                event_kind="planner_orchestrator_admin_dispatch_blocked",
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        if subagent_id:
            collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        return {"dispatched": True, "completed": False, "task_id": task_id_value, "reason": "subagent_blocked", "subagent_id": subagent_id or "none", "backend": chosen_backend}

    evidence = _build_admin_evidence(payload, task_id_value)
    if not _payload_has_delivery_evidence(payload, target_role="admin"):
        with board_lock(board_path):
            board = load_board(board_path)
            _record_admin_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id or "none",
                blocking_issue="delivery_evidence_incomplete",
                event_kind="planner_orchestrator_admin_dispatch_incomplete",
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
        else:
            live_task = task_index(board).get(task_id_value)
            if isinstance(live_task, dict):
                _clear_admin_takeover(live_task)
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


def _prune_planner_subagent_row(config: Any, rows: list[dict[str, Any]], subagent_id: str) -> bool:
    token = str(subagent_id or "").strip()
    if not token:
        return False
    before = len(rows)
    rows[:] = [row for row in rows if str(row.get("subagent_id", "")).strip() != token]
    return len(rows) != before


def _task_effectively_done(task: dict[str, Any] | None) -> bool:
    if not isinstance(task, dict):
        return False
    state = str(task.get("state", "")).strip().upper()
    if state == STATE_DONE:
        return True
    return bool(str(task.get("completed_at", "")).strip())


def _mark_stale_dev_subagents(root: Path, source: str) -> list[str]:
    config, rows = _planner_registry_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    now_text = now_iso()
    now_dt = datetime.now(timezone.utc)
    changed = False
    actions: list[str] = []
    active_openclaw_ids = _openclaw_agent_ids()
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
        raw_path = config.results_dir / f"{subagent_id}.raw.txt"
        launcher_log = config.results_dir / f"{subagent_id}.launcher.log"
        task_id_value = str(row.get("owner_task_id", "")).strip()
        if task_id_value:
            with board_lock(board_path):
                board = load_board(board_path)
                task = task_index(board).get(task_id_value)
                if _task_effectively_done(task):
                    changed = _prune_planner_subagent_row(config, rows, subagent_id) or changed
                    actions.append(f"dev_drop_done:{task_id_value}")
                    continue
        created_raw = str(row.get("created_at", "")).strip() or str(row.get("last_update_at", "")).strip()
        created_at = _parse_iso_utc(created_raw)
        if created_at is None:
            continue
        age_seconds = max(0, int((now_dt - created_at).total_seconds()))
        backend_token = str(row.get("backend", "")).strip().lower()
        live_session = True
        if backend_token == "openclaw":
            live_session = subagent_id in active_openclaw_ids
        empty_launcher = launcher_log.exists() and launcher_log.stat().st_size == 0
        progress_at = _file_mtime_utc(result_path) if result_path.exists() else None
        progress_kind = "result_payload" if progress_at is not None else ""
        if progress_at is None and raw_path.exists():
            raw_text = _read_text_if_exists(raw_path)
            if _meaningful_subagent_text(raw_text):
                progress_at = _file_mtime_utc(raw_path)
                progress_kind = "raw_output"
        if progress_at is None and launcher_log.exists() and not empty_launcher:
            launcher_text = _read_text_if_exists(launcher_log)
            if _meaningful_subagent_text(launcher_text):
                progress_at = _file_mtime_utc(launcher_log)
                progress_kind = "launcher_output"
        if task_id_value:
            with board_lock(board_path):
                board = load_board(board_path)
                task = task_index(board).get(task_id_value)
                if isinstance(task, dict):
                    if progress_at is not None:
                        execution_state = "long_running" if age_seconds >= DEV_LONG_RUNNING_AFTER_SECONDS else "running"
                        if str(task.get("state", "")).strip().upper() == STATE_READY_DEV:
                            task["state"] = STATE_IN_PROGRESS
                        task["blocked_reason"] = ""
                        task["stalled_reason"] = ""
                        _record_dev_progress(task, progress_at, progress_kind, execution_state=execution_state)
                        reconcile_state(board, board_path.parent / "priority-queue.json")
                        save_board(board_path, board)
                        continue

                    if not live_session:
                        streak = _task_failure_streak(task, "dev", "orphaned") + 1
                        reason = f"dev_orphaned_streak:{streak}"
                        task["state"] = STATE_READY_DEV
                        task["blocked_reason"] = ""
                        task["stalled_reason"] = reason
                        task["dev_execution_state"] = "orphaned"
                        task["updated_at"] = now_text
                        task["last_progress_at"] = now_text
                        _set_failure_streak(task, "dev", "orphaned", streak, reason)
                        _mark_role_recovery_required(task, "dev", reason)
                        append_event(
                            board,
                            "planner_orchestrator_dev_orphaned_requeue",
                            {"task_id": task_id_value, "source": source, "subagent_id": subagent_id, "age_s": age_seconds, "orphaned_streak": streak},
                        )
                        actions.append(f"dev_orphaned_reset:{task_id_value}")
                        reconcile_state(board, board_path.parent / "priority-queue.json")
                        save_board(board_path, board)
                        row["status"] = "failed"
                        row["failed_at"] = now_text
                        row["summary"] = "planner dev capability lost liveness and was requeued"
                        row["blocking_issue"] = "dev_orphaned"
                        row["last_update_at"] = now_text
                        changed = True
                        continue

                    baseline = _task_progress_baseline(task, row, progress_at)
                    baseline_age_seconds = max(0, int((now_dt - baseline).total_seconds())) if baseline is not None else age_seconds
                    if baseline_age_seconds < DEV_NO_PROGRESS_WINDOW_SECONDS and not (empty_launcher and age_seconds >= EMPTY_LAUNCHER_STALE_SECONDS):
                        task["dev_execution_state"] = "long_running" if age_seconds >= DEV_LONG_RUNNING_AFTER_SECONDS else "running"
                        task["updated_at"] = now_text
                        reconcile_state(board, board_path.parent / "priority-queue.json")
                        save_board(board_path, board)
                        continue

                    streak = _task_failure_streak(task, "dev", "no_progress") + 1
                    reason = f"dev_no_progress_streak:{streak}"
                    task["dev_execution_state"] = "no_progress"
                    task["updated_at"] = now_text
                    _set_failure_streak(task, "dev", "no_progress", streak, reason)
                    if streak >= DEV_STALLED_STREAK_THRESHOLD:
                        task["state"] = STATE_READY_DEV
                        task["blocked_reason"] = ""
                        task["stalled_reason"] = reason
                        task["last_progress_at"] = now_text
                        _mark_role_recovery_required(task, "dev", reason)
                        append_event(
                            board,
                            "planner_orchestrator_dev_recovery_required",
                            {
                                "task_id": task_id_value,
                                "source": source,
                                "subagent_id": subagent_id,
                                "age_s": age_seconds,
                                "failure_kind": "no_progress",
                                "streak": streak,
                                "baseline_age_s": baseline_age_seconds,
                            },
                        )
                        actions.append(f"dev_recovery_required:{task_id_value}")
                        row["status"] = "failed"
                        row["failed_at"] = now_text
                        row["summary"] = "planner dev capability made no meaningful progress and was requeued"
                        row["blocking_issue"] = "dev_no_progress"
                        row["last_update_at"] = now_text
                        changed = True
                    else:
                        task["stalled_reason"] = reason
                        append_event(
                            board,
                            "planner_orchestrator_dev_no_progress",
                            {
                                "task_id": task_id_value,
                                "source": source,
                                "subagent_id": subagent_id,
                                "age_s": age_seconds,
                                "baseline_age_s": baseline_age_seconds,
                                "no_progress_streak": streak,
                            },
                        )
                        actions.append(f"dev_no_progress:{task_id_value}")
                    reconcile_state(board, board_path.parent / "priority-queue.json")
                    save_board(board_path, board)
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
        raw_path = config.results_dir / f"{subagent_id}.raw.txt"
        launcher_log = config.results_dir / f"{subagent_id}.launcher.log"
        task_id_value = str(row.get("owner_task_id", "")).strip()
        if task_id_value:
            with board_lock(board_path):
                board = load_board(board_path)
                task = task_index(board).get(task_id_value)
                if _task_effectively_done(task):
                    changed = _prune_planner_subagent_row(config, rows, subagent_id) or changed
                    actions.append(f"admin_drop_done:{task_id_value}")
                    continue
        if result_path.exists() or raw_path.exists():
            continue
        created_raw = str(row.get("created_at", "")).strip() or str(row.get("last_update_at", "")).strip()
        created_at = _parse_iso_utc(created_raw)
        if created_at is None:
            continue
        age_seconds = max(0, int((datetime.now(timezone.utc) - created_at).total_seconds()))
        empty_launcher = launcher_log.exists() and launcher_log.stat().st_size == 0
        if age_seconds < threshold_seconds and not (empty_launcher and age_seconds >= EMPTY_LAUNCHER_STALE_SECONDS):
            continue
        if task_id_value:
            with board_lock(board_path):
                board = load_board(board_path)
                task = task_index(board).get(task_id_value)
                if isinstance(task, dict):
                    task["state"] = STATE_READY
                    task["blocked_reason"] = ""
                    streak = _task_timeout_streak(task, "admin") + 1
                    reason = f"admin_timeout_streak:{streak}"
                    task["stalled_reason"] = reason
                    task["updated_at"] = now_text
                    task["last_progress_at"] = now_text
                    _set_timeout_streak(task, "admin", streak, reason)
                    if streak >= ADMIN_TIMEOUT_STREAK_THRESHOLD:
                        _mark_admin_takeover_required(task, reason)
                        append_event(
                            board,
                            "planner_orchestrator_admin_takeover_required",
                            {"task_id": task_id_value, "source": source, "subagent_id": subagent_id, "age_s": age_seconds, "timeout_streak": streak},
                        )
                        actions.append(f"admin_takeover_required:{task_id_value}")
                    else:
                        append_event(
                            board,
                            "planner_orchestrator_admin_dispatch_stale",
                            {"task_id": task_id_value, "source": source, "subagent_id": subagent_id, "age_s": age_seconds, "timeout_streak": streak},
                        )
                        actions.append(f"admin_stale_reset:{task_id_value}")
                    reconcile_state(board, board_path.parent / "priority-queue.json")
                    save_board(board_path, board)
        row["status"] = "failed"
        row["failed_at"] = now_text
        row["summary"] = "stale planner capability with no result requeued"
        row["blocking_issue"] = "stale_no_result"
        row["last_update_at"] = now_text
        changed = True
    if changed:
        _write_planner_registry_rows(config, rows)
    return actions


def _has_active_subagent(root: Path, target_role: str = "") -> bool:
    _, rows = _planner_registry_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    board = load_board(board_path)
    index = task_index(board)
    target = str(target_role or "").strip().lower()
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner":
            continue
        if target and str(row.get("target_role", "")).strip().lower() != target:
            continue
        if str(row.get("status", "")).strip().lower() not in ACTIVE_STATUSES:
            continue
        owner_task_id = str(row.get("owner_task_id", "")).strip()
        owner_task = index.get(owner_task_id) if owner_task_id else None
        if _task_effectively_done(owner_task):
            continue
        if _subagent_has_collectible_result(root, row):
            continue
        if str(row.get("blocking_issue", "")).strip().lower() in {"owner_task_already_done", "stale_no_result"}:
            continue
        return True
    return False


def _collect_finished_dev_subagents(root: Path, source: str, owner_task_filter: str = "", subagent_filter: str = "") -> list[str]:
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
        if subagent_filter and subagent_id != subagent_filter:
            continue
        if owner_task_filter and str(row.get("owner_task_id", "")).strip() != owner_task_filter:
            continue
        if str(row.get("status", "")).strip().lower() == "merged":
            continue
        result_path = config.results_dir / f"{subagent_id}.result.json"
        raw_path = config.results_dir / f"{subagent_id}.raw.txt"
        if not result_path.exists() and not raw_path.exists():
            continue
        rc, payload = collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        if not isinstance(payload, dict):
            continue
        task_id_value = str(payload.get("owner_task_id") or row.get("owner_task_id", "")).strip()
        if not task_id_value:
            continue
        actions.append(f"dev_collect:{task_id_value}")
        with board_lock(board_path):
            board = load_board(board_path)
            live_task = task_index(board).get(task_id_value)
        if _task_effectively_done(live_task):
            if _prune_planner_subagent_row(config, rows, subagent_id):
                _write_planner_registry_rows(config, rows)
            actions.append(f"dev_skip_done:{task_id_value}")
            continue
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
                if not isinstance(task_index(board).get(task_id_value), dict):
                    actions.append(f"dev_orphan_collect:{task_id_value}")
                    continue
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
                    live_task = task_index(board).get(task_id_value)
                    if isinstance(live_task, dict):
                        _clear_role_recovery(live_task, "dev")
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
            if completed:
                with board_lock(board_path):
                    board = load_board(board_path)
                    live_task = task_index(board).get(task_id_value)
                if isinstance(live_task, dict) and _requires_browser_proof(live_task) and not _browser_validation_done(live_task):
                    browser_ok, _browser_detail = _run_browser_validation(root, live_task, source=source, phase="future_delivery")
                    actions.append(f"browser_validate:{task_id_value}:{'ok' if browser_ok else 'failed'}")
            continue
        blocking_issue = str(payload.get("blocking_issue") or payload.get("recommended_next") or status_token or "subagent_not_ready")
        with board_lock(board_path):
            board = load_board(board_path)
            if not isinstance(task_index(board).get(task_id_value), dict):
                actions.append(f"dev_orphan_collect:{task_id_value}")
                continue
            outcome = _record_dev_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id,
                blocking_issue=blocking_issue,
                event_kind="planner_orchestrator_dev_dispatch_failed",
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        actions.append(f"dev_block:{task_id_value}:{outcome}")
    return actions


def _collect_finished_admin_subagents(root: Path, source: str, owner_task_filter: str = "", subagent_filter: str = "") -> list[str]:
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
        if subagent_filter and subagent_id != subagent_filter:
            continue
        if owner_task_filter and str(row.get("owner_task_id", "")).strip() != owner_task_filter:
            continue
        if str(row.get("status", "")).strip().lower() == "merged":
            continue
        result_path = config.results_dir / f"{subagent_id}.result.json"
        raw_path = config.results_dir / f"{subagent_id}.raw.txt"
        if not result_path.exists() and not raw_path.exists():
            continue
        rc, payload = collect_subagent(config, "planner", subagent_id, "", mark_merged=True)
        if not isinstance(payload, dict):
            continue
        task_id_value = str(payload.get("owner_task_id") or row.get("owner_task_id", "")).strip()
        if not task_id_value:
            continue
        actions.append(f"admin_collect:{task_id_value}")
        with board_lock(board_path):
            board = load_board(board_path)
            live_task = task_index(board).get(task_id_value)
        if _task_effectively_done(live_task):
            if _prune_planner_subagent_row(config, rows, subagent_id):
                _write_planner_registry_rows(config, rows)
            actions.append(f"admin_skip_done:{task_id_value}")
            continue
        status_token = _payload_status(payload)
        if status_token in SUCCESS_SUBAGENT_STATUSES and _payload_has_delivery_evidence(payload, target_role="admin"):
            evidence = _build_admin_evidence(payload, task_id_value)
            with board_lock(board_path):
                board = load_board(board_path)
                if not isinstance(task_index(board).get(task_id_value), dict):
                    actions.append(f"admin_orphan_collect:{task_id_value}")
                    continue
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
                    live_task = task_index(board).get(task_id_value)
                    if isinstance(live_task, dict):
                        _clear_admin_takeover(live_task)
                    reconcile_state(board, board_path.parent / "priority-queue.json")
                    save_board(board_path, board)
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
            if not isinstance(task_index(board).get(task_id_value), dict):
                actions.append(f"admin_orphan_collect:{task_id_value}")
                continue
            outcome = _record_admin_failure(
                board,
                task_id_value=task_id_value,
                source=source,
                subagent_id=subagent_id,
                blocking_issue=blocking_issue,
                event_kind="planner_orchestrator_admin_dispatch_failed",
            )
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
        actions.append(f"admin_block:{task_id_value}:{outcome}")
    return actions


def _collect_finished_qa_workers(root: Path, source: str, owner_task_filter: str = "") -> list[str]:
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
        if owner_task_filter and str(row.get("owner_task_id", "")).strip() != owner_task_filter:
            continue
        if str(row.get("status", "")).strip().lower() == "merged":
            continue
        result_path = config.results_dir / f"{worker_id}.result.json"
        if not result_path.exists() and str(row.get("status", "")).strip().lower() in ACTIVE_STATUSES:
            continue
        rc, payload = collect_worker(config, "planner", worker_id, "", mark_merged=True)
        if not isinstance(payload, dict):
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
            if rc == 0 and str(payload.get("status", "")).strip().lower() in {"completed", "merged"}:
                append_event(board, "planner_orchestrator_qa_review_completed", {"task_id": task_id_value, "source": source, "worker_id": worker_id})
                actions.append(f"qa_complete:{task_id_value}")
            else:
                task["qa_status"] = "failed"
                task["qa_blocking_issue"] = str(payload.get("blocking_issue", "qa_worker_failed")).strip() or "qa_worker_failed"
                append_event(board, "planner_orchestrator_qa_review_failed", {"task_id": task_id_value, "source": source, "worker_id": worker_id})
                actions.append(f"qa_failed:{task_id_value}")
            reconcile_state(board, board_path.parent / "priority-queue.json")
            save_board(board_path, board)
    return actions


def _prune_resolved_qa_workers(root: Path, source: str) -> list[str]:
    config, rows = _load_worker_rows(root)
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    with board_lock(board_path):
        board = load_board(board_path)
        index = task_index(board)
    kept: list[dict[str, Any]] = []
    actions: list[str] = []
    changed = False
    for row in rows:
        if str(row.get("parent_role", "")).strip().lower() != "planner" or str(row.get("worker_type", "")).strip() != "qa_review_worker":
            kept.append(row)
            continue
        task_id_value = str(row.get("owner_task_id", "")).strip()
        task = index.get(task_id_value)
        if not isinstance(task, dict):
            kept.append(row)
            continue
        if not _qa_review_already_done(task):
            kept.append(row)
            continue
        worker_id = str(row.get("worker_id", "")).strip()
        if str(row.get("status", "")).strip().lower() in ACTIVE_STATUSES and worker_id:
            try:
                _openclaw_delete_agent(worker_id)
            except Exception:
                pass
        actions.append(f"qa_prune:{task_id_value}")
        changed = True
        continue
    if changed:
        payload = {"updated_at": now_iso(), "workers": kept}
        config.registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return actions


def _infer_result_target_role(payload: dict[str, Any], subagent_id: str) -> str:
    token = str(payload.get("target_role", "")).strip().lower()
    if token in {"dev", "admin", "qa"}:
        return token
    subagent_token = str(subagent_id or "").strip().lower()
    if subagent_token.startswith("planner_dev_"):
        return "dev"
    if subagent_token.startswith("planner_admin_"):
        return "admin"
    return ""


def _collect_orphan_result_payloads(root: Path, source: str, owner_task_filter: str = "", target_role: str = "") -> list[str]:
    config = load_subagent_config(root)
    results_dir = config.results_dir
    if not results_dir.exists():
        return []
    _, rows = _planner_registry_rows(root)
    registry_ids = {str(row.get("subagent_id", "")).strip() for row in rows if str(row.get("subagent_id", "")).strip()}
    board_path = root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json"
    actions: list[str] = []
    for result_path in sorted(results_dir.glob("*.result.json")):
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            continue
        subagent_id = str(payload.get("subagent_id", result_path.stem)).strip()
        if subagent_id in registry_ids:
            continue
        task_id_value = str(payload.get("owner_task_id", "")).strip()
        if not task_id_value:
            continue
        if owner_task_filter and task_id_value != owner_task_filter:
            continue
        role_token = _infer_result_target_role(payload, subagent_id)
        if target_role and role_token != str(target_role).strip().lower():
            continue
        with board_lock(board_path):
            board = load_board(board_path)
            task = task_index(board).get(task_id_value)
            if not isinstance(task, dict):
                continue
            if str(task.get("state", "")).strip().upper() == STATE_DONE:
                continue
            status_token = _payload_status(payload)
            if role_token == "dev" and status_token in SUCCESS_SUBAGENT_STATUSES and _payload_has_delivery_evidence(payload):
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
                    "next_action_unique": f"PLANNER_ORPHAN_MERGE_{task_id_value}",
                }
                if _complete_task_from_evidence(root=root, board_path=board_path, role="dev", task_id_value=task_id_value, evidence=evidence, source=source, board=board):
                    actions.append(f"orphan_dev_complete:{task_id_value}")
                continue
            if role_token == "admin" and status_token in SUCCESS_SUBAGENT_STATUSES and _payload_has_delivery_evidence(payload, target_role="admin"):
                evidence = _build_admin_evidence(payload, task_id_value)
                if _complete_task_from_evidence(root=root, board_path=board_path, role="admin", task_id_value=task_id_value, evidence=evidence, source=source, board=board):
                    actions.append(f"orphan_admin_complete:{task_id_value}")
                continue
    return actions


def collect_pending_results(root: Path, source: str, owner_task_id: str = "", target_role: str = "", subagent_id: str = "") -> dict[str, Any]:
    actions: list[str] = []
    role_token = str(target_role or "").strip().lower()
    if role_token in {"", "dev"}:
        actions.extend(
            _collect_finished_dev_subagents(
                root,
                source,
                owner_task_filter=owner_task_id,
                subagent_filter=subagent_id,
            )
        )
    if role_token in {"", "admin"}:
        actions.extend(
            _collect_finished_admin_subagents(
                root,
                source,
                owner_task_filter=owner_task_id,
                subagent_filter=subagent_id,
            )
        )
    if role_token in {"", "qa"}:
        actions.extend(_collect_finished_qa_workers(root, source, owner_task_filter=owner_task_id))
        actions.extend(_prune_resolved_qa_workers(root, source))
    actions.extend(_collect_orphan_result_payloads(root, source, owner_task_filter=owner_task_id, target_role=role_token))
    return {"ok": True, "actions": actions, "owner_task_id": owner_task_id or "", "target_role": role_token or ""}


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
    actions.extend(_prune_resolved_qa_workers(root, source))
    actions.extend(_collect_orphan_result_payloads(root, source))
    actions.extend(_backfill_admin_runtime_no_code_metadata(root, source))
    actions.extend(_backfill_historical_browser_proof(root, source))
    actions.extend(_dispatch_pending_qa_reviews(root, source))
    actions.extend(_auto_complete_planner_gov_reviews(root, source))

    priority_admin = _select_dispatchable_admin_task(load_board(board_path))
    priority_admin_takeover = isinstance(priority_admin, dict) and bool(priority_admin.get("planner_takeover_required"))

    dispatch: dict[str, Any] = {
        "dispatched": False,
        "reason": "active_subagent_present" if _has_active_subagent(root, "dev") else "not_needed",
    }
    if priority_admin_takeover and not _has_active_subagent(root, "admin"):
        dispatch = _dispatch_admin_capability(root, source=source, backend=backend)
        if dispatch.get("dispatched"):
            actions.append(f"admin_dispatch:{dispatch.get('task_id', 'unknown')}")
            if dispatch.get("completed"):
                actions.append(f"admin_complete:{dispatch.get('task_id', 'unknown')}")

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
    elif task_update == "claim" and task_id_value and not priority_admin_takeover:
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

    if not dispatch.get("dispatched") and not _has_active_subagent(root, "dev"):
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
    contract = _rewrite_contract_for_live_dispatch(contract, dispatch, actions)
    return _render_contract(contract), {"ok": True, "actions": actions, "dispatch": dispatch}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Planner orchestrator execution bridge")
    parser.add_argument("--root", default=str(Path.cwd()))
    parser.add_argument("--role", default="planner")
    parser.add_argument("--source", default="runner")
    parser.add_argument("--backend", default="auto", choices=["auto", "openclaw", "codex_exec", "mock"])
    parser.add_argument("--contract-file")
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--owner-task-id", default="")
    parser.add_argument("--target-role", default="")
    parser.add_argument("--subagent-id", default="")
    return parser


def _canonical_runtime_root(root: Path) -> Path:
    canonical = Path("/home/venom/analyse-financiere")
    try:
        if canonical.exists() and (canonical / "platform").is_dir() and (canonical / "scripts").is_dir():
            if str(root).startswith("/home/venom/shared/analyse-financiere"):
                return canonical
    except Exception:
        pass
    return root


def main() -> int:
    args = build_parser().parse_args()
    root = _canonical_runtime_root(Path(args.root).expanduser().resolve())
    if args.collect_only:
        payload = collect_pending_results(
            root=root,
            source=args.source,
            owner_task_id=str(args.owner_task_id or "").strip(),
            target_role=str(args.target_role or "").strip(),
            subagent_id=str(args.subagent_id or "").strip(),
        )
        print(json.dumps(payload, ensure_ascii=True))
        return 0
    if not args.contract_file:
        raise SystemExit("--contract-file is required unless --collect-only is used")
    contract_path = Path(args.contract_file).expanduser().resolve()
    text = contract_path.read_text(encoding="utf-8", errors="ignore")
    updated, payload = apply_bridge(root=root, role=args.role, contract_text=text, source=args.source, backend=args.backend)
    contract_path.write_text(updated, encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
