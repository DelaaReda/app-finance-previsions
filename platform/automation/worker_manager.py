#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from openclaw_control_plane import sync_canonical_skills
from worker_contract import (
    ALLOWED_PARENT_ROLES,
    WorkerRecord,
    WorkerResult,
    canonical_role,
    default_result_kind,
    default_thinking,
    save_result,
    worker_allowed,
)


ACTIVE_STATUSES = {"spawned", "running"}
FINISHED_STATUSES = {"completed", "failed", "merged"}


@dataclass
class WorkerManagerConfig:
    root: Path
    registry_path: Path
    events_path: Path
    results_dir: Path
    enabled: bool
    max_active: int
    default_ttl_min: int
    retry_max: int
    allowed_roles: set[str]


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


def _compact(text: str, limit: int = 180) -> str:
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


def _load_config(root: Path) -> WorkerManagerConfig:
    cfg_path = root / "platform" / "config" / "runner" / "runner.v1.yaml"
    if not cfg_path.exists():
        cfg_path = root / "platform" / "config" / "runner" / "runner_config.v1.yaml"
    cfg = _read_json(cfg_path, {})
    features = cfg.get("features", {}) if isinstance(cfg, dict) else {}
    workers = features.get("dynamic_workers", {}) if isinstance(features, dict) else {}
    enabled = str(os.environ.get("FC_DYNAMIC_WORKERS_ENABLED", workers.get("enabled", 0))).strip() not in {"0", "false", "False", ""}
    max_active = int(os.environ.get("FC_DYNAMIC_WORKERS_MAX_ACTIVE", workers.get("max_active", 6)) or 6)
    default_ttl_min = int(os.environ.get("FC_DYNAMIC_WORKERS_DEFAULT_TTL_MIN", workers.get("default_ttl_min", 60)) or 60)
    retry_max = int(os.environ.get("FC_DYNAMIC_WORKERS_RETRY_MAX", workers.get("retry_max", 2)) or 2)
    allowed_roles_raw = os.environ.get("FC_DYNAMIC_WORKERS_ALLOWED_ROLES", "")
    if allowed_roles_raw.strip():
        allowed_roles = {canonical_role(tok) for tok in allowed_roles_raw.split(",") if tok.strip()}
    else:
        raw_roles = workers.get("allowed_roles", ["planner", "dev", "admin"])
        if not isinstance(raw_roles, list):
            raw_roles = ["planner", "dev", "admin"]
        allowed_roles = {canonical_role(str(tok)) for tok in raw_roles if str(tok).strip()}
    orch_dir = root / "docs" / "operations" / "orchestrator"
    return WorkerManagerConfig(
        root=root,
        registry_path=orch_dir / "dynamic-workers-registry.json",
        events_path=orch_dir / "dynamic-workers-events.jsonl",
        results_dir=orch_dir / "dynamic-workers-results",
        enabled=enabled,
        max_active=max(1, max_active),
        default_ttl_min=max(5, default_ttl_min),
        retry_max=max(0, retry_max),
        allowed_roles=allowed_roles or set(ALLOWED_PARENT_ROLES),
    )


def _load_registry(path: Path) -> dict[str, Any]:
    payload = _read_json(path, {"workers": [], "updated_at": ""})
    if not isinstance(payload, dict):
        payload = {"workers": [], "updated_at": ""}
    workers = payload.get("workers", [])
    if not isinstance(workers, list):
        workers = []
    payload["workers"] = workers
    return payload


def _save_registry(path: Path, records: list[WorkerRecord]) -> None:
    _write_json(
        path,
        {
            "updated_at": _iso(),
            "workers": [record.as_dict() for record in records],
        },
    )


def _records_from_registry(payload: dict[str, Any]) -> list[WorkerRecord]:
    out: list[WorkerRecord] = []
    for item in payload.get("workers", []):
        if not isinstance(item, dict):
            continue
        out.append(WorkerRecord.from_dict(item))
    return out


def _emit_event(config: WorkerManagerConfig, event: str, record: WorkerRecord, extra: dict[str, Any] | None = None) -> None:
    payload = {
        "ts": _iso(),
        "event": event,
        "worker_id": record.worker_id,
        "worker_type": record.worker_type,
        "parent_role": record.parent_role,
        "owner_task_id": record.owner_task_id,
        "status": record.status,
        "backend": record.backend,
    }
    if extra:
        payload.update(extra)
    _append_jsonl(config.events_path, payload)


def _active_count(records: list[WorkerRecord]) -> int:
    return sum(1 for record in records if record.status in ACTIVE_STATUSES)


def _find_duplicate(records: list[WorkerRecord], parent_role: str, worker_type: str, owner_task_id: str) -> WorkerRecord | None:
    for record in records:
        if (
            record.parent_role == parent_role
            and record.worker_type == worker_type
            and record.owner_task_id == owner_task_id
            and record.status in ACTIVE_STATUSES
        ):
            return record
    return None


def _cleanup_records(config: WorkerManagerConfig, records: list[WorkerRecord], now: datetime | None = None) -> tuple[list[WorkerRecord], list[str]]:
    now = now or _now()
    kept: list[WorkerRecord] = []
    removed: list[str] = []
    for record in records:
        expires_at = _parse_iso(record.expires_at)
        if expires_at is None or expires_at > now:
            kept.append(record)
            continue
        _emit_event(config, "worker_cleanup", record, {"reason": "ttl_expired"})
        if record.backend == "openclaw" and record.backend_ref and shutil_which("openclaw"):
            subprocess.run(
                ["openclaw", "agents", "delete", record.backend_ref],
                text=True,
                capture_output=True,
                check=False,
                env=_openclaw_env(),
            )
        removed.append(record.worker_id)
    return kept, removed


def shutil_which(binary: str) -> str:
    from shutil import which

    return which(binary) or ""


def _openclaw_cli_model(model: str) -> str:
    token = str(model or "").strip()
    if not token:
        return "codex-cli/gpt-5.4"
    if "/" in token:
        return token
    return f"codex-cli/{token}"


OPENCLAW_CAPABILITY_CONFIG_TEMPLATE = """model = "{model}"
model_reasoning_effort = "{thinking}"

[features]
multi_agent = true
apps = true
js_repl = true
prevent_idle_sleep = true
"""
OPENCLAW_CAPABILITY_SOUL = """# SOUL.md

You are a bounded planner-owned capability executor.

Core rules:
- Stay narrow and task-focused.
- Prefer direct implementation over exploration.
- Do not ask bootstrap or identity questions.
- Do not create your own orchestration layer.
"""
OPENCLAW_CAPABILITY_USER = """# USER.md

- You are helping the planner orchestrator of the analyse-financiere project.
- This workspace is ephemeral and task-scoped.
"""
OPENCLAW_CAPABILITY_AGENTS = """# AGENTS.md

This workspace is a minimal capability runner for planner-owned execution.

Rules:
1. Do not perform bootstrap or identity setup.
2. Do not spawn subagents, explorers, or workers.
3. Do not read MEMORY.md or daily memory unless the task explicitly asks for it.
4. Read only the files directly required by the task prompt.
5. Prefer one minimal patch plus targeted verification.
6. Return only the final structured result requested by the prompt.
"""
OPENCLAW_CAPABILITY_IDENTITY = """# IDENTITY.md

name: Planner Capability
role: bounded execution helper
"""
OPENCLAW_CAPABILITY_HEARTBEAT = "HEARTBEAT_OK\n"


def _openclaw_env() -> dict[str, str]:
    env = dict(os.environ)
    desired = str(env.get("OPENCLAW_NODE_OPTIONS", "")).strip() or "--max-old-space-size=1536 --max-semi-space-size=64"
    existing = str(env.get("NODE_OPTIONS", "")).strip()
    if desired not in existing:
        env["NODE_OPTIONS"] = f"{existing} {desired}".strip()
    return env


def _write_text_if_changed(path: Path, content: str) -> None:
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="ignore")
    if existing == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _openclaw_capability_workspace(root: Path, workspace_key: str, model: str, thinking: str = "medium") -> Path:
    safe_key = canonical_role(workspace_key).replace("/", "_") or "shared"
    workspace = root / "logs-codex-runs" / "openclaw-capabilities" / safe_key
    config_path = workspace / ".codex" / "config.toml"
    config_body = OPENCLAW_CAPABILITY_CONFIG_TEMPLATE.format(
        model=str(model or "gpt-5.4").strip(),
        thinking=str(thinking or "medium").strip(),
    )
    _write_text_if_changed(config_path, config_body)
    _write_text_if_changed(workspace / "SOUL.md", OPENCLAW_CAPABILITY_SOUL)
    _write_text_if_changed(workspace / "USER.md", OPENCLAW_CAPABILITY_USER)
    _write_text_if_changed(workspace / "AGENTS.md", OPENCLAW_CAPABILITY_AGENTS)
    _write_text_if_changed(workspace / "IDENTITY.md", OPENCLAW_CAPABILITY_IDENTITY)
    _write_text_if_changed(workspace / "HEARTBEAT.md", OPENCLAW_CAPABILITY_HEARTBEAT)
    bootstrap = workspace / "BOOTSTRAP.md"
    if bootstrap.exists():
        bootstrap.unlink()
    sync_canonical_skills(workspace, root)
    return workspace


def _ensure_agent(
    agent_id: str,
    root: Path,
    model: str,
    workspace_key: str = "shared",
    thinking: str = "medium",
    workspace_path: Path | None = None,
) -> tuple[bool, str]:
    if not shutil_which("openclaw"):
        return False, "openclaw_missing"
    openclaw_model = _openclaw_cli_model(model)
    capability_workspace = (
        Path(workspace_path).expanduser().resolve()
        if workspace_path is not None
        else _openclaw_capability_workspace(root, workspace_key, model, thinking)
    )
    listed = subprocess.run(
        ["openclaw", "agents", "list", "--json"],
        text=True,
        capture_output=True,
        check=False,
        env=_openclaw_env(),
    )
    if listed.returncode == 0:
        try:
            payload = json.loads(listed.stdout or "[]")
        except Exception:
            payload = []
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and str(item.get("id", "")) == agent_id:
                    existing_workspace = str(item.get("workspace", "")).strip()
                    existing_model = str(item.get("model", "")).strip()
                    if existing_workspace == str(capability_workspace) and existing_model == openclaw_model:
                        return True, agent_id
                    subprocess.run(
                        ["openclaw", "agents", "delete", agent_id],
                        text=True,
                        capture_output=True,
                        check=False,
                        env=_openclaw_env(),
                    )
    created = subprocess.run(
        ["openclaw", "agents", "add", agent_id, "--workspace", str(capability_workspace), "--model", openclaw_model, "--non-interactive", "--json"],
        text=True,
        capture_output=True,
        check=False,
        env=_openclaw_env(),
    )
    if created.returncode == 0:
        return True, agent_id
    detail = (created.stderr or created.stdout or "").strip()
    if not detail:
        detail = "openclaw_agent_add_failed"
    return False, _compact(detail, 220)


def _extract_summary(stdout: str) -> tuple[str, str]:
    text = (stdout or "").strip()
    if not text:
        return "none", ""
    try:
        payload = json.loads(text)
    except Exception:
        return _compact(text), ""
    candidates: list[str] = []
    refs: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                lowered = str(key).lower()
                if lowered in {"text", "message", "reply", "summary", "response"} and isinstance(value, str):
                    candidates.append(value)
                elif lowered in {"session_id", "id", "agent_id"} and isinstance(value, str):
                    refs.append(f"{key}={value}")
                else:
                    walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(payload)
    summary = _compact(candidates[-1] if candidates else json.dumps(payload, ensure_ascii=True), 220)
    return summary, ",".join(refs[:4])


def plan_worker(config: WorkerManagerConfig, role: str, worker_type: str, owner_task_id: str, task_kind: str) -> dict[str, Any]:
    parent_role = canonical_role(role)
    allowed, reason = worker_allowed(parent_role, worker_type, task_kind)
    registry = _load_registry(config.registry_path)
    records = _records_from_registry(registry)
    records, _ = _cleanup_records(config, records)
    duplicate = _find_duplicate(records, parent_role, worker_type, owner_task_id)
    active_count = _active_count(records)
    if parent_role not in config.allowed_roles:
        allowed = False
        reason = f"role_not_enabled:{parent_role}"
    if not config.enabled:
        allowed = False
        reason = "dynamic_workers_disabled"
    if duplicate is not None:
        allowed = False
        reason = f"duplicate_active:{duplicate.worker_id}"
    if active_count >= config.max_active:
        allowed = False
        reason = f"max_active_reached:{active_count}/{config.max_active}"
    return {
        "allowed": allowed,
        "reason": reason,
        "parent_role": parent_role,
        "worker_type": worker_type,
        "owner_task_id": owner_task_id,
        "task_kind": task_kind,
        "active_count": active_count,
        "max_active": config.max_active,
        "default_ttl_min": config.default_ttl_min,
        "duplicate_worker_id": duplicate.worker_id if duplicate else "",
        "result_kind": default_result_kind(worker_type),
        "thinking": default_thinking(worker_type),
    }


def run_worker(
    config: WorkerManagerConfig,
    role: str,
    worker_type: str,
    owner_task_id: str,
    task_kind: str,
    message: str,
    ttl_min: int,
    backend: str,
    timeout_seconds: int,
    thinking: str,
    result_kind: str,
) -> tuple[int, dict[str, Any]]:
    plan = plan_worker(config, role, worker_type, owner_task_id, task_kind)
    if not plan["allowed"]:
        return 2, plan

    registry = _load_registry(config.registry_path)
    records = _records_from_registry(registry)
    records, _ = _cleanup_records(config, records)
    worker_id = f"worker_{worker_type}_{uuid.uuid4().hex[:10]}"
    now = _now()
    ttl = max(5, ttl_min or config.default_ttl_min)
    record = WorkerRecord(
        worker_id=worker_id,
        worker_type=worker_type,
        parent_role=canonical_role(role),
        owner_task_id=owner_task_id,
        task_kind=task_kind,
        status="spawned",
        created_at=_iso(now),
        expires_at=_iso(now + timedelta(minutes=ttl)),
        ttl_min=ttl,
        backend=backend,
        result_kind=result_kind or default_result_kind(worker_type),
        message_ref="inline_message",
        metadata={"thinking": thinking or default_thinking(worker_type)},
    )
    records.append(record)
    _save_registry(config.registry_path, records)
    _emit_event(config, "worker_spawn", record, {"task_kind": task_kind})

    stdout = ""
    stderr = ""
    rc = 0
    backend_ref = worker_id
    record.status = "running"
    record.last_update_at = _iso()
    _save_registry(config.registry_path, records)
    _emit_event(config, "worker_start", record, {"backend": backend})

    chosen_backend = backend
    if backend == "auto":
        chosen_backend = "openclaw" if shutil_which("openclaw") else "unavailable"

    if chosen_backend == "openclaw":
        ok, backend_ref = _ensure_agent(
            worker_id,
            config.root,
            os.environ.get("FC_DYNAMIC_WORKERS_MODEL", "gpt-5.4"),
            workspace_key=f"worker-{role}-{worker_type}",
            thinking=thinking or "medium",
        )
        if not ok:
            rc = 5
            stderr = "openclaw_agent_create_failed"
        else:
            proc = subprocess.run(
                [
                    "openclaw",
                    "agent",
                    "--agent",
                    worker_id,
                    "--local",
                    "--json",
                    "--thinking",
                    thinking or default_thinking(worker_type),
                    "--timeout",
                    str(max(30, timeout_seconds)),
                    "--message",
                    message,
                ],
                text=True,
                capture_output=True,
                check=False,
                env=_openclaw_env(),
            )
            rc = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
    elif chosen_backend == "mock":
        stdout = json.dumps(
            {
                "worker_id": worker_id,
                "backend": "mock",
                "summary": f"Mock worker executed for {worker_type}: {_compact(message, 120)}",
            },
            ensure_ascii=True,
        )
    else:
        rc = 5
        stderr = "openclaw_missing"

    raw_path = config.results_dir / f"{worker_id}.raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(stdout if stdout else stderr, encoding="utf-8")
    summary, backend_summary_ref = _extract_summary(stdout if stdout else stderr)
    result = WorkerResult(
        worker_id=worker_id,
        worker_type=worker_type,
        owner_task_id=owner_task_id,
        parent_role=canonical_role(role),
        result_kind=result_kind or default_result_kind(worker_type),
        status="completed" if rc == 0 else "failed",
        summary=summary,
        artifact=str(raw_path.relative_to(config.root)),
        verify=f"proof=worker_backend:{chosen_backend}; rc={rc}",
        raw_output_ref=str(raw_path.relative_to(config.root)),
        backend=chosen_backend,
        backend_ref=backend_summary_ref or backend_ref,
        started_at=record.created_at,
        finished_at=_iso(),
    )
    result_path = config.results_dir / f"{worker_id}.result.json"
    save_result(result_path, result)

    for idx, existing in enumerate(records):
        if existing.worker_id == worker_id:
            records[idx].status = result.status
            records[idx].backend = chosen_backend
            records[idx].backend_ref = backend_ref
            records[idx].last_update_at = result.finished_at
            records[idx].summary = summary
            records[idx].artifact = result.artifact
            records[idx].verify = result.verify
            records[idx].raw_output_ref = result.raw_output_ref
            records[idx].result_kind = result.result_kind
            break
    _save_registry(config.registry_path, records)
    _emit_event(
        config,
        "worker_result",
        records[-1] if records and records[-1].worker_id == worker_id else WorkerRecord.from_dict(result.as_dict()),
        {"rc": rc, "result_path": str(result_path.relative_to(config.root))},
    )
    payload = result.as_dict()
    payload["ok"] = rc == 0
    payload["rc"] = rc
    if stderr:
        payload["stderr"] = _compact(stderr, 220)
    return 0 if rc == 0 else 6, payload


def collect_worker(config: WorkerManagerConfig, role: str, worker_id: str, owner_task_id: str, mark_merged: bool) -> tuple[int, dict[str, Any]]:
    registry = _load_registry(config.registry_path)
    records = _records_from_registry(registry)
    target: WorkerRecord | None = None
    for record in records:
        if worker_id and record.worker_id == worker_id:
            target = record
            break
        if owner_task_id and record.owner_task_id == owner_task_id and record.parent_role == canonical_role(role):
            target = record
    if target is None:
        return 3, {"ok": False, "reason": "worker_not_found"}
    if canonical_role(role) != target.parent_role:
        return 4, {"ok": False, "reason": "parent_role_mismatch"}
    result_path = config.results_dir / f"{target.worker_id}.result.json"
    payload = _read_json(result_path, {})
    if not isinstance(payload, dict):
        payload = {}
    if mark_merged:
        for record in records:
            if record.worker_id == target.worker_id:
                record.status = "merged"
                record.merged_at = _iso()
                _emit_event(config, "worker_merge", record, {"merged_by": canonical_role(role)})
                break
        _save_registry(config.registry_path, records)
    payload["ok"] = True
    return 0, payload


def cleanup_workers(config: WorkerManagerConfig) -> dict[str, Any]:
    registry = _load_registry(config.registry_path)
    records = _records_from_registry(registry)
    kept, removed = _cleanup_records(config, records)
    _save_registry(config.registry_path, kept)
    return {"ok": True, "removed": removed, "remaining": len(kept)}


def status_snapshot(config: WorkerManagerConfig, role: str = "") -> dict[str, Any]:
    registry = _load_registry(config.registry_path)
    records = _records_from_registry(registry)
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
        "role": role_token,
        "active_count": len(active),
        "max_active": config.max_active,
        "active": active,
        "recent": recent,
        "events_path": str(config.events_path.relative_to(config.root)),
        "registry_path": str(config.registry_path.relative_to(config.root)),
    }


def prompt_context(config: WorkerManagerConfig, role: str) -> str:
    snapshot = status_snapshot(config, role)
    active = snapshot.get("active", [])
    recent = snapshot.get("recent", [])
    max_active = int(snapshot.get("max_active", 0) or 0)
    active_count = int(snapshot.get("active_count", 0) or 0)
    open_slots = max(0, max_active - active_count)
    active_bits: list[str] = []
    for item in active[:3]:
        active_bits.append(f"{item.get('worker_type')}:{item.get('owner_task_id')}:{item.get('status')}")
    recent_bits: list[str] = []
    for item in recent[-3:]:
        recent_bits.append(f"{item.get('worker_type')}:{item.get('owner_task_id')}:{_compact(item.get('summary', ''), 80)}")
    return (
        f"dynamic_workers_enabled={1 if config.enabled else 0} | "
        f"worker_open_slots={open_slots} | "
        f"worker_active={'; '.join(active_bits) if active_bits else 'none'} | "
        f"worker_recent_results={'; '.join(recent_bits) if recent_bits else 'none'}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dynamic worker manager bridge")
    parser.add_argument("--root", default=str(Path.cwd()))
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--role", required=True)
    p_plan.add_argument("--worker-type", required=True)
    p_plan.add_argument("--owner-task-id", required=True)
    p_plan.add_argument("--task-kind", default="investigation")

    p_run = sub.add_parser("run")
    p_run.add_argument("--role", required=True)
    p_run.add_argument("--worker-type", required=True)
    p_run.add_argument("--owner-task-id", required=True)
    p_run.add_argument("--task-kind", default="investigation")
    p_run.add_argument("--message", required=True)
    p_run.add_argument("--ttl-min", type=int, default=0)
    p_run.add_argument("--backend", default="auto", choices=["auto", "openclaw", "mock"])
    p_run.add_argument("--timeout-seconds", type=int, default=180)
    p_run.add_argument("--thinking", default="")
    p_run.add_argument("--result-kind", default="")

    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--role", required=True)
    p_collect.add_argument("--worker-id", default="")
    p_collect.add_argument("--owner-task-id", default="")
    p_collect.add_argument("--mark-merged", action="store_true")

    p_cleanup = sub.add_parser("cleanup")

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
        print(json.dumps(plan_worker(config, args.role, args.worker_type, args.owner_task_id, args.task_kind), ensure_ascii=True))
        return 0
    if args.cmd == "run":
        rc, payload = run_worker(
            config,
            role=args.role,
            worker_type=args.worker_type,
            owner_task_id=args.owner_task_id,
            task_kind=args.task_kind,
            message=args.message,
            ttl_min=args.ttl_min,
            backend=args.backend,
            timeout_seconds=args.timeout_seconds,
            thinking=args.thinking,
            result_kind=args.result_kind,
        )
        print(json.dumps(payload, ensure_ascii=True))
        return rc
    if args.cmd == "collect":
        rc, payload = collect_worker(config, args.role, args.worker_id, args.owner_task_id, args.mark_merged)
        print(json.dumps(payload, ensure_ascii=True))
        return rc
    if args.cmd == "cleanup":
        print(json.dumps(cleanup_workers(config), ensure_ascii=True))
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
