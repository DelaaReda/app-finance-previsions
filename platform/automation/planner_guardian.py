#!/usr/bin/env python3
"""Continuous quality monitor for planner role outputs.

Inputs:
  planner_guardian.py <role> <source> <payload_file> <runtime_context_file> \
    <latest_file> <events_file> <state_dir> <directive_bus_file>

Behavior:
  - Parse planner contract + evidence keys.
  - Score autonomy/alignment quality.
  - Track streaks (ready-but-idle, low score, no batch while runway short).
  - Persist latest/events artifacts for observability.
  - Emit a directive on repeated drift (deduplicated by fingerprint).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

CONTRACT_KEYS = (
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "RISKS",
    "NEXT",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
)
GUARDIAN_VERSION = "2026-03-03.v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def one_line(text: str, limit: int = 320) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(value) > limit:
        return value[:limit]
    return value


def parse_contract(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in text.splitlines():
        m = re.match(r"^\s*([A-Z_]+)\s*:\s*(.*)$", raw.strip())
        if not m:
            continue
        key = m.group(1).upper()
        if key in CONTRACT_KEYS and key not in out:
            out[key] = m.group(2).strip()
    return out


def parse_evidence_kv(raw: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for frag in raw.split(";"):
        if "=" not in frag:
            continue
        k, v = frag.split("=", 1)
        key = k.strip().lower()
        if not key or key in out:
            continue
        out[key] = v.strip()
    return out


def parse_runtime_flag(text: str, key: str, default: int = 0) -> int:
    m = re.search(rf"\b{re.escape(key)}=([01])\b", text)
    if not m:
        return default
    try:
        return int(m.group(1))
    except Exception:
        return default


def parse_runtime_context(text: str) -> Dict[str, int]:
    return {
        "queue_has_ready": parse_runtime_flag(text, "queue_has_ready", 0),
        "workboard_role_has_in_progress": parse_runtime_flag(
            text, "workboard_role_has_in_progress", 0
        ),
        "planner_batch_runway_short": parse_runtime_flag(
            text, "planner_batch_runway_short", 0
        ),
    }


def truthy(value: str) -> bool:
    token = str(value or "").strip().lower()
    return token in {"1", "true", "yes", "on", "ok", "created", "done"}


def compute_score(
    contract: Dict[str, str],
    evidence: Dict[str, str],
    runtime: Dict[str, int],
) -> Dict[str, object]:
    score = 100
    issues: List[str] = []

    status = contract.get("STATUS", "")
    delta = contract.get("DELTA", "")
    blocker = contract.get("BLOCKER_ID", "")
    task_update = evidence.get("task_update", "")
    has_stream = bool(evidence.get("stream_id"))
    has_task = bool(evidence.get("task_id"))

    has_planner_artifact = bool(evidence.get("planner_artifact"))
    has_arch_ref = bool(evidence.get("architecture_plan_ref"))
    has_vision_alignment = bool(evidence.get("vision_alignment"))
    has_arch_audit = bool(evidence.get("architecture_audit"))
    batch_created = truthy(evidence.get("batch_created", ""))
    arch_ref_value = str(evidence.get("architecture_plan_ref", "")).lower()
    vision_alignment_value = str(evidence.get("vision_alignment", "")).lower()
    arch_audit_value = str(evidence.get("architecture_audit", "")).lower()

    if not task_update:
        score -= 25
        issues.append("missing_task_update")
    if not has_planner_artifact:
        score -= 20
        issues.append("missing_planner_artifact")

    if runtime.get("queue_has_ready", 0) == 1:
        if delta.upper() == "NO_DELTA":
            score -= 30
            issues.append("ready_but_no_delta")
        if task_update in {"none_no_ready", "none_no_signal"}:
            score -= 35
            issues.append("ready_but_none_task_update")

    if status.upper() == "BLOCKED" and blocker.strip().upper() in {"", "NONE"}:
        score -= 20
        issues.append("blocked_without_blocker_id")

    if task_update in {"claim", "complete", "handoff"} and (not has_stream or not has_task):
        score -= 25
        issues.append("missing_stream_task_on_delivery_update")

    if runtime.get("planner_batch_runway_short", 0) == 1 and not batch_created:
        score -= 15
        issues.append("runway_short_without_batch_creation")

    # If planner did active work, demand stronger architecture/vision traceability.
    if task_update not in {"none_no_ready", "none_no_signal", "analysis_only", ""}:
        if not has_arch_ref:
            score -= 10
            issues.append("missing_architecture_plan_ref")
        if not has_vision_alignment:
            score -= 10
            issues.append("missing_vision_alignment")
        if not has_arch_audit:
            score -= 10
            issues.append("missing_architecture_audit")
        if has_arch_ref and not any(
            token in arch_ref_value
            for token in ("architecture_map", "docs/architecture", "apps/api", "apps/web")
        ):
            score -= 8
            issues.append("architecture_ref_not_canonical")
        if has_vision_alignment and not any(
            token in vision_alignment_value
            for token in ("product_vision", "batch-", "workstate", "roadmap")
        ):
            score -= 8
            issues.append("vision_alignment_not_traceable")
        if has_arch_audit and not any(
            token in arch_audit_value
            for token in ("apps/api", "apps/web", "platform/automation")
        ):
            score -= 8
            issues.append("architecture_audit_missing_paths")

    score = max(0, min(100, score))
    level = "green" if score >= 85 else ("yellow" if score >= 70 else "red")
    return {"score": score, "level": level, "issues": issues}


def load_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(read_text(path))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(path: Path, data: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def update_streaks(
    state: Dict[str, object],
    runtime: Dict[str, int],
    contract: Dict[str, str],
    evidence: Dict[str, str],
    score: int,
) -> Dict[str, int]:
    streaks = state.get("streaks")
    if not isinstance(streaks, dict):
        streaks = {}

    ready_idle = (
        runtime.get("queue_has_ready", 0) == 1
        and (
            contract.get("DELTA", "").upper() == "NO_DELTA"
            or evidence.get("task_update", "") in {"none_no_ready", "none_no_signal"}
        )
    )
    runway_no_batch = (
        runtime.get("planner_batch_runway_short", 0) == 1
        and not truthy(evidence.get("batch_created", ""))
    )

    streaks["ready_idle_streak"] = int(streaks.get("ready_idle_streak", 0)) + 1 if ready_idle else 0
    streaks["low_score_streak"] = int(streaks.get("low_score_streak", 0)) + 1 if score < 70 else 0
    streaks["runway_no_batch_streak"] = (
        int(streaks.get("runway_no_batch_streak", 0)) + 1 if runway_no_batch else 0
    )

    # Detect planner handoff-loop: same task_id handoffed repeatedly without progress.
    # Triggers when task_update=handoff on the same task >=3 consecutive ticks.
    current_task = evidence.get("task_id", "").strip()
    last_handoff_task = str(streaks.get("_last_handoff_task", "")).strip()
    is_handoff = evidence.get("task_update", "").strip().lower() == "handoff"
    if is_handoff and current_task and current_task == last_handoff_task:
        streaks["handoff_same_task_streak"] = int(streaks.get("handoff_same_task_streak", 0)) + 1
    else:
        streaks["handoff_same_task_streak"] = 0
    streaks["_last_handoff_task"] = current_task if is_handoff else ""

    return {k: int(v) for k, v in streaks.items() if not k.startswith("_")}, \
           {"_last_handoff_task": streaks.get("_last_handoff_task", "")}


def recommendations(issues: List[str]) -> List[str]:
    out: List[str] = []
    if "ready_but_no_delta" in issues or "ready_but_none_task_update" in issues:
        out.append("Claim une tache READY et fournir un dispatch concret vers role delivery.")
    if "missing_architecture_plan_ref" in issues or "missing_architecture_audit" in issues:
        out.append("Ajouter architecture_plan_ref + architecture_audit relies aux chemins apps/api|apps/web.")
    if "missing_vision_alignment" in issues:
        out.append("Lier explicitement le batch cree au target de PRODUCT_VISION.")
    if "vision_alignment_not_traceable" in issues:
        out.append("Rendre vision_alignment tracable avec PRODUCT_VISION + id BATCH explicite.")
    if "architecture_ref_not_canonical" in issues:
        out.append("Pointer architecture_plan_ref vers docs/architecture/ARCHITECTURE_MAP.md ou chemins apps/api|apps/web.")
    if "architecture_audit_missing_paths" in issues:
        out.append("Ajouter dans architecture_audit les chemins impactes (apps/api, apps/web, platform/automation).")
    if "runway_short_without_batch_creation" in issues:
        out.append("Creer un batch top-level BATCH-XX pour maintenir la runway planner.")
    if "missing_stream_task_on_delivery_update" in issues:
        out.append("Completer stream_id et task_id pour tout task_update claim|complete|handoff.")
    if not out:
        out.append("Maintenir cadence actuelle et poursuivre fermeture IN_PROGRESS avant nouveaux claims.")
    return out[:3]


def maybe_emit_directive(
    role: str,
    source: str,
    streaks: Dict[str, int],
    issues: List[str],
    score: int,
    bus_file: Path,
    state_dir: Path,
) -> None:
    handoff_loop = streaks.get("handoff_same_task_streak", 0) >= 3
    need_directive = (
        streaks.get("ready_idle_streak", 0) >= 3
        or streaks.get("low_score_streak", 0) >= 3
        or streaks.get("runway_no_batch_streak", 0) >= 3
        or handoff_loop
    )
    if not need_directive:
        return

    if handoff_loop:
        last_task = streaks.get("_last_handoff_task", "unknown")
        message = (
            f"planner_guardian HANDOFF_LOOP: tache '{last_task}' handoffee {streaks['handoff_same_task_streak']} fois sans cloture. "
            "Si la tache est de type GOV_REVIEW ou role=planner, completer toi-meme via task_update=complete. "
            "Ne pas handoff une tache dont tu es l assignee. "
            "Verifier que tous les depends_on sont DONE, puis marquer complete."
        )
    else:
        message = (
            f"planner_guardian escalation: score={score}; issues={','.join(issues) or 'none'}; "
            f"ready_idle_streak={streaks.get('ready_idle_streak', 0)}; "
            f"low_score_streak={streaks.get('low_score_streak', 0)}; "
            f"runway_no_batch_streak={streaks.get('runway_no_batch_streak', 0)}. "
            "Action attendue: claim READY ou creation batch top-level aligne vision+architecture."
        )
    fp = hashlib.sha256(message.encode("utf-8")).hexdigest()
    fp_file = state_dir / f"{role}.planner_guardian.last_directive_fp"
    prev = read_text(fp_file).strip()
    if prev == fp:
        return

    payload = {
        "ts_utc": now_utc(),
        "kind": "policy",
        "source": "planner_guardian",
        "targets": [role],
        "ttl_min": 180,
        "message": one_line(message, 600),
        "meta": {
            "score": score,
            "issues": issues[:8],
            "source_contract": source,
        },
    }
    bus_file.parent.mkdir(parents=True, exist_ok=True)
    with bus_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")
    fp_file.write_text(fp + "\n", encoding="utf-8")


def write_latest(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def append_event(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


def main() -> int:
    if len(sys.argv) != 9:
        print(
            "usage: planner_guardian.py <role> <source> <payload_file> <runtime_context_file> "
            "<latest_file> <events_file> <state_dir> <directive_bus_file>",
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1].strip()
    source = sys.argv[2].strip()
    payload_file = Path(sys.argv[3])
    runtime_context_file = Path(sys.argv[4])
    latest_file = Path(sys.argv[5])
    events_file = Path(sys.argv[6])
    state_dir = Path(sys.argv[7])
    directive_bus_file = Path(sys.argv[8])

    if role != "planner":
        return 0

    contract = parse_contract(read_text(payload_file))
    evidence = parse_evidence_kv(contract.get("EVIDENCE", ""))
    runtime = parse_runtime_context(read_text(runtime_context_file))

    score_info = compute_score(contract, evidence, runtime)
    score = int(score_info["score"])
    level = str(score_info["level"])
    issues = [str(item) for item in score_info["issues"]]

    state_file = state_dir / "planner_guardian_state.json"
    state = load_state(state_file)
    streaks_result = update_streaks(state, runtime, contract, evidence, score)
    streaks, meta = streaks_result if isinstance(streaks_result, tuple) else (streaks_result, {})
    recos = recommendations(issues)

    payload: Dict[str, object] = {
        "ts_utc": now_utc(),
        "guardian_version": GUARDIAN_VERSION,
        "role": role,
        "source": source,
        "score": score,
        "level": level,
        "issues": issues,
        "recommendations": recos,
        "streaks": streaks,
        "runtime": runtime,
        "summary": {
            "status": one_line(contract.get("STATUS", "")),
            "delta": one_line(contract.get("DELTA", "")),
            "verdict": one_line(contract.get("VERDICT", "")),
            "blocker_id": one_line(contract.get("BLOCKER_ID", "")),
            "next_action_unique": one_line(contract.get("NEXT_ACTION_UNIQUE", "")),
            "task_update": one_line(evidence.get("task_update", "")),
            "planner_artifact": one_line(evidence.get("planner_artifact", "")),
            "batch_created": one_line(evidence.get("batch_created", "")),
            "architecture_plan_ref": one_line(evidence.get("architecture_plan_ref", "")),
            "vision_alignment": one_line(evidence.get("vision_alignment", "")),
            "architecture_audit": one_line(evidence.get("architecture_audit", "")),
        },
    }

    state["updated_at_utc"] = payload["ts_utc"]
    state["streaks"] = {**streaks, **meta}  # persist _last_handoff_task alongside streak counts
    state["last_score"] = score
    state["last_level"] = level
    state["last_issues"] = issues[:12]
    save_state(state_file, state)

    write_latest(latest_file, payload)
    append_event(events_file, payload)
    maybe_emit_directive(
        role=role,
        source=source,
        streaks=streaks,
        issues=issues,
        score=score,
        bus_file=directive_bus_file,
        state_dir=state_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
