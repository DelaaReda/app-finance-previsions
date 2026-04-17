#!/usr/bin/env python3
"""Canonical lane-validity summary for orchestration health and recovery."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CANONICAL_ORCHESTRATOR_DIR = Path("logs-codex-runs/orchestrator-state")
STATE_DIR_DEFAULT = Path.home() / ".openclaw/cron/role-state"
BATCH_ID_RE = re.compile(r"\b(BATCH-\d+)\b", re.IGNORECASE)
STREAM_ID_INLINE_RE = re.compile(r"\bstream_id\s*=\s*([A-Za-z0-9._:-]+)", re.IGNORECASE)
TASK_ID_INLINE_RE = re.compile(r"\btask_id\s*=\s*([A-Za-z0-9._:-]+)", re.IGNORECASE)
ACTIONABLE_TASK_STATES = {
    "READY",
    "READY_DEV",
    "READY_PLANNER",
    "READY_ADMIN",
    "IN_PROGRESS",
    "REVIEW",
}
ACTIVE_CONTRACT_STATUSES = {
    "IN_PROGRESS",
    "BLOCKED",
    "WAIT",
    "MUTED",
}
ROLE_KEYS = (
    "role",
    "owner",
    "target_role",
    "assigned_role",
    "lane",
    "executor_role",
)
ROLE_ALIASES = {
    "vision_architect_tasks_planner": "planner",
    "vision-architect-tasks-planner": "planner",
    "analyst": "planner",
    "architect": "planner",
    "po": "planner",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_role(raw: object) -> str:
    token = str(raw or "").strip().lower().replace("-", "_")
    return ROLE_ALIASES.get(token, token)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _tmux_session_name(role: str) -> str:
    return f"codex_{_normalize_role(role)}_cron"


def _tmux_pane_path(session: str) -> str:
    try:
        proc = subprocess.run(
            ["tmux", "display-message", "-p", "-t", f"{session}:0.0", "#{pane_current_path}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    return str(proc.stdout or "").strip()


def _tmux_display(session: str, fmt: str) -> str:
    try:
        proc = subprocess.run(
            ["tmux", "display-message", "-p", "-t", f"{session}:0.0", fmt],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    return str(proc.stdout or "").strip()


def _tmux_session_ready(session: str) -> bool:
    cmd = _tmux_display(session, "#{pane_current_command}").strip().lower()
    if any(token in cmd for token in ("codex", "qwen")) or cmd == "node":
        return True
    pid_token = _tmux_display(session, "#{pane_pid}").strip()
    if not pid_token.isdigit():
        return False
    try:
        proc = subprocess.run(
            ["pgrep", "-P", pid_token, "-af"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return False
    child_text = str(proc.stdout or "").lower()
    return any(token in child_text for token in ("codex", "qwen", "openai/codex"))


def _workspace_path_reason(path_value: str, root: Path) -> str:
    token = str(path_value or "").strip()
    if not token:
        return "ok"
    if "(deleted)" in token:
        return "deleted_workdir"
    try:
        path_obj = Path(token)
        if not path_obj.exists():
            return "missing_workdir"
        if not path_obj.samefile(root):
            return "foreign_workdir"
    except Exception:
        return "foreign_workdir"
    return "ok"


def _workspace_path_invalid(path_value: str, root: Path) -> bool:
    return _workspace_path_reason(path_value, root) != "ok"


def _proc_cwd(pid: int) -> str:
    if pid <= 0:
        return ""
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except Exception:
        return ""


def _proc_children(pid: int) -> list[int]:
    if pid <= 0:
        return []
    try:
        raw = Path(f"/proc/{pid}/task/{pid}/children").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return [int(token) for token in raw.split() if token.isdigit()]


def _tmux_runtime_path_reason(session: str, root: Path) -> tuple[str, str]:
    pane_path = _tmux_pane_path(session)
    pane_reason = _workspace_path_reason(pane_path, root)
    if pane_reason != "ok":
        return pane_reason, pane_path

    pid_token = _tmux_display(session, "#{pane_pid}")
    pane_pid = int(pid_token) if str(pid_token).isdigit() else 0
    pane_cwd = _proc_cwd(pane_pid)
    pane_cwd_reason = _workspace_path_reason(pane_cwd, root)
    if pane_cwd_reason != "ok":
        return pane_cwd_reason, pane_cwd

    for child_pid in _proc_children(pane_pid):
        child_cwd = _proc_cwd(child_pid)
        child_reason = _workspace_path_reason(child_cwd, root)
        if child_reason != "ok":
            return child_reason, child_cwd

    return "ok", pane_path


def _batch_id_from_values(*values: object) -> str:
    for value in values:
        match = BATCH_ID_RE.search(str(value or ""))
        if match:
            return match.group(1).upper()
    return ""


def _parse_iso(value: object) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        if token.endswith("Z"):
            token = token[:-1] + "+00:00"
        dt = datetime.fromisoformat(token)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _contract_fields(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return {}
    for raw in lines:
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        token = key.strip().upper()
        if token and token not in fields:
            fields[token] = value.strip()
    inline_sources = [str(fields.get(key, "")).strip() for key in ("EVIDENCE", "NEXT", "RISKS")]
    if "STREAM_ID" not in fields:
        for value in inline_sources:
            match = STREAM_ID_INLINE_RE.search(value)
            if match:
                fields["STREAM_ID"] = match.group(1).strip()
                break
    if "TASK_ID" not in fields:
        for value in inline_sources:
            match = TASK_ID_INLINE_RE.search(value)
            if match:
                fields["TASK_ID"] = match.group(1).strip()
                break
    if "BATCH_ID" not in fields:
        batch_id = _batch_id_from_values(fields.get("STREAM_ID"), fields.get("TASK_ID"), *inline_sources)
        if batch_id:
            fields["BATCH_ID"] = batch_id
    return fields


def _contract_age_seconds(path: Path, fields: dict[str, str]) -> int | None:
    for key in ("UPDATED_AT", "TIMESTAMP", "GENERATED_AT"):
        dt = _parse_iso(fields.get(key))
        if dt is not None:
            delta = (datetime.now(timezone.utc) - dt).total_seconds()
            return max(0, int(delta))
    try:
        delta = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    except Exception:
        return None
    return max(0, int(delta))


def _active_batches(queue_obj: dict[str, Any], workboard_obj: dict[str, Any]) -> list[str]:
    for payload in (queue_obj, workboard_obj):
        active_cycle = payload.get("active_cycle")
        if isinstance(active_cycle, dict):
            batch_ids = active_cycle.get("active_batch_ids")
            if isinstance(batch_ids, list):
                cleaned = [str(item).strip().upper() for item in batch_ids if str(item).strip()]
                if cleaned:
                    return cleaned
    return []


def _iter_task_records(node: Any) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if isinstance(node, dict):
        task_id = node.get("task_id") or node.get("id") or ""
        state = node.get("state") or node.get("status") or ""
        role = ""
        for key in ROLE_KEYS:
            value = _normalize_role(node.get(key))
            if value:
                role = value
                break
        if task_id and state:
            stream_id = str(node.get("stream_id") or node.get("batch_id") or node.get("stream") or "").strip()
            records.append(
                {
                    "task_id": str(task_id).strip(),
                    "state": str(state).strip().upper(),
                    "role": role,
                    "batch_id": _batch_id_from_values(stream_id, task_id),
                }
            )
        for value in node.values():
            records.extend(_iter_task_records(value))
    elif isinstance(node, list):
        for item in node:
            records.extend(_iter_task_records(item))
    return records


def build_lane_validity_summary(
    root: Path,
    *,
    roles: list[str] | None = None,
    proof_max_age_seconds: int = 1800,
) -> dict[str, Any]:
    queue_obj = _read_json(root / CANONICAL_ORCHESTRATOR_DIR / "priority-queue.json")
    workboard_obj = _read_json(root / CANONICAL_ORCHESTRATOR_DIR / "parallel-workstreams.json")
    active_batches = _active_batches(queue_obj, workboard_obj)
    workboard_tasks = _iter_task_records(workboard_obj)
    target_roles = [_normalize_role(role) for role in (roles or ["planner", "dev", "admin"]) if _normalize_role(role)]
    state_dir = Path(root / STATE_DIR_DEFAULT) if not STATE_DIR_DEFAULT.is_absolute() else STATE_DIR_DEFAULT
    results: dict[str, Any] = {}

    for role in target_roles:
        session_name = _tmux_session_name(role)
        tmux_path_reason, tmux_path = _tmux_runtime_path_reason(session_name, root)
        tmux_path_invalid = tmux_path_reason != "ok"
        tmux_ready = _tmux_session_ready(session_name)
        actionable_tasks = [
            task
            for task in workboard_tasks
            if task.get("role") == role
            and task.get("state") in ACTIONABLE_TASK_STATES
            and (not active_batches or task.get("batch_id") in active_batches)
        ]
        contract_path = state_dir / f"{role}.last_contract"
        contract = _contract_fields(contract_path)
        contract_batch_id = _batch_id_from_values(
            contract.get("STREAM_ID"),
            contract.get("TASK_ID"),
            contract.get("BATCH_ID"),
            contract.get("NEXT"),
        )
        contract_age = _contract_age_seconds(contract_path, contract) if contract else None
        contract_recent = contract_age is not None and contract_age <= max(60, proof_max_age_seconds)
        contract_status = str(contract.get("STATUS", "")).strip().upper()
        contract_verdict = str(contract.get("VERDICT", "")).strip().upper()
        contract_active_claim = bool(
            contract_status in ACTIVE_CONTRACT_STATUSES
            or contract_verdict in ACTIVE_CONTRACT_STATUSES
            or contract.get("TASK_ID")
            or contract.get("STREAM_ID")
        )
        cycle_match = True
        if active_batches and contract_batch_id:
            cycle_match = contract_batch_id in active_batches
        elif active_batches and actionable_tasks and contract_active_claim and not contract_batch_id:
            cycle_match = False

        if tmux_path_invalid:
            status = {
                "deleted_workdir": "invalid_deleted_workdir",
                "missing_workdir": "invalid_missing_workdir",
                "foreign_workdir": "invalid_foreign_workdir",
            }.get(tmux_path_reason, "invalid_foreign_workdir")
            reason = tmux_path_reason
            needs_recovery = True
        elif not tmux_ready:
            status = "invalid_tmux_not_ready"
            reason = "tmux_not_ready"
            needs_recovery = True
        elif not actionable_tasks:
            status = "idle_no_actionable_work"
            reason = "no_actionable_work"
            needs_recovery = False
        elif not contract:
            status = "invalid_missing_contract"
            reason = "missing_contract"
            needs_recovery = True
        elif not contract_recent:
            status = "invalid_stale_contract"
            reason = "stale_contract"
            needs_recovery = True
        elif not cycle_match:
            if contract_batch_id:
                status = "invalid_cycle_mismatch"
                reason = "cycle_mismatch"
            else:
                status = "invalid_missing_cycle_binding"
                reason = "missing_cycle_binding"
            needs_recovery = True
        else:
            status = "productive_proof"
            reason = "fresh_canonical_proof"
            needs_recovery = False

        results[role] = {
            "status": status,
            "reason": reason,
            "needs_recovery": needs_recovery,
            "actionable_task_count": len(actionable_tasks),
            "actionable_task_ids": [task["task_id"] for task in actionable_tasks[:10]],
            "tmux_session": session_name,
            "tmux_pane_path": tmux_path,
            "tmux_path_reason": tmux_path_reason,
            "tmux_path_invalid": tmux_path_invalid,
            "tmux_ready": tmux_ready,
            "contract_exists": bool(contract),
            "contract_age_seconds": contract_age,
            "contract_recent": bool(contract_recent),
            "contract_status": contract_status,
            "contract_verdict": contract_verdict,
            "contract_stream_id": str(contract.get("STREAM_ID", "")).strip(),
            "contract_task_id": str(contract.get("TASK_ID", "")).strip(),
            "contract_batch_id": contract_batch_id,
            "contract_active_cycle_match": bool(cycle_match),
        }
    return {
        "generated_at": _now_iso(),
        "proof_max_age_seconds": proof_max_age_seconds,
        "active_batches": active_batches,
        "roles": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canonical lane validity summary")
    sub = parser.add_subparsers(dest="command", required=True)

    summary_parser = sub.add_parser("summary")
    summary_parser.add_argument("--root", default=".", help="workspace root")
    summary_parser.add_argument("--roles", default="planner,dev,admin", help="comma-separated roles")
    summary_parser.add_argument("--proof-max-age", type=int, default=1800, help="fresh proof max age in seconds")

    args = parser.parse_args(argv)
    if args.command == "summary":
        roles = [item.strip() for item in str(args.roles or "").split(",") if item.strip()]
        payload = build_lane_validity_summary(
            Path(args.root).resolve(),
            roles=roles,
            proof_max_age_seconds=max(60, int(args.proof_max_age or 1800)),
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
