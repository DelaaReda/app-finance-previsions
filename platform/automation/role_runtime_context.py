#!/usr/bin/env python3
"""Build compact runtime context consumed by role runner prompts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from orchestrator_paths import resolve_orchestrator_read_path
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot

PLANNER_GROUP = {
    "planner",
    "vision_architect_tasks_planner",
    "vision-architect-tasks-planner",
    "analyst",
    "architect",
    "po",
    "scrum_master",
    "product_owner",
    "owner",
    "po_engineer",
}
DEV_GROUP = {
    "dev",
    "backend_engineer",
    "frontend_engineer",
    "data_analyst",
    "infra_engineer",
    "integrator",
    "tester",
    "qa",
}
ADMIN_GROUP = {"admin", "clawsentinel", "infra"}


def compact_text(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return "none"
    if len(normalized) > limit:
        return normalized[:limit]
    return normalized


def compact_file_tail(path: Path, lines: int, max_chars: int) -> str:
    if not path.exists():
        return "none"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "none"
    tail_lines = text.splitlines()[-max(1, lines) :]
    return compact_text(" ".join(tail_lines), max_chars)


def read_last_contract_hint(path: Path, scope: str) -> str:
    if not path.exists():
        return f"{scope}:none"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return f"{scope}:none"

    status = "unknown"
    delta = "unknown"
    next_action = "unknown"
    for raw in text.splitlines():
        line = raw.strip()
        if line.upper().startswith("STATUS:") and status == "unknown":
            status = compact_text(line.split(":", 1)[1], 120)
        elif line.upper().startswith("DELTA:") and delta == "unknown":
            delta = compact_text(line.split(":", 1)[1], 120)
        elif line.upper().startswith("NEXT_ACTION_UNIQUE:") and next_action == "unknown":
            next_action = compact_text(line.split(":", 1)[1], 160)

    # Filtrer les états rate_limit pour éviter qu'ils se propagent comme contexte actif
    # Un état rate_limit n'est pas un état métier, juste un skip temporaire
    if "RATE_LIMIT_CODEX_SKIP" in next_action or "rate_limit" in delta.lower():
        return f"{scope}:status=RATE_LIMIT_SKIP,delta=RECOVERING,next=retry_after_backoff"

    return f"{scope}:status={status},delta={delta},next={next_action}"


def peer_contracts_hint(state_dir: Path, role: str) -> str:
    # Priorité: lane planner unifié + lanes delivery actives — 3 pairs max
    # Active lean roles only — legacy roles (backend_engineer, etc.) have been consolidated into 'dev'
    priority_roles = ["planner", "dev", "admin", "scrum_master"]
    _now = __import__("time").time()
    _stale_threshold_s = 7200  # 2h — contracts older than this are not reliable peers
    role_files = sorted(
        [f for f in state_dir.glob("*.last_contract") if (_now - f.stat().st_mtime) < _stale_threshold_s],
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    hints: list[str] = []
    seen: set[str] = set()
    # Priorité aux rôles lean actifs d'abord
    for prio in priority_roles:
        if prio == role:
            continue
        f = state_dir / f"{prio}.last_contract"
        if f.exists() and (_now - f.stat().st_mtime) < _stale_threshold_s:
            hints.append(read_last_contract_hint(f, prio))
            seen.add(prio)
        if len(hints) >= 3:
            break
    # Compléter avec les autres peers récents si la liste prioritaire est incomplète.
    if len(hints) < 3:
        for role_file in role_files:
            role_name = role_file.stem
            if not role_name or role_name == role or role_name in seen:
                continue
            hints.append(read_last_contract_hint(role_file, role_name))
            seen.add(role_name)
            if len(hints) >= 3:
                break
    if not hints:
        return "none"
    return compact_text("; ".join(hints), 240)


def run_parallel_workstream(script_path: Path, role: str, subcmd: str, limit: int, max_chars: int, cwd: Path | None = None) -> str:
    if not script_path.exists():
        return "none"
    cmd = [sys.executable, str(script_path), subcmd, "--role", role, "--limit", str(limit)]
    # CRITICAL: compat/projections/parallel_workstream.py uses a relative DEFAULT_BOARD path.
    # If cwd is not set to workspace root, subprocess cannot resolve board files.
    run_cwd = str(cwd) if cwd is not None else None
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False, cwd=run_cwd)
    except Exception:
        return "none"
    if cp.returncode != 0:
        return "none"
    return compact_text(cp.stdout, max_chars)


def _load_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _canonical_role(value: str) -> str:
    token = str(value or "").strip().replace("-", "_").lower()
    if not token:
        return ""
    if token in PLANNER_GROUP:
        return "planner"
    if token in DEV_GROUP:
        return "dev"
    if token in ADMIN_GROUP:
        return "admin"
    return token


def _runtime_workboard_payload(queue_path: Path) -> dict:
    return _load_json_dict(queue_path.parent / "parallel-workstreams.json")


def _role_task_matches(task: dict, role: str) -> bool:
    role_token = _canonical_role(role)
    if not role_token:
        return False
    task_role = _canonical_role(task.get("role", ""))
    task_assignee = _canonical_role(task.get("assignee", ""))
    return role_token in {task_role, task_assignee}


def runtime_parallel_hint(queue_path: Path, role: str, max_chars: int = 240) -> str:
    board = _runtime_workboard_payload(queue_path)
    tasks = board.get("tasks", []) if isinstance(board.get("tasks"), list) else []
    if not tasks:
        return "runtime_projection=none"

    ready = 0
    in_progress = 0
    blocked = 0
    role_open = 0
    role_ready = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        state = str(task.get("state", "")).strip().upper()
        if state in {"READY", "READY_PLANNER", "READY_DEV"}:
            ready += 1
        elif state in {"IN_PROGRESS", "REVIEW"}:
            in_progress += 1
        elif state == "BLOCKED":
            blocked += 1
        if _role_task_matches(task, role):
            if state not in {"DONE", "PASS", "CLOSED"}:
                role_open += 1
            if state in {"READY", "READY_PLANNER", "READY_DEV"}:
                role_ready += 1

    return compact_text(
        f"runtime_projection=parallel-workstreams ready={ready} in_progress={in_progress} blocked={blocked} "
        f"role_open={role_open} role_ready={role_ready}",
        max_chars,
    )


def runtime_workboard_context(queue_path: Path, role: str, max_chars: int = 300) -> str:
    board = _runtime_workboard_payload(queue_path)
    tasks = board.get("tasks", []) if isinstance(board.get("tasks"), list) else []
    if not tasks:
        return "none"

    matches: list[str] = []
    for task in tasks:
        if not isinstance(task, dict) or not _role_task_matches(task, role):
            continue
        state = str(task.get("state", "")).strip().upper()
        if state in {"DONE", "PASS", "CLOSED"}:
            continue
        task_id = str(task.get("id", "")).strip() or "task?"
        title = str(task.get("title", "")).strip() or "untitled"
        depends_on_raw = task.get("depends_on")
        blocked_by_raw = task.get("blocked_by")
        depends_on = (
            ",".join(str(item).strip() for item in depends_on_raw if str(item).strip())
            if isinstance(depends_on_raw, list)
            else str(depends_on_raw or "").strip()
        )
        blocked_by = (
            ",".join(str(item).strip() for item in blocked_by_raw if str(item).strip())
            if isinstance(blocked_by_raw, list)
            else str(blocked_by_raw or "").strip()
        )
        depends_on = depends_on or "none"
        blocked_by = blocked_by or "none"
        matches.append(f"{task_id}:{state}:depends_on={depends_on}:blocked_by={blocked_by}:{title}")
        if len(matches) >= 3:
            break
    return compact_text(" ; ".join(matches), max_chars) if matches else "none"


def publication_channels_hint(
    queue_path: Path,
    team_chat_file: Path,
    directive_bus_file: Path,
    max_chars: int = 360,
) -> str:
    board_path = queue_path.parent / "parallel-workstreams.json"
    parts = [
        f"runtime_queue={queue_path}",
        f"runtime_workboard={board_path}",
        f"team_chat={team_chat_file}",
        f"directives={directive_bus_file}",
        "docs_projection=compat_only",
    ]
    return compact_text(" ; ".join(parts), max_chars)


def dynamic_worker_context(root: Path, role: str, max_chars: int = 240) -> str:
    script_path = root / "platform" / "automation" / "compat" / "legacy_workers" / "worker_manager.py"
    if not script_path.exists():
        return "none"
    cmd = [sys.executable, str(script_path), "--root", str(root), "prompt-context", "--role", role]
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False, cwd=str(root))
    except Exception:
        return "none"
    if cp.returncode != 0:
        return "none"
    return compact_text(cp.stdout, max_chars)


def planner_subagent_context(root: Path, role: str, max_chars: int = 240) -> str:
    script_path = root / "platform" / "automation" / "planner_subagent_manager.py"
    if not script_path.exists():
        return "none"
    cmd = [sys.executable, str(script_path), "--root", str(root), "prompt-context", "--role", role]
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False, cwd=str(root))
    except Exception:
        return "none"
    if cp.returncode != 0:
        return "none"
    return compact_text(cp.stdout, max_chars)


def product_priority_context(root: Path, max_chars: int = 240) -> str:
    script_path = root / "platform" / "automation" / "product_priority_guard.py"
    if not script_path.exists():
        return "none"
    cmd = [
        sys.executable,
        str(script_path),
        "--root",
        str(root),
        "--api-base-url",
        os.environ.get("FC_API_BASE_URL", "http://127.0.0.1:8050"),
        "prompt-context",
    ]
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False, cwd=str(root))
    except Exception:
        return "none"
    if cp.returncode != 0:
        return "none"
    return compact_text(cp.stdout, max_chars)


def queue_summary(queue_path: Path) -> dict[str, str]:
    result = {
        "ready_items": "none",
        "blocked_items": "none",
        "queue_states": "none",
        "ready_next_actions": "none",
        "queue_has_ready": "0",
        "top_level_total": "0",
        "top_level_non_closed": "0",
        "top_level_ready": "0",
        "planner_batch_runway_short": "1",
    }
    # Prefer reading from workstreams.json streams (single source of truth).
    # Falls back to priority-queue.json if workstreams not available.
    ws_path = queue_path.parent / "parallel-workstreams.json"
    if ws_path.exists():
        try:
            ws_obj = json.loads(ws_path.read_text(encoding="utf-8"))
            raw_streams = ws_obj.get("streams", [])
            # Convert streams to queue-like items for unified processing
            items: list = [
                {
                    "id": s.get("id", ""),
                    "state": s.get("state", ""),
                    "title": s.get("title", ""),
                    "blocker_id": s.get("blocker_id", "NONE"),
                    "next_action": s.get("next_action", ""),
                }
                for s in raw_streams
                if isinstance(s, dict) and re.fullmatch(r"BATCH-\d{2}", str(s.get("id", "")))
            ]
        except Exception:
            items = []
    elif queue_path.exists():
        try:
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
            items = payload.get("items", [])
        except Exception:
            items = []
    else:
        return result
    if not isinstance(items, list):
        return result

    ready_items: list[str] = []
    blocked_items: list[str] = []
    queue_states: list[str] = []
    ready_next_actions: list[str] = []
    ready_count = 0
    top_level_total = 0
    top_level_non_closed = 0
    top_level_ready = 0

    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        state = str(item.get("state", "")).strip()
        state_upper = state.upper()
        title = str(item.get("title", "")).strip()
        blocker_id = str(item.get("blocker_id", "NONE")).strip() or "NONE"
        next_action = str(item.get("next_action", "NONE")).strip() or "NONE"
        # Only show actionable states (READY/IN_PROGRESS) + DONE summary to reduce noise.
        # WAITING_DEP batches beyond the immediate next are not actionable.
        if item_id and state_upper in {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "BLOCKED"}:
            queue_states.append(f"{item_id}={state}")
        if re.fullmatch(r"BATCH-\d{2}", item_id):
            top_level_total += 1
            if state_upper in {"READY", "READY_PLANNER", "READY_DEV"}:
                top_level_ready += 1
            if state_upper not in {"CLOSED", "PASS", "DONE"}:
                top_level_non_closed += 1
        if state_upper in {"READY", "READY_PLANNER", "READY_DEV"}:
            ready_count += 1
            if len(ready_items) < 3:
                ready_items.append(f"{item_id}:{title}")
            if len(ready_next_actions) < 5:
                ready_next_actions.append(f"{item_id}:{next_action}")
        if state == "BLOCKED" and len(blocked_items) < 3:
            blocked_items.append(f"{item_id}:{blocker_id}")

    result["ready_items"] = compact_text("; ".join(ready_items), 320) if ready_items else "none"
    result["blocked_items"] = compact_text("; ".join(blocked_items), 320) if blocked_items else "none"
    result["queue_states"] = compact_text("; ".join(queue_states[:8]), 360) if queue_states else "none"
    result["ready_next_actions"] = compact_text("; ".join(ready_next_actions), 360) if ready_next_actions else "none"
    result["queue_has_ready"] = "1" if ready_count > 0 else "0"
    result["top_level_total"] = str(top_level_total)
    result["top_level_non_closed"] = str(top_level_non_closed)
    result["top_level_ready"] = str(top_level_ready)
    # runway_short: only flag when pipeline is truly empty.
    # WAITING_DEP batches count as queued work — planner should NOT create new batches
    # just because non_closed < 20 (most of those are blocked behind sequencing).
    # Threshold: flag only when non_closed < 3 (near-empty pipeline) AND ready == 0.
    result["planner_batch_runway_short"] = "1" if (top_level_non_closed < 3 and top_level_ready == 0) else "0"
    return result


def reconcile_summary(report_path: Path) -> dict[str, str]:
    result = {
        "reconcile_at": "none",
        "reconcile_fixes_applied": "0",
        "reconcile_ready_starvation_detected": "0",
        "reconcile_stale_inprogress_marked": "0",
        "reconcile_runtime_blockers_cleared": "0",
        "reconcile_stale_locks_removed": "0",
    }
    if not report_path.exists():
        return result
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return result
    if not isinstance(payload, dict):
        return result
    result["reconcile_at"] = compact_text(str(payload.get("at", "none")), 64)
    result["reconcile_fixes_applied"] = str(int(payload.get("fixes_applied", 0) or 0))
    result["reconcile_ready_starvation_detected"] = str(int(payload.get("ready_starvation_detected", 0) or 0))
    result["reconcile_stale_inprogress_marked"] = str(int(payload.get("stale_inprogress_marked", 0) or 0))
    result["reconcile_runtime_blockers_cleared"] = str(int(payload.get("runtime_blockers_cleared", 0) or 0))
    result["reconcile_stale_locks_removed"] = str(int(payload.get("stale_locks_removed", 0) or 0))
    return result


def resolve_orchestrator_queue_path(root: Path) -> tuple[Path, str]:
    canonical = root / "logs-codex-runs/orchestrator-state/priority-queue.json"
    resolved = resolve_orchestrator_read_path(root, "priority-queue.json")
    if resolved == canonical:
        return resolved, "canonical"
    return resolved, "projection_fallback"


def dev_ready_snapshot(workboard_path: Path, role: str, limit: int = 8) -> tuple[str, str, str, str]:
    if str(role or "").strip().lower() != "dev":
        return "0", "none", "none", "0"
    if not workboard_path.exists():
        return "0", "none", "none", "0"
    try:
        board = json.loads(workboard_path.read_text(encoding="utf-8"))
    except Exception:
        return "0", "none", "none", "0"
    if not isinstance(board, dict):
        return "0", "none", "none", "0"

    ready_states = {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "REVIEW"}
    task_ids: list[str] = []
    ready_dev_count = 0
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        task_role = _canonical_role(task.get("role", ""))
        task_assignee = _canonical_role(task.get("assignee", ""))
        if "dev" not in {task_role, task_assignee}:
            continue
        state_upper = str(task.get("state", "")).strip().upper()
        if state_upper not in ready_states:
            continue
        if state_upper == "READY_DEV":
            ready_dev_count += 1
        task_id = str(task.get("id", "")).strip()
        stream_id = str(task.get("stream_id", "")).strip()
        if not task_id or not stream_id:
            continue
        task_ids.append(task_id)

    if not task_ids:
        return "0", "none", "none", str(ready_dev_count)
    bounded = task_ids[: max(1, limit)]
    return str(len(task_ids)), ",".join(bounded), "role_task_present", str(ready_dev_count)
def directives_tail(path: Path, role: str, now_iso: str) -> str:
    if not path.exists():
        return "none"
    try:
        raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return "none"
    lines = raw_lines[-220:]
    records: list[dict[str, str]] = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        expires_at = str(obj.get("expires_at", "")).strip()
        if expires_at and expires_at <= now_iso:
            continue
        targets = obj.get("targets", [])
        if isinstance(targets, list):
            target_values = [str(x) for x in targets]
        else:
            target_values = []
        if "all" not in target_values and role not in target_values:
            continue
        records.append(
            {
                "ts": str(obj.get("ts", "")),
                "id": str(obj.get("id", "DIR?")),
                "kind": str(obj.get("kind", "policy")),
                "msg": str(obj.get("msg", "")),
            }
        )

    if not records:
        return "none"
    records.sort(key=lambda rec: rec.get("ts", ""), reverse=True)
    parts = [f"{rec['id']}:{rec['kind']}:{rec['msg']}" for rec in records[:3]]
    return compact_text(" ; ".join(parts), 340)


def agent_messages_tail(path: Path, role: str, now_iso: str, limit: int) -> tuple[str, str]:
    if not path.exists():
        return "none", "none"
    try:
        raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return "none", "none"

    posts: dict[str, dict] = {}
    closed: set[str] = set()
    delivered: dict[str, set[str]] = {}
    rows = raw_lines[-2000:]
    for raw in rows:
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        event = str(obj.get("event", "")).strip()
        message_id = str(obj.get("message_id", "")).strip()
        if not message_id:
            continue
        if event == "message_posted":
            posts[message_id] = obj
        elif event == "message_closed":
            closed.add(message_id)
        elif event == "message_delivered":
            role_delivered = str(obj.get("role", "")).strip().lower()
            if role_delivered:
                delivered.setdefault(message_id, set()).add(role_delivered)

    active: list[dict[str, str]] = []
    role_l = role.strip().lower()
    for message_id, post in posts.items():
        if message_id in closed:
            continue
        expires_at = str(post.get("expires_at_utc") or post.get("expires_at") or "").strip()
        if expires_at and expires_at <= now_iso:
            continue
        targets_raw = post.get("targets", [])
        targets = [str(x).strip().lower() for x in targets_raw] if isinstance(targets_raw, list) else []
        if "all" not in targets and role_l not in targets:
            continue
        if role_l in delivered.get(message_id, set()):
            continue
        active.append(
            {
                "ts": str(post.get("ts_utc") or post.get("ts") or ""),
                "id": message_id,
                "priority": str(post.get("priority", "normal")),
                "from": str(post.get("source") or post.get("from") or ""),
                "msg": compact_text(str(post.get("payload") or post.get("msg") or ""), 160),
            }
        )

    if not active:
        return "none", "none"
    active.sort(key=lambda rec: rec.get("ts", ""), reverse=True)
    bounded_limit = max(1, min(limit, 3))
    active = active[:bounded_limit]
    tail = " ; ".join(
        f"MSG:{rec['id']}:from={rec['from']}:{rec['msg']}"
        for rec in active
    )
    message_ids = ",".join(rec["id"] for rec in active if rec.get("id"))
    return compact_text(tail, 420), (message_ids or "none")


def main() -> int:
    if len(sys.argv) not in (15, 17):
        print(
            "usage: role_runtime_context.py <role> <root> <state_dir> <role_memory_dir> <team_chat_file> <team_iter_file> "
            "<directive_bus_file> <trace_file> <last_contract_file> <queue_version> <workboard_version> "
            "<workboard_role_has_work> <workboard_role_has_ready> <workboard_role_has_in_progress> "
            "[<agent_message_bus_file> <agent_message_limit>]",
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1]
    root = Path(sys.argv[2])
    state_dir = Path(sys.argv[3])
    role_memory_dir = Path(sys.argv[4])
    team_chat_file = Path(sys.argv[5])
    team_iter_file = Path(sys.argv[6])
    directive_bus_file = Path(sys.argv[7])
    trace_file = Path(sys.argv[8])
    last_contract_file = Path(sys.argv[9])
    queue_version = sys.argv[10] or "queue_unknown"
    workboard_version = sys.argv[11] or "workboard_unknown"
    workboard_role_has_work = sys.argv[12] or "0"
    workboard_role_has_ready = sys.argv[13] or "0"
    workboard_role_has_in_progress = sys.argv[14] or "0"
    agent_message_bus_file = Path(sys.argv[15]) if len(sys.argv) == 17 else Path()
    if len(sys.argv) == 17:
        try:
            agent_message_limit = int(sys.argv[16] or "3")
        except Exception:
            agent_message_limit = 3
    else:
        agent_message_limit = 3

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue_path, orchestrator_source = resolve_orchestrator_queue_path(root)
    runtime_truth = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24)
    event_store_primary = bool(runtime_truth.get("event_store_primary", False))
    if (not event_store_primary) and len(sys.argv) != 17:
        agent_message_bus_file = resolve_orchestrator_read_path(root, "agent-message-bus.jsonl")
    queue_data = queue_summary(queue_path)
    workboard_path = queue_path.parent / "parallel-workstreams.json"
    reconcile_data = reconcile_summary(queue_path.parent / "state-reconcile-report.json")
    workstate_hint = "secondary_compat_only"

    parallel_hint = runtime_parallel_hint(queue_path, role, 240)
    workboard_context = runtime_workboard_context(queue_path, role, 300)
    publication_channels = publication_channels_hint(queue_path, team_chat_file, directive_bus_file, 360)
    if event_store_primary:
        worker_summary = "none"
        planner_subagent_summary = "none"
    else:
        worker_summary = dynamic_worker_context(root, role)
        planner_subagent_summary = planner_subagent_context(root, role)
    product_priority_summary = product_priority_context(root)

    agent_memory = compact_file_tail(role_memory_dir / f"{role}.md", 8, 180)
    self_last_contract = compact_text(read_last_contract_hint(last_contract_file, "self"), 200)
    peer_contracts = peer_contracts_hint(state_dir, role)
    team_chat_tail = compact_file_tail(team_chat_file, 4, 140)
    team_iteration_tail = compact_file_tail(team_iter_file, 2, 100)
    directives = directives_tail(directive_bus_file, role, now_iso)
    if event_store_primary:
        agent_messages_tail_text, agent_message_ids = ("secondary_compat_only", "secondary_compat_only")
    else:
        agent_messages_tail_text, agent_message_ids = agent_messages_tail(
            agent_message_bus_file,
            role,
            now_iso,
            max(1, agent_message_limit),
        )
    trace_tail = compact_file_tail(trace_file, 3, 140)
    dev_ready_count, dev_ready_task_ids, dev_ready_reason, dev_ready_dev_count = dev_ready_snapshot(workboard_path, role)
    dev_has_ready_task = "1" if role == "dev" and str(workboard_role_has_ready) == "1" else "0"
    dev_wait_allowed = (
        "1"
        if role == "dev"
        and dev_has_ready_task != "1"
        and str(dev_ready_count) == "0"
        and str(workboard_role_has_in_progress) != "1"
        else "0"
    )

    if role == "admin":
        line = (
            "RUNTIME_CONTEXT: "
            f"now_iso={now_iso} | "
            f"queue_has_ready={queue_data['queue_has_ready']} | "
            f"orchestrator_source={orchestrator_source} | "
            f"queue_version={queue_version} | "
            f"workboard_version={workboard_version} | "
            f"ready_items={queue_data['ready_items']} | "
            f"ready_next_actions={queue_data['ready_next_actions']} | "
            f"blocked_items={queue_data['blocked_items']} | "
            f"reconcile_at={reconcile_data['reconcile_at']} | "
            f"reconcile_fixes_applied={reconcile_data['reconcile_fixes_applied']} | "
            f"reconcile_ready_starvation_detected={reconcile_data['reconcile_ready_starvation_detected']} | "
            f"reconcile_runtime_blockers_cleared={reconcile_data['reconcile_runtime_blockers_cleared']} | "
            f"reconcile_stale_locks_removed={reconcile_data['reconcile_stale_locks_removed']} | "
            f"workstate_hint={workstate_hint} | "
            f"workboard_role_has_work={workboard_role_has_work} | "
            f"workboard_role_has_ready={workboard_role_has_ready} | "
            f"workboard_role_has_in_progress={workboard_role_has_in_progress} | "
            f"dev_has_ready_task={dev_has_ready_task} | "
            f"dev_ready_count={dev_ready_count} | "
            f"dev_ready_task_ids={dev_ready_task_ids} | "
            f"dev_ready_reason={dev_ready_reason} | "
            f"dev_ready_dev_count={dev_ready_dev_count} | "
            f"dev_wait_allowed={dev_wait_allowed} | "
            f"self_last_contract={self_last_contract} | "
            f"peer_contracts={peer_contracts} | "
            f"workboard_context={workboard_context} | "
            f"worker_summary={worker_summary} | "
            f"planner_subagent_summary={planner_subagent_summary} | "
            f"product_priority_summary={product_priority_summary} | "
            f"agent_messages_tail={agent_messages_tail_text} | "
            f"agent_message_ids={agent_message_ids} | "
            f"trace_tail={trace_tail} | "
            "execution_rules=debottleneck,keep_runtime_green,never_block_without_runtime_proof"
        )
    else:
        line = (
            "RUNTIME_CONTEXT: "
            f"now_iso={now_iso} | "
            f"queue_states={queue_data['queue_states']} | "
            f"queue_has_ready={queue_data['queue_has_ready']} | "
            f"orchestrator_source={orchestrator_source} | "
            f"top_level_total={queue_data['top_level_total']} | "
            f"top_level_non_closed={queue_data['top_level_non_closed']} | "
            f"top_level_ready={queue_data['top_level_ready']} | "
            f"planner_batch_runway_short={queue_data['planner_batch_runway_short']} | "
            f"queue_version={queue_version} | "
            f"workboard_version={workboard_version} | "
            f"ready_items={queue_data['ready_items']} | "
            f"ready_next_actions={queue_data['ready_next_actions']} | "
            f"blocked_items={queue_data['blocked_items']} | "
            f"reconcile_at={reconcile_data['reconcile_at']} | "
            f"reconcile_fixes_applied={reconcile_data['reconcile_fixes_applied']} | "
            f"reconcile_ready_starvation_detected={reconcile_data['reconcile_ready_starvation_detected']} | "
            f"reconcile_stale_inprogress_marked={reconcile_data['reconcile_stale_inprogress_marked']} | "
            f"workstate_hint={workstate_hint} | "
            f"parallel_hint={parallel_hint} | "
            f"workboard_role_has_work={workboard_role_has_work} | "
            f"workboard_role_has_ready={workboard_role_has_ready} | "
            f"workboard_role_has_in_progress={workboard_role_has_in_progress} | "
            f"dev_has_ready_task={dev_has_ready_task} | "
            f"dev_ready_count={dev_ready_count} | "
            f"dev_ready_task_ids={dev_ready_task_ids} | "
            f"dev_ready_reason={dev_ready_reason} | "
            f"dev_ready_dev_count={dev_ready_dev_count} | "
            f"dev_wait_allowed={dev_wait_allowed} | "
            f"agent_memory={agent_memory} | "
            f"self_last_contract={self_last_contract} | "
            f"peer_contracts={peer_contracts} | "
            f"workboard_context={workboard_context} | "
            f"worker_summary={worker_summary} | "
            f"planner_subagent_summary={planner_subagent_summary} | "
            f"product_priority_summary={product_priority_summary} | "
            f"publication_channels={publication_channels} | "
            f"team_chat_tail={team_chat_tail} | "
            f"team_iteration_tail={team_iteration_tail} | "
            f"directives_tail={directives} | "
            f"agent_messages_tail={agent_messages_tail_text} | "
            f"agent_message_ids={agent_message_ids} | "
            f"trace_tail={trace_tail} | "
            "execution_rules=respect_run_lock,update_tasks,ack_handoffs,read_publication_channels,assess_impact"
        )
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
