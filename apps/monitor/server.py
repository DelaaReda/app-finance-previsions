#!/usr/bin/env python3
"""Finance Copilot — Monitor Web Server — http://localhost:7779"""
from __future__ import annotations
import json, os, re, subprocess, time
import socket
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

def _latest_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for p in paths:
        try:
            if p.exists():
                latest = max(latest, float(p.stat().st_mtime))
        except Exception:
            continue
    return latest

def _workspace_writable(p: Path) -> bool:
    log_dir = p / "logs-codex-runs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    return os.access(log_dir, os.W_OK)

def _load_json_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _orchestrator_root_for_workspace(p: Path) -> Path | None:
    canonical = p / "docs" / "operations" / "orchestrator"
    legacy = p / "docs" / "orchestrator-ops"
    if canonical.exists() and legacy.exists():
        try:
            return canonical if canonical.stat().st_mtime >= legacy.stat().st_mtime else legacy
        except Exception:
            return canonical
    if canonical.exists():
        return canonical
    if legacy.exists():
        return legacy
    return None

def _score_root_candidate(p: Path) -> float:
    score = 0.0
    orch = _orchestrator_root_for_workspace(p)
    if orch is not None:
        score += 100.0
        queue_file = orch / "priority-queue.json"
        workboard_file = orch / "parallel-workstreams.json"
        queue_data = _load_json_file(queue_file) if queue_file.exists() else {}
        workboard_data = _load_json_file(workboard_file) if workboard_file.exists() else {}
        queue_items = queue_data.get("items", [])
        workboard_tasks = workboard_data.get("tasks", [])
        if isinstance(queue_items, list):
            score += min(40.0, float(len(queue_items)))
        if isinstance(workboard_tasks, list):
            score += min(40.0, float(len(workboard_tasks)))
        if queue_file.exists():
            score += 8.0
        if workboard_file.exists():
            score += 8.0
    tick_dir = p / "logs-codex-runs" / "fc-ticks"
    runner_dir = p / "logs-codex-runs" / "role-runner"
    if tick_dir.exists():
        score += 60.0
    if runner_dir.exists():
        score += 25.0
    if _workspace_writable(p):
        score += 55.0
    else:
        score -= 80.0
    # Bias toward the workspace that has the freshest runtime traces.
    tick_logs = list(tick_dir.glob("*.tick.log")) if tick_dir.exists() else []
    runner_logs = list(runner_dir.glob("*.live.log")) if runner_dir.exists() else []
    latest = _latest_mtime(tick_logs + runner_logs)
    if latest > 0:
        # More recent is better: invert by subtracting age bucket.
        age_minutes = max(0.0, (time.time() - latest) / 60.0)
        score += max(0.0, 80.0 - min(80.0, age_minutes))
    # Very light preference for shared VM mapping only when writable.
    if "/shared/" in str(p) and _workspace_writable(p):
        score += 3.0
    return score

def resolve_root() -> Path:
    env_root = os.environ.get("FC_MONITOR_ROOT", "").strip()
    if env_root:
        p = Path(env_root).expanduser()
        if p.exists():
            return p
    candidates = [
        Path("/home/venom/shared/analyse-financiere"),
        Path("/home/venom/analyse-financiere"),
        Path("/Users/venom/Documents/analyse-financiere"),
        Path(__file__).resolve().parents[2],
    ]
    scored: list[tuple[float, Path]] = []
    for p in candidates:
        if not p.exists():
            continue
        scored.append((_score_root_candidate(p), p))
    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
    return Path(__file__).resolve().parents[2]


ROOT = resolve_root()
STATE = Path(os.environ.get("FC_MONITOR_STATE_DIR", "/home/venom/.openclaw/cron/role-state")).expanduser()
INSTANCE_ID = os.environ.get(
    "FC_MONITOR_INSTANCE_ID",
    f"{socket.gethostname()}:{ROOT}",
)
CORE_ROLES = ("planner", "dev", "admin")
ERROR_FEED_RECENT_MINUTES = max(10, int(os.environ.get("FC_MONITOR_ERROR_FEED_RECENT_MINUTES", "90")))
RUNTIME_DIAG_RECENT_MINUTES = max(10, int(os.environ.get("FC_MONITOR_RUNTIME_DIAG_RECENT_MINUTES", "90")))
DEFAULT_SCHEDULE_MAP = {
    "planner": [0, 22, 44],
    "dev": [6, 28, 50],
    "admin": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
}
ROLE_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _ordered_roles(roles: list[str] | set[str] | tuple[str, ...]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for role in roles:
        r = (role or "").strip()
        if not r or not ROLE_NAME_RE.fullmatch(r):
            continue
        if r in seen:
            continue
        seen.add(r)
        cleaned.append(r)
    priority = list(CORE_ROLES)
    ordered = [r for r in priority if r in cleaned]
    ordered += sorted(r for r in cleaned if r not in priority)
    return tuple(ordered)


def _roles_from_topology() -> tuple[str, ...]:
    candidates = [
        ROOT / "docs" / "operations" / "orchestrator" / "parallel-role-topology-active.json",
        ROOT / "docs" / "orchestrator-ops" / "parallel-role-topology-active.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        roles_raw = data.get("roles") if isinstance(data, dict) else None
        if not isinstance(roles_raw, list):
            continue
        roles: list[str] = []
        for item in roles_raw:
            if isinstance(item, str):
                role = item.strip()
                if role:
                    roles.append(role)
                continue
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            enabled = item.get("enabled", True)
            if role and enabled is not False:
                roles.append(role)
        ordered = _ordered_roles(roles)
        if ordered:
            return ordered
    return ()


def _roles_from_crontab() -> tuple[str, ...]:
    try:
        proc = subprocess.run(
            ["crontab", "-l"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ()
    if proc.returncode != 0:
        return ()
    roles: list[str] = []
    for line in (proc.stdout or "").splitlines():
        if "fc_agent_tick.sh" not in line:
            continue
        m = re.search(r"fc_agent_tick\.sh\s+([A-Za-z0-9_]+)", line)
        if not m:
            continue
        roles.append(m.group(1).strip())
    ordered = _ordered_roles(roles)
    return ordered if ordered else ()

def discover_roles() -> tuple[str, ...]:
    env_roles = [r.strip() for r in os.environ.get("FC_MONITOR_ROLES", "").split(",") if r.strip()]
    if env_roles:
        ordered = _ordered_roles(env_roles)
        if ordered:
            return ordered
    cron_roles = _roles_from_crontab()
    if cron_roles:
        return cron_roles
    topology_roles = _roles_from_topology()
    if topology_roles:
        return topology_roles
    return CORE_ROLES


def active_roles() -> tuple[str, ...]:
    roles = discover_roles()
    return roles if roles else CORE_ROLES


ROLE_CANONICAL_MAP = {
    "analyst": "planner",
    "architect": "planner",
    "po": "planner",
    "scrum_master": "planner",
    "backend_engineer": "dev",
    "frontend_engineer": "dev",
    "data_analyst": "dev",
    "infra_engineer": "dev",
    "integrator": "dev",
    "tester": "dev",
    "qa": "dev",
    "clawsentinel": "admin",
}


def canonical_role(role: str) -> str:
    raw = (role or "").strip()
    if not raw:
        return "?"
    return ROLE_CANONICAL_MAP.get(raw, raw)


def _batch_sort_key(batch_id: str) -> tuple[int, str]:
    m = re.search(r"BATCH-(\d+)", str(batch_id or ""))
    return (int(m.group(1)) if m else 10**9, str(batch_id or ""))


def _merge_queue_display_rows(queue_items: list[dict], derived_batches: list[dict]) -> list[dict]:
    """Use queue as source-of-truth for list coverage and derived batches for live task counters."""
    derived_map: dict[str, dict] = {
        str(b.get("id", "")).strip(): b for b in derived_batches if str(b.get("id", "")).strip()
    }
    rows: list[dict] = []
    seen: set[str] = set()

    for item in queue_items:
        batch_id = str(item.get("id", "")).strip()
        if not batch_id:
            continue
        row = {
            "id": batch_id,
            "state": str(item.get("state", "")).upper() or "UNKNOWN",
        }
        if batch_id in derived_map:
            row.update(derived_map[batch_id])
            row["state"] = str(row.get("state", "")).upper() or "UNKNOWN"
        rows.append(row)
        seen.add(batch_id)

    for batch_id, derived in derived_map.items():
        if batch_id in seen:
            continue
        row = dict(derived)
        row["id"] = batch_id
        row["state"] = str(row.get("state", "")).upper() or "UNKNOWN"
        rows.append(row)

    rows.sort(key=lambda r: _batch_sort_key(str(r.get("id", ""))))
    return rows


LOG_KIND_LABELS = {
    "tick": "fc-ticks",
    "cron": "fc-cron",
    "runner": "runner-live",
    "events": "runner-events",
    "contract": "last-contract",
}

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def jload(p):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except: return {}

def orchestrator_file(rel: str) -> Path:
    rel = (rel or "").strip().lstrip("/")
    canonical = ROOT / "docs" / "operations" / "orchestrator" / rel
    legacy = ROOT / "docs" / "orchestrator-ops" / rel
    existing = [p for p in (canonical, legacy) if p.exists()]
    if existing:
        try:
            existing.sort(key=lambda p: float(p.stat().st_mtime), reverse=True)
        except Exception:
            pass
        return existing[0]
    return canonical


def monitor_latest_snapshot() -> dict:
    data = jload(orchestrator_file("executors-monitoring-latest.json"))
    return data if isinstance(data, dict) else {}

def contract(role):
    f = STATE / f"{role}.last_contract"
    if not f.exists(): return {}
    d = {}
    for l in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" in l:
            k,_,v = l.partition(":"); d[k.strip()] = v.strip()
    return d

def contract_raw(role):
    f = STATE / f"{role}.last_contract"
    if not f.exists(): return ""
    return f.read_text(encoding="utf-8", errors="ignore")

def parse_evidence_kv(evidence_line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = (evidence_line or "").strip()
    if not raw:
        return out
    for part in raw.split(";"):
        seg = part.strip()
        if not seg or "=" not in seg:
            continue
        k, v = seg.split("=", 1)
        key = k.strip()
        if not key:
            continue
        out[key] = v.strip()
    return out

def parse_contract_fields(role: str) -> dict:
    c = contract(role)
    evidence = parse_evidence_kv(c.get("EVIDENCE", ""))
    run_note = evidence.get("run_note", "")
    run_note_words = len([w for w in run_note.split() if w.strip()])
    task_update = evidence.get("task_update", "").strip().lower()
    issues: list[str] = []
    checks = {
        "task_update": bool(task_update),
        "run_note_5w": run_note_words >= 5,
        "root_cause": bool(evidence.get("root_cause", "").strip()),
        "fix_applied": bool(evidence.get("fix_applied", "").strip()),
        "verify": bool(evidence.get("verify", "").strip()),
        "reuse_check": bool(evidence.get("reuse_check", "").strip()),
        "architecture_check": bool(evidence.get("architecture_check", "").strip()),
        "vision_alignment": bool(evidence.get("vision_alignment", "").strip()),
        "qa_proof": bool(evidence.get("qa_proof", "").strip()),
    }
    # Contextual requirements based on task_update.
    if task_update in {"claim", "complete", "handoff"}:
        for key in ("root_cause", "reuse_check"):
            if not checks[key]:
                issues.append(f"missing_{key}")
    if task_update in {"complete", "handoff"}:
        for key in ("fix_applied", "verify"):
            if not checks[key]:
                issues.append(f"missing_{key}")
    if role == "dev" and task_update in {"claim", "complete", "handoff"}:
        for key in ("architecture_check", "vision_alignment"):
            if not checks[key]:
                issues.append(f"missing_{key}")
        if task_update in {"complete", "handoff"} and not checks["qa_proof"]:
            issues.append("missing_qa_proof")
    if not checks["run_note_5w"]:
        issues.append("run_note_too_short")
    score = 100
    score -= 12 * len(issues)
    score = max(0, min(100, score))
    if score >= 80:
        quality = "STRONG"
    elif score >= 55:
        quality = "MEDIUM"
    else:
        quality = "WEAK"
    return {
        "role": role,
        "contract": c,
        "evidence": evidence,
        "task_update": task_update or "unknown",
        "run_note_words": run_note_words,
        "quality_score": score,
        "quality": quality,
        "issues": issues,
    }

def tick_age(role):
    log = ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    if not log.exists(): return None
    for l in reversed(log.read_text(encoding="utf-8",errors="ignore").splitlines()):
        m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", l)
        if m and any(x in l for x in ("[END]","[SKIP]","[BACKOFF]")):
            try:
                ep = datetime.strptime(m.group(1),"%Y-%m-%dT%H:%M:%S").astimezone(timezone.utc).timestamp()
                return int((time.time()-ep)/60)
            except: pass
    return None

def tick_hist(role, n=25):
    log = ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    if not log.exists(): return []
    out = []
    for l in reversed(log.read_text(encoding="utf-8",errors="ignore").splitlines()):
        if len(out)>=n: break
        if not any(x in l for x in ("[END]","[SKIP]","[BACKOFF]")): continue
        ts=re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",l)
        rc=re.search(r"rc=(\d+)",l); ag=re.search(r"agent=(\w+)",l)
        out.append({"ts":ts.group(1) if ts else "?","rc":int(rc.group(1)) if rc else None,
                    "agent":ag.group(1) if ag else "?",
                    "type":"SKIP" if "[SKIP]" in l else "BACKOFF" if "[BACKOFF]" in l else "END"})
    return out

def _tail_lines(path: Path, n: int) -> list[str]:
    if n <= 0:
        return []
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
    except Exception:
        return []

def _tail_jsonl(path: Path, n: int) -> list[dict]:
    if n <= 0:
        return []
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            if isinstance(item, dict):
                out.append(item)
    except Exception:
        return []
    return out

def _state_counts(items: list[dict], key: str = "state") -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for item in items:
        val = str(item.get(key, "?") or "?").upper()
        counts[val] += 1
    return dict(counts)

def _queue_workboard_mismatches(queue_items: list[dict], tasks: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in queue_items:
        batch_id = str(item.get("id", "")).strip()
        if not batch_id or not re.fullmatch(r"BATCH-\d{2}", batch_id):
            continue
        q_state = str(item.get("state", "")).upper()
        related = [t for t in tasks if str(t.get("id", "")).startswith(f"{batch_id}-")]
        if not related:
            # Planned/queued-only batches can legitimately have no instantiated tasks yet.
            if q_state in {"WAITING_DEP", "PLANNED", "READY_FOR_PARALLEL_DISPATCH"}:
                continue
            out.append({"batch": batch_id, "issue": "no_tasks_for_batch", "queue_state": q_state})
            continue
        ready = sum(1 for t in related if str(t.get("state", "")).upper() == "READY")
        in_prog = sum(1 for t in related if str(t.get("state", "")).upper() == "IN_PROGRESS")
        done = sum(1 for t in related if str(t.get("state", "")).upper() in {"DONE", "CLOSED", "PASS"})
        if q_state == "READY" and (ready + in_prog) == 0:
            out.append({"batch": batch_id, "issue": "queue_ready_but_no_ready_task", "queue_state": q_state, "tasks_done": done})
        if q_state == "IN_PROGRESS" and in_prog == 0:
            out.append({"batch": batch_id, "issue": "queue_in_progress_but_no_task_in_progress", "queue_state": q_state, "tasks_ready": ready})
    return out


def _batch_prefix(task_id: str) -> str:
    raw = (task_id or "").strip()
    m = re.match(r"^(BATCH-\d{2})\b", raw)
    if m:
        return m.group(1)
    parts = raw.split("-")
    if len(parts) >= 2 and parts[0] == "BATCH":
        return "-".join(parts[:2])
    return ""


def _derive_batches_from_workboard(tasks: list[dict]) -> list[dict]:
    by_batch: dict[str, dict] = {}
    for t in tasks:
        bid = _batch_prefix(str(t.get("id", "")))
        if not bid:
            continue
        state = str(t.get("state", "")).upper() or "UNKNOWN"
        node = by_batch.setdefault(bid, {"id": bid, "task_states": defaultdict(int), "tasks_total": 0})
        node["task_states"][state] += 1
        node["tasks_total"] += 1

    out: list[dict] = []
    for bid, node in by_batch.items():
        states: dict[str, int] = dict(node["task_states"])
        in_prog = states.get("IN_PROGRESS", 0)
        ready = states.get("READY", 0)
        open_non_ready = sum(v for k, v in states.items() if k not in {"DONE", "CLOSED", "PASS", "READY", "IN_PROGRESS"})
        closed = states.get("DONE", 0) + states.get("CLOSED", 0) + states.get("PASS", 0)
        total = int(node["tasks_total"])

        if in_prog > 0:
            batch_state = "IN_PROGRESS"
        elif ready > 0:
            batch_state = "READY"
        elif closed >= total and total > 0:
            batch_state = "CLOSED"
        elif open_non_ready > 0:
            batch_state = "WAITING_DEP"
        else:
            batch_state = "WAITING_DEP"

        out.append({
            "id": bid,
            "state": batch_state,
            "tasks_total": total,
            "ready": ready,
            "in_progress": in_prog,
            "closed": closed,
            "state_counts": states,
        })

    def _batch_num(item: dict) -> int:
        m = re.search(r"BATCH-(\d+)", str(item.get("id", "")))
        return int(m.group(1)) if m else 10**9

    out.sort(key=lambda x: (_batch_num(x), str(x.get("id", ""))))
    return out

def _find_last_tick_markers(lines: list[str]) -> tuple[str, str]:
    last_start = ""
    last_end = ""
    for line in reversed(lines):
        if not last_end and any(marker in line for marker in ("[END]", "[SKIP]", "[BACKOFF]")):
            last_end = line
        if not last_start and "[START]" in line:
            last_start = line
        if last_start and last_end:
            break
    return last_start, last_end

def latest_execution(role: str, tick_n: int = 35, runner_n: int = 55) -> dict:
    tick_log = ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    runner_log = ROOT / f"logs-codex-runs/role-runner/{role}.live.log"
    events_log = ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    tick_lines = _tail_lines(tick_log, tick_n)
    runner_lines = _tail_lines(runner_log, runner_n)
    events_lines = _tail_lines(events_log, runner_n)
    last_start, last_end = _find_last_tick_markers(tick_lines)

    rc_match = re.search(r"rc=(\d+)", last_end or "")
    agent_match = re.search(r"agent=(\w+)", last_end or "")
    ts_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", last_end or "")
    if not ts_match:
        ts_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", last_start or "")

    merged = tick_lines + runner_lines + events_lines
    sev = defaultdict(int)
    for line in merged:
        sev[classify_log_line(line)] += 1

    return {
        "role": role,
        "tick_tail": tick_lines,
        "runner_tail": runner_lines,
        "events_tail": events_lines,
        "last_start": last_start,
        "last_end": last_end,
        "last_ts": ts_match.group(1) if ts_match else "",
        "last_rc": int(rc_match.group(1)) if rc_match else None,
        "last_agent": agent_match.group(1) if agent_match else "",
        "severity_counts": dict(sev),
    }

def _parse_runner_events(role: str, n: int = 160) -> list[dict]:
    log = ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    lines = _tail_lines(log, n)
    out: list[dict] = []
    for line in lines:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+role=([a-zA-Z0-9_]+)\s+event=([a-zA-Z0-9_]+)\s+detail=(.*)$", line.strip())
        if not m:
            continue
        out.append({
            "ts": m.group(1),
            "role": m.group(2),
            "event": m.group(3),
            "detail": m.group(4),
        })
    return out

def execution_insight(role: str) -> dict:
    ex = latest_execution(role, tick_n=40, runner_n=80)
    cf = parse_contract_fields(role)
    events = _parse_runner_events(role, n=180)

    action_events = {
        "primary_structured_ok",
        "retry_structured_ok",
        "codex_fallback_structured_ok",
        "final_output",
    }
    error_hint = re.compile(r"(checkpoint_fallback|prompt_stall_abort|session_not_ready|contract_guard_external_failed|syntax_error|module not found|traceback|error)", re.I)
    warn_hint = re.compile(r"(rate_limit|backoff|retry_prompt_begin|go_with_caution|monitoring_publish_skipped)", re.I)

    e_counts: defaultdict[str, int] = defaultdict(int)
    interesting: list[dict] = []
    for ev in events:
        ev_name = str(ev.get("event", ""))
        detail = str(ev.get("detail", ""))
        if ev_name in action_events:
            e_counts["action"] += 1
            interesting.append(ev)
            continue
        if error_hint.search(ev_name) or error_hint.search(detail):
            e_counts["error"] += 1
            interesting.append(ev)
            continue
        if warn_hint.search(ev_name) or warn_hint.search(detail):
            e_counts["warn"] += 1
            continue
        e_counts["meta"] += 1

    task_update = cf.get("task_update", "unknown")
    quality = cf.get("quality", "WEAK")
    quality_score = int(cf.get("quality_score", 0))
    issues = cf.get("issues", [])

    if task_update in {"claim", "complete", "handoff"} and quality in {"STRONG", "MEDIUM"}:
        activity = "PRODUCTIVE"
    elif task_update in {"none_no_ready", "none_no_signal", "analysis_only"}:
        activity = "IDLE"
    else:
        activity = "CHECK"

    return {
        "role": role,
        "activity": activity,
        "task_update": task_update,
        "quality": quality,
        "quality_score": quality_score,
        "issues": issues[:8],
        "run_note_words": cf.get("run_note_words", 0),
        "last_rc": ex.get("last_rc"),
        "last_ts": ex.get("last_ts"),
        "last_agent": ex.get("last_agent"),
        "severity_counts": ex.get("severity_counts", {}),
        "event_counts": dict(e_counts),
        "interesting_events": interesting[-8:],
        "runner_events_tail": events[-24:],
        "contract_status": {
            "status": cf.get("contract", {}).get("STATUS", ""),
            "delta": cf.get("contract", {}).get("DELTA", ""),
            "verdict": cf.get("contract", {}).get("VERDICT", ""),
            "blocker_id": cf.get("contract", {}).get("BLOCKER_ID", ""),
            "next": cf.get("contract", {}).get("NEXT", ""),
        },
    }

def classify_log_line(line: str) -> str:
    txt = (line or "").strip()
    u = txt.upper()
    if not txt:
        return "empty"
    if any(k in u for k in (
        "ASK QUESTIONS, EDIT FILES, OR RUN COMMANDS.",
        "BE SPECIFIC FOR THE BEST RESULTS.",
        "/HELP FOR MORE INFORMATION.",
        "INSTALLED VIA HOMEBREW. PLEASE UPDATE WITH",
        "USING: 1 QWEN.MD FILE",
    )):
        return "meta"
    if re.search(r"^\(ESC TO CANCEL", u):
        return "meta"
    if any(k in u for k in ("CODER-MODEL", "SANDBOX (", "NO SANDBOX")):
        return "meta"
    if re.search(r"[\u2800-\u28ff]", txt):
        return "meta"
    if re.search(r"\brc=(1|2|124|13|22|43)\b", txt):
        return "error"
    if any(k in u for k in ("[ERROR]", "ERROR:", "TRACEBACK", "EXCEPTION", "MODULE NOT FOUND", "UNEXPECTED EOF", "SYNTAX ERROR")):
        return "error"
    if any(k in u for k in ("[BLOCKED]", "VERDICT: BLOCKED", "STATUS: BLOCKED")):
        return "error"
    if "BLOCKER_ID:" in u:
        m_blocker = re.search(r"BLOCKER_ID:\s*([A-Z0-9_\-?]+)", u)
        blocker = (m_blocker.group(1) if m_blocker else "").strip()
        if blocker and blocker not in {"NONE", "NO_BLOCKER", "?"}:
            return "error"
    if any(k in u for k in ("[BACKOFF]", "RATE_LIMIT", "[SKIP]", "GO_WITH_CAUTION", "WARN", "WARNING")):
        return "warn"
    if "[ACTION]" in u:
        return "action"
    if "[CONTRACT]" in u:
        return "contract"
    if any(k in u for k in ("VERDICT: PASS", "VERDICT: GO", "STATUS: COMPLETE", "STATUS: OK", "TEST_RESULT=PASS")):
        return "ok"
    if any(k in u for k in ("[START]", "[END]", "[TICK]", "[MODEL]", "[CONFIG]", "[MODEL_EFFECTIVE]", "PRIMARY_PROMPT_BEGIN", "PRIMARY_PROMPT_END", "FINAL_OUTPUT")):
        return "meta"
    return "normal"

def _extract_ts(line: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line or "")
    return m.group(1) if m else ""


def _extract_ts_epoch(line: str) -> float | None:
    txt = (line or "").strip()
    if not txt:
        return None
    # 2026-03-03T23:40:09Z
    m_z = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z", txt)
    if m_z:
        try:
            return datetime.strptime(m_z.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            pass
    # 2026-03-03T19:06:04-0500
    m_off = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})", txt)
    if m_off:
        try:
            return datetime.strptime(m_off.group(1), "%Y-%m-%dT%H:%M:%S%z").timestamp()
        except Exception:
            pass
    # 2026-03-03T19:02:37 (naive, assume local tz)
    m_local = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", txt)
    if m_local:
        try:
            dt = datetime.strptime(m_local.group(1), "%Y-%m-%dT%H:%M:%S")
            local_tz = datetime.now().astimezone().tzinfo
            if local_tz is None:
                local_tz = timezone.utc
            return dt.replace(tzinfo=local_tz).timestamp()
        except Exception:
            return None
    return None


def _is_recent_line(line: str, recent_minutes: int, now_epoch: float | None = None) -> bool:
    if recent_minutes <= 0:
        return True
    epoch = _extract_ts_epoch(line)
    if epoch is None:
        return True
    if now_epoch is None:
        now_epoch = time.time()
    return (now_epoch - epoch) <= (recent_minutes * 60)

def resolve_role_log_path(role: str, kind: str) -> Path | None:
    role = (role or "").strip()
    kind = (kind or "").strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9_]+", role):
        return None
    if kind == "tick":
        return ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log"
    if kind == "cron":
        return ROOT / f"logs-codex-runs/fc-ticks/{role}.cron.log"
    if kind == "runner":
        return ROOT / f"logs-codex-runs/role-runner/{role}.live.log"
    if kind == "events":
        return ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    if kind == "contract":
        return STATE / f"{role}.last_contract"
    return None

def rate_limits():
    out=[]
    for b in ["codex","qwen"]:
        f=STATE/f"{b}.rate_limit_gate_cache"
        if not f.exists(): continue
        try:
            until=int(f.read_text().strip().split("|")[0]); rem=int(until-time.time())
            if rem>0: out.append({"model":b,"remaining_s":rem})
            else: f.unlink()
        except: pass
    return out

def kpi_last():
    path = orchestrator_file("kpi-history.jsonl")
    if not path.exists(): return {}
    for l in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            d=json.loads(l)
            if d.get("workboard") or d.get("done_total"): return d
        except: pass
    return {}

def is_rate_limit_marker(verdict: str, status: str, delta: str, blocker: str) -> bool:
    b = (blocker or "").upper()
    s = (status or "").upper()
    d = (delta or "").upper()
    return b.startswith("AGENT_RATE_LIMIT_") or s in ("RATE_LIMIT_SKIP", "RATE_LIMIT_BACKOFF") or d == "RATE_LIMIT_BACKOFF"

@app.get("/api/status")
def status():
    now=datetime.now(timezone.utc); m=now.minute
    latest_snapshot = monitor_latest_snapshot()
    latest_roles_raw = latest_snapshot.get("roles", {})
    latest_roles = latest_roles_raw if isinstance(latest_roles_raw, dict) else {}
    # Canonical UI scope: only currently active topology roles.
    # Do not auto-reintroduce legacy roles from monitoring snapshots.
    roles = active_roles()
    pq=jload(orchestrator_file("priority-queue.json"))
    qi=pq.get("items",[])
    wb=jload(orchestrator_file("parallel-workstreams.json"))
    tasks=wb.get("tasks",[])
    derived_batches = _derive_batches_from_workboard(tasks)
    # Canonical source: priority-queue.json -> items[].
    # Keep derived fallback only when queue is empty/unavailable.
    queue_items = qi if isinstance(qi, list) else []
    if not queue_items and derived_batches:
        queue_items = [{"id": b.get("id"), "state": b.get("state")} for b in derived_batches]
    qa=[i for i in queue_items if i.get("state") not in ("CLOSED","DONE","PASS")]
    bs=defaultdict(int)
    for t in tasks: bs[t.get("state","?")] += 1
    done=bs["DONE"]+bs["CLOSED"]+bs["PASS"]
    ready_t=[{"id":t["id"],"role":canonical_role(t.get("assignee") or t.get("role","?")),"title":t.get("title","")[:60]} for t in tasks if t.get("state")=="READY"]
    ip_t=[{"id":t["id"],"role":canonical_role(t.get("assignee") or t.get("role","?")),"title":t.get("title","")[:60]} for t in tasks if t.get("state")=="IN_PROGRESS"]
    queue_state_counts = _state_counts(queue_items, key="state")
    workboard_state_counts = _state_counts(tasks, key="state")
    mismatches = _queue_workboard_mismatches(queue_items, tasks)
    hs = latest_snapshot.get("health_snapshot", {}) if isinstance(latest_snapshot, dict) else {}
    hs_queue = hs.get("queue", {}) if isinstance(hs, dict) else {}
    hs_workboard = hs.get("workboard", {}) if isinstance(hs, dict) else {}

    queue_total = len(queue_items)
    queue_closed = len(queue_items) - len(qa)
    if queue_total == 0 and isinstance(hs_queue, dict) and hs_queue:
        queue_total = int(hs_queue.get("total") or 0)
        queue_closed = int(hs_queue.get("closed") or 0)

    queue_active_rows = [{"id": i["id"], "state": str(i.get("state", "")).upper()} for i in qa]
    queue_display_rows = _merge_queue_display_rows(queue_items, derived_batches)
    queue_display_total = len(queue_display_rows)
    queue_display_closed = sum(
        1 for b in queue_display_rows
        if str(b.get("state", "")).upper() in {"CLOSED", "DONE", "PASS"}
    )

    workboard_total = len(tasks)
    workboard_done = done
    workboard_ready = len(ready_t)
    workboard_in_progress = len(ip_t)
    if workboard_total == 0 and isinstance(hs_workboard, dict) and hs_workboard:
        workboard_total = int(hs_workboard.get("total") or 0)
        workboard_done = int(hs_workboard.get("done") or 0)
        workboard_ready = int(hs_workboard.get("ready") or 0)
        workboard_in_progress = int(hs_workboard.get("in_progress") or 0)

    agents={}
    for role in roles:
        c=contract(role)
        snap = latest_roles.get(role, {}) if isinstance(latest_roles, dict) else {}
        if not isinstance(snap, dict):
            snap = {}
        mins=DEFAULT_SCHEDULE_MAP.get(role, [])
        nm = None
        wait = -1
        if mins:
            nm=next((x for x in sorted(mins) if x>m),sorted(mins)[0])
            wait=(nm-m) if nm>m else (60-m+nm)
        age=tick_age(role)
        verdict = c.get("VERDICT") or snap.get("verdict") or "?"
        status_value = c.get("STATUS") or snap.get("status") or "?"
        delta_value = c.get("DELTA") or snap.get("delta") or "?"
        blocker_value = c.get("BLOCKER_ID") or snap.get("blocker_id") or "NONE"
        if is_rate_limit_marker(verdict, status_value, delta_value, blocker_value):
            if (verdict or "").upper() == "BLOCKED":
                verdict = "WAIT"
            if (status_value or "").upper() == "BLOCKED":
                status_value = "RATE_LIMIT_SKIP"
            if (blocker_value or "").upper().startswith("AGENT_RATE_LIMIT_"):
                blocker_value = "NONE"
        agents[role]={"verdict":verdict,"status":status_value,"delta":delta_value,
                      "blocker":blocker_value,"next":c.get("NEXT") or snap.get("next", ""),
                      "schedule":(f":{','.join(str(x) for x in mins)}" if mins else "manual"),
                      "tick_age_min":age,"next_tick_min":wait,
                      "next_tick_at":(f":{nm:02d}" if nm is not None else "--")}
    kpi={}
    try:
        kd=kpi_last(); v=kd.get("velocity",{}); wb2=kd.get("workboard",{})
        lv = latest_snapshot.get("velocity", {}) if isinstance(latest_snapshot, dict) else {}
        if not isinstance(lv, dict):
            lv = {}
        kpi={"done_total":wb2.get("done") or kd.get("done_total") or hs_workboard.get("done"),
             "done_24h":v.get("done_24h") or kd.get("done_24h") or lv.get("done_24h"),
             "done_7d":v.get("done_7d") or lv.get("done_7d"),
             "proofs":v.get("proofs") or lv.get("proofs"),
             "ts":(kd.get("ts_utc","") or latest_snapshot.get("updated_at",""))[:16]}
    except: pass
    rl=rate_limits()
    hard_blocked = any(
        (a.get("blocker", "NONE") not in ("NONE", ""))
        and not is_rate_limit_marker(a.get("verdict", ""), a.get("status", ""), a.get("delta", ""), a.get("blocker", ""))
        for a in agents.values()
    )
    rate_limited_agents = any(
        is_rate_limit_marker(a.get("verdict", ""), a.get("status", ""), a.get("delta", ""), a.get("blocker", ""))
        for a in agents.values()
    )
    health = "DEGRADED" if hard_blocked else ("STALE" if (rl or rate_limited_agents) else "OK")
    queue_path = orchestrator_file("priority-queue.json")
    workboard_path = orchestrator_file("parallel-workstreams.json")
    latest_runtime_ts = _latest_mtime([
        queue_path,
        workboard_path,
        *[ROOT / f"logs-codex-runs/fc-ticks/{role}.tick.log" for role in roles],
    ])
    freshness_s = int(max(0, time.time() - latest_runtime_ts)) if latest_runtime_ts > 0 else -1
    freshness_state = "fresh" if 0 <= freshness_s <= 240 else ("warm" if 0 <= freshness_s <= 900 else "stale")
    if health == "DEGRADED":
        summary = latest_snapshot.get("summary", {}) if isinstance(latest_snapshot, dict) else {}
        blocker_roles = summary.get("blocker_roles", []) if isinstance(summary, dict) else []
        blocker_roles = blocker_roles if isinstance(blocker_roles, list) else []
        if not hard_blocked and not blocker_roles:
            health = "OK"

    return {"ts_utc":now.isoformat(),"health":health,
            "instance":INSTANCE_ID,
            "root":str(ROOT),
            "state_dir":str(STATE),
            "roles":list(roles),
            "queue":{"total":queue_total,"closed":queue_closed,"active":queue_active_rows,
                     "display_total":queue_display_total,
                     "display_closed":queue_display_closed,
                     "display_batches":queue_display_rows,
                     "state_counts":queue_state_counts,
                     "mismatch_count":len(mismatches),
                     "mismatches":mismatches[:8]},
            "workboard":{"total":workboard_total,"done":workboard_done,"ready":workboard_ready,"in_progress":workboard_in_progress,
                         "ready_tasks":ready_t,"in_progress_tasks":ip_t,
                         "state_counts":workboard_state_counts},
            "agents":agents,"rate_limits":rl,"kpi":kpi,
            "runtime_freshness":{"seconds":freshness_s,"state":freshness_state},
            "sources":{
                "queue":str(queue_path),
                "workboard":str(workboard_path),
                "kpi":str(orchestrator_file("kpi-history.jsonl")),
            }}

@app.get("/api/ticks/{role}")
def ticks(role:str, n:int=25):
    roles = active_roles()
    if role=="all":
        return {r: tick_hist(r, n) for r in roles}
    return {"role":role,"ticks":tick_hist(role,n)}

@app.get("/api/contract/{role}")
def get_contract(role:str):
    raw=contract_raw(role)
    if not raw: return JSONResponse({"error":"not found"},status_code=404)
    return JSONResponse({"role":role,"contract":raw},media_type="application/json")

@app.get("/api/logs/{role}")
def logs(role:str, n:int=80):
    log=ROOT/f"logs-codex-runs/role-runner/{role}.live.log"
    if not log.exists(): return JSONResponse({"error":"not found"},status_code=404)
    return {"role":role,"lines":log.read_text(encoding="utf-8",errors="ignore").splitlines()[-n:]}

@app.get("/api/logs/{role}/events")
def log_events(role:str, n:int=120):
    log = ROOT / f"logs-codex-runs/role-runner/{role}.events.log"
    if not log.exists():
        return JSONResponse({"error":"not found"}, status_code=404)
    return {"role": role, "lines": _tail_lines(log, n)}

@app.get("/api/planner/timeline")
def planner_timeline(n:int=150):
    timeline = orchestrator_file("planner-timeline.log")
    if not timeline.exists():
        return JSONResponse({"error":"not found"}, status_code=404)
    return {"role":"planner", "lines": _tail_lines(timeline, n)}

@app.get("/api/planner/log-bundle")
def planner_log_bundle(n:int=120):
    timeline = orchestrator_file("planner-timeline.log")
    audit = orchestrator_file("planner-audit-events.jsonl")
    guardian_events = orchestrator_file("planner-guardian-events.jsonl")
    guardian_latest = orchestrator_file("planner-guardian-latest.json")
    runner_events = ROOT / "logs-codex-runs/role-runner/planner.events.log"

    latest = {}
    if guardian_latest.exists():
        try:
            loaded = json.loads(guardian_latest.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(loaded, dict):
                latest = loaded
        except Exception:
            latest = {}

    return {
        "role": "planner",
        "guardian_latest": latest,
        "guardian_events": _tail_jsonl(guardian_events, n),
        "audit_events": _tail_jsonl(audit, n),
        "timeline": _tail_lines(timeline, n),
        "runner_events": _tail_lines(runner_events, n),
        "paths": {
            "timeline": str(timeline),
            "audit_events": str(audit),
            "guardian_events": str(guardian_events),
            "guardian_latest": str(guardian_latest),
            "runner_events": str(runner_events),
        },
    }

@app.get("/api/execution/{role}")
def execution(role: str, tick_n: int = 35, runner_n: int = 55):
    roles = active_roles()
    if role == "all":
        return {r: latest_execution(r, tick_n=tick_n, runner_n=runner_n) for r in roles}
    if role not in roles:
        return JSONResponse({"error": "invalid role"}, status_code=400)
    return latest_execution(role, tick_n=tick_n, runner_n=runner_n)

@app.get("/api/execution-insights/{role}")
def execution_insights(role: str):
    roles = active_roles()
    if role == "all":
        return {r: execution_insight(r) for r in roles}
    if role not in roles:
        return JSONResponse({"error": "invalid role"}, status_code=400)
    return execution_insight(role)

@app.get("/api/agent-insights")
def agent_insights():
    roles = active_roles()
    agents: dict[str, dict] = {}
    for role in roles:
        parsed = parse_contract_fields(role)
        ex = latest_execution(role, tick_n=80, runner_n=120)
        tick_tail = ex.get("tick_tail", []) or []
        runner_tail = ex.get("runner_tail", []) or []
        last_action = ""
        last_contract = ""
        for ln in reversed(tick_tail):
            if not last_action and "[ACTION]" in ln:
                last_action = ln
            if not last_contract and "[CONTRACT]" in ln:
                last_contract = ln
            if last_action and last_contract:
                break
        # Interesting execution if a concrete change is claimed/completed/handoff
        # and quality is not weak.
        t = parsed.get("task_update", "unknown")
        interesting = t in {"claim", "complete", "handoff"} and parsed.get("quality") in {"STRONG", "MEDIUM"}
        agents[role] = {
            **parsed,
            "last_execution": {
                "last_ts": ex.get("last_ts", ""),
                "last_rc": ex.get("last_rc"),
                "last_agent": ex.get("last_agent", ""),
                "last_start": ex.get("last_start", ""),
                "last_end": ex.get("last_end", ""),
            },
            "last_action_line": last_action,
            "last_contract_line": last_contract,
            "runner_tail": runner_tail[-24:],
            "tick_tail": tick_tail[-24:],
            "interesting_execution": interesting,
        }
    return {"roles": list(roles), "agents": agents}

@app.get("/api/log-catalog")
def log_catalog():
    roles = active_roles()
    data: dict[str, dict[str, dict]] = {}
    for role in roles:
        role_entry: dict[str, dict] = {}
        for kind in LOG_KIND_LABELS:
            p = resolve_role_log_path(role, kind)
            exists = bool(p and p.exists())
            size = 0
            if exists and p:
                try:
                    size = int(p.stat().st_size)
                except Exception:
                    size = 0
            role_entry[kind] = {
                "label": LOG_KIND_LABELS[kind],
                "path": str(p) if p else "",
                "exists": exists,
                "size_bytes": size,
            }
        data[role] = role_entry
    return {"roles": list(roles), "kinds": list(LOG_KIND_LABELS.keys()), "catalog": data}

@app.get("/api/log-view")
def log_view(role: str = "planner", kind: str = "tick", n: int = 180):
    roles = active_roles()
    role = (role or "").strip()
    kind = (kind or "").strip().lower()
    if role not in roles:
        return JSONResponse({"error": "invalid role"}, status_code=400)
    if kind not in LOG_KIND_LABELS:
        return JSONResponse({"error": "invalid kind"}, status_code=400)
    p = resolve_role_log_path(role, kind)
    if p is None:
        return JSONResponse({"error": "invalid target"}, status_code=400)
    n = max(20, min(int(n), 600))
    lines = _tail_lines(p, n)
    entries = []
    counts = {"error": 0, "warn": 0, "action": 0, "contract": 0, "ok": 0, "meta": 0, "normal": 0}
    for ln in lines:
        sev = classify_log_line(ln)
        if sev not in counts:
            counts[sev] = 0
        counts[sev] += 1
        entries.append({"ts": _extract_ts(ln), "severity": sev, "line": ln})
    return {
        "role": role,
        "kind": kind,
        "label": LOG_KIND_LABELS[kind],
        "path": str(p),
        "exists": p.exists(),
        "lines": lines,
        "entries": entries,
        "severity_counts": counts,
    }

@app.get("/api/error-feed")
def error_feed(n: int = 120, recent_minutes: int = ERROR_FEED_RECENT_MINUTES):
    max_lines = max(40, min(int(n), 400))
    recent_minutes = max(0, min(int(recent_minutes), 24 * 60))
    rows: list[dict] = []
    dropped_stale = 0
    now_epoch = time.time()
    for role in active_roles():
        for kind in ("tick", "cron", "runner", "events", "contract"):
            p = resolve_role_log_path(role, kind)
            if p is None or not p.exists():
                continue
            for ln in _tail_lines(p, max_lines):
                sev = classify_log_line(ln)
                if sev not in {"error", "warn"}:
                    continue
                if not _is_recent_line(ln, recent_minutes, now_epoch):
                    dropped_stale += 1
                    continue
                rows.append({
                    "ts": _extract_ts(ln),
                    "role": role,
                    "kind": kind,
                    "severity": sev,
                    "line": ln,
                })
    # ISO timestamps are lexicographically sortable.
    rows.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return {
        "count": len(rows),
        "items": rows[:max_lines],
        "recent_minutes": recent_minutes,
        "dropped_stale": dropped_stale,
    }

@app.get("/api/runtime-diagnostics")
def runtime_diagnostics():
    logs_root = ROOT / "logs-codex-runs"
    role_recovery_lines = _tail_lines(logs_root / "role-recovery.log", 5000)
    health_lines = _tail_lines(logs_root / "health-snapshot.log", 320)
    resume_lines = _tail_lines(logs_root / "vm-resume.log", 1200)
    admin_event_lines = _tail_lines(logs_root / "role-runner" / "admin.events.log", 700)

    perm_re = re.compile(r"(cannot create directory|operation not permitted|permission denied)", re.I)
    ts_re = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})")
    recent_perm_hits: list[str] = []
    historical_perm_hits: list[str] = []
    last_ts_epoch: float | None = None
    now_epoch = time.time()
    recent_window_seconds = RUNTIME_DIAG_RECENT_MINUTES * 60
    for ln in role_recovery_lines:
        m_ts = ts_re.match((ln or "").strip())
        if m_ts:
            try:
                last_ts_epoch = datetime.strptime(m_ts.group(1), "%Y-%m-%dT%H:%M:%S%z").timestamp()
            except Exception:
                last_ts_epoch = None
        if not perm_re.search(ln):
            continue
        if last_ts_epoch is not None and (now_epoch - last_ts_epoch) <= recent_window_seconds:
            recent_perm_hits.append(ln)
        else:
            historical_perm_hits.append(ln)

    blocked_re = re.compile(r"blocked=\[(.*?)\]")
    last_health = health_lines[-1] if health_lines else ""
    last_blocked_roles: list[str] = []
    m_blocked = blocked_re.search(last_health)
    if m_blocked:
        payload = m_blocked.group(1)
        last_blocked_roles = re.findall(r"'([^']+)'", payload)

    degraded_recent = sum(1 for ln in health_lines[-80:] if "health=DEGRADED" in ln)
    stale_recent = sum(1 for ln in health_lines[-80:] if "health=STALE" in ln)

    resume_events = []
    for ln in resume_lines:
        m = re.search(r"status=RESUME_DETECTED.*?gap_s=(\d+)", ln)
        if not m:
            continue
        gap_s = int(m.group(1))
        ts_match = re.search(r'ts="([^"]+)"', ln)
        resume_events.append({
            "ts": ts_match.group(1) if ts_match else "",
            "gap_s": gap_s,
            "line": ln,
        })
    max_gap_s = max((e["gap_s"] for e in resume_events), default=0)

    timeout_re = re.compile(r"event=(primary_prompt_end|retry_prompt_end).*rc=124", re.I)
    admin_timeout_events = [ln for ln in admin_event_lines if timeout_re.search(ln)]
    admin_timeout_recent_lines = [
        ln for ln in admin_timeout_events if _is_recent_line(ln, RUNTIME_DIAG_RECENT_MINUTES, now_epoch)
    ]
    admin_timeout_recent = len(admin_timeout_recent_lines)

    planner_c = contract("planner")
    planner_blocker = (planner_c.get("BLOCKER_ID", "") or "").strip()
    planner_guard_block = planner_blocker == "PLANNER_BATCH_ID_INVALID"

    findings: list[dict] = []
    if recent_perm_hits:
        findings.append({
            "severity": "critical",
            "title": "Permission denied in role-recovery",
            "detail": f"{len(recent_perm_hits)} recent hit(s) in role-recovery.log",
            "sample": recent_perm_hits[-1],
        })
    elif historical_perm_hits:
        findings.append({
            "severity": "high",
            "title": "Permission denied (historical) in role-recovery",
            "detail": f"{len(historical_perm_hits)} old hit(s), not recent",
            "sample": historical_perm_hits[-1],
        })
    if planner_guard_block:
        findings.append({
            "severity": "critical",
            "title": "Planner contract guard blocked",
            "detail": "BLOCKER_ID=PLANNER_BATCH_ID_INVALID",
            "sample": planner_c.get("NEXT", ""),
        })
    if admin_timeout_recent > 0:
        findings.append({
            "severity": "high",
            "title": "Admin prompt timeout bursts",
            "detail": f"{admin_timeout_recent} timeout event(s) rc=124 (recent window)",
            "sample": admin_timeout_recent_lines[-1] if admin_timeout_recent_lines else "",
        })
    if max_gap_s >= 1800:
        findings.append({
            "severity": "high",
            "title": "VM resume long gap detected",
            "detail": f"max gap_s={max_gap_s}",
            "sample": resume_events[-1]["line"] if resume_events else "",
        })
    if last_blocked_roles:
        findings.append({
            "severity": "high",
            "title": "Blocked roles seen in health snapshot",
            "detail": ",".join(last_blocked_roles),
            "sample": last_health,
        })

    if not findings:
        findings.append({
            "severity": "ok",
            "title": "No critical runtime anomaly in scanned window",
            "detail": "logs look stable in recent tails",
            "sample": "",
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {
            "role_recovery_lines": len(role_recovery_lines),
            "health_snapshot_lines": len(health_lines),
            "vm_resume_lines": len(resume_lines),
            "admin_events_lines": len(admin_event_lines),
        },
        "signals": {
            "recent_window_minutes": RUNTIME_DIAG_RECENT_MINUTES,
            "permission_errors_recent": len(recent_perm_hits),
            "permission_errors_historical": len(historical_perm_hits),
            "health_degraded_recent": degraded_recent,
            "health_stale_recent": stale_recent,
            "health_last_blocked_roles": last_blocked_roles,
            "resume_detected_count": len(resume_events),
            "resume_max_gap_s": max_gap_s,
            "admin_timeout_events_recent": admin_timeout_recent,
            "admin_timeout_events_historical": max(0, len(admin_timeout_events) - admin_timeout_recent),
            "planner_guard_blocked": planner_guard_block,
            "planner_blocker_id": planner_blocker or "NONE",
        },
        "top_findings": findings[:6],
    }

@app.get("/api/workboard")
def workboard():
    wb=jload(orchestrator_file("parallel-workstreams.json"))
    return {"tasks":[{"id":t["id"],"state":t.get("state"),"role":canonical_role(t.get("assignee") or t.get("role")),
                      "title":t.get("title","")[:60],"updated_at":t.get("updated_at","")} for t in wb.get("tasks",[])]}



HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FC Monitor</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root {
  --ink:#05080d;--surface:#090e15;--panel:#0d1520;--lift:#111d2b;--raised:#162030;
  --edge:rgba(255,255,255,.055);--edge2:rgba(255,255,255,.10);
  --ink-text:#b8cfe0;--ghost:#4a6882;--dim:#243344;
  --aqua:#00d4ff;--emerald:#00e87a;--amber:#ffb340;--coral:#ff4d6a;--lavender:#9b7fff;--sky:#40a9ff;
  --gaq:rgba(0,212,255,.12);--gem:rgba(0,232,122,.10);--cor:rgba(255,77,106,.12);
  --mono:'IBM Plex Mono',monospace;--sans:'DM Sans',sans-serif;--r:8px;--r2:12px;
}
html{background:var(--ink)}
body{font-family:var(--mono);font-size:12px;line-height:1.5;color:var(--ink-text);background:var(--ink);min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;z-index:0;background-image:radial-gradient(circle,rgba(0,212,255,.04) 1px,transparent 1px);background-size:32px 32px;pointer-events:none}
body::after{content:'';position:fixed;top:0;left:0;right:0;height:200px;z-index:0;background:radial-gradient(ellipse 80% 100% at 50% 0%,rgba(0,212,255,.06) 0%,transparent 100%);pointer-events:none}
header{position:sticky;top:0;z-index:100;height:52px;background:rgba(5,8,13,.92);backdrop-filter:blur(20px) saturate(180%);border-bottom:1px solid var(--edge);display:flex;align-items:center;padding:0 20px;gap:20px}
.hd-brand{display:flex;align-items:center;gap:10px;flex-shrink:0}
.hd-orb{width:28px;height:28px;border-radius:50%;background:conic-gradient(from 0deg,var(--aqua),var(--emerald),var(--aqua));box-shadow:0 0 12px rgba(0,212,255,.4);animation:spin 8s linear infinite;flex-shrink:0}
@keyframes spin{to{transform:rotate(360deg)}}
.hd-title{font-family:var(--sans);font-weight:700;font-size:14px;color:#fff;letter-spacing:-.01em}
.hd-sub{font-family:var(--mono);font-size:10px;color:var(--ghost);letter-spacing:.08em;text-transform:uppercase}
.hd-sep{width:1px;height:24px;background:var(--edge);flex-shrink:0}
.status-capsule{display:flex;align-items:center;gap:8px;padding:5px 12px;border-radius:99px;border:1px solid;font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
.status-capsule.ok{color:var(--emerald);border-color:rgba(0,232,122,.3);background:rgba(0,232,122,.06)}
.status-capsule.err{color:var(--coral);border-color:rgba(255,77,106,.3);background:rgba(255,77,106,.06);animation:pulse-err 1.5s ease-in-out infinite}
.status-capsule.warn{color:var(--amber);border-color:rgba(255,179,64,.3);background:rgba(255,179,64,.06)}
@keyframes pulse-err{0%,100%{box-shadow:0 0 0 0 rgba(255,77,106,.3)}50%{box-shadow:0 0 0 4px rgba(255,77,106,0)}}
.status-dot{width:6px;height:6px;border-radius:50%;background:currentColor;flex-shrink:0}
.status-dot.live{animation:blink 1.2s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.hd-spacer{flex:1}
.hd-meta{display:flex;align-items:center;gap:16px;font-size:11px;color:var(--ghost)}
.hd-btn{background:var(--lift);border:1px solid var(--edge);color:var(--ink-text);padding:5px 14px;border-radius:var(--r);font-family:var(--mono);font-size:11px;cursor:pointer;transition:all .15s;display:flex;align-items:center;gap:6px}
.hd-btn:hover{border-color:var(--aqua);color:var(--aqua);background:rgba(0,212,255,.06)}
.page{position:relative;z-index:1;max-width:1480px;margin:0 auto;padding:16px 16px 48px;display:grid;grid-template-columns:280px 1fr;gap:10px}
@media(max-width:960px){.page{grid-template-columns:1fr}}
.col-left{grid-column:1;display:flex;flex-direction:column;gap:10px}
.col-right{grid-column:2;display:flex;flex-direction:column;gap:10px}
.span2{grid-column:1/-1}
.panel{background:var(--panel);border:1px solid var(--edge);border-radius:var(--r2);overflow:hidden}
.panel-head{padding:9px 14px;background:var(--lift);border-bottom:1px solid var(--edge);display:flex;align-items:center;justify-content:space-between;gap:8px}
.panel-label{font-family:var(--sans);font-size:10px;font-weight:600;letter-spacing:.10em;text-transform:uppercase;color:var(--ghost)}
.panel-body{padding:14px}
.health-hero{text-align:center;padding:20px 14px 16px}
.health-ring-wrap{position:relative;width:80px;height:80px;margin:0 auto 12px}
.health-ring{width:80px;height:80px;border-radius:50%;position:relative;display:flex;align-items:center;justify-content:center}
.health-ring.ok{background:conic-gradient(var(--emerald) 100%,var(--dim) 0);box-shadow:0 0 20px rgba(0,232,122,.25)}
.health-ring.err{background:conic-gradient(var(--coral) 100%,var(--dim) 0);box-shadow:0 0 20px rgba(255,77,106,.25)}
.health-ring.warn{background:conic-gradient(var(--amber) 100%,var(--dim) 0)}
.health-ring-inner{position:absolute;inset:6px;background:var(--panel);border-radius:50%;display:flex;align-items:center;justify-content:center;flex-direction:column}
.health-pct{font-family:var(--sans);font-weight:700;font-size:18px;line-height:1;color:#fff}
.health-pct-label{font-size:8px;color:var(--ghost);letter-spacing:.05em;margin-top:2px}
.health-status-word{font-family:var(--sans);font-weight:700;font-size:20px;letter-spacing:-.01em;margin-bottom:3px}
.health-status-word.ok{color:var(--emerald)}.health-status-word.err{color:var(--coral)}.health-status-word.warn{color:var(--amber)}
.health-ts{font-size:10px;color:var(--ghost)}
.stat4{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:0 14px 14px}
.stat-tile{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:10px 12px;position:relative;overflow:hidden}
.stat-tile::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:var(--r) var(--r) 0 0}
.stat-tile.g::before{background:var(--emerald)}.stat-tile.b::before{background:var(--aqua)}.stat-tile.y::before{background:var(--amber)}.stat-tile.v::before{background:var(--lavender)}
.stat-n{font-family:var(--sans);font-weight:700;font-size:24px;color:#fff;line-height:1;margin-bottom:3px}
.stat-n.g{color:var(--emerald)}.stat-n.b{color:var(--aqua)}.stat-n.y{color:var(--amber)}.stat-n.v{color:var(--lavender)}
.stat-lbl{font-size:10px;color:var(--ghost);text-transform:uppercase;letter-spacing:.07em}
.progress-track{height:4px;background:var(--dim);border-radius:2px;overflow:hidden;margin-bottom:10px}
.progress-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--emerald),var(--aqua));transition:width .8s cubic-bezier(.4,0,.2,1);box-shadow:0 0 8px rgba(0,212,255,.3)}
.queue-list{display:flex;flex-direction:column;gap:6px}
.queue-states{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.state-chip{font-size:10px;border:1px solid var(--edge);border-radius:999px;padding:2px 8px;background:var(--lift);color:var(--ghost)}
.state-chip.ready{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.state-chip.progress{color:var(--sky);border-color:rgba(64,169,255,.35);background:rgba(64,169,255,.08)}
.state-chip.wait{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.state-chip.done{color:#8a9bad}
.queue-sync{font-size:10px;border:1px solid var(--edge);border-radius:var(--r);padding:6px 8px;margin-top:8px;line-height:1.5}
.queue-sync.ok{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.queue-sync.warn{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.queue-sync.err{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.queue-row{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--lift);border:1px solid var(--edge);border-left:3px solid;border-radius:var(--r);transition:background .15s}
.queue-row:hover{background:var(--raised)}
.queue-row.READY{border-left-color:var(--emerald)}.queue-row.WAITING_DEP{border-left-color:var(--dim)}.queue-row.CLOSED{border-left-color:var(--dim);opacity:.45}
.queue-id{font-weight:700;font-size:12px;color:var(--ink-text)}
.queue-badge{font-size:10px;letter-spacing:.05em;text-transform:uppercase;padding:2px 7px;border-radius:3px}
.queue-badge.READY{color:var(--emerald);background:rgba(0,232,122,.1)}.queue-badge.WAITING_DEP{color:var(--ghost);background:rgba(255,255,255,.04)}.queue-badge.CLOSED{color:var(--dim);background:transparent}
.alert-banner{background:rgba(255,77,106,.07);border:1px solid rgba(255,77,106,.35);border-left:4px solid var(--coral);border-radius:var(--r);padding:10px 14px;display:flex;align-items:center;gap:10px;color:var(--coral);font-size:11px;animation:slideDown .2s ease}
@keyframes slideDown{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
.agents-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:800px){.agents-row{grid-template-columns:1fr}}
.agent-tile{background:var(--panel);border:1px solid var(--edge);border-radius:var(--r2);overflow:hidden;cursor:pointer;transition:transform .15s,box-shadow .15s,border-color .2s}
.agent-tile:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.4);border-color:var(--edge2)}
.agent-stripe{height:3px;width:100%}
.agent-stripe.GO,.agent-stripe.PASS{background:linear-gradient(90deg,var(--emerald),var(--aqua));box-shadow:0 2px 8px rgba(0,232,122,.4)}
.agent-stripe.WAIT,.agent-stripe.READY{background:linear-gradient(90deg,var(--sky),var(--aqua));box-shadow:0 2px 8px rgba(64,169,255,.3)}
.agent-stripe.BLOCKED{background:linear-gradient(90deg,var(--coral),#ff8c40);box-shadow:0 2px 8px rgba(255,77,106,.4);animation:stripe-err .8s ease-in-out infinite alternate}
@keyframes stripe-err{from{opacity:.7}to{opacity:1}}
.agent-stripe.MUTED{background:var(--dim)}
.agent-inner{padding:14px}
.agent-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.agent-name-wrap{display:flex;align-items:center;gap:8px}
.agent-name{font-family:var(--sans);font-weight:700;font-size:15px;color:#fff}
.agent-sched{font-size:10px;color:var(--ghost)}
.vc{padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;border:1px solid}
.vc.GO,.vc.PASS{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.vc.WAIT,.vc.READY{color:var(--sky);border-color:rgba(64,169,255,.35);background:rgba(64,169,255,.08)}
.vc.BLOCKED{color:var(--coral);border-color:rgba(255,77,106,.4);background:rgba(255,77,106,.10)}
.vc.MUTED{color:var(--ghost);border-color:var(--edge);background:transparent}
.agent-delta{font-size:11px;color:var(--ghost);background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:7px 10px;margin-bottom:8px;line-height:1.5;min-height:34px;word-break:break-word}
.agent-blocker{background:rgba(255,77,106,.07);border:1px solid rgba(255,77,106,.3);border-radius:var(--r);padding:5px 10px;color:var(--coral);font-size:10px;margin-bottom:8px;display:flex;align-items:center;gap:6px}
.agent-next{font-size:10px;color:var(--ink-text);opacity:.7;line-height:1.55;margin-bottom:10px;min-height:28px}
.spark{display:flex;align-items:flex-end;gap:2px;height:22px;margin-bottom:8px}
.spark-bar{flex:1;border-radius:2px 2px 0 0;transition:height .3s ease}
.spark-bar.ok{background:var(--emerald);opacity:.65}.spark-bar.err{background:var(--coral);opacity:.9}.spark-bar.skip{background:var(--amber);opacity:.75}.spark-bar.empty{background:var(--dim);opacity:.3;height:4px!important}
.agent-footer{display:flex;align-items:center;justify-content:space-between;padding-top:8px;border-top:1px solid var(--edge)}
.next-lbl{font-size:10px;color:var(--ghost)}.next-time{font-size:10px;font-weight:700;color:var(--aqua)}
.age-chip{font-size:9px;padding:2px 7px;border-radius:3px;background:var(--lift);border:1px solid var(--edge);color:var(--ghost)}
.task-grid{display:flex;flex-wrap:wrap;gap:6px}
.task-chip{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:var(--r);font-size:11px;border:1px solid;transition:all .14s}
.task-chip:hover{transform:translateY(-1px)}
.task-chip.READY{border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.07);color:var(--emerald)}
.task-chip.IN_PROGRESS{border-color:rgba(0,212,255,.4);background:rgba(0,212,255,.07);color:var(--aqua)}
.task-chip-role{opacity:.55;font-size:10px}
.tab-bar{display:flex;gap:5px;margin-bottom:10px}
.t-tab{padding:4px 13px;border-radius:var(--r);border:1px solid var(--edge);background:transparent;color:var(--ghost);font-family:var(--mono);font-size:11px;cursor:pointer;transition:all .12s}
.t-tab:hover{border-color:var(--edge2);color:var(--ink-text)}
.t-tab.on{background:var(--aqua);color:var(--ink);border-color:var(--aqua);font-weight:700}
.t-tab.on-v{background:var(--lavender);color:#fff;border-color:var(--lavender);font-weight:700}
.tick-scroll{max-height:240px;overflow-y:auto}
.tick-scroll::-webkit-scrollbar{width:3px}
.tick-scroll::-webkit-scrollbar-thumb{background:var(--dim);border-radius:2px}
.t-row{display:grid;grid-template-columns:140px 68px 60px 46px;gap:6px;align-items:center;padding:5px 8px;border-radius:4px;font-size:11px;border-bottom:1px solid rgba(255,255,255,.03);transition:background .1s}
.t-row:hover{background:var(--lift)}.t-row:last-child{border:none}
.t-ts{color:var(--ghost);font-size:10px}
.t-type{font-size:10px;letter-spacing:.05em}
.t-type.END{color:var(--ghost)}.t-type.SKIP{color:var(--amber)}.t-type.BACKOFF{color:var(--coral);font-weight:600}
.t-rc.ok{color:var(--emerald)}.t-rc.err{color:var(--coral)}.t-rc.skip{color:var(--amber)}
.contract-block{background:var(--ink);border:1px solid var(--edge);border-radius:var(--r);padding:14px;font-size:11px;line-height:1.9;max-height:220px;overflow-y:auto}
.contract-block::-webkit-scrollbar{width:3px}.contract-block::-webkit-scrollbar-thumb{background:var(--dim)}
.c-key{color:var(--aqua);font-weight:600}.c-ok{color:var(--emerald)}.c-err{color:var(--coral);font-weight:700}.c-muted{color:var(--ghost)}
.link-row{display:flex;gap:14px;padding-top:10px;flex-wrap:wrap}
.ext-link{font-size:10px;color:var(--ghost);text-decoration:none;display:flex;align-items:center;gap:4px;transition:color .12s}
.ext-link:hover{color:var(--aqua)}
.exec-meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:6px;margin-bottom:10px}
.exec-pill{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:7px 9px;min-height:42px}
.exec-pill-label{font-size:9px;color:var(--ghost);text-transform:uppercase;letter-spacing:.07em;margin-bottom:2px}
.exec-pill-value{font-size:10px;color:var(--ink-text);word-break:break-word}
.exec-pill-value.ok{color:var(--emerald)}.exec-pill-value.err{color:var(--coral)}.exec-pill-value.skip{color:var(--amber)}
.activity-chip{display:inline-flex;align-items:center;gap:6px;padding:2px 8px;border-radius:999px;border:1px solid;font-size:10px;font-weight:700;letter-spacing:.06em}
.activity-chip.PRODUCTIVE{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.activity-chip.IDLE{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.activity-chip.CHECK{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.exec-logs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.log-box{background:var(--ink);border:1px solid var(--edge);border-radius:var(--r);overflow:hidden}
.log-head{padding:7px 9px;background:var(--lift);border-bottom:1px solid var(--edge);font-size:10px;color:var(--ghost);text-transform:uppercase;letter-spacing:.07em}
.log-scroll{max-height:220px;overflow:auto;padding:9px}
.log-scroll::-webkit-scrollbar{width:3px}.log-scroll::-webkit-scrollbar-thumb{background:var(--dim)}
.log-line{font-size:10px;line-height:1.45;color:var(--ink-text);font-family:var(--mono);white-space:pre-wrap;word-break:break-word;border-bottom:1px solid rgba(255,255,255,.03);padding:2px 0}
.log-line.err{color:var(--coral);background:rgba(255,77,106,.08);border-left:2px solid rgba(255,77,106,.65);padding-left:6px}
.log-line.warn{color:var(--amber);background:rgba(255,179,64,.07);border-left:2px solid rgba(255,179,64,.55);padding-left:6px}
.log-line.ok{color:var(--emerald)}
.log-line.action{color:var(--aqua);background:rgba(0,212,255,.06);border-left:2px solid rgba(0,212,255,.5);padding-left:6px}
.log-line.contract{color:var(--lavender);background:rgba(155,127,255,.08);border-left:2px solid rgba(155,127,255,.55);padding-left:6px}
.log-line.meta{color:var(--ghost)}
.log-line:last-child{border-bottom:none}
.log-empty{font-size:10px;color:var(--ghost)}
.t-tab.on-g{background:var(--emerald);color:var(--ink);border-color:var(--emerald);font-weight:700}
.sev-row{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 10px}
.sev-chip{font-size:10px;border:1px solid var(--edge);border-radius:999px;padding:2px 8px;background:var(--lift);color:var(--ghost)}
.sev-chip.err{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.sev-chip.warn{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.sev-chip.action{color:var(--aqua);border-color:rgba(0,212,255,.35);background:rgba(0,212,255,.08)}
.sev-chip.contract{color:var(--lavender);border-color:rgba(155,127,255,.35);background:rgba(155,127,255,.08)}
.insight-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.insight-tile{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:10px}
.insight-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.insight-role{font-family:var(--sans);font-weight:700;color:#fff;font-size:13px}
.insight-score{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;border:1px solid}
.insight-score.STRONG{color:var(--emerald);border-color:rgba(0,232,122,.35);background:rgba(0,232,122,.08)}
.insight-score.MEDIUM{color:var(--amber);border-color:rgba(255,179,64,.35);background:rgba(255,179,64,.08)}
.insight-score.WEAK{color:var(--coral);border-color:rgba(255,77,106,.35);background:rgba(255,77,106,.08)}
.insight-meta{font-size:10px;color:var(--ghost);margin-bottom:6px}
.insight-line{font-size:10px;color:var(--ink-text);line-height:1.5;margin-bottom:4px}
.insight-issues{font-size:10px;color:var(--coral);line-height:1.45}
.insight-events{font-size:10px;color:var(--ghost);line-height:1.45;margin-top:6px;max-height:80px;overflow:auto}
.diag-list{display:flex;flex-direction:column;gap:7px}
.diag-item{background:var(--lift);border:1px solid var(--edge);border-radius:var(--r);padding:8px 10px}
.diag-item.critical{border-left:3px solid var(--coral);background:rgba(255,77,106,.08)}
.diag-item.high{border-left:3px solid var(--amber);background:rgba(255,179,64,.08)}
.diag-item.ok{border-left:3px solid var(--emerald);background:rgba(0,232,122,.08)}
.diag-title{font-family:var(--sans);font-size:12px;font-weight:700;color:#fff}
.diag-meta{font-size:10px;color:var(--ghost);margin-top:2px}
.diag-sample{font-size:10px;color:var(--ink-text);line-height:1.45;margin-top:4px;max-height:38px;overflow:auto}
@media(max-width:1000px){.insight-grid{grid-template-columns:1fr}}
@media(max-width:1280px){.exec-logs{grid-template-columns:1fr 1fr}}
@media(max-width:980px){.exec-logs{grid-template-columns:1fr}}
.spin-sm{display:inline-block;width:10px;height:10px;border:2px solid rgba(255,255,255,.1);border-top-color:var(--aqua);border-radius:50%;animation:sp .5s linear infinite;vertical-align:middle}
@keyframes sp{to{transform:rotate(360deg)}}
.fade{animation:fadeUp .25s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
</style>
</head>
<body>
<header>
  <div class="hd-brand">
    <div class="hd-orb"></div>
    <div><div class="hd-title">FC Ops Monitor</div><div class="hd-sub">Finance Copilot · Orchestration</div></div>
  </div>
  <div class="hd-sep"></div>
  <div class="status-capsule err" id="health-capsule">
    <span class="status-dot live"></span><span id="health-txt">—</span>
  </div>
  <div class="hd-spacer"></div>
  <div class="hd-meta">
    <span id="hd-ts">—</span>
    <button class="hd-btn" onclick="doRefresh()"><span id="ri">⟳</span> Refresh</button>
    <a class="hd-btn" href="/planner-debug" target="_blank">Planner Debug</a>
    <span id="cd" style="min-width:60px;text-align:right">auto 12s</span>
  </div>
</header>
<div class="page" id="page">
  <div class="span2" style="display:flex;align-items:center;justify-content:center;height:60vh;color:var(--ghost);flex-direction:column;gap:12px">
    <span class="spin-sm" style="width:20px;height:20px;border-width:3px"></span>
    <span style="font-family:DM Sans,sans-serif;font-size:13px">Chargement…</span>
  </div>
</div>
<script>
let D=null,T=null,E=null,L=null,LC=null,I=null,X=null,F=null,G=null,API_ERRORS=[],cdr=12,iv=null,tickRole='planner',contractRole='planner',execRole='planner',logRole='planner',logKind='runner';
async function fetchJson(url, fallback={}, timeoutMs=6000){
  const ctrl=new AbortController();
  const tid=setTimeout(()=>ctrl.abort(), timeoutMs);
  try{
    const r=await fetch(url,{cache:'no-store',signal:ctrl.signal});
    if(!r.ok)return {ok:false,data:fallback,error:`http_${r.status}`,url};
    return {ok:true,data:await r.json(),error:'',url};
  }catch(err){
    const kind=(err&&err.name==='AbortError')?'timeout':'network';
    return {ok:false,data:fallback,error:kind,url};
  }finally{
    clearTimeout(tid);
  }
}
async function load(){
  const[s,t,e,l,lc,i,x,f,g]=await Promise.all([
    fetchJson('/api/status',{}),
    fetchJson('/api/ticks/all?n=20',{}),
    fetchJson('/api/execution/all?tick_n=40&runner_n=90',{}),
    fetchJson(`/api/log-view?role=${encodeURIComponent(logRole)}&kind=${encodeURIComponent(logKind)}&n=220`,{}),
    fetchJson('/api/log-catalog',{}),
    fetchJson('/api/agent-insights',{}),
    fetchJson('/api/execution-insights/all',{}),
    fetchJson('/api/error-feed?n=140',{}),
    fetchJson('/api/runtime-diagnostics',{})
  ]);
  API_ERRORS=[s,t,e,l,lc,i,x,f,g].filter(r=>!r.ok).map(r=>`${r.url}:${r.error}`);

  const statusOk = !!(s.ok && s.data && s.data.queue && s.data.workboard && s.data.agents);
  if(statusOk){
    D=s.data;
    D.__status_unavailable=false;
  }else if(!D){
    D={health:'UNKNOWN',queue:null,workboard:null,agents:{},rate_limits:[],kpi:{},runtime_freshness:{seconds:-1,state:'stale'},sources:{},__status_unavailable:true};
  }else{
    D.__status_unavailable=true;
  }
  if(t.ok)T=t.data;
  if(e.ok)E=e.data;
  if(l.ok)L=l.data;
  if(lc.ok)LC=lc.data;
  if(i.ok)I=i.data;
  if(x.ok)X=x.data;
  if(f.ok)F=f.data;
  if(g.ok)G=g.data;
}
function esc(v){return String(v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
function shortPath(v, max=92){
  const s=String(v||'');
  if(!s)return'—';
  if(s.length<=max)return s;
  return `…${s.slice(-(max-1))}`;
}
function classifyLineClient(line){
  const t=String(line||'');
  const u=t.toUpperCase();
  if(/ASK QUESTIONS, EDIT FILES, OR RUN COMMANDS\.|BE SPECIFIC FOR THE BEST RESULTS\.|\/HELP FOR MORE INFORMATION\.|INSTALLED VIA HOMEBREW|USING:\s*1 QWEN\.MD FILE/.test(u))return'meta';
  if(/^\(ESC TO CANCEL/.test(u))return'meta';
  if(/CODER-MODEL|SANDBOX \(|NO SANDBOX/.test(u))return'meta';
  if(/[⠁-⣿]/.test(t))return'meta';
  if(/\brc=(1|2|124|13|22|43)\b/.test(t))return'err';
  if(/TRACEBACK|EXCEPTION|ERROR:|MODULE NOT FOUND|SYNTAX ERROR|UNEXPECTED EOF/.test(u))return'err';
  if(/\[BLOCKED\]|VERDICT:\s*BLOCKED|STATUS:\s*BLOCKED/.test(u))return'err';
  const blockerMatch=u.match(/BLOCKER_ID:\s*([A-Z0-9_\-?]+)/);
  if(blockerMatch&&blockerMatch[1]&&!['NONE','NO_BLOCKER','?'].includes(blockerMatch[1]))return'err';
  if(/\[BACKOFF\]|RATE_LIMIT|\[SKIP\]|GO_WITH_CAUTION|WARN|WARNING/.test(u))return'warn';
  if(/\[ACTION\]/.test(u))return'action';
  if(/\[CONTRACT\]/.test(u))return'contract';
  if(/VERDICT:\s*(PASS|GO)|STATUS:\s*(COMPLETE|OK)|TEST_RESULT=PASS/.test(u))return'ok';
  if(/\[(START|END|TICK|MODEL|CONFIG|MODEL_EFFECTIVE)\]|PRIMARY_PROMPT_(BEGIN|END)|FINAL_OUTPUT/.test(u))return'meta';
  return'normal';
}
function isRateLimited(v,s,b,d){
  const V=(v||'').toUpperCase(),S=(s||'').toUpperCase(),B=(b||'NONE').toUpperCase(),D=(d||'').toUpperCase();
  return B.startsWith('AGENT_RATE_LIMIT_')||S==='RATE_LIMIT_SKIP'||S==='RATE_LIMIT_BACKOFF'||D==='RATE_LIMIT_BACKOFF'||(V==='WAIT'&&S==='RATE_LIMIT_SKIP');
}
function monitorRoles(){
  const entries=Object.entries((D&&D.agents)||{}).filter(([r])=>!!r);
  const fromStatus=entries
    .filter(([,a])=>{
      const delta=String((a&&a.delta)||'').toUpperCase();
      const blocker=String((a&&a.blocker)||'').toUpperCase();
      const age=(a&&a.tick_age_min);
      const hasRecentTickAge = Number.isFinite(age) && age >= 0 && age <= 240;
      const hasDelta = delta && delta !== '?' && delta !== 'NO_DELTA';
      const hasBlocker = blocker && blocker !== 'NONE' && blocker !== '?';
      return hasRecentTickAge || hasDelta || hasBlocker;
    })
    .map(([r])=>r);
  if(fromStatus.length){
    const preferred=['planner','dev','admin'];
    const forceCore = preferred.filter(r=>entries.some(([name])=>name===r));
    const ordered=[
      ...forceCore.filter(r=>fromStatus.includes(r)),
      ...forceCore.filter(r=>!fromStatus.includes(r)),
      ...fromStatus.filter(r=>!preferred.includes(r)),
    ];
    return [...new Set(ordered)];
  }
  return ['planner','dev','admin'];
}
function ensureRole(selected, roles){
  if(roles.includes(selected))return selected;
  if(roles.includes('planner'))return 'planner';
  return roles[0]||'planner';
}
function vc(v,s,b,d){
  const V=(v||'').toUpperCase(),B=(b||'NONE').toUpperCase();
  if(isRateLimited(v,s,b,d))return'WAIT';
  if(B!=='NONE'&&B)return'BLOCKED';
  if(V==='GO'||V==='PASS')return V;
  if(V==='WAIT'||(s||'').toUpperCase()==='WAIT')return'WAIT';
  if(V==='BLOCKED')return'BLOCKED';
  if(V==='READY')return'READY';
  return'MUTED';
}
function vcIcon(v){return{GO:'✦',PASS:'✦',WAIT:'◎',READY:'◎',BLOCKED:'⚠',MUTED:'·'}[v]||'·'}
function sparkHtml(role){
  const list=(T&&T[role])||[];
  const items=[...list].reverse().slice(0,16);
  while(items.length<16)items.unshift(null);
  return items.map(t=>{
    if(!t)return'<div class="spark-bar empty"></div>';
    const cls=t.rc===0?'ok':(t.type!=='END'?'skip':'err');
    const h=t.rc===0?18:(t.type==='BACKOFF'?12:9);
    return`<div class="spark-bar ${cls}" style="height:${h}px"></div>`;
  }).join('');
}
function tickRowsHtml(role){
  const list=(T&&T[role])||[];
  if(!list.length)return'<div style="color:var(--ghost);padding:10px;font-size:11px">Aucun tick</div>';
  return list.map(t=>{
    const ok=t.rc===0,sk=t.type!=='END';
    const rcc=ok?'ok':sk?'skip':'err';
    const icon=ok?'✔':(t.type==='BACKOFF'?'↺':'✘');
    return`<div class="t-row"><span class="t-ts">${t.ts}</span><span class="t-type ${t.type}">${t.type}</span><span style="color:var(--ghost)">${t.agent}</span><span class="t-rc ${rcc}">${icon}</span></div>`;
  }).join('');
}
function contractBodyHtml(role){
  const a=(D&&D.agents&&D.agents[role])||{};
  const xi=(X&&X[role])||{};
  const cs=xi.contract_status||{};
  const verdict=a.verdict||cs.verdict||'MUTED';
  const statusVal=a.status||cs.status||'';
  const blocker=a.blocker||cs.blocker_id||'NONE';
  const delta=a.delta||cs.delta||'';
  const nextVal=a.next||cs.next||'';
  const rl=isRateLimited(verdict,statusVal,blocker,delta);
  const v=vc(verdict,statusVal,blocker,delta);
  return[
    ['VERDICT',verdict,v==='GO'||v==='PASS'?'c-ok':v==='BLOCKED'?'c-err':'c-muted'],
    ['STATUS',statusVal,v==='BLOCKED'?'c-err':'c-muted'],
    ['BLOCKER',rl?'NONE':blocker,(!rl&&blocker&&blocker!=='NONE')?'c-err':'c-muted'],
    ['DELTA',delta,'c-muted'],
    ['NEXT',(nextVal||'').slice(0,160),'c-muted'],
  ].map(([k,val,cls])=>`<div><span class="c-key">${k}:</span>&nbsp;<span class="${cls}">${val||'?'}</span></div>`).join('');
}
function latestExec(role){
  return (E&&E[role])||{tick_tail:[],runner_tail:[],events_tail:[],last_ts:'',last_rc:null,last_agent:'',last_start:'',last_end:''};
}
function isNoiseLine(line){
  const t=String(line||'').trim();
  if(!t)return true;
  const u=t.toUpperCase();
  if(/ASK QUESTIONS, EDIT FILES, OR RUN COMMANDS\.|BE SPECIFIC FOR THE BEST RESULTS\.|\/HELP FOR MORE INFORMATION\.|INSTALLED VIA HOMEBREW|USING:\s*1 QWEN\.MD FILE/.test(u))return true;
  if(/^\(ESC TO CANCEL/.test(u))return true;
  if(/CODER-MODEL|SANDBOX \(|NO SANDBOX/.test(u))return true;
  if(/[⠁-⣿]/.test(t))return true;
  if(t.startsWith('...~//analyse-financiere'))return true;
  return false;
}
function logLinesHtml(lines, entries=null){
  const rendered=[];
  if(entries && entries.length){
    const sevMap={error:'err',warn:'warn',action:'action',contract:'contract',ok:'ok',meta:'meta',normal:'normal'};
    for(const e of entries){
      const ln=String(e.line||'');
      const cls = sevMap[String(e.severity||'').toLowerCase()] || classifyLineClient(ln);
      if(isNoiseLine(ln) && !['err','warn','action','contract'].includes(cls))continue;
      rendered.push(`<div class="log-line ${cls}">${esc(ln)}</div>`);
    }
  }else{
    if(!lines||!lines.length)return '<div class="log-empty">Aucune ligne récente</div>';
    for(const l of lines){
      const cls=classifyLineClient(l);
      if(isNoiseLine(l) && !['err','warn','action','contract'].includes(cls))continue;
      rendered.push(`<div class="log-line ${cls}">${esc(l)}</div>`);
    }
  }
  if(!rendered.length)return '<div class="log-empty">Aucune ligne utile (bruit UI filtré)</div>';
  return rendered.join('');
}
function execMetaHtml(role){
  const x=latestExec(role);
  const xi=(X&&X[role])||{};
  const sev=xi.severity_counts||{};
  const ev=xi.event_counts||{};
  const activity=xi.activity||'CHECK';
  const quality=xi.quality||'WEAK';
  const taskUpdate=xi.task_update||'unknown';
  const rc=x.last_rc;
  const rcTxt=rc==null?'?':String(rc);
  const rcCls=rc==null?'':(rc===0?'ok':'err');
  return `
    <div class="exec-pill"><div class="exec-pill-label">Dernier timestamp</div><div class="exec-pill-value">${esc(x.last_ts||'—')}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Retour / agent</div><div class="exec-pill-value ${rcCls}">rc=${esc(rcTxt)} · ${esc(x.last_agent||'?')}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Dernier marqueur</div><div class="exec-pill-value">${esc(x.last_end||x.last_start||'—')}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Activité / qualité</div><div class="exec-pill-value"><span class="activity-chip ${esc(activity)}">${esc(activity)}</span> · ${esc(quality)} · ${esc(taskUpdate)}</div></div>
    <div class="exec-pill"><div class="exec-pill-label">Errors · Warn · Actions</div><div class="exec-pill-value">E:${sev.error||0} · W:${sev.warn||0} · A:${sev.action||0} · Events:${(ev.action||0)+(ev.warn||0)+(ev.error||0)}</div></div>
  `;
}
function logCatalogFor(role, kind){
  const c=LC&&LC.catalog&&LC.catalog[role]&&LC.catalog[role][kind];
  return c||null;
}
function logRoleTabsHtml(){
  const roles=monitorRoles();
  return roles.map(r=>`<button class="t-tab${r===logRole?' on':''}" onclick="setLogRole('${r}')">${r}</button>`).join('');
}
function logKindTabsHtml(){
  const kinds=['tick','cron','runner','events','contract'];
  return kinds.map(k=>{
    const c=logCatalogFor(logRole,k);
    const on=k===logKind?' on-g':'';
    const badge = c && c.exists ? '●' : '○';
    return `<button class="t-tab${on}" onclick="setLogKind('${k}')">${badge} ${k}</button>`;
  }).join('');
}
function logViewerHtml(){
  const lines=(L&&L.lines)||[];
  const entries=(L&&L.entries)||[];
  const counts=(L&&L.severity_counts)||{};
  const meta=logCatalogFor(logRole,logKind);
  const path = (L&&L.path) || (meta&&meta.path) || '—';
  const exists = (L&&typeof L.exists==='boolean') ? L.exists : !!(meta&&meta.exists);
  const sev = `
    <div class="sev-row">
      <span class="sev-chip err">error ${counts.error||0}</span>
      <span class="sev-chip warn">warn ${counts.warn||0}</span>
      <span class="sev-chip action">action ${counts.action||0}</span>
      <span class="sev-chip contract">contract ${counts.contract||0}</span>
      <span class="sev-chip">ok ${counts.ok||0}</span>
      <span class="sev-chip">meta ${counts.meta||0}</span>
    </div>`;
  return `
    <div class="tab-bar" id="log-role-tabs">${logRoleTabsHtml()}</div>
    <div class="tab-bar" id="log-kind-tabs">${logKindTabsHtml()}</div>
    ${sev}
    <div class="log-box">
      <div class="log-head">log-view · ${esc(logRole)} · ${esc(logKind)} · ${exists?'available':'missing'}</div>
      <div class="log-scroll">${logLinesHtml(lines,entries)}</div>
    </div>
    <div class="link-row">
      <a class="ext-link" href="/api/log-view?role=${encodeURIComponent(logRole)}&kind=${encodeURIComponent(logKind)}&n=220" target="_blank">⬡ Log JSON</a>
      <a class="ext-link" href="/api/log-catalog" target="_blank">⬡ Catalog</a>
      <span class="ext-link" style="pointer-events:none;opacity:.75">📄 ${esc(path)}</span>
    </div>
  `;
}
function insightsHtml(){
  const agents=(I&&I.agents)||{};
  const exi=(X||{});
  const roles=monitorRoles();
  return `<div class="insight-grid">${
    roles.map(r=>{
      const a=agents[r]||{};
      const x=exi[r]||{};
      const score=(x.quality_score==null?(a.quality_score==null?'?':a.quality_score):x.quality_score);
      const q=(x.quality||a.quality||'WEAK');
      const e=a.evidence||{};
      const issues=(x.issues&&x.issues.length?x.issues:(a.issues||[]));
      const interesting=(x.interesting_events||[]).slice(-3).map(ev=>`[${ev.ts||''}] ${ev.event||''} ${ev.detail||''}`).join('\n');
      const evc=x.event_counts||{};
      const svc=x.severity_counts||{};
      const activity=x.activity||'CHECK';
      const taskUpdate=x.task_update||a.task_update||'?';
      return `<div class="insight-tile">
        <div class="insight-head">
          <span class="insight-role">${r}</span>
          <span class="insight-score ${q}">${q} ${score}</span>
        </div>
        <div class="insight-meta">activity=${esc(activity)} · task_update=${esc(taskUpdate)} · run_note_words=${esc(x.run_note_words||a.run_note_words||0)}</div>
        <div class="insight-line"><strong>next:</strong> ${esc((x.contract_status&&x.contract_status.next)||(a.contract&&a.contract.NEXT)||'?').slice(0,140)}</div>
        <div class="insight-line"><strong>action:</strong> ${esc(a.last_action_line||'—').slice(0,170)}</div>
        <div class="insight-line"><strong>root_cause:</strong> ${esc(e.root_cause||'—').slice(0,120)}</div>
        <div class="insight-line"><strong>verify:</strong> ${esc(e.verify||'—').slice(0,120)}</div>
        <div class="insight-line"><strong>signals:</strong> E:${svc.error||0} W:${svc.warn||0} A:${svc.action||0} · events A:${evc.action||0} W:${evc.warn||0} E:${evc.error||0}</div>
        <div class="insight-issues">${issues.length?`issues: ${esc(issues.join(', '))}`:'issues: none'}</div>
        <div class="insight-events">${interesting?esc(interesting):'Aucun événement marquant récent'}</div>
      </div>`;
    }).join('')
  }</div>`;
}
function errorFeedHtml(){
  const items=(F&&F.items)||[];
  if(!items.length)return '<div class="log-empty">Aucune alerte récente.</div>';
  return items.slice(0,60).map(it=>{
    const cls=it.severity==='error'?'err':'warn';
    return `<div class="log-line ${cls}">[${esc(it.ts||'?')}] [${esc(it.role)}:${esc(it.kind)}] ${esc(it.line||'')}</div>`;
  }).join('');
}
function runtimeDiagnosticsHtml(){
  const Dg=G||{};
  const findings=(Dg.top_findings)||[];
  const s=(Dg.signals)||{};
  const permRecent=s.permission_errors_recent||0;
  const permHist=s.permission_errors_historical||0;
  const hdr=`perm_recent=${permRecent} · perm_hist=${permHist} · blocked=${(s.health_last_blocked_roles||[]).join(',')||'none'} · resume_max_gap=${s.resume_max_gap_s||0}s · admin_rc124=${s.admin_timeout_events_recent||0} · planner_guard=${s.planner_guard_blocked?'yes':'no'}`;
  const rows=findings.length?findings.map(f=>`
    <div class="diag-item ${esc(f.severity||'high')}">
      <div class="diag-title">${esc(f.title||'Finding')}</div>
      <div class="diag-meta">${esc(f.detail||'')}</div>
      <div class="diag-sample">${esc((f.sample||'').slice(0,220))}</div>
    </div>`).join(''):'<div class="diag-item ok"><div class="diag-title">No findings</div></div>';
  return `<div class="diag-meta" style="margin-bottom:8px">${esc(hdr)}</div><div class="diag-list">${rows}</div>`;
}
function render(){
  if(!D)return;
  const statusUnavailable = !!D.__status_unavailable || !D.queue || !D.workboard;
  const health=(statusUnavailable?'UNKNOWN':(D.health||'DEGRADED'));
  const queue=D.queue||{total:null,closed:null,active:[],state_counts:{},mismatch_count:0,mismatches:[]};
  const workboard=D.workboard||{total:null,done:null,ready:null,in_progress:null,ready_tasks:[],in_progress_tasks:[]};
  const agents=D.agents||{};
  const rl=D.rate_limits||[];
  const kpi=D.kpi||{};
  const src=D.sources||{};
  document.getElementById('hd-ts').textContent=new Date().toLocaleTimeString('fr-FR');
  const hc=document.getElementById('health-capsule');
  hc.className='status-capsule '+(statusUnavailable?'warn':(health==='OK'?'ok':health==='STALE'?'warn':'err'));
  document.getElementById('health-txt').textContent=health;
  const qDisplayTotal=(typeof queue.display_total==='number' && queue.display_total>0)?queue.display_total:queue.total;
  const qDisplayClosed=(typeof queue.display_closed==='number')?queue.display_closed:queue.closed;
  const pct=(typeof qDisplayTotal==='number' && qDisplayTotal>0 && typeof qDisplayClosed==='number')?Math.round(qDisplayClosed/qDisplayTotal*100):0;
  const hcls=statusUnavailable?'warn':(health==='OK'?'ok':health==='STALE'?'warn':'err');
  const alertsHtml=(rl||[]).map(r=>`<div class="alert-banner span2 fade"><span style="font-size:16px">⚠</span><div><strong>${r.model.toUpperCase()} RATE-LIMIT</strong> — ${r.remaining_s}s (~${Math.ceil(r.remaining_s/60)}min)</div></div>`).join('');
  const apiErrHtml = statusUnavailable
    ? `<div class="alert-banner span2 fade"><span style="font-size:16px">⚠</span><div><strong>Data source indisponible</strong> — affichage partiel (errors: ${esc((API_ERRORS||[]).slice(0,4).join(' | ')||'status fetch failed')})</div></div>`
    : '';
  const qsc=(queue.state_counts)||{};
  const queueStatesHtml = [
    `<span class="state-chip ready">READY ${qsc.READY||0}</span>`,
    `<span class="state-chip progress">IN_PROGRESS ${qsc.IN_PROGRESS||0}</span>`,
    `<span class="state-chip wait">WAITING_DEP ${qsc.WAITING_DEP||0}</span>`,
    `<span class="state-chip done">DONE/CLOSED ${qDisplayClosed ?? '—'}</span>`
  ].join('');
  const mismatchItems=(queue.mismatches||[]);
  const mismatchHtml = statusUnavailable
    ? `<div class="queue-sync warn"><strong>Queue/workboard indisponible</strong><br>Impossible de confirmer la cohérence temps réel.</div>`
    : mismatchItems.length
    ? `<div class="queue-sync err"><strong>Mismatch ${queue.mismatch_count||mismatchItems.length}</strong><br>${mismatchItems.map(m=>`${esc(m.batch)} · ${esc(m.issue)}`).join('<br>')}</div>`
    : `<div class="queue-sync ok">Queue/workboard sync OK</div>`;
  const batchRows=((queue.display_batches&&queue.display_batches.length)?queue.display_batches:(queue.active||[]));
  const qRows=batchRows.map(i=>`<div class="queue-row ${i.state}"><span class="queue-id">${i.id}</span><span class="queue-badge ${i.state}">${i.state==='READY'?'▶ READY':i.state==='IN_PROGRESS'?'⟳ IN PROG':i.state==='CLOSED'?'■ CLOSED':'◌ WAITING'}</span></div>`).join('')+`<div class="queue-row CLOSED"><span class="queue-id" style="color:var(--dim)">■ ${qDisplayClosed ?? '—'} clos / ${qDisplayTotal ?? '—'}</span></div>`;
  const rf=(D&&D.runtime_freshness)||{};
  const freshnessClass = rf.state==='fresh'?'ok':(rf.state==='warm'?'warn':'err');
  const freshnessText = (rf.seconds>=0 && !statusUnavailable)?`${rf.state||'unknown'} · ${rf.seconds}s`:'unknown';
  const roles=monitorRoles();
  tickRole=ensureRole(tickRole,roles);
  contractRole=ensureRole(contractRole,roles);
  execRole=ensureRole(execRole,roles);
  logRole=ensureRole(logRole,roles);
  const tileRoles=roles.length ? roles : ['planner','dev','admin'];
  const agentTiles=tileRoles.map(role=>{
    const a=agents[role]||{};
    const xi=(X&&X[role])||{};
    const contractStatus=xi.contract_status||{};
    const verdict=a.verdict||contractStatus.verdict||'MUTED';
    const statusVal=a.status||contractStatus.status||'';
    const blocker=a.blocker||contractStatus.blocker_id||'NONE';
    const delta=a.delta||contractStatus.delta||'';
    const nextVal=a.next||contractStatus.next||'';
    const rl=isRateLimited(verdict,statusVal,blocker,delta);
    const v=vc(verdict,statusVal,blocker,delta);
    const bl=(!rl&&blocker&&blocker!=='NONE')?`<div class="agent-blocker"><span>▲</span>${esc(blocker)}</div>`:'';
    const age=a.tick_age_min!=null?`${a.tick_age_min}m ago`:(xi.last_ts?esc(xi.last_ts):'?');
    const schedule=a.schedule||'—';
    const nextTick=(a.next_tick_at&&a.next_tick_min!=null)?`${a.next_tick_at} · ~${a.next_tick_min}min`:'—';
    return`<div class="agent-tile fade" onclick="setContract('${role}')"><div class="agent-stripe ${v}"></div><div class="agent-inner"><div class="agent-header"><div class="agent-name-wrap"><span style="font-size:18px">${vcIcon(v)}</span><div><div class="agent-name">${role}</div><div class="agent-sched">${schedule}</div></div></div><div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px"><span class="vc ${v}">${v}</span><span class="age-chip">${age}</span></div></div><div class="agent-delta">${esc(delta)||'—'}</div>${bl}<div class="agent-next">${esc(nextVal).slice(0,120)}</div><div class="spark">${sparkHtml(role)}</div><div class="agent-footer"><span class="next-lbl">Prochain tick</span><span class="next-time">${nextTick}</span></div></div></div>`;
  }).join('');
  const wbHtml=[...(workboard.in_progress_tasks||[]).map(t=>`<div class="task-chip IN_PROGRESS" title="${t.title}"><span>⟳</span><strong>${t.id}</strong><span class="task-chip-role">${t.role}</span></div>`),
    ...(workboard.ready_tasks||[]).map(t=>`<div class="task-chip READY" title="${t.title}"><span>▶</span><strong>${t.id}</strong><span class="task-chip-role">${t.role}</span></div>`)].join('')||'<span style="color:var(--ghost);font-size:11px">Aucune tâche active</span>';
  const tickTabs=roles.map(r=>`<button class="t-tab${r===tickRole?' on':''}" onclick="setTick('${r}')">${r}</button>`).join('');
  const ctabs=roles.map(r=>`<button class="t-tab${r===contractRole?' on-v':''}" onclick="setContract('${r}')">${r}</button>`).join('');
  const etabs=roles.map(r=>`<button class="t-tab${r===execRole?' on-g':''}" onclick="setExec('${r}')">${r}</button>`).join('');
  const ex=latestExec(execRole);
  const plannerExecLinks = execRole==='planner'
    ? `<a class="ext-link" href="/api/planner/log-bundle" target="_blank">⬡ Planner bundle</a><a class="ext-link" href="/api/planner/timeline?n=120" target="_blank">⬡ Planner timeline</a>`
    : '';
  const plannerContractLinks = contractRole==='planner'
    ? `<a class="ext-link" href="/api/planner/log-bundle" target="_blank">⬡ Planner bundle</a><a class="ext-link" href="/api/planner/timeline?n=120" target="_blank">⬡ Planner timeline</a>`
    : '';
  document.getElementById('page').innerHTML=`
    ${apiErrHtml}
    ${alertsHtml}
    <div class="col-left">
      <div class="panel fade"><div class="panel-head"><span class="panel-label">Santé</span><div class="status-capsule ${hcls}" style="padding:3px 9px;font-size:10px"><span class="status-dot${health==='OK'?' live':''}"></span>${health}</div></div>
        <div class="health-hero"><div class="health-ring-wrap"><div class="health-ring ${hcls}"><div class="health-ring-inner"><div class="health-pct">${pct}</div><div class="health-pct-label">%</div></div></div></div><div class="health-status-word ${hcls}">${health}</div><div class="health-ts">${new Date().toLocaleTimeString('fr-FR')}</div></div>
        <div class="stat4"><div class="stat-tile g"><div class="stat-n g">${workboard.done ?? '—'}</div><div class="stat-lbl">DONE</div></div><div class="stat-tile b"><div class="stat-n b">${workboard.ready ?? '—'}</div><div class="stat-lbl">READY</div></div><div class="stat-tile y"><div class="stat-n y">${kpi.done_24h??'—'}</div><div class="stat-lbl">24h</div></div><div class="stat-tile v"><div class="stat-n v">${kpi.proofs??'—'}</div><div class="stat-lbl">PROOFS</div></div></div></div>
      <div class="panel fade"><div class="panel-head"><span class="panel-label">Batches</span><span style="font-size:10px;color:var(--ghost)">${qDisplayClosed ?? '—'}/${qDisplayTotal ?? '—'}</span></div><div class="panel-body"><div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div><div class="queue-states">${queueStatesHtml}</div><div class="queue-list">${qRows}</div>${mismatchHtml}</div></div>
      <div class="panel fade"><div class="panel-head"><span class="panel-label">Vélocité</span><span style="font-size:10px;color:var(--ghost)">${kpi.ts??''}</span></div><div class="stat4"><div class="stat-tile g"><div class="stat-n g">${kpi.done_total??'—'}</div><div class="stat-lbl">Total</div></div><div class="stat-tile y"><div class="stat-n y">${kpi.done_24h??'—'}</div><div class="stat-lbl">24h</div></div><div class="stat-tile"><div class="stat-n">${kpi.done_7d??'—'}</div><div class="stat-lbl">7 jours</div></div><div class="stat-tile b"><div class="stat-n b">${kpi.proofs??'—'}</div><div class="stat-lbl">Proofs</div></div></div></div>
    </div>
	    <div class="col-right">
	      <div class="panel fade"><div class="panel-head"><span class="panel-label">Agents</span><span style="font-size:10px;color:var(--ghost)">cliquer → contrat</span></div><div class="panel-body"><div class="agents-row">${agentTiles}</div></div></div>
	      <div class="panel fade"><div class="panel-head"><span class="panel-label">Workboard actif</span><span style="font-size:10px;color:var(--ghost)">${workboard.total ?? '—'} tâches · ${workboard.done ?? '—'} done</span></div><div class="panel-body"><div class="task-grid">${wbHtml}</div><div class="queue-sync ${freshnessClass}" style="margin-top:10px"><strong>Runtime freshness</strong> · ${freshnessText}</div><div style="margin-top:8px;font-size:10px;color:var(--ghost);line-height:1.5"><strong>sources:</strong><br>queue=${esc(shortPath(src.queue||''))}<br>workboard=${esc(shortPath(src.workboard||''))}</div></div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Exécution récente</span><span style="color:var(--emerald);font-size:11px;font-weight:600">${execRole}</span></div><div class="panel-body"><div class="tab-bar" id="exec-tabs">${etabs}</div><div class="exec-meta">${execMetaHtml(execRole)}</div><div class="exec-logs"><div class="log-box"><div class="log-head">fc-ticks (${execRole}.tick.log)</div><div class="log-scroll">${logLinesHtml(ex.tick_tail)}</div></div><div class="log-box"><div class="log-head">role-runner (${execRole}.live.log)</div><div class="log-scroll">${logLinesHtml(ex.runner_tail)}</div></div><div class="log-box"><div class="log-head">runner-events (${execRole}.events.log)</div><div class="log-scroll">${logLinesHtml(ex.events_tail)}</div></div></div><div class="link-row"><a class="ext-link" href="/api/execution/${execRole}" target="_blank">⬡ Execution JSON</a><a class="ext-link" href="/api/logs/${execRole}" target="_blank">⬡ Runner logs</a><a class="ext-link" href="/api/logs/${execRole}/events" target="_blank">⬡ Runner events</a><a class="ext-link" href="/api/ticks/${execRole}" target="_blank">⬡ Ticks</a>${plannerExecLinks}</div></div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Execution Truth Matrix</span><span style="color:var(--amber);font-size:11px;font-weight:600">activité réelle · qualité · signaux</span></div><div class="panel-body">${insightsHtml()}</div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Logs agents</span><span style="color:var(--aqua);font-size:11px;font-weight:600">${logRole} · ${logKind}</span></div><div class="panel-body">${logViewerHtml()}</div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Diagnostic Rapide Runtime</span><span style="color:var(--amber);font-size:11px;font-weight:600">root causes auto</span></div><div class="panel-body">${runtimeDiagnosticsHtml()}</div></div>
		      <div class="panel fade"><div class="panel-head"><span class="panel-label">Error Feed Global</span><span style="color:var(--coral);font-size:11px;font-weight:600">${(F&&F.count)||0} événements</span></div><div class="panel-body"><div class="log-box"><div class="log-head">Dernières erreurs/warnings (tous agents)</div><div class="log-scroll">${errorFeedHtml()}</div></div></div></div>
		      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
	        <div class="panel fade"><div class="panel-head"><span class="panel-label">Ticks</span></div><div class="panel-body"><div class="tab-bar" id="tick-tabs">${tickTabs}</div><div class="tick-scroll" id="tick-content">${tickRowsHtml(tickRole)}</div></div></div>
	        <div class="panel fade"><div class="panel-head"><span class="panel-label">Contrat</span><span style="color:var(--lavender);font-size:11px;font-weight:600">${contractRole}</span></div><div class="panel-body"><div class="tab-bar" id="contract-tabs">${ctabs}</div><div class="contract-block" id="contract-content">${contractBodyHtml(contractRole)}</div><div class="link-row"><a class="ext-link" href="/api/contract/${contractRole}" target="_blank">⬡ JSON</a><a class="ext-link" href="/api/logs/${contractRole}" target="_blank">⬡ Logs</a><a class="ext-link" href="/api/logs/${contractRole}/events" target="_blank">⬡ Events</a><a class="ext-link" href="/api/ticks/${contractRole}" target="_blank">⬡ Ticks</a><a class="ext-link" href="/api/workboard" target="_blank">⬡ Workboard</a>${plannerContractLinks}</div></div></div>
	      </div>
	    </div>`;
}
function setTick(r){tickRole=r;const el=document.getElementById('tick-content');const tabs=document.querySelectorAll('#tick-tabs .t-tab');if(el)el.innerHTML=tickRowsHtml(r);tabs.forEach(t=>t.classList.toggle('on',t.textContent.trim()===r));}
function setContract(r){contractRole=r;render();}
function setExec(r){execRole=r;render();}
async function setLogRole(r){logRole=r;await doRefresh();}
async function setLogKind(k){logKind=k;await doRefresh();}
async function doRefresh(){cdr=12;const ri=document.getElementById('ri');if(ri)ri.innerHTML='<span class="spin-sm"></span>';await load();render();if(ri)ri.textContent='⟳';}
function startCd(){clearInterval(iv);iv=setInterval(async()=>{cdr--;const el=document.getElementById('cd');const ts=document.getElementById('hd-ts');if(ts)ts.textContent=new Date().toLocaleTimeString('fr-FR');if(cdr<=0){cdr=12;await load();render();}if(el)el.textContent=`auto ${cdr}s`;},1000);}
doRefresh().then(startCd);
</script>
</body>
</html>"""

PLANNER_DEBUG_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FC Planner Debug</title>
<style>
*{box-sizing:border-box} body{margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#060b11;color:#c9dae8}
.wrap{max-width:1440px;margin:0 auto;padding:16px}
.top{display:flex;gap:10px;align-items:center;justify-content:space-between;margin-bottom:12px}
.title{font-size:18px;font-weight:700;color:#fff}
.actions{display:flex;gap:8px;align-items:center}
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid #274159;border-radius:8px;color:#9fd4ff;text-decoration:none;background:#0e1824}
.btn:hover{border-color:#37b7ff}
.cd{font-size:11px;color:#7ea2bd}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.card{background:#0c1520;border:1px solid #1d2f41;border-radius:10px;overflow:hidden}
.head{padding:9px 12px;background:#101c2a;border-bottom:1px solid #1d2f41;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#7ea2bd}
.body{padding:12px}
.kpi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
.pill{padding:8px;border:1px solid #223447;border-radius:8px;background:#0b121c}
.lbl{font-size:10px;color:#7191ab;text-transform:uppercase}
.val{font-size:17px;color:#fff;font-weight:700}
.ok{color:#00e58a}.warn{color:#ffc24f}.err{color:#ff5d75}
.list{margin:0;padding-left:18px;line-height:1.5}
.table{width:100%;border-collapse:collapse;font-size:11px}
.table th,.table td{border-bottom:1px solid #1a2a39;padding:6px 6px;text-align:left;vertical-align:top}
.table th{color:#7ea2bd;font-weight:600}
.mono{white-space:pre-wrap;word-break:break-word;background:#070e16;border:1px solid #1a2a39;border-radius:8px;padding:10px;max-height:300px;overflow:auto;font-size:11px;line-height:1.45}
.span2{grid-column:1/-1}
@media(max-width:980px){.grid{grid-template-columns:1fr}.kpi{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="title">Planner Debug</div>
    <div class="actions">
      <a class="btn" href="/">← Dashboard</a>
      <a class="btn" href="/api/planner/log-bundle" target="_blank">Bundle JSON</a>
      <button class="btn" onclick="refreshNow()">⟳ Refresh</button>
      <span id="cd" class="cd">auto 15s</span>
    </div>
  </div>
  <div id="app" class="grid">
    <div class="card span2"><div class="body">Chargement…</div></div>
  </div>
</div>
<script>
let cdr=15, iv=null;
function esc(v){return String(v||'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
function scoreCls(s){if(s>=85)return'ok';if(s>=70)return'warn';return'err'}
function lines(arr, empty='(empty)'){if(!arr||!arr.length)return empty;return arr.map(x=>String(x)).join('\n')}
function normTs(v){return v||'—'}
function auditRows(events){
  if(!events||!events.length) return '<tr><td colspan="8">Aucun event audit</td></tr>';
  return events.slice().reverse().slice(0,25).map(e=>`<tr>
    <td>${esc(normTs(e.ts_utc))}</td>
    <td>${esc(e.source||'')}</td>
    <td>${esc(e.task_update||'')}</td>
    <td>${esc(e.delta||'')}</td>
    <td>${esc(e.guardian_score)}</td>
    <td>${esc(e.guardian_level||'')}</td>
    <td>${esc(e.blocker_id||'')}</td>
    <td>${esc(e.next_action_unique||'')}</td>
  </tr>`).join('');
}
function render(bundle,status){
  const g=bundle.guardian_latest||{};
  const issues=(g.issues||[]);
  const recos=(g.recommendations||[]);
  const streaks=(g.streaks||{});
  const score=Number(g.score||0);
  const scls=scoreCls(score);
  const health=(status&&status.health)||'—';
  const app=document.getElementById('app');
  app.innerHTML=`
    <div class="card span2"><div class="head">Guardian Snapshot</div><div class="body">
      <div class="kpi">
        <div class="pill"><div class="lbl">Health</div><div class="val">${esc(health)}</div></div>
        <div class="pill"><div class="lbl">Score</div><div class="val ${scls}">${esc(g.score)}</div></div>
        <div class="pill"><div class="lbl">Level</div><div class="val">${esc(g.level||'')}</div></div>
        <div class="pill"><div class="lbl">Updated</div><div class="val" style="font-size:12px">${esc(normTs(g.ts_utc))}</div></div>
        <div class="pill"><div class="lbl">Ready Idle Streak</div><div class="val">${esc(streaks.ready_idle_streak)}</div></div>
        <div class="pill"><div class="lbl">Low Score Streak</div><div class="val">${esc(streaks.low_score_streak)}</div></div>
        <div class="pill"><div class="lbl">Runway No Batch</div><div class="val">${esc(streaks.runway_no_batch_streak)}</div></div>
        <div class="pill"><div class="lbl">Source</div><div class="val" style="font-size:12px">${esc(g.source||'')}</div></div>
      </div>
    </div></div>

    <div class="card"><div class="head">Issues</div><div class="body"><ul class="list">${issues.length?issues.map(i=>`<li>${esc(i)}</li>`).join(''):'<li>none</li>'}</ul></div></div>
    <div class="card"><div class="head">Recommendations</div><div class="body"><ul class="list">${recos.length?recos.map(i=>`<li>${esc(i)}</li>`).join(''):'<li>none</li>'}</ul></div></div>

    <div class="card span2"><div class="head">Planner Audit (Latest 25)</div><div class="body">
      <table class="table">
        <thead><tr><th>ts</th><th>source</th><th>task_update</th><th>delta</th><th>score</th><th>level</th><th>blocker</th><th>next_action</th></tr></thead>
        <tbody>${auditRows(bundle.audit_events||[])}</tbody>
      </table>
    </div></div>

    <div class="card"><div class="head">Planner Timeline</div><div class="body"><div class="mono">${esc(lines(bundle.timeline||[]))}</div></div></div>
    <div class="card"><div class="head">Runner Events</div><div class="body"><div class="mono">${esc(lines(bundle.runner_events||[]))}</div></div></div>
  `;
}
async function load(){
  const [bundle,status]=await Promise.all([
    fetch('/api/planner/log-bundle?n=120').then(r=>r.json()),
    fetch('/api/status').then(r=>r.json())
  ]);
  render(bundle,status);
}
async function refreshNow(){cdr=15;await load();}
function startCd(){
  clearInterval(iv);
  iv=setInterval(async()=>{
    cdr--;
    const el=document.getElementById('cd');
    if(el)el.textContent=`auto ${cdr}s`;
    if(cdr<=0){cdr=15;await load();}
  },1000);
}
refreshNow().then(startCd);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(
        HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.get("/planner-debug", response_class=HTMLResponse)
def planner_debug_page():
    return HTMLResponse(
        PLANNER_DEBUG_HTML,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

if __name__=="__main__":
    print("\u2705  Monitor : http://localhost:7779")
    uvicorn.run(app, host="0.0.0.0", port=7779, log_level="warning")
