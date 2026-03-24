from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_write_path, runtime_state_root
from runtime.core.contracts import OrchestrationEvent, PlannerGraphState


def event_store_path(root: Path) -> Path:
    state_root = runtime_state_root(root)
    state_root.mkdir(parents=True, exist_ok=True)
    return state_root / "orchestration-runtime.sqlite"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class EventStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.path = event_store_path(self.root)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS orchestration_events (
                    event_id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    cycle_id TEXT,
                    batch_id TEXT,
                    task_id TEXT,
                    owner_role TEXT,
                    target_role TEXT,
                    checkpoint_id TEXT,
                    graph_node TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_orchestration_events_ts
                    ON orchestration_events(ts DESC);
                CREATE INDEX IF NOT EXISTS idx_orchestration_events_task
                    ON orchestration_events(task_id, ts DESC);

                CREATE TABLE IF NOT EXISTS planner_graph_state (
                    task_id TEXT PRIMARY KEY,
                    batch_id TEXT,
                    cycle_id TEXT,
                    owner_role TEXT,
                    target_role TEXT,
                    status TEXT,
                    current_node TEXT,
                    checkpoint_id TEXT,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

    def append_event(self, event: OrchestrationEvent) -> str:
        payload = event.model_dump()
        if not payload.get("event_id"):
            raise ValueError("event_id is required")
        ts = str(payload.get("ts") or _utc_now()).strip() or _utc_now()
        payload["ts"] = ts
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO orchestration_events (
                    event_id, ts, event_type, cycle_id, batch_id, task_id,
                    owner_role, target_role, checkpoint_id, graph_node, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["event_id"],
                    ts,
                    str(payload.get("event_type", "") or ""),
                    str(payload.get("cycle_id", "") or ""),
                    str(payload.get("batch_id", "") or ""),
                    str(payload.get("task_id", "") or ""),
                    str(payload.get("owner_role", "") or ""),
                    str(payload.get("target_role", "") or ""),
                    str(payload.get("checkpoint_id", "") or ""),
                    str(payload.get("graph_node", "") or ""),
                    json.dumps(payload, ensure_ascii=True),
                ),
            )
        self._project_jsonl(payload)
        return str(payload["event_id"])

    def upsert_graph_state(self, state: PlannerGraphState) -> None:
        payload = state.model_dump()
        task_id = str(payload.get("task_id", "") or "").strip()
        if not task_id:
            raise ValueError("PlannerGraphState.task_id is required")
        updated_at = str(payload.get("updated_at") or _utc_now()).strip() or _utc_now()
        payload["updated_at"] = updated_at
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO planner_graph_state (
                    task_id, batch_id, cycle_id, owner_role, target_role, status,
                    current_node, checkpoint_id, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    batch_id=excluded.batch_id,
                    cycle_id=excluded.cycle_id,
                    owner_role=excluded.owner_role,
                    target_role=excluded.target_role,
                    status=excluded.status,
                    current_node=excluded.current_node,
                    checkpoint_id=excluded.checkpoint_id,
                    updated_at=excluded.updated_at,
                    payload_json=excluded.payload_json
                """,
                (
                    task_id,
                    str(payload.get("batch_id", "") or ""),
                    str(payload.get("cycle_id", "") or ""),
                    str(payload.get("owner_role", "") or ""),
                    str(payload.get("target_role", "") or ""),
                    str(payload.get("status", "") or ""),
                    str(payload.get("current_node", "") or ""),
                    str(payload.get("checkpoint_id", "") or ""),
                    updated_at,
                    json.dumps(payload, ensure_ascii=True),
                ),
            )
        snapshot_path = resolve_orchestrator_write_path(self.root, "planner-graph-state.json")
        latest = self.latest_graph_states(limit=200)
        snapshot_path.write_text(json.dumps({"items": latest, "updated_at": _utc_now()}, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    def load_graph_state(self, task_id: str) -> dict[str, Any]:
        token = str(task_id or "").strip()
        if not token:
            return {}
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM planner_graph_state WHERE task_id = ?",
                (token,),
            ).fetchone()
        if row is None:
            return {}
        try:
            payload = json.loads(str(row["payload_json"] or "{}"))
        except Exception:
            payload = {}
        return payload if isinstance(payload, dict) else {}

    def recent_events(self, *, hours: int = 6, limit: int = 200) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, min(int(hours), 168)))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM orchestration_events
                WHERE ts >= ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (cutoff.isoformat().replace("+00:00", "Z"), max(1, int(limit))),
            ).fetchall()
        payloads: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                payloads.append(payload)
        return payloads

    def latest_graph_states(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM planner_graph_state
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
        payloads: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except Exception:
                payload = {}
            if isinstance(payload, dict):
                payloads.append(payload)
        return payloads

    def _project_jsonl(self, payload: dict[str, Any]) -> None:
        path = resolve_orchestrator_write_path(self.root, "planner-graph-events.jsonl")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def recent_events(root: Path, *, hours: int = 6, limit: int = 200) -> list[dict[str, Any]]:
    try:
        return EventStore(root).recent_events(hours=hours, limit=limit)
    except Exception:
        return []


def latest_graph_states(root: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    try:
        return EventStore(root).latest_graph_states(limit=limit)
    except Exception:
        return []
