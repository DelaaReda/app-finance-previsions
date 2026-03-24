#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

READY_STATES = {"READY", "READY_PLANNER", "READY_DEV"}
ACTIVE_STATES = {"IN_PROGRESS", "REVIEW"}
MESSAGE_TTL = {"planner": 120, "dev": 90, "admin": 60}
STALE_CONTRACT_SECONDS = 3600


@dataclass
class Intent:
    target: str
    message: str
    reason: str
    ttl: int


@dataclass
class PolicyConfig:
    root: Path
    state_dir: Path
    queue_path: Path
    board_path: Path
    reconcile_report_path: Path
    state_file: Path
    ready_starvation_seconds: int = 1800
    stalled_in_progress_seconds: int = 14400
    escalate_after_cycles: int = 2
    reset_window_seconds: int = 21600


@dataclass
class PolicyResult:
    intents: list[Intent]
    metrics: dict[str, int]


def _canonical_role(role: str) -> str:
    token = (role or "").strip().lower()
    if token in {"backend_engineer", "frontend_engineer", "data_analyst", "integrator"}:
        return "dev"
    if token in {"qa", "tester", "infra_engineer", "clawsentinel"}:
        return "admin"
    if token in {"analyst", "architect", "po", "vision-architect-tasks-planner", "vision_architect_tasks_planner"}:
        return "planner"
    return token


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return default


def _parse_iso_epoch(value: str) -> int:
    raw = (value or "").strip()
    if not raw:
        return 0
    try:
        if raw.endswith("Z"):
            from datetime import datetime, timezone

            return int(datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
        from datetime import datetime, timezone

        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except Exception:
        return 0


def _parse_contract(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return values
    for raw in lines:
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip().upper()
        if key and key not in values:
            values[key] = value.strip()
    return values


def _contract_is_fresh(path: Path, now_epoch: int, max_age_seconds: int = STALE_CONTRACT_SECONDS) -> bool:
    try:
        if not path.exists():
            return False
        return (now_epoch - int(path.stat().st_mtime)) <= max_age_seconds
    except Exception:
        return False


def _parse_evidence(raw: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for frag in str(raw or "").split(";"):
        item = frag.strip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key and key not in pairs:
            pairs[key] = value.strip()
    return pairs


def _load_state(path: Path) -> dict:
    state = _load_json(path, {})
    return state if isinstance(state, dict) else {}


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _bump_streak(container: dict, category: str, key: str, now_epoch: int, reset_window: int) -> int:
    group = container.setdefault(category, {})
    entry = group.get(key, {}) if isinstance(group.get(key), dict) else {}
    last_seen = int(entry.get("last_seen", 0) or 0)
    count = int(entry.get("count", 0) or 0)
    if now_epoch - last_seen > reset_window:
        count = 0
    count += 1
    group[key] = {"count": count, "last_seen": now_epoch}
    return count


def evaluate_policy(config: PolicyConfig, now_epoch: int | None = None) -> PolicyResult:
    now_epoch = int(now_epoch or time.time())
    queue_obj = _load_json(config.queue_path, {"items": []})
    board_obj = _load_json(config.board_path, {"tasks": []})
    report = _load_json(config.reconcile_report_path, {})
    state = _load_state(config.state_file)
    intents: list[Intent] = []
    metrics = {
        "blocked_agents_detected": 0,
        "messages_sent": 0,
        "messages_deduped": 0,
        "claims_triggered": 0,
        "escalations_triggered": 0,
        "unblocks_successful": 0,
    }

    tasks = board_obj.get("tasks", []) if isinstance(board_obj, dict) else []
    seen_targets: set[str] = set()

    # 1) READY starvation / unclaimed READY tasks.
    for task in tasks:
        if not isinstance(task, dict):
            continue
        state_token = str(task.get("state", "")).strip().upper()
        if state_token not in READY_STATES:
            continue
        updated_epoch = _parse_iso_epoch(str(task.get("updated_at", "")))
        ready_starved = bool(task.get("ready_starvation")) or (
            updated_epoch > 0 and (now_epoch - updated_epoch) >= config.ready_starvation_seconds
        )
        if not ready_starved:
            continue
        role = _canonical_role(str(task.get("role") or task.get("assignee") or ""))
        if role not in {"planner", "dev"} or role in seen_targets:
            continue
        task_id = str(task.get("id", "")).strip() or "task"
        intents.append(
            Intent(
                target=role,
                ttl=MESSAGE_TTL[role],
                reason="ready_starvation",
                message=f"READY task {task_id} is aging without claim. Claim it now and publish verify proof.",
            )
        )
        seen_targets.add(role)
        metrics["blocked_agents_detected"] += 1
        metrics["claims_triggered"] += 1

    # 2) Contract-guard blocks on planner/dev -> targeted correction, then admin escalation if persistent.
    for role in ("planner", "dev"):
        if role in seen_targets:
            continue
        contract_path = config.state_dir / f"{role}.last_contract"
        if not _contract_is_fresh(contract_path, now_epoch):
            continue
        contract = _parse_contract(contract_path)
        evidence = _parse_evidence(contract.get("EVIDENCE", ""))
        status = str(contract.get("STATUS", "")).strip().upper()
        delta = str(contract.get("DELTA", "")).strip().upper()
        blocker = str(contract.get("BLOCKER_ID", "")).strip().upper()
        issues = str(evidence.get("issues", "") or "").lower()
        guard_like = (
            status == "BLOCKED"
            and (
                delta == "CONTRACT_GUARD_BLOCK"
                or "contract_guard" in issues
                or blocker.endswith("FORMAT_INVALID")
                or blocker.endswith("MISSING")
            )
        )
        if not guard_like:
            continue
        metrics["blocked_agents_detected"] += 1
        streak = _bump_streak(state, "guard_blocks", f"{role}:{blocker or delta}", now_epoch, config.reset_window_seconds)
        if streak >= config.escalate_after_cycles:
            intents.append(
                Intent(
                    target="admin",
                    ttl=MESSAGE_TTL["admin"],
                    reason="contract_guard_escalation",
                    message=f"{role} is still blocked by {blocker or delta} after {streak} cycles. Take over and clear the execution blocker.",
                )
            )
            metrics["escalations_triggered"] += 1
            seen_targets.add("admin")
        else:
            intents.append(
                Intent(
                    target=role,
                    ttl=MESSAGE_TTL[role],
                    reason="contract_guard_block",
                    message=f"Fix contract blocker {blocker or delta} now, then claim the next READY task.",
                )
            )
            seen_targets.add(role)

    # 3) Stalled in-progress work -> role nudge, then admin escalate.
    for task in tasks:
        if not isinstance(task, dict):
            continue
        state_token = str(task.get("state", "")).strip().upper()
        if state_token not in ACTIVE_STATES:
            continue
        role = _canonical_role(str(task.get("role") or task.get("assignee") or ""))
        if role not in {"planner", "dev", "admin"}:
            continue
        updated_epoch = _parse_iso_epoch(str(task.get("updated_at", "")))
        if updated_epoch <= 0 or (now_epoch - updated_epoch) < config.stalled_in_progress_seconds:
            continue
        task_id = str(task.get("id", "")).strip() or "task"
        metrics["blocked_agents_detected"] += 1
        streak = _bump_streak(state, "stalled_tasks", task_id, now_epoch, config.reset_window_seconds)
        if streak >= config.escalate_after_cycles and "admin" not in seen_targets:
            intents.append(
                Intent(
                    target="admin",
                    ttl=MESSAGE_TTL["admin"],
                    reason="stalled_in_progress_escalation",
                    message=f"Task {task_id} stayed IN_PROGRESS too long. Reconcile state or take over execution now.",
                )
            )
            metrics["escalations_triggered"] += 1
            seen_targets.add("admin")
        elif role not in seen_targets:
            intents.append(
                Intent(
                    target=role,
                    ttl=MESSAGE_TTL[role],
                    reason="stalled_in_progress",
                    message=f"Task {task_id} has no measurable progress. Publish progress or release the task now.",
                )
            )
            seen_targets.add(role)

    # 4) Reconcile report drift -> planner/admin.
    if isinstance(report, dict) and int(report.get("ready_starvation_detected", 0) or 0) > 0 and "planner" not in seen_targets:
        intents.append(
            Intent(
                target="planner",
                ttl=MESSAGE_TTL["planner"],
                reason="ready_starvation_report",
                message="State reconciler detected READY starvation. Reprioritize the active READY runway now.",
            )
        )
        seen_targets.add("planner")

    metrics["messages_sent"] = len(intents)
    _save_state(config.state_file, state)
    return PolicyResult(intents=intents[:3], metrics=metrics)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrum master unblock-first policy")
    parser.add_argument("--root", default=str(Path.cwd()))
    parser.add_argument("--state-dir", default=str(Path.home() / ".openclaw" / "cron" / "role-state"))
    parser.add_argument("--queue", default="logs-codex-runs/orchestrator-state/priority-queue.json")
    parser.add_argument("--board", default="logs-codex-runs/orchestrator-state/parallel-workstreams.json")
    parser.add_argument("--reconcile-report", default="logs-codex-runs/orchestrator-state/state-reconcile-report.json")
    parser.add_argument("--policy-state", default=str(Path.home() / ".openclaw" / "cron" / "role-state" / "scrum_policy_state.json"))
    parser.add_argument("--ready-starvation-seconds", type=int, default=1800)
    parser.add_argument("--stalled-in-progress-seconds", type=int, default=14400)
    parser.add_argument("--escalate-after-cycles", type=int, default=2)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    config = PolicyConfig(
        root=root,
        state_dir=Path(args.state_dir).expanduser().resolve(),
        queue_path=(root / args.queue).resolve() if not str(args.queue).startswith("/") else Path(args.queue).resolve(),
        board_path=(root / args.board).resolve() if not str(args.board).startswith("/") else Path(args.board).resolve(),
        reconcile_report_path=(root / args.reconcile_report).resolve() if not str(args.reconcile_report).startswith("/") else Path(args.reconcile_report).resolve(),
        state_file=Path(args.policy_state).expanduser().resolve(),
        ready_starvation_seconds=max(300, int(args.ready_starvation_seconds)),
        stalled_in_progress_seconds=max(300, int(args.stalled_in_progress_seconds)),
        escalate_after_cycles=max(1, int(args.escalate_after_cycles)),
    )
    result = evaluate_policy(config)
    for intent in result.intents:
        print(f"emit|{intent.target}|none|{intent.ttl}|{intent.message}|{intent.reason}")
    for key, value in sorted(result.metrics.items()):
        print(f"metric|{key}|{value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
