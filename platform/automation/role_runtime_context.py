#!/usr/bin/env python3
"""Build compact runtime context consumed by role runner prompts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


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
    priority_roles = ["planner", "backend_engineer", "frontend_engineer", "data_analyst", "dev"]
    role_files = sorted(state_dir.glob("*.last_contract"), key=lambda p: p.stat().st_mtime, reverse=True)
    hints: list[str] = []
    seen: set[str] = set()
    # Priorité aux rôles importants d'abord
    for prio in priority_roles:
        if prio == role:
            continue
        f = state_dir / f"{prio}.last_contract"
        if f.exists():
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


def run_parallel_workstream(script_path: Path, role: str, subcmd: str, limit: int, max_chars: int) -> str:
    if not script_path.exists():
        return "none"
    cmd = [sys.executable, str(script_path), subcmd, "--role", role, "--limit", str(limit)]
    try:
        cp = subprocess.run(cmd, text=True, capture_output=True, check=False)
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
        if item_id and state_upper in {"READY", "IN_PROGRESS", "BLOCKED"}:
            queue_states.append(f"{item_id}={state}")
        if re.fullmatch(r"BATCH-\d{2}", item_id):
            top_level_total += 1
            if state_upper == "READY":
                top_level_ready += 1
            if state_upper not in {"CLOSED", "PASS"}:
                top_level_non_closed += 1
        if state == "READY":
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
    result["planner_batch_runway_short"] = "1" if top_level_non_closed < 20 else "0"
    return result


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


def main() -> int:
    if len(sys.argv) != 14:
        print(
            "usage: role_runtime_context.py <role> <root> <state_dir> <role_memory_dir> <team_chat_file> <team_iter_file> "
            "<directive_bus_file> <trace_file> <last_contract_file> <queue_version> <workboard_version> "
            "<workboard_role_has_work> <workboard_role_has_in_progress>",
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
    workboard_role_has_in_progress = sys.argv[13] or "0"

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    queue_data = queue_summary(root / "docs/orchestrator-ops/priority-queue.json")
    workstate_primary = root / "docs/product/planning/WORKSTATE.md"
    workstate_fallback = root / "docs/planning/WORKSTATE.md"
    workstate_target = workstate_primary if workstate_primary.exists() else workstate_fallback
    workstate_hint = compact_file_tail(workstate_target, 8, 160)

    parallel_script = root / "scripts/parallel_workstream.py"
    parallel_hint = run_parallel_workstream(parallel_script, role, "status", 3, 240)
    workboard_context = run_parallel_workstream(parallel_script, role, "context", 3, 300)
    publication_channels = run_parallel_workstream(parallel_script, role, "channels", 4, 360)

    agent_memory = compact_file_tail(role_memory_dir / f"{role}.md", 8, 180)
    self_last_contract = compact_text(read_last_contract_hint(last_contract_file, "self"), 200)
    peer_contracts = peer_contracts_hint(state_dir, role)
    team_chat_tail = compact_file_tail(team_chat_file, 4, 140)
    team_iteration_tail = compact_file_tail(team_iter_file, 2, 100)
    directives = directives_tail(directive_bus_file, role, now_iso)
    trace_tail = compact_file_tail(trace_file, 3, 140)

    if role == "admin":
        line = (
            "RUNTIME_CONTEXT: "
            f"now_iso={now_iso} | "
            f"queue_has_ready={queue_data['queue_has_ready']} | "
            f"queue_version={queue_version} | "
            f"workboard_version={workboard_version} | "
            f"ready_items={queue_data['ready_items']} | "
            f"ready_next_actions={queue_data['ready_next_actions']} | "
            f"blocked_items={queue_data['blocked_items']} | "
            f"workstate_hint={workstate_hint} | "
            f"workboard_role_has_work={workboard_role_has_work} | "
            f"workboard_role_has_in_progress={workboard_role_has_in_progress} | "
            f"self_last_contract={self_last_contract} | "
            f"peer_contracts={peer_contracts} | "
            f"workboard_context={workboard_context} | "
            f"trace_tail={trace_tail} | "
            "execution_rules=debottleneck,keep_runtime_green,never_block_without_runtime_proof"
        )
    else:
        line = (
            "RUNTIME_CONTEXT: "
            f"now_iso={now_iso} | "
            f"queue_states={queue_data['queue_states']} | "
            f"queue_has_ready={queue_data['queue_has_ready']} | "
            f"top_level_total={queue_data['top_level_total']} | "
            f"top_level_non_closed={queue_data['top_level_non_closed']} | "
            f"top_level_ready={queue_data['top_level_ready']} | "
            f"planner_batch_runway_short={queue_data['planner_batch_runway_short']} | "
            f"queue_version={queue_version} | "
            f"workboard_version={workboard_version} | "
            f"ready_items={queue_data['ready_items']} | "
            f"ready_next_actions={queue_data['ready_next_actions']} | "
            f"blocked_items={queue_data['blocked_items']} | "
            f"workstate_hint={workstate_hint} | "
            f"parallel_hint={parallel_hint} | "
            f"workboard_role_has_work={workboard_role_has_work} | "
            f"workboard_role_has_in_progress={workboard_role_has_in_progress} | "
            f"agent_memory={agent_memory} | "
            f"self_last_contract={self_last_contract} | "
            f"peer_contracts={peer_contracts} | "
            f"workboard_context={workboard_context} | "
            f"publication_channels={publication_channels} | "
            f"team_chat_tail={team_chat_tail} | "
            f"team_iteration_tail={team_iteration_tail} | "
            f"directives_tail={directives} | "
            f"trace_tail={trace_tail} | "
            "execution_rules=respect_run_lock,update_tasks,ack_handoffs,read_publication_channels,assess_impact"
        )
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
