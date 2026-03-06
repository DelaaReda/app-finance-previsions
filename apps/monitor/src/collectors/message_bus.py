from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _parse_ts_epoch(raw: str) -> float | None:
    token = str(raw or "").strip()
    if not token:
        return None
    try:
        if token.endswith("Z"):
            token = token[:-1] + "+00:00"
        return datetime.fromisoformat(token).timestamp()
    except Exception:
        return None


def collect_message_bus_snapshot(
    *,
    bus_file: Path,
    now_iso: str,
    recent_minutes: int,
    core_roles: tuple[str, ...] = ("planner", "dev", "admin", "scrum_master"),
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "open": 0,
        "open_count": 0,
        "delivered": 0,
        "delivered_count": 0,
        "actioned": 0,
        "actioned_count": 0,
        "closed": 0,
        "closed_count": 0,
        "delivered_recent": 0,
        "actioned_recent": 0,
        "closed_recent": 0,
        "expired": 0,
        "expired_count": 0,
        "posted": 0,
        "posted_count": 0,
        "recent_posts": [],
        "recent_actions": [],
        "pending_by_role": {},
        "open_by_role": {},
        "last_message_id_by_role": {},
        "latest_action_status_by_role": {},
        "source": str(bus_file),
    }
    if not bus_file.exists():
        return payload

    rows: list[dict[str, Any]] = []
    try:
        for raw in bus_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    except Exception:
        return payload

    now_epoch = _parse_ts_epoch(now_iso) or time.time()
    recent_cutoff = now_epoch - float(max(1, recent_minutes) * 60)
    posts: dict[str, dict[str, Any]] = {}
    closed: set[str] = set()
    delivered_ids: set[str] = set()
    actioned_ids: set[str] = set()
    delivered_by_role: dict[str, set[str]] = defaultdict(set)
    latest_action_status_by_role = {role: "none" for role in core_roles}
    latest_action_ts_by_role = {role: "" for role in core_roles}
    closed_recent = 0
    delivered_recent = 0
    actioned_recent = 0
    recent_posts: list[dict[str, Any]] = []
    recent_actions: list[dict[str, Any]] = []

    for row in rows:
        event = str(row.get("event", "")).strip()
        mid = str(row.get("message_id", "")).strip()
        if not mid:
            continue
        row_ts = str(row.get("ts_utc") or row.get("ts") or "")
        ts_epoch = _parse_ts_epoch(row_ts)
        is_recent = ts_epoch is not None and ts_epoch >= recent_cutoff
        if event == "message_posted":
            posts[mid] = row
            recent_posts.append(
                {
                    "id": mid,
                    "ts": row_ts,
                    "from": str(row.get("source") or row.get("from") or ""),
                    "targets": row.get("targets", []),
                    "priority": str(row.get("priority", "normal")),
                    "msg": str(row.get("payload") or row.get("msg") or ""),
                }
            )
        elif event == "message_closed":
            closed.add(mid)
            if is_recent:
                closed_recent += 1
        elif event == "message_delivered":
            delivered_ids.add(mid)
            role = str(row.get("role", "")).strip().lower()
            if role:
                delivered_by_role[role].add(mid)
            if is_recent:
                delivered_recent += 1
        elif event == "message_action":
            actioned_ids.add(mid)
            if is_recent:
                actioned_recent += 1
            action_role = str(row.get("role", "")).strip().lower()
            action_status = str(row.get("action_status") or row.get("status") or "").strip().lower()
            if action_role in core_roles and action_status in {"done", "deferred", "blocked"}:
                prev_ts = latest_action_ts_by_role.get(action_role, "")
                if row_ts and (not prev_ts or row_ts >= prev_ts):
                    latest_action_ts_by_role[action_role] = row_ts
                    latest_action_status_by_role[action_role] = action_status
            recent_actions.append(
                {
                    "id": mid,
                    "ts": row_ts,
                    "role": str(row.get("role", "")),
                    "status": str(row.get("action_status") or row.get("status") or ""),
                    "note": str(row.get("note", "")),
                }
            )

    open_count = 0
    expired_count = 0
    pending_by_role = {role: 0 for role in core_roles}
    open_by_role = {role: 0 for role in core_roles}
    last_message_id_by_role = {role: "" for role in core_roles}
    role_latest_ts = {role: "" for role in core_roles}

    for mid, post in posts.items():
        if mid in closed:
            continue
        expires_at = str(post.get("expires_at_utc") or post.get("expires_at") or "").strip()
        if expires_at and expires_at <= now_iso:
            expired_count += 1
            continue
        open_count += 1
        targets_raw = post.get("targets", [])
        targets = [str(x).strip().lower() for x in targets_raw] if isinstance(targets_raw, list) else []
        ts = str(post.get("ts_utc") or post.get("ts") or "")
        for role in core_roles:
            if "all" not in targets and role not in targets:
                continue
            open_by_role[role] = open_by_role.get(role, 0) + 1
            if mid in delivered_by_role.get(role, set()):
                continue
            pending_by_role[role] = pending_by_role.get(role, 0) + 1
            latest = role_latest_ts.get(role, "")
            if ts and (not latest or ts >= latest):
                role_latest_ts[role] = ts
                last_message_id_by_role[role] = mid

    payload.update(
        {
            "open": open_count,
            "open_count": open_count,
            "delivered": len(delivered_ids),
            "delivered_count": len(delivered_ids),
            "actioned": len(actioned_ids),
            "actioned_count": len(actioned_ids),
            "closed": len(closed),
            "closed_count": len(closed),
            "delivered_recent": delivered_recent,
            "actioned_recent": actioned_recent,
            "closed_recent": closed_recent,
            "expired": expired_count,
            "expired_count": expired_count,
            "posted": len(posts),
            "posted_count": len(posts),
            "recent_posts": sorted(recent_posts, key=lambda r: str(r.get("ts", "")), reverse=True)[:8],
            "recent_actions": sorted(recent_actions, key=lambda r: str(r.get("ts", "")), reverse=True)[:8],
            "pending_by_role": pending_by_role,
            "open_by_role": open_by_role,
            "last_message_id_by_role": last_message_id_by_role,
            "latest_action_status_by_role": latest_action_status_by_role,
        }
    )
    return payload
