#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from worker_manager import _ensure_agent as _ensure_openclaw_agent
from worker_manager import _openclaw_env
from worker_manager import shutil_which


ACTIVE_STATUSES = {"spawned", "running"}
FINISHED_STATUSES = {"completed", "failed", "merged"}
SUCCESS_RESULT_STATUSES = {"completed", "done", "pass", "ok", "success", "merged"}
ALLOWED_PARENT_ROLES = {"planner"}
DEFAULT_MANAGED_ROLES = ("dev", "admin", "scrum_master")
ROLE_MODELS = {
    "dev": ("gpt-5.4", "high", "workspace-write"),
    "admin": ("gpt-5.4", "medium", "workspace-write"),
    "scrum_master": ("gpt-5.3-codex-spark", "low", "read-only"),
}
ROLE_TASK_KINDS = {
    "dev": {"delivery", "implementation", "verification", "targeted_fix"},
    "admin": {"runtime", "reconcile", "takeover", "repair"},
    "scrum_master": {"flow", "coordination", "unblock", "starvation"},
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


def _openclaw_cli_model(model: str) -> str:
    token = str(model or "").strip()
    if not token:
        return "codex-cli/gpt-5.4"
    if "/" in token:
        return token
    return f"codex-cli/{token}"


def _openclaw_runtime_model(model: str, sandbox: str) -> str:
    token = str(model or "").strip() or "gpt-5.4"
    if "/" in token:
        return token
    if str(sandbox or "").strip().lower() == "workspace-write":
        return f"codex-cli-write/{token}"
    return f"codex-cli/{token}"


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


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
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
    proc = subprocess.run(
        ["openclaw", "agents", "list", "--json"],
        text=True,
        capture_output=True,
        check=False,
        env=_openclaw_env(),
    )
    if proc.returncode != 0:
        return set()
    try:
        payload = json.loads(proc.stdout or "[]")
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


def _extract_openclaw_payload_text(raw_text: str) -> tuple[str, str]:
    text = (raw_text or "").strip()
    if not text:
        return "", ""
    try:
        payload = json.loads(text)
    except Exception:
        return text, ""

    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, dict):
        payloads = result.get("payloads")
        if isinstance(payloads, list):
            text_candidates = []
            for item in payloads:
                if isinstance(item, dict):
                    candidate = item.get("text")
                    if isinstance(candidate, str) and candidate.strip():
                        text_candidates.append(candidate.strip())
            if text_candidates:
                meta = result.get("meta")
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
        elif isinstance(obj, str):
            candidates.append(obj)

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
    managed_roles: set[str]


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
        }


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
        return {
            "subagent_id": self.subagent_id,
            "target_role": self.target_role,
            "owner_task_id": self.owner_task_id,
            "parent_role": self.parent_role,
            "task_kind": self.task_kind,
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
            "metadata": self.metadata,
            "merged_at": self.merged_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerSubagentRecord":
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
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {},
            merged_at=str(payload.get("merged_at", "")).strip(),
        )


def _load_config(root: Path) -> PlannerSubagentConfig:
    cfg_path = root / "platform" / "config" / "runner" / "runner.v1.yaml"
    if not cfg_path.exists():
        cfg_path = root / "platform" / "config" / "runner" / "runner_config.v1.yaml"
    cfg = _read_json(cfg_path, {})
    features = cfg.get("features", {}) if isinstance(cfg, dict) else {}
    orchestrator = features.get("planner_orchestrator", {}) if isinstance(features, dict) else {}
    enabled = str(os.environ.get("FC_PLANNER_ORCHESTRATOR_ENABLED", orchestrator.get("enabled", 0))).strip() not in {"0", "false", "False", ""}
    cron_planner_only = str(os.environ.get("FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY", orchestrator.get("cron_planner_only", 0))).strip() not in {"0", "false", "False", ""}
    max_active = int(os.environ.get("FC_PLANNER_ORCHESTRATOR_MAX_ACTIVE", orchestrator.get("max_active", 3)) or 3)
    default_ttl_min = int(os.environ.get("FC_PLANNER_ORCHESTRATOR_DEFAULT_TTL_MIN", orchestrator.get("default_ttl_min", 45)) or 45)
    retry_max = int(os.environ.get("FC_PLANNER_ORCHESTRATOR_RETRY_MAX", orchestrator.get("retry_max", 2)) or 2)
    backend = str(os.environ.get("FC_PLANNER_ORCHESTRATOR_BACKEND", orchestrator.get("backend", "codex_exec")) or "codex_exec").strip().lower()
    raw_roles = os.environ.get("FC_PLANNER_ORCHESTRATOR_MANAGED_ROLES", "")
    if raw_roles.strip():
        managed_roles = {canonical_role(tok) for tok in raw_roles.split(",") if tok.strip()}
    else:
        cfg_roles = orchestrator.get("managed_roles", list(DEFAULT_MANAGED_ROLES))
        if not isinstance(cfg_roles, list):
            cfg_roles = list(DEFAULT_MANAGED_ROLES)
        managed_roles = {canonical_role(tok) for tok in cfg_roles if str(tok).strip()}
    orch_dir = root / "docs" / "operations" / "orchestrator"
    return PlannerSubagentConfig(
        root=root,
        registry_path=orch_dir / "planner-subagents-registry.json",
        events_path=orch_dir / "planner-subagents-events.jsonl",
        results_dir=orch_dir / "planner-subagents-results",
        enabled=enabled,
        cron_planner_only=cron_planner_only,
        max_active=max(1, max_active),
        default_ttl_min=max(5, default_ttl_min),
        retry_max=max(0, retry_max),
        backend=backend or "codex_exec",
        managed_roles=managed_roles or set(DEFAULT_MANAGED_ROLES),
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


def _save_registry(path: Path, records: list[PlannerSubagentRecord]) -> None:
    _write_json(path, {"updated_at": _iso(), "subagents": [record.as_dict() for record in records]})


def _emit_event(config: PlannerSubagentConfig, event: str, record: PlannerSubagentRecord, extra: dict[str, Any] | None = None) -> None:
    payload = {
        "ts": _iso(),
        "event": event,
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


def _active_count(records: list[PlannerSubagentRecord]) -> int:
    return sum(1 for record in records if record.status in ACTIVE_STATUSES)


def _cleanup_records(config: PlannerSubagentConfig, records: list[PlannerSubagentRecord], now: datetime | None = None) -> tuple[list[PlannerSubagentRecord], list[str]]:
    now = now or _now()
    stale_active_seconds = max(300, int(os.environ.get("FC_PLANNER_SUBAGENT_STALE_ACTIVE_SECONDS", "600")))
    active_openclaw_ids = _openclaw_agent_ids()
    kept: list[PlannerSubagentRecord] = []
    removed: list[str] = []
    for record in records:
        result_path = config.results_dir / f"{record.subagent_id}.result.json"
        last_seen = _parse_iso(record.last_update_at) or _parse_iso(record.created_at)
        if (
            record.status in ACTIVE_STATUSES
            and record.backend == "openclaw"
            and record.subagent_id not in active_openclaw_ids
            and not result_path.exists()
        ):
            _emit_event(
                config,
                "planner_subagent_cleanup",
                record,
                {"reason": "openclaw_agent_missing"},
            )
            removed.append(record.subagent_id)
            continue
        if (
            record.status in ACTIVE_STATUSES
            and not result_path.exists()
            and last_seen is not None
            and int((now - last_seen).total_seconds()) >= stale_active_seconds
        ):
            _emit_event(
                config,
                "planner_subagent_cleanup",
                record,
                {"reason": f"stale_active_no_result>{stale_active_seconds}s"},
            )
            removed.append(record.subagent_id)
            continue
        expires_at = _parse_iso(record.expires_at)
        if expires_at is None or expires_at > now:
            kept.append(record)
            continue
        _emit_event(config, "planner_subagent_cleanup", record, {"reason": "ttl_expired"})
        if record.backend == "openclaw":
            _openclaw_delete_agent(record.subagent_id)
        removed.append(record.subagent_id)
    return kept, removed


def _find_duplicate(records: list[PlannerSubagentRecord], target_role: str, owner_task_id: str) -> PlannerSubagentRecord | None:
    for record in records:
        if record.target_role == target_role and record.owner_task_id == owner_task_id and record.status in ACTIVE_STATUSES:
            return record
    return None


def _role_runtime_defaults(config: PlannerSubagentConfig, target_role: str) -> tuple[str, str, str]:
    cfg_path = config.root / "platform" / "config" / "runner" / "runner.v1.yaml"
    if not cfg_path.exists():
        cfg_path = config.root / "platform" / "config" / "runner" / "runner_config.v1.yaml"
    cfg = _read_json(cfg_path, {})
    roles = cfg.get("roles", {}) if isinstance(cfg, dict) else {}
    role_cfg = roles.get(target_role, {}) if isinstance(roles, dict) else {}
    model_default, thinking_default, sandbox_default = ROLE_MODELS.get(target_role, ("gpt-5.4", "medium", "workspace-write"))
    model = str(role_cfg.get("model", model_default) or model_default).strip()
    thinking = str(role_cfg.get("thinking", thinking_default) or thinking_default).strip()
    sandbox = "read-only" if target_role == "scrum_master" else sandbox_default
    return model, thinking, sandbox


def _build_prompt(target_role: str, owner_task_id: str, task_kind: str, message: str) -> str:
    common = (
        "PLANNER_ORCHESTRATED_SUBAGENT=1\n"
        f"TARGET_ROLE={target_role}\n"
        f"OWNER_TASK_ID={owner_task_id}\n"
        f"TASK_KIND={task_kind}\n"
        "Rules:\n"
        "- Planner remains the only source of orchestration truth.\n"
        "- Treat planner-only scheduling as current reality: planner is the sole scheduled role; dev/admin/scrum_master are planner capabilities.\n"
        "- Do not call parallel_workstream.py claim/complete/handoff.\n"
        "- Do not update queue/workboard/contracts directly.\n"
        "- You may read the repo, edit files only if your role allows it, run bounded targeted commands, and return structured evidence.\n"
        "- Keep scope narrow to the owner task and the planner instruction.\n"
        "- If blocked, say exactly what the planner should do next.\n"
        "- Return ONLY one JSON object with keys: status, summary, root_cause, fix_applied, artifact, verify, files_touched, tests_run, commit_sha, architecture_check, vision_alignment, recommended_next, blocking_issue.\n"
        "- If no file or test applies, use 'none' or 'SKIP(reason)' explicitly.\n"
        f"Planner instruction: {message.strip()}\n"
    )
    if target_role == "dev":
        return common + (
            "Dev mission:\n"
            "- Produce the smallest concrete patch or verification step that advances delivery.\n"
            "- Do not inspect monitor, doctor, or unrelated architecture docs unless the task is explicitly blocked by runtime truth.\n"
            "- Do not broaden the task into a repo-wide audit.\n"
            "- Prefer one minimal vertical slice tied directly to the owner task notes.\n"
            "- Prefer targeted tests only.\n"
            "- If you changed code or config, commit it and return the real commit_sha.\n"
            "- verify must include before=..., after=..., test=...\n"
            "- architecture_check must include layer=..., imports_ok=..., path_target=...\n"
            "- vision_alignment must include batch=..., target=..., impact=...\n"
            "- Return files_touched and tests_run precisely.\n"
        )
    if target_role == "admin":
        return common + (
            "Admin mission:\n"
            "- Use runtime probes only when they are directly required.\n"
            "- Repair runtime truth, stale locks, stale blockers, or broken execution paths.\n"
            "- Prefer reversible fixes and concrete verification.\n"
            "- If the issue is not runtime/infra, point planner back to dev or scrum_master.\n"
        )
    return common + (
        "Scrum mission:\n"
        "- Act as unblock-first coordinator.\n"
        "- Do not inspect the full repo or launch technical workers.\n"
        "- Do not edit files or claim tasks.\n"
        "- Return one precise unblock action or escalation.\n"
    )


def _parse_result_payload(raw_text: str, subagent_id: str, target_role: str, owner_task_id: str, parent_role: str, task_kind: str, backend: str) -> PlannerSubagentResult:
    text = (raw_text or "").strip()
    payload: dict[str, Any] = {}
    if text:
        try:
            payload = json.loads(text)
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}
        if not payload:
            markers = ('{"status"', '{\n"status"')
            start = -1
            for marker in markers:
                pos = text.rfind(marker)
                if pos > start:
                    start = pos
            if start >= 0:
                candidate = text[start:].strip()
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        payload = parsed
                except Exception:
                    payload = {}
    status = str(payload.get("status", "failed")).strip() or "failed"
    summary = _compact(payload.get("summary", text or "no_summary"), 260)
    root_cause = _compact(payload.get("root_cause", "none"), 220)
    fix_applied = _compact(payload.get("fix_applied", "none"), 220)
    artifact = _compact(payload.get("artifact", "none"), 220)
    verify = _compact(payload.get("verify", "none"), 220)
    files_touched = _compact(payload.get("files_touched", "none"), 220)
    tests_run = _compact(payload.get("tests_run", "SKIP(no_tests)"), 220)
    commit_sha = _compact(payload.get("commit_sha", "none"), 120)
    architecture_check = _compact(payload.get("architecture_check", "none"), 220)
    vision_alignment = _compact(payload.get("vision_alignment", "none"), 220)
    recommended_next = _compact(payload.get("recommended_next", "none"), 220)
    blocking_issue = _compact(payload.get("blocking_issue", "none"), 160)
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
    chosen_backend = str(backend_override or config.backend or "codex_exec").strip().lower()
    if chosen_backend == "auto":
        chosen_backend = config.backend
    records = _records_from_registry(_load_registry(config.registry_path))
    records, _ = _cleanup_records(config, records)
    duplicate = _find_duplicate(records, target, owner_task_id)
    active_count = _active_count(records)
    allowed = True
    reason = "allowed"
    if parent_role not in ALLOWED_PARENT_ROLES:
        allowed = False
        reason = f"parent_role_forbidden:{parent_role}"
    elif not config.enabled:
        allowed = False
        reason = "planner_orchestrator_disabled"
    elif target not in config.managed_roles:
        allowed = False
        reason = f"target_role_not_managed:{target}"
    elif task_kind not in ROLE_TASK_KINDS.get(target, set()):
        allowed = False
        reason = f"task_kind_not_allowed:{target}:{task_kind}"
    elif duplicate is not None:
        allowed = False
        reason = f"duplicate_active:{duplicate.subagent_id}"
    elif active_count >= config.max_active:
        allowed = False
        reason = f"max_active_reached:{active_count}/{config.max_active}"
    elif chosen_backend == "codex_exec" and not _codex_available():
        allowed = False
        reason = "codex_missing"
    elif chosen_backend == "openclaw" and not _openclaw_available():
        allowed = False
        reason = "openclaw_missing"
    elif chosen_backend not in {"codex_exec", "openclaw", "mock"}:
        allowed = False
        reason = f"unsupported_backend:{chosen_backend}"
    model, thinking, sandbox = _role_runtime_defaults(config, target)
    return {
        "allowed": allowed,
        "reason": reason,
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
        backend=backend,
        metadata={"model": plan["model"], "thinking": plan["thinking"], "sandbox": plan["sandbox"]},
    )
    records.append(record)
    _save_registry(config.registry_path, records)
    _emit_event(config, "planner_subagent_spawn", record, {"task_kind": task_kind})

    chosen_backend = plan["backend"]
    record.status = "running"
    record.last_update_at = _iso()
    _save_registry(config.registry_path, records)
    _emit_event(config, "planner_subagent_start", record, {"backend": chosen_backend})

    stdout = ""
    stderr = ""
    rc = 0
    backend_ref = subagent_id
    prompt = _build_prompt(plan["target_role"], owner_task_id, task_kind, message)

    if chosen_backend == "mock":
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
    elif chosen_backend == "openclaw":
        openclaw_model = _openclaw_runtime_model(plan["model"], plan["sandbox"])
        ok, backend_ref = _ensure_openclaw_agent(
            subagent_id,
            config.root,
            openclaw_model,
            workspace_key=f"planner-{plan['target_role']}",
            thinking=plan["thinking"],
        )
        if not ok:
            rc = 5
            stderr = backend_ref or "openclaw_agent_create_failed"
            backend_ref = subagent_id
        else:
            try:
                proc = subprocess.run(
                    [
                        "openclaw",
                        "agent",
                        "--agent",
                        subagent_id,
                        "--json",
                        "--thinking",
                        str(plan["thinking"]),
                        "--timeout",
                        str(max(30, timeout_seconds)),
                        "--message",
                        prompt,
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    env=_openclaw_env(),
                    timeout=max(30, timeout_seconds + 15),
                )
                rc = proc.returncode
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
            except subprocess.TimeoutExpired as exc:
                rc = 124
                stdout = str(exc.stdout or "")
                stderr = str(exc.stderr or "") or f"openclaw_timeout_after_{max(30, timeout_seconds + 15)}s"
    elif chosen_backend == "codex_exec":
        with tempfile.TemporaryDirectory(prefix="planner-subagent-") as td:
            tmpdir = Path(td)
            schema_path = tmpdir / "schema.json"
            out_path = tmpdir / "last_message.json"
            schema_path.write_text(json.dumps(RESULT_SCHEMA, ensure_ascii=True), encoding="utf-8")
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
                "--sandbox",
                str(plan["sandbox"]),
                "-m",
                str(plan["model"]),
                "-c",
                f'model_reasoning_effort="{plan["thinking"]}"',
            ]
            if plan["sandbox"] == "workspace-write":
                cmd.append("--full-auto")
            try:
                proc = subprocess.run(
                    cmd + [prompt],
                    text=True,
                    capture_output=True,
                    check=False,
                    cwd=str(config.root),
                    timeout=max(30, timeout_seconds),
                )
                rc = proc.returncode
                stdout = out_path.read_text(encoding="utf-8", errors="ignore") if out_path.exists() else (proc.stdout or "")
                stderr = proc.stderr or ""
            except subprocess.TimeoutExpired as exc:
                rc = 124
                stdout = out_path.read_text(encoding="utf-8", errors="ignore") if out_path.exists() else str(exc.stdout or "")
                stderr = str(exc.stderr or "") or f"codex_exec_timeout_after_{max(30, timeout_seconds)}s"
            backend_ref = f"codex_exec:{subagent_id}"
    else:
        rc = 5
        stderr = f"unsupported_backend:{chosen_backend}"

    config.results_dir.mkdir(parents=True, exist_ok=True)
    raw_path = config.results_dir / f"{subagent_id}.raw.txt"
    raw_path.write_text(stdout if stdout else stderr, encoding="utf-8")
    result_source = stdout if stdout else stderr
    if chosen_backend == "openclaw" and stdout:
        extracted_text, extracted_ref = _extract_openclaw_payload_text(stdout)
        result_source = extracted_text or stdout
        if extracted_ref:
            backend_ref = extracted_ref
    result = _parse_result_payload(
        result_source,
        subagent_id,
        plan["target_role"],
        owner_task_id,
        plan["parent_role"],
        task_kind,
        chosen_backend,
    )
    result.raw_output_ref = str(raw_path.relative_to(config.root))
    result.backend_ref = backend_ref
    result.started_at = record.created_at
    result.finished_at = _iso()
    if rc != 0:
        result.status = "failed"
        if result.blocking_issue == "none":
            result.blocking_issue = _compact(stderr or f"{chosen_backend}_rc_{rc}", 160)
        if result.summary == "none":
            result.summary = _compact(stderr or f"{chosen_backend}_failed", 220)
    result_path = config.results_dir / f"{subagent_id}.result.json"
    result_path.write_text(json.dumps(result.as_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    for idx, existing in enumerate(records):
        if existing.subagent_id == subagent_id:
            records[idx].status = result.status
            records[idx].backend = chosen_backend
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
            break
    _save_registry(config.registry_path, records)
    emitted = next((row for row in records if row.subagent_id == subagent_id), record)
    _emit_event(config, "planner_subagent_result", emitted, {"rc": rc, "result_path": str(result_path.relative_to(config.root))})
    payload = result.as_dict()
    payload["ok"] = rc == 0 and str(result.status).strip().lower() in SUCCESS_RESULT_STATUSES
    payload["rc"] = rc
    if chosen_backend == "openclaw":
        payload["model"] = _openclaw_cli_model(plan["model"])
    if stderr:
        payload["stderr"] = _compact(stderr, 220)
    return (0 if payload["ok"] else 6), payload


def collect_subagent(config: PlannerSubagentConfig, role: str, subagent_id: str, owner_task_id: str, mark_merged: bool) -> tuple[int, dict[str, Any]]:
    records = _records_from_registry(_load_registry(config.registry_path))
    target: PlannerSubagentRecord | None = None
    for record in records:
        if subagent_id and record.subagent_id == subagent_id:
            target = record
            break
        if owner_task_id and record.owner_task_id == owner_task_id and record.parent_role == canonical_role(role):
            target = record
    if target is None:
        return 3, {"ok": False, "reason": "subagent_not_found"}
    if canonical_role(role) != target.parent_role:
        return 4, {"ok": False, "reason": "parent_role_mismatch"}
    result_path = config.results_dir / f"{target.subagent_id}.result.json"
    payload = _read_json(result_path, {})
    if not isinstance(payload, dict):
        payload = {}
    if mark_merged:
        for record in records:
            if record.subagent_id == target.subagent_id:
                record.status = "merged"
                record.merged_at = _iso()
                _emit_event(config, "planner_subagent_merge", record, {"merged_by": canonical_role(role)})
                break
        _save_registry(config.registry_path, records)
    payload["ok"] = True
    return 0, payload


def cleanup_subagents(config: PlannerSubagentConfig) -> dict[str, Any]:
    records = _records_from_registry(_load_registry(config.registry_path))
    kept, removed = _cleanup_records(config, records)
    _save_registry(config.registry_path, kept)
    return {"ok": True, "removed": removed, "remaining": len(kept)}


def status_snapshot(config: PlannerSubagentConfig, role: str = "") -> dict[str, Any]:
    records = _records_from_registry(_load_registry(config.registry_path))
    records, removed = _cleanup_records(config, records)
    if removed:
        _save_registry(config.registry_path, records)
    role_token = canonical_role(role) if role else ""
    filtered = [record for record in records if not role_token or record.parent_role == role_token]
    active = [record.as_dict() for record in filtered if record.status in ACTIVE_STATUSES]
    recent = [record.as_dict() for record in filtered if record.status in FINISHED_STATUSES][-8:]
    return {
        "ok": True,
        "enabled": config.enabled,
        "cron_planner_only": config.cron_planner_only,
        "role": role_token,
        "active_count": len(active),
        "max_active": config.max_active,
        "active": active,
        "recent": recent,
        "events_path": str(config.events_path.relative_to(config.root)),
        "registry_path": str(config.registry_path.relative_to(config.root)),
    }


def prompt_context(config: PlannerSubagentConfig, role: str) -> str:
    snapshot = status_snapshot(config, role)
    active = snapshot.get("active", [])
    recent = snapshot.get("recent", [])
    max_active = int(snapshot.get("max_active", 0) or 0)
    active_count = int(snapshot.get("active_count", 0) or 0)
    open_slots = max(0, max_active - active_count)
    active_bits = [f"{item.get('target_role')}:{item.get('owner_task_id')}:{item.get('status')}" for item in active[:3]]
    recent_bits = [f"{item.get('target_role')}:{item.get('owner_task_id')}:{_compact(item.get('summary', ''), 80)}" for item in recent[-3:]]
    return (
        f"planner_orchestrator_enabled={1 if config.enabled else 0} | "
        f"planner_cron_only={1 if config.cron_planner_only else 0} | "
        f"planner_subagent_open_slots={open_slots} | "
        f"planner_subagent_active={'; '.join(active_bits) if active_bits else 'none'} | "
        f"planner_subagent_recent={'; '.join(recent_bits) if recent_bits else 'none'}"
    )


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
    p_run.add_argument("--backend", default="auto", choices=["auto", "openclaw", "codex_exec", "mock"])
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


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
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
