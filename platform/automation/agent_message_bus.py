#!/usr/bin/env python3
"""Canonical targeted agent message bus.

Events are append-only JSONL records in AGENT_MESSAGE_BUS.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


TARGET_RE = re.compile(r"^[a-z0-9_\-]{2,40}$")
PRIORITIES = {"normal", "high", "urgent"}
ACTION_STATUSES = {"done", "deferred", "blocked"}
ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# Accept generated IDs and operator-defined IDs (ex: MSG-001, MSG_INCIDENT_DEV_01).
MSG_ID_RE = re.compile(r"^MSG[-_A-Za-z0-9]{3,120}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_text(raw: str) -> str:
    return re.sub(r"\s+", " ", str(raw or "")).strip()


def generate_ulid() -> str:
    ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    time_part = _encode_base32(ts_ms, 10)
    rand_part = _encode_base32(random.getrandbits(80), 16)
    return f"{time_part}{rand_part}"


def _encode_base32(value: int, length: int) -> str:
    chars = []
    current = value
    for _ in range(length):
        chars.append(ULID_ALPHABET[current & 0x1F])
        current >>= 5
    return "".join(reversed(chars))


def generate_message_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"MSG_{stamp}_{generate_ulid()}"


def parse_targets(raw: str) -> list[str]:
    text = normalize_text(raw).lower()
    if text == "all":
        return ["all"]
    roles: list[str] = []
    seen: set[str] = set()
    for token in text.split(","):
        role = normalize_text(token).lower()
        if not role:
            continue
        if not TARGET_RE.fullmatch(role):
            raise ValueError(f"invalid target role: {role}")
        if role in seen:
            continue
        seen.add(role)
        roles.append(role)
    if not roles:
        raise ValueError("empty targets")
    return roles


def parse_bool01(raw: str) -> bool:
    text = normalize_text(raw).lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ValueError("invalid bool flag (expected 0/1)")


def as_int(raw: str, field: str, minimum: int = 0) -> int:
    try:
        value = int(str(raw).strip())
    except Exception as exc:
        raise ValueError(f"invalid {field}") from exc
    if value < minimum:
        raise ValueError(f"invalid {field}")
    return value


@dataclass
class Bus:
    path: Path

    def ensure(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for raw in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
        return out

    def append(self, row: dict) -> None:
        self.ensure()
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def event_record(
    *,
    event: str,
    message_id: str,
    ts_utc: str,
    source: str = "",
    targets: Iterable[str] | None = None,
    priority: str = "normal",
    sticky: bool = True,
    ttl_min: int = 0,
    expires_at_utc: str = "",
    payload: str = "",
    role: str = "",
    tick_id: str = "",
    action_status: str = "",
    note: str = "",
    close_reason: str = "",
    auto_post_reason: str = "",
    auto_generated_id: bool = False,
) -> dict:
    # Keep legacy aliases (ts/from/msg/expires_at/reason/status) for compatibility
    # with existing monitor/runtime consumers during migration.
    base = {
        "event": event,
        "message_id": message_id,
        "ts_utc": ts_utc,
        "source": source,
        "targets": list(targets or []),
        "priority": priority,
        "sticky": bool(sticky),
        "ttl_min": int(ttl_min),
        "expires_at_utc": expires_at_utc,
        "payload": payload,
        "role": role,
        "tick_id": tick_id,
        "action_status": action_status,
        "note": note,
        "close_reason": close_reason,
        "auto_post_reason": auto_post_reason,
        "auto_generated_id": bool(auto_generated_id),
        "ts": ts_utc,
        "from": source,
        "msg": payload,
        "expires_at": expires_at_utc,
        "status": action_status,
        "reason": close_reason,
    }
    return base


def _posted_events(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        if str(row.get("event", "")).strip() != "message_posted":
            continue
        message_id = str(row.get("message_id", "")).strip()
        if message_id:
            out[message_id] = row
    return out


def _closed_ids(rows: list[dict]) -> set[str]:
    out: set[str] = set()
    for row in rows:
        if str(row.get("event", "")).strip() != "message_closed":
            continue
        message_id = str(row.get("message_id", "")).strip()
        if message_id:
            out.add(message_id)
    return out


def _delivered_roles(rows: list[dict]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in rows:
        if str(row.get("event", "")).strip() != "message_delivered":
            continue
        message_id = str(row.get("message_id", "")).strip()
        role = normalize_text(str(row.get("role", "")).lower())
        if message_id and role:
            out.setdefault(message_id, set()).add(role)
    return out


def _is_expired(post: dict, now: str) -> bool:
    expires_at = normalize_text(str(post.get("expires_at_utc") or post.get("expires_at") or ""))
    return bool(expires_at and expires_at <= now)


def cmd_post(bus: Bus, args: argparse.Namespace) -> int:
    rows = bus.rows()
    existing_ids = {
        normalize_text(str(row.get("message_id", "")))
        for row in rows
        if normalize_text(str(row.get("message_id", "")))
    }

    message_id = normalize_text(args.id or "")
    id_generated_by_bus = False
    if message_id:
        if not MSG_ID_RE.fullmatch(message_id):
            print("ERROR invalid --id format", file=sys.stderr)
            return 2
        if message_id in existing_ids:
            print(f"ERROR message_id collision: {message_id}", file=sys.stderr)
            return 2
    else:
        for _ in range(80):
            candidate = generate_message_id()
            if candidate not in existing_ids:
                message_id = candidate
                id_generated_by_bus = True
                break
        if not message_id:
            print("ERROR message_id_generation_failed", file=sys.stderr)
            return 2

    targets = parse_targets(args.targets)
    priority = normalize_text(args.priority).lower()
    if priority not in PRIORITIES:
        raise ValueError("invalid --priority")

    sticky = parse_bool01(str(args.sticky))
    ttl_min = as_int(args.ttl_min, "--ttl-min", minimum=1)
    payload = normalize_text(args.msg)
    if not payload:
        raise ValueError("empty --msg")
    ts = now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=ttl_min)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    source = normalize_text(args.source or os.environ.get("ADMIN_ROLE") or "main")
    auto_post_reason = normalize_text(args.auto_post_reason or "")
    auto_generated_id = id_generated_by_bus
    if str(args.auto_generated_id or "").strip():
        auto_generated_id = parse_bool01(str(args.auto_generated_id))
    row = event_record(
        event="message_posted",
        message_id=message_id,
        ts_utc=ts,
        source=source,
        targets=targets,
        priority=priority,
        sticky=sticky,
        ttl_min=ttl_min,
        expires_at_utc=expires_at,
        payload=payload,
        auto_post_reason=auto_post_reason,
        auto_generated_id=auto_generated_id,
    )
    bus.append(row)
    print(
        f"OK message_id={message_id} expires_at={expires_at} "
        f"targets={','.join(targets)} priority={priority} sticky={int(sticky)} "
        f"auto_generated_id={int(bool(auto_generated_id))}"
    )
    return 0


def cmd_close(bus: Bus, args: argparse.Namespace) -> int:
    message_id = normalize_text(args.id)
    if not message_id:
        raise ValueError("missing --id")
    rows = bus.rows()
    posted = _posted_events(rows)
    if message_id not in posted:
        print(f"ERROR unknown message_id: {message_id}", file=sys.stderr)
        return 2
    closed = _closed_ids(rows)
    if message_id in closed:
        print(f"NOOP message_id={message_id} already_closed=1")
        return 0
    source = normalize_text(args.by or os.environ.get("ADMIN_ROLE") or "main")
    row = event_record(
        event="message_closed",
        message_id=message_id,
        ts_utc=now_iso(),
        source=source,
        close_reason=normalize_text(args.reason or "closed_by_operator"),
    )
    row["by"] = source
    bus.append(row)
    print(f"OK message_id={message_id} closed=1")
    return 0


def cmd_deliver(bus: Bus, args: argparse.Namespace) -> int:
    message_id = normalize_text(args.id)
    role = normalize_text(args.role).lower()
    tick_id = normalize_text(args.tick)
    if not message_id or not role or not tick_id:
        raise ValueError("missing --id/--role/--tick")
    rows = bus.rows()
    posted = _posted_events(rows)
    if message_id not in posted:
        print(f"ERROR unknown message_id: {message_id}", file=sys.stderr)
        return 2
    closed = _closed_ids(rows)
    if message_id in closed:
        print(f"ERROR message_id closed: {message_id}", file=sys.stderr)
        return 2
    if _is_expired(posted[message_id], now_iso()):
        print(f"ERROR message_id expired: {message_id}", file=sys.stderr)
        return 2
    delivered = _delivered_roles(rows)
    if role in delivered.get(message_id, set()):
        print(f"NOOP message_id={message_id} role={role} delivered=1")
        return 0
    row = event_record(
        event="message_delivered",
        message_id=message_id,
        ts_utc=now_iso(),
        role=role,
        tick_id=tick_id,
    )
    bus.append(row)
    print(f"OK message_id={message_id} role={role} delivered=1")
    return 0


def cmd_action(bus: Bus, args: argparse.Namespace) -> int:
    message_id = normalize_text(args.id)
    role = normalize_text(args.role).lower()
    status = normalize_text(args.status).lower()
    note = normalize_text(args.note or "")
    tick_id = normalize_text(args.tick or "")
    if not message_id or not role or not status:
        raise ValueError("missing --id/--role/--status")
    if status not in ACTION_STATUSES:
        raise ValueError("invalid --status")
    rows = bus.rows()
    posted = _posted_events(rows)
    if message_id not in posted:
        print(f"ERROR unknown message_id: {message_id}", file=sys.stderr)
        return 2
    closed = _closed_ids(rows)
    if message_id in closed:
        print(f"ERROR message_id closed: {message_id}", file=sys.stderr)
        return 2
    if _is_expired(posted[message_id], now_iso()):
        print(f"ERROR message_id expired: {message_id}", file=sys.stderr)
        return 2
    row = event_record(
        event="message_action",
        message_id=message_id,
        ts_utc=now_iso(),
        role=role,
        tick_id=tick_id,
        action_status=status,
        note=note,
    )
    bus.append(row)
    print(f"OK message_id={message_id} role={role} status={status}")
    return 0


def cmd_history(bus: Bus, args: argparse.Namespace) -> int:
    message_id = normalize_text(args.id)
    if not message_id:
        raise ValueError("missing --id")
    rows = [row for row in bus.rows() if normalize_text(str(row.get("message_id", ""))) == message_id]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def _active_rows_for_role(rows: list[dict], role: str, now: str, limit: int) -> list[dict]:
    posts = _posted_events(rows)
    closed = _closed_ids(rows)
    delivered = _delivered_roles(rows)
    role_norm = role.strip().lower()
    active: list[dict] = []
    for message_id, post in posts.items():
        if message_id in closed:
            continue
        expires_at = normalize_text(str(post.get("expires_at_utc") or post.get("expires_at") or ""))
        if expires_at and expires_at <= now:
            continue
        targets_raw = post.get("targets", [])
        targets = [normalize_text(str(x)).lower() for x in targets_raw] if isinstance(targets_raw, list) else []
        if "all" not in targets and role_norm not in targets:
            continue
        if role_norm in delivered.get(message_id, set()):
            continue
        active.append(
            {
                "ts_utc": str(post.get("ts_utc") or post.get("ts") or ""),
                "message_id": message_id,
                "source": str(post.get("source") or post.get("from") or ""),
                "priority": str(post.get("priority") or "normal"),
                "sticky": bool(post.get("sticky", True)),
                "payload": str(post.get("payload") or post.get("msg") or ""),
                "targets": targets,
                "expires_at_utc": expires_at,
            }
        )
    active.sort(key=lambda row: str(row.get("ts_utc", "")), reverse=True)
    return active[: max(1, limit)]


def cmd_active(bus: Bus, args: argparse.Namespace) -> int:
    role = normalize_text(args.role).lower()
    if not role:
        raise ValueError("missing --role")
    limit = as_int(args.limit, "--limit", minimum=1)
    rows = bus.rows()
    active = _active_rows_for_role(rows, role, now_iso(), limit=limit)
    if args.json:
        print(json.dumps(active, ensure_ascii=False))
        return 0
    if not active:
        print("none")
        return 0
    for item in active:
        print(
            f"{item['ts_utc']} {item['message_id']} priority={item['priority']} "
            f"from={item['source']} msg={item['payload']}"
        )
    return 0


def cmd_stats(bus: Bus, _args: argparse.Namespace) -> int:
    rows = bus.rows()
    posts = _posted_events(rows)
    closed = _closed_ids(rows)
    delivered_events = [r for r in rows if str(r.get("event", "")) == "message_delivered"]
    action_events = [r for r in rows if str(r.get("event", "")) == "message_action"]
    now = now_iso()
    open_count = 0
    expired_count = 0
    for message_id, post in posts.items():
        if message_id in closed:
            continue
        expires_at = normalize_text(str(post.get("expires_at_utc") or post.get("expires_at") or ""))
        if expires_at and expires_at <= now:
            expired_count += 1
            continue
        open_count += 1
    payload = {
        "open": open_count,
        "open_count": open_count,
        "delivered": len({normalize_text(str(e.get('message_id', ''))) for e in delivered_events if normalize_text(str(e.get('message_id', '')))}),
        "delivered_count": len(delivered_events),
        "actioned": len({normalize_text(str(e.get('message_id', ''))) for e in action_events if normalize_text(str(e.get('message_id', '')))}),
        "actioned_count": len(action_events),
        "closed": len(closed),
        "closed_count": len(closed),
        "expired": expired_count,
        "expired_count": expired_count,
        "posted": len(posts),
        "posted_count": len(posts),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_message_bus.py",
        description="Append-only message bus for targeted role directives.",
    )
    parser.add_argument(
        "--bus-file",
        default=os.environ.get("AGENT_MESSAGE_BUS_FILE", ""),
        help="JSONL bus path (defaults to AGENT_MESSAGE_BUS_FILE env).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    post = sub.add_parser("post")
    post.add_argument("--targets", required=True)
    post.add_argument("--msg", required=True)
    post.add_argument("--priority", default="normal")
    post.add_argument("--sticky", default=os.environ.get("AGENT_MESSAGE_STICKY_DEFAULT", "1"))
    post.add_argument("--ttl-min", default=os.environ.get("AGENT_MESSAGE_DEFAULT_TTL_MIN", "10080"))
    post.add_argument("--id", default="")
    post.add_argument("--source", default="")
    post.add_argument("--auto-post-reason", default="")
    post.add_argument("--auto-generated-id", default="")
    post.set_defaults(func=cmd_post)

    close = sub.add_parser("close")
    close.add_argument("--id", required=True)
    close.add_argument("--reason", default="closed_by_operator")
    close.add_argument("--by", default="")
    close.set_defaults(func=cmd_close)

    active = sub.add_parser("active")
    active.add_argument("--role", required=True)
    active.add_argument("--limit", default=os.environ.get("AGENT_MESSAGE_MAX_ACTIVE_PER_ROLE", "10"))
    active.add_argument("--json", action="store_true")
    active.set_defaults(func=cmd_active)

    history = sub.add_parser("history")
    history.add_argument("--id", required=True)
    history.set_defaults(func=cmd_history)

    deliver = sub.add_parser("deliver")
    deliver.add_argument("--id", required=True)
    deliver.add_argument("--role", required=True)
    deliver.add_argument("--tick", required=True)
    deliver.set_defaults(func=cmd_deliver)

    action = sub.add_parser("action")
    action.add_argument("--id", required=True)
    action.add_argument("--role", required=True)
    action.add_argument("--status", required=True)
    action.add_argument("--note", default="")
    action.add_argument("--tick", default="")
    action.set_defaults(func=cmd_action)

    stats = sub.add_parser("stats")
    stats.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    bus_file = normalize_text(args.bus_file)
    if not bus_file:
        print("ERROR bus file not set (--bus-file or AGENT_MESSAGE_BUS_FILE)", file=sys.stderr)
        return 2
    bus = Bus(Path(bus_file))
    bus.ensure()
    try:
        return int(args.func(bus, args))
    except ValueError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
