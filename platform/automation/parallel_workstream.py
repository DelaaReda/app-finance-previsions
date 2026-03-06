#!/usr/bin/env python3
"""Parallel workstream board for multi-role delivery orchestration.

This script keeps a local task mesh so specialized roles can work in parallel
while preserving explicit dependencies, handoffs, and validation ownership.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import random
import sys
import re
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DEFAULT_BOARD = Path("docs/operations/orchestrator/parallel-workstreams.json")
DEFAULT_PRIORITY_QUEUE = Path("docs/operations/orchestrator/priority-queue.json")
DEFAULT_PROOF_ROOT = Path("docs/operations/orchestrator/proofs")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHARED_LOCK_DIR = Path(
    os.environ.get("OPENCLAW_LOCK_DIR", str(ROOT / ".tmp" / "openclaw-shared-locks"))
)

INTEGRATION_REUSE_TAG = "INTEGRATION-APP-EENGINEER-RECOMMENDATIONS"
INTEGRATION_REUSE_TAG_ALIAS = "INTEGRATION-APP-ENGINEER-RECOMMENDATIONS"
PUBLIC_PLANNER_ROLE = "vision-architect-tasks-planner"
DEPRECATED_ROLES = {"analyst", "architect", "po"}
DEPRECATED_TASK_CODES = {"PO_REVIEW", "SCRUM_REVIEW"}
MIN_CHANGE_PLAN_STEPS = 5
MIN_ARCHITECTURE_CHECKS = 3
MIN_CHANGE_PLAN_WORDS = 2
MIN_REFLECTION_DIMENSIONS = 5
PRECHANGE_GATE_VERSION = 2

REFLECTION_DIMENSION_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "scope": (
        r"\b(scope|perimeter|perimetre|objectif|objective|module|endpoint|component|ui|api|task|tache|story)\b",
    ),
    "dependency_impact": (
        r"\b(dependency|dependencies|dependance|dependances|impact|blast|upstream|downstream|integration|couplage|cross[-_ ]role)\b",
    ),
    "risk": (
        r"\b(risk|risque|failure|incident|regression|tradeoff|edge[-_ ]case)\b",
    ),
    "verification": (
        r"\b(test|tests|pytest|validation|verify|verification|assert|snapshot|qa|proof|smoke)\b",
    ),
    "rollback": (
        r"\b(rollback|revert|fallback|backout|mitigation|contingency|degrade|degradation)\b",
    ),
}


def shared_lock_path(prefix: str, target: Path) -> Path:
    # Keep orchestration locks outside docs/*.lock files to avoid permission drift.
    resolved = target.resolve(strict=False)
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:20]
    return DEFAULT_SHARED_LOCK_DIR / f"{prefix}-{digest}.lock"


def ensure_shared_lock_access(lock_path: Path) -> None:
    lock_dir = lock_path.parent
    lock_dir.mkdir(parents=True, exist_ok=True)
    # Cross-runtime (host + sandbox user) write access.
    try:
        os.chmod(lock_dir, 0o1777)
    except OSError:
        pass
    try:
        if not lock_path.exists():
            lock_path.touch(exist_ok=True)
        os.chmod(lock_path, 0o666)
    except OSError:
        pass


@contextmanager
def board_lock(board_path: Path, write: bool = True):
    """Global board lock to keep multi-role writes deterministic."""
    board_text = str(board_path or "").strip()
    # Defensive: avoid creating weird "..lock" when board_path is empty (Path("") -> ".").
    if board_text in {"", ".", "./"}:
        board_path = DEFAULT_BOARD
    lock_path = shared_lock_path("parallel-workstreams", board_path)
    if write:
        ensure_shared_lock_access(lock_path)
        with lock_path.open("a+", encoding="utf-8") as lock_fh:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        return

    # Read-only mode: avoid opening lock file in write mode (sandbox/read-only envs).
    lock_handle = None
    try:
        lock_handle = lock_path.open("r", encoding="utf-8")
    except FileNotFoundError:
        if board_path.exists():
            lock_handle = board_path.open("r", encoding="utf-8")
    except PermissionError:
        if board_path.exists():
            lock_handle = board_path.open("r", encoding="utf-8")

    if lock_handle is None:
        yield
        return

    with lock_handle as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)

STATE_BACKLOG = "BACKLOG"
STATE_WAITING_DEP = "WAITING_DEP"
STATE_READY_PLANNER = "READY_PLANNER"
STATE_READY_DEV = "READY_DEV"
STATE_READY_LEGACY = "READY"
# Backward-compat alias for previous READY semantics.
STATE_READY = STATE_READY_PLANNER
STATE_IN_PROGRESS = "IN_PROGRESS"
STATE_REVIEW = "REVIEW"
STATE_DONE = "DONE"
STATE_BLOCKED = "BLOCKED"

ACTIVE_STATES = {STATE_IN_PROGRESS, STATE_REVIEW}
READY_LIKE_STATES = {STATE_BACKLOG, STATE_WAITING_DEP, STATE_READY, STATE_READY_DEV, STATE_READY_LEGACY}
PLANNER_GROUP_ROLES = {
    "planner",
    "vision_architect_tasks_planner",
    "vision-architect-tasks-planner",
    "analyst",
    "architect",
    "po",
    "product_owner",
    "owner",
    "po_engineer",
}

# Lean team consolidation: 3 rôles actifs couvrent tous les anciens rôles.
# dev couvre les rôles build/validation; admin couvre les rôles ops/safety.
DEV_GROUP_ROLES = {
    "dev",
    "backend_engineer",
    "frontend_engineer",
    "data_analyst",
    "infra_engineer",
    "integrator",
    "tester",
    "qa",
}
ADMIN_GROUP_ROLES = {
    "admin",
    "clawsentinel",
    "infra",
}

ROLE_CATALOG: Dict[str, Dict[str, object]] = {
    # Keep planner strictly serial to avoid multi-stream dependency deadlocks.
    "planner": {"wip_limit": 1, "can_edit": False, "focus": "vision conformance, dispatch hygiene, scope/value decisions, and WIP/flow checks"},
    "backend_engineer": {"wip_limit": 3, "can_edit": True, "focus": "api and backend impl"},
    "frontend_engineer": {"wip_limit": 3, "can_edit": True, "focus": "ui and frontend impl"},
    "data_analyst": {"wip_limit": 2, "can_edit": True, "focus": "data quality and metrics"},
    "infra_engineer": {"wip_limit": 2, "can_edit": True, "focus": "infra and ci/cd"},
    "integrator": {"wip_limit": 2, "can_edit": True, "focus": "cross-team integration"},
    "dev": {"wip_limit": 6, "can_edit": True, "focus": "build delivery — covers backend_engineer, frontend_engineer, data_analyst, infra_engineer, integrator, tester, qa"},
    "admin": {"wip_limit": 3, "can_edit": True, "focus": "runtime governance, cron/monitor stability, unblock and safety operations"},
    "scrum_master": {"wip_limit": 2, "can_edit": True, "focus": "active unblock coordination, queue/workboard remediation, escalation"},
    "tester": {"wip_limit": 3, "can_edit": True, "focus": "test automation and checks"},
    "qa": {"wip_limit": 3, "can_edit": True, "focus": "quality gate and validation"},
    "clawsentinel": {"wip_limit": 2, "can_edit": False, "focus": "anti-drift and safety"},
}


@dataclass(frozen=True)
class TemplateStep:
    code: str
    role: str
    deps: Tuple[str, ...]


STREAM_TEMPLATE: Tuple[TemplateStep, ...] = (
    # Canonical runtime chain: planner -> dev -> admin -> planner.
    TemplateStep("PLAN", "planner", tuple()),
    TemplateStep("ANALYSIS", "planner", ("PLAN",)),
    TemplateStep("ARCH", "planner", ("ANALYSIS",)),
    TemplateStep("DEV-01", "dev", ("ARCH",)),
    TemplateStep("DEV-02", "dev", ("DEV-01",)),
    TemplateStep("DEV-03", "dev", ("DEV-02",)),
    TemplateStep("ADMIN-01", "admin", ("DEV-03",)),
    TemplateStep("GOV_REVIEW", "planner", ("ADMIN-01",)),
)

STREAM_TEMPLATE_DEPS: Dict[str, Tuple[str, ...]] = {step.code: step.deps for step in STREAM_TEMPLATE}

DEFAULT_STEP_NOTES: Dict[str, List[str]] = {
    "PLAN": [
        "GOVERNANCE-NOTE: keep queue/workboard in sync; run scripts/parallel_workstream.py sync-priority when drift is detected.",
    ],
    "DEV-01": [
        f"{INTEGRATION_REUSE_TAG}: reuse Judge endpoint stack (apps/api/src/domains/judge/api/judge.py, apps/api/src/domains/judge/application/judge_pipeline.py, apps/api/src/domains/judge/application/g4f_client.py) + follow docs/ops/API_ENDPOINT_BEST_PRACTICES.md, docs/ops/REUSE_MODULES_CATALOG.md, and docs/ops/INTEGRATION_APP_ENGINEER_RECOMMENDATIONS.md.",
    ],
    "DEV-02": [
        f"{INTEGRATION_REUSE_TAG}: reuse existing widgets (apps/web/src/domains/forecasts/components/*) + shared UI wiring (apps/web/src/platform) before creating new components.",
    ],
    "DEV-03": [
        f"{INTEGRATION_REUSE_TAG}: avoid duplicate helpers; search reuse catalog first; keep patches minimal and covered by targeted tests and scripts/backend_regression_gate.sh.",
    ],
    "ADMIN-01": [
        f"{INTEGRATION_REUSE_TAG}: validate monitor/cron/runtime health after dev chain and capture explicit unblock or blocker evidence.",
    ],
    "GOV_REVIEW": [
        "GOVERNANCE-NOTE: final scope/value + flow/WIP review (planner absorbs legacy PO/Scrum steps).",
        f"{INTEGRATION_REUSE_TAG_ALIAS}: alias for search and legacy task notes (same meaning as {INTEGRATION_REUSE_TAG}).",
    ],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def priority_rank(value: str) -> int:
    value = (value or "").strip().upper()
    ranks = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return ranks.get(value, 9)


def task_id(stream_id: str, code: str) -> str:
    return f"{stream_id}-{code}"


def _normalize_verdict(value: str) -> str:
    token = (value or "").strip().upper()
    if token in {"GO", "PASS"}:
        return "PASS"
    if token in {"BLOCKED", "FAIL"}:
        return "BLOCKED"
    if token == "GO_WITH_CAUTION":
        return "GO_WITH_CAUTION"
    return "GO_WITH_CAUTION"


def _tests_result(value: str) -> str:
    token = (value or "").strip().upper()
    if "FAIL" in token:
        return "FAIL"
    if token.startswith("SKIP(") or token.startswith("SKIP"):
        return "SKIP"
    return "PASS"


def _yaml_quote(value: str) -> str:
    text = str(value or "")
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return f"\"{text}\""


def _auto_idempotency_key(role: str, task_id_value: str, handoff_to: str) -> str:
    seed = f"{role}|{task_id_value}|{handoff_to}|{now_iso()}|{random.randint(1000,9999)}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return f"IK-{digest}"


def _split_reasoning_list(value: str, min_items: int) -> List[str]:
    raw_items = re.split(r"[,;\n\r]+", (value or "").strip())
    items: List[str] = []
    for raw in raw_items:
        normalized = " ".join(str(raw).split())
        if not normalized:
            continue
        items.append(normalized)
        if len(items) >= 25:
            break
    if min_items <= 0:
        return items
    return items


def _normalize_reasoning_item(item: str) -> str:
    return " ".join(str(item or "").strip().lower().split())


def _count_reasoning_tokens(item: str) -> int:
    normalized = str(item or "").strip()
    return len(re.findall(r"\w+", normalized, flags=re.UNICODE))


def _coerce_reasoning_from_value(value: object) -> List[str]:
    if isinstance(value, (list, tuple)):
        return _split_reasoning_list("\n".join(str(item) for item in value if str(item).strip()), 0)
    return _split_reasoning_list((value or "").strip(), 0)


def _normalize_reasoning_match_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    return " ".join(normalized.split())


def _detect_reflection_dimensions(plan_items: List[str], arch_items: List[str]) -> List[str]:
    corpus = _normalize_reasoning_match_text(" ".join([*plan_items, *arch_items]))
    found: List[str] = []
    for dimension, patterns in REFLECTION_DIMENSION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, corpus):
                found.append(dimension)
                break
    return found


def _normalize_arch_check(item: str) -> str:
    normalized = " ".join(str(item or "").strip().lower().split())
    normalized = re.sub(r"\s+", "_", normalized)
    return normalized


def _validate_prechange_checks(
    change_plan: str,
    architecture_checks: str,
    role: str,
    *,
    strict_reflection: bool,
) -> Tuple[List[str], List[str], List[str]]:
    raw_plan_items = _split_reasoning_list(change_plan, MIN_CHANGE_PLAN_STEPS)
    if len(raw_plan_items) < MIN_CHANGE_PLAN_STEPS:
        raise SystemExit(
            "PRECHANGE_PLAN_INVALID: "
            f"role={role} requires >= {MIN_CHANGE_PLAN_STEPS} concrete reasoning steps before change"
        )

    plan_items: List[str] = []
    seen_plan = set()
    for item in raw_plan_items:
        normalized = _normalize_reasoning_item(item)
        if not normalized:
            continue
        if _count_reasoning_tokens(normalized) < MIN_CHANGE_PLAN_WORDS:
            raise SystemExit(
                "PRECHANGE_PLAN_INVALID: "
                f"role={role} change_plan item too short: '{item}' (need >= {MIN_CHANGE_PLAN_WORDS} words)"
            )
        if normalized not in seen_plan:
            plan_items.append(normalized)
            seen_plan.add(normalized)

    if len(plan_items) < MIN_CHANGE_PLAN_STEPS:
        raise SystemExit(
            "PRECHANGE_PLAN_INVALID: "
            f"role={role} requires >= {MIN_CHANGE_PLAN_STEPS} unique concrete reasoning steps before change"
        )

    arch_raw = _split_reasoning_list(architecture_checks, MIN_ARCHITECTURE_CHECKS)
    if len(arch_raw) < MIN_ARCHITECTURE_CHECKS:
        raise SystemExit(
            "ARCHITECTURE_CHECK_INVALID: "
            f"role={role} requires >= {MIN_ARCHITECTURE_CHECKS} architecture checks before change"
        )

    arch_items: List[str] = []
    for item in arch_raw:
        norm = _normalize_arch_check(item)
        if len(norm) < 6:
            raise SystemExit(f"ARCHITECTURE_CHECK_INVALID: role={role} check item too short -> '{item}'")
        if norm not in arch_items:
            arch_items.append(norm)

    if len(arch_items) < MIN_ARCHITECTURE_CHECKS:
        raise SystemExit(
            "ARCHITECTURE_CHECK_INVALID: "
            f"role={role} requires {MIN_ARCHITECTURE_CHECKS} unique architecture checks before change"
        )

    reflection_dimensions = _detect_reflection_dimensions(plan_items, arch_items)
    if strict_reflection:
        missing_dimensions = [dim for dim in REFLECTION_DIMENSION_PATTERNS if dim not in reflection_dimensions]
        if missing_dimensions:
            raise SystemExit(
                "PRECHANGE_REFLECTION_INVALID: "
                f"role={role} requires {MIN_REFLECTION_DIMENSIONS} reflection dimensions "
                "(scope, dependency_impact, risk, verification, rollback) "
                f"missing={','.join(missing_dimensions)}"
            )

    return plan_items, arch_items, reflection_dimensions


def _requires_prechange_gate(role: str) -> bool:
    return bool(ROLE_CATALOG.get(role, {}).get("can_edit", False))


def _write_proof_manifest(
    proof_root: Path,
    task: dict,
    role: str,
    artifact: str,
    note: str,
    handoff_to: str,
    handoff_id: str,
    cmd: str,
    tests_run: str,
    review_ref: str,
    reviewer_role: str,
    review_verdict: str,
    prechange_plan_items: List[str] | None,
    prechange_architecture_checks: List[str] | None,
    prechange_reflection_dimensions: List[str] | None,
    prechange_gate_version: int,
    idempotency_key: str,
) -> str:
    stream_id_value = str(task.get("stream_id", "UNSET")).strip() or "UNSET"
    task_id_value = str(task.get("id", "UNKNOWN")).strip() or "UNKNOWN"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = random.randint(100, 999)
    manifest_dir = proof_root / stream_id_value / task_id_value
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{stamp}-{suffix}.yaml"

    cmd_value = (cmd or "").strip() or "SKIP(no_cmd_recorded)"
    tests_value = (tests_run or "").strip() or "SKIP(no_tests_recorded)"
    rc_value = "0" if not cmd_value.upper().startswith("SKIP(") else "SKIP(reasoned)"
    review_ref_value = (review_ref or "").strip() or "none"
    reviewer_value = (reviewer_role or "").strip() or "none"
    verdict_value = _normalize_verdict(review_verdict)
    tests_result = _tests_result(tests_value)
    artifact_value = (artifact or "").strip() or "none"
    note_value = (note or "").strip() or "none"
    proof_id = f"PRF-{stream_id_value}-{task_id_value}-{stamp}-{suffix}"
    produced = now_iso()
    handoff_to_value = (handoff_to or "").strip() or "none"
    handoff_id_value = (handoff_id or "").strip() or "none"
    plan_items = prechange_plan_items or []
    arch_items = prechange_architecture_checks or []
    reflection_items = prechange_reflection_dimensions or []
    gate_version = int(prechange_gate_version or 1)

    lines = [
        f"proof_id: {_yaml_quote(proof_id)}",
        f"stream_id: {_yaml_quote(stream_id_value)}",
        f"task_id: {_yaml_quote(task_id_value)}",
        f"role: {_yaml_quote(role)}",
        f"produced_at_utc: {_yaml_quote(produced)}",
        "inputs:",
        f"  queue_snapshot_ref: {_yaml_quote(str(DEFAULT_PRIORITY_QUEUE))}",
        f"  workboard_snapshot_ref: {_yaml_quote(str(DEFAULT_BOARD))}",
        f"  prior_contract_ref: {_yaml_quote(f'/home/venom/.openclaw/cron/role-state/{role}.last_contract')}",
        "preconditions:",
    ]
    if plan_items:
        lines.append("  change_plan:")
        for plan_item in plan_items:
            lines.append(f"    - {_yaml_quote(str(plan_item))}")
    else:
        lines.append("  change_plan: []")
    if arch_items:
        lines.append("  architecture_checks:")
        for arch_item in arch_items:
            lines.append(f"    - {_yaml_quote(str(arch_item))}")
    else:
        lines.append("  architecture_checks: []")
    if reflection_items:
        lines.append("  reflection_dimensions:")
        for reflection_item in reflection_items:
            lines.append(f"    - {_yaml_quote(str(reflection_item))}")
    else:
        lines.append("  reflection_dimensions: []")
    lines.append(f"  gate_version: {_yaml_quote(str(gate_version))}")
    lines.extend(
        [
        "execution:",
        "  commands:",
        f"    - cmd: {_yaml_quote(cmd_value)}",
        f"      rc: {_yaml_quote(rc_value)}",
        f"      started_at_utc: {_yaml_quote(produced)}",
        f"      ended_at_utc: {_yaml_quote(produced)}",
        "validations:",
        "  tests:",
        f"    - name: {_yaml_quote('targeted')}",
        f"      result: {_yaml_quote(tests_result)}",
        f"      evidence: {_yaml_quote(tests_value)}",
        "outputs:",
        f"  role_contract_ref: {_yaml_quote(f'/home/venom/.openclaw/cron/role-state/{role}.last_contract')}",
        "  artifacts:",
        f"    - {_yaml_quote(artifact_value)}",
        "handoff:",
        f"  to_role: {_yaml_quote(handoff_to_value)}",
        f"  handoff_id: {_yaml_quote(handoff_id_value)}",
        "signoff:",
        f"  producer_agent: {_yaml_quote(role)}",
        f"  reviewer_agent: {_yaml_quote(reviewer_value)}",
        f"  qa_verdict: {_yaml_quote(verdict_value)}",
        "meta:",
        f"  idempotency_key: {_yaml_quote(idempotency_key)}",
        f"  review_ref: {_yaml_quote(review_ref_value)}",
        f"  note: {_yaml_quote(note_value)}",
        ]
    )
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(manifest_path)


def load_board(path: Path) -> dict:
    if not path.exists():
        return default_board()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"BOARD_READ_ERROR: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"BOARD_SCHEMA_ERROR: {path} root must be object")
    data.setdefault("version", 1)
    data.setdefault("updated_at", now_iso())
    data.setdefault("sprint", {"id": "S-UNSET", "goal": ""})
    roles = data.get("roles", {})
    if not isinstance(roles, dict):
        roles = {}
    # Prune deprecated always-on roles from the board state to avoid drift and stuck tasks.
    for deprecated in DEPRECATED_ROLES:
        roles.pop(deprecated, None)
    # Sync canonical role configuration while preserving any extra keys.
    for role_name, role_cfg in ROLE_CATALOG.items():
        merged = dict(roles.get(role_name, {}))
        merged.update(role_cfg)
        roles[role_name] = merged
    data["roles"] = roles
    data.setdefault("streams", [])
    data.setdefault("tasks", [])
    data.setdefault("handoffs", [])
    data.setdefault("events", [])
    migrated = migrate_legacy_stream_tasks(data)
    if migrated:
        append_event(data, "migrate_legacy_stream_tasks", {"migrated": str(migrated)})
    return data


def save_board(path: Path, board: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    board["updated_at"] = now_iso()
    path.write_text(json.dumps(board, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def default_board() -> dict:
    return {
        "version": 1,
        "updated_at": now_iso(),
        "sprint": {
            "id": "S-BOOTSTRAP",
            "goal": "Accélérer la livraison parallèle sans désordre",
            "cadence_days": 14,
        },
        "roles": ROLE_CATALOG,
        "streams": [],
        "tasks": [],
        "handoffs": [],
        "events": [],
    }


def append_event(board: dict, kind: str, details: dict) -> None:
    board.setdefault("events", []).append({
        "at": now_iso(),
        "kind": kind,
        "details": details,
    })


def task_index(board: dict) -> Dict[str, dict]:
    return {str(task.get("id")): task for task in board.get("tasks", [])}


def stream_index(board: dict) -> Dict[str, dict]:
    return {str(stream.get("id")): stream for stream in board.get("streams", [])}


def _normalize_dep_token(value: str) -> str:
    """Normalize dependency IDs to absorb underscore/hyphen drift.

    Some manual edits introduce variants like `BATCH-27-GOV-REVIEW` while the
    canonical task ID is `BATCH-27-GOV_REVIEW`. Normalize separators so runtime
    dependency evaluation remains stable and does not keep lanes stuck.
    """
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    return re.sub(r"[-_]+", "_", raw)


def ensure_stream(
    board: dict,
    stream_id: str,
    title: str,
    priority: str,
    source_state: str,
    legacy_task_codes: set[str] | None = None,
    legacy_stream_depends_on: List[str] | None = None,
) -> int:
    # GUARD: Prevent recursive micro-task explosion.
    # Only top-level streams (BATCH-NN format, max 2 segments) are allowed.
    # Streams like BATCH-05-PLAN-BACKEND are invalid and create workboard bloat.
    import re as _re
    _sid = str(stream_id).strip().upper()
    _parts = _sid.split('-')
    if _parts[0] == 'BATCH' and len(_parts) >= 4:
        # e.g. BATCH-05-PLAN-BACKEND has 4 parts → reject
        raise ValueError(
            f"ensure_stream guard: stream_id '{stream_id}' looks like a micro-task ID "
            f"(4+ segments). Only top-level streams allowed. "
            f"Use the existing role task directly instead of creating a sub-stream."
        )
    streams = stream_index(board)
    tasks = task_index(board)
    created = 0
    legacy_tasks = {str(code).strip().upper() for code in (legacy_task_codes or []) if str(code).strip()}

    if stream_id not in streams:
        board.setdefault("streams", []).append(
            {
                "id": stream_id,
                "title": title,
                "priority": priority,
                "source_state": source_state,
                "state": STATE_READY,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
    else:
        stream = streams[stream_id]
        stream["title"] = title
        stream["priority"] = priority
        stream["source_state"] = source_state
        stream["updated_at"] = now_iso()

    if legacy_tasks:
        kept: List[dict] = []
        pruned: List[str] = []
        for task in board.get("tasks", []):
            if str(task.get("stream_id", "")) != stream_id:
                kept.append(task)
                continue
            code = str(task.get("code", "")).strip().upper()
            if code in legacy_tasks:
                kept.append(task)
                continue
            pruned.append(str(task.get("id", "")) or str(code or "unknown"))
        if pruned:
            board["tasks"] = kept
            append_event(board, "prune_legacy_tasks", {"stream_id": stream_id, "pruned_task_ids": pruned})
            tasks = task_index(board)

    for step in STREAM_TEMPLATE:
        if legacy_tasks and step.code not in legacy_tasks:
            continue
        tid = task_id(stream_id, step.code)
        deps = [task_id(stream_id, dep) for dep in step.deps]
        default_notes = DEFAULT_STEP_NOTES.get(step.code, [])
        if tid in tasks:
            existing = tasks[tid]
            expected_title = f"{title} [{step.code}]"
            updated = False
            if str(existing.get("title", "")) != expected_title:
                existing["title"] = expected_title
                updated = True
            if str(existing.get("role", "")) != step.role:
                existing["role"] = step.role
                updated = True
            if str(existing.get("priority", "")) != priority:
                existing["priority"] = priority
                updated = True
            current_deps = [dep for dep in existing.get("depends_on", []) if dep]
            if str(existing.get("state", "")) != STATE_DONE and current_deps != deps:
                existing["depends_on"] = deps
                updated = True
            if default_notes:
                notes = existing.get("notes")
                if not isinstance(notes, list):
                    notes = []
                for note in default_notes:
                    if note not in notes:
                        notes.append(note)
                        updated = True
                existing["notes"] = notes
            if updated:
                existing["updated_at"] = now_iso()
            continue
        init_state = STATE_READY if not deps else STATE_WAITING_DEP
        board.setdefault("tasks", []).append(
            {
                "id": tid,
                "stream_id": stream_id,
                "code": step.code,
                "title": f"{title} [{step.code}]",
                "role": step.role,
                "state": init_state,
                "priority": priority,
                "depends_on": deps,
                "assignee": "",
                "blocked_reason": "",
                "artifacts": [],
                "notes": list(default_notes) if default_notes else [],
                "handoff_to": "",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "started_at": "",
                "completed_at": "",
            }
        )
        tasks[tid] = board["tasks"][-1]
        created += 1

    # Remove legacy governance tasks if they were created by older templates.
    pruned: List[str] = []
    kept: List[dict] = []
    for task in board.get("tasks", []):
        if str(task.get("stream_id", "")) != stream_id:
            kept.append(task)
            continue
        code = str(task.get("code", "")).strip().upper()
        tid = str(task.get("id", "")).strip()
        state = str(task.get("state", "")).strip().upper()
        if state != STATE_DONE and (code in DEPRECATED_TASK_CODES or tid.endswith("-PO_REVIEW") or tid.endswith("-SCRUM_REVIEW")):
            pruned.append(tid or code or "unknown")
            continue
        kept.append(task)
    if pruned:
        board["tasks"] = kept
        append_event(board, "prune_legacy_tasks", {"stream_id": stream_id, "pruned_task_ids": pruned})
    return created


def _legacy_task_state_to_board_state(raw_state: str) -> str:
    value = (raw_state or "").strip().lower()
    if value in {"ready", "rdy", "queued", "queue", "open", "unblocked", "start", "todo"}:
        return STATE_READY_PLANNER
    if value in {"in_progress", "inprogress", "working", "started", "wip", "active"}:
        return STATE_IN_PROGRESS
    if value in {"blocked", "blocked_dep", "blocked-dep", "dependency_blocked"}:
        return STATE_BLOCKED
    if value in {"review", "qa", "ready_for_review"}:
        return STATE_REVIEW
    if value in {"done", "completed", "complete", "closed", "finished"}:
        return STATE_DONE
    if value in {"planned", "backlog", "wait", "waiting", "not_started", "pending", "not_started"}:
        return STATE_WAITING_DEP
    return STATE_BACKLOG


def _canonical_role(value: str) -> str:
    role = str(value or "").strip().replace("-", "_").lower()
    if not role:
        return ""
    if role in PLANNER_GROUP_ROLES:
        return "planner"
    if role in DEV_GROUP_ROLES:
        return "dev"
    if role in ADMIN_GROUP_ROLES:
        return "admin"
    if role in ROLE_CATALOG:
        return role
    return ""


def _template_default_role(code: str) -> str:
    for step in STREAM_TEMPLATE:
        if step.code == code:
            return step.role
    return "planner"


def _stream_task_id_code(stream_id: str, legacy_task: dict, index: int) -> str:
    legacy_id = str(legacy_task.get("id", "")).strip()
    if legacy_id:
        return legacy_id
    explicit_code = str(legacy_task.get("code", "")).strip()
    if explicit_code:
        explicit_code = explicit_code.upper()
        return f"{stream_id}-{explicit_code}" if stream_id else explicit_code
    return f"{stream_id}-TASK{index}"


def _stream_task_code(stream_id: str, task_id: str) -> str:
    sid = (stream_id or "").strip()
    value = (task_id or "").strip()
    if not sid:
        return value.upper()
    if value == sid:
        return ""
    code = str(value).strip()
    if sid and code.startswith(f"{sid}-"):
        code = code[len(sid) + 1 :]
    return code.upper()


def _legacy_task_needs_assignee(task_state: str) -> bool:
    return task_state in {STATE_IN_PROGRESS, STATE_REVIEW}


def _all_tasks_for_stream_done(board: dict, stream_id: str) -> bool:
    stream_id_norm = str(stream_id or "").strip()
    stream_tasks = [task for task in board.get("tasks", []) if str(task.get("stream_id", "")) == stream_id_norm]
    if not stream_tasks:
        return False
    return all(str(task.get("state", "")) == STATE_DONE for task in stream_tasks)


def _queue_item_state(item: dict) -> str:
    return _normalize_state_token(item.get("state", ""))


def _normalize_state_token(raw_state: str) -> str:
    token = str(raw_state or "").strip().upper()
    if token == "CLOSED":
        return STATE_DONE
    if token in {"READY", "READY_PLANNER"}:
        return STATE_READY
    if token == "READY_DEV":
        return STATE_READY_DEV
    return token or STATE_BACKLOG


def _derive_stream_state_from_task_states(states: set[str]) -> str:
    if STATE_IN_PROGRESS in states or STATE_REVIEW in states:
        return STATE_IN_PROGRESS
    if STATE_READY_DEV in states:
        return STATE_READY_DEV
    if STATE_READY in states or STATE_READY_LEGACY in states:
        return STATE_READY
    if STATE_WAITING_DEP in states:
        return STATE_WAITING_DEP
    if STATE_BLOCKED in states:
        return STATE_BLOCKED
    if STATE_DONE in states:
        return STATE_DONE
    if states:
        return sorted(states)[0]
    return STATE_BACKLOG


def _dependency_batches_closed(queue_states: Dict[str, str], depends_on: List[str]) -> bool:
    if not depends_on:
        return True
    for dep in depends_on:
        state = queue_states.get(str(dep).strip().upper(), "")
        if state not in {"CLOSED", "PASS"}:
            return False
    return True


def _decouple_inter_batch_dependencies(queue_obj: dict, all_batches: bool = True) -> Dict[str, int]:
    """Drop inter-batch queue dependencies according to single-batch policy."""
    items = queue_obj.get("items")
    if not isinstance(items, list):
        return {
            "decoupled_total": 0,
            "decoupled_closed": 0,
            "decoupled_open": 0,
            "waiting_dep_reclassified": 0,
        }

    counts = {
        "decoupled_total": 0,
        "decoupled_closed": 0,
        "decoupled_open": 0,
        "waiting_dep_reclassified": 0,
    }
    closed_states = {"CLOSED", "DONE", "PASS"}
    for item in items:
        if not isinstance(item, dict):
            continue
        state = _queue_item_state(item)
        should_enforce = all_batches or state not in closed_states
        deps = [str(dep).strip().upper() for dep in item.get("depends_on", []) if str(dep).strip()]
        removed_dependencies = False
        if should_enforce and deps:
            if not item.get("legacy_depends_on"):
                item["legacy_depends_on"] = deps
            item["depends_on"] = []
            item["dependency_policy"] = "single_batch"
            item["inter_batch_decoupled_at"] = now_iso()
            item["updated_at"] = now_iso()
            counts["decoupled_total"] += 1
            if state in closed_states:
                counts["decoupled_closed"] += 1
            else:
                counts["decoupled_open"] += 1
            removed_dependencies = True
        if removed_dependencies and state == "WAITING_DEP":
            item["state"] = "PLANNED"
            item["updated_at"] = now_iso()
            counts["waiting_dep_reclassified"] += 1
    return counts


def _count_queue_inter_batch_dependencies(queue_obj: dict) -> int:
    items = queue_obj.get("items")
    if not isinstance(items, list):
        return 0
    total = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        deps = item.get("depends_on", [])
        if isinstance(deps, list):
            total += sum(1 for dep in deps if str(dep).strip())
        elif str(deps).strip():
            total += 1
    return total


def _queue_inter_batch_dep_count(queue_path: Path) -> int:
    if not queue_path.exists():
        return 0
    try:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    return _count_queue_inter_batch_dependencies(payload)


def _count_cross_stream_task_dependencies(board: dict) -> int:
    tasks = board.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return 0
    by_id = task_index(board)
    by_norm: Dict[str, dict] = {}
    for dep_id, dep_task in by_id.items():
        token = _normalize_dep_token(dep_id)
        if token and token not in by_norm:
            by_norm[token] = dep_task

    total = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        stream_id = str(task.get("stream_id", "")).strip()
        if not stream_id:
            continue
        deps_raw = [str(dep).strip() for dep in (task.get("depends_on") or []) if str(dep).strip()]
        if not deps_raw:
            continue
        for dep in deps_raw:
            dep_task = by_id.get(dep) or by_id.get(dep.upper()) or by_norm.get(_normalize_dep_token(dep))
            if not isinstance(dep_task, dict):
                continue
            dep_stream = str(dep_task.get("stream_id", "")).strip()
            if dep_stream and dep_stream != stream_id:
                total += 1
    return total


def _sanitize_task_dependencies(board: dict) -> int:
    """Keep only same-stream task dependencies; remove cross-batch links."""
    tasks = board.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return 0
    by_id = task_index(board)
    by_norm: Dict[str, dict] = {}
    for dep_id, dep_task in by_id.items():
        token = _normalize_dep_token(dep_id)
        if token and token not in by_norm:
            by_norm[token] = dep_task
    cleaned = 0
    for task in tasks:
        stream_id = str(task.get("stream_id", "")).strip()
        deps_raw = [str(dep).strip() for dep in (task.get("depends_on") or []) if str(dep).strip()]
        if not deps_raw:
            continue
        keep: List[str] = []
        seen: set[str] = set()
        for dep in deps_raw:
            dep_task = by_id.get(dep) or by_id.get(dep.upper()) or by_norm.get(_normalize_dep_token(dep))
            if not isinstance(dep_task, dict):
                cleaned += 1
                continue
            dep_id = str(dep_task.get("id", "")).strip()
            dep_stream = str(dep_task.get("stream_id", "")).strip()
            if stream_id and dep_stream and dep_stream != stream_id:
                cleaned += 1
                continue
            if dep_id and dep_id not in seen:
                keep.append(dep_id)
                seen.add(dep_id)
        if keep != deps_raw:
            task["depends_on"] = keep
            task["updated_at"] = now_iso()
    return cleaned


def migrate_legacy_stream_tasks(board: dict) -> int:
    tasks_by_id = task_index(board)
    migrated = 0

    for stream in board.get("streams", []):
        if not isinstance(stream, dict):
            continue

        stream_id = str(stream.get("id", "")).strip()
        if not stream_id:
            continue

        stream_title = str(stream.get("title", stream_id)).strip() or stream_id
        priority = str(stream.get("priority", "P2")).strip().upper() or "P2"
        legacy_tasks = stream.get("tasks")
        legacy_task_codes: set[str] = set()
        stream_depends_on: list[str] = []
        raw_depends_on = stream.get("depends_on")
        if isinstance(raw_depends_on, list):
            stream_depends_on = [str(dep).strip().upper() for dep in raw_depends_on if str(dep).strip()]
        if isinstance(legacy_tasks, list):
            for raw_task in legacy_tasks:
                if not isinstance(raw_task, dict):
                    continue
                task_id = str(raw_task.get("id", "")).strip()
                if task_id:
                    legacy_task_codes.add(_stream_task_code(stream_id, task_id).upper())
        if not isinstance(legacy_tasks, list):
            continue

        stream_migrated = 0
        for idx, raw_task in enumerate(legacy_tasks):
            if not isinstance(raw_task, dict):
                continue
            task_id = _stream_task_id_code(stream_id, raw_task, idx + 1).upper()
            task_code = _stream_task_code(stream_id, task_id)
            task_code = task_code if task_code else str(raw_task.get("code", "")).strip().upper()
            if not task_code:
                continue

            state = _legacy_task_state_to_board_state(raw_task.get("status", ""))
            assigned_to = _canonical_role(raw_task.get("assigned_to", ""))
            if not assigned_to:
                assigned_to = _template_default_role(task_code)
            # No cross-batch dependency propagation: keep only in-stream template deps.
            depends_on = [f"{stream_id}-{dep}" for dep in STREAM_TEMPLATE_DEPS.get(task_code, ())]
            notes = []
            description = str(raw_task.get("description", "")).strip()
            if description:
                notes.append(f"legacy_note: {description}")
            existing = tasks_by_id.get(task_id)
            if existing:
                changed = False
                if str(existing.get("stream_id", "")).strip() != stream_id:
                    existing["stream_id"] = stream_id
                    changed = True
                if str(existing.get("code", "")).strip() != task_code:
                    existing["code"] = task_code
                    changed = True
                expected_title = f"{stream_title} [{task_code}]"
                if str(existing.get("title", "")).strip() != expected_title:
                    existing["title"] = expected_title
                    changed = True
                if str(existing.get("role", "")).strip() == "":
                    if assigned_to:
                        existing["role"] = assigned_to
                        changed = True
                if str(existing.get("state", "")) in {STATE_BACKLOG, STATE_WAITING_DEP, STATE_READY} and existing.get("state") != state:
                    existing["state"] = state
                    changed = True
                if str(existing.get("state", "")) not in {STATE_DONE} and task_code in legacy_task_codes:
                    existing["depends_on"] = depends_on
                    changed = True
                if _legacy_task_needs_assignee(state) and not str(existing.get("assignee", "")).strip() and assigned_to:
                    existing["assignee"] = assigned_to
                    changed = True
                existing_notes = [str(item).strip() for item in (existing.get("notes") or []) if str(item).strip()]
                for note in notes:
                    if note not in existing_notes:
                        existing_notes.append(note)
                        changed = True
                existing["notes"] = existing_notes
            if existing and task_code not in legacy_task_codes:
                existing_depends = [dep for dep in (existing.get("depends_on") or []) if str(dep).strip()]
                if depends_on != existing_depends:
                    existing["depends_on"] = depends_on
                    changed = True
            elif existing:
                if depends_on != [dep for dep in (existing.get("depends_on") or []) if str(dep).strip()]:
                    existing["depends_on"] = depends_on
                    changed = True
            elif depends_on != []:
                existing["depends_on"] = depends_on
                changed = True
            if existing is None:
                board.setdefault("tasks", []).append(
                    {
                        "id": task_id,
                        "stream_id": stream_id,
                        "code": task_code,
                        "title": f"{stream_title} [{task_code}]",
                        "role": assigned_to or "planner",
                        "state": state,
                        "priority": priority,
                        "depends_on": depends_on,
                        "assignee": assigned_to if _legacy_task_needs_assignee(state) else "",
                        "blocked_reason": "",
                        "artifacts": [],
                        "notes": notes,
                        "handoff_to": "",
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                        "started_at": now_iso() if _legacy_task_needs_assignee(state) else "",
                        "completed_at": now_iso() if state == STATE_DONE else "",
                    }
                )
                tasks_by_id = task_index(board)
                migrated += 1
                stream_migrated += 1
                continue
            if str(existing.get("priority", "")).strip() != priority:
                existing["priority"] = priority
                changed = True
            if changed:
                existing["updated_at"] = now_iso()

        if stream_migrated:
            append_event(
                board,
                "migrated_legacy_tasks",
                {
                    "stream_id": stream_id,
                    "migrated_count": str(stream_migrated),
                },
            )

    return migrated


def _auto_advance_queue(board: dict, queue_obj: dict) -> Tuple[int, str | None, int, Dict[str, int]]:
    items = queue_obj.get("items")
    if not isinstance(items, list):
        queue_obj["items"] = []
        return (
            0,
            None,
            0,
            {
                "decoupled_total": 0,
                "decoupled_closed": 0,
                "decoupled_open": 0,
                "waiting_dep_reclassified": 0,
            },
        )

    queue_states: Dict[str, str] = {}
    for item in items:
        sid = str(item.get("id", "")).strip().upper()
        if not sid:
            continue
        queue_states[sid] = _queue_item_state(item)

    closed_count = 0
    opened_batch = None
    synced_queue_items = 0
    decoupled_counts = _decouple_inter_batch_dependencies(queue_obj, all_batches=True)

    # Build stream state index from workboard for bidirectional sync.
    # Task-derived state is preferred (runtime truth), stream-level state is fallback metadata.
    stream_states_from_wb: Dict[str, str] = {}
    task_stream_states: Dict[str, set[str]] = {}
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        sid = str(task.get("stream_id", "")).strip().upper()
        if not sid:
            continue
        task_stream_states.setdefault(sid, set()).add(_normalize_state_token(task.get("state", "")))
    for sid, states in task_stream_states.items():
        stream_states_from_wb[sid] = _derive_stream_state_from_task_states(states)

    for stream in board.get("streams", []):
        sid = str(stream.get("id", "")).strip().upper()
        if sid and sid not in stream_states_from_wb:
            stream_states_from_wb[sid] = _normalize_state_token(stream.get("state", ""))

    # Keep queue stream-state aligned with workboard stream-state for active lanes.
    # Previous behavior only propagated WAITING_DEP/READY -> IN_PROGRESS.
    # That left stale queue entries when a stream returned to READY after plan/arch
    # completion, causing "queue READY=0" while the workboard had READY tasks.
    for item in items:
        item_id = str(item.get("id", "")).strip().upper()
        if not item_id:
            continue
        q_state = queue_states.get(item_id, "")
        wb_stream_state = stream_states_from_wb.get(item_id, "")
        desired_state = None
        if wb_stream_state in {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS"}:
            desired_state = _normalize_state_token(wb_stream_state)
        elif wb_stream_state in {"WAITING_DEP", "PLANNED"}:
            desired_state = _normalize_state_token(wb_stream_state)
        elif wb_stream_state in {"DONE", "CLOSED"}:
            desired_state = "CLOSED"

        # Also reconcile PLANNED -> READY/IN_PROGRESS when the stream is already active on workboard.
        if desired_state and q_state in {"PLANNED", "WAITING_DEP", "READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS"} and q_state != desired_state:
            item["state"] = desired_state
            item["updated_at"] = now_iso()
            if desired_state in {"READY", "READY_PLANNER", "READY_DEV"}:
                item["dispatch_authorized"] = True
                item.setdefault("ready_at", now_iso())
            if desired_state == "CLOSED":
                item.setdefault("closed_at", now_iso())
                closed_count += 1
            queue_states[item_id] = desired_state
            synced_queue_items += 1

    for item in items:
        item_id = str(item.get("id", "")).strip().upper()
        if not item_id:
            continue
        state = queue_states.get(item_id, "")
        if state not in {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS"}:
            continue
        if _all_tasks_for_stream_done(board, item_id):
            item["state"] = "CLOSED"
            item["closed_at"] = now_iso()
            queue_states[item_id] = "CLOSED"
            closed_count += 1

    active_count = sum(1 for item in items if _queue_item_state(item) in {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS"})
    if active_count:
        return closed_count, None, synced_queue_items, decoupled_counts

    for item in items:
        if _queue_item_state(item) not in {"PLANNED", "WAITING_DEP"}:
            continue
        item["state"] = "READY_PLANNER"
        item["dispatch_authorized"] = True
        item.setdefault("ready_at", now_iso())
        if "opened_at" not in item:
            item["opened_at"] = now_iso()
        opened_batch = str(item.get("id", "")).strip()
        break

    return closed_count, opened_batch, synced_queue_items, decoupled_counts



def _update_stream_next_action(board: dict) -> None:
    """Update stream.next_action to reflect the real next READY task.
    
    This prevents agents from reading stale next_action like 'ouvrir BATCH-XX-PLAN'
    when PLAN is already DONE. Called after recompute_states so states are fresh.
    """
    tasks_by_stream: dict = {}
    for task in board.get("tasks", []):
        sid = str(task.get("stream_id", ""))
        tasks_by_stream.setdefault(sid, []).append(task)

    for stream in board.get("streams", []):
        sid = str(stream.get("id", ""))
        if not sid:
            continue
        stream_tasks = tasks_by_stream.get(sid, [])
        if not stream_tasks:
            continue

        # Find the first READY or IN_PROGRESS task (canonical next step)
        ordered_codes = [step.code for step in STREAM_TEMPLATE]
        def task_order(t: dict) -> int:
            code = str(t.get("code", "")).upper()
            try:
                return ordered_codes.index(code)
            except ValueError:
                return 999

        ready_tasks = sorted(
            [t for t in stream_tasks if t.get("state") in (STATE_READY, STATE_READY_DEV, STATE_IN_PROGRESS)],
            key=task_order
        )
        done_tasks = [t for t in stream_tasks if t.get("state") == STATE_DONE]

        if not ready_tasks:
            # All done or all waiting
            if len(done_tasks) == len(stream_tasks) and stream_tasks:
                new_action = "batch complete — awaiting GOV_REVIEW closure"
            else:
                # Find next waiting_dep task (what will be ready next)
                waiting = sorted(
                    [t for t in stream_tasks if t.get("state") == STATE_WAITING_DEP],
                    key=task_order
                )
                if waiting:
                    next_t = waiting[0]
                    new_action = f"attendre completion de {next_t.get('depends_on',['?'])[0] if next_t.get('depends_on') else '?'} puis claim {next_t['id']} (role={next_t.get('role','?')})"
                else:
                    continue
        else:
            next_t = ready_tasks[0]
            code = str(next_t.get("code", "")).upper()
            role = str(next_t.get("role", "?"))
            tid = str(next_t.get("id", ""))
            state = str(next_t.get("state", ""))
            verb = "compléter" if state == STATE_IN_PROGRESS else "claim"
            ready_label = "READY_DEV" if state == STATE_READY_DEV else "READY_PLANNER"
            new_action = f"{verb} {tid} ({ready_label} pour {role})"

        old_action = stream.get("next_action", "")
        if old_action != new_action:
            stream["next_action"] = new_action
            stream["updated_at"] = now_iso()


def recompute_states(board: dict, queue_states: Dict[str, str] | None = None) -> None:
    _sanitize_task_dependencies(board)
    tasks_by_id = task_index(board)
    tasks_by_norm: Dict[str, dict] = {}
    for _task_id, _task in tasks_by_id.items():
        _norm = _normalize_dep_token(_task_id)
        if _norm and _norm not in tasks_by_norm:
            tasks_by_norm[_norm] = _task
    # Charger la priority-queue pour résoudre les dépendances de haut niveau (BATCH-NN)
    if queue_states is None:
        queue_states = {}
        try:
            _pq = json.loads(DEFAULT_PRIORITY_QUEUE.read_text(encoding="utf-8"))
            for _item in _pq.get("items", []):
                _sid = str(_item.get("id", "")).strip().upper()
                _st  = str(_item.get("state", "")).strip().upper()
                if _sid:
                    queue_states[_sid] = _st
        except Exception:
            pass
    _queue_closed = {"CLOSED", "DONE", "PASS"}
    for task in board.get("tasks", []):
        raw_state = str(task.get("state", ""))
        state = _normalize_state_token(raw_state)
        if state != raw_state:
            task["state"] = state
            task["updated_at"] = now_iso()
        if state in {STATE_DONE, STATE_BLOCKED, STATE_IN_PROGRESS, STATE_REVIEW}:
            continue
        deps = [dep for dep in task.get("depends_on", []) if dep]
        def _dep_satisfied(dep: str) -> bool:
            dep_u = dep.strip().upper()
            # Priorité 1: dans le workboard
            wb_task = (
                tasks_by_id.get(dep_u)
                or tasks_by_id.get(dep)
                or tasks_by_norm.get(_normalize_dep_token(dep_u))
            )
            if wb_task:
                return wb_task.get("state") == STATE_DONE
            # Priorité 2: dans la priority-queue (BATCH-NN)
            q_state = queue_states.get(dep_u, "")
            return q_state in _queue_closed
        deps_done = all(_dep_satisfied(dep) for dep in deps)
        new_state = task.get("state", STATE_BACKLOG)
        if deps_done:
            if state in READY_LIKE_STATES:
                role_token = _canonical_role(str(task.get("role", "")) or str(task.get("assignee", "")))
                new_state = STATE_READY_DEV if role_token == "dev" else STATE_READY
        else:
            if state in READY_LIKE_STATES:
                new_state = STATE_WAITING_DEP
        if new_state != state:
            task["state"] = new_state
            task["updated_at"] = now_iso()

    tasks_by_stream: Dict[str, List[dict]] = {}
    for task in board.get("tasks", []):
        stream_id = str(task.get("stream_id", ""))
        tasks_by_stream.setdefault(stream_id, []).append(task)

    for stream in board.get("streams", []):
        stream_id = str(stream.get("id", ""))
        stream_tasks = tasks_by_stream.get(stream_id, [])
        states = {_normalize_state_token(task.get("state", "")) for task in stream_tasks}
        if stream_tasks and states == {STATE_DONE}:
            stream_state = STATE_DONE
        elif STATE_BLOCKED in states:
            stream_state = STATE_BLOCKED
        elif STATE_IN_PROGRESS in states or STATE_REVIEW in states:
            stream_state = STATE_IN_PROGRESS
        elif STATE_READY_DEV in states:
            stream_state = STATE_READY_DEV
        elif STATE_READY in states or STATE_READY_LEGACY in states:
            stream_state = STATE_READY
        else:
            stream_state = STATE_WAITING_DEP
        if stream.get("state") != stream_state:
            stream["state"] = stream_state
            stream["updated_at"] = now_iso()


def sync_from_priority_queue(board: dict, queue_path: Path, include_pass: bool = False) -> Tuple[int, int]:
    if not queue_path.exists():
        raise SystemExit(f"QUEUE_MISSING: {queue_path}")
    try:
        queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"QUEUE_READ_ERROR: {queue_path}: {exc}") from exc

    eligible = {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS"}
    if include_pass:
        eligible.add("PASS")

    created_streams = 0
    created_tasks = 0
    # Canonicalize stream states from task truth before queue sync.
    # Without this pre-pass, stale stream.state (e.g. IN_PROGRESS) can overwrite
    # queue items even when all tasks have already moved the stream back to READY.
    recompute_states(board)
    closed_streams, opened_batch, synced_queue_items, decoupled_counts = _auto_advance_queue(board, queue_obj)

    existing_streams = stream_index(board)
    streams_by_id = existing_streams
    for item in queue_obj.get("items", []):
        stream_id = str(item.get("id", "")).strip().upper()
        state = str(item.get("state", "")).strip().upper()
        if not stream_id or state not in eligible:
            continue
        title = str(item.get("title", stream_id)).strip() or stream_id
        priority = str(item.get("priority", "P2")).strip().upper() or "P2"
        stream_obj = streams_by_id.get(stream_id)
        raw_tasks = stream_obj.get("tasks") if isinstance(stream_obj, dict) else None
        legacy_task_codes = None
        legacy_stream_depends_on = None
        if isinstance(raw_tasks, list) and raw_tasks:
            tmp_codes = set()
            for raw_task in raw_tasks:
                if not isinstance(raw_task, dict):
                    continue
                legacy_task_code = _stream_task_code(stream_id, str(raw_task.get("id", "")))
                if legacy_task_code:
                    tmp_codes.add(legacy_task_code)
            if tmp_codes:
                legacy_task_codes = tmp_codes
            legacy_depends_on_raw = stream_obj.get("depends_on")
            if isinstance(legacy_depends_on_raw, list):
                legacy_stream_depends_on = legacy_depends_on_raw
        if stream_id not in existing_streams:
            created_streams += 1
        created_tasks += ensure_stream(
            board,
            stream_id,
            title,
            priority,
            state,
            legacy_task_codes=legacy_task_codes,
            legacy_stream_depends_on=legacy_stream_depends_on,
        )
        existing_streams = stream_index(board)
        streams_by_id = existing_streams

    remaining_inter_batch_deps = _count_queue_inter_batch_dependencies(queue_obj)
    if remaining_inter_batch_deps > 0:
        raise SystemExit(
            "QUEUE_DEP_POLICY_VIOLATION: "
            f"inter_batch_dependencies_remaining={remaining_inter_batch_deps} queue={queue_path}"
        )

    if (
        closed_streams
        or opened_batch
        or synced_queue_items
        or decoupled_counts["decoupled_total"]
        or decoupled_counts["waiting_dep_reclassified"]
    ):
        queue_obj.setdefault("updated_at", now_iso())
        queue_path.write_text(json.dumps(queue_obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        append_event(
            board,
            "auto_advance_queue",
            {
                "queue": str(queue_path),
                "closed_streams": str(closed_streams),
                "opened_batch": str(opened_batch or "none"),
                "synced_queue_items": str(synced_queue_items),
                "decoupled_batches": str(decoupled_counts["decoupled_total"]),
                "decoupled_total": str(decoupled_counts["decoupled_total"]),
                "decoupled_closed": str(decoupled_counts["decoupled_closed"]),
                "decoupled_open": str(decoupled_counts["decoupled_open"]),
                "waiting_dep_reclassified": str(decoupled_counts["waiting_dep_reclassified"]),
            },
        )

    recompute_states(board)
    if created_streams > 0 or created_tasks > 0:
        append_event(
            board,
            "sync_priority_queue",
            {
                "queue": str(queue_path),
                "created_streams": created_streams,
                "created_tasks": created_tasks,
            },
        )
    return created_streams, created_tasks


def reconcile_state(board: dict, queue_path: Path) -> Dict[str, int]:
    """Non-destructive queue/workboard state reconciliation.

    - use workboard runtime truth (tasks/streams) to refresh queue state
    - update only non-closed queue entries
    - do not modify dependency wiring
    """
    if not queue_path.exists():
        raise SystemExit(f"QUEUE_MISSING: {queue_path}")
    try:
        queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"QUEUE_READ_ERROR: {queue_path}: {exc}") from exc
    if not isinstance(queue_obj, dict):
        raise SystemExit(f"QUEUE_SCHEMA_ERROR: {queue_path} root must be object")

    items = queue_obj.get("items", [])
    if not isinstance(items, list):
        queue_obj["items"] = []
        items = []

    recompute_states(board)

    stream_states_from_wb: Dict[str, str] = {}
    task_stream_states: Dict[str, set[str]] = {}
    for task in board.get("tasks", []):
        if not isinstance(task, dict):
            continue
        stream_id = str(task.get("stream_id", "")).strip().upper()
        if not stream_id:
            continue
        task_stream_states.setdefault(stream_id, set()).add(_normalize_state_token(task.get("state", "")))
    for stream_id, states in task_stream_states.items():
        stream_states_from_wb[stream_id] = _derive_stream_state_from_task_states(states)

    for stream in board.get("streams", []):
        if not isinstance(stream, dict):
            continue
        stream_id = str(stream.get("id", "")).strip().upper()
        if not stream_id or stream_id in stream_states_from_wb:
            continue
        stream_states_from_wb[stream_id] = _normalize_state_token(stream.get("state", ""))

    queue_synced = 0
    waiting_dep_reclassified = 0
    queue_changed = False
    now = now_iso()
    closed_states = {"CLOSED", "DONE", "PASS"}

    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip().upper()
        if not item_id:
            continue
        q_state = _queue_item_state(item)
        if q_state in closed_states:
            continue
        wb_state = stream_states_from_wb.get(item_id, "")
        if not wb_state:
            continue

        desired_state = None
        if wb_state in {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "WAITING_DEP", "PLANNED", "REVIEW"}:
            desired_state = _normalize_state_token(wb_state)
        elif wb_state in {"DONE", "CLOSED"}:
            desired_state = "CLOSED"

        if not desired_state or desired_state == q_state:
            continue

        if q_state == "WAITING_DEP" and desired_state in {"READY", "READY_PLANNER", "READY_DEV", "IN_PROGRESS", "PLANNED"}:
            waiting_dep_reclassified += 1

        item["state"] = desired_state
        item["updated_at"] = now
        if desired_state in {"READY", "READY_PLANNER", "READY_DEV"}:
            item["dispatch_authorized"] = True
            item.setdefault("ready_at", now)
        if desired_state == "CLOSED":
            item.setdefault("closed_at", now)
        queue_synced += 1
        queue_changed = True

    if queue_changed:
        queue_obj["updated_at"] = now
        queue_path.write_text(json.dumps(queue_obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    append_event(
        board,
        "reconcile_state",
        {
            "queue": str(queue_path),
            "queue_synced": str(queue_synced),
            "waiting_dep_reclassified": str(waiting_dep_reclassified),
            "non_destructive": "1",
        },
    )
    return {
        "queue_synced": queue_synced,
        "waiting_dep_reclassified": waiting_dep_reclassified,
    }


def sanitize_queue_dependencies(queue_path: Path, all_batches: bool = True) -> Dict[str, int]:
    if not queue_path.exists():
        raise SystemExit(f"QUEUE_MISSING: {queue_path}")
    try:
        queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"QUEUE_READ_ERROR: {queue_path}: {exc}") from exc
    if not isinstance(queue_obj, dict):
        raise SystemExit(f"QUEUE_SCHEMA_ERROR: {queue_path} root must be object")

    counters = _decouple_inter_batch_dependencies(queue_obj, all_batches=all_batches)
    remaining = _count_queue_inter_batch_dependencies(queue_obj)
    if remaining > 0:
        raise SystemExit(
            "QUEUE_DEP_POLICY_VIOLATION: "
            f"inter_batch_dependencies_remaining={remaining} queue={queue_path}"
        )

    if counters["decoupled_total"] or counters["waiting_dep_reclassified"]:
        queue_obj.setdefault("updated_at", now_iso())
        queue_path.write_text(json.dumps(queue_obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return counters


def _parse_iso_epoch(raw: str) -> float | None:
    token = str(raw or "").strip()
    if not token:
        return None
    try:
        return datetime.fromisoformat(token.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _next_batch_id(queue_obj: dict, board: dict) -> str:
    max_seen = 0
    pattern = re.compile(r"^BATCH-(\d+)$")
    for item in queue_obj.get("items", []):
        if not isinstance(item, dict):
            continue
        match = pattern.match(str(item.get("id", "")).strip().upper())
        if not match:
            continue
        max_seen = max(max_seen, int(match.group(1)))
    for stream in board.get("streams", []):
        if not isinstance(stream, dict):
            continue
        match = pattern.match(str(stream.get("id", "")).strip().upper())
        if not match:
            continue
        max_seen = max(max_seen, int(match.group(1)))
    return f"BATCH-{max_seen + 1:02d}"


def _autobatch_seed(workspace_root: Path) -> Tuple[str, str]:
    candidates = [
        workspace_root / "docs/product/planning/PRODUCT_VISION.md",
        workspace_root / "docs/product/planning/WORKSTATE.md",
        workspace_root / "docs/planning/WORKSTATE.md",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        heading = ""
        for idx, raw in enumerate(lines, start=1):
            line = str(raw or "").strip()
            if not line:
                continue
            if line.startswith("#"):
                heading = line.lstrip("#").strip()[:96]
                continue
            # Skip markdown emphasis/italic lines (e.g. _Document de référence...)
            # and separator lines — these are metadata, not batch titles
            if line.startswith("_") or line.startswith(">") or line.startswith("-") or line.startswith("|"):
                continue
            if line.startswith("---") or line.startswith("==="):
                continue
            if len(line) < 12:
                continue
            title = line[:96]
            rel = path.relative_to(workspace_root).as_posix()
            if heading:
                return title, f"{rel}#{heading}"
            return title, f"{rel}:L{idx}"

        if heading:
            rel = path.relative_to(workspace_root).as_posix()
            return heading, f"{rel}#{heading}"

    return "Planner Autonomy Batch", "none"


def planner_autobatch(
    board: dict,
    queue_path: Path,
    *,
    reason: str,
    cooldown_s: int,
    source: str,
    workspace_root: Path,
) -> Dict[str, str]:
    now = now_iso()
    now_epoch = datetime.now(timezone.utc).timestamp()

    planner_tasks = [
        task
        for task in board.get("tasks", [])
        if _canonical_role(str(task.get("role", ""))) == "planner"
    ]
    planner_actionable = [
        task
        for task in planner_tasks
        if str(task.get("state", "")).upper() in {STATE_READY, STATE_READY_DEV, STATE_IN_PROGRESS, STATE_REVIEW}
    ]
    if planner_actionable:
        return {
            "status": "skip",
            "reason": "planner_work_exists",
            "batch_id": "none",
            "stream_created": "0",
            "task_created": "0",
            "cooldown_applied": "0",
        }

    last_created_epoch = None
    for event in reversed(board.get("events", [])):
        if not isinstance(event, dict):
            continue
        if str(event.get("kind", "")).strip() != "planner_autobatch_created":
            continue
        last_created_epoch = _parse_iso_epoch(str(event.get("at", "")))
        if last_created_epoch is not None:
            break
    if cooldown_s > 0 and last_created_epoch is not None and (now_epoch - last_created_epoch) < cooldown_s:
        return {
            "status": "skip",
            "reason": "cooldown",
            "batch_id": "none",
            "stream_created": "0",
            "task_created": "0",
            "cooldown_applied": "1",
        }

    queue_obj: dict
    if queue_path.exists():
        try:
            queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemExit(f"QUEUE_READ_ERROR: {queue_path}: {exc}") from exc
        if not isinstance(queue_obj, dict):
            raise SystemExit(f"QUEUE_SCHEMA_ERROR: {queue_path} root must be object")
    else:
        queue_obj = {"version": 1, "updated_at": now_iso(), "items": [], "meta": {}}

    batch_id = _next_batch_id(queue_obj, board)
    title, vision_ref = _autobatch_seed(workspace_root)

    # DUPLICATE_TITLE_GUARD: prevent creating the same-titled batch repeatedly.
    # If an identical title already exists in any non-CLOSED batch, skip creation.
    existing_titles = {
        str(i.get("title", "")).strip().lower()
        for i in queue_obj.get("items", [])
        if str(i.get("state", "")).upper() not in {"CLOSED", "DONE", "PASS"}
    }
    if title.strip().lower() in existing_titles:
        return {
            "status": "skip",
            "reason": "duplicate_title",
            "batch_id": "none",
            "stream_created": "0",
            "task_created": "0",
            "cooldown_applied": "0",
        }

    queue_obj.setdefault("items", [])
    queue_obj["items"].append(
        {
            "id": batch_id,
            "title": title,
            "state": "READY",
            "priority": "P2",
            "owner_role": "planner",
            "created_by": "planner_autonomy",
            "vision_ref": vision_ref,
            "next_action": f"ouvrir {batch_id}-PLAN",
            "depends_on": [],
            "dependency_policy": "single_batch",
            "created_at": now,
            "updated_at": now,
        }
    )
    queue_obj["updated_at"] = now
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(queue_obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    stream_created = 0
    if batch_id not in stream_index(board):
        board.setdefault("streams", []).append(
            {
                "id": batch_id,
                "title": title,
                "priority": "P2",
                "source_state": STATE_READY,
                "state": STATE_READY,
                "created_at": now,
                "updated_at": now,
            }
        )
        stream_created = 1

    task_created = 0
    task_id_value = f"{batch_id}-ANALYSIS"
    existing_task = task_index(board).get(task_id_value)
    if existing_task is None:
        board.setdefault("tasks", []).append(
            {
                "id": task_id_value,
                "stream_id": batch_id,
                "code": "ANALYSIS",
                "title": f"{title} [ANALYSIS]",
                "role": "planner",
                "state": STATE_READY,
                "priority": "P2",
                "depends_on": [],
                "assignee": "",
                "blocked_reason": "",
                "artifacts": [],
                "notes": [
                    "AUTOBATCH-NOTE: generated by planner-autobatch to keep planner lane non-passive."
                ],
                "handoff_to": "",
                "created_at": now,
                "updated_at": now,
                "started_at": "",
                "completed_at": "",
            }
        )
        task_created = 1
    else:
        existing_task["state"] = STATE_READY
        existing_task["depends_on"] = []
        existing_task["updated_at"] = now

    append_event(
        board,
        "planner_autobatch_created",
        {
            "batch_id": batch_id,
            "reason": reason or "idle_no_ready",
            "cooldown_s": str(max(0, cooldown_s)),
            "source": source or "planner_autobatch_cli",
            "vision_ref": vision_ref,
            "stream_created": str(stream_created),
            "task_created": str(task_created),
        },
    )
    recompute_states(board)
    return {
        "status": "ok",
        "reason": "created",
        "batch_id": batch_id,
        "stream_created": str(stream_created),
        "task_created": str(task_created),
        "vision_ref": vision_ref,
        "cooldown_applied": "1" if cooldown_s > 0 else "0",
    }


def iter_tasks_for_role(board: dict, role: str) -> Iterable[dict]:
    role_canonical = _canonical_role(role)
    if not role_canonical:
        return iter(())
    return (
        task
        for task in board.get("tasks", [])
        if _canonical_role(str(task.get("role", ""))) == role_canonical
    )


def dev_ready_tasks(board: dict) -> List[dict]:
    ready_states = {STATE_READY, STATE_READY_DEV, STATE_IN_PROGRESS, STATE_REVIEW}
    out: List[dict] = []
    for task in iter_tasks_for_role(board, "dev"):
        if str(task.get("state", "")).strip().upper() not in ready_states:
            continue
        task_id_value = str(task.get("id", "")).strip()
        stream_id_value = str(task.get("stream_id", "")).strip()
        if not task_id_value or not stream_id_value:
            continue
        out.append(task)
    out.sort(key=lambda t: (priority_rank(str(t.get("priority", "P9"))), str(t.get("id", ""))))
    return out


def role_wip_count(board: dict, role: str) -> int:
    return sum(1 for task in iter_tasks_for_role(board, role) if str(task.get("state", "")) in ACTIVE_STATES)


def claim_task(
    board: dict,
    role: str,
    task_id_override: str | None = None,
    change_plan: str = "",
    architecture_checks: str = "",
) -> dict:
    # WIP GUARD: Prevent workboard explosion.
    # If active tasks (READY+IN_PROGRESS) exceed 60, block claim and alert.
    _wip_limit = 60
    _active_count = sum(
        1 for t in board.get("tasks", [])
        if str(t.get("state", "")) in (STATE_READY, STATE_READY_DEV, STATE_IN_PROGRESS)
    )
    if _active_count > _wip_limit:
        raise RuntimeError(
            f"WIP limit exceeded: {_active_count} active tasks > {_wip_limit} allowed. "
            f"Complete or archive tasks before claiming new ones. "
            f"Run: python3 scripts/parallel_workstream.py list --state READY,IN_PROGRESS"
        )
    # Keep claim behavior consistent with status/context outputs.
    recompute_states(board)
    tasks = list(iter_tasks_for_role(board, role))
    candidates = [
        task
        for task in tasks
        if str(task.get("state", "")).strip().upper() in {STATE_READY, STATE_READY_DEV, "READY"}
    ]
    candidates.sort(key=lambda t: (priority_rank(str(t.get("priority", "P9"))), str(t.get("stream_id", "")), str(t.get("code", ""))))

    if task_id_override:
        match = next((task for task in candidates if str(task.get("id", "")) == task_id_override), None)
        if match is None:
            raise SystemExit(f"CLAIM_ERROR: task {task_id_override} not READY for role {role}")
        chosen = match
    else:
        if not candidates:
            raise SystemExit(f"NO_READY_TASK: role={role}")
        chosen = candidates[0]

    role_conf = board.get("roles", {}).get(role, {})
    wip_limit = int(role_conf.get("wip_limit", 2))
    if role_wip_count(board, role) >= wip_limit:
        raise SystemExit(f"WIP_LIMIT_REACHED: role={role} limit={wip_limit}")

    # PLAN_SERIAL_GUARD: planner can only have 1 PLAN-type task IN_PROGRESS at a time
    # (PLAN tasks bootstrap a batch chain; running 2 simultaneously causes context scatter)
    if role == "planner":
        active_plans = [
            t for t in iter_tasks_for_role(board, role)
            if str(t.get("state", "")) == STATE_IN_PROGRESS
            and str(t.get("code", "")).upper().startswith("PLAN")
        ]
        chosen_is_plan = str(chosen.get("code", "")).upper().startswith("PLAN")
        if chosen_is_plan and active_plans:
            raise SystemExit(
                f"PLAN_SERIAL_VIOLATION: planner already has IN_PROGRESS PLAN task "
                f"{active_plans[0].get('id')}. Complete it before claiming {chosen.get('id')}."
            )

    if _requires_prechange_gate(role):
        if not change_plan or not architecture_checks:
            raise SystemExit(
                "PRECHANGE_PLAN_INVALID: "
                f"role={role} requires claim with --change-plan and --architecture-checks before task change"
            )
        validated_plan_items, validated_arch_items, validated_reflection = _validate_prechange_checks(
            change_plan,
            architecture_checks,
            role,
            strict_reflection=True,
        )
        chosen["prechange_plan_items"] = validated_plan_items
        chosen["prechange_architecture_checks"] = validated_arch_items
        chosen["prechange_reflection_dimensions"] = validated_reflection
        chosen["prechange_gate_version"] = PRECHANGE_GATE_VERSION

    chosen["state"] = STATE_IN_PROGRESS
    chosen["assignee"] = role
    chosen["started_at"] = chosen.get("started_at") or now_iso()
    chosen["updated_at"] = now_iso()
    append_event(
        board,
        "claim",
        {
            "role": role,
            "task_id": chosen.get("id"),
            "prechange_plan_count": str(len(chosen.get("prechange_plan_items", []))),
            "prechange_arch_count": str(len(chosen.get("prechange_architecture_checks", []))),
            "prechange_reflection_count": str(len(chosen.get("prechange_reflection_dimensions", []))),
            "prechange_gate_version": str(chosen.get("prechange_gate_version", 1)),
        },
    )
    recompute_states(board)
    return chosen


def complete_task(
    board: dict,
    role: str,
    task_id_value: str,
    artifact: str,
    note: str,
    handoff_to: str,
    proof_root: Path,
    cmd: str,
    tests_run: str,
    review_ref: str,
    reviewer_role: str,
    review_verdict: str,
    change_plan: str = "",
    architecture_checks: str = "",
    idempotency_key: str = "",
) -> dict:
    tasks = task_index(board)
    task = tasks.get(task_id_value)
    if task is None:
        raise SystemExit(f"COMPLETE_ERROR: task_not_found={task_id_value}")
    task_role = _canonical_role(str(task.get("role", "")))
    if task_role != role:
        raise SystemExit(f"COMPLETE_ERROR: role_mismatch task_role={task_role} caller_role={role}")

    if str(task.get("state", "")) not in {STATE_IN_PROGRESS, STATE_READY, STATE_READY_DEV, STATE_REVIEW}:
        raise SystemExit(f"COMPLETE_ERROR: invalid_state={task.get('state')} task={task_id_value}")

    deps = [dep for dep in task.get("depends_on", []) if dep]
    not_done = [dep for dep in deps if str(tasks.get(dep, {}).get("state", "")) != STATE_DONE]
    if not_done:
        raise SystemExit(f"COMPLETE_ERROR: deps_not_done={','.join(not_done)} task={task_id_value}")

    prechange_plan_items: List[str] = _coerce_reasoning_from_value(task.get("prechange_plan_items"))
    prechange_architecture_checks: List[str] = _coerce_reasoning_from_value(task.get("prechange_architecture_checks"))
    prechange_reflection_dimensions: List[str] = _coerce_reasoning_from_value(task.get("prechange_reflection_dimensions"))
    prechange_gate_version = int(task.get("prechange_gate_version", 1) or 1)
    if _requires_prechange_gate(role):
        strict_reflection = False
        if change_plan or architecture_checks:
            strict_reflection = True
            prechange_plan_items, prechange_architecture_checks, prechange_reflection_dimensions = _validate_prechange_checks(
                change_plan,
                architecture_checks,
                role,
                strict_reflection=strict_reflection,
            )
        else:
            if not prechange_plan_items or not prechange_architecture_checks:
                raise SystemExit(
                    "PRECHANGE_PLAN_INVALID: "
                    f"role={role} requires pre-change plan + architecture checks before task change "
                    " (pass via claim --change-plan --architecture-checks or complete overrides)."
                )
            strict_reflection = prechange_gate_version >= PRECHANGE_GATE_VERSION
            prechange_plan_items, prechange_architecture_checks, prechange_reflection_dimensions = _validate_prechange_checks(
                "\n".join(prechange_plan_items),
                "\n".join(prechange_architecture_checks),
                role,
                strict_reflection=strict_reflection,
            )

        task["prechange_plan_items"] = prechange_plan_items
        task["prechange_architecture_checks"] = prechange_architecture_checks
        task["prechange_reflection_dimensions"] = prechange_reflection_dimensions
        task["prechange_gate_version"] = PRECHANGE_GATE_VERSION if strict_reflection else max(1, prechange_gate_version)
        prechange_gate_version = int(task.get("prechange_gate_version", 1) or 1)

    effective_idempotency = (idempotency_key or "").strip() or _auto_idempotency_key(role, task_id_value, handoff_to)
    task["last_idempotency_key"] = effective_idempotency

    task["state"] = STATE_DONE
    task["completed_at"] = now_iso()
    task["updated_at"] = now_iso()
    task["blocked_reason"] = ""
    if artifact:
        task.setdefault("artifacts", []).append(artifact)
    if note:
        task.setdefault("notes", []).append(note)

    handoff_id = ""
    if handoff_to:
        handoff_id = f"HO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}"
        board.setdefault("handoffs", []).append(
            {
                "id": handoff_id,
                "task_id": task_id_value,
                "stream_id": task.get("stream_id"),
                "from_role": role,
                "to_role": handoff_to,
                "status": "OPEN",
                "note": note,
                "idempotency_key": effective_idempotency,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        )
        task["handoff_to"] = handoff_to

    manifest_path = _write_proof_manifest(
        proof_root=proof_root,
        task=task,
        role=role,
        artifact=artifact,
        note=note,
        handoff_to=handoff_to,
        handoff_id=handoff_id,
        cmd=cmd,
        tests_run=tests_run,
        review_ref=review_ref,
        reviewer_role=reviewer_role,
        review_verdict=review_verdict,
        prechange_plan_items=prechange_plan_items,
        prechange_architecture_checks=prechange_architecture_checks,
        prechange_reflection_dimensions=prechange_reflection_dimensions,
        prechange_gate_version=prechange_gate_version,
        idempotency_key=effective_idempotency,
    )
    task.setdefault("proof_manifests", []).append(manifest_path)
    note_kv = (
        f"cmd={(cmd or '').strip() or 'SKIP(no_cmd_recorded)'};"
        f"tests_run={(tests_run or '').strip() or 'SKIP(no_tests_recorded)'};"
        f"prechange_plan_count={len(prechange_plan_items)};"
        f"prechange_arch_count={len(prechange_architecture_checks)};"
        f"prechange_reflection_count={len(prechange_reflection_dimensions)};"
        f"prechange_gate_version={prechange_gate_version};"
        f"review_ref={(review_ref or '').strip() or 'none'};"
        f"review_verdict={_normalize_verdict(review_verdict)};"
        f"proof_manifest={manifest_path}"
    )
    task.setdefault("notes", []).append(note_kv)

    append_event(
        board,
        "complete",
        {
            "role": role,
            "task_id": task_id_value,
            "artifact": artifact,
            "handoff_to": handoff_to or "none",
            "handoff_id": handoff_id or "none",
            "proof_manifest": manifest_path,
            "idempotency_key": effective_idempotency,
            "prechange_plan_count": str(len(prechange_plan_items)),
            "prechange_arch_count": str(len(prechange_architecture_checks)),
            "prechange_reflection_count": str(len(prechange_reflection_dimensions)),
            "prechange_gate_version": str(prechange_gate_version),
        },
    )
    recompute_states(board)
    return task


def set_block_state(board: dict, task_id_value: str, reason: str, blocked: bool) -> dict:
    tasks = task_index(board)
    task = tasks.get(task_id_value)
    if task is None:
        raise SystemExit(f"TASK_NOT_FOUND: {task_id_value}")
    if blocked:
        task["state"] = STATE_BLOCKED
        task["blocked_reason"] = reason or "blocked_without_reason"
    else:
        if str(task.get("state", "")) == STATE_BLOCKED:
            task["state"] = STATE_WAITING_DEP
        task["blocked_reason"] = ""
    task["updated_at"] = now_iso()
    append_event(board, "block" if blocked else "unblock", {"task_id": task_id_value, "reason": reason})
    recompute_states(board)
    return task


def handoff_update(board: dict, handoff_id: str, status: str, actor_role: str) -> dict:
    handoffs = [h for h in board.get("handoffs", []) if str(h.get("id", "")) == handoff_id]
    if not handoffs:
        raise SystemExit(f"HANDOFF_NOT_FOUND: {handoff_id}")
    handoff = handoffs[0]
    to_role = _canonical_role(str(handoff.get("to_role", "")))
    actor_role_canonical = _canonical_role(actor_role)
    if status == "ACK" and actor_role_canonical and actor_role_canonical != to_role:
        raise SystemExit(f"HANDOFF_ACK_ROLE_MISMATCH: expected={to_role} got={actor_role}")
    handoff["status"] = status
    handoff["updated_at"] = now_iso()
    append_event(board, "handoff_update", {"handoff_id": handoff_id, "status": status, "actor": actor_role_canonical or actor_role})
    return handoff


def enforce_handoff_sla(board: dict, ack_sla_seconds: int, close_sla_seconds: int, apply: bool) -> dict:
    now = datetime.now(timezone.utc)
    tasks = task_index(board)
    summary = {
        "open_total": 0,
        "ack_total": 0,
        "ack_overdue": 0,
        "close_overdue": 0,
        "escalated": 0,
        "blocked_tasks": 0,
    }

    for handoff in board.get("handoffs", []):
        status = str(handoff.get("status", "")).upper()
        if status not in {"OPEN", "ACK"}:
            continue
        created = _parse_utc(str(handoff.get("created_at", ""))) or _parse_utc(str(handoff.get("updated_at", "")))
        if created is None:
            continue
        age_seconds = int((now - created).total_seconds())
        hid = str(handoff.get("id", ""))
        task_ref = str(handoff.get("task_id", ""))

        if status == "OPEN":
            summary["open_total"] += 1
            if age_seconds > ack_sla_seconds:
                summary["ack_overdue"] += 1
                if apply:
                    handoff["sla_state"] = "ACK_OVERDUE"
                    handoff["owner"] = "planner"
                    handoff["updated_at"] = now_iso()
                    append_event(
                        board,
                        "handoff_sla_escalation",
                        {"handoff_id": hid, "severity": "WARN", "reason": "ACK_OVERDUE", "owner": "planner"},
                    )
                    summary["escalated"] += 1
            if age_seconds > close_sla_seconds:
                summary["close_overdue"] += 1
                if apply:
                    handoff["sla_state"] = "CLOSE_OVERDUE"
                    handoff["owner"] = "planner"
                    handoff["updated_at"] = now_iso()
                    append_event(
                        board,
                        "handoff_sla_escalation",
                        {"handoff_id": hid, "severity": "BLOCKED", "reason": "CLOSE_OVERDUE", "owner": "planner"},
                    )
                    summary["escalated"] += 1
                    task = tasks.get(task_ref)
                    if task is not None and str(task.get("state", "")) in {STATE_READY, STATE_READY_DEV, STATE_IN_PROGRESS, STATE_REVIEW}:
                        task["state"] = STATE_BLOCKED
                        task["blocked_reason"] = f"handoff_close_sla_exceeded:{hid}"
                        task["updated_at"] = now_iso()
                        summary["blocked_tasks"] += 1
        elif status == "ACK":
            summary["ack_total"] += 1
            ack_at = _parse_utc(str(handoff.get("updated_at", ""))) or created
            ack_age = int((now - ack_at).total_seconds())
            if ack_age > close_sla_seconds:
                summary["close_overdue"] += 1
                if apply:
                    handoff["sla_state"] = "CLOSE_OVERDUE_AFTER_ACK"
                    handoff["owner"] = "planner"
                    handoff["updated_at"] = now_iso()
                    append_event(
                        board,
                        "handoff_sla_escalation",
                        {"handoff_id": hid, "severity": "BLOCKED", "reason": "CLOSE_OVERDUE_AFTER_ACK", "owner": "planner"},
                    )
                    summary["escalated"] += 1
    if apply:
        recompute_states(board)
    return summary


def _parse_utc(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _queue_ready_count(queue_path: Path) -> int:
    if not queue_path.exists():
        return 0
    try:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    return sum(1 for item in payload.get("items", []) if str(item.get("state", "")).upper() in {STATE_READY, STATE_READY_DEV, "READY"})


def _queue_state_map(queue_path: Path) -> Dict[str, str]:
    if not queue_path.exists():
        return {}
    try:
        payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    states: Dict[str, str] = {}
    for item in payload.get("items", []):
        sid = str(item.get("id", "")).strip().upper()
        if not sid:
            continue
        states[sid] = str(item.get("state", "")).strip().upper()
    return states


def _artifact_ref_exists(raw: str) -> bool:
    value = (raw or "").strip()
    if not value:
        return False
    lower = value.lower()
    if lower.startswith(("http://", "https://", "proof:", "inline:")):
        return True
    path = Path(value).expanduser()
    return path.exists()


def _manifest_required_keys_present(text: str) -> List[str]:
    required = [
        "proof_id:",
        "stream_id:",
        "task_id:",
        "role:",
        "produced_at_utc:",
        "execution:",
        "outputs:",
        "signoff:",
    ]
    upper = text.upper()
    missing = []
    for key in required:
        if key.upper() not in upper:
            missing.append(key.rstrip(":"))
    return missing


def _validate_manifest_file(manifest_path: Path) -> List[str]:
    issues: List[str] = []
    if not manifest_path.exists():
        issues.append(f"MANIFEST_NOT_FOUND:{manifest_path}")
        return issues
    try:
        text = manifest_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        issues.append(f"MANIFEST_READ_ERROR:{manifest_path}:{exc}")
        return issues
    missing = _manifest_required_keys_present(text)
    if missing:
        issues.append(f"MANIFEST_MISSING_KEYS:{manifest_path}:{','.join(missing)}")
    verdict_match = "QA_VERDICT:" in text.upper()
    if not verdict_match:
        issues.append(f"MANIFEST_MISSING_QA_VERDICT:{manifest_path}")
    return issues


def validate_board(
    board: dict,
    queue_path: Path,
    ack_sla_seconds: int,
    close_sla_seconds: int,
    proof_root: Path,
    require_proof_manifest: bool,
    in_progress_stale_seconds: int,
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    tasks = board.get("tasks", [])
    seen = set()
    idx = task_index(board)
    done_roles_need_test_evidence = {
        "dev",
        "backend_engineer",
        "frontend_engineer",
        "integrator",
        "data_analyst",
        "infra_engineer",
        "tester",
        "qa",
    }

    for task in tasks:
        tid = str(task.get("id", ""))
        if not tid:
            errors.append("TASK_WITHOUT_ID")
            continue
        if tid in seen:
            errors.append(f"DUPLICATE_TASK_ID:{tid}")
        seen.add(tid)
        role_raw = str(task.get("role", ""))
        role = _canonical_role(role_raw)
        if role not in ROLE_CATALOG:
            errors.append(f"UNKNOWN_ROLE:{tid}:{role_raw}")
        for dep in task.get("depends_on", []):
            if dep not in idx:
                errors.append(f"MISSING_DEP:{tid}:{dep}")
        state = str(task.get("state", ""))
        if state in {STATE_READY, STATE_READY_DEV}:
            deps = task.get("depends_on", [])
            not_done = [dep for dep in deps if idx.get(dep, {}).get("state") != STATE_DONE]
            if not_done:
                errors.append(f"READY_WITH_OPEN_DEPS:{tid}:{','.join(not_done)}")
        if state == STATE_DONE:
            artifacts = [str(a).strip() for a in task.get("artifacts", []) if str(a).strip()]
            if not artifacts:
                errors.append(f"INV-DONE-PROOF:NO_ARTIFACT:task={tid}:owner=qa:remediation=done_to_review")
            else:
                existing = [a for a in artifacts if _artifact_ref_exists(a)]
                if not existing:
                    refs = ",".join(artifacts[:3])
                    errors.append(f"INV-DONE-PROOF:ARTIFACT_NOT_FOUND:task={tid}:refs={refs}:owner=qa:remediation=fix_artifact_ref")
            if role in done_roles_need_test_evidence:
                notes_blob = " ".join(str(n) for n in task.get("notes", [])).upper()
                if "CMD=" not in notes_blob and "TESTS_RUN=" not in notes_blob and "SKIP(" not in notes_blob:
                    warnings.append(
                        f"INV-DONE-PROOF-WARN:MISSING_CMD_TEST_EVIDENCE:task={tid}:owner=qa:remediation=add_cmd_tests_or_skip_reason"
                    )
            manifests = [str(p).strip() for p in task.get("proof_manifests", []) if str(p).strip()]
            if not manifests:
                msg = f"INV-DONE-PROOF-MANIFEST:task={tid}:owner=qa:remediation=attach_proof_manifest"
                if require_proof_manifest:
                    errors.append(msg)
                else:
                    warnings.append(msg)
            else:
                for manifest_raw in manifests:
                    manifest_path = Path(manifest_raw)
                    if not manifest_path.is_absolute():
                        candidate = (Path(".") / manifest_path).resolve()
                        if candidate.exists():
                            manifest_path = candidate
                        else:
                            manifest_path = (proof_root / manifest_path.name).resolve()
                    for issue in _validate_manifest_file(manifest_path):
                        if "MISSING_KEYS" in issue or "MISSING_QA_VERDICT" in issue:
                            errors.append(f"INV-DONE-PROOF:{tid}:{issue}")
                        else:
                            warnings.append(f"INV-DONE-PROOF-WARN:{tid}:{issue}")

    # INV-CROSS-DEP (ERROR): single-batch autonomy policy.
    cross_task_dep_count = _count_cross_stream_task_dependencies(board)
    if cross_task_dep_count > 0:
        errors.append(
            f"INV-CROSS-DEP-TASK:count={cross_task_dep_count}:owner=planner:remediation=sanitize-dependencies_and_sync-priority"
        )
    queue_inter_batch_dep_count = _queue_inter_batch_dep_count(queue_path)
    if queue_inter_batch_dep_count > 0:
        errors.append(
            f"INV-CROSS-DEP-QUEUE:count={queue_inter_batch_dep_count}:owner=planner:remediation=sanitize-dependencies"
        )

    # INV-READY-SYNC (WARN): queue/workboard drift signal.
    queue_states = _queue_state_map(queue_path)
    ready_tasks = []
    for task in tasks:
        if str(task.get("state", "")) not in {STATE_READY, STATE_READY_DEV}:
            continue
        stream_id = str(task.get("stream_id", "")).strip().upper()
        # Ignore READY tasks belonging to streams already marked PASS in the queue.
        if stream_id and queue_states.get(stream_id, "") == "PASS":
            continue
        ready_tasks.append(str(task.get("id", "")))
    queue_ready = _queue_ready_count(queue_path)
    if queue_ready == 0 and ready_tasks:
        sample = ",".join([tid for tid in ready_tasks if tid][:5]) or "none"
        warnings.append(
            f"INV-READY-SYNC:owner=planner:queue_ready=0:board_ready={len(ready_tasks)}:sample={sample}:remediation=sync-priority"
        )

    # INV-QUEUE-CLOSED-WITH-OPEN-TASKS (WARN): stream marked PASS/CLOSED in queue while actionable tasks remain.
    actionable_states = {STATE_READY, STATE_READY_DEV, STATE_IN_PROGRESS, STATE_REVIEW, STATE_BLOCKED}
    stream_open_tasks: Dict[str, List[str]] = {}
    for task in tasks:
        state = str(task.get("state", ""))
        if state not in actionable_states:
            continue
        stream_id = str(task.get("stream_id", "")).strip().upper()
        if not stream_id:
            continue
        stream_open_tasks.setdefault(stream_id, []).append(str(task.get("id", "")))

    for stream_id, task_ids in sorted(stream_open_tasks.items()):
        queue_state = queue_states.get(stream_id, "")
        if queue_state not in {"PASS", "CLOSED"}:
            continue
        sample = ",".join([tid for tid in task_ids if tid][:5]) or "none"
        warnings.append(
            "INV-QUEUE-CLOSED-WITH-OPEN-TASKS:"
            f"stream={stream_id}:queue_state={queue_state}:open_tasks={len(task_ids)}:sample={sample}:"
            "owner=planner:remediation=reopen_queue_or_close_workboard_tasks"
        )

    now = datetime.now(timezone.utc)
    for handoff in board.get("handoffs", []):
        task_ref = str(handoff.get("task_id", ""))
        hid = str(handoff.get("id", ""))
        if task_ref and task_ref not in idx:
            errors.append(f"HANDOFF_TASK_MISSING:{hid}:{task_ref}")
        if not str(handoff.get("idempotency_key", "")).strip():
            warnings.append(f"HANDOFF_IDEMPOTENCY_MISSING:handoff={hid}:owner=planner:remediation=attach_idempotency_key")
        status = str(handoff.get("status", "")).upper()
        created_at = _parse_utc(str(handoff.get("created_at", ""))) or _parse_utc(str(handoff.get("updated_at", "")))
        if created_at is None:
            if status in {"OPEN", "ACK"}:
                warnings.append(f"INV-HANDOFF-SLA:INVALID_TIMESTAMP:handoff={hid}:owner=planner:remediation=repair_timestamps")
            continue
        age_seconds = int((now - created_at).total_seconds())
        if status == "OPEN":
            if age_seconds > close_sla_seconds:
                errors.append(
                    f"INV-HANDOFF-SLA:CLOSE_OVERDUE:handoff={hid}:age={age_seconds}s:owner=planner:remediation=escalate_and_reduce_wip"
                )
            elif age_seconds > ack_sla_seconds:
                warnings.append(
                    f"INV-HANDOFF-SLA:ACK_OVERDUE:handoff={hid}:age={age_seconds}s:owner=planner:remediation=handoff-ack_or_reassign"
                )
        elif status == "ACK":
            ack_at = _parse_utc(str(handoff.get("updated_at", ""))) or created_at
            ack_age = int((now - ack_at).total_seconds())
            if ack_age > close_sla_seconds:
                warnings.append(
                    f"INV-HANDOFF-SLA:CLOSE_OVERDUE_AFTER_ACK:handoff={hid}:age={ack_age}s:owner=planner:remediation=handoff-close_or_reassign"
                )

    for task in tasks:
        if str(task.get("state", "")) != STATE_IN_PROGRESS:
            continue
        tid = str(task.get("id", ""))
        ref_time = _parse_utc(str(task.get("updated_at", ""))) or _parse_utc(str(task.get("started_at", "")))
        if ref_time is None:
            continue
        age_seconds = int((now - ref_time).total_seconds())
        if age_seconds > in_progress_stale_seconds:
            warnings.append(
                f"INV-INPROGRESS-STALE:task={tid}:age={age_seconds}s:owner=planner:remediation=reclaim_or_close"
            )

    return errors, warnings


def print_status(board: dict, role: str, compact: bool, limit: int, dev_ready_mode: bool = False) -> None:
    tasks = board.get("tasks", [])
    if dev_ready_mode:
        ready = dev_ready_tasks(board)
        ids = ",".join(str(t.get("id", "")).strip() for t in ready[: max(1, limit)]) or "none"
        reason = "role_task_present" if ready else "minimal_contract"
        print(f"DEV_READY count={len(ready)} task_ids={ids} reason={reason}")
        return

    summary = {
        "total": len(tasks),
        "ready": sum(1 for t in tasks if t.get("state") in {STATE_READY, STATE_READY_DEV}),
        "ready_planner": sum(1 for t in tasks if t.get("state") == STATE_READY),
        "ready_dev": sum(1 for t in tasks if t.get("state") == STATE_READY_DEV),
        "in_progress": sum(1 for t in tasks if t.get("state") == STATE_IN_PROGRESS),
        "blocked": sum(1 for t in tasks if t.get("state") == STATE_BLOCKED),
        "done": sum(1 for t in tasks if t.get("state") == STATE_DONE),
        "open_handoffs": sum(1 for h in board.get("handoffs", []) if h.get("status") == "OPEN"),
    }

    if compact:
        if role:
            role_canonical = _canonical_role(role)
            if not role_canonical:
                raise SystemExit(f"UNKNOWN_ROLE: {role}")
            r_tasks = list(iter_tasks_for_role(board, role_canonical))
            r_ready = [t for t in r_tasks if t.get("state") in {STATE_READY, STATE_READY_DEV}]
            r_active = [t for t in r_tasks if t.get("state") in ACTIVE_STATES]
            r_blocked = [t for t in r_tasks if t.get("state") == STATE_BLOCKED]
            head = (
                f"ROLE={role_canonical} total={len(r_tasks)} ready={len(r_ready)} in_progress={len(r_active)} "
                f"blocked={len(r_blocked)} open_handoffs={summary['open_handoffs']}"
            )
            lines = [head]
            for task in sorted(r_ready, key=lambda t: (priority_rank(str(t.get("priority", "P9"))), str(t.get("id", ""))))[:limit]:
                lines.append(
                    f"READY task={task.get('id')} prio={task.get('priority')} stream={task.get('stream_id')} deps={len(task.get('depends_on', []))}"
                )
            print("\n".join(lines))
            return

        print(
            f"SUMMARY total={summary['total']} ready={summary['ready']} in_progress={summary['in_progress']} "
            f"blocked={summary['blocked']} done={summary['done']} open_handoffs={summary['open_handoffs']}"
        )
        return

    out = {
        "summary": summary,
        "by_role": {},
        "open_handoffs": [h for h in board.get("handoffs", []) if h.get("status") == "OPEN"],
    }
    canonical_roles = sorted({_canonical_role(role_name) for role_name in ROLE_CATALOG if _canonical_role(role_name)})
    for role_name in canonical_roles:
        role_tasks = list(iter_tasks_for_role(board, role_name))
        out["by_role"][role_name] = {
            "total": len(role_tasks),
            "ready": [t for t in role_tasks if t.get("state") in {STATE_READY, STATE_READY_DEV}][:limit],
            "in_progress": [t for t in role_tasks if t.get("state") in ACTIVE_STATES][:limit],
            "blocked": [t for t in role_tasks if t.get("state") == STATE_BLOCKED][:limit],
        }
    if role:
        role_canonical = _canonical_role(role)
        if not role_canonical:
            raise SystemExit(f"UNKNOWN_ROLE: {role}")
        out = {
            "role": role_canonical,
            "summary": out["by_role"].get(role_canonical, {"total": 0, "ready": [], "in_progress": [], "blocked": []}),
            "open_handoffs": [
                h
                for h in out["open_handoffs"]
                if _canonical_role(str(h.get("to_role", ""))) == role_canonical
                or _canonical_role(str(h.get("from_role", ""))) == role_canonical
            ],
        }
    print(json.dumps(out, ensure_ascii=True, indent=2))


def print_role_context(board: dict, role: str, limit: int) -> None:
    role_canonical = _canonical_role(role)
    if role_canonical not in ROLE_CATALOG:
        raise SystemExit(f"UNKNOWN_ROLE: {role}")
    recompute_states(board)
    role_tasks = list(iter_tasks_for_role(board, role_canonical))
    ready_tasks = sorted(
        [t for t in role_tasks if str(t.get("state", "")) in {STATE_READY, STATE_READY_DEV}],
        key=lambda t: (priority_rank(str(t.get("priority", "P9"))), str(t.get("id", ""))),
    )
    active_tasks = [t for t in role_tasks if str(t.get("state", "")) in ACTIVE_STATES]
    waiting_dep_tasks = [t for t in role_tasks if str(t.get("state", "")) == STATE_WAITING_DEP]
    blocked_tasks = [t for t in role_tasks if str(t.get("state", "")) == STATE_BLOCKED]

    open_handoffs = [h for h in board.get("handoffs", []) if str(h.get("status", "")) == "OPEN"]
    open_to = [h for h in open_handoffs if _canonical_role(str(h.get("to_role", ""))) == role_canonical]
    open_from = [h for h in open_handoffs if _canonical_role(str(h.get("from_role", ""))) == role_canonical]

    recent_peer_events: List[str] = []
    for event in reversed(board.get("events", [])):
        kind = str(event.get("kind", "")).strip()
        if not kind:
            continue
        details = event.get("details", {}) if isinstance(event.get("details", {}), dict) else {}
        actor = _canonical_role(str(details.get("role") or details.get("from_role") or details.get("actor") or "").strip())
        if actor == role_canonical:
            continue
        ref = str(details.get("task_id") or details.get("handoff_id") or details.get("stream_id") or actor or "none").strip()
        recent_peer_events.append(f"{kind}:{ref}")
        if len(recent_peer_events) >= max(1, limit):
            break

    def csv(values: List[str]) -> str:
        cleaned = [v for v in values if v]
        return ",".join(cleaned[: max(1, limit)]) if cleaned else "none"

    next_task = str(ready_tasks[0].get("id", "none")) if ready_tasks else "none"
    ready_ids = [str(t.get("id", "")) for t in ready_tasks]
    active_ids = [str(t.get("id", "")) for t in active_tasks]
    waiting_ids = [str(t.get("id", "")) for t in waiting_dep_tasks]
    blocked_ids = [str(t.get("id", "")) for t in blocked_tasks]
    to_ids = [str(h.get("id", "")) for h in open_to]
    from_ids = [str(h.get("id", "")) for h in open_from]

    print(
        "ROLE_CONTEXT "
        f"role={role_canonical} "
        f"total={len(role_tasks)} "
        f"ready={len(ready_tasks)} "
        f"in_progress={len(active_tasks)} "
        f"waiting_dep={len(waiting_dep_tasks)} "
        f"blocked={len(blocked_tasks)} "
        f"next_task={next_task} "
        f"ready_tasks={csv(ready_ids)} "
        f"in_progress_tasks={csv(active_ids)} "
        f"waiting_dep_tasks={csv(waiting_ids)} "
        f"blocked_tasks={csv(blocked_ids)} "
        f"open_handoffs_to={len(open_to)} "
        f"open_handoffs_from={len(open_from)} "
        f"handoffs_to_ids={csv(to_ids)} "
        f"handoffs_from_ids={csv(from_ids)} "
        f"peer_events={csv(recent_peer_events)}"
    )


def print_publication_channels_context(board: dict, role: str, limit: int) -> None:
    role_canonical = _canonical_role(role)
    if role_canonical not in ROLE_CATALOG:
        raise SystemExit(f"UNKNOWN_ROLE: {role}")
    recompute_states(board)
    idx = task_index(board)

    actionable_states = {STATE_READY, STATE_READY_DEV, STATE_IN_PROGRESS, STATE_REVIEW, STATE_BLOCKED}
    peer_active_states = {STATE_IN_PROGRESS, STATE_REVIEW}

    role_tasks = list(iter_tasks_for_role(board, role_canonical))
    own_actionable = [t for t in role_tasks if str(t.get("state", "")) in actionable_states]
    own_ids = {str(t.get("id", "")) for t in own_actionable}
    own_streams = {str(t.get("stream_id", "")) for t in own_actionable}

    peer_active = [
        t
        for t in board.get("tasks", [])
        if _canonical_role(str(t.get("role", ""))) != role_canonical and str(t.get("state", "")) in peer_active_states
    ]

    shared_stream_impacts: List[str] = []
    for task in peer_active:
        stream_id = str(task.get("stream_id", ""))
        if stream_id and stream_id in own_streams:
            shared_stream_impacts.append(
                f"{task.get('id')}:{task.get('role')}:{task.get('state')}"
            )

    upstream_impacts: List[str] = []
    for task in own_actionable:
        for dep in task.get("depends_on", []):
            dep_task = idx.get(str(dep))
            if dep_task is None:
                continue
            dep_role = str(dep_task.get("role", ""))
            dep_state = str(dep_task.get("state", ""))
            dep_role_canonical = _canonical_role(dep_role)
            if dep_role_canonical == role_canonical or dep_state == STATE_DONE:
                continue
            upstream_impacts.append(f"{dep_task.get('id')}:{dep_role_canonical}:{dep_state}")

    downstream_impacts: List[str] = []
    for task in board.get("tasks", []):
        task_role = _canonical_role(str(task.get("role", "")))
        task_state = str(task.get("state", ""))
        if task_role == role_canonical or task_state not in actionable_states:
            continue
        deps = {str(dep) for dep in task.get("depends_on", []) if dep}
        if own_ids.intersection(deps):
            downstream_impacts.append(f"{task.get('id')}:{task_role}:{task_state}")

    open_handoffs = [h for h in board.get("handoffs", []) if str(h.get("status", "")) == "OPEN"]
    open_to = [h for h in open_handoffs if _canonical_role(str(h.get("to_role", ""))) == role_canonical]
    open_from = [h for h in open_handoffs if _canonical_role(str(h.get("from_role", ""))) == role_canonical]

    recent_peer_events: List[str] = []
    for event in reversed(board.get("events", [])):
        kind = str(event.get("kind", "")).strip()
        if not kind:
            continue
        details = event.get("details", {}) if isinstance(event.get("details", {}), dict) else {}
        actor = _canonical_role(str(details.get("role") or details.get("from_role") or details.get("actor") or "").strip())
        if actor == role_canonical:
            continue
        ref = str(details.get("task_id") or details.get("handoff_id") or details.get("stream_id") or "none").strip()
        recent_peer_events.append(f"{kind}:{ref}")
        if len(recent_peer_events) >= max(1, limit):
            break

    impact_level = "none"
    impact_action = "none"
    if open_to or any(item.endswith(f":{STATE_BLOCKED}") for item in upstream_impacts):
        impact_level = "high"
        impact_action = "handoff-ack_or_unblock_upstream"
    elif upstream_impacts or shared_stream_impacts or downstream_impacts or open_from:
        impact_level = "medium"
        impact_action = "sync_cross_role"
    elif recent_peer_events:
        impact_level = "low"
        impact_action = "monitor_updates"

    def csv(values: List[str]) -> str:
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        return ",".join(cleaned[: max(1, limit)]) if cleaned else "none"

    own_status_counts = {
        STATE_READY: 0,
        STATE_READY_DEV: 0,
        STATE_IN_PROGRESS: 0,
        STATE_REVIEW: 0,
        STATE_DONE: 0,
        STATE_BLOCKED: 0,
    }
    for task in role_tasks:
        state = str(task.get("state", ""))
        if state in own_status_counts:
            own_status_counts[state] += 1

    print(
        "CHANNELS_CONTEXT "
        f"role={role_canonical} "
        "channels=workboard_tasks,workboard_handoffs,workboard_events,role_contracts,admin_chat,admin_iterations "
        f"self_active={len(own_actionable)} "
        f"peer_active={len(peer_active)} "
        f"open_handoffs_to={len(open_to)} "
        f"open_handoffs_from={len(open_from)} "
        f"shared_stream_impacts={csv(shared_stream_impacts)} "
        f"upstream_impacts={csv(upstream_impacts)} "
        f"downstream_impacts={csv(downstream_impacts)} "
        f"peer_events={csv(recent_peer_events)} "
        f"impact_level={impact_level} "
        f"impact_action={impact_action} "
        f"status_ready={own_status_counts[STATE_READY]} status_ready_dev={own_status_counts.get(STATE_READY_DEV,0)} "
        f"status_in_progress={own_status_counts[STATE_IN_PROGRESS]} "
        f"status_review={own_status_counts[STATE_REVIEW]} "
        f"status_done={own_status_counts[STATE_DONE]} "
        f"status_blocked={own_status_counts[STATE_BLOCKED]}"
    )


def replay_events(board: dict, limit: int, kind_filter: str, role_filter: str) -> None:
    events = board.get("events", [])
    if not isinstance(events, list):
        print("REPLAY_EMPTY reason=events_not_list")
        return
    selected: List[dict] = []
    for event in events:
        kind = str(event.get("kind", "")).strip()
        if kind_filter and kind_filter != kind:
            continue
        details = event.get("details", {}) if isinstance(event.get("details", {}), dict) else {}
        actor = _canonical_role(str(details.get("role") or details.get("from_role") or details.get("actor") or "").strip())
        if role_filter and role_filter != actor:
            continue
        selected.append(event)
    if limit > 0:
        selected = selected[-limit:]
    for idx, event in enumerate(selected, start=1):
        at = str(event.get("at", "unknown"))
        kind = str(event.get("kind", "unknown"))
        details = event.get("details", {}) if isinstance(event.get("details", {}), dict) else {}
        ref = str(details.get("task_id") or details.get("handoff_id") or details.get("stream_id") or "none")
        actor = str(details.get("role") or details.get("from_role") or details.get("actor") or "none")
        print(f"REPLAY idx={idx} at={at} kind={kind} actor={actor} ref={ref} details={json.dumps(details, ensure_ascii=True, separators=(',',':'))}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parallel workstream plumbing for multi-role delivery")
    parser.add_argument("--board", default=str(DEFAULT_BOARD), help="Path to board JSON file")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create board if missing (or overwrite with --force)").add_argument(
        "--force", action="store_true", help="Overwrite existing board"
    )

    sync_p = sub.add_parser("sync-priority", help="Create/refresh stream tasks from priority queue")
    sync_p.add_argument("--queue", default=str(DEFAULT_PRIORITY_QUEUE), help="Priority queue JSON path")
    sync_p.add_argument("--include-pass", action="store_true", help="Also sync PASS streams")

    reconcile_p = sub.add_parser("reconcile-state", help="Non-destructive queue/workboard reconciliation")
    reconcile_p.add_argument("--queue", default=str(DEFAULT_PRIORITY_QUEUE), help="Priority queue JSON path")

    sanitize_p = sub.add_parser("sanitize-dependencies", help="Enforce single-batch dependency policy in queue")
    sanitize_p.add_argument("--queue", default=str(DEFAULT_PRIORITY_QUEUE), help="Priority queue JSON path")
    sanitize_p.add_argument("--all-batches", action="store_true", default=True, help="Sanitize dependencies for all batches")
    sanitize_p.add_argument("--open-only", action="store_true", help="Sanitize only non-closed batches")

    autobatch_p = sub.add_parser("planner-autobatch", help="Create one planner READY batch when planner lane is idle")
    autobatch_p.add_argument("--queue", default=str(DEFAULT_PRIORITY_QUEUE), help="Priority queue JSON path")
    autobatch_p.add_argument("--reason", default="idle_no_ready", help="Reason tag for audit event")
    autobatch_p.add_argument("--cooldown-s", type=int, default=1800, help="Minimum seconds between autobatch creations")

    status_p = sub.add_parser("status", help="Print board status")
    status_p.add_argument("--role", default="", help="Filter by role")
    status_p.add_argument("--compact", action="store_true", help="Compact text output")
    status_p.add_argument("--limit", type=int, default=5, help="Per-list output limit")
    status_p.add_argument("--dev-ready", action="store_true", help="Print dev executable-ready summary")

    claim_p = sub.add_parser("claim", help="Claim one READY task for a role")
    claim_p.add_argument("--role", required=True)
    claim_p.add_argument("--task", default="", help="Optional explicit task id")
    claim_p.add_argument(
        "--change-plan",
        default="",
        help="Concrete change plan steps (>=5, >=2 words each, unique; must cover scope/dependencies/risk/verification/rollback with architecture checks)",
    )
    claim_p.add_argument(
        "--architecture-checks",
        default="",
        help="Concrete architecture checks before change (>=3 unique, >=6 chars, separators: , ; newline)",
    )

    done_p = sub.add_parser("complete", help="Mark task DONE")
    done_p.add_argument("--role", required=True)
    done_p.add_argument("--task", required=True)
    done_p.add_argument("--artifact", default="")
    done_p.add_argument("--note", default="")
    done_p.add_argument("--handoff-to", default="")
    done_p.add_argument("--exec-cmd", dest="exec_cmd", default="", help="Executed command evidence or SKIP(reason)")
    done_p.add_argument("--tests-run", default="", help="Test evidence or SKIP(reason)")
    done_p.add_argument("--review-ref", default="", help="Independent review reference")
    done_p.add_argument("--reviewer-role", default="", help="Independent reviewer role/agent")
    done_p.add_argument("--review-verdict", default="GO_WITH_CAUTION", help="Review verdict GO|BLOCKED|PASS")
    done_p.add_argument(
        "--change-plan",
        default="",
        help="Concrete change plan steps (>=5, >=2 words each, unique; must cover scope/dependencies/risk/verification/rollback with architecture checks)",
    )
    done_p.add_argument(
        "--architecture-checks",
        default="",
        help="Concrete architecture checks before change (>=3 unique, >=6 chars, separators: , ; newline)",
    )
    done_p.add_argument("--idempotency-key", default="", help="Stable idempotency key for completion/handoff")
    done_p.add_argument("--proof-root", default=str(DEFAULT_PROOF_ROOT), help="Proof manifest root directory")

    block_p = sub.add_parser("block", help="Mark task BLOCKED")
    block_p.add_argument("--task", required=True)
    block_p.add_argument("--reason", required=True)

    unblock_p = sub.add_parser("unblock", help="Clear task BLOCKED state")
    unblock_p.add_argument("--task", required=True)

    ack_p = sub.add_parser("handoff-ack", help="ACK an OPEN handoff")
    ack_p.add_argument("--handoff", required=True)
    ack_p.add_argument("--role", required=True)

    close_p = sub.add_parser("handoff-close", help="Close a handoff")
    close_p.add_argument("--handoff", required=True)
    close_p.add_argument("--role", default="")

    context_p = sub.add_parser("context", help="Compact role context for cron wake-up")
    context_p.add_argument("--role", required=True)
    context_p.add_argument("--limit", type=int, default=3, help="Max ids/events in context")

    channels_p = sub.add_parser("channels", help="Publication channels context + cross-role impact")
    channels_p.add_argument("--role", required=True)
    channels_p.add_argument("--limit", type=int, default=3, help="Max ids/events in channel summary")

    replay_p = sub.add_parser("replay", help="Deterministic replay of board events for audit/postmortem")
    replay_p.add_argument("--limit", type=int, default=50, help="Max events to print (tail)")
    replay_p.add_argument("--kind", default="", help="Filter by event kind")
    replay_p.add_argument("--role", default="", help="Filter by role/actor")

    validate_p = sub.add_parser("validate", help="Validate board consistency + coordination invariants")
    validate_p.add_argument("--queue", default=str(DEFAULT_PRIORITY_QUEUE), help="Priority queue JSON path for drift checks")
    validate_p.add_argument("--ack-sla-seconds", type=int, default=900, help="SLA for OPEN handoff ACK")
    validate_p.add_argument("--close-sla-seconds", type=int, default=3600, help="SLA for OPEN handoff CLOSE")
    validate_p.add_argument("--proof-root", default=str(DEFAULT_PROOF_ROOT), help="Proof manifest root directory")
    validate_p.add_argument("--require-proof-manifest", action="store_true", help="Block when DONE tasks have no proof manifest")
    validate_p.add_argument("--strict-warn", action="store_true", help="Treat warnings as blocking")
    validate_p.add_argument("--in-progress-stale-seconds", type=int, default=14400, help="Warn on stale IN_PROGRESS tasks")

    sla_p = sub.add_parser("enforce-sla", help="Evaluate/apply handoff SLA ownership and escalation")
    sla_p.add_argument("--ack-sla-seconds", type=int, default=900)
    sla_p.add_argument("--close-sla-seconds", type=int, default=3600)
    sla_p.add_argument("--apply", action="store_true", help="Persist SLA escalation fields on handoffs/tasks")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    board_path = Path(args.board)

    if args.cmd == "init":
        with board_lock(board_path):
            if board_path.exists() and not args.force:
                print(f"INIT_SKIP board_exists={board_path}")
                return 0
            board = default_board()
            save_board(board_path, board)
            print(f"INIT_OK board={board_path}")
            return 0

    if args.cmd == "sanitize-dependencies":
        all_batches = bool(args.all_batches) and not bool(args.open_only)
        with board_lock(board_path):
            board = load_board(board_path)
            counters = sanitize_queue_dependencies(Path(args.queue), all_batches=all_batches)
            append_event(
                board,
                "dependency_policy_migration_v1" if all_batches else "dependency_policy_sanitize",
                {
                    "queue": str(args.queue),
                    "dependency_policy": "single_batch",
                    "all_batches": "1" if all_batches else "0",
                    "decoupled_total": str(counters["decoupled_total"]),
                    "decoupled_closed": str(counters["decoupled_closed"]),
                    "decoupled_open": str(counters["decoupled_open"]),
                    "waiting_dep_reclassified": str(counters["waiting_dep_reclassified"]),
                },
            )
            save_board(board_path, board)
        print(
            "SANITIZE_OK "
            f"decoupled_total={counters['decoupled_total']} "
            f"decoupled_closed={counters['decoupled_closed']} "
            f"decoupled_open={counters['decoupled_open']} "
            f"waiting_dep_reclassified={counters['waiting_dep_reclassified']}"
        )
        return 0

    write_commands = {"sync-priority", "reconcile-state", "planner-autobatch", "claim", "complete", "block", "unblock", "handoff-ack", "handoff-close"}
    lock_write = args.cmd in write_commands or (args.cmd == "enforce-sla" and bool(args.apply))

    with board_lock(board_path, write=lock_write):
        board = load_board(board_path)

        if args.cmd == "sync-priority":
            created_streams, created_tasks = sync_from_priority_queue(
                board,
                Path(args.queue),
                include_pass=bool(args.include_pass),
            )
            save_board(board_path, board)
            print(f"SYNC_OK streams_created={created_streams} tasks_created={created_tasks} board={board_path}")
            return 0

        if args.cmd == "reconcile-state":
            result = reconcile_state(board, Path(args.queue))
            save_board(board_path, board)
            print(
                "RECONCILE_OK "
                f"queue_synced={result.get('queue_synced', 0)} "
                f"waiting_dep_reclassified={result.get('waiting_dep_reclassified', 0)} "
                f"board={board_path}"
            )
            return 0

        if args.cmd == "planner-autobatch":
            result = planner_autobatch(
                board,
                Path(str(args.queue)),
                reason=str(args.reason or "idle_no_ready").strip() or "idle_no_ready",
                cooldown_s=max(0, int(args.cooldown_s)),
                source="planner_autobatch_cli",
                workspace_root=Path.cwd().resolve(),
            )
            if result.get("status") == "ok":
                save_board(board_path, board)
                print(
                    "AUTOBATCH_OK "
                    f"batch_id={result.get('batch_id', 'none')} "
                    f"stream_created={result.get('stream_created', '0')} "
                    f"task_created={result.get('task_created', '0')} "
                    f"cooldown_applied={result.get('cooldown_applied', '0')}"
                )
            else:
                print(
                    "AUTOBATCH_SKIP "
                    f"reason={result.get('reason', 'unknown')} "
                    f"batch_id={result.get('batch_id', 'none')}"
                )
            return 0

        if args.cmd == "status":
            recompute_states(board)
            role_filter = str(args.role or "").strip()
            role_filter = _canonical_role(role_filter) if role_filter else ""
            print_status(
                board,
                role=role_filter,
                compact=bool(args.compact),
                limit=max(1, int(args.limit)),
                dev_ready_mode=bool(getattr(args, "dev_ready", False)),
            )
            return 0

        if args.cmd == "context":
            role = _canonical_role(str(args.role).strip())
            if role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {args.role}")
            print_role_context(board, role=role, limit=max(1, int(args.limit)))
            return 0

        if args.cmd == "channels":
            role = _canonical_role(str(args.role).strip())
            if role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {args.role}")
            print_publication_channels_context(board, role=role, limit=max(1, int(args.limit)))
            return 0

        if args.cmd == "replay":
            role_filter = _canonical_role(str(args.role or "").strip()) if str(args.role or "").strip() else ""
            replay_events(
                board,
                limit=max(1, int(args.limit)),
                kind_filter=str(args.kind or "").strip(),
                role_filter=role_filter,
            )
            return 0

        if args.cmd == "claim":
            role = _canonical_role(str(args.role).strip())
            if role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {args.role}")
            task = claim_task(
                board,
                role=role,
                task_id_override=str(args.task or "") or None,
                change_plan=str(args.change_plan or "").strip(),
                architecture_checks=str(args.architecture_checks or "").strip(),
            )
            save_board(board_path, board)
            print(
                f"CLAIM_OK role={role} task={task.get('id')} stream={task.get('stream_id')} priority={task.get('priority')} state={task.get('state')}"
            )
            return 0

        if args.cmd == "complete":
            role = _canonical_role(str(args.role).strip())
            if role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {args.role}")
            handoff_to = _canonical_role(str(args.handoff_to or "").strip()) if str(args.handoff_to or "").strip() else ""
            if handoff_to and handoff_to not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_HANDOFF_ROLE: {args.handoff_to}")
            task = complete_task(
                board,
                role=role,
                task_id_value=str(args.task).strip(),
                artifact=str(args.artifact or "").strip(),
                note=str(args.note or "").strip(),
                handoff_to=handoff_to,
                proof_root=Path(str(args.proof_root)),
                cmd=str(args.exec_cmd or "").strip(),
                tests_run=str(args.tests_run or "").strip(),
                review_ref=str(args.review_ref or "").strip(),
                reviewer_role=str(args.reviewer_role or "").strip(),
                review_verdict=str(args.review_verdict or "").strip(),
                change_plan=str(args.change_plan or "").strip(),
                architecture_checks=str(args.architecture_checks or "").strip(),
                idempotency_key=str(args.idempotency_key or "").strip(),
            )
            save_board(board_path, board)
            print(
                f"COMPLETE_OK role={role} task={task.get('id')} stream={task.get('stream_id')} handoff_to={handoff_to or 'none'}"
            )
            return 0

        if args.cmd == "block":
            task = set_block_state(board, task_id_value=str(args.task).strip(), reason=str(args.reason).strip(), blocked=True)
            save_board(board_path, board)
            print(f"BLOCK_OK task={task.get('id')} reason={task.get('blocked_reason')}")
            return 0

        if args.cmd == "unblock":
            task = set_block_state(board, task_id_value=str(args.task).strip(), reason="", blocked=False)
            save_board(board_path, board)
            print(f"UNBLOCK_OK task={task.get('id')} state={task.get('state')}")
            return 0

        if args.cmd == "handoff-ack":
            actor_role = _canonical_role(str(args.role).strip())
            if actor_role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {args.role}")
            handoff = handoff_update(board, handoff_id=str(args.handoff).strip(), status="ACK", actor_role=actor_role)
            save_board(board_path, board)
            print(f"HANDOFF_ACK_OK handoff={handoff.get('id')} task={handoff.get('task_id')} to={handoff.get('to_role')}")
            return 0

        if args.cmd == "handoff-close":
            actor_role = _canonical_role(str(args.role or "").strip()) if str(args.role or "").strip() else ""
            if actor_role and actor_role not in ROLE_CATALOG:
                raise SystemExit(f"UNKNOWN_ROLE: {args.role}")
            handoff = handoff_update(board, handoff_id=str(args.handoff).strip(), status="CLOSED", actor_role=actor_role)
            save_board(board_path, board)
            print(f"HANDOFF_CLOSE_OK handoff={handoff.get('id')} task={handoff.get('task_id')}")
            return 0

        if args.cmd == "enforce-sla":
            summary = enforce_handoff_sla(
                board,
                ack_sla_seconds=max(1, int(args.ack_sla_seconds)),
                close_sla_seconds=max(1, int(args.close_sla_seconds)),
                apply=bool(args.apply),
            )
            if bool(args.apply):
                save_board(board_path, board)
            print(
                "HANDOFF_SLA_SUMMARY "
                f"open_total={summary['open_total']} "
                f"ack_total={summary['ack_total']} "
                f"ack_overdue={summary['ack_overdue']} "
                f"close_overdue={summary['close_overdue']} "
                f"escalated={summary['escalated']} "
                f"blocked_tasks={summary['blocked_tasks']} "
                f"apply={1 if bool(args.apply) else 0}"
            )
            if summary["close_overdue"] > 0:
                return 2
            return 0

        if args.cmd == "validate":
            recompute_states(board)
            errors, warnings = validate_board(
                board,
                queue_path=Path(str(args.queue)),
                ack_sla_seconds=max(1, int(args.ack_sla_seconds)),
                close_sla_seconds=max(1, int(args.close_sla_seconds)),
                proof_root=Path(str(args.proof_root)),
                require_proof_manifest=bool(args.require_proof_manifest),
                in_progress_stale_seconds=max(1, int(args.in_progress_stale_seconds)),
            )
            if errors or (warnings and bool(args.strict_warn)):
                print("VALIDATE_BLOCKED")
                for err in errors:
                    print(f"- {err}")
                for warn in warnings:
                    print(f"! {warn}")
                return 2
            if warnings:
                print("VALIDATE_PASS_WITH_WARN")
                for warn in warnings:
                    print(f"! {warn}")
            else:
                print("VALIDATE_PASS")
            cross_task_dep_count = _count_cross_stream_task_dependencies(board)
            queue_inter_batch_dep_count = _queue_inter_batch_dep_count(Path(str(args.queue)))
            print(
                f"EVIDENCE tasks={len(board.get('tasks', []))} streams={len(board.get('streams', []))} "
                f"handoffs_open={sum(1 for h in board.get('handoffs', []) if h.get('status') == 'OPEN')} "
                f"warnings={len(warnings)} errors={len(errors)} "
                f"cross_dep_count={cross_task_dep_count + queue_inter_batch_dep_count} "
                f"cross_task_dep_count={cross_task_dep_count} "
                f"queue_inter_batch_dep_count={queue_inter_batch_dep_count}"
            )
            return 0

    parser.error(f"Unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
