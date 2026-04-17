#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import which as shutil_which
from typing import Any
import yaml

from orchestrator_paths import (
    CANONICAL_VM_ROOT,
    SHARED_VM_ROOT,
    canonical_docs_root,
    resolve_orchestrator_read_path,
    resolve_orchestrator_write_path,
    runtime_state_root,
)
from runtime.core.contracts import CapabilityResult, CapabilityTask, DeliveryProof
from runtime.model_plane import active_rate_limit_reason as model_plane_active_rate_limit_reason
from runtime.model_plane import looks_like_rate_limited as model_plane_looks_like_rate_limited
from runtime.model_plane import resolve_effective_backend_details as model_plane_resolve_effective_backend_details
from runtime.model_plane import run_qwen_cli_fallback as model_plane_run_qwen_cli_fallback
from runtime.model_plane import run_secondary_then_qwen_fallback as model_plane_run_secondary_then_qwen_fallback
from runtime.planner.planner_graph_runtime import PlannerGraphRuntime
from runtime.truth.dispatch_snapshot import build_stable_planner_dispatch_snapshot
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot
from runtime.model_plane.model_plane import resolve_planner_backend_choice as model_plane_resolve_planner_backend_choice
from runtime.model_plane.model_plane import validate_planner_dispatch_backend as model_plane_validate_planner_dispatch_backend
from compat.legacy_workers.worker_manager import _openclaw_env


ACTIVE_STATUSES = {"spawned", "running"}
FINISHED_STATUSES = {"completed", "failed", "merged"}
SUCCESS_RESULT_STATUSES = {"complete", "completed", "done", "pass", "ok", "success", "merged"}
SUCCESS_OUTPUT_STATUSES = {"complete", "completed", "done", "pass", "ok", "success"}
BLOCKED_RESULT_STATUSES = {"blocked"}
RETRYABLE_BACKEND_FAILURE_MARKERS = {
    "invalid_subagent_result:start_banner_only",
    "invalid_subagent_result:structured_output_missing",
    "invalid_subagent_result:output_schema_missing",
}
RETRYABLE_BACKEND_FAILURE_COOLDOWN_SECONDS = max(
    60,
    int(os.environ.get("FC_PLANNER_RETRYABLE_FAILURE_COOLDOWN_SECONDS", "300") or "300"),
)
ALLOWED_PARENT_ROLES = {"planner"}
DEFAULT_MANAGED_ROLES = ("dev", "admin", "scrum_master")
CODEX_STARTUP_NOISE_MARKERS = (
    "openai codex v",
    "research preview",
    "approval: never",
    "sandbox: danger-full-access",
    "sandbox: workspace-write",
    "reasoning effort:",
    "session id:",
    "provider: openai",
    "failed to refresh available models",
    "missing bearer or basic authentication",
    "401 unauthorized",
    "unexpected status 401 unauthorized",
    "transport channel",
    "worker quit with fatal",
    "reconnecting...",
)
SECONDARY_CODEX_DEFAULT_MODEL = "gpt-5.4"
SECONDARY_CODEX_DEFAULT_THINKING = "high"
CANONICAL_RUNTIME_WORKSPACE = Path("/home/venom/analyse-financiere")
ROLE_MODELS = {
    "dev": ("codex-full/gpt-5.4", "high", "danger-full-access"),
    "admin": ("codex-full/gpt-5.4", "high", "danger-full-access"),
    "scrum_master": ("codex-full/gpt-5.4", "high", "danger-full-access"),
}
ROLE_TASK_KINDS = {
    "dev": {"delivery", "implementation", "verification", "targeted_fix"},
    "admin": {"runtime", "reconcile", "takeover", "repair"},
    "scrum_master": {"flow", "coordination", "unblock", "starvation"},
}
STATUS_RANK = {
    "spawned": 1,
    "running": 2,
    "blocked": 3,
    "failed": 3,
    "completed": 3,
    "done": 3,
    "pass": 3,
    "ok": 3,
    "success": 3,
    "merged": 4,
}
EMPTY_FIELD_TOKENS = {"", "none", "n/a", "na", "null", "unknown"}
NON_MEANINGFUL_DELTA_TOKENS = {
    "",
    "none",
    "null",
    "unknown",
    "no_delta",
    "heartbeat",
    "heartbeat_only",
    "monitor_updates",
    "noop",
}
RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "summary",
        "root_cause",
        "fix_applied",
        "artifact",
        "verify",
        "files_touched",
        "tests_run",
        "commit_sha",
        "architecture_check",
        "vision_alignment",
        "recommended_next",
        "blocking_issue",
    ],
    "properties": {
        "status": {"type": "string"},
        "summary": {"type": "string"},
        "root_cause": {"type": "string"},
        "fix_applied": {"type": "string"},
        "artifact": {"type": "string"},
        "verify": {"type": "string"},
        "files_touched": {"type": "string"},
        "tests_run": {"type": "string"},
        "commit_sha": {"type": "string"},
        "architecture_check": {"type": "string"},
        "vision_alignment": {"type": "string"},
        "recommended_next": {"type": "string"},
        "blocking_issue": {"type": "string"},
    },
}


def canonical_role(value: Any) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if token in {"po_scrum_master", "scrum"}:
        return "scrum_master"
    return token


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _compact(text: Any, limit: int = 180) -> str:
    value = " ".join(str(text or "").split())
    if not value:
        return "none"
    return value[:limit]


def _value_present(value: Any) -> bool:
    token = str(value or "").strip().lower()
    if not token or token in {"none", "n/a", "na", "null", "unknown"}:
        return False
    if _looks_like_placeholder_only_value(token):
        return False
    return True


def _looks_like_placeholder_only_value(value: Any) -> bool:
    token = " ".join(str(value or "").strip().split()).lower()
    if not token:
        return True
    if token in {"...", "..", ".", "…", "?", "??", "tbd"}:
        return True
    if re.fullmatch(r"(?:[a-z_]+=\.\.\.)(?:\s*;\s*[a-z_]+=\.\.\.)*", token):
        return True
    return False


def _meaningful_issue(value: Any) -> str:
    token = " ".join(str(value or "").strip().split())
    if not token:
        return ""
    if token.lower() in EMPTY_FIELD_TOKENS:
        return ""
    return token


def _looks_like_startup_noise(text: Any) -> bool:
    token = " ".join(str(text or "").strip().lower().split())
    if not token:
        return True
    return any(marker in token for marker in CODEX_STARTUP_NOISE_MARKERS)


def _normalized_retryable_backend_issue(text: Any) -> str:
    token = " ".join(str(text or "").strip().split())
    if not token:
        return "invalid_subagent_result:structured_output_missing"
    if _looks_like_rate_limited(token):
        cached_reason = _active_rate_limit_reason(("codex", "global"))
        return cached_reason or _compact(token, 160)
    if _looks_like_startup_noise(token):
        return "invalid_subagent_result:start_banner_only"
    return "invalid_subagent_result:structured_output_missing"


def _semantic_result_gate(payload: dict[str, Any]) -> tuple[bool, str]:
    semantic_success = _payload_semantic_success(payload)
    status = str(payload.get("status", "")).strip().lower()
    summary = str(payload.get("summary", "")).strip()
    blocking_issue = str(payload.get("blocking_issue", "")).strip().lower()
    proof_fields = (
        payload.get("artifact"),
        payload.get("verify"),
        payload.get("files_touched"),
        payload.get("recommended_next"),
        payload.get("root_cause"),
        payload.get("fix_applied"),
        payload.get("tests_run"),
        payload.get("commit_sha"),
    )
    has_structured_signal = any(_value_present(value) for value in proof_fields)
    if status not in SUCCESS_OUTPUT_STATUSES:
        if semantic_success:
            return True, "none"
        return False, blocking_issue or f"subagent_status_{status or 'unknown'}"
    if not has_structured_signal and _looks_like_startup_noise(summary):
        return False, "invalid_subagent_result:start_banner_only"
    if not has_structured_signal and not _value_present(summary):
        return False, "invalid_subagent_result:empty_payload"
    return True, "none"


def _payload_semantic_success(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status", "")).strip().lower()
    if status in SUCCESS_OUTPUT_STATUSES:
        return True
    blocking_issue = str(payload.get("blocking_issue", "")).strip().lower()
    if _looks_like_startup_noise(blocking_issue):
        blocking_issue = ""
    strong_success_signal = all(
        _value_present(payload.get(key))
        for key in ("artifact", "verify", "tests_run")
    )
    return strong_success_signal and blocking_issue in {"", "none"}


def _subprocess_timeout_value(timeout_seconds: int) -> int | None:
    try:
        token = int(timeout_seconds)
    except Exception:
        token = 0
    if token <= 0:
        return None
    return max(30, token)


def _looks_like_rate_limited(text: str) -> bool:
    return model_plane_looks_like_rate_limited(text)


INVALID_RESULT_PREFIX = "invalid_subagent_result:"
INVALID_RESULT_THRESHOLD = max(1, int(os.environ.get("FC_PLANNER_INVALID_RESULT_THRESHOLD", "3") or 3))
INVALID_RESULT_WINDOW_SECONDS = max(60, int(os.environ.get("FC_PLANNER_INVALID_RESULT_WINDOW_SECONDS", str(15 * 60)) or (15 * 60)))
INVALID_RESULT_COOLDOWN_SECONDS = max(60, int(os.environ.get("FC_PLANNER_INVALID_RESULT_COOLDOWN_SECONDS", str(30 * 60)) or (30 * 60)))


def _active_rate_limit_reason(prefixes: tuple[str, ...]) -> str:
    if os.environ.get("PYTEST_CURRENT_TEST") or "unittest" in sys.modules:
        return ""
    return _compact(model_plane_active_rate_limit_reason(prefixes, os.environ, int(_now().timestamp())), 220)


def _running_under_tests() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or "unittest" in sys.modules)


def _allow_runtime_rate_limit_cache(config: PlannerSubagentConfig) -> bool:
    return True


def _invalid_result_route_path(config: PlannerSubagentConfig) -> Path:
    state_root = _canonical_runtime_root(config.root)
    state_root.mkdir(parents=True, exist_ok=True)
    return state_root / "planner-invalid-result-routes.json"


def _parse_iso_dt(value: Any) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        return datetime.fromisoformat(token.replace("Z", "+00:00"))
    except Exception:
        return None


def _load_invalid_result_routes(path: Path) -> dict[str, Any]:
    payload = _read_structured(path, {"version": 1, "routes": {}})
    if not isinstance(payload, dict):
        payload = {"version": 1, "routes": {}}
    if not isinstance(payload.get("routes", {}), dict):
        payload["routes"] = {}
    return payload


def _save_invalid_result_routes(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _invalid_result_route_key(owner_task_id: str, target_role: str) -> str:
    return f"{canonical_role(target_role)}::{str(owner_task_id or '').strip()}"


def _is_invalid_result_reason(value: Any) -> bool:
    return str(value or "").strip().lower().startswith(INVALID_RESULT_PREFIX)


def _active_invalid_result_routes(config: PlannerSubagentConfig) -> list[dict[str, Any]]:
    path = _invalid_result_route_path(config)
    payload = _load_invalid_result_routes(path)
    routes = payload.get("routes", {})
    now = _now()
    active: list[dict[str, Any]] = []
    dirty = False
    for key, entry in list(routes.items()):
        if not isinstance(entry, dict):
            routes.pop(key, None)
            dirty = True
            continue
        cooldown_until = _parse_iso_dt(entry.get("cooldown_until"))
        if cooldown_until is None or cooldown_until <= now:
            routes.pop(key, None)
            dirty = True
            continue
        current = dict(entry)
        current["key"] = key
        active.append(current)
    if dirty:
        _save_invalid_result_routes(path, payload)
    active.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
    return active


def _recent_invalid_result_records(
    records: list["PlannerSubagentRecord"],
    owner_task_id: str,
    target_role: str,
) -> list["PlannerSubagentRecord"]:
    cutoff = _now() - timedelta(seconds=INVALID_RESULT_WINDOW_SECONDS)
    matches: list[PlannerSubagentRecord] = []
    role_token = canonical_role(target_role)
    task_token = str(owner_task_id or "").strip()
    for record in records:
        if str(record.owner_task_id or "").strip() != task_token:
            continue
        if canonical_role(record.target_role) != role_token:
            continue
        if not _is_invalid_result_reason(record.blocking_issue):
            continue
        stamp = _parse_iso_dt(record.last_update_at) or _parse_iso_dt(record.created_at)
        if stamp is None or stamp < cutoff:
            continue
        matches.append(record)
    matches.sort(key=_record_sort_stamp, reverse=True)
    return matches


def _current_invalid_result_route(
    config: PlannerSubagentConfig,
    records: list["PlannerSubagentRecord"],
    owner_task_id: str,
    target_role: str,
    current_failure_reason: str = "",
) -> dict[str, Any]:
    task_token = str(owner_task_id or "").strip()
    role_token = canonical_role(target_role)
    if not task_token or not role_token:
        return {}
    path = _invalid_result_route_path(config)
    payload = _load_invalid_result_routes(path)
    routes = payload.get("routes", {})
    now = _now()
    key = _invalid_result_route_key(task_token, role_token)
    existing = routes.get(key, {})
    if isinstance(existing, dict):
        cooldown_until = _parse_iso_dt(existing.get("cooldown_until"))
        if cooldown_until is not None and cooldown_until > now:
            active = dict(existing)
            active["key"] = key
            return active
    if key in routes:
        routes.pop(key, None)
        _save_invalid_result_routes(path, payload)
    recent = _recent_invalid_result_records(records, task_token, role_token)
    current_invalid = _is_invalid_result_reason(current_failure_reason)
    merged_retry_compensation = 1 if current_invalid and recent else 0
    recent_count = len(recent) + (1 if current_invalid else 0) + merged_retry_compensation
    if recent_count < INVALID_RESULT_THRESHOLD:
        return {}
    latest_reason = str(current_failure_reason or (recent[0].blocking_issue if recent else INVALID_RESULT_PREFIX + "threshold")).strip()
    entry = {
        "owner_task_id": task_token,
        "target_role": role_token,
        "route_reason": "invalid_result_burst",
        "backend": "qwen",
        "failure_count": recent_count,
        "last_reason": latest_reason,
        "updated_at": _iso(now),
        "cooldown_until": _iso(now + timedelta(seconds=INVALID_RESULT_COOLDOWN_SECONDS)),
    }
    routes[key] = entry
    _save_invalid_result_routes(path, payload)
    active = dict(entry)
    active["key"] = key
    return active


def _clear_invalid_result_route(config: PlannerSubagentConfig, owner_task_id: str, target_role: str) -> None:
    task_token = str(owner_task_id or "").strip()
    role_token = canonical_role(target_role)
    if not task_token or not role_token:
        return
    path = _invalid_result_route_path(config)
    payload = _load_invalid_result_routes(path)
    routes = payload.get("routes", {})
    key = _invalid_result_route_key(task_token, role_token)
    if key in routes:
        routes.pop(key, None)
        _save_invalid_result_routes(path, payload)


def _result_schema_score(payload: dict[str, Any]) -> tuple[int, int, int, int]:
    schema_keys = tuple(RESULT_SCHEMA.get("required", []) or ())
    present_count = sum(1 for key in schema_keys if key in payload)
    meaningful_count = sum(1 for key in schema_keys if _value_present(payload.get(key)))
    has_status = 1 if _value_present(payload.get("status")) else 0
    try:
        encoded_len = len(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    except Exception:
        encoded_len = 0
    return has_status, present_count, meaningful_count, encoded_len


def _extract_first_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        payload, _ = json.JSONDecoder().raw_decode(raw)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _extract_last_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    direct = _extract_first_json_object(raw)
    candidates: list[dict[str, Any]] = [direct] if direct else []
    decoder = json.JSONDecoder()
    for idx, char in enumerate(raw):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw[idx:])
        except Exception:
            continue
        if isinstance(payload, dict):
            candidates.append(payload)
    if not candidates:
        return {}
    candidates.sort(key=_result_schema_score, reverse=True)
    return candidates[0]


def _stringify_result_atom(value: Any, *, limit: int = 120) -> str:
    if isinstance(value, dict):
        try:
            return _compact(json.dumps(value, ensure_ascii=True, sort_keys=True), limit)
        except Exception:
            return _compact(str(value), limit)
    if isinstance(value, list):
        parts = [_stringify_result_atom(item, limit=80) for item in value]
        parts = [part for part in parts if _value_present(part)]
        return _compact(" | ".join(parts), limit) if parts else ""
    token = " ".join(str(value or "").split())
    return _compact(token, limit) if token else ""


def _normalize_result_field(value: Any, *, fallback: str, limit: int, field: str) -> str:
    if isinstance(value, dict):
        if field in {"artifact", "verify", "architecture_check", "vision_alignment"}:
            parts = []
            for key, item in value.items():
                rendered = _stringify_result_atom(item, limit=120)
                if _value_present(rendered):
                    parts.append(f"{key}={rendered}")
            if parts:
                return _compact("; ".join(parts), limit)
        rendered = _stringify_result_atom(value, limit=limit)
        return rendered if _value_present(rendered) else fallback
    if isinstance(value, list):
        joiner = ", " if field == "files_touched" else " | "
        parts = [_stringify_result_atom(item, limit=120) for item in value]
        parts = [part for part in parts if _value_present(part)]
        if parts:
            return _compact(joiner.join(parts), limit)
        return fallback
    token = _compact(value, limit)
    return token if _value_present(token) else fallback


def _payload_needs_raw_recovery(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status", "")).strip().lower()
    if status not in {"failed", "blocked"}:
        return False
    blocking_issue = _meaningful_issue(payload.get("blocking_issue"))
    summary = " ".join(str(payload.get("summary", "")).split()).strip().lower()
    if blocking_issue.startswith("invalid_subagent_result:"):
        return True
    if blocking_issue:
        return False
    tests_run = str(payload.get("tests_run", "")).strip().lower()
    has_evidence = any(
        _value_present(value)
        for value in (
            payload.get("root_cause"),
            payload.get("fix_applied"),
            payload.get("artifact"),
            payload.get("verify"),
            payload.get("files_touched"),
            payload.get("commit_sha"),
            payload.get("architecture_check"),
            payload.get("vision_alignment"),
            payload.get("recommended_next"),
        )
    )
    if not has_evidence and tests_run not in {"", "none", "n/a", "na", "null", "unknown", "skip(no_tests)", "skip(no_code_runtime_fix)", "skip(no_result_payload)"}:
        has_evidence = True
    return not has_evidence or summary in {"", "none", "failed"} or not _value_present(summary)


def _payload_signal_score(payload: dict[str, Any]) -> tuple[int, int, int]:
    status_ok = 1 if _value_present(payload.get("status")) else 0
    evidence_count = sum(
        1
        for key in (
            "summary",
            "root_cause",
            "fix_applied",
            "artifact",
            "verify",
            "files_touched",
            "tests_run",
            "commit_sha",
            "architecture_check",
            "vision_alignment",
            "recommended_next",
        )
        if _value_present(payload.get(key))
    )
    issue_ok = 1 if _meaningful_issue(payload.get("blocking_issue")) else 0
    return status_ok, evidence_count, issue_ok


def _recover_payload_from_raw_output(
    raw_text: str,
    *,
    subagent_id: str,
    target_role: str,
    owner_task_id: str,
    parent_role: str,
    task_kind: str,
    backend: str,
) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        return {}
    result_source = text
    if str(backend or "").strip().lower() == "openclaw":
        wrapper = _extract_first_json_object(text)
        if wrapper:
            extracted_text, _ = _extract_openclaw_payload_text(json.dumps(wrapper, ensure_ascii=True))
            if extracted_text:
                result_source = extracted_text
    recovered = _parse_result_payload(
        result_source,
        subagent_id,
        target_role,
        owner_task_id,
        parent_role,
        task_kind,
        backend,
    ).as_dict()
    return recovered if isinstance(recovered, dict) else {}


def _canonical_runtime_mirror_path(path: Path) -> Path | None:
    marker = f"{os.sep}logs-codex-runs{os.sep}orchestrator-state{os.sep}"
    raw = str(path)
    if marker not in raw:
        return None
    prefix, suffix = raw.split(marker, 1)
    root = Path(prefix)
    return canonical_docs_root(root) / suffix


def _load_structured_output(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    payload = _extract_last_json_object(raw)
    if not payload or not str(payload.get("status", "")).strip():
        return ""
    return json.dumps(payload, ensure_ascii=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _read_structured(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(text)
            if payload not in (None, {}) or not text.strip():
                return payload if payload is not None else default
            return json.loads(text)
        return json.loads(text)
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _codex_available() -> bool:
    from shutil import which

    return bool(which("codex"))


def _openclaw_available() -> bool:
    return bool(shutil_which("openclaw"))


def _openclaw_agent_ids() -> set[str]:
    if not _openclaw_available():
        return set()
    try:
        proc = subprocess.run(
            ["openclaw", "agents", "list", "--json"],
            text=True,
            capture_output=True,
            check=False,
            env=_openclaw_env(),
        )
    except Exception:
        return set()
    if int(getattr(proc, "returncode", 1) or 1) != 0:
        return set()
    try:
        payload = json.loads(getattr(proc, "stdout", "") or "[]")
    except Exception:
        return set()
    agent_ids: set[str] = set()
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                token = str(item.get("id", "")).strip()
                if token:
                    agent_ids.add(token)
    return agent_ids


def _openclaw_delete_agent(agent_id: str) -> None:
    token = str(agent_id or "").strip()
    if not token or not _openclaw_available():
        return
    subprocess.run(
        ["openclaw", "agents", "delete", "--force", token],
        text=True,
        capture_output=True,
        check=False,
        env=_openclaw_env(),
    )


def _subagent_launcher_alive(subagent_id: str) -> bool:
    token = str(subagent_id or "").strip()
    if not token:
        return False
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        return False
    if int(getattr(proc, "returncode", 1) or 1) != 0:
        return False
    needle = f"--subagent-id {token}"
    for line in str(getattr(proc, "stdout", "") or "").splitlines():
        text = str(line or "").strip()
        if not text or needle not in text:
            continue
        if "planner_subagent_manager.py" in text:
            return True
        if "openclaw agent" in text:
            return True
    return False


def _extract_openclaw_payload_text(raw_text: str) -> tuple[str, str]:
    text = (raw_text or "").strip()
    if not text:
        return "", ""
    try:
        payload = json.loads(text)
    except Exception:
        return text, ""

    container = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(container, dict) and isinstance(payload, dict) and isinstance(payload.get("payloads"), list):
        container = payload
    if isinstance(container, dict):
        payloads = container.get("payloads")
        if isinstance(payloads, list):
            text_candidates = []
            for item in payloads:
                if isinstance(item, dict):
                    candidate = item.get("text")
                    if isinstance(candidate, str) and candidate.strip():
                        text_candidates.append(candidate.strip())
            if text_candidates:
                meta = container.get("meta")
                if not isinstance(meta, dict) and isinstance(payload, dict):
                    meta = payload.get("meta")
                refs: list[str] = []
                if isinstance(meta, dict):
                    agent_meta = meta.get("agentMeta")
                    if isinstance(agent_meta, dict):
                        for key in ("sessionId", "provider", "model"):
                            value = agent_meta.get(key)
                            if isinstance(value, str) and value.strip():
                                refs.append(f"{key}={value}")
                return text_candidates[-1], ",".join(refs[:4])

    candidates: list[str] = []
    refs: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                lowered = str(key).lower()
                if lowered in {
                    "text",
                    "message",
                    "reply",
                    "summary",
                    "response",
                    "output",
                    "content",
                } and isinstance(value, str):
                    candidates.append(value)
                elif lowered in {"session_id", "id", "agent_id"} and isinstance(value, str):
                    refs.append(f"{key}={value}")
                else:
                    walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    walk(payload)
    return (candidates[-1] if candidates else text, ",".join(refs[:4]))


@dataclass
class PlannerSubagentConfig:
    root: Path
    registry_path: Path
    events_path: Path
    results_dir: Path
    enabled: bool
    cron_planner_only: bool
    max_active: int
    default_ttl_min: int
    retry_max: int
    backend: str
    backend_by_role: dict[str, str]
    managed_roles: set[str]
    allow_runtime_explorer: bool
    default_helper_mode: str


@dataclass
class PlannerSubagentResult:
    subagent_id: str
    target_role: str
    owner_task_id: str
    parent_role: str
    task_kind: str
    status: str
    summary: str
    root_cause: str
    fix_applied: str
    artifact: str
    verify: str
    raw_output_ref: str
    backend: str
    backend_ref: str = ""
    files_touched: str = "none"
    tests_run: str = "SKIP(no_tests)"
    commit_sha: str = "none"
    architecture_check: str = "none"
    vision_alignment: str = "none"
    recommended_next: str = "none"
    blocking_issue: str = "none"
    started_at: str = ""
    finished_at: str = ""
    backend_route_reason: str = "none"
    model: str = ""
    thinking: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "subagent_id": self.subagent_id,
            "target_role": self.target_role,
            "owner_task_id": self.owner_task_id,
            "parent_role": self.parent_role,
            "task_kind": self.task_kind,
            "status": self.status,
            "summary": self.summary,
            "root_cause": self.root_cause,
            "fix_applied": self.fix_applied,
            "artifact": self.artifact,
            "verify": self.verify,
            "raw_output_ref": self.raw_output_ref,
            "backend": self.backend,
            "backend_ref": self.backend_ref,
            "files_touched": self.files_touched,
            "tests_run": self.tests_run,
            "commit_sha": self.commit_sha,
            "architecture_check": self.architecture_check,
            "vision_alignment": self.vision_alignment,
            "recommended_next": self.recommended_next,
            "blocking_issue": self.blocking_issue,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "backend_route_reason": self.backend_route_reason,
            "model": self.model,
            "thinking": self.thinking,
        }


def _result_has_delivery_proof(result: PlannerSubagentResult, *, target_role: str) -> bool:
    if str(result.artifact or "").strip().lower() in EMPTY_FIELD_TOKENS:
        return False
    if str(result.verify or "").strip().lower() in EMPTY_FIELD_TOKENS:
        return False
    role_token = canonical_role(target_role)
    if role_token in {"dev", "admin"} and str(result.tests_run or "").strip().lower() in EMPTY_FIELD_TOKENS:
        return False
    if role_token == "dev" and str(result.commit_sha or "").strip().lower() in EMPTY_FIELD_TOKENS:
        return False
    return True


@dataclass
class PlannerSubagentRecord:
    subagent_id: str
    target_role: str
    owner_task_id: str
    parent_role: str
    task_kind: str
    status: str
    created_at: str
    expires_at: str
    ttl_min: int
    backend: str = "codex_exec"
    backend_ref: str = ""
    last_update_at: str = ""
    summary: str = ""
    root_cause: str = ""
    fix_applied: str = ""
    artifact: str = ""
    verify: str = ""
    files_touched: str = "none"
    tests_run: str = "SKIP(no_tests)"
    commit_sha: str = "none"
    architecture_check: str = "none"
    vision_alignment: str = "none"
    recommended_next: str = "none"
    blocking_issue: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)
    merged_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        purpose = str(self.metadata.get("purpose", self.task_kind) or self.task_kind).strip()
        role = str(self.metadata.get("role", self.target_role) or self.target_role).strip()
        last_meaningful_delta = str(self.metadata.get("last_meaningful_delta", "none") or "none").strip() or "none"
        monitor_agent_id = str(self.metadata.get("monitor_agent_id", "") or "").strip()
        target_agent_id = str(self.metadata.get("target_agent_id", "") or "").strip()
        stalled = bool(self.metadata.get("stalled", False))
        backend_route_reason = str(self.metadata.get("backend_route_reason", "none") or "none").strip() or "none"
        backend_cooldown_until = str(self.metadata.get("backend_cooldown_until", "") or "").strip()
        return {
            "subagent_id": self.subagent_id,
            "target_role": self.target_role,
            "role": role,
            "owner_task_id": self.owner_task_id,
            "parent_role": self.parent_role,
            "task_kind": self.task_kind,
            "purpose": purpose,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "ttl_min": self.ttl_min,
            "backend": self.backend,
            "backend_ref": self.backend_ref,
            "last_update_at": self.last_update_at,
            "summary": self.summary,
            "root_cause": self.root_cause,
            "fix_applied": self.fix_applied,
            "artifact": self.artifact,
            "verify": self.verify,
            "files_touched": self.files_touched,
            "tests_run": self.tests_run,
            "commit_sha": self.commit_sha,
            "architecture_check": self.architecture_check,
            "vision_alignment": self.vision_alignment,
            "recommended_next": self.recommended_next,
            "blocking_issue": self.blocking_issue,
            "last_meaningful_delta": last_meaningful_delta,
            "monitor_agent_id": monitor_agent_id,
            "target_agent_id": target_agent_id,
            "stalled": stalled,
            "backend_route_reason": backend_route_reason,
            "backend_cooldown_until": backend_cooldown_until,
            "metadata": self.metadata,
            "merged_at": self.merged_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerSubagentRecord":
        raw_metadata = payload.get("metadata", {})
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        projected_metadata = dict(metadata)
        for key in (
            "role",
            "purpose",
            "last_meaningful_delta",
            "monitor_agent_id",
            "target_agent_id",
            "stalled",
            "backend_route_reason",
            "backend_cooldown_until",
        ):
            if key in payload and key not in projected_metadata:
                projected_metadata[key] = payload.get(key)
        return cls(
            subagent_id=str(payload.get("subagent_id", "")).strip(),
            target_role=canonical_role(payload.get("target_role", "")),
            owner_task_id=str(payload.get("owner_task_id", "")).strip(),
            parent_role=canonical_role(payload.get("parent_role", "planner")),
            task_kind=str(payload.get("task_kind", "delivery")).strip(),
            status=str(payload.get("status", "spawned")).strip(),
            created_at=str(payload.get("created_at", "")).strip(),
            expires_at=str(payload.get("expires_at", "")).strip(),
            ttl_min=int(payload.get("ttl_min", 30) or 30),
            backend=str(payload.get("backend", "codex_exec")).strip(),
            backend_ref=str(payload.get("backend_ref", "")).strip(),
            last_update_at=str(payload.get("last_update_at", "")).strip(),
            summary=str(payload.get("summary", "")).strip(),
            root_cause=str(payload.get("root_cause", "")).strip(),
            fix_applied=str(payload.get("fix_applied", "")).strip(),
            artifact=str(payload.get("artifact", "")).strip(),
            verify=str(payload.get("verify", "")).strip(),
            files_touched=str(payload.get("files_touched", "none")).strip() or "none",
            tests_run=str(payload.get("tests_run", "SKIP(no_tests)")).strip() or "SKIP(no_tests)",
            commit_sha=str(payload.get("commit_sha", "none")).strip() or "none",
            architecture_check=str(payload.get("architecture_check", "none")).strip() or "none",
            vision_alignment=str(payload.get("vision_alignment", "none")).strip() or "none",
            recommended_next=str(payload.get("recommended_next", "none")).strip() or "none",
            blocking_issue=str(payload.get("blocking_issue", "none")).strip() or "none",
            metadata=projected_metadata,
            merged_at=str(payload.get("merged_at", "")).strip(),
        )


def _load_config(root: Path) -> PlannerSubagentConfig:
    cfg_path = root / "platform" / "config" / "runner" / "runner.v1.yaml"
    if not cfg_path.exists():
        cfg_path = root / "platform" / "config" / "runner" / "runner_config.v1.yaml"
    cfg = _read_structured(cfg_path, {})
    features = cfg.get("features", {}) if isinstance(cfg, dict) else {}
    orchestrator = features.get("planner_orchestrator", {}) if isinstance(features, dict) else {}
    env_enabled = "" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_ENABLED", "")
    env_cron_planner_only = "" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY", "")
    env_max_active = "" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_MAX_ACTIVE", "")
    env_default_ttl_min = "" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_DEFAULT_TTL_MIN", "")
    env_retry_max = "" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_RETRY_MAX", "")
    env_backend = "" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_BACKEND", "")
    enabled = str(env_enabled or orchestrator.get("enabled", 0)).strip() not in {"0", "false", "False", ""}
    cron_planner_only = str(env_cron_planner_only or orchestrator.get("cron_planner_only", 0)).strip() not in {"0", "false", "False", ""}
    max_active = int(env_max_active or orchestrator.get("max_active", 3) or 3)
    default_ttl_min = int(env_default_ttl_min or orchestrator.get("default_ttl_min", 45) or 45)
    retry_max = int(env_retry_max or orchestrator.get("retry_max", 2) or 2)
    backend = str(env_backend or orchestrator.get("backend", "codex_exec") or "codex_exec").strip().lower()
    allow_runtime_explorer = str(
        ("" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_ALLOW_RUNTIME_EXPLORER", ""))
        or orchestrator.get("allow_runtime_explorer", 0)
        or "0"
    ).strip().lower() not in {"0", "false", "no", "off", ""}
    default_helper_mode = str(
        ("" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_DEFAULT_HELPER_MODE", ""))
        or orchestrator.get("default_helper_mode", "native_codex")
        or "native_codex"
    ).strip().lower() or "native_codex"
    backend_by_role: dict[str, str] = {}
    raw_backend_by_role = "" if _running_under_tests() else str(os.environ.get("FC_PLANNER_ORCHESTRATOR_BACKEND_BY_ROLE", "") or "").strip()
    if not raw_backend_by_role:
        cfg_backend_by_role = orchestrator.get("backend_by_role", {})
        if isinstance(cfg_backend_by_role, dict):
            raw_backend_by_role = ",".join(
                f"{str(key).strip()}={str(value).strip()}"
                for key, value in cfg_backend_by_role.items()
                if str(key).strip() and str(value).strip()
            )
    for chunk in raw_backend_by_role.split(","):
        token = str(chunk or "").strip()
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key_token = str(key or "").strip().lower()
        value_token = str(value or "").strip().lower()
        if key_token and value_token:
            backend_by_role[key_token] = value_token
    raw_roles = "" if _running_under_tests() else os.environ.get("FC_PLANNER_ORCHESTRATOR_MANAGED_ROLES", "")
    if raw_roles.strip():
        managed_roles = {canonical_role(tok) for tok in raw_roles.split(",") if tok.strip()}
    else:
        cfg_roles = orchestrator.get("managed_roles", list(DEFAULT_MANAGED_ROLES))
        if not isinstance(cfg_roles, list):
            cfg_roles = list(DEFAULT_MANAGED_ROLES)
        managed_roles = {canonical_role(tok) for tok in cfg_roles if str(tok).strip()}
    planner_state_dir = resolve_orchestrator_write_path(root, "planner-subagents-registry.json").parent.resolve()
    registry_path = planner_state_dir / "planner-subagents-registry.json"
    events_path = planner_state_dir / "planner-subagents-events.jsonl"
    planner_state_dir.mkdir(parents=True, exist_ok=True)
    return PlannerSubagentConfig(
        root=root,
        registry_path=registry_path,
        events_path=events_path,
        results_dir=planner_state_dir / "planner-subagents-results",
        enabled=enabled,
        cron_planner_only=cron_planner_only,
        max_active=max(1, max_active),
        default_ttl_min=max(5, default_ttl_min),
        retry_max=max(0, retry_max),
        backend=backend or "codex_exec",
        backend_by_role=backend_by_role,
        managed_roles=managed_roles or set(DEFAULT_MANAGED_ROLES),
        allow_runtime_explorer=allow_runtime_explorer,
        default_helper_mode=default_helper_mode,
    )


def _resolve_backend(config: PlannerSubagentConfig, target_role: str, task_kind: str, backend_override: str = "") -> str:
    return model_plane_resolve_planner_backend_choice(
        target_role,
        task_kind,
        backend_override=backend_override,
        config_backend=config.backend,
        backend_by_role=config.backend_by_role,
    )


def _load_registry(path: Path) -> dict[str, Any]:
    payload = _read_json(path, {"subagents": [], "updated_at": ""})
    if not isinstance(payload, dict):
        payload = {"subagents": [], "updated_at": ""}
    rows = payload.get("subagents", [])
    if not isinstance(rows, list):
        rows = []
    payload["subagents"] = rows
    return payload


def _records_from_registry(payload: dict[str, Any]) -> list[PlannerSubagentRecord]:
    out: list[PlannerSubagentRecord] = []
    for item in payload.get("subagents", []):
        if isinstance(item, dict):
            out.append(PlannerSubagentRecord.from_dict(item))
    return out


def _registry_lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


@contextmanager
def _registry_lock(path: Path):
    lock_path = _registry_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _record_result_paths(path: Path, subagent_id: str) -> tuple[Path, Path]:
    state_root = path.parent
    results_dir = state_root / "planner-subagents-results"
    return results_dir / f"{subagent_id}.result.json", results_dir / f"{subagent_id}.raw.txt"


def _record_has_collectible_result(path: Path, record: PlannerSubagentRecord) -> bool:
    if not str(record.subagent_id or "").strip():
        return False
    result_path, raw_path = _record_result_paths(path, record.subagent_id)
    return result_path.exists() or raw_path.exists()


def _status_rank(status: str) -> int:
    return STATUS_RANK.get(str(status or "").strip().lower(), 0)


def _meaningful_text(value: Any) -> bool:
    token = str(value or "").strip()
    return bool(token and token.lower() not in EMPTY_FIELD_TOKENS)


def _coalesce_text(primary: Any, secondary: Any, *, fallback: str = "") -> str:
    if _meaningful_text(primary):
        return str(primary).strip()
    if _meaningful_text(secondary):
        return str(secondary).strip()
    return fallback


def _choose_iso(first: str, second: str, *, prefer_latest: bool) -> str:
    first_dt = _parse_iso(first)
    second_dt = _parse_iso(second)
    if first_dt and second_dt:
        chosen = max(first_dt, second_dt) if prefer_latest else min(first_dt, second_dt)
        return _iso(chosen)
    return str(first or second or "").strip()


def _record_sort_stamp(record: PlannerSubagentRecord) -> datetime:
    return (
        _parse_iso(record.merged_at)
        or _parse_iso(record.last_update_at)
        or _parse_iso(record.created_at)
        or datetime.fromtimestamp(0, timezone.utc)
    )


def _merge_record(existing: PlannerSubagentRecord, incoming: PlannerSubagentRecord) -> PlannerSubagentRecord:
    existing_rank = _status_rank(existing.status)
    incoming_rank = _status_rank(incoming.status)
    if incoming_rank > existing_rank:
        preferred, fallback = incoming, existing
    elif existing_rank > incoming_rank:
        preferred, fallback = existing, incoming
    elif str(existing.status).strip().lower() != str(incoming.status).strip().lower():
        if str(existing.status).strip().lower() in ACTIVE_STATUSES and str(incoming.status).strip().lower() not in ACTIVE_STATUSES:
            preferred, fallback = incoming, existing
        elif str(incoming.status).strip().lower() in ACTIVE_STATUSES and str(existing.status).strip().lower() not in ACTIVE_STATUSES:
            preferred, fallback = existing, incoming
        else:
            preferred, fallback = incoming, existing
    elif _record_sort_stamp(incoming) >= _record_sort_stamp(existing):
        preferred, fallback = incoming, existing
    else:
        preferred, fallback = existing, incoming

    status = preferred.status or fallback.status
    if existing_rank == incoming_rank == _status_rank("merged") and not str(preferred.merged_at or "").strip():
        status = "merged"
    status_token = str(status or "").strip().lower()
    if status_token in SUCCESS_RESULT_STATUSES.union({"merged"}):
        blocking_issue = _meaningful_issue(preferred.blocking_issue) or "none"
    else:
        blocking_issue = _coalesce_text(preferred.blocking_issue, fallback.blocking_issue, fallback="none")

    return PlannerSubagentRecord(
        subagent_id=preferred.subagent_id or fallback.subagent_id,
        target_role=preferred.target_role or fallback.target_role,
        owner_task_id=preferred.owner_task_id or fallback.owner_task_id,
        parent_role=preferred.parent_role or fallback.parent_role,
        task_kind=preferred.task_kind or fallback.task_kind,
        status=status,
        created_at=_choose_iso(existing.created_at, incoming.created_at, prefer_latest=False),
        expires_at=_choose_iso(existing.expires_at, incoming.expires_at, prefer_latest=True),
        ttl_min=max(int(existing.ttl_min or 0), int(incoming.ttl_min or 0)),
        backend=_coalesce_text(preferred.backend, fallback.backend, fallback="codex_exec"),
        backend_ref=_coalesce_text(preferred.backend_ref, fallback.backend_ref),
        last_update_at=_choose_iso(existing.last_update_at, incoming.last_update_at, prefer_latest=True),
        summary=_coalesce_text(preferred.summary, fallback.summary),
        root_cause=_coalesce_text(preferred.root_cause, fallback.root_cause),
        fix_applied=_coalesce_text(preferred.fix_applied, fallback.fix_applied),
        artifact=_coalesce_text(preferred.artifact, fallback.artifact),
        verify=_coalesce_text(preferred.verify, fallback.verify),
        files_touched=_coalesce_text(preferred.files_touched, fallback.files_touched, fallback="none"),
        tests_run=_coalesce_text(preferred.tests_run, fallback.tests_run, fallback="SKIP(no_tests)"),
        commit_sha=_coalesce_text(preferred.commit_sha, fallback.commit_sha, fallback="none"),
        architecture_check=_coalesce_text(preferred.architecture_check, fallback.architecture_check, fallback="none"),
        vision_alignment=_coalesce_text(preferred.vision_alignment, fallback.vision_alignment, fallback="none"),
        recommended_next=_coalesce_text(preferred.recommended_next, fallback.recommended_next, fallback="none"),
        blocking_issue=blocking_issue,
        metadata={**fallback.metadata, **preferred.metadata},
        merged_at=_choose_iso(existing.merged_at, incoming.merged_at, prefer_latest=True),
    )


def _save_registry(path: Path, records: list[PlannerSubagentRecord]) -> None:
    with _registry_lock(path):
        existing_rows = _records_from_registry(_load_registry(path))
        existing_by_id = {row.subagent_id: row for row in existing_rows if str(row.subagent_id or "").strip()}
        merged_rows: list[PlannerSubagentRecord] = []
        seen_ids: set[str] = set()
        for record in records:
            token = str(record.subagent_id or "").strip()
            if token and token in existing_by_id:
                merged = _merge_record(existing_by_id[token], record)
                existing_by_id[token] = merged
                if token in seen_ids:
                    merged_rows = [row for row in merged_rows if str(row.subagent_id or "").strip() != token]
                merged_rows.append(merged)
                seen_ids.add(token)
            else:
                if token:
                    existing_by_id[token] = record
                    seen_ids.add(token)
                merged_rows.append(record)
        payload = {
            "updated_at": _iso(),
            "legacy_compat_only": True,
            "decision_capable": False,
            "new_feature_target": False,
            "storage_plane": "runtime_mutable",
            "registry_secondary_only": True,
            "events_secondary_only": True,
            "provider_policy_plane": "model_plane",
            "subagents": [record.as_dict() for record in merged_rows],
        }
        _write_json(path, payload)
        mirror_path = _canonical_runtime_mirror_path(path)
        if mirror_path is not None:
            _write_json(mirror_path, payload)


def _emit_event(config: PlannerSubagentConfig, event: str, record: PlannerSubagentRecord, extra: dict[str, Any] | None = None) -> None:
    payload = {
        "ts": _iso(),
        "event": event,
        "legacy_compat_only": True,
        "decision_capable": False,
        "subagent_id": record.subagent_id,
        "target_role": record.target_role,
        "owner_task_id": record.owner_task_id,
        "parent_role": record.parent_role,
        "task_kind": record.task_kind,
        "status": record.status,
        "backend": record.backend,
    }
    if extra:
        payload.update(extra)
    _append_jsonl(config.events_path, payload)
    mirror_path = _canonical_runtime_mirror_path(config.events_path)
    if mirror_path is not None:
        _append_jsonl(mirror_path, payload)


def _cleanup_failure_record(
    config: PlannerSubagentConfig,
    record: PlannerSubagentRecord,
    reason: str,
    now: datetime,
) -> PlannerSubagentRecord:
    payload = record.as_dict()
    metadata = dict(payload.get("metadata", {}))
    metadata.update(
        {
            "cleanup_reason": str(reason or "").strip() or "cleanup",
            "cleanup_recorded_at": _iso(now),
            "last_meaningful_delta": f"cleanup:{str(reason or '').strip() or 'cleanup'}",
            "stalled": True,
        }
    )
    payload.update(
        {
            "status": "failed",
            "last_update_at": _iso(now),
            "summary": _compact(payload.get("summary") or f"Planner cleanup converted stalled subagent to failed: {reason}", 180),
            "artifact": payload.get("artifact") or _runtime_relpath(config.events_path, config.root),
            "verify": payload.get("verify") or f"cleanup_reason={reason}",
            "blocking_issue": str(reason or "").strip() or "planner_subagent_cleanup",
            "recommended_next": payload.get("recommended_next") or "planner_repair_or_reroute",
            "metadata": metadata,
        }
    )
    return PlannerSubagentRecord.from_dict(payload)


def _active_count(config: PlannerSubagentConfig, records: list[PlannerSubagentRecord]) -> int:
    return sum(1 for record in records if _record_effectively_active(config, record))


def _cleanup_records(config: PlannerSubagentConfig, records: list[PlannerSubagentRecord], now: datetime | None = None) -> tuple[list[PlannerSubagentRecord], list[str]]:
    now = now or _now()
    stale_active_seconds = max(300, int(os.environ.get("FC_PLANNER_SUBAGENT_STALE_ACTIVE_SECONDS", "600")))
    kept: list[PlannerSubagentRecord] = []
    removed: list[str] = []
    for record in records:
        if str(record.backend or "").strip().lower() == "openclaw" and record.status in ACTIVE_STATUSES:
            reason = "legacy_openclaw_backend_unsupported"
            _emit_event(
                config,
                "planner_subagent_cleanup",
                record,
                {"reason": reason},
            )
            kept.append(_cleanup_failure_record(config, record, reason, now))
            removed.append(record.subagent_id)
            continue
        result_path = config.results_dir / f"{record.subagent_id}.result.json"
        last_seen = _parse_iso(record.last_update_at) or _parse_iso(record.created_at)
        if (
            record.status in ACTIVE_STATUSES
            and not result_path.exists()
            and last_seen is not None
            and int((now - last_seen).total_seconds()) >= stale_active_seconds
        ):
            reason = f"stale_active_no_result>{stale_active_seconds}s"
            _emit_event(
                config,
                "planner_subagent_cleanup",
                record,
                {"reason": reason},
            )
            kept.append(_cleanup_failure_record(config, record, reason, now))
            removed.append(record.subagent_id)
            continue
        expires_at = _parse_iso(record.expires_at)
        if expires_at is None or expires_at > now:
            kept.append(record)
            continue
        _emit_event(config, "planner_subagent_cleanup", record, {"reason": "ttl_expired"})
        removed.append(record.subagent_id)
    return kept, removed


def _record_effectively_active(config: PlannerSubagentConfig, record: PlannerSubagentRecord) -> bool:
    if record.status not in ACTIVE_STATUSES:
        return False
    if _record_has_collectible_result(config.registry_path, record):
        return False
    return True


def _find_duplicate(config: PlannerSubagentConfig, records: list[PlannerSubagentRecord], target_role: str, owner_task_id: str) -> PlannerSubagentRecord | None:
    for record in records:
        if (
            record.target_role == target_role
            and record.owner_task_id == owner_task_id
            and _record_effectively_active(config, record)
        ):
            return record
    return None


def _recent_retryable_failure(
    records: list[PlannerSubagentRecord],
    target_role: str,
    owner_task_id: str,
) -> PlannerSubagentRecord | None:
    now = _now()
    for record in reversed(records):
        if record.target_role != target_role or record.owner_task_id != owner_task_id:
            continue
        if str(record.status or "").strip().lower() != "failed":
            continue
        issue = str(record.blocking_issue or "").strip().lower()
        if issue not in RETRYABLE_BACKEND_FAILURE_MARKERS:
            continue
        ref = _parse_iso(record.last_update_at) or _parse_iso(record.created_at)
        if ref is None:
            continue
        if (now - ref).total_seconds() <= RETRYABLE_BACKEND_FAILURE_COOLDOWN_SECONDS:
            return record
        break
    return None


def _expected_target_role_from_owner_task_id(owner_task_id: str) -> str:
    token = str(owner_task_id or "").strip().upper()
    if not token:
        return ""
    parts = [part for part in token.split("-") if part]
    if len(parts) < 3:
        return ""
    marker = parts[2]
    if marker == "DEV":
        return "dev"
    if marker == "ADMIN":
        return "admin"
    if marker == "GOV_REVIEW":
        return "admin"
    if marker == "SCRUM_MASTER":
        return "scrum_master"
    return ""


def _role_runtime_defaults(config: PlannerSubagentConfig, target_role: str) -> tuple[str, str, str]:
    cfg_path = config.root / "platform" / "config" / "runner" / "runner.v1.yaml"
    if not cfg_path.exists():
        cfg_path = config.root / "platform" / "config" / "runner" / "runner_config.v1.yaml"
    cfg = _read_json(cfg_path, {})
    roles = cfg.get("roles", {}) if isinstance(cfg, dict) else {}
    role_cfg = roles.get(target_role, {}) if isinstance(roles, dict) else {}
    model_default, thinking_default, sandbox_default = ROLE_MODELS.get(target_role, ("gpt-5.4", "high", "workspace-write"))
    model = str(role_cfg.get("model", model_default) or model_default).strip()
    thinking = str(role_cfg.get("thinking", thinking_default) or thinking_default).strip()
    sandbox = sandbox_default
    return model, thinking, sandbox


def _effective_task_sandbox(target_role: str, task_kind: str, sandbox: str) -> str:
    role = canonical_role(target_role)
    current = str(sandbox or "").strip().lower() or "workspace-write"
    if role in {"dev", "admin", "scrum_master"}:
        return "danger-full-access"
    return current


def _normalize_meaningful_delta(value: Any, *, fallback: str = "none") -> str:
    token = " ".join(str(value or "").strip().split())
    if not token:
        return fallback
    if token.lower() in NON_MEANINGFUL_DELTA_TOKENS:
        return fallback
    return _compact(token, 220)


def _result_meaningful_delta(result: PlannerSubagentResult) -> str:
    if str(result.backend or "").strip().lower() == "qwen":
        return "degraded_backend:qwen_fallback"
    if _is_invalid_result_reason(result.blocking_issue):
        return "none"
    artifact = str(result.artifact or "").strip().lower()
    if artifact and artifact not in {"none", "n/a", "na"}:
        return "artifact_delta"
    files_touched = str(result.files_touched or "").strip().lower()
    if files_touched and files_touched not in {"none", "n/a", "na"}:
        return "code_delta"
    tests_run = str(result.tests_run or "").strip().lower()
    if tests_run and tests_run not in {"none", "n/a", "na", "skip(no_tests)", "skip(no_code_runtime_fix)"}:
        return "test_delta"
    verify = str(result.verify or "").strip().lower()
    if verify and verify not in {"none", "n/a", "na"}:
        return "verify_delta"
    status = str(result.status or "").strip().lower()
    if status in SUCCESS_RESULT_STATUSES:
        return "subagent_completed"
    if status in BLOCKED_RESULT_STATUSES:
        return str(result.blocking_issue or "blocked").strip() or "blocked"
    if status in ACTIVE_STATUSES:
        return "subagent_running"
    return "none"


def _payload_meaningful_delta(payload: dict[str, Any]) -> str:
    backend = str(payload.get("backend", "")).strip().lower()
    if backend == "qwen":
        return "degraded_backend:qwen_fallback"
    artifact = str(payload.get("artifact", "")).strip().lower()
    if artifact and artifact not in {"none", "n/a", "na"}:
        return "artifact_delta"
    files_touched = str(payload.get("files_touched", "")).strip().lower()
    if files_touched and files_touched not in {"none", "n/a", "na"}:
        return "code_delta"
    tests_run = str(payload.get("tests_run", "")).strip().lower()
    if tests_run and tests_run not in {"none", "n/a", "na", "skip(no_tests)", "skip(no_code_runtime_fix)"}:
        return "test_delta"
    verify = str(payload.get("verify", "")).strip().lower()
    if verify and verify not in {"none", "n/a", "na"}:
        return "verify_delta"
    blocking_issue = str(payload.get("blocking_issue", "")).strip()
    if _is_invalid_result_reason(blocking_issue):
        return "none"
    status = str(payload.get("status", "")).strip().lower()
    if status in SUCCESS_RESULT_STATUSES:
        return "subagent_completed"
    if status in BLOCKED_RESULT_STATUSES:
        return blocking_issue or "blocked"
    return "none"


def _build_prompt(target_role: str, owner_task_id: str, task_kind: str, message: str) -> str:
    common = (
        "PLANNER_ORCHESTRATED_SUBAGENT=1\n"
        f"TARGET_ROLE={target_role}\n"
        f"OWNER_TASK_ID={owner_task_id}\n"
        f"TASK_KIND={task_kind}\n"
        "MODE=planner_capability\n"
        "Hard output contract:\n"
        "Return exactly one JSON object only: {status, summary, root_cause, fix_applied, artifact, verify, files_touched, tests_run, commit_sha, architecture_check, vision_alignment, recommended_next, blocking_issue}.\n"
        "First non-whitespace byte must be { and last must be }. No markdown, no code fence, no prose before or after, no kickoff/progress chatter or shell/banner echo.\n"
        "summary must be final outcome only, never a plan, progress note, or \"I will...\".\n"
        "status must be completed, blocked, or failed. blocked=in-scope blocker; failed=tool/runtime failure. If shipped or verified, set blocking_issue=none and recommended_next=planner_merge_result.\n"
        "blocked/failed require concrete blocking_issue + recommended_next. Use none or SKIP(reason) only when a field truly does not apply.\n"
        "You are a capability inside OWNER_TASK_ID, not a scheduler. No queue/workboard mutation, no repo-wide audit, no broad repo hygiene.\n"
        "Target the smallest in-scope fix or proof for the Finance Copilot brief+ask with explainable memo output path or its next delivery blocker.\n"
        "Read minimum context with rg/sed/tail; for large memory/log files use rg/sed/tail instead of cat. As soon as you have proof or a real blocker, emit the final JSON immediately.\n"
        "Prefer a bounded fix or artifact now; do not stop at analysis-only.\n"
        "Work on the narrowest file/test set that can unblock OWNER_TASK_ID.\n"
        f"Planner instruction: {message.strip()}\n"
    )
    if target_role == "dev":
        return common + (
            "Dev role:\n"
            "- Default to code/config/tests inside the task path; touch docs/prompts only when the task notes make them part of the delivery slice.\n"
            "- Reuse existing modules, services, and contracts before creating new helpers or files.\n"
            "- verify=before=...; after=...; test=...\n"
            "- architecture_check=layer=...; imports_ok=...; path_target=...\n"
            "- vision_alignment=batch=...; target=...; impact=...\n"
        )
    if target_role == "admin":
        return common + (
            "Admin role:\n"
            "- Handle runtime truth, orchestration drift, stale locks, dispatch/collect failures, or broken execution paths blocking delivery.\n"
            "- VM UTM runtime truth = control-plane truth; EC2 public app runtime = product truth. queue/workboard/monitor are projections; on EC2 app-only, planner-gap / issue_publication_gap and missing `executors-monitoring-latest.json` / `agent-iteration-issues*` stay advisory.\n"
            "- Prefer planner_runtime_actions.py, runtime truth helpers, VM-safe wrappers before broader control-plane surgery.\n"
            "- Use runtime helpers first; patch control-plane only if helpers are insufficient.\n"
            "- Prefer the narrowest reversible fix that resumes delivery, collect, QA, or dispatch within one planner tick.\n"
            "- If it is not a runtime/control-plane issue, set recommended_next=planner_route_to_dev_or_scrum and say why.\n"
        )
    return common + (
        "Scrum role:\n"
        "- Own delivery acceleration, flow clarity, and unblock coordination for this task.\n"
        "- You may edit task-scoped docs, proofs, handoff notes, prompts, memory, coordination artifacts, acceptance criteria, dependency notes, or narrow supporting config/spec text when that increases deliverability.\n"
        "- Prefer small changes that remove ambiguity, improve handoff quality, strengthen acceptance criteria, or fix stale orchestration guidance.\n"
        "- Aim to make the next dev/admin move obvious, bounded, and mergeable.\n"
        "- Do not edit queue/workboard/contracts directly, and do not take over deep dev/admin implementation unless planner reroutes the task.\n"
        "- Return one precise unblock action, or a small coordination artifact plus the next planner action.\n"
    )


def _parse_result_payload(raw_text: str, subagent_id: str, target_role: str, owner_task_id: str, parent_role: str, task_kind: str, backend: str) -> PlannerSubagentResult:
    text = (raw_text or "").strip()
    payload: dict[str, Any] = {}
    if text:
        payload = _extract_last_json_object(text)
        if not payload:
            if _looks_like_rate_limited(text):
                rate_limit_issue = _active_rate_limit_reason(("codex", "global")) or _compact(text, 160)
                return PlannerSubagentResult(
                    subagent_id=subagent_id,
                    target_role=target_role,
                    owner_task_id=owner_task_id,
                    parent_role=parent_role,
                    task_kind=task_kind,
                    status="failed",
                    summary=rate_limit_issue,
                    root_cause="codex_exec_rate_limit",
                    fix_applied="none",
                    artifact="none",
                    verify="none",
                    raw_output_ref="",
                    backend=backend,
                    files_touched="none",
                    tests_run="SKIP(no_tests)",
                    commit_sha="none",
                    architecture_check="none",
                    vision_alignment="none",
                    recommended_next="planner_retry_with_secondary_codex_or_wait_for_quota",
                    blocking_issue=rate_limit_issue,
                )
            line0 = str(text.splitlines()[0] if text.splitlines() else text).strip()
            normalized_issue = ""
            if line0.startswith("invalid_subagent_result:"):
                normalized_issue = line0
            elif _looks_like_startup_noise(text):
                normalized_issue = "invalid_subagent_result:start_banner_only"
            if normalized_issue:
                return PlannerSubagentResult(
                    subagent_id=subagent_id,
                    target_role=target_role,
                    owner_task_id=owner_task_id,
                    parent_role=parent_role,
                    task_kind=task_kind,
                    status="failed",
                    summary=normalized_issue,
                    root_cause="none",
                    fix_applied="none",
                    artifact="none",
                    verify="none",
                    raw_output_ref="",
                    backend=backend,
                    files_touched="none",
                    tests_run="SKIP(no_tests)",
                    commit_sha="none",
                    architecture_check="none",
                    vision_alignment="none",
                    recommended_next="planner_retry_or_fallback",
                    blocking_issue=normalized_issue,
                )
    status = _normalize_result_field(payload.get("status", "failed"), fallback="failed", limit=80, field="status")
    summary = _normalize_result_field(payload.get("summary", text or "no_summary"), fallback="none", limit=260, field="summary")
    root_cause = _normalize_result_field(payload.get("root_cause", "none"), fallback="none", limit=220, field="root_cause")
    fix_applied = _normalize_result_field(payload.get("fix_applied", "none"), fallback="none", limit=220, field="fix_applied")
    artifact = _normalize_result_field(payload.get("artifact", "none"), fallback="none", limit=220, field="artifact")
    verify = _normalize_result_field(payload.get("verify", "none"), fallback="none", limit=220, field="verify")
    files_touched = _normalize_result_field(payload.get("files_touched", "none"), fallback="none", limit=220, field="files_touched")
    tests_run = _normalize_result_field(payload.get("tests_run", "SKIP(no_tests)"), fallback="SKIP(no_tests)", limit=220, field="tests_run")
    commit_sha = _normalize_result_field(payload.get("commit_sha", "none"), fallback="none", limit=120, field="commit_sha")
    architecture_check = _normalize_result_field(payload.get("architecture_check", "none"), fallback="none", limit=220, field="architecture_check")
    vision_alignment = _normalize_result_field(payload.get("vision_alignment", "none"), fallback="none", limit=220, field="vision_alignment")
    recommended_next = _normalize_result_field(payload.get("recommended_next", "none"), fallback="none", limit=220, field="recommended_next")
    blocking_issue = _normalize_result_field(payload.get("blocking_issue", "none"), fallback="none", limit=160, field="blocking_issue")
    return PlannerSubagentResult(
        subagent_id=subagent_id,
        target_role=target_role,
        owner_task_id=owner_task_id,
        parent_role=parent_role,
        task_kind=task_kind,
        status=status,
        summary=summary,
        root_cause=root_cause,
        fix_applied=fix_applied,
        artifact=artifact,
        verify=verify,
        raw_output_ref="",
        backend=backend,
        files_touched=files_touched,
        tests_run=tests_run,
        commit_sha=commit_sha,
        architecture_check=architecture_check,
        vision_alignment=vision_alignment,
        recommended_next=recommended_next,
        blocking_issue=blocking_issue,
    )


def _run_codex_exec_subagent(
    config: PlannerSubagentConfig,
    plan: dict[str, Any],
    prompt: str,
    timeout_seconds: int,
    subagent_id: str,
) -> tuple[int, str, str, str]:
    cached_reason = _active_rate_limit_reason(("codex", "global"))
    def _invoke_codex_exec(
        timeout_override_seconds: int,
        model_override: str = "",
        thinking_override: str = "",
    ) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory(prefix="planner-subagent-") as td:
            tmpdir = Path(td)
            schema_path = tmpdir / "schema.json"
            out_path = tmpdir / "last_message.json"
            schema_path.write_text(json.dumps(RESULT_SCHEMA, ensure_ascii=True), encoding="utf-8")
            sandbox_token = str(plan["sandbox"]).strip().lower()
            cmd = [
                "codex",
                "exec",
                "--enable",
                "multi_agent",
                "--enable",
                "apps",
                "--enable",
                "js_repl",
                "-C",
                str(config.root),
                "--skip-git-repo-check",
                "--color",
                "never",
                "--output-schema",
                str(schema_path),
                "-o",
                str(out_path),
                "-m",
                str(model_override or plan["model"]),
                "-c",
                f'model_reasoning_effort="{thinking_override or plan["thinking"]}"',
            ]
            if sandbox_token in {"off", "danger-full-access"}:
                cmd.append("--dangerously-bypass-approvals-and-sandbox")
            else:
                cmd.extend(["--sandbox", str(plan["sandbox"])])
            if sandbox_token == "workspace-write":
                cmd.append("--full-auto")
            timeout_value = _subprocess_timeout_value(timeout_override_seconds)
            try:
                proc = subprocess.run(
                    cmd + [prompt],
                    text=True,
                    capture_output=True,
                    check=False,
                    cwd=str(config.root),
                    timeout=timeout_value,
                )
                rc = proc.returncode
                stdout = _load_structured_output(out_path)
                stderr = proc.stderr or ""
                if not stdout:
                    normalized_issue = _normalized_retryable_backend_issue(proc.stdout or stderr or "")
                    stderr = "\n".join(part for part in (normalized_issue, stderr) if str(part or "").strip())
                    stdout = proc.stdout or ""
            except subprocess.TimeoutExpired as exc:
                rc = 124
                stdout = str(exc.stdout or "")
                timeout_label = timeout_value if isinstance(timeout_value, int) else "unbounded"
                stderr = str(exc.stderr or "") or f"codex_exec_timeout_after_{timeout_label}s"
            return rc, stdout, stderr

    if cached_reason:
        chained_fallback = model_plane_run_secondary_then_qwen_fallback(
            str(plan.get("target_role", "")),
            plan.get("model", ""),
            plan.get("thinking", ""),
            prompt,
            timeout_seconds,
            subagent_id,
            reason=cached_reason,
            source="codex_exec_cache",
            invoke_codex_exec=_invoke_codex_exec,
            env=os.environ,
            which=shutil_which,
            cwd=config.root,
            default_model=SECONDARY_CODEX_DEFAULT_MODEL,
            default_thinking=SECONDARY_CODEX_DEFAULT_THINKING,
            invalid_result_prefix="invalid_subagent_result:",
        )
        if chained_fallback is not None:
            return chained_fallback
    rc, stdout, stderr = _invoke_codex_exec(timeout_seconds)
    combined = "\n".join(part for part in (stdout, stderr) if str(part or "").strip())
    if _looks_like_rate_limited(combined):
        chained_fallback = model_plane_run_secondary_then_qwen_fallback(
            str(plan.get("target_role", "")),
            plan.get("model", ""),
            plan.get("thinking", ""),
            prompt,
            timeout_seconds,
            subagent_id,
            reason=combined,
            source="codex_exec_rate_limit",
            invoke_codex_exec=_invoke_codex_exec,
            env=os.environ,
            which=shutil_which,
            cwd=config.root,
            default_model=SECONDARY_CODEX_DEFAULT_MODEL,
            default_thinking=SECONDARY_CODEX_DEFAULT_THINKING,
            invalid_result_prefix="invalid_subagent_result:",
        )
        if chained_fallback is not None:
            return chained_fallback
    if "invalid_subagent_result:" in combined:
        retry_timeout = min(max(45, int(timeout_seconds or 0) or 45), 90)
        retry_rc, retry_stdout, retry_stderr = _invoke_codex_exec(retry_timeout)
        retry_combined = "\n".join(part for part in (retry_stdout, retry_stderr) if str(part or "").strip())
        if _looks_like_rate_limited(retry_combined):
            qwen_fallback = model_plane_run_qwen_cli_fallback(
                prompt,
                timeout_seconds,
                subagent_id,
                reason=retry_combined,
                source="codex_exec_retry",
                env=os.environ,
                which=shutil_which,
                cwd=config.root,
            )
            if qwen_fallback is not None:
                return qwen_fallback
        if "invalid_subagent_result:" not in retry_combined:
            return retry_rc, retry_stdout, retry_stderr, f"codex_exec:{subagent_id}"
        qwen_fallback = model_plane_run_qwen_cli_fallback(
            prompt,
            timeout_seconds,
            subagent_id,
            reason=_normalized_retryable_backend_issue(retry_combined),
            source="codex_exec_invalid_result_direct",
            env=os.environ,
            which=shutil_which,
            cwd=config.root,
        )
        if qwen_fallback is not None:
            return qwen_fallback
        chained_fallback = model_plane_run_secondary_then_qwen_fallback(
            str(plan.get("target_role", "")),
            plan.get("model", ""),
            plan.get("thinking", ""),
            prompt,
            timeout_seconds,
            subagent_id,
            reason=_normalized_retryable_backend_issue(retry_combined),
            source="codex_exec_invalid_result",
            invoke_codex_exec=_invoke_codex_exec,
            env=os.environ,
            which=shutil_which,
            cwd=config.root,
            default_model=SECONDARY_CODEX_DEFAULT_MODEL,
            default_thinking=SECONDARY_CODEX_DEFAULT_THINKING,
            invalid_result_prefix="invalid_subagent_result:",
        )
        if chained_fallback is not None:
            return chained_fallback
        return max(retry_rc, 65), retry_stdout, retry_stderr, f"codex_exec:{subagent_id}"
    return rc, stdout, stderr, f"codex_exec:{subagent_id}"


def plan_subagent(
    config: PlannerSubagentConfig,
    role: str,
    target_role: str,
    owner_task_id: str,
    task_kind: str,
    backend_override: str = "",
) -> dict[str, Any]:
    parent_role = canonical_role(role)
    target = canonical_role(target_role)
    chosen_backend = _resolve_backend(config, target, task_kind, backend_override)
    records = _records_from_registry(_load_registry(config.registry_path))
    records, _ = _cleanup_records(config, records)
    duplicate = _find_duplicate(config, records, target, owner_task_id)
    active_count = _active_count(config, records)
    allowed = True
    reason = "allowed"
    expected_target_role = _expected_target_role_from_owner_task_id(owner_task_id)
    if parent_role not in ALLOWED_PARENT_ROLES:
        allowed = False
        reason = f"parent_role_forbidden:{parent_role}"
    elif not config.enabled:
        allowed = False
        reason = "planner_orchestrator_disabled"
    elif target not in config.managed_roles:
        allowed = False
        reason = f"target_role_not_managed:{target}"
    elif expected_target_role and target != expected_target_role:
        allowed = False
        reason = f"owner_task_target_role_mismatch:{expected_target_role}!={target}"
    elif task_kind not in ROLE_TASK_KINDS.get(target, set()):
        allowed = False
        reason = f"task_kind_not_allowed:{target}:{task_kind}"
    elif duplicate is not None:
        allowed = False
        reason = f"duplicate_active:{duplicate.subagent_id}"
    else:
        recent_retryable = _recent_retryable_failure(records, target, owner_task_id)
        if recent_retryable is not None:
            allowed = False
            reason = f"recent_retryable_failure:{recent_retryable.subagent_id}"
    if allowed and active_count >= config.max_active:
        allowed = False
        reason = f"max_active_reached:{active_count}/{config.max_active}"
    elif allowed:
        backend_reason = model_plane_validate_planner_dispatch_backend(chosen_backend, which=shutil_which)
        if backend_reason:
            allowed = False
            reason = backend_reason
    model, thinking, sandbox = _role_runtime_defaults(config, target)
    sandbox = _effective_task_sandbox(target, task_kind, sandbox)
    return {
        "allowed": allowed,
        "reason": reason,
        "provider_policy_plane": "model_plane",
        "parent_role": parent_role,
        "target_role": target,
        "owner_task_id": owner_task_id,
        "task_kind": task_kind,
        "active_count": active_count,
        "max_active": config.max_active,
        "default_ttl_min": config.default_ttl_min,
        "backend": chosen_backend,
        "model": model,
        "thinking": thinking,
        "sandbox": sandbox,
        "duplicate_subagent_id": duplicate.subagent_id if duplicate else "",
    }


def _planner_batch_id(owner_task_id: str) -> str:
    token = str(owner_task_id or "").strip()
    parts = [part for part in token.split("-") if part]
    if len(parts) >= 2 and parts[0].upper() in {"BATCH", "VB"}:
        return "-".join(parts[:2])
    return token


def run_subagent(
    config: PlannerSubagentConfig,
    role: str,
    target_role: str,
    owner_task_id: str,
    task_kind: str,
    message: str,
    ttl_min: int,
    backend: str,
    timeout_seconds: int,
    subagent_id_override: str = "",
) -> tuple[int, dict[str, Any]]:
    plan = plan_subagent(config, role, target_role, owner_task_id, task_kind, backend)
    if not plan["allowed"]:
        return 2, plan

    records = _records_from_registry(_load_registry(config.registry_path))
    records, _ = _cleanup_records(config, records)
    subagent_id = str(subagent_id_override or "").strip() or f"planner_{plan['target_role']}_{uuid.uuid4().hex[:10]}"
    now = _now()
    ttl = max(5, ttl_min or config.default_ttl_min)
    record = PlannerSubagentRecord(
        subagent_id=subagent_id,
        target_role=plan["target_role"],
        owner_task_id=owner_task_id,
        parent_role=plan["parent_role"],
        task_kind=task_kind,
        status="spawned",
        created_at=_iso(now),
        expires_at=_iso(now + timedelta(minutes=ttl)),
        ttl_min=ttl,
        backend=plan["backend"],
        metadata={"model": plan["model"], "thinking": plan["thinking"], "sandbox": plan["sandbox"], "purpose": task_kind, "role": plan["target_role"], "monitor_agent_id": "", "target_agent_id": "", "last_meaningful_delta": "spawned", "stalled": False, "backend_route_reason": "none", "backend_cooldown_until": "", "provider_policy_plane": "model_plane"},
    )
    records.append(record)
    _save_registry(config.registry_path, records)
    _emit_event(config, "planner_subagent_spawn", record, {"task_kind": task_kind})

    chosen_backend = plan["backend"]
    record.status = "running"
    record.last_update_at = _iso()
    record.metadata["last_meaningful_delta"] = "subagent_running"
    record.metadata["stalled"] = False
    _save_registry(config.registry_path, records)
    _emit_event(config, "planner_subagent_start", record, {"backend": chosen_backend})

    stdout = ""
    stderr = ""
    rc = 0
    backend_ref = subagent_id
    effective_backend = chosen_backend
    prompt = _build_prompt(plan["target_role"], owner_task_id, task_kind, message)
    active_invalid_route = _current_invalid_result_route(config, records, owner_task_id, plan["target_role"])
    backend_route_reason = str(active_invalid_route.get("route_reason", "none") or "none").strip() or "none"
    backend_cooldown_until = str(active_invalid_route.get("cooldown_until", "") or "").strip()
    record.metadata["backend_route_reason"] = backend_route_reason
    record.metadata["backend_cooldown_until"] = backend_cooldown_until
    capability_task = CapabilityTask(
        batch_id=_planner_batch_id(owner_task_id),
        task_id=owner_task_id,
        task_kind=task_kind,
        owner_role=plan["parent_role"],
        target_role=plan["target_role"],
        backend=chosen_backend,
        model=str(plan["model"] or ""),
        thinking=str(plan["thinking"] or ""),
        sandbox=str(plan["sandbox"] or ""),
        timeout_seconds=int(timeout_seconds or 0),
        queue_snapshot_ref=str(resolve_orchestrator_read_path(config.root, "priority-queue.json")),
        workboard_snapshot_ref=str(resolve_orchestrator_read_path(config.root, "parallel-workstreams.json")),
        metadata={
            "subagent_id": subagent_id,
            "backend_requested": chosen_backend,
            "backend_route_reason": backend_route_reason,
            "backend_cooldown_until": backend_cooldown_until,
            "provider_policy_plane": "model_plane",
            "operator_plane": "openclaw",
        },
    )
    try:
        PlannerGraphRuntime(config.root).observe_dispatch(capability_task)
    except Exception:
        pass

    if chosen_backend == "openclaw":
        chosen_backend = "codex_exec"
        effective_backend = "codex_exec"
        backend_route_reason = "openclaw_provider_removed"
        record.metadata["backend_route_reason"] = backend_route_reason

    if active_invalid_route and chosen_backend != "mock":
        chosen_backend = "qwen"
        effective_backend = "qwen"
        qwen_fallback = model_plane_run_qwen_cli_fallback(
            prompt,
            timeout_seconds,
            subagent_id,
            reason=backend_route_reason,
            source="invalid_result_route",
            env=os.environ,
            which=shutil_which,
            cwd=config.root,
        )
        if qwen_fallback is None:
            rc = 5
            backend_ref = f"qwen:{subagent_id}"
            stderr = f"qwen_route_disabled:{backend_route_reason}"
        else:
            rc, stdout, stderr, backend_ref = qwen_fallback
    elif chosen_backend == "mock":
        stdout = json.dumps(
            {
                "status": "completed",
                "summary": f"Mock {plan['target_role']} subagent executed for {owner_task_id}",
                "root_cause": f"mock_root_cause_for_{owner_task_id}",
                "fix_applied": f"mock_fix_for_{owner_task_id}",
                "artifact": "mock://artifact",
                "verify": "before=mock_before; after=mock_after; test=mock_probe",
                "files_touched": "mock/file.py",
                "tests_run": "SKIP(mock)",
                "commit_sha": "mock-commit-sha",
                "architecture_check": "layer=platform; imports_ok=yes; path_target=mock/file.py",
                "vision_alignment": f"batch={owner_task_id.split('-', 2)[0] if '-' in owner_task_id else owner_task_id}; target=mock_delivery; impact=planner_bridge_validation",
                "recommended_next": "planner_merge_mock_result",
                "blocking_issue": "none",
            },
            ensure_ascii=True,
        )
    elif chosen_backend == "codex_exec":
        rc, stdout, stderr, backend_ref = _run_codex_exec_subagent(
            config,
            plan,
            prompt,
            timeout_seconds,
            subagent_id,
        )
    else:
        rc = 5
        stderr = f"unsupported_backend:{chosen_backend}"

    backend_ref_token = str(backend_ref or "").strip().lower()
    if backend_ref_token.startswith("qwen:"):
        effective_backend = "qwen"
    elif backend_ref_token.startswith("codex_exec:"):
        effective_backend = "codex_exec"
    elif effective_backend != "qwen":
        effective_backend = chosen_backend
    if backend_route_reason in {"", "none"}:
        if backend_ref_token.startswith("codex_exec:") and str(backend_ref or "").count(":") >= 2:
            backend_route_reason = "secondary_codex_fallback"
        elif backend_ref_token.startswith("qwen:") or effective_backend == "qwen":
            backend_route_reason = "qwen_fallback"

    config.results_dir.mkdir(parents=True, exist_ok=True)
    raw_path = config.results_dir / f"{subagent_id}.raw.txt"
    raw_blob = "\n".join(part for part in (stdout, stderr) if str(part or "").strip())
    raw_path.write_text(raw_blob, encoding="utf-8")
    normalized_error = ""
    for candidate in (stderr, stdout):
        line0 = str(candidate or "").splitlines()[0].strip() if str(candidate or "").splitlines() else ""
        if line0.startswith("invalid_subagent_result:"):
            normalized_error = line0
            break
    # Keep the full raw streams for result parsing so we can salvage the last
    # structured JSON object even when Codex also emits a startup-noise marker.
    # This preserves the real blocker/recommended_next instead of flattening the
    # run into `invalid_subagent_result:start_banner_only`.
    result_source = raw_blob if raw_blob else (normalized_error or (stdout if stdout else stderr))
    result = _parse_result_payload(
        result_source,
        subagent_id,
        plan["target_role"],
        owner_task_id,
        plan["parent_role"],
        task_kind,
        effective_backend,
    )
    result.raw_output_ref = _runtime_relpath(raw_path, config.root)
    result.backend_ref = backend_ref
    result.started_at = record.created_at
    result.finished_at = _iso()
    route_reason_value, result_model, result_thinking = model_plane_resolve_effective_backend_details(
        plan,
        effective_backend,
        backend_ref,
        backend_route_reason,
        env=os.environ,
        default_qwen_model="qwen",
        default_secondary_model=SECONDARY_CODEX_DEFAULT_MODEL,
        default_secondary_thinking=SECONDARY_CODEX_DEFAULT_THINKING,
    )
    result.backend_route_reason = route_reason_value
    result.model = result_model
    result.thinking = result_thinking
    if rc != 0:
        result.status = "failed"
        if normalized_error:
            result.blocking_issue = normalized_error
        elif result.blocking_issue == "none":
            result.blocking_issue = _compact(stderr or f"{effective_backend}_rc_{rc}", 160)
        if normalized_error and (_looks_like_startup_noise(result.summary) or result.summary == "none"):
            result.summary = normalized_error
        elif result.summary == "none":
            result.summary = _compact(stderr or f"{effective_backend}_failed", 220)
    else:
        status_token = str(result.status).strip().lower()
        if status_token == "blocked":
            blocked_has_signal = any(
                _value_present(value)
                for value in (
                    result.summary,
                    result.recommended_next,
                    result.blocking_issue,
                    result.verify,
                    result.artifact,
                )
            )
            if not blocked_has_signal or (_looks_like_startup_noise(result.summary) and result.blocking_issue == "none"):
                result.status = "failed"
                if result.blocking_issue == "none":
                    result.blocking_issue = "invalid_subagent_result:blocked_without_signal"
                if result.summary == "none" or _looks_like_startup_noise(result.summary):
                    result.summary = _compact(result.blocking_issue, 220)
        else:
            mergeable, invalid_reason = _semantic_result_gate(result.as_dict())
            if not mergeable:
                result.status = "failed"
                if result.blocking_issue == "none":
                    result.blocking_issue = invalid_reason
                if result.summary == "none" or _looks_like_startup_noise(result.summary):
                    result.summary = _compact(invalid_reason, 220)
                if effective_backend == "codex_exec" and _is_invalid_result_reason(invalid_reason):
                    triggered_route = _current_invalid_result_route(
                        config,
                        records,
                        owner_task_id,
                        plan["target_role"],
                        current_failure_reason=invalid_reason,
                    )
                    if triggered_route:
                        backend_route_reason = str(triggered_route.get("route_reason", "invalid_result_burst") or "invalid_result_burst").strip()
                        backend_cooldown_until = str(triggered_route.get("cooldown_until", "") or "").strip()
                        if result.recommended_next == "none":
                            result.recommended_next = "planner_retry_with_qwen_after_invalid_result_burst"
                    else:
                        route_path = _invalid_result_route_path(config)
                        route_payload = _load_invalid_result_routes(route_path)
                        route_key = _invalid_result_route_key(owner_task_id, plan["target_role"])
                        route_entry = {
                            "owner_task_id": str(owner_task_id or "").strip(),
                            "target_role": canonical_role(plan["target_role"]),
                            "route_reason": "invalid_result_burst",
                            "backend": "qwen",
                            "failure_count": 2,
                            "last_reason": invalid_reason,
                            "updated_at": _iso(_now()),
                            "cooldown_until": _iso(_now() + timedelta(seconds=INVALID_RESULT_COOLDOWN_SECONDS)),
                        }
                        route_payload.setdefault("routes", {})[route_key] = route_entry
                        _save_invalid_result_routes(route_path, route_payload)
                        backend_route_reason = "invalid_result_burst"
                        backend_cooldown_until = str(route_entry.get("cooldown_until", "") or "").strip()
                        if result.recommended_next == "none":
                            result.recommended_next = "planner_retry_with_qwen_after_invalid_result_burst"
    result_path = config.results_dir / f"{subagent_id}.result.json"
    result_path.write_text(json.dumps(result.as_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    capability_result = CapabilityResult(
        batch_id=_planner_batch_id(owner_task_id),
        task_id=owner_task_id,
        owner_role=plan["parent_role"],
        target_role=plan["target_role"],
        backend=effective_backend,
        status=str(result.status or ""),
        rc=int(rc or 0),
        summary=str(result.summary or ""),
        blocking_issue=str(result.blocking_issue or "none"),
        artifact=str(result.artifact or "none"),
        verify=str(result.verify or "none"),
        files_touched=str(result.files_touched or "none"),
        tests_run=str(result.tests_run or "none"),
        commit_sha=str(result.commit_sha or "none"),
        raw_output_ref=str(result.raw_output_ref or ""),
        backend_ref=str(result.backend_ref or ""),
        result_path=_runtime_relpath(result_path, config.root),
        metadata={
            "subagent_id": subagent_id,
            "backend_requested": capability_task.metadata.get("backend_requested", ""),
            "backend_used": effective_backend,
            "backend_route_reason": route_reason_value,
        },
    )
    delivery_proof = None
    if _result_has_delivery_proof(result, target_role=plan["target_role"]):
        delivery_proof = DeliveryProof(
            batch_id=_planner_batch_id(owner_task_id),
            task_id=owner_task_id,
            artifact=str(result.artifact or "none"),
            verify=str(result.verify or "none"),
            tests_run=str(result.tests_run or "none"),
            commit_sha=str(result.commit_sha or "none"),
            summary=str(result.summary or ""),
        )
    try:
        PlannerGraphRuntime(config.root).observe_result(
            capability_task,
            capability_result,
            delivery_proof=delivery_proof,
        )
    except Exception:
        pass
    if effective_backend == "qwen" and str(result.status).strip().lower() in SUCCESS_RESULT_STATUSES:
        _clear_invalid_result_route(config, owner_task_id, plan["target_role"])
        backend_cooldown_until = ""

    for idx, existing in enumerate(records):
        if existing.subagent_id == subagent_id:
            records[idx].status = result.status
            records[idx].backend = effective_backend
            records[idx].backend_ref = backend_ref
            records[idx].last_update_at = result.finished_at
            records[idx].summary = result.summary
            records[idx].root_cause = result.root_cause
            records[idx].fix_applied = result.fix_applied
            records[idx].artifact = result.artifact
            records[idx].verify = result.verify
            records[idx].files_touched = result.files_touched
            records[idx].tests_run = result.tests_run
            records[idx].commit_sha = result.commit_sha
            records[idx].architecture_check = result.architecture_check
            records[idx].vision_alignment = result.vision_alignment
            records[idx].recommended_next = result.recommended_next
            records[idx].blocking_issue = result.blocking_issue
            records[idx].metadata["purpose"] = existing.task_kind or task_kind
            records[idx].metadata["role"] = existing.target_role or plan["target_role"]
            records[idx].metadata["model"] = result_model
            records[idx].metadata["thinking"] = result_thinking
            records[idx].metadata["last_meaningful_delta"] = _result_meaningful_delta(result)
            records[idx].metadata["stalled"] = bool(result.status in BLOCKED_RESULT_STATUSES or str(result.blocking_issue).strip().lower() not in {"", "none"})
            records[idx].metadata["monitor_agent_id"] = str(records[idx].metadata.get("monitor_agent_id", "") or "")
            records[idx].metadata["target_agent_id"] = str(records[idx].metadata.get("target_agent_id", "") or "")
            records[idx].metadata["backend_route_reason"] = route_reason_value
            records[idx].metadata["backend_cooldown_until"] = backend_cooldown_until
            break
    _save_registry(config.registry_path, records)
    emitted = next((row for row in records if row.subagent_id == subagent_id), record)
    _emit_event(config, "planner_subagent_result", emitted, {"rc": rc, "result_path": _runtime_relpath(result_path, config.root)})
    if plan["parent_role"] == "planner" and plan["target_role"] in config.managed_roles:
        _trigger_runtime_collect(config, owner_task_id=owner_task_id, target_role=plan["target_role"])
    payload = result.as_dict()
    payload["ok"] = rc == 0 and str(result.status).strip().lower() in SUCCESS_RESULT_STATUSES
    payload["rc"] = rc
    payload["backend_route_reason"] = route_reason_value
    payload["model"] = result_model
    payload["thinking"] = result_thinking
    if stderr:
        payload["stderr"] = _compact(stderr, 220)
    return (0 if payload["ok"] else 6), payload


def _recover_subagent_from_results(
    config: PlannerSubagentConfig,
    role: str,
    subagent_id: str,
    owner_task_id: str,
) -> tuple[PlannerSubagentRecord | None, dict[str, Any]]:
    candidate_paths: list[Path] = []
    if subagent_id:
        candidate_paths.append(config.results_dir / f"{subagent_id}.result.json")
    else:
        candidate_paths.extend(sorted(config.results_dir.glob("*.result.json")))
    parent_role = canonical_role(role)
    for candidate in candidate_paths:
        payload = _read_json(candidate, {})
        if not isinstance(payload, dict) or not payload:
            continue
        candidate_subagent_id = str(payload.get("subagent_id") or candidate.name.removesuffix(".result.json")).strip()
        candidate_owner_task_id = str(payload.get("owner_task_id", "")).strip()
        candidate_parent_role = canonical_role(payload.get("parent_role") or role)
        if subagent_id and candidate_subagent_id != subagent_id:
            continue
        if owner_task_id and candidate_owner_task_id != owner_task_id:
            continue
        if candidate_parent_role != parent_role:
            continue
        target_role = canonical_role(payload.get("target_role") or payload.get("role"))
        if not target_role:
            token = candidate_subagent_id.lower()
            if token.startswith("planner_dev_"):
                target_role = "dev"
            elif token.startswith("planner_admin_"):
                target_role = "admin"
            elif token.startswith("planner_scrum_master_") or token.startswith("planner_sm_"):
                target_role = "scrum_master"
        if not target_role:
            continue
        status = str(payload.get("status", "completed")).strip() or "completed"
        created_at = str(payload.get("started_at") or payload.get("created_at") or _iso()).strip() or _iso()
        try:
            ttl_min = max(1, int(payload.get("ttl_min") or 30))
        except Exception:
            ttl_min = 30
        expires_at = str(payload.get("expires_at") or _iso((_parse_iso(created_at) or _now()) + timedelta(minutes=ttl_min))).strip()
        if not expires_at:
            expires_at = _iso((_parse_iso(created_at) or _now()) + timedelta(minutes=ttl_min))
        record = PlannerSubagentRecord(
            subagent_id=candidate_subagent_id,
            target_role=target_role,
            owner_task_id=candidate_owner_task_id,
            parent_role=candidate_parent_role,
            task_kind=str(payload.get("task_kind") or payload.get("purpose") or "delivery").strip() or "delivery",
            status=status,
            created_at=created_at,
            expires_at=expires_at,
            ttl_min=ttl_min,
            backend=str(payload.get("backend") or "codex_exec").strip() or "codex_exec",
            backend_ref=str(payload.get("backend_ref") or "").strip(),
            last_update_at=str(payload.get("finished_at") or payload.get("updated_at") or created_at).strip() or created_at,
            summary=str(payload.get("summary") or "").strip(),
            root_cause=str(payload.get("root_cause") or "").strip(),
            fix_applied=str(payload.get("fix_applied") or "").strip(),
            artifact=str(payload.get("artifact") or "").strip(),
            verify=str(payload.get("verify") or "").strip(),
            files_touched=str(payload.get("files_touched") or "none").strip() or "none",
            tests_run=str(payload.get("tests_run") or "SKIP(no_tests)").strip() or "SKIP(no_tests)",
            commit_sha=str(payload.get("commit_sha") or "none").strip() or "none",
            architecture_check=str(payload.get("architecture_check") or "none").strip() or "none",
            vision_alignment=str(payload.get("vision_alignment") or "none").strip() or "none",
            recommended_next=str(payload.get("recommended_next") or "none").strip() or "none",
            blocking_issue=str(payload.get("blocking_issue") or "none").strip() or "none",
            metadata={"recovered_from_result": True},
        )
        return record, payload
    return None, {}


def collect_subagent(config: PlannerSubagentConfig, role: str, subagent_id: str, owner_task_id: str, mark_merged: bool) -> tuple[int, dict[str, Any]]:
    records = _records_from_registry(_load_registry(config.registry_path))
    target: PlannerSubagentRecord | None = None
    recovered_payload: dict[str, Any] = {}
    for record in records:
        if subagent_id and record.subagent_id == subagent_id:
            target = record
            break
        if subagent_id:
            continue
        if owner_task_id and record.owner_task_id == owner_task_id and record.parent_role == canonical_role(role):
            target = record
    if target is None:
        target, recovered_payload = _recover_subagent_from_results(config, role, subagent_id, owner_task_id)
        if target is None:
            return 3, {"ok": False, "reason": "subagent_not_found"}
        if not any(record.subagent_id == target.subagent_id for record in records):
            records.append(target)
    if canonical_role(role) != target.parent_role:
        return 4, {"ok": False, "reason": "parent_role_mismatch"}
    result_path = config.results_dir / f"{target.subagent_id}.result.json"
    raw_path = config.results_dir / f"{target.subagent_id}.raw.txt"
    payload = recovered_payload or _read_json(result_path, {})
    if not isinstance(payload, dict):
        payload = {}
    if payload and raw_path.exists() and _payload_needs_raw_recovery(payload):
        recovered_from_raw = _recover_payload_from_raw_output(
            _read_text_if_exists(raw_path),
            subagent_id=target.subagent_id,
            target_role=target.target_role,
            owner_task_id=target.owner_task_id,
            parent_role=target.parent_role,
            task_kind=target.task_kind,
            backend=target.backend,
        )
        if _payload_signal_score(recovered_from_raw) > _payload_signal_score(payload):
            payload = recovered_from_raw
            _write_json(result_path, payload)
    if not payload:
        if str(target.status).strip().lower() in ACTIVE_STATUSES:
            payload = {
                "subagent_id": target.subagent_id,
                "target_role": target.target_role,
                "owner_task_id": target.owner_task_id,
                "parent_role": target.parent_role,
                "task_kind": target.task_kind,
                "status": str(target.status).strip().lower() or "running",
                "summary": "subagent_result_pending:missing_result_payload",
                "root_cause": "pending_result_payload",
                "fix_applied": "pending_result_payload",
                "artifact": target.artifact or "none",
                "verify": target.verify or "none",
                "files_touched": target.files_touched or "none",
                "tests_run": target.tests_run or "SKIP(no_result_payload)",
                "commit_sha": target.commit_sha or "none",
                "architecture_check": target.architecture_check or "none",
                "vision_alignment": target.vision_alignment or "none",
                "recommended_next": "await_result_payload",
                "blocking_issue": "subagent_result_pending:missing_result_payload",
            }
        else:
            payload = {
                "subagent_id": target.subagent_id,
                "target_role": target.target_role,
                "owner_task_id": target.owner_task_id,
                "parent_role": target.parent_role,
                "task_kind": target.task_kind,
                "status": "failed",
                "summary": "invalid_subagent_result:missing_result_payload",
                "root_cause": "missing_result_payload",
                "fix_applied": "none",
                "artifact": target.artifact or "none",
                "verify": target.verify or "none",
                "files_touched": target.files_touched or "none",
                "tests_run": target.tests_run or "SKIP(no_result_payload)",
                "commit_sha": target.commit_sha or "none",
                "architecture_check": target.architecture_check or "none",
                "vision_alignment": target.vision_alignment or "none",
                "recommended_next": "repair_result_payload",
                "blocking_issue": "invalid_subagent_result:missing_result_payload",
            }
    status_token = str(payload.get("status", "")).strip().lower()
    mergeable, invalid_reason = _semantic_result_gate(payload)
    semantic_success = _payload_semantic_success(payload)
    pending_result = str(payload.get("blocking_issue", "")).strip().lower().startswith("subagent_result_pending:")
    if mark_merged:
        for record in records:
            if record.subagent_id == target.subagent_id:
                record.last_update_at = _iso()
                record.summary = str(payload.get("summary", record.summary)).strip()
                record.root_cause = str(payload.get("root_cause", record.root_cause)).strip() or record.root_cause
                record.fix_applied = str(payload.get("fix_applied", record.fix_applied)).strip() or record.fix_applied
                record.artifact = str(payload.get("artifact", record.artifact)).strip() or record.artifact
                record.verify = str(payload.get("verify", record.verify)).strip() or record.verify
                record.files_touched = str(payload.get("files_touched", record.files_touched)).strip() or record.files_touched
                record.tests_run = str(payload.get("tests_run", record.tests_run)).strip() or record.tests_run
                record.commit_sha = str(payload.get("commit_sha", record.commit_sha)).strip() or record.commit_sha
                record.architecture_check = str(payload.get("architecture_check", record.architecture_check)).strip() or record.architecture_check
                record.vision_alignment = str(payload.get("vision_alignment", record.vision_alignment)).strip() or record.vision_alignment
                record.recommended_next = str(payload.get("recommended_next", record.recommended_next)).strip() or record.recommended_next
                payload_issue = _meaningful_issue(payload.get("blocking_issue"))
                if payload_issue:
                    record.blocking_issue = payload_issue
                record.metadata["last_meaningful_delta"] = _payload_meaningful_delta(payload)
                if pending_result and str(record.status).strip().lower() in ACTIVE_STATUSES:
                    record.status = str(record.status).strip().lower() or "running"
                    record.metadata["stalled"] = False
                elif mergeable and semantic_success:
                    record.status = "merged"
                    record.merged_at = _iso()
                    record.blocking_issue = "none"
                    record.metadata["stalled"] = False
                    _emit_event(config, "planner_subagent_merge", record, {"merged_by": canonical_role(role)})
                else:
                    record.status = "failed" if status_token != "blocked" else "blocked"
                    record.blocking_issue = (
                        invalid_reason
                        if invalid_reason != "none"
                        else _meaningful_issue(record.blocking_issue) or f"subagent_status_{status_token or 'unknown'}"
                    )
                    record.metadata["stalled"] = bool(record.status == "blocked")
                    _emit_event(config, "planner_subagent_rejected", record, {"merged_by": canonical_role(role), "reason": record.blocking_issue})
                break
        _save_registry(config.registry_path, records)
    payload["mergeable"] = mergeable
    payload["ok"] = bool(mergeable and semantic_success)
    if mark_merged and bool(payload.get("ok")):
        try:
            capability_task = CapabilityTask(
                batch_id=_planner_batch_id(target.owner_task_id),
                task_id=target.owner_task_id,
                task_kind=target.task_kind,
                owner_role=target.parent_role,
                target_role=target.target_role,
                backend=str(payload.get("backend") or target.backend or ""),
                queue_snapshot_ref=str(resolve_orchestrator_read_path(config.root, "priority-queue.json")),
                workboard_snapshot_ref=str(resolve_orchestrator_read_path(config.root, "parallel-workstreams.json")),
                metadata={
                    "subagent_id": target.subagent_id,
                    "backend_requested": str(target.backend or ""),
                    "backend_route_reason": str(target.metadata.get("backend_route_reason", "")).strip(),
                    "backend_cooldown_until": str(target.metadata.get("backend_cooldown_until", "")).strip(),
                    "provider_policy_plane": "model_plane",
                    "operator_plane": "openclaw",
                },
            )
            PlannerGraphRuntime(config.root).observe_merge(
                capability_task,
                True,
                note=str(payload.get("summary") or payload.get("recommended_next") or "merged"),
            )
        except Exception:
            pass
    if invalid_reason != "none" and not _meaningful_issue(payload.get("blocking_issue")):
        payload["blocking_issue"] = invalid_reason
    elif not payload["ok"] and not _meaningful_issue(payload.get("blocking_issue")):
        payload["blocking_issue"] = f"subagent_status_{status_token or 'unknown'}"
    return (0 if payload["ok"] else 6), payload


def cleanup_subagents(config: PlannerSubagentConfig) -> dict[str, Any]:
    records = _records_from_registry(_load_registry(config.registry_path))
    kept, removed = _cleanup_records(config, records)
    _save_registry(config.registry_path, kept)
    return {"ok": True, "removed": removed, "remaining": len(kept)}


def status_snapshot(config: PlannerSubagentConfig, role: str = "") -> dict[str, Any]:
    records = []
    role_token = canonical_role(role) if role else ""
    runtime_truth_source = "fallback"
    event_store_primary = False

    def _normalize_dispatch_row(row: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(row)
        normalized["target_role"] = str(row.get("target_role") or row.get("role", "")).strip()
        normalized["role"] = str(row.get("role") or row.get("target_role", "")).strip()
        normalized["parent_role"] = str(row.get("parent_role") or "planner").strip()
        normalized["monitor_agent_id"] = str(row.get("monitor_agent_id", "")).strip()
        normalized["target_agent_id"] = str(row.get("target_agent_id", "")).strip()
        normalized["last_update_at"] = str(row.get("last_update_at", "")).strip()
        normalized["created_at"] = str(row.get("created_at", "")).strip()
        normalized["merged_at"] = str(row.get("merged_at", "")).strip()
        normalized["summary"] = str(row.get("summary", "")).strip()
        normalized["blocking_issue"] = str(row.get("blocking_issue", "")).strip()
        normalized["last_meaningful_delta"] = _normalize_meaningful_delta(row.get("last_meaningful_delta"), fallback="none")
        return normalized

    try:
        dispatch_snapshot = build_stable_planner_dispatch_snapshot(config.root, recent_limit=8)
    except Exception:
        dispatch_snapshot = {}
    runtime_truth_source = str(dispatch_snapshot.get("runtime_truth_source", "fallback") or "fallback").strip().lower()
    event_store_primary = bool(dispatch_snapshot.get("event_store_primary", False))

    if runtime_truth_source == "sqlite":
        active = [
            _normalize_dispatch_row(row)
            for row in dispatch_snapshot.get("active", [])
            if isinstance(row, dict) and (not role_token or canonical_role(row.get("parent_role", "")) == role_token)
        ]
        active.sort(key=lambda row: str(row.get("last_update_at") or row.get("created_at") or ""), reverse=True)
        recent = [
            _normalize_dispatch_row(row)
            for row in dispatch_snapshot.get("recent", [])
            if isinstance(row, dict) and (not role_token or canonical_role(row.get("parent_role", "")) == role_token)
        ]
        recent.sort(key=lambda row: str(row.get("merged_at") or row.get("last_update_at") or row.get("created_at") or ""), reverse=True)
        recent = recent[:8]
        if not active and not recent:
            records = _records_from_registry(_load_registry(config.registry_path))
            records, removed = _cleanup_records(config, records)
            if removed:
                _save_registry(config.registry_path, records)
            filtered = [record for record in records if not role_token or record.parent_role == role_token]
            active = [record.as_dict() for record in filtered if _record_effectively_active(config, record)]
            active.sort(key=lambda row: str(row.get("last_update_at") or row.get("created_at") or ""), reverse=True)
            recent = [record.as_dict() for record in filtered if record.status in FINISHED_STATUSES]
            recent.sort(key=lambda row: str(row.get("merged_at") or row.get("last_update_at") or row.get("created_at") or ""), reverse=True)
            recent = recent[:8]
    else:
        records = _records_from_registry(_load_registry(config.registry_path))
        records, removed = _cleanup_records(config, records)
        if removed:
            _save_registry(config.registry_path, records)
        filtered = [record for record in records if not role_token or record.parent_role == role_token]
        active = [record.as_dict() for record in filtered if _record_effectively_active(config, record)]
        active.sort(key=lambda row: str(row.get("last_update_at") or row.get("created_at") or ""), reverse=True)
        recent = [record.as_dict() for record in filtered if record.status in FINISHED_STATUSES]
        recent.sort(key=lambda row: str(row.get("merged_at") or row.get("last_update_at") or row.get("created_at") or ""), reverse=True)
        recent = recent[:8]

    anomaly_after_seconds = max(300, int(os.environ.get("FC_PLANNER_NATIVE_DELTA_STALE_SECONDS", "1800")))
    now = _now()
    anomalies: list[dict[str, Any]] = []
    known_ids = {str(row.get("subagent_id", "")).strip() for row in active + recent if str(row.get("subagent_id", "")).strip()}
    for row in active:
        subagent_id = str(row.get("subagent_id", "")).strip()
        backend = str(row.get("backend", "")).strip().lower()
        target_agent_id = str(row.get("target_agent_id", "")).strip()
        monitor_agent_id = str(row.get("monitor_agent_id", "")).strip()
        last_update_at = _parse_iso(str(row.get("last_update_at", "")).strip()) or _parse_iso(str(row.get("created_at", "")).strip())
        age_seconds = int((now - last_update_at).total_seconds()) if last_update_at else -1
        delta = _normalize_meaningful_delta(row.get("last_meaningful_delta"), fallback="none")
        if backend == "openclaw" and subagent_id and not _subagent_launcher_alive(subagent_id):
            anomalies.append({"code": "agent_referenced_missing", "subagent_id": subagent_id})
        if monitor_agent_id and target_agent_id and target_agent_id not in known_ids:
            anomalies.append({"code": "monitor_without_target", "subagent_id": subagent_id, "target_agent_id": target_agent_id})
        if age_seconds >= anomaly_after_seconds and delta == "none":
            anomalies.append({"code": "no_meaningful_delta", "subagent_id": subagent_id, "age_s": age_seconds})

    recent_success_count = sum(1 for row in recent if str(row.get("status", "")).strip().lower() in SUCCESS_RESULT_STATUSES)
    recent_failed_count = sum(1 for row in recent if str(row.get("status", "")).strip().lower() == "failed")
    recent_blocked_count = sum(1 for row in recent if str(row.get("status", "")).strip().lower() in BLOCKED_RESULT_STATUSES)
    recent_fallback_like_count = sum(1 for row in recent if str(row.get("backend", "")).strip().lower() == "qwen")
    recent_invalid_result_count = sum(1 for row in recent if "invalid_subagent_result" in str(row.get("blocking_issue", "")).strip().lower())
    recent_timeout_like_count = sum(1 for row in recent if "timeout" in str(row.get("blocking_issue", "")).strip().lower())
    monitor_active_count = sum(
        1
        for row in active
        if str(row.get("monitor_agent_id", "")).strip() or str(row.get("role", "")).strip().lower() == "monitor"
    )
    recent_by_role: dict[str, dict[str, int]] = {}
    for row in recent:
        role_name = str(row.get("role", row.get("target_role", "unknown"))).strip() or "unknown"
        bucket = recent_by_role.setdefault(role_name, {"total": 0, "success": 0, "failed": 0, "blocked": 0, "fallback_like": 0})
        bucket["total"] += 1
        status_token = str(row.get("status", "")).strip().lower()
        if status_token in SUCCESS_RESULT_STATUSES:
            bucket["success"] += 1
        elif status_token == "failed":
            bucket["failed"] += 1
        elif status_token in BLOCKED_RESULT_STATUSES:
            bucket["blocked"] += 1
        if str(row.get("backend", "")).strip().lower() == "qwen":
            bucket["fallback_like"] += 1

    latest = active[0] if active else (recent[0] if recent else {})
    active_invalid_routes = [] if event_store_primary else _active_invalid_result_routes(config)
    latest_invalid_route = active_invalid_routes[0] if active_invalid_routes else {}
    latest_status = str(latest.get("status", "")).strip().lower()
    latest_backend = str(latest.get("backend", "")).strip().lower()
    latest_failure_mode = str(latest.get("blocking_issue", "")).strip().lower() or "none"
    latest_last_meaningful_delta = _normalize_meaningful_delta(latest.get("last_meaningful_delta"), fallback="none")
    if _is_invalid_result_reason(latest_failure_mode):
        latest_last_meaningful_delta = "none"
    monitor_without_target_count = sum(1 for item in anomalies if str(item.get("code", "")).strip() == "monitor_without_target")
    collect_timeout_without_agents = any(
        str(item.get("code", "")).strip() == "collect_timeout_without_agents" for item in anomalies
    )
    backend_route_reason = str(latest_invalid_route.get("route_reason", "none") or "none").strip() or "none"
    backend_cooldown_until = str(latest_invalid_route.get("cooldown_until", "") or "").strip()
    degraded_backend = latest_backend == "qwen" or backend_route_reason != "none"
    if degraded_backend:
        planner_state = "degraded_backend"
    elif monitor_active_count > 0:
        planner_state = "monitoring"
    elif active:
        planner_state = "waiting_on_agents"
    elif _is_invalid_result_reason(latest_failure_mode):
        planner_state = "blocked"
    elif anomalies or latest_status in BLOCKED_RESULT_STATUSES.union({"failed"}):
        planner_state = "blocked"
    else:
        planner_state = "working"
    success_denominator = recent_success_count + recent_failed_count + recent_blocked_count
    recent_success_rate = (recent_success_count / success_denominator) if success_denominator > 0 else 1.0
    return {
        "ok": True,
        "enabled": config.enabled,
        "cron_planner_only": config.cron_planner_only,
        "legacy_compat_only": True,
        "decision_capable": False,
        "storage_plane": "runtime_mutable",
        "provider_policy_plane": "model_plane",
        "runtime_truth_source": runtime_truth_source,
        "event_store_primary": event_store_primary,
        "registry_secondary_only": True,
        "role": role_token,
        "active_count": len(active),
        "max_active": config.max_active,
        "active": active,
        "recent": recent,
        "recent_total": len(recent),
        "recent_success_count": recent_success_count,
        "recent_failed_count": recent_failed_count,
        "recent_blocked_count": recent_blocked_count,
        "recent_fallback_like_count": recent_fallback_like_count,
        "recent_invalid_result_count": recent_invalid_result_count,
        "recent_timeout_like_count": recent_timeout_like_count,
        "recent_success_rate": recent_success_rate,
        "recent_by_role": recent_by_role,
        "latest_status": latest_status,
        "latest_backend": latest_backend,
        "latest_owner_task_id": str(latest.get("owner_task_id", "")).strip(),
        "latest_update_at": str(latest.get("last_update_at", "")).strip(),
        "latest_last_meaningful_delta": latest_last_meaningful_delta,
        "latest_monitor_agent_id": str(latest.get("monitor_agent_id", "")).strip(),
        "latest_purpose": str(latest.get("purpose", "")).strip(),
        "latest_fallback_like": latest_backend == "qwen",
        "latest_failure_mode": latest_failure_mode,
        "monitor_active_count": monitor_active_count,
        "monitoring_count": monitor_active_count,
        "monitor_without_target_count": monitor_without_target_count,
        "degraded_backend": degraded_backend,
        "backend_route_reason": backend_route_reason,
        "backend_cooldown_until": backend_cooldown_until,
        "last_meaningful_delta": latest_last_meaningful_delta,
        "collect_timeout_without_agents": collect_timeout_without_agents,
        "planner_state": planner_state,
        "status": planner_state,
        "anomalies": anomalies[:8],
        "compat_registry_present": False if event_store_primary else config.registry_path.exists(),
        "compat_events_present": False if event_store_primary else config.events_path.exists(),
        "compat_results_present": False if event_store_primary else config.results_dir.exists(),
        "events_path": "secondary_compat_only",
        "registry_path": "secondary_compat_only",
        "secondary_registry_path": "secondary_compat_only",
        "active_storage_root": "secondary_compat_only" if event_store_primary else _runtime_relpath(config.registry_path.parent, config.root),
    }


def prompt_context(config: PlannerSubagentConfig, role: str) -> str:
    snapshot = status_snapshot(config, role)
    active = snapshot.get("active", [])
    recent = snapshot.get("recent", [])
    max_active = int(snapshot.get("max_active", 0) or 0)
    active_count = int(snapshot.get("active_count", 0) or 0)
    open_slots = max(0, max_active - active_count)
    active_bits = [f"{item.get('target_role') or item.get('role')}:{item.get('owner_task_id')}:{item.get('status')}" for item in active[:3]]
    recent_bits = [f"{item.get('target_role') or item.get('role')}:{item.get('owner_task_id')}:{_compact(item.get('summary', ''), 80)}" for item in recent[-3:]]
    return (
        f"planner_orchestrator_enabled={1 if config.enabled else 0} | "
        f"planner_cron_only={1 if config.cron_planner_only else 0} | "
        f"planner_subagent_storage_plane=runtime_mutable | "
        f"planner_subagent_open_slots={open_slots} | "
        f"planner_subagent_active={'; '.join(active_bits) if active_bits else 'none'} | "
        f"planner_subagent_recent={'; '.join(recent_bits) if recent_bits else 'none'}"
    )


def _trigger_runtime_collect(config: PlannerSubagentConfig, owner_task_id: str, target_role: str) -> None:
    runtime_actions_path = config.root / "platform" / "automation" / "runtime" / "planner" / "planner_runtime_actions.py"
    if not runtime_actions_path.exists():
        return
    cmd = [
        os.environ.get("PYTHON", "python3"),
        str(runtime_actions_path),
        "--root",
        str(config.root),
        "--role",
        "planner",
        "--source",
        "planner_subagent_manager",
        "--backend",
        "auto",
        "--collect-only",
        "--owner-task-id",
        str(owner_task_id or "").strip(),
        "--target-role",
        canonical_role(target_role),
    ]
    try:
        subprocess.run(
            cmd,
            cwd=str(config.root),
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except Exception:
        return


def _trigger_bridge_collect(config: PlannerSubagentConfig, owner_task_id: str, target_role: str) -> None:
    _trigger_runtime_collect(config, owner_task_id, target_role)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Planner-owned Codex subagent manager")
    parser.add_argument("--root", default=str(Path.cwd()))
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--role", required=True)
    p_plan.add_argument("--target-role", required=True)
    p_plan.add_argument("--owner-task-id", required=True)
    p_plan.add_argument("--task-kind", default="delivery")

    p_run = sub.add_parser("run")
    p_run.add_argument("--role", required=True)
    p_run.add_argument("--target-role", required=True)
    p_run.add_argument("--owner-task-id", required=True)
    p_run.add_argument("--task-kind", default="delivery")
    p_run.add_argument("--message", required=True)
    p_run.add_argument("--ttl-min", type=int, default=0)
    p_run.add_argument("--backend", default="auto", choices=["auto", "codex_exec", "mock"])
    p_run.add_argument("--timeout-seconds", type=int, default=240)
    p_run.add_argument("--subagent-id", default="")

    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--role", required=True)
    p_collect.add_argument("--subagent-id", default="")
    p_collect.add_argument("--owner-task-id", default="")
    p_collect.add_argument("--mark-merged", action="store_true")

    sub.add_parser("cleanup")

    p_status = sub.add_parser("status")
    p_status.add_argument("--role", default="")

    p_prompt = sub.add_parser("prompt-context")
    p_prompt.add_argument("--role", required=True)
    return parser


def _canonical_runtime_root(root: Path) -> Path:
    try:
        if CANONICAL_VM_ROOT.exists() and (CANONICAL_VM_ROOT / "platform").is_dir() and (CANONICAL_VM_ROOT / "scripts").is_dir():
            if str(root).startswith(str(SHARED_VM_ROOT)):
                return CANONICAL_VM_ROOT
    except Exception:
        pass
    return root


def _runtime_relpath(path: Path, root: Path) -> str:
    candidate_path = Path(path)
    candidate_root = Path(root)
    try:
        if str(candidate_path).startswith(str(SHARED_VM_ROOT)):
            candidate_path = CANONICAL_VM_ROOT / candidate_path.relative_to(SHARED_VM_ROOT)
        elif str(candidate_path).startswith(str(CANONICAL_VM_ROOT)):
            candidate_path = CANONICAL_VM_ROOT / candidate_path.relative_to(CANONICAL_VM_ROOT)
    except Exception:
        candidate_path = Path(path)
    try:
        if str(candidate_root).startswith(str(SHARED_VM_ROOT)):
            candidate_root = CANONICAL_VM_ROOT / candidate_root.relative_to(SHARED_VM_ROOT)
        elif str(candidate_root).startswith(str(CANONICAL_VM_ROOT)):
            candidate_root = CANONICAL_VM_ROOT / candidate_root.relative_to(CANONICAL_VM_ROOT)
    except Exception:
        candidate_root = Path(root)
    try:
        return str(candidate_path.relative_to(candidate_root))
    except Exception:
        return str(candidate_path)


def main() -> int:
    args = build_parser().parse_args()
    root = _canonical_runtime_root(Path(args.root).expanduser().resolve())
    config = _load_config(root)

    if args.cmd == "plan":
        print(json.dumps(plan_subagent(config, args.role, args.target_role, args.owner_task_id, args.task_kind), ensure_ascii=True))
        return 0
    if args.cmd == "run":
        rc, payload = run_subagent(
            config,
            role=args.role,
            target_role=args.target_role,
            owner_task_id=args.owner_task_id,
            task_kind=args.task_kind,
            message=args.message,
            ttl_min=args.ttl_min,
            backend=args.backend,
            timeout_seconds=args.timeout_seconds,
            subagent_id_override=args.subagent_id,
        )
        print(json.dumps(payload, ensure_ascii=True))
        return rc
    if args.cmd == "collect":
        rc, payload = collect_subagent(config, args.role, args.subagent_id, args.owner_task_id, args.mark_merged)
        print(json.dumps(payload, ensure_ascii=True))
        return rc
    if args.cmd == "cleanup":
        print(json.dumps(cleanup_subagents(config), ensure_ascii=True))
        return 0
    if args.cmd == "status":
        print(json.dumps(status_snapshot(config, args.role), ensure_ascii=True))
        return 0
    if args.cmd == "prompt-context":
        print(prompt_context(config, args.role))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
