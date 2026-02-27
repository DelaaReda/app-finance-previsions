#!/usr/bin/env python3
"""Role contract guard extracted from cron_tmux_role_runner.sh.

Input payload must be the 8-line contract. If payload is incomplete, it is
returned unchanged to preserve the original fallback flow.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

KEYS = [
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "RISKS",
    "NEXT",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
]

ROLE_TOKENS = {
    "planner": ["QUEUE", "READY", "PRIOR", "WORKSTATE", "PLAN"],
    "analyst": ["ANALYSIS", "REQUIREMENT", "ASSUMPTION", "TASK_ID", "DISCOVERY"],
    "dev": ["TASK", "STOR", "PATCH", "FILE=", "IMPLEMENT", "CODE"],
    "backend_engineer": ["BACKEND", "API", "ENDPOINT", "TASK_ID", "PATCH", "SERVICE"],
    "frontend_engineer": ["FRONTEND", "UI", "COMPONENT", "TASK_ID", "PATCH", "SCREEN"],
    "integrator": ["INTEGRATION", "TASK_ID", "CONTRACT", "E2E", "MERGE", "PIPELINE"],
    "data_analyst": ["DATA", "METRIC", "TASK_ID", "QUERY", "MODEL", "QUALITY"],
    "infra_engineer": ["INFRA", "CI", "DEPLOY", "TASK_ID", "OBSERVABILITY", "PIPELINE"],
    "tester": ["TEST", "PYTEST", "CASE", "SCENARIO", "COVER"],
    "qa": ["QA", "GATE", "VERDICT", "BLOCKER", "COHER"],
    "architect": ["ARCH", "CONTRAIN", "DEPEND", "RISK", "DESIGN", "CONFORMANCE", "ARCH_RULE", "VIOLATION"],
    "po": ["PO", "BACKLOG", "PRIOR", "SCOPE", "VALEUR", "VALUE"],
    "scrum_master": ["SCRUM", "SPRINT", "WIP", "BLOCKER", "CADENCE", "FLOW"],
    "clawsentinel": ["SENTINEL", "CRON", "HEALTH", "DRIFT", "WATCHDOG", "RISK"],
}

ARTIFACT_MARKERS = {
    "planner": "PLANNER_ARTIFACT=",
    "analyst": "ANALYST_ARTIFACT=",
    "dev": "DEV_ARTIFACT=",
    "backend_engineer": "BACKEND_ARTIFACT=",
    "frontend_engineer": "FRONTEND_ARTIFACT=",
    "integrator": "INTEGRATOR_ARTIFACT=",
    "data_analyst": "DATA_ARTIFACT=",
    "infra_engineer": "INFRA_ARTIFACT=",
    "tester": "TESTER_ARTIFACT=",
    "qa": "QA_ARTIFACT=",
    "architect": "ARCHITECT_ARTIFACT=",
    "po": "PO_ARTIFACT=",
    "scrum_master": "SCRUM_ARTIFACT=",
    "clawsentinel": "SENTINEL_ARTIFACT=",
}

COMMON_ARCHITECTURE_EVIDENCE_KEYS = ("arch_rule", "review_scope", "conformance", "violations")
ROLE_REQUIRED_EVIDENCE_KEYS = {
    "planner": ("vision_rule", *COMMON_ARCHITECTURE_EVIDENCE_KEYS),
    "analyst": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "dev": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "backend_engineer": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "frontend_engineer": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "integrator": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "data_analyst": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "infra_engineer": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "tester": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "qa": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "architect": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "po": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "scrum_master": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
    "clawsentinel": COMMON_ARCHITECTURE_EVIDENCE_KEYS,
}


def _parse_contract(text: str) -> dict[str, str]:
    values = {k: "" for k in KEYS}
    for raw in text.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip().upper()
        if key in values and not values[key]:
            values[key] = val.strip()
    return values


def _parse_evidence_kv(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for fragment in raw.split(";"):
        item = fragment.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key_norm = key.strip().lower()
        if not key_norm:
            continue
        out[key_norm] = value.strip()
    return out


def _append_evidence(raw: str, fragment: str) -> str:
    base = (raw or "").strip(" ;")
    frag = fragment.strip(" ;")
    if not frag:
        return base
    if not base:
        return frag
    if frag.lower() in base.lower():
        return base
    return f"{base}; {frag}"


def _is_skip_with_reason(value: str) -> bool:
    v = (value or "").strip()
    upper = v.upper()
    return upper.startswith("SKIP(") and v.endswith(")") and len(v) > len("SKIP()")


def _looks_like_permission_error(value: str) -> bool:
    upper = (value or "").strip().upper()
    markers = (
        "PERMISSION DENIED",
        "READ_ONLY",
        "READ-ONLY",
        "NON_ECRIVABLE",
        "WRITE_DENIED",
        "EROFS",
        "EPERM",
    )
    return any(marker in upper for marker in markers)


def _render_contract(values: dict[str, str]) -> str:
    return "\n".join(f"{k}: {values[k]}" for k in KEYS)


def main() -> int:
    if len(sys.argv) != 9:
        print(
            "usage: role_contract_guard.py <role> <source> <payload_file> "
            "<allow_file_edits:0|1> <workboard_has_work:0|1> "
            "<workboard_has_in_progress:0|1> <queue_version> <workboard_version>",
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1]
    source = sys.argv[2]
    payload_path = Path(sys.argv[3])
    allow_file_edits = sys.argv[4] == "1"
    workboard_role_has_work = sys.argv[5] == "1"
    workboard_role_has_in_progress = sys.argv[6] == "1"
    runtime_queue_version = sys.argv[7]
    runtime_workboard_version = sys.argv[8]

    text = payload_path.read_text(encoding="utf-8", errors="ignore")
    values = _parse_contract(text)

    if any(not values[k] for k in KEYS):
        # Keep original flow unchanged on partial payloads.
        print(text.strip())
        return 0

    evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", "").strip())

    queue_states: dict[str, str] = {}
    ready_ids: set[str] = set()
    queue_path = Path("docs/orchestrator-ops/priority-queue.json")
    if queue_path.exists():
        try:
            queue_obj = json.loads(queue_path.read_text(encoding="utf-8"))
            for item in queue_obj.get("items", []):
                item_id = str(item.get("id", "")).strip().upper()
                state = str(item.get("state", "")).strip().upper()
                if item_id:
                    queue_states[item_id] = state
                if item_id and state == "READY":
                    ready_ids.add(item_id)
        except Exception:
            pass
    queue_has_ready = bool(ready_ids)

    def emit_blocked(blocker_id: str, reason: str) -> None:
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        blocker_slug = re.sub(r"[^a-z0-9_]+", "_", blocker_id.lower()).strip("_") or "role_contract_guard"
        reason_clean = re.sub(r"\s+", "_", str(reason or "").strip())
        reason_clean = reason_clean.replace(";", ",")
        reason_clean = re.sub(r"[^A-Za-z0-9_.,:/=+-]", "", reason_clean)[:260] or "none"
        evidence = (
            "task_update=blocked; lock_check=ok; "
            "run_note=contract guard a bloque la sortie role pour incoherence; "
            f"exec_report=contract_guard_{blocker_slug}; "
            f"issues={blocker_slug}; "
            "suggestions=regenerer_sortie_role_specifique_avec_preuve_et_cmd; "
            "stream_id=none; task_id=none; "
            "tool_request=none; skill_request=none; "
            "channels_read=runtime_context; impact_assessment=medium; impact_action=regenerate_contract; "
            f"arch_rule=api_contract; review_scope={role}_contract_guard; "
            f"conformance=BLOCKED; violations={blocker_slug}; "
            f"role_artifact=contract_guard_{blocker_slug}; blocker_reason={reason_clean}"
        )
        blocked = {
            "STATUS": "BLOCKED",
            "DELTA": "ROLE_OUTPUT_NOT_SPECIFIC",
            "EVIDENCE": evidence,
            "RISKS": "livraison de role non spécifique, iteration non fiable",
            "NEXT": "regenerer une sortie avec preuve explicite liée au role et artefact concret",
            "VERDICT": "BLOCKED",
            "BLOCKER_ID": blocker_id,
            "NEXT_ACTION_UNIQUE": f"FIX_ROLE_CONTRACT_{role.upper()}_{now}",
        }
        print(_render_contract(blocked))
        raise SystemExit(0)

    def emit_permission_continue(reason: str, writable_refs: list[str] | None = None) -> None:
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        reason_clean = re.sub(r"\s+", "_", str(reason or "").strip())
        reason_clean = reason_clean.replace(";", ",")
        reason_clean = re.sub(r"[^A-Za-z0-9_.,:/=+-]", "", reason_clean)[:260] or "none"
        current_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))
        stream_id = (current_kv.get("stream_id") or "none").strip() or "none"
        task_id = (current_kv.get("task_id") or "none").strip() or "none"
        run_note = "probe lock incoherent, reprise livraison demandee"
        evidence = (
            "task_update=analysis_only; lock_check=ok; "
            f"run_note={run_note}; "
            "exec_report=delivery_probe_inconsistent_lock_only; "
            "issues=lock_probe_false_positive; "
            "suggestions=reprendre_livraison_sur_fichier_metier_et_fermer_tache; "
            f"stream_id={stream_id}; task_id={task_id}; "
            "tool_request=none; skill_request=none; "
            "channels_read=runtime_context; impact_assessment=low; impact_action=resume_delivery; "
            f"arch_rule=api_contract; review_scope={role}_delivery_probe; conformance=WARN; violations=lock_probe_false_positive; "
            f"{required_artifact_key}=delivery_probe_lock_false_positive; "
            f"queue_version={runtime_queue_version}; workboard_version={runtime_workboard_version}; "
            f"coordination_ref=analysis_only:{task_id}; probe_reason={reason_clean}"
        )
        if writable_refs:
            evidence = _append_evidence(evidence, f"probe_writable_refs_count={len(writable_refs)}")
        values["STATUS"] = "IN_PROGRESS"
        values["DELTA"] = "DELIVERY_PROBE_INCONSISTENT_CONTINUE"
        values["EVIDENCE"] = evidence
        values["RISKS"] = "signal lock incoherent; reprendre livraison sur commande metier ciblee"
        values["NEXT"] = (
            f"owner={role}; action=reprendre_claim_ou_complete_avec_preuve_cmd_sur_fichier_metier"
        )
        values["VERDICT"] = "GO_WITH_CAUTION"
        values["BLOCKER_ID"] = "NONE"
        values["NEXT_ACTION_UNIQUE"] = f"RECHECK_DELIVERY_PROBE_{role.upper()}_{now}"
        print(_render_contract(values))
        raise SystemExit(0)

    status_u = values["STATUS"].upper()
    blocker_id_u = values["BLOCKER_ID"].strip().upper()
    if status_u == "BLOCKED" and blocker_id_u in {"", "NONE", "N/A", "NULL"}:
        emit_blocked(
            "BLOCKER_ID_MISSING",
            f"role={role}; source={source}; required=BLOCKER_ID != NONE when STATUS=BLOCKED",
        )

    tokens = ROLE_TOKENS.get(role, [])
    required_marker = ARTIFACT_MARKERS.get(role, "ROLE_ARTIFACT=")
    required_artifact_key = required_marker.rstrip("=").lower()
    task_update = evidence_kv.get("task_update", "").strip().lower()
    lock_check = evidence_kv.get("lock_check", "").strip().lower()

    if not evidence_kv:
        emit_blocked(
            "EVIDENCE_KV_FORMAT_MISSING",
            f"role={role}; source={source}; required=format key=value;key2=value2 in EVIDENCE",
        )

    allowed_task_updates = {
        "claim",
        "complete",
        "handoff",
        "blocked",
        "analysis_only",
        "none_no_ready",
        "none_no_signal",
    }
    if not task_update:
        emit_blocked(
            "TASK_UPDATE_MISSING",
            f"role={role}; source={source}; required=task_update in EVIDENCE",
        )
    if task_update and task_update not in allowed_task_updates:
        emit_blocked(
            "TASK_UPDATE_INVALID",
            f"role={role}; source={source}; task_update={task_update}; allowed={','.join(sorted(allowed_task_updates))}",
        )
    if role in {"planner", "analyst", "architect", "po", "scrum_master", "clawsentinel"} and (not allow_file_edits) and task_update in {"claim", "complete", "handoff"}:
        emit_blocked(
            "READ_ONLY_TASK_UPDATE_INVALID",
            f"role={role}; source={source}; task_update={task_update}; mode=read_only; allowed=analysis_only|blocked|none_no_ready|none_no_signal",
        )
    if lock_check != "ok":
        emit_blocked(
            "LOCK_CHECK_MISSING",
            f"role={role}; source={source}; required=lock_check=ok in EVIDENCE",
        )

    run_note = evidence_kv.get("run_note", "").strip()
    if not run_note:
        emit_blocked(
            "RUN_NOTE_MISSING",
            f"role={role}; source={source}; required=run_note (>=5 words) in EVIDENCE",
        )
    run_note_words = [w for w in re.split(r"\s+", run_note) if w]
    if len(run_note_words) < 5:
        emit_blocked(
            "RUN_NOTE_TOO_SHORT",
            f"role={role}; source={source}; run_note_words={len(run_note_words)}; required>=5",
        )

    exec_report = evidence_kv.get("exec_report", "").strip()
    issues_summary = evidence_kv.get("issues", "").strip()
    suggestions_summary = evidence_kv.get("suggestions", "").strip()
    channels_read = evidence_kv.get("channels_read", "").strip().lower()
    impact_assessment = evidence_kv.get("impact_assessment", "").strip().lower()
    impact_action = evidence_kv.get("impact_action", "").strip().lower()
    if not exec_report:
        emit_blocked(
            "EXEC_REPORT_MISSING",
            f"role={role}; source={source}; required=exec_report in EVIDENCE",
        )
    if not issues_summary:
        emit_blocked(
            "ISSUES_SUMMARY_MISSING",
            f"role={role}; source={source}; required=issues in EVIDENCE (use none if no issue)",
        )
    if not suggestions_summary:
        emit_blocked(
            "SUGGESTIONS_SUMMARY_MISSING",
            f"role={role}; source={source}; required=suggestions in EVIDENCE (use none if no suggestion)",
        )
    issues_summary_l = issues_summary.strip().lower()
    suggestions_summary_l = suggestions_summary.strip().lower()
    if issues_summary_l and issues_summary_l not in {"none", "n/a", "na"} and suggestions_summary_l in {"none", "n/a", "na"}:
        emit_blocked(
            "SUGGESTIONS_REQUIRED_WITH_ISSUES",
            f"role={role}; source={source}; issues={issues_summary}; required=suggestions actionable when issues!=none",
        )

    require_publication_check = queue_has_ready or workboard_role_has_work or workboard_role_has_in_progress
    if require_publication_check:
        none_like = {"none", "n/a", "na"}
        if not channels_read:
            emit_blocked(
                "CHANNELS_READ_MISSING",
                f"role={role}; source={source}; required=channels_read in EVIDENCE when queue_or_workboard_has_work=1",
            )
        if channels_read in none_like:
            emit_blocked(
                "CHANNELS_READ_INVALID",
                f"role={role}; source={source}; channels_read={channels_read}; required=explicit_publication_channels",
            )
        if not impact_assessment:
            emit_blocked(
                "IMPACT_ASSESSMENT_MISSING",
                f"role={role}; source={source}; required=impact_assessment in EVIDENCE when queue_or_workboard_has_work=1",
            )
        allowed_impact = {"none", "low", "medium", "high", "critical"}
        if impact_assessment and impact_assessment not in allowed_impact:
            emit_blocked(
                "IMPACT_ASSESSMENT_INVALID",
                f"role={role}; source={source}; impact_assessment={impact_assessment}; allowed={','.join(sorted(allowed_impact))}",
            )
        if not impact_action:
            emit_blocked(
                "IMPACT_ACTION_MISSING",
                f"role={role}; source={source}; required=impact_action in EVIDENCE when queue_or_workboard_has_work=1",
            )
        if impact_assessment in {"medium", "high", "critical"} and impact_action in none_like:
            emit_blocked(
                "IMPACT_ACTION_INSUFFICIENT",
                f"role={role}; source={source}; impact_assessment={impact_assessment}; impact_action={impact_action}; required=concrete_action",
            )
        if impact_assessment in {"high", "critical"} and impact_action in {"monitor", "monitor_updates"}:
            emit_blocked(
                "IMPACT_ACTION_INSUFFICIENT",
                f"role={role}; source={source}; impact_assessment={impact_assessment}; impact_action={impact_action}; required=concrete_action",
            )

    if allow_file_edits and task_update in {"claim", "complete", "handoff"}:
        preannounce_required = ("intent_id", "intent_chat_ref", "intent_memory_ref", "intent_registry_ref", "edit_scope")
        missing_preannounce = [k for k in preannounce_required if not evidence_kv.get(k, "").strip()]
        if missing_preannounce:
            emit_blocked(
                "PREANNOUNCE_EVIDENCE_MISSING",
                f"role={role}; source={source}; task_update={task_update}; missing={','.join(missing_preannounce)}; required={','.join(preannounce_required)}",
            )

    if allow_file_edits and workboard_role_has_in_progress and task_update in {"analysis_only", "none_no_ready", "none_no_signal"}:
        emit_blocked(
            "IN_PROGRESS_NO_RESUME",
            f"role={role}; source={source}; task_update={task_update}; required=claim|complete|blocked|handoff when workboard_in_progress=1",
        )

    has_artifact_marker = required_marker in values.get("EVIDENCE", "").upper() or bool(evidence_kv.get(required_artifact_key))
    if not has_artifact_marker:
        emit_blocked(
            "ROLE_ARTIFACT_MISSING",
            f"role={role}; source={source}; required_marker={required_marker}",
        )

    required_evidence_keys = ROLE_REQUIRED_EVIDENCE_KEYS.get(role, tuple())
    if required_evidence_keys:
        missing_required = [k for k in required_evidence_keys if not evidence_kv.get(k, "").strip()]
        if missing_required:
            emit_blocked(
                "ROLE_MENTOR_EVIDENCE_MISSING",
                f"role={role}; source={source}; missing={','.join(missing_required)}; required={','.join(required_evidence_keys)}",
            )

    if "conformance" in required_evidence_keys:
        conformance = evidence_kv.get("conformance", "").strip().upper()
        if conformance not in {"PASS", "WARN", "BLOCKED"}:
            emit_blocked(
                "ARCHITECTURE_CONFORMANCE_INVALID",
                f"role={role}; source={source}; conformance={conformance or 'missing'}; allowed=PASS,WARN,BLOCKED",
            )

    if role == "planner":
        if (queue_has_ready or workboard_role_has_in_progress) and not evidence_kv.get("task_id", "").strip():
            emit_blocked(
                "PLANNER_TASK_ID_MISSING",
                f"role={role}; source={source}; required=task_id when queue_ready=1 or workboard_in_progress=1",
            )
    if role == "architect":
        if (queue_has_ready or workboard_role_has_in_progress) and not evidence_kv.get("task_id", "").strip():
            emit_blocked(
                "ARCHITECT_TASK_ID_MISSING",
                f"role={role}; source={source}; required=task_id when queue_ready=1 or workboard_in_progress=1",
            )

    if not evidence_kv.get("queue_version", "").strip():
        values["EVIDENCE"] = _append_evidence(values.get("EVIDENCE", ""), f"queue_version={runtime_queue_version}")
        evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))
    if not evidence_kv.get("workboard_version", "").strip():
        values["EVIDENCE"] = _append_evidence(values.get("EVIDENCE", ""), f"workboard_version={runtime_workboard_version}")
        evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))
    if not evidence_kv.get("coordination_ref", "").strip():
        coord_task = evidence_kv.get("task_id", "").strip() or "none"
        values["EVIDENCE"] = _append_evidence(values.get("EVIDENCE", ""), f"coordination_ref={task_update}:{coord_task}")
        evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))

    if queue_has_ready or workboard_role_has_work:
        phase1_missing = [k for k in ("stream_id", "task_id") if not evidence_kv.get(k, "").strip()]
        if phase1_missing:
            values["EVIDENCE"] = _append_evidence(values.get("EVIDENCE", ""), f"phase1_should_missing={','.join(phase1_missing)}")
            evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))

    if task_update == "complete":
        missing_phase2 = [k for k in ("stream_id", "task_id") if not evidence_kv.get(k, "").strip()]
        cmd_value = evidence_kv.get("cmd", "").strip()
        tests_value = evidence_kv.get("tests_run", "").strip()
        if not cmd_value:
            missing_phase2.append("cmd")
        elif cmd_value.upper().startswith("SKIP(") and not _is_skip_with_reason(cmd_value):
            missing_phase2.append("cmd_skip_reason")
        if not tests_value:
            missing_phase2.append("tests_run")
        elif tests_value.upper().startswith("SKIP(") and not _is_skip_with_reason(tests_value):
            missing_phase2.append("tests_run_skip_reason")
        if missing_phase2:
            emit_blocked(
                "EVIDENCE_PHASE2_MISSING",
                f"role={role}; source={source}; task_update=complete; missing={','.join(missing_phase2)}",
            )

    if task_update in {"claim", "handoff"}:
        missing_phase_claim = [k for k in ("stream_id", "task_id") if not evidence_kv.get(k, "").strip()]
        if missing_phase_claim:
            emit_blocked(
                "EVIDENCE_PHASE2_MISSING",
                f"role={role}; source={source}; task_update={task_update}; missing={','.join(missing_phase_claim)}",
            )

    if task_update == "handoff":
        handoff_to = evidence_kv.get("handoff_to", "").strip()
        if not handoff_to:
            emit_blocked(
                "HANDOFF_TO_MISSING",
                f"role={role}; source={source}; required=handoff_to for task_update=handoff",
            )
        valid_roles = set(ROLE_TOKENS.keys())
        if handoff_to and handoff_to not in valid_roles:
            emit_blocked(
                "HANDOFF_TO_INVALID",
                f"role={role}; source={source}; handoff_to={handoff_to}; allowed={','.join(sorted(valid_roles))}",
            )
        if not evidence_kv.get("handoff_ref", "").strip() and not evidence_kv.get("handoff_id", "").strip():
            values["EVIDENCE"] = _append_evidence(values.get("EVIDENCE", ""), "handoff_ref=pending")
            evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))

    scope_text = " ".join([values["DELTA"], values["EVIDENCE"], values["RISKS"], values["NEXT"], values["NEXT_ACTION_UNIQUE"]]).upper()
    has_role_signal = any(tok in scope_text for tok in tokens)
    chain_targets = set(re.findall(r"BATCH-[0-9]+", scope_text))
    is_generic_dispatch = (
        "DISPATCH_BATCH" in scope_text
        or "LANCER" in scope_text and "DISPATCH" in scope_text
        or "READY_DETECTE" in scope_text
    )
    target_ready = any(queue_states.get(t, "") == "READY" for t in chain_targets)
    permission_claimed = _looks_like_permission_error(scope_text)

    if is_generic_dispatch and not queue_has_ready:
        emit_blocked(
            "STALE_READY_ACTION",
            f"role={role}; source={source}; queue_ready=0; observed_dispatch={','.join(sorted(chain_targets)) or 'none'}",
        )
    if is_generic_dispatch and chain_targets and not target_ready:
        emit_blocked(
            "STALE_READY_ACTION",
            f"role={role}; source={source}; queue_ready_ids={','.join(sorted(ready_ids)) or 'none'}; observed_dispatch={','.join(sorted(chain_targets))}",
        )

    if role in {"dev", "backend_engineer", "frontend_engineer", "integrator", "data_analyst", "infra_engineer", "tester", "qa"} and allow_file_edits and queue_has_ready:
        has_cmd_evidence = any(
            token in scope_text
            for token in ("CMD=", "COMMAND=", "EXEC_SAFE.SH", "PYTEST", "BACKEND_REGRESSION_GATE", "CURL ", "NPM ", "PNPM ", "YARN ", "UV ", "MAKE ")
        )
        if values["DELTA"].strip().upper() == "NO_DELTA":
            emit_blocked(
                "DELIVERY_NO_DELTA_WITH_READY",
                f"role={role}; source={source}; queue_ready_ids={','.join(sorted(ready_ids))}; delta=NO_DELTA",
            )
        if not has_cmd_evidence:
            if source == "fallback_checkpoint":
                values["STATUS"] = "IN_PROGRESS"
                values["VERDICT"] = "GO_WITH_CAUTION"
                values["BLOCKER_ID"] = "NONE"
                values["DELTA"] = "READY_ITEM_AVAILABLE_RUNTIME_CONTEXT"
                values["RISKS"] = "signal de sortie non exploitable sur ce tick, preuve cmd a completer au prochain run"
                values["EVIDENCE"] = _append_evidence(
                    values.get("EVIDENCE", ""),
                    f"cmd_evidence_pending=1; queue_ready_ids={','.join(sorted(ready_ids))}",
                )
                evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))
            else:
                emit_blocked(
                    "ROLE_EXEC_EVIDENCE_MISSING",
                    f"role={role}; source={source}; required=CMD evidence for delivery role; queue_ready_ids={','.join(sorted(ready_ids))}",
                )

    if role in {"dev", "backend_engineer", "frontend_engineer", "integrator", "data_analyst", "infra_engineer", "tester", "qa"} and allow_file_edits and task_update == "blocked" and permission_claimed:
        cmd_value = evidence_kv.get("cmd", "").strip()
        cmd_err_excerpt = evidence_kv.get("cmd_err_excerpt", "").strip()
        if not (_looks_like_permission_error(cmd_value) or _looks_like_permission_error(cmd_err_excerpt)):
            emit_permission_continue(
                f"role={role}; source={source}; missing_write_error_evidence",
            )

        probe_sources = " ".join(
            [
                values.get("EVIDENCE", ""),
                values.get("RISKS", ""),
                values.get("NEXT", ""),
                cmd_value,
                cmd_err_excerpt,
            ]
        )
        path_candidates: set[str] = set()
        for quoted in re.findall(r"[\"']([^\"']+)[\"']", probe_sources):
            cand = quoted.strip()
            if "/" in cand or cand.startswith(("docs/", "copilot-app/")):
                path_candidates.add(cand)

        known_probe_paths = {
            "docs/orchestrator-ops/parallel-workstreams.json.lock",
            "docs/orchestrator-ops/intent-registry.json.lock",
            "docs/orchestrator-ops/parallel-workstreams.json",
            "docs/planning/tasks.md",
            "copilot-app/backend/logs/finance_analysis.log",
            "/home/venom/shared/analyse-financiere/copilot-app/backend/logs/finance_analysis.log",
        }
        path_candidates.update(known_probe_paths)

        writable_refs: list[str] = []
        cwd = Path.cwd()
        for raw_path in sorted(path_candidates):
            try:
                p = Path(raw_path)
                if not p.is_absolute():
                    p = (cwd / p).resolve(strict=False)
                else:
                    p = p.resolve(strict=False)
                probe_target = p if p.exists() else p.parent
                if probe_target and os.access(probe_target, os.W_OK):
                    writable_refs.append(str(p))
            except Exception:
                continue
        if writable_refs:
            emit_permission_continue(
                f"role={role}; source={source}; lock_probe_failed_but_paths_writable",
                writable_refs=writable_refs,
            )

    cmd_value_norm = evidence_kv.get("cmd", "").strip()
    if "/home/venom/shared/analyse-financiere" in cmd_value_norm:
        values["EVIDENCE"] = _append_evidence(values.get("EVIDENCE", ""), "workdir_alias=shared_ok")
        evidence_kv = _parse_evidence_kv(values.get("EVIDENCE", ""))

    if status_u == "BLOCKED":
        print(_render_contract(values))
        return 0

    if (queue_has_ready or workboard_role_has_work) and role in {
        "planner",
        "analyst",
        "architect",
        "dev",
        "backend_engineer",
        "frontend_engineer",
        "integrator",
        "data_analyst",
        "infra_engineer",
        "tester",
        "qa",
        "po",
        "scrum_master",
        "clawsentinel",
    }:
        if not task_update:
            emit_blocked(
                "TASK_UPDATE_MISSING",
                f"role={role}; source={source}; required=task_update marker when queue_or_workboard_has_work=1",
            )
        if lock_check != "ok":
            emit_blocked(
                "LOCK_CHECK_MISSING",
                f"role={role}; source={source}; required=lock_check=ok marker when queue_or_workboard_has_work=1",
            )

    has_runtime_context = any(sig in scope_text for sig in ["RUNTIME_CONTEXT", "QUEUE_STATES", "BATCH-"])
    generic_dispatch_weak = (
        is_generic_dispatch
        and role in {
            "tester",
            "qa",
            "architect",
            "po",
            "scrum_master",
            "clawsentinel",
            "analyst",
            "backend_engineer",
            "frontend_engineer",
            "integrator",
            "data_analyst",
            "infra_engineer",
        }
        and len(scope_text) < 260
        and not has_runtime_context
    )

    if has_role_signal and has_artifact_marker and not generic_dispatch_weak:
        print(_render_contract(values))
        return 0

    obs = re.sub(r"\s+", " ", scope_text).strip()[:140]
    required = "|".join(tokens) if tokens else "ROLE_SPECIFIC_SIGNAL"
    emit_blocked(
        "ROLE_CONTRACT_MISSING",
        f"role={role}; source={source}; required_any={required}; required_marker={required_marker}; observed={obs}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
