from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _tail_lines(path: Path, limit: int) -> list[str]:
    if limit <= 0:
        return []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            return list(deque((ln.rstrip("\n") for ln in fh), maxlen=limit))
    except Exception:
        return []


def _parse_iso_ts(raw: str) -> datetime | None:
    token = str(raw or "").strip()
    if not token:
        return None
    try:
        if token.endswith("Z"):
            token = token[:-1] + "+00:00"
        dt = datetime.fromisoformat(token)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _extract_ts_from_line(line: str) -> datetime | None:
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", str(line or ""))
    if not m:
        return None
    return _parse_iso_ts(m.group(1))


def _kv_from_detail(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    token = str(raw or "")
    for m in re.finditer(r"\b([a-zA-Z0-9_]+)=([^\s]+)", token):
        out[m.group(1)] = m.group(2)
    return out


def _normalize_role(role: str) -> str:
    role_token = str(role or "").strip().lower()
    if not role_token:
        return "unknown"
    alias = {
        "po_scrum_master": "scrum_master",
        "qa": "dev",
        "tester": "dev",
        "backend_engineer": "dev",
        "frontend_engineer": "dev",
        "analyst": "planner",
        "architect": "planner",
        "po": "planner",
    }
    return alias.get(role_token, role_token)


def _extract_batch_task(raw: str) -> tuple[str, str]:
    text = str(raw or "").strip()
    if not text:
        return "", ""
    task_id = text
    m_task = re.search(r"(BATCH-[0-9]+-[A-Z0-9_\-]+)", text)
    if m_task:
        task_id = m_task.group(1)
    m_batch = re.search(r"(BATCH-[0-9]+)", task_id)
    batch_id = m_batch.group(1) if m_batch else ""
    return batch_id, task_id


def _action_from_token(token: str) -> str:
    up = str(token or "").upper()
    if not up:
        return "NOOP"
    if "CLAIM" in up:
        return "CLAIM"
    if "COMPLETE" in up or "DONE" in up:
        return "COMPLETE"
    if "HANDOFF" in up:
        return "HANDOFF"
    if "PATCH" in up:
        return "PATCH"
    if "TEST" in up or "VERIFY" in up:
        return "TEST"
    if "CHECK" in up or "SYNC" in up or "PROBE" in up:
        return "CHECK"
    if "BLOCK" in up or "FAIL" in up:
        return "BLOCKED"
    if "RECOVER" in up or "UNBLOCK" in up:
        return "RECOVER"
    if "PROGRESS" in up or "UPDATE" in up:
        return "PROGRESS"
    return "NOOP"


def _event_id(*parts: str) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return hashlib.sha1(payload.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _window_cutoff(window_hours: int) -> datetime:
    now = datetime.now(timezone.utc)
    safe_hours = max(1, min(int(window_hours), 72))
    return now - timedelta(hours=safe_hours)


def _build_orchestrator_event_rows(
    path: Path,
    *,
    cutoff: datetime,
    max_lines: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in _tail_lines(path, max_lines):
    token_text = str(token or "").strip().upper()
    if token_text.endswith("_DELTA"):
        if token_text == "TEST_DELTA":
            return "TEST"
        if token_text in {"ARTIFACT_DELTA", "CODE_DELTA"}:
            return "PATCH"
        return "PROGRESS"
    if token_text.endswith("BRIDGE_RESULT") or token_text == "BRIDGE_RESULT":
        return "PROGRESS"
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        ts = _parse_iso_ts(str(payload.get("at") or payload.get("ts_utc") or payload.get("ts") or ""))
        if ts is None or ts < cutoff:
            continue
        kind = str(payload.get("kind") or "").strip()
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        role = _normalize_role(str(details.get("role") or payload.get("role") or ""))
        task_id = str(details.get("task_id") or "").strip()
        batch_id, task_norm = _extract_batch_task(task_id)
        artifact = str(details.get("artifact") or details.get("proof_manifest") or "").strip()
        tick_id = str(details.get("tick") or "").strip()
        action = _action_from_token(kind)
        event_id = _event_id(ts.isoformat(), role, task_norm, action, tick_id, str(path))
        rows.append(
            {
                "event_id": event_id,
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "role": role,
                "action": action,
                "batch_id": batch_id,
                "task_id": task_norm,
                "state_before": str(details.get("state_before") or ""),
                "state_after": str(details.get("state_after") or ""),
                "reason_code": str(details.get("reason_code") or kind or "").strip().upper(),
                "tick_id": tick_id,
                "source_file": str(path),
                "source_kind": "orchestrator_event",
                "raw_event": kind,
                "artifact_refs": [artifact] if artifact else [],
                "evidence_refs": [],
                "summary": f"{role} → {kind}",
            }
        )
    return rows


def _build_runner_event_rows(
    path: Path,
    *,
    cutoff: datetime,
    max_lines: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in _tail_lines(path, max_lines):
        ts = _extract_ts_from_line(line)
        if ts is None or ts < cutoff:
            continue
        role_m = re.search(r"\brole=([a-zA-Z0-9_\-]+)", line)
        event_m = re.search(r"\bevent=([a-zA-Z0-9_\-]+)", line)
        detail_m = re.search(r"\bdetail=(.*)$", line)
        role = _normalize_role(role_m.group(1) if role_m else "")
        event_name = str(event_m.group(1) if event_m else "").strip()
        detail = str(detail_m.group(1) if detail_m else "")
        kv = _kv_from_detail(detail)
        tick_id = str(kv.get("tick") or "").strip()
        batch_id, task_id = _extract_batch_task(str(kv.get("task") or kv.get("task_id") or detail))
        reason_code = str(kv.get("reason") or event_name or "").strip().upper()
        action = _action_from_token(event_name)
        if action == "NOOP":
            action = _action_from_token(reason_code)
        artifact_refs: list[str] = []
        for key in ("artifact", "proof", "proof_manifest"):
            val = str(kv.get(key) or "").strip()
            if val:
                artifact_refs.append(val)
        event_id = _event_id(ts.isoformat(), role, task_id, action, tick_id, str(path), event_name)
        rows.append(
            {
                "event_id": event_id,
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "role": role,
                "action": action,
                "batch_id": batch_id,
                "task_id": task_id,
                "state_before": "",
                "state_after": "",
                "reason_code": reason_code,
                "tick_id": tick_id,
                "source_file": str(path),
                "source_kind": "runner_event",
                "raw_event": event_name,
                "artifact_refs": artifact_refs,
                "evidence_refs": [],
                "summary": f"{role} → {event_name}",
            }
        )
    return rows


def collect_activity_events(
    *,
    root: Path,
    state_dir: Path,
    window_hours: int = 6,
    limit: int = 300,
) -> dict[str, Any]:
    cutoff = _window_cutoff(window_hours)
    max_lines = max(200, min(6000, int(limit) * 12))
    orch_path = root / "docs" / "operations" / "orchestrator" / "events.jsonl"
    runner_dir = root / "logs-codex-runs" / "role-runner"
    rows: list[dict[str, Any]] = []

    if orch_path.exists():
        rows.extend(_build_orchestrator_event_rows(orch_path, cutoff=cutoff, max_lines=max_lines))

    for role in ("planner", "dev", "admin", "scrum_master"):
        path = runner_dir / f"{role}.events.log"
        if path.exists():
            rows.extend(_build_runner_event_rows(path, cutoff=cutoff, max_lines=max_lines))

    # Add a lightweight contract event if state files are available.
    for role in ("planner", "dev", "admin", "scrum_master"):
        path = state_dir / f"{role}.last_contract"
        if not path.exists():
            continue
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except Exception:
            continue
        if mtime < cutoff:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        next_line = ""
        for ln in text.splitlines():
            if ln.startswith("NEXT:"):
                next_line = ln.split(":", 1)[1].strip()
                break
        batch_id, task_id = _extract_batch_task(next_line)
        event_id = _event_id(mtime.isoformat(), role, task_id, "PROGRESS", "contract", str(path))
        rows.append(
            {
                "event_id": event_id,
                "ts": mtime.isoformat().replace("+00:00", "Z"),
                "role": role,
                "action": "PROGRESS",
                "batch_id": batch_id,
                "task_id": task_id,
                "state_before": "",
                "state_after": "",
                "reason_code": "CONTRACT_SNAPSHOT",
                "tick_id": "",
                "source_file": str(path),
                "source_kind": "contract",
                "raw_event": "contract_snapshot",
                "artifact_refs": [],
                "evidence_refs": [],
                "summary": f"{role} contract snapshot",
            }
        )

    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        dedup[row["event_id"]] = row

    ordered = sorted(dedup.values(), key=lambda item: str(item.get("ts", "")), reverse=True)
    bounded = ordered[: max(20, min(int(limit), 1000))]
    return {
        "window_hours": max(1, min(int(window_hours), 72)),
        "count": len(bounded),
        "timeline": bounded,
        "sources": {
            "orchestrator_events": str(orch_path),
            "runner_events_dir": str(runner_dir),
            "state_dir": str(state_dir),
        },
    }
