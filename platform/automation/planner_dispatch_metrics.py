#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path


ACTIVE_STATUSES = {"spawned", "running"}
SUCCESS_STATUSES = {"completed", "merged", "done", "pass", "ok", "success"}
BLOCKED_STATUSES = {"blocked"}
FALLBACK_MARKERS = ("falling back to embedded", "failovererror", "gateway agent failed")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_iso(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _recent_sort_key(item: dict[str, Any]) -> float:
    for key in ("last_update_at", "merged_at", "finished_at", "created_at"):
        dt = _parse_iso(item.get(key))
        if dt is not None:
            return dt.timestamp()
    return 0.0


def _is_fallback_like(root: Path, subagent_id: str) -> bool:
    raw_path = root / "docs" / "operations" / "orchestrator" / "planner-subagents-results" / f"{subagent_id}.raw.txt"
    raw_text = _read_text(raw_path).lower()
    return any(marker in raw_text for marker in FALLBACK_MARKERS)


def build_planner_dispatch_metrics(root: Path, *, recent_limit: int = 12) -> dict[str, Any]:
    registry_path = resolve_orchestrator_read_path(root, "planner-subagents-registry.json")
    payload = _read_json(registry_path) if registry_path.exists() else {}
    rows = payload.get("subagents", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []

    active: list[dict[str, Any]] = []
    recent_rows: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        normalized = {
            "subagent_id": str(item.get("subagent_id", "")),
            "target_role": str(item.get("target_role", "")),
            "parent_role": str(item.get("parent_role", "")),
            "owner_task_id": str(item.get("owner_task_id", "")),
            "status": str(item.get("status", "")),
            "summary": str(item.get("summary", "")),
            "artifact": str(item.get("artifact", "")),
            "last_update_at": str(item.get("last_update_at", "")),
            "created_at": str(item.get("created_at", "")),
            "backend": str(item.get("backend", "")),
            "backend_ref": str(item.get("backend_ref", "")),
        }
        status = normalized["status"].strip().lower()
        if status in ACTIVE_STATUSES:
            active.append(normalized)
        else:
            recent_rows.append(normalized)

    recent_rows = sorted(recent_rows, key=_recent_sort_key)[-max(1, int(recent_limit)) :]
    success_count = 0
    failed_count = 0
    blocked_count = 0
    fallback_like_count = 0
    by_role: dict[str, dict[str, int]] = {}
    for item in recent_rows:
        role = item["target_role"] or "unknown"
        bucket = by_role.setdefault(role, {"total": 0, "success": 0, "failed": 0, "blocked": 0, "fallback_like": 0})
        bucket["total"] += 1
        status = item["status"].strip().lower()
        if status in SUCCESS_STATUSES:
            success_count += 1
            bucket["success"] += 1
        elif status in BLOCKED_STATUSES:
            blocked_count += 1
            bucket["blocked"] += 1
        else:
            failed_count += 1
            bucket["failed"] += 1
        if _is_fallback_like(root, item["subagent_id"]):
            fallback_like_count += 1
            bucket["fallback_like"] += 1

    recent_total = len(recent_rows)
    success_rate = round(success_count / recent_total, 3) if recent_total else 1.0
    latest: dict[str, Any] = {}
    latest_status = ""
    latest_fallback_like = False
    latest_update_at = ""
    latest_owner_task_id = ""
    if recent_rows:
        latest = dict(recent_rows[-1])
        latest_status = str(latest.get("status", "")).strip().lower()
        latest_fallback_like = _is_fallback_like(root, str(latest.get("subagent_id", "")))
        latest_update_at = str(
            latest.get("last_update_at")
            or latest.get("merged_at")
            or latest.get("finished_at")
            or latest.get("created_at")
            or ""
        ).strip()
        latest_owner_task_id = str(latest.get("owner_task_id", "")).strip()
    status = "ok"
    if recent_total and (
        latest_status not in SUCCESS_STATUSES
        or latest_fallback_like
    ):
        status = "degraded"
    return {
        "registry_path": str(registry_path),
        "active_count": len(active),
        "active": active[:8],
        "recent": recent_rows[-8:],
        "recent_total": recent_total,
        "recent_success_count": success_count,
        "recent_failed_count": failed_count,
        "recent_blocked_count": blocked_count,
        "recent_fallback_like_count": fallback_like_count,
        "recent_success_rate": success_rate,
        "recent_by_role": by_role,
        "latest_status": latest_status,
        "latest_fallback_like": latest_fallback_like,
        "latest_owner_task_id": latest_owner_task_id,
        "latest_update_at": latest_update_at,
        "status": status,
    }
