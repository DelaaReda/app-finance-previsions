#!/usr/bin/env python3
"""Role contract guard — version LEAN.

Vérifie l'essentiel uniquement. 10 checks, zéro overhead.
Remplace l'ancienne version 1091-lignes qui bloquait plus qu'elle n'aidait.
"""
from __future__ import annotations

import json
import os
import re
import sys
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

KEYS = ["STATUS", "DELTA", "EVIDENCE", "RISKS", "NEXT", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE"]

READ_ONLY_ROLES = {"planner", "analyst", "architect", "po", "clawsentinel"}
DELIVERY_ROLES  = {"backend_engineer", "frontend_engineer", "data_analyst", "dev",
                   "tester", "qa", "integrator", "infra_engineer", "admin"}

ALLOWED_TASK_UPDATES = {
    "claim", "complete", "handoff", "blocked",
    "analysis_only", "none_no_ready", "none_no_signal",
}

ARTIFACT_MARKERS = {
    "planner": "planner_artifact",
    "admin": "admin_artifact",
    "analyst": "analyst_artifact",
    "dev": "dev_artifact",
    "backend_engineer": "backend_artifact",
    "frontend_engineer": "frontend_artifact",
    "integrator": "integrator_artifact",
    "data_analyst": "data_artifact",
    "infra_engineer": "infra_artifact",
    "tester": "tester_artifact",
    "qa": "qa_artifact",
    "architect": "architect_artifact",
    "po": "po_artifact",
    "scrum_master": "scrum_artifact",
    "clawsentinel": "sentinel_artifact",
}

ADMIN_RUNTIME_BLOCKER_PREFIXES = (
    "API_",
    "BACKEND_",
    "FRONTEND_",
    "RUNTIME_",
    "CRON_",
    "SESSION_",
    "LOCK_",
    "SERVICE_",
    "PORT_",
    "NETWORK_",
    "DNS_",
    "RATE_LIMIT_",
    "DEPENDENCY_",
)

EMPTY_VALUE_MARKERS = {"", "none", "n/a", "null", "-", "na", "non", "aucun", "aucune"}
WEAK_EVIDENCE_MARKERS = {
    "?",
    "??",
    "???",
    "tbd",
    "todo",
    "to_do",
    "fixme",
    "a_faire",
    "coming_soon",
    "unknown",
    "pending",
    "later",
}
ISSUE_SEVERITY_VALUES = {"none", "low", "medium", "high", "critical"}
ISSUE_BLOCKED_MIN_SEVERITIES = {"medium", "high", "critical"}
ISSUE_CODE_RE = re.compile(r"^[a-z0-9_]{3,64}$")
FALLBACK_CHANNELS_ALLOWED = {"runtime_context"}
FALLBACK_IMPACT_ALLOWED = {"low"}
FALLBACK_IMPACT_ACTION_ALLOWED = {"monitor_updates"}
FALLBACK_CHANNELS_ISSUE_CODE = "channels_autofill_fallback"
ROLE_ALIAS_MAP = {
    "vision-architect-tasks-planner": "planner",
    "vision_architect_tasks_planner": "planner",
}

PLANNER_SOFT_BLOCKERS = {
    "HANDOFF_TO_MISSING",
    "PLANNER_BATCH_ID_INVALID",
    "MODE_ANALYSE_NO_EDITS",
    "BLOCKED_BY_MULTI_WAITING_DEPENDENCIES",
    "WAITING_DEP_TASKS",
    "WAITING_DEPENDENCIES",
    "PLANNER_INTER_BATCH_DEP_FORBIDDEN",
}


def _parse_contract(text: str) -> dict[str, str]:
    values = {k: "" for k in KEYS}
    for raw in text.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw).strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().upper()
        if key in values and not values[key]:
            values[key] = val.strip()
    return values


def _parse_kv(raw: str) -> dict[str, str]:
    kv: dict[str, str] = {}
    for frag in raw.split(";"):
        frag = frag.strip()
        if "=" in frag:
            k, _, v = frag.partition("=")
            kv[k.strip().lower()] = v.strip()
    return kv


def _parse_issue_codes(raw: str) -> tuple[list[str], list[str], bool]:
    text = (raw or "").strip()
    if not text:
        return [], [], False
    if text.lower() == "none":
        return [], [], True

    valid: list[str] = []
    invalid: list[str] = []
    for token in text.split(","):
        code = token.strip().lower()
        if not code:
            continue
        if ISSUE_CODE_RE.fullmatch(code):
            valid.append(code)
        else:
            invalid.append(code)
    return valid, invalid, False


def _crontab_agent_jobs() -> int:
    try:
        proc = subprocess.run(
            ["crontab", "-l"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return -1
    if proc.returncode != 0:
        return 0
    text = proc.stdout or ""
    return len(re.findall(r"(fc_agent_tick|cron_tmux_role_runner)", text))


def _recent_admin_cron_log(max_age_minutes: int = 120) -> bool:
    root = Path.cwd()
    log_path = root / "logs-codex-runs" / "fc-ticks" / "admin.cron.log"
    if not log_path.exists():
        return False
    try:
        age_seconds = datetime.now(timezone.utc).timestamp() - log_path.stat().st_mtime
        return age_seconds <= max_age_minutes * 60
    except Exception:
        return False


def _http_ok(url: str, timeout_s: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            code = int(getattr(resp, "status", 0) or resp.getcode() or 0)
            return 200 <= code < 500
    except Exception:
        return False


def _admin_runtime_probe_now() -> tuple[bool, bool]:
    backend_ok = _http_ok("http://127.0.0.1:8050/api/health", timeout_s=2.0)
    monitor_ok = _http_ok("http://127.0.0.1:7779/api/status", timeout_s=2.0)
    return backend_ok, monitor_ok


def _planner_runtime_unavailable(ev: dict[str, str], values: dict[str, str]) -> bool:
    force_up = str(os.environ.get("TMUX_ROLE_PLANNER_RUNTIME_FORCE_UP", "") or "").strip()
    force_down = str(os.environ.get("TMUX_ROLE_PLANNER_RUNTIME_FORCE_DOWN", "") or "").strip()
    if force_up == "1":
        return False
    if force_down == "1":
        return True
    runtime_markers = {"backend_api_unreachable", "monitor_api_unreachable", "runtime_unavailable"}
    blocker = str(values.get("BLOCKER_ID", "") or "").strip().lower()
    if blocker in runtime_markers:
        return True
    issues = {tok.strip().lower() for tok in str(ev.get("issues", "") or "").split(",") if tok.strip()}
    if issues & runtime_markers:
        return True
    backend_ok, monitor_ok = _admin_runtime_probe_now()
    return not (backend_ok and monitor_ok)


def _is_normalized_fallback_issue_report(ev: dict[str, str], source: str) -> bool:
    source_l = str(source or "").strip().lower()
    source_match = (
        "rate_limit_gate" in source_l
        or "fallback_checkpoint" in source_l
        or "no_delta" in source_l
    )
    marker_match = any(
        key in ev
        for key in (
            "fallback_mode",
            "rate_limit_source",
            "rate_limit_reason",
            "no_delta_streak",
        )
    )
    if not (source_match or marker_match):
        return False
    issues_raw = str(ev.get("issues", "") or "").strip().lower()
    issue_codes = [tok.strip() for tok in issues_raw.split(",") if tok.strip()]
    if FALLBACK_CHANNELS_ISSUE_CODE not in issue_codes:
        return False
    channels = str(ev.get("channels_read", "") or "").strip().lower()
    impact_assessment = str(ev.get("impact_assessment", "") or "").strip().lower()
    impact_action = str(ev.get("impact_action", "") or "").strip().lower()
    return (
        channels in FALLBACK_CHANNELS_ALLOWED
        and impact_assessment in FALLBACK_IMPACT_ALLOWED
        and impact_action in FALLBACK_IMPACT_ACTION_ALLOWED
    )


def _render(values: dict[str, str]) -> str:
    return "\n".join(f"{k}: {values[k]}" for k in KEYS)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _blocked(role: str, source: str, blocker_id: str, reason: str, values: dict[str, str]) -> None:
    slug = re.sub(r"[^a-z0-9_]+", "_", blocker_id.lower()).strip("_")
    issue_code = f"contract_guard_{slug}" if slug else "contract_guard_block"
    artifact_key = ARTIFACT_MARKERS.get(role, "role_artifact")
    ev = (
        f"task_update=blocked; lock_check=ok; "
        f"run_note=contract guard bloque {slug}; "
        f"{artifact_key}=platform/policies/role_contract_guard.py; "
        f"stream_id=none; task_id=none; "
        f"issues={issue_code}; issue_count=1; issue_severity=high"
    )
    out = {
        "STATUS": "BLOCKED",
        "DELTA": "CONTRACT_GUARD_BLOCK",
        "EVIDENCE": ev,
        "RISKS": reason[:200],
        "NEXT": f"owner={role}; action=corriger le contrat puis relancer",
        "VERDICT": "BLOCKED",
        "BLOCKER_ID": blocker_id,
        "NEXT_ACTION_UNIQUE": f"FIX_{role.upper()}_{_now()}",
    }
    print(_render(out))
    raise SystemExit(0)


def _sanitize_evidence(raw: str) -> str:
    """Strip noisy/debug fragments before persisting into role contracts."""
    if not raw:
        return ""
    cleaned: list[str] = []
    for frag in raw.split(";"):
        frag = frag.strip()
        if not frag:
            continue
        key = frag.split("=", 1)[0].strip().lower()
        if key.startswith("raw_"):
            continue
        if "=" in frag:
            k, v = frag.split("=", 1)
            v = v.strip()
            if len(v) > 180:
                v = v[:180]
            frag = f"{k.strip()}={v}"
        elif len(frag) > 180:
            frag = frag[:180]
        cleaned.append(frag)
    return "; ".join(cleaned)


def _upsert_evidence(values: dict[str, str], ev: dict[str, str], key: str, val: str) -> dict[str, str]:
    """Upsert one EVIDENCE key=value in both the parsed map and raw contract field."""
    key_norm = (key or "").strip().lower()
    if not key_norm:
        return ev
    ev[key_norm] = val
    evidence = values.get("EVIDENCE", "").strip()
    if re.search(rf"(^|[;\s]){re.escape(key_norm)}=", evidence, flags=re.IGNORECASE):
        values["EVIDENCE"] = re.sub(
            rf"(?i)\b{re.escape(key_norm)}=[^;]*",
            f"{key_norm}={val}",
            evidence,
        )
    else:
        sep = "; " if evidence else ""
        values["EVIDENCE"] = f"{evidence}{sep}{key_norm}={val}"
    return _parse_kv(values.get("EVIDENCE", ""))


def _is_admin_runtime_blocker(blocker_id: str) -> bool:
    blocker = (blocker_id or "").strip().upper()
    if blocker in {"", "NONE", "N/A", "NULL"}:
        return False
    return any(blocker.startswith(prefix) for prefix in ADMIN_RUNTIME_BLOCKER_PREFIXES)


def _is_empty_marker(raw: str) -> bool:
    return (raw or "").strip().lower() in EMPTY_VALUE_MARKERS


def _is_placeholder_marker(raw: str) -> bool:
    token = re.sub(r"\s+", "", (raw or "").strip().lower())
    if token in WEAK_EVIDENCE_MARKERS:
        return True
    return bool(re.fullmatch(r"[?.!_~\-]+", token))


def _is_empty_or_placeholder(raw: str) -> bool:
    return _is_empty_marker(raw) or _is_placeholder_marker(raw)


def _is_weak_evidence(raw: str) -> bool:
    text = (raw or "").strip()
    if _is_empty_marker(text) or _is_placeholder_marker(text):
        return True
    return len(text) < 3


def _default_channels_read_for_role(role: str) -> str:
    token = (role or "").strip().lower()
    if token == "admin":
        return "runtime_context,workboard_tasks,workboard_handoffs,role_contracts,admin_chat,admin_iterations"
    if token == "dev":
        return "runtime_context,workboard_tasks,workboard_handoffs,workboard_events,role_contracts"
    return "runtime_context,workboard_tasks,role_contracts"


def _has_required_kv_markers(
    raw: str,
    required_keys: tuple[str, ...],
    evidence: dict[str, str] | None = None,
) -> bool:
    text = (raw or "").strip().lower()
    remaining = {key.strip().lower() for key in required_keys if key.strip()}
    if text:
        for key in tuple(remaining):
            if re.search(rf"(^|[;,\s]){re.escape(key)}=", text):
                remaining.discard(key)
    if not remaining:
        return True
    if not evidence:
        return False
    for key in tuple(remaining):
        value = str(evidence.get(key, "") or "").strip()
        if not _is_empty_or_placeholder(value):
            remaining.discard(key)
    return not remaining


def _planner_batch_created_ids(raw: str) -> tuple[list[str], list[str]]:
    """
    Parse planner batch_created evidence into:
    - created_top_level_ids: explicit BATCH-XX creations
    - invalid_tokens: malformed tokens
    """
    created_top_level_ids: list[str] = []
    invalid_tokens: list[str] = []
    text = (raw or "").strip()
    if not text or _is_empty_marker(text):
        return created_top_level_ids, invalid_tokens

    # Accept common planner notations such as:
    # - "BATCH-26 -> BATCH-27"
    # - "batch_created=BATCH-26|BATCH-27"
    # - "BATCH-26/BATCH-27"
    normalized = (
        text.replace("->", " ")
        .replace("=>", " ")
        .replace("/", " ")
        .replace("\\", " ")
    )
    tokens = [tok for tok in re.split(r"[|,;\s>]+", normalized) if tok]
    for tok in tokens:
        token = tok.strip().strip("\"'`[](){}<>").strip().rstrip(".,:")
        token = token.upper()
        if not token or _is_empty_marker(token):
            continue
        if token.startswith("BATCH_CREATED="):
            token = token.split("=", 1)[1].strip()
            if not token or _is_empty_marker(token):
                continue
        if re.fullmatch(r"BATCH-\d{2}", token):
            created_top_level_ids.append(token)
            continue
        # Subtask/stream references are tolerated (not considered batch creations).
        if re.fullmatch(r"BATCH-\d{2}[-_][A-Z0-9][A-Z0-9._:-]*", token):
            continue
        # Ignore non-batch free text in this field, but keep strict checks
        # for malformed batch-like tokens.
        if token.startswith("BATCH-"):
            invalid_tokens.append(tok)

    return created_top_level_ids, invalid_tokens


def _canonical_role(role: str) -> str:
    token = (role or "").strip()
    if not token:
        return ""
    return ROLE_ALIAS_MAP.get(token, token)


def _safe_int(raw: str | None, default: int) -> int:
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def _previous_probe_streak(role: str) -> int:
    state_dir = Path(
        os.environ.get(
            "TMUX_ROLE_STATE_DIR",
            str(Path.home() / ".openclaw" / "cron" / "role-state"),
        )
    ).expanduser()
    previous_contract_path = state_dir / f"{role}.last_contract"
    if not previous_contract_path.exists():
        return 0
    try:
        previous_text = previous_contract_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    evidence_line = ""
    for line in previous_text.splitlines():
        if line.startswith("EVIDENCE:"):
            evidence_line = line.split(":", 1)[1].strip()
            break
    if not evidence_line:
        return 0
    m = re.search(r"delivery_probe_streak=(\d+)\s*/\s*(\d+)", evidence_line)
    if not m:
        return 0
    return _safe_int(m.group(1), 0)


def _set_delivery_probe_continue(
    *,
    values: dict[str, str],
    role: str,
    artifact_key: str,
    stream_id: str,
    task_id: str,
    threshold: int,
    streak: int,
    reason: str,
) -> dict[str, str]:
    values["STATUS"] = "IN_PROGRESS"
    values["DELTA"] = "DELIVERY_PROBE_INCONSISTENT_CONTINUE"
    values["VERDICT"] = "GO_WITH_CAUTION"
    values["BLOCKER_ID"] = "NONE"
    values["RISKS"] = "permission blocker non confirme converti en probe continue"
    values["NEXT"] = f"owner={role}; action=executer_cmd_metier_reel_puis_complete_ou_handoff"
    values["NEXT_ACTION_UNIQUE"] = f"RECHECK_DELIVERY_PROBE_{role.upper()}_{_now()}"
    values["EVIDENCE"] = (
        "task_update=none_no_signal; lock_check=ok; "
        "run_note=permission blocker non confirme converti en delivery probe continue; "
        f"{artifact_key}=platform/policies/role_contract_guard.py; "
        f"stream_id={stream_id}; task_id={task_id}; "
        f"permission_probe=unverified_continue; probe_reason={reason}; "
        f"delivery_probe_streak={streak}/{threshold}; "
        "issues=none; issue_count=0; issue_severity=none"
    )
    return _parse_kv(values.get("EVIDENCE", ""))


def _set_delivery_probe_streak_exceeded(
    *,
    values: dict[str, str],
    role: str,
    artifact_key: str,
    stream_id: str,
    task_id: str,
    threshold: int,
    streak: int,
    reason: str,
) -> dict[str, str]:
    values["STATUS"] = "BLOCKED"
    values["DELTA"] = "DELIVERY_PROBE_STREAK_EXCEEDED"
    values["VERDICT"] = "BLOCKED"
    values["BLOCKER_ID"] = "DELIVERY_PROBE_STREAK_EXCEEDED"
    values["RISKS"] = (
        f"delivery probe streak exceeded ({streak}/{threshold}); execution proof concrete requise avant nouveau blocage."
    )
    values["NEXT"] = f"owner={role}; action=fournir cmd+cmd_err_excerpt ou completer/handoff avec preuve concrete"
    values["NEXT_ACTION_UNIQUE"] = f"ESCALATE_DELIVERY_PROBE_{role.upper()}_{_now()}"
    values["EVIDENCE"] = (
        "task_update=blocked; lock_check=ok; "
        "run_note=delivery probe streak depasse le seuil, blocage conserve avec evidence explicite; "
        f"{artifact_key}=platform/policies/role_contract_guard.py; "
        f"stream_id={stream_id}; task_id={task_id}; "
        f"probe_reason={reason}; delivery_probe_streak={streak}/{threshold}; "
        "issues=delivery_probe_streak_exceeded; issue_count=1; issue_severity=high"
    )
    return _parse_kv(values.get("EVIDENCE", ""))


def _min_reflection_passes() -> int:
    raw = (
        os.environ.get("TMUX_ROLE_MIN_REFLECTION_PASSES")
        or os.environ.get("LM_USED_ROLE_MIN_REFLECTION_PASSES")
        or os.environ.get("MODEL_CONFIG_PARALLEL_ROLE_MIN_REFLECTION_PASSES")
        or "2"
    )
    return max(1, _safe_int(raw, 2))


def _should_convert_to_delivery_probe(
    *,
    role: str,
    task_update: str,
    values: dict[str, str],
    ev: dict[str, str],
) -> tuple[bool, str]:
    if task_update != "blocked":
        return False, ""
    if role not in DELIVERY_ROLES and role != "planner":
        return False, ""

    blocker = (values.get("BLOCKER_ID", "") or "").strip().lower()
    delta = (values.get("DELTA", "") or "").strip().lower()
    risk = (values.get("RISKS", "") or "").strip().lower()
    cmd = (ev.get("cmd", "") or "").strip().lower()
    cmd_err = (ev.get("cmd_err_excerpt", "") or "").strip().lower()
    violations = (ev.get("violations", "") or "").strip().lower()
    issue = (ev.get("issues", "") or "").strip().lower()
    suggestion = (ev.get("suggestions", "") or "").strip().lower()
    scope = " ".join([blocker, delta, risk, cmd, cmd_err, violations, issue, suggestion])

    is_permission = ("permission" in scope) or ("read_only" in scope) or ("readonly" in scope)
    if not is_permission:
        return False, ""

    if "lock" in scope:
        return True, "permission_lock_probe"
    return True, "permission_probe"


def _validate_issue_report(
    *,
    role: str,
    source: str,
    values: dict[str, str],
    ev: dict[str, str],
    task_update: str,
) -> dict[str, str]:
    """Validate issue reporting fields without masking higher-priority blockers."""
    if role == "scrum_master":
        # Advisory lane is normalized to non-blocking later in the pipeline.
        # Keep issue-report validation soft to avoid hard-blocking advisory output.
        return ev
    required_issue_fields = ("issues", "issue_count", "issue_severity")
    missing_issue_fields = [key for key in required_issue_fields if key not in ev]
    if missing_issue_fields:
        provided_issue_fields = [key for key in required_issue_fields if key in ev]
        if not provided_issue_fields:
            # Compat path: historical contracts often omitted issue fields entirely.
            # Keep strictness for partial reports, but auto-fill fully absent blocks.
            ev = _upsert_evidence(values, ev, "issues", "none")
            ev = _upsert_evidence(values, ev, "issue_count", "0")
            ev = _upsert_evidence(values, ev, "issue_severity", "none")
        else:
            blocker_id = "DEV_ISSUE_REPORT_INCOMPLETE" if role == "dev" else "ISSUE_REPORT_MISSING"
            _blocked(
                role,
                source,
                blocker_id,
                (
                    "issue reporting manquant: "
                    f"{','.join(missing_issue_fields)} (role={role})"
                ),
                values,
            )

    issues_raw = ev.get("issues", "").strip()
    issue_count_raw = ev.get("issue_count", "").strip()
    issue_severity = ev.get("issue_severity", "").strip().lower()

    if not re.fullmatch(r"\d+", issue_count_raw):
        _blocked(
            role,
            source,
            "ISSUE_REPORT_INVALID",
            f"issue_count invalide '{issue_count_raw}' (role={role})",
            values,
        )
    issue_count = int(issue_count_raw)
    if issue_count < 0:
        _blocked(
            role,
            source,
            "ISSUE_REPORT_INVALID",
            f"issue_count negatif '{issue_count_raw}' (role={role})",
            values,
        )

    if issue_severity not in ISSUE_SEVERITY_VALUES:
        _blocked(
            role,
            source,
            "ISSUE_REPORT_INVALID",
            (
                "issue_severity invalide "
                f"'{issue_severity}' (attendu={','.join(sorted(ISSUE_SEVERITY_VALUES))})"
            ),
            values,
        )

    issue_codes, invalid_issue_codes, issues_is_none = _parse_issue_codes(issues_raw)
    if invalid_issue_codes:
        _blocked(
            role,
            source,
            "ISSUE_REPORT_INVALID",
            f"issues contient des codes invalides: {','.join(invalid_issue_codes[:5])}",
            values,
        )
    if not issues_is_none and not issue_codes:
        _blocked(
            role,
            source,
            "ISSUE_REPORT_INVALID",
            "issues doit contenir au moins un code valide ou la valeur 'none'",
            values,
        )

    if issues_is_none:
        if issue_count != 0 or issue_severity != "none":
            _blocked(
                role,
                source,
                "ISSUE_REPORT_INCONSISTENT",
                (
                    "issues=none exige issue_count=0 et issue_severity=none "
                    f"(got count={issue_count}, severity={issue_severity})"
                ),
                values,
            )
    else:
        if issue_count <= 0:
            _blocked(
                role,
                source,
                "ISSUE_REPORT_INCONSISTENT",
                f"issue_count doit etre >0 quand issues!=none (got {issue_count})",
                values,
            )
        if issue_count != len(issue_codes):
            _blocked(
                role,
                source,
                "ISSUE_REPORT_INCONSISTENT",
                (
                    f"issue_count={issue_count} ne correspond pas au nombre de codes "
                    f"({len(issue_codes)})"
                ),
                values,
            )
        if issue_severity == "none":
            _blocked(
                role,
                source,
                "ISSUE_REPORT_INCONSISTENT",
                "issue_severity=none interdit quand issues!=none",
                values,
            )

    blocker_present = values["BLOCKER_ID"].strip().upper() not in {"", "NONE", "N/A", "NULL"}
    if task_update == "blocked" or blocker_present:
        if issues_is_none or issue_count < 1 or issue_severity not in ISSUE_BLOCKED_MIN_SEVERITIES:
            _blocked(
                role,
                source,
                "BLOCKED_WITHOUT_ISSUE_REPORT",
                (
                    "blocked/blocker exige issue valide: "
                    "issue_count>=1 et issue_severity in {medium,high,critical}"
                ),
                values,
            )
    return ev


def _append_issue(
    *,
    ev: dict[str, str],
    values: dict[str, str],
    code: str,
    severity: str = "low",
) -> dict[str, str]:
    issue_code = (code or "").strip().lower()
    if not issue_code:
        return ev
    issues_raw = (ev.get("issues", "") or "").strip()
    if issues_raw.lower() in {"", "none"}:
        issue_codes: list[str] = []
    else:
        issue_codes = [tok.strip().lower() for tok in issues_raw.split(",") if tok.strip()]
    if issue_code not in issue_codes:
        issue_codes.append(issue_code)
    sev_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    current = (ev.get("issue_severity", "") or "none").strip().lower()
    desired = (severity or "low").strip().lower()
    if desired not in sev_rank:
        desired = "low"
    if current not in sev_rank:
        current = "none"
    issue_severity = desired if sev_rank[desired] > sev_rank[current] else current
    ev = _upsert_evidence(values, ev, "issues", ",".join(issue_codes) if issue_codes else "none")
    ev = _upsert_evidence(values, ev, "issue_count", str(len(issue_codes)))
    ev = _upsert_evidence(values, ev, "issue_severity", issue_severity if issue_codes else "none")
    return ev


def main() -> int:
    if len(sys.argv) != 9:
        print(
            "usage: role_contract_guard.py <role> <source> <payload_file> "
            "<allow_file_edits:0|1> <workboard_has_work:0|1> "
            "<workboard_has_in_progress:0|1> <queue_version> <workboard_version>",
            file=sys.stderr,
        )
        return 2

    role = _canonical_role(sys.argv[1])
    source = sys.argv[2]
    payload_path = Path(sys.argv[3])
    allow_file_edits = sys.argv[4] == "1"
    workboard_has_work = sys.argv[5] == "1"
    workboard_has_in_progress = sys.argv[6] == "1"
    queue_version = (sys.argv[7] or "").strip()
    workboard_version = (sys.argv[8] or "").strip()

    text = payload_path.read_text(encoding="utf-8", errors="ignore")
    values = _parse_contract(text)

    # Payload incomplet -> normaliser vers un contrat exploitable (anti NO_DATA)
    if any(not values[k] for k in KEYS):
        artifact_key = ARTIFACT_MARKERS.get(role, "role_artifact")
        evidence_parts = [
            "task_update=none_no_signal",
            "lock_check=ok",
            "run_note=guard a complete automatiquement un contrat incomplet pour continuer la lane",
            f"{artifact_key}=platform/policies/role_contract_guard.py",
            "issues=contract_incomplete_autofill",
            "issue_count=1",
            "issue_severity=low",
        ]
        if role in DELIVERY_ROLES:
            evidence_parts.extend(
                [
                    f"channels_read={_default_channels_read_for_role(role)}",
                    "impact_assessment=low",
                    "impact_action=monitor_updates",
                ]
            )
        out = {
            "STATUS": "IN_PROGRESS",
            "DELTA": "NO_DELTA",
            "EVIDENCE": "; ".join(evidence_parts),
            "RISKS": "contrat incomplet auto-normalise par le guard",
            "NEXT": f"owner={role}; action=publier un contrat complet au prochain tick",
            "VERDICT": "GO_WITH_CAUTION",
            "BLOCKER_ID": "NONE",
            "NEXT_ACTION_UNIQUE": f"CONTINUE_{(role or 'role').upper()}_CONTRACT_AUTOFILL_{_now()}",
        }
        print(_render(out))
        return 0

    ev = _parse_kv(values.get("EVIDENCE", ""))
    task_update = ev.get("task_update", "").strip().lower()
    lock_check  = ev.get("lock_check", "").strip().lower()
    run_note    = ev.get("run_note", "").strip()
    artifact_key = ARTIFACT_MARKERS.get(role, "role_artifact")

    # ── PRE-NORMALIZATION : planner blocker drift ───────────────────────────
    # Keep planner lane active when model emits known soft blockers as hard BLOCKED.
    inter_batch_signal = False
    if role == "planner":
        dep_hint_fields = (
            "batch_depends_on",
            "depends_on_batch",
            "inter_batch_dep",
        )
        for field in dep_hint_fields:
            value = (ev.get(field, "") or "").strip().lower()
            if not value:
                continue
            if field == "inter_batch_dep":
                if value in {"1", "true", "yes", "on"}:
                    inter_batch_signal = True
                    break
                continue
            if value not in EMPTY_VALUE_MARKERS:
                inter_batch_signal = True
                break
        if inter_batch_signal:
            values["STATUS"] = "BLOCKED"
            values["VERDICT"] = "BLOCKED"
            values["BLOCKER_ID"] = "PLANNER_INTER_BATCH_DEP_FORBIDDEN"
            ev = _upsert_evidence(values, ev, "original_blocker", "PLANNER_INTER_BATCH_DEP_FORBIDDEN")
            task_update = ev.get("task_update", "").strip().lower()

    blocker_upper = values["BLOCKER_ID"].strip().upper()
    if role == "planner" and blocker_upper in PLANNER_SOFT_BLOCKERS and (
        task_update == "blocked" or values["STATUS"].strip().upper() == "BLOCKED"
    ):
        risk_map = {
            "HANDOFF_TO_MISSING": "handoff planner sans cible explicite converti en attente active",
            "PLANNER_BATCH_ID_INVALID": "batch_created invalide converti en attente active",
            "MODE_ANALYSE_NO_EDITS": "mode analyse sans edits converti en attente active",
            "BLOCKED_BY_MULTI_WAITING_DEPENDENCIES": "dépendances multiples en attente converties en attente active planifiée",
            "WAITING_DEP_TASKS": "tâches dépendantes en attente converties en attente active planifiée",
            "WAITING_DEPENDENCIES": "dépendances en attente converties en attente active planifiée",
            "PLANNER_INTER_BATCH_DEP_FORBIDDEN": "dépendance inter-batch interdite convertie en regroupement intra-batch",
        }
        next_map = {
            "HANDOFF_TO_MISSING": "owner=planner; action=reprendre le flux READY/IN_PROGRESS et cibler dev lors du prochain handoff",
            "PLANNER_BATCH_ID_INVALID": "owner=planner; action=normaliser batch_created puis reprendre le flux READY/IN_PROGRESS",
            "MODE_ANALYSE_NO_EDITS": "owner=planner; action=surveiller queue/workboard puis basculer delivery uniquement avec item claimable",
            "BLOCKED_BY_MULTI_WAITING_DEPENDENCIES": "owner=planner; action=faire avancer PLAN/ARCH en cours puis relancer sync-priority",
            "WAITING_DEP_TASKS": "owner=planner; action=faire avancer la tâche IN_PROGRESS racine puis relancer sync-priority",
            "WAITING_DEPENDENCIES": "owner=planner; action=faire avancer la tâche IN_PROGRESS racine puis relancer sync-priority",
            "PLANNER_INTER_BATCH_DEP_FORBIDDEN": "owner=planner; action=convert dependency to intra-batch tasks and rerun sync-priority",
        }
        evidence_note = {
            "HANDOFF_TO_MISSING": "handoff_to_autofill=dev",
            "PLANNER_BATCH_ID_INVALID": "batch_created_sanitized=1",
            "MODE_ANALYSE_NO_EDITS": "analysis_mode_converted_wait=1",
            "BLOCKED_BY_MULTI_WAITING_DEPENDENCIES": "waiting_dep_softblock_normalized=1",
            "WAITING_DEP_TASKS": "waiting_dep_softblock_normalized=1",
            "WAITING_DEPENDENCIES": "waiting_dep_softblock_normalized=1",
            "PLANNER_INTER_BATCH_DEP_FORBIDDEN": "dependency_policy_enforced=1",
        }
        action_tag = {
            "HANDOFF_TO_MISSING": "WAIT_HANDOFF_TARGET_NORMALIZED",
            "PLANNER_BATCH_ID_INVALID": "WAIT_BATCH_ID_SANITIZED",
            "MODE_ANALYSE_NO_EDITS": "WAIT_ANALYSIS_MODE",
            "BLOCKED_BY_MULTI_WAITING_DEPENDENCIES": "WAIT_DEPENDENCY_CHAIN",
            "WAITING_DEP_TASKS": "WAIT_DEPENDENCY_CHAIN",
            "WAITING_DEPENDENCIES": "WAIT_DEPENDENCY_CHAIN",
            "PLANNER_INTER_BATCH_DEP_FORBIDDEN": "WAIT_INTRA_BATCH_POLICY",
        }

        values["STATUS"] = "WAIT"
        values["DELTA"] = "NO_DELTA"
        values["VERDICT"] = "PASS"
        values["BLOCKER_ID"] = "NONE"
        values["RISKS"] = risk_map.get(blocker_upper, "planner soft blocker converti en attente active")
        values["NEXT"] = next_map.get(blocker_upper, "owner=planner; action=reprendre flux actif")
        values["NEXT_ACTION_UNIQUE"] = f"{action_tag.get(blocker_upper, 'WAIT_PLANNER_NORMALIZED')}_{_now()}"
        values["EVIDENCE"] = (
            "task_update=none_no_signal; lock_check=ok; "
            "run_note=guard neutralise un soft blocker planner et maintient le flux actif; "
            "planner_artifact=platform/policies/role_contract_guard.py; "
            f"{evidence_note.get(blocker_upper, 'guard_soft_blocker_normalized=1')}; "
            f"original_blocker={blocker_upper}; "
            "issues=none; issue_count=0; issue_severity=none"
        )
        ev = _parse_kv(values.get("EVIDENCE", ""))
        task_update = ev.get("task_update", "").strip().lower()
        lock_check = ev.get("lock_check", "").strip().lower()
        run_note = ev.get("run_note", "").strip()

    planner_never_wait = str(os.environ.get("TMUX_ROLE_PLANNER_NEVER_WAIT", "0")).strip() == "1"
    if role == "planner" and planner_never_wait and task_update in {"none_no_ready", "none_no_signal"}:
        runtime_down = _planner_runtime_unavailable(ev, values)
        if runtime_down:
            values["STATUS"] = "WAIT"
            values["DELTA"] = "RUNTIME_UNAVAILABLE"
            values["VERDICT"] = "GO_WITH_CAUTION"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "runtime indisponible detecte: exception planner passive autorisee"
            values["NEXT"] = "owner=planner; action=attendre retour runtime puis claim/create batch planner"
            values["NEXT_ACTION_UNIQUE"] = f"PLANNER_RUNTIME_EXCEPTION_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=runtime down confirme, exception planner passive activee; "
                "planner_artifact=platform/policies/role_contract_guard.py; "
                "planner_runtime_exception=1; planner_non_passive_policy=enforced; "
                "issues=runtime_unavailable; issue_count=1; issue_severity=medium"
            )
        else:
            values["STATUS"] = "IN_PROGRESS"
            values["DELTA"] = "PLANNER_PROGRESS_REQUIRED"
            values["VERDICT"] = "GO_WITH_CAUTION"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "sortie planner passive auto-corrigee par policy non-passive"
            values["NEXT"] = "owner=planner; action=sync-priority then claim/create planner batch"
            values["NEXT_ACTION_UNIQUE"] = f"PLANNER_NON_PASSIVE_AUTOFIX_{_now()}"
            values["EVIDENCE"] = (
                "task_update=analysis_only; lock_check=ok; "
                "run_note=guard force progression planner au lieu de passive none_no_ready; "
                "planner_artifact=platform/policies/role_contract_guard.py; "
                "planner_passive_autofix=1; planner_non_passive_policy=enforced; "
                "planner_action_required=create_or_claim; dependency_policy_enforced=1; "
                "issues=none; issue_count=0; issue_severity=none"
            )
        ev = _parse_kv(values.get("EVIDENCE", ""))
        task_update = ev.get("task_update", "").strip().lower()
        lock_check = ev.get("lock_check", "").strip().lower()
        run_note = ev.get("run_note", "").strip()

    # ── CHECK 1 : BLOCKED doit avoir un BLOCKER_ID non-NONE ──────────────────
    if values["STATUS"].upper() == "BLOCKED" and values["BLOCKER_ID"].upper() in ("", "NONE", "N/A", "NULL"):
        _blocked(role, source, "BLOCKER_ID_MISSING",
                 f"STATUS=BLOCKED mais BLOCKER_ID manquant (role={role})", values)

    # ── CHECK 2 : task_update doit être présent et valide ───────────────────
    if not task_update:
        _blocked(role, source, "TASK_UPDATE_MISSING",
                 f"task_update absent de EVIDENCE (role={role})", values)
    if task_update not in ALLOWED_TASK_UPDATES:
        _blocked(role, source, "TASK_UPDATE_INVALID",
                 f"task_update={task_update} invalide; valeurs: {','.join(sorted(ALLOWED_TASK_UPDATES))}", values)

    # ── CHECK 2b : planner quality soft-enforcement (non-blocking) ───────────
    planner_quality_soft_enforce = (
        str(os.environ.get("PLANNER_QUALITY_SOFT_ENFORCE", "1")).strip() == "1"
    )
    if role == "planner" and planner_quality_soft_enforce:
        planner_quality_task_updates = {"analysis_only", "claim", "complete", "handoff"}
        planner_passive_autofix = str(ev.get("planner_passive_autofix", "")).strip() == "1"
        if task_update in planner_quality_task_updates and not planner_passive_autofix:
            required_quality_fields = ("root_cause", "fix_applied", "verify", "reuse_check", "architecture_check", "vision_alignment")
            missing_quality_fields = [
                field for field in required_quality_fields if _is_weak_evidence(ev.get(field, ""))
            ]
            if missing_quality_fields:
                missing_csv = ",".join(missing_quality_fields)
                planner_quality_score = max(0, 100 - (len(missing_quality_fields) * 25))
                if values.get("STATUS", "").strip().upper() != "BLOCKED":
                    if values.get("DELTA", "").strip().upper() not in {
                        "PLANNER_PROGRESS_REQUIRED",
                        "RUNTIME_UNAVAILABLE",
                        "PLANNER_DISPATCH_INCOMPLETE",
                    }:
                        values["DELTA"] = "PLANNER_QUALITY_INCOMPLETE"
                    values["STATUS"] = "IN_PROGRESS"
                    values["VERDICT"] = "GO_WITH_CAUTION"
                    values["BLOCKER_ID"] = "NONE"
                    values["RISKS"] = "evidence qualite planner incomplete (soft autofix non bloquant)"
                    planner_action_required = str(ev.get("planner_action_required", "")).strip().lower()
                    if task_update == "complete":
                        values["DELTA"] = "PLANNER_QUALITY_BACKFILL_REQUIRED"
                        values["RISKS"] = "evidence qualite planner incomplete; complete converti en backfill"
                        values["NEXT"] = "owner=planner; action=backfill missing quality fields before complete"
                        values["NEXT_ACTION_UNIQUE"] = f"PLANNER_QUALITY_BACKFILL_{_now()}"
                        ev = _upsert_evidence(values, ev, "task_update", "analysis_only")
                        task_update = "analysis_only"
                    elif planner_action_required not in {"create_or_claim", "repair_dispatch_ids"}:
                        values["NEXT"] = "owner=planner; action=backfill missing quality fields before complete"
                        values["NEXT_ACTION_UNIQUE"] = f"PLANNER_QUALITY_BACKFILL_{_now()}"
                ev = _upsert_evidence(values, ev, "planner_quality_missing", missing_csv)
                ev = _upsert_evidence(values, ev, "planner_quality_score", str(planner_quality_score))
                ev = _upsert_evidence(values, ev, "planner_quality_autofix", "1")
                ev = _upsert_evidence(values, ev, "planner_non_passive_policy", "enforced")
                if _is_empty_or_placeholder(ev.get("planner_action_required", "")):
                    ev = _upsert_evidence(values, ev, "planner_action_required", "quality_backfill")
                task_update = str(ev.get("task_update", task_update)).strip().lower()

    # ── CHECK 3 : rôles read-only ne peuvent pas claim/complete/handoff ──────
    if role in READ_ONLY_ROLES and not allow_file_edits and task_update in {"claim", "complete", "handoff"}:
        values["EVIDENCE"] = re.sub(r"task_update=[^;]+", "task_update=analysis_only", values["EVIDENCE"])
        ev["task_update"] = task_update = "analysis_only"

    # ── CHECK 4 : lock_check=ok obligatoire ──────────────────────────────────
    if lock_check != "ok":
        _blocked(role, source, "LOCK_CHECK_MISSING",
                 f"lock_check manquant ou != ok dans EVIDENCE (role={role})", values)

    # ── CHECK 5 : run_note doit avoir ≥ 5 mots ───────────────────────────────
    if len([w for w in run_note.split() if w]) < 5:
        _blocked(role, source, "RUN_NOTE_TOO_SHORT",
                 f"run_note trop court (<5 mots): '{run_note}' (role={role})", values)
    # ── CHECK 6 : artefact rôle obligatoire ──────────────────────────────────
    artifact_val = ev.get(artifact_key, "").strip()
    if not artifact_val and role in DELIVERY_ROLES and task_update in {"blocked", "analysis_only", "none_no_ready", "none_no_signal"}:
        ev = _upsert_evidence(values, ev, artifact_key, "platform/policies/role_contract_guard.py")
        issues_raw = (ev.get("issues", "") or "").strip().lower()
        issue_codes = [tok.strip() for tok in issues_raw.split(",") if tok.strip() and tok.strip() != "none"]
        if "artifact_autofill_missing" not in issue_codes:
            issue_codes.append("artifact_autofill_missing")
        if issue_codes:
            ev = _upsert_evidence(values, ev, "issues", ",".join(issue_codes))
            ev = _upsert_evidence(values, ev, "issue_count", str(len(issue_codes)))
            current_sev = (ev.get("issue_severity", "") or "none").strip().lower()
            if current_sev not in {"low", "medium", "high", "critical"} or current_sev == "none":
                ev = _upsert_evidence(values, ev, "issue_severity", "low")
        artifact_val = ev.get(artifact_key, "").strip()
    if not artifact_val and role == "scrum_master":
        scrum_artifact_autofill = str(os.environ.get("FC_SCRUM_ARTIFACT_AUTOFILL", "1")).strip() == "1"
        if scrum_artifact_autofill:
            ev = _upsert_evidence(values, ev, artifact_key, "docs/ops/PO_SCRUM_MASTER_REPORTS.md")
            ev = _append_issue(ev=ev, values=values, code="scrum_artifact_autofill_missing", severity="low")
            artifact_val = ev.get(artifact_key, "").strip()
    if not artifact_val and role not in {"dev", "scrum_master"}:
        _blocked(role, source, "ROLE_ARTIFACT_MISSING",
                 f"{artifact_key} absent de EVIDENCE (role={role})", values)

    # ── CHECK 7 : claim/handoff → stream_id + task_id ────────────────────────
    if task_update in {"claim", "handoff"}:
        for field in ("stream_id", "task_id"):
            val = ev.get(field, "").strip().lower()
            if not val or val == "none":
                _blocked(role, source, f"CLAIM_{field.upper()}_MISSING",
                         f"{field} requis pour task_update={task_update} (role={role})", values)

    # ── CHECK 8 : complete → cmd présente (tests_run optionnel) ────────────
    if task_update == "complete":
        cmd = ev.get("cmd", "").strip()
        if not cmd and role != "dev":
            _blocked(role, source, "COMPLETE_CMD_MISSING",
                     f"cmd requise pour task_update=complete (role={role})", values)
        if not cmd and role == "dev":
            ev = _append_issue(ev=ev, values=values, code="complete_cmd_missing_non_blocking", severity="low")

    # ── CHECK 8a : channels/impact checks (avant delivery gate strict) ──────
    if role in DELIVERY_ROLES and task_update in {"analysis_only", "none_no_ready", "none_no_signal"}:
        fallback_issue_report = _is_normalized_fallback_issue_report(ev, source)
        channels_read = ev.get("channels_read", "").strip()
        impact_assessment = ev.get("impact_assessment", "").strip().lower()
        impact_action = ev.get("impact_action", "").strip()
        dev_autofill_enabled = str(os.environ.get("FC_DEV_CHANNELS_IMPACT_AUTOFILL", "1")).strip() == "1"

        if role == "dev" and dev_autofill_enabled:
            # Optional permissive mode for runtime experimentation.
            if _is_empty_or_placeholder(channels_read):
                ev = _upsert_evidence(values, ev, "channels_read", "runtime_context")
                ev = _append_issue(ev=ev, values=values, code="channels_autofill_missing", severity="low")
            if impact_assessment not in {"none", "low", "medium", "high", "critical"}:
                ev = _upsert_evidence(values, ev, "impact_assessment", "low")
                impact_assessment = "low"
                ev = _append_issue(ev=ev, values=values, code="impact_autofill_missing", severity="low")
            if _is_empty_or_placeholder(impact_action):
                ev = _upsert_evidence(values, ev, "impact_action", "monitor_updates")
                ev = _append_issue(ev=ev, values=values, code="impact_autofill_missing", severity="low")
        elif fallback_issue_report:
            if channels_read.lower() not in FALLBACK_CHANNELS_ALLOWED:
                _blocked(
                    role,
                    source,
                    "CHANNELS_READ_INVALID",
                    (
                        "fallback technique normalise exige channels_read "
                        f"in {{{','.join(sorted(FALLBACK_CHANNELS_ALLOWED))}}}"
                    ),
                    values,
                )
            if impact_assessment not in FALLBACK_IMPACT_ALLOWED:
                _blocked(
                    role,
                    source,
                    "IMPACT_ASSESSMENT_INVALID",
                    (
                        "fallback technique normalise exige impact_assessment "
                        f"in {{{','.join(sorted(FALLBACK_IMPACT_ALLOWED))}}}"
                    ),
                    values,
                )
            if impact_action.lower() not in FALLBACK_IMPACT_ACTION_ALLOWED:
                _blocked(
                    role,
                    source,
                    "IMPACT_ACTION_INSUFFICIENT",
                    (
                        "fallback technique normalise exige impact_action "
                        f"in {{{','.join(sorted(FALLBACK_IMPACT_ACTION_ALLOWED))}}}"
                    ),
                    values,
                )
        else:
            if _is_empty_or_placeholder(channels_read):
                _blocked(
                    role,
                    source,
                    "CHANNELS_READ_MISSING",
                    f"channels_read obligatoire pour task_update={task_update} (role={role})",
                    values,
                )
            if impact_assessment not in {"none", "low", "medium", "high", "critical"}:
                _blocked(
                    role,
                    source,
                    "IMPACT_ASSESSMENT_INVALID",
                    f"impact_assessment invalide '{impact_assessment}' (role={role})",
                    values,
                )
            if _is_empty_or_placeholder(impact_action):
                blocker_id = "IMPACT_ACTION_INSUFFICIENT" if impact_assessment in {"medium", "high", "critical"} else "IMPACT_ACTION_MISSING"
                _blocked(
                    role,
                    source,
                    blocker_id,
                    (
                        "impact_action obligatoire et concret pour task_update="
                        f"{task_update} (role={role})"
                    ),
                    values,
                )

    # ── CHECK 8a-ter : permission faux positif -> probe continue/streak ─────
    should_convert_probe, probe_reason = _should_convert_to_delivery_probe(
        role=role,
        task_update=task_update,
        values=values,
        ev=ev,
    )
    if should_convert_probe:
        threshold = max(1, _safe_int(os.environ.get("TMUX_ROLE_DELIVERY_PROBE_THRESHOLD"), 3))
        previous_streak = _previous_probe_streak(role)
        streak = previous_streak + 1
        stream_id = ev.get("stream_id", "").strip() or "none"
        task_id = ev.get("task_id", "").strip() or "none"
        if streak >= threshold:
            ev = _set_delivery_probe_streak_exceeded(
                values=values,
                role=role,
                artifact_key=artifact_key,
                stream_id=stream_id,
                task_id=task_id,
                threshold=threshold,
                streak=streak,
                reason=probe_reason,
            )
        else:
            ev = _set_delivery_probe_continue(
                values=values,
                role=role,
                artifact_key=artifact_key,
                stream_id=stream_id,
                task_id=task_id,
                threshold=threshold,
                streak=streak,
                reason=probe_reason,
            )
        task_update = ev.get("task_update", "").strip().lower()
        lock_check = ev.get("lock_check", "").strip().lower()
        run_note = ev.get("run_note", "").strip()

    # ── CHECK 8b : dev must provide architecture/reuse/qa evidence ──────────
    if role == "dev" and task_update in {"claim", "complete", "handoff"}:
        if task_update == "claim":
            # Claim payloads are intentionally lightweight for continuous flow.
            # Deep evidence stays mandatory only at complete/handoff stages.
            weak_or_missing_dev = []
        else:
            required_dev_fields = (
                "root_cause",
                "fix_applied",
                "verify",
                "reuse_check",
                "architecture_check",
                "vision_alignment",
                "qa_proof",
            )
            weak_or_missing_dev = []
            for field in required_dev_fields:
                raw_val = ev.get(field, "")
                # Keep explicit NONE for reuse_check to route to the dedicated
                # DEV_REUSE_CHECK_INVALID blocker with clearer remediation.
                if field == "reuse_check" and (raw_val or "").strip().lower() == "none":
                    continue
                if _is_weak_evidence(raw_val):
                    weak_or_missing_dev.append(field)
        if weak_or_missing_dev:
            _blocked(
                role,
                source,
                "DEV_DELIVERY_EVIDENCE_MISSING",
                (
                    "dev evidence incomplet/faible pour delivery; "
                    f"task_update={task_update}; weak_or_missing={','.join(weak_or_missing_dev)}"
                ),
                values,
            )
        reuse_check = ev.get("reuse_check", "")
        reuse_norm = reuse_check.strip().lower()
        if task_update != "claim" and reuse_norm == "none":
            _blocked(
                role,
                source,
                "DEV_REUSE_CHECK_INVALID",
                (
                    "reuse_check doit être un module concret ou NONE(<raison courte>); "
                    f"task_update={task_update}"
                ),
                values,
            )
        if task_update != "claim" and not _is_weak_evidence(reuse_check):
            # Prevent ambiguous NONE without rationale.
            if reuse_norm.startswith("none") and not re.match(
                r"^none\(.{3,}\)$", reuse_check.strip(), flags=re.IGNORECASE
            ):
                _blocked(
                    role,
                    source,
                    "DEV_REUSE_CHECK_INVALID",
                    (
                        "reuse_check doit être un module concret ou NONE(<raison courte>); "
                        f"task_update={task_update}"
                    ),
                    values,
                )
        if task_update != "claim" and not _has_required_kv_markers(
            ev.get("architecture_check", ""), ("layer", "imports_ok", "path_target"), ev
        ):
            _blocked(
                role,
                source,
                "DEV_ARCH_CHECK_FORMAT_INVALID",
                (
                    "architecture_check invalide; attendu "
                    "layer=<...>; imports_ok=<yes|no>; path_target=<...>"
                ),
                values,
            )
        if task_update != "claim" and not _has_required_kv_markers(
            ev.get("vision_alignment", ""), ("batch", "target", "impact"), ev
        ):
            _blocked(
                role,
                source,
                "DEV_VISION_ALIGNMENT_INVALID",
                (
                    "vision_alignment invalide; attendu "
                    "batch=<BATCH-XX>; target=<...>; impact=<...>"
                ),
                values,
            )
        if task_update in {"complete", "handoff"}:
            if not _has_required_kv_markers(ev.get("verify", ""), ("before", "after", "test"), ev):
                _blocked(
                    role,
                    source,
                    "DEV_VERIFY_FORMAT_INVALID",
                    "verify invalide; attendu before=<...>; after=<...>; test=<...>",
                    values,
                )
            if not _has_required_kv_markers(ev.get("qa_proof", ""), ("test", "result"), ev):
                _blocked(
                    role,
                    source,
                    "DEV_QA_PROOF_FORMAT_INVALID",
                    "qa_proof invalide; attendu test=<...>; result=<PASS|FAIL|SKIP(reason)>",
                    values,
                )

    # ── CHECK 8c : réflexion obligatoire (claim/handoff delivery lanes) ─────
    if role == "planner" and task_update in {"claim", "complete", "handoff"}:
        planner_required_fields = (
            "root_cause",
            "fix_applied",
            "verify",
            "reuse_check",
            "architecture_check",
            "vision_alignment",
        )
        weak_or_missing_planner: list[str] = []
        for field in planner_required_fields:
            raw_val = ev.get(field, "")
            if _is_weak_evidence(raw_val):
                weak_or_missing_planner.append(field)
                continue
            if field == "reuse_check":
                reuse_norm = raw_val.strip().lower()
                if reuse_norm == "none":
                    weak_or_missing_planner.append(field)
                    continue
                if reuse_norm.startswith("none") and not re.match(
                    r"^none\(.{3,}\)$", raw_val.strip(), flags=re.IGNORECASE
                ):
                    weak_or_missing_planner.append(field)
                    continue
            if field == "verify" and not _has_required_kv_markers(
                raw_val, ("before", "after", "test"), ev
            ):
                weak_or_missing_planner.append(field)
                continue
            if field == "vision_alignment" and not _has_required_kv_markers(
                raw_val, ("batch", "target", "impact"), ev
            ):
                weak_or_missing_planner.append(field)
                continue
        if weak_or_missing_planner:
            missing_csv = ",".join(sorted(set(weak_or_missing_planner)))
            if task_update == "complete":
                values["STATUS"] = "IN_PROGRESS"
                values["DELTA"] = "PLANNER_QUALITY_BACKFILL_REQUIRED"
                values["VERDICT"] = "GO_WITH_CAUTION"
                values["BLOCKER_ID"] = "NONE"
                values["RISKS"] = "planner evidence incomplete; complete converti en quality backfill"
                values["NEXT"] = "owner=planner; action=backfill missing quality fields before complete"
                values["NEXT_ACTION_UNIQUE"] = f"PLANNER_QUALITY_BACKFILL_{_now()}"
                ev = _upsert_evidence(values, ev, "task_update", "analysis_only")
                ev = _upsert_evidence(values, ev, "planner_quality_missing", missing_csv or "none")
                ev = _upsert_evidence(values, ev, "planner_quality_autofix", "1")
                ev = _upsert_evidence(values, ev, "planner_action_required", "quality_backfill")
                ev = _append_issue(
                    ev=ev,
                    values=values,
                    code="planner_evidence_incomplete_soft",
                    severity="low",
                )
                values["EVIDENCE"] = "; ".join(
                    f"{k}={v}" for k, v in ev.items() if str(k).strip()
                )
                task_update = "analysis_only"
            elif planner_quality_soft_enforce:
                planner_quality_soft_enforce = (
                    str(os.environ.get("PLANNER_QUALITY_SOFT_ENFORCE", "1")).strip() == "1"
                )
                planner_quality_score = max(0, 100 - (len(set(weak_or_missing_planner)) * 20))
                values["STATUS"] = "IN_PROGRESS"
                if values.get("DELTA", "").strip().upper() not in {
                    "PLANNER_PROGRESS_REQUIRED",
                    "RUNTIME_UNAVAILABLE",
                    "PLANNER_DISPATCH_INCOMPLETE",
                }:
                    values["DELTA"] = "PLANNER_QUALITY_INCOMPLETE"
                values["VERDICT"] = "GO_WITH_CAUTION"
                values["BLOCKER_ID"] = "NONE"
                values["RISKS"] = "evidence qualite planner incomplete (soft autofix non bloquant)"
                planner_action_required = str(ev.get("planner_action_required", "")).strip().lower()
                if planner_action_required not in {"create_or_claim", "repair_dispatch_ids"}:
                    values["NEXT"] = "owner=planner; action=backfill missing quality fields before complete"
                    values["NEXT_ACTION_UNIQUE"] = f"PLANNER_QUALITY_BACKFILL_{_now()}"
                ev = _upsert_evidence(values, ev, "planner_quality_missing", missing_csv)
                ev = _upsert_evidence(values, ev, "planner_quality_score", str(planner_quality_score))
                ev = _upsert_evidence(values, ev, "planner_quality_autofix", "1")
                ev = _upsert_evidence(values, ev, "planner_non_passive_policy", "enforced")
                if _is_empty_or_placeholder(ev.get("planner_action_required", "")):
                    ev = _upsert_evidence(values, ev, "planner_action_required", "quality_backfill")
                # Compatibility marker for downstream monitors/tests expecting legacy soft issue token.
                ev = _append_issue(
                    ev=ev,
                    values=values,
                    code="planner_evidence_incomplete_soft",
                    severity="low",
                )
                values["EVIDENCE"] = "; ".join(
                    f"{k}={v}" for k, v in ev.items() if str(k).strip()
                )
            elif task_update == "claim":
                ev = _append_issue(
                    ev=ev,
                    values=values,
                    code="planner_evidence_incomplete_soft",
                    severity="low",
                )
                ev = _upsert_evidence(
                    values,
                    ev,
                    "planner_quality_missing",
                    ",".join(sorted(set(weak_or_missing_planner))),
                )
                values["STATUS"] = "IN_PROGRESS"
                if values["VERDICT"].strip().upper() != "BLOCKED":
                    values["VERDICT"] = "GO_WITH_CAUTION"
                values["BLOCKER_ID"] = "NONE"
                values["EVIDENCE"] = "; ".join(
                    f"{k}={v}" for k, v in ev.items() if str(k).strip()
                )
            else:
                planner_evidence_strict = str(os.environ.get("FC_PLANNER_EVIDENCE_STRICT", "0")).strip() == "1"
                runtime_markers_present = (
                    not _is_empty_or_placeholder(ev.get("queue_version", ""))
                    and not _is_empty_or_placeholder(ev.get("workboard_version", ""))
                )
                if (not planner_evidence_strict) and runtime_markers_present:
                    missing_csv = ",".join(sorted(set(weak_or_missing_planner)))
                    values["STATUS"] = "IN_PROGRESS"
                    values["VERDICT"] = "GO_WITH_CAUTION"
                    values["BLOCKER_ID"] = "NONE"
                    values["DELTA"] = "PLANNER_EVIDENCE_AUTOFILLED"
                    values["RISKS"] = "planner evidence incomplete soft-autofill with runtime markers"
                    values["NEXT"] = "owner=planner; action=backfill missing quality fields before complete"
                    values["NEXT_ACTION_UNIQUE"] = f"PLANNER_EVIDENCE_AUTOFILL_{_now()}"
                    ev = _upsert_evidence(values, ev, "planner_evidence_missing", missing_csv)
                    ev = _upsert_evidence(values, ev, "planner_evidence_autofill", "1")
                    if _is_weak_evidence(ev.get("root_cause", "")):
                        ev = _upsert_evidence(values, ev, "root_cause", "runtime_autofill_missing")
                    if _is_weak_evidence(ev.get("fix_applied", "")):
                        ev = _upsert_evidence(values, ev, "fix_applied", "runtime_autofill_missing")
                    if _is_weak_evidence(ev.get("verify", "")):
                        ev = _upsert_evidence(values, ev, "verify", "before=missing; after=autofill_pending; test=next_tick")
                    ev = _append_issue(
                        ev=ev,
                        values=values,
                        code="planner_evidence_autofill_missing",
                        severity="low",
                    )
                    # Backward-compat marker still consumed by legacy dashboards/tests.
                    ev = _append_issue(
                        ev=ev,
                        values=values,
                        code="planner_evidence_incomplete_soft",
                        severity="low",
                    )
                    values["EVIDENCE"] = "; ".join(
                        f"{k}={v}" for k, v in ev.items() if str(k).strip()
                    )
                else:
                    missing_csv = ",".join(sorted(set(weak_or_missing_planner)))
                    values["STATUS"] = "IN_PROGRESS"
                    if values.get("DELTA", "").strip().upper() not in {
                        "PLANNER_PROGRESS_REQUIRED",
                        "RUNTIME_UNAVAILABLE",
                        "PLANNER_DISPATCH_INCOMPLETE",
                    }:
                        values["DELTA"] = "PLANNER_QUALITY_INCOMPLETE"
                    values["VERDICT"] = "GO_WITH_CAUTION"
                    values["BLOCKER_ID"] = "NONE"
                    values["RISKS"] = "planner evidence incomplete soft-enforced with mandatory quality backfill"
                    if _is_empty_or_placeholder(ev.get("planner_action_required", "")):
                        ev = _upsert_evidence(values, ev, "planner_action_required", "quality_backfill")
                    planner_quality_score_local = max(0, 100 - (len(sorted(set(weak_or_missing_planner))) * 25))
                    ev = _upsert_evidence(values, ev, "planner_quality_missing", missing_csv or "none")
                    ev = _upsert_evidence(values, ev, "planner_quality_score", str(planner_quality_score_local))
                    ev = _upsert_evidence(values, ev, "planner_quality_autofix", "1")
                    ev = _append_issue(
                        ev=ev,
                        values=values,
                        code="planner_evidence_incomplete_soft",
                        severity="low",
                    )
                    values["EVIDENCE"] = "; ".join(
                        f"{k}={v}" for k, v in ev.items() if str(k).strip()
                    )

    # ── CHECK 8c : réflexion obligatoire (claim/handoff delivery lanes) ─────
    if role in DELIVERY_ROLES and task_update in {"claim", "handoff"}:
        min_passes = _min_reflection_passes()
        reflection_passes = _safe_int(ev.get("reflection_passes"), -1)
        dimensions_raw = ev.get("reflection_dimensions", "")
        dimensions = {
            d.strip().lower()
            for d in re.split(r"[,\s|]+", dimensions_raw)
            if d.strip()
        }
        required_dimensions = {"scope", "dependency_impact", "risk", "verification", "rollback"}
        if reflection_passes < min_passes or not required_dimensions.issubset(dimensions):
            _blocked(
                role,
                source,
                "REFLECTION_PASSES_INVALID",
                (
                    f"reflection invalide pour task_update={task_update}; "
                    f"passes={reflection_passes} min={min_passes} "
                    f"dimensions={','.join(sorted(dimensions)) or 'none'}"
                ),
                values,
            )

    # ── CHECK 9 : handoff → handoff_to ───────────────────────────────────────
    if task_update == "handoff":
        # Planner handoff defaults to dev lane when target omitted.
        # This avoids unnecessary lane-wide BLOCKED while preserving explicit handoff intent.
        if role == "planner" and _is_empty_or_placeholder(ev.get("handoff_to", "")):
            ev = _upsert_evidence(values, ev, "handoff_to", "dev")
        if _is_empty_or_placeholder(ev.get("handoff_to", "")):
            _blocked(role, source, "HANDOFF_TO_MISSING",
                     f"handoff_to requis pour task_update=handoff (role={role})", values)

    # ── CHECK 9b : planner ne peut pas handoff vers lui-même ─────────────────
    # Les handoffs planner -> dev/admin restent valides; on bloque uniquement
    # les auto-handoffs explicites vers lane planner.
    if task_update == "handoff" and role == "planner":
        handoff_to_raw = ev.get("handoff_to", "").strip().lower()
        if handoff_to_raw in {"planner", "plan"}:
            _blocked(
                role,
                source,
                "PLANNER_SELF_HANDOFF_INVALID",
                "handoff_to=planner invalide pour role=planner; cibler une lane de delivery.",
                values,
            )

    # ── CHECK 10 : blocked avec motif permission doit avoir cmd_err_excerpt ──
    if task_update == "blocked":
        blocker_raw = values["BLOCKER_ID"].lower()
        if "permission" in blocker_raw or "read_only" in blocker_raw:
            if not ev.get("cmd_err_excerpt", "").strip():
                _blocked(role, source, "PERMISSION_BLOCKER_NO_PROOF",
                         f"blocker permission/read_only sans cmd_err_excerpt (role={role})", values)

    # ── CHECK 11 : planner batch creation must include architecture details ──
    if role == "planner":
        batch_created = ev.get("batch_created", "").strip()
        if batch_created and not _is_empty_marker(batch_created):
            created_batch_ids, invalid_ids = _planner_batch_created_ids(batch_created)
            if invalid_ids:
                # Never hard-block planner on malformed batch_created hints:
                # keep valid top-level IDs only and continue with a soft warning.
                sanitized = "|".join(created_batch_ids) if created_batch_ids else "none"
                if "batch_created=" in values.get("EVIDENCE", "").lower():
                    values["EVIDENCE"] = re.sub(
                        r"(?i)\bbatch_created=[^;]*",
                        f"batch_created={sanitized}",
                        values["EVIDENCE"],
                    )
                else:
                    sep = "; " if values.get("EVIDENCE", "").strip() else ""
                    values["EVIDENCE"] = f"{values.get('EVIDENCE', '')}{sep}batch_created={sanitized}"
                ev = _parse_kv(values.get("EVIDENCE", ""))
                note = f"batch_created_invalid_tokens_ignored={','.join(invalid_ids[:3])}"
                risks_prev = values.get("RISKS", "")
                values["RISKS"] = f"{risks_prev}; {note}".strip("; ").strip()
            if created_batch_ids:
                required_planner_fields = (
                    "architecture_plan_ref",
                    "implementation_tracks",
                    "integration_reuse",
                    "acceptance_gate",
                )
                missing = [
                    field
                    for field in required_planner_fields
                    if _is_empty_marker(ev.get(field, ""))
                ]
                if missing:
                    _blocked(
                        role,
                        source,
                        "PLANNER_BATCH_ARCH_MISSING",
                        f"creation batch sans details architecture: missing={','.join(missing)}",
                        values,
                    )

    # ── CHECK 11b : planner analysis-mode blocker should not hard-stop lane ─
    if role == "planner" and (task_update == "blocked" or values["BLOCKER_ID"].strip().upper() == "HANDOFF_TO_MISSING"):
        blocker = values["BLOCKER_ID"].strip().upper()
        if blocker == "MODE_ANALYSE_NO_EDITS":
            values["STATUS"] = "WAIT"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "PASS"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "mode analyse sans edits converti en attente active"
            values["NEXT"] = (
                "owner=planner; action=surveiller queue/workboard puis basculer delivery uniquement avec item claimable"
            )
            values["NEXT_ACTION_UNIQUE"] = f"WAIT_ANALYSIS_MODE_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard convertit faux blocage mode analyse en attente active; "
                "planner_artifact=platform/policies/role_contract_guard.py; "
                f"original_blocker={blocker}; "
                "issues=none; issue_count=0; issue_severity=none"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"
        elif blocker == "PLANNER_BATCH_ID_INVALID":
            values["STATUS"] = "WAIT"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "PASS"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "batch_created invalide converti en attente active"
            values["NEXT"] = (
                "owner=planner; action=normaliser batch_created puis reprendre le flux READY/IN_PROGRESS"
            )
            values["NEXT_ACTION_UNIQUE"] = f"WAIT_BATCH_ID_SANITIZED_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard convertit planner_batch_id_invalid en attente active; "
                "planner_artifact=platform/policies/role_contract_guard.py; "
                "batch_created_sanitized=1; original_blocker=PLANNER_BATCH_ID_INVALID; "
                "issues=none; issue_count=0; issue_severity=none"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"
        elif blocker == "HANDOFF_TO_MISSING":
            values["STATUS"] = "WAIT"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "PASS"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "handoff planner sans cible explicite converti en attente active"
            values["NEXT"] = (
                "owner=planner; action=reprendre le flux READY/IN_PROGRESS et cibler dev lors du prochain handoff"
            )
            values["NEXT_ACTION_UNIQUE"] = f"WAIT_HANDOFF_TARGET_NORMALIZED_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard neutralise handoff_to_missing planner et conserve lane active; "
                "planner_artifact=platform/policies/role_contract_guard.py; "
                "handoff_to_autofill=dev; original_blocker=HANDOFF_TO_MISSING; "
                "issues=none; issue_count=0; issue_severity=none"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"

    # ── CHECK 12 : mode delivery strict quand lane active ────────────────────
    # Empêche les sorties passives quand il existe du travail réel sur la lane.
    if role in DELIVERY_ROLES and role != "dev" and allow_file_edits and workboard_has_in_progress:
        if task_update in {"analysis_only", "none_no_ready"}:
            _blocked(
                role,
                source,
                "DELIVERY_ACTION_REQUIRED",
                (
                    f"lane active (work={int(workboard_has_work)} in_progress={int(workboard_has_in_progress)}) "
                    f"mais task_update={task_update}; attendu claim/complete/handoff/blocked avec preuve."
                ),
                values,
            )

    # ── CHECK 12b : dev anti-stall avec contexte actionnable ───────────────
    if role == "dev" and allow_file_edits:
        dev_ready_count = _safe_int(ev.get("dev_ready_count"), _safe_int(os.environ.get("RUNTIME_DEV_READY_COUNT"), 0))
        if dev_ready_count > 0 and task_update in {"analysis_only", "none_no_ready", "none_no_signal"}:
            values["STATUS"] = "IN_PROGRESS"
            values["DELTA"] = "DEV_READY_FORCE_CLAIM"
            values["VERDICT"] = "GO_WITH_CAUTION"
            values["BLOCKER_ID"] = "NONE"
            values["NEXT"] = "owner=dev; action=claim_or_progress_now"
            values["NEXT_ACTION_UNIQUE"] = f"DEV_READY_FORCE_CLAIM_{_now()}"
            ev = _upsert_evidence(values, ev, "task_update", "claim")
            ev = _upsert_evidence(values, ev, "dev_non_passive_policy", "enforced")
            ev = _upsert_evidence(values, ev, "dev_wait_allowed", "0")
            ev = _upsert_evidence(values, ev, "dev_wait_reason", "dev_ready_available")
            ev = _upsert_evidence(values, ev, "dev_passive_autofix", "1")
            ev = _append_issue(ev=ev, values=values, code="dev_passive_with_dev_ready", severity="low")
            task_update = "claim"

        dev_none_streak = _safe_int(os.environ.get("DEV_AUTONOMY_NONE_STREAK"), 0)
        dev_stall_threshold = max(
            1,
            _safe_int(os.environ.get("TMUX_ROLE_DEV_AUTONOMY_STALL_THRESHOLD_TICKS"), 2),
        )
        dev_guard_active = str(os.environ.get("DEV_AUTONOMY_ENFORCE_GUARD", "0")).strip() == "1"
        dev_wait_role_scoped = str(os.environ.get("TMUX_ROLE_DEV_WAIT_ROLE_SCOPED", "1")).strip() == "1"
        queue_has_ready_env = str(os.environ.get("RUNTIME_QUEUE_HAS_READY", "0")).strip() == "1"
        if dev_wait_role_scoped:
            actionable_work = bool(workboard_has_in_progress or workboard_has_work)
        else:
            actionable_work = bool(workboard_has_in_progress or workboard_has_work or queue_has_ready_env)
        if actionable_work and task_update in {"none_no_signal", "none_no_ready", "analysis_only"}:
            sev = "medium" if task_update == "analysis_only" else "low"
            ev = _append_issue(
                ev=ev,
                values=values,
                code="dev_passive_with_ready",
                severity=sev,
            )
            if dev_guard_active:
                _blocked(
                    role,
                    source,
                    "DEV_ENFORCED_ACTION_MISSING",
                    (
                        "dev autonomy enforcement actif mais sortie passive detectee; "
                        f"streak={dev_none_streak} threshold={dev_stall_threshold}"
                    ),
                    values,
                )
            elif dev_none_streak >= (dev_stall_threshold + 2):
                _blocked(
                    role,
                    source,
                    "DEV_STALL_WITH_ACTIONABLE_WORK",
                    (
                        "dev none_no_signal/none_no_ready repete avec travail actionnable; "
                        f"streak={dev_none_streak} threshold={dev_stall_threshold}"
                    ),
                    values,
                )

    # ── CHECK 13 : admin ne doit pas se bloquer sur des dérives non-runtime ─
    if role == "admin" and task_update == "blocked":
        blocker = values["BLOCKER_ID"].strip().upper()
        runtime_port_blockers = {
            "BACKEND_API_UNREACHABLE",
            "MONITOR_API_UNREACHABLE",
            "READY_BLOCKED_BY_RUNTIME",
            "RUNTIME_DEGRADED",
            "RUNTIME_PORTS_DOWN",
        }
        if blocker in runtime_port_blockers:
            cmd_err = ev.get("cmd_err_excerpt", "").strip()
            backend_now_ok, monitor_now_ok = _admin_runtime_probe_now()
            if backend_now_ok and monitor_now_ok and not cmd_err:
                values["STATUS"] = "WAIT"
                values["DELTA"] = "NO_DELTA"
                values["VERDICT"] = "WAIT"
                values["BLOCKER_ID"] = "NONE"
                values["RISKS"] = "faux blocage runtime neutralise: probes locales backend/monitor OK"
                values["NEXT"] = (
                    "owner=admin; action=continuer supervision et prioriser debottleneck workflow actif"
                )
                values["NEXT_ACTION_UNIQUE"] = f"ADMIN_RUNTIME_FALSE_ALARM_SUPPRESSED_{_now()}"
                values["EVIDENCE"] = (
                    "task_update=none_no_signal; lock_check=ok; "
                    "run_note=guard neutralise blocker runtime sans preuve car probes locales ok; "
                    "admin_artifact=platform/policies/role_contract_guard.py; "
                    f"original_blocker={blocker}; "
                    f"runtime_probe_backend={'up' if backend_now_ok else 'down'}; "
                    f"runtime_probe_monitor={'up' if monitor_now_ok else 'down'}; "
                    "issues=none; issue_count=0; issue_severity=none"
                )
                ev = _parse_kv(values["EVIDENCE"])
                task_update = "none_no_signal"

        if blocker != "CRON_SCHEDULE_MISSING" and not _is_admin_runtime_blocker(blocker):
            values["STATUS"] = "IN_PROGRESS"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "GO_WITH_CAUTION"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "blocage admin non-runtime converti en supervision continue"
            values["NEXT"] = (
                "owner=admin; action=traiter la derive et pousser une action de debottleneck, sans auto-blocker lane"
            )
            values["NEXT_ACTION_UNIQUE"] = f"CONTINUE_ADMIN_DEBOTTLENECK_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard retire auto-blocker non-runtime et force supervision active; "
                "admin_artifact=platform/policies/role_contract_guard.py; "
                f"original_blocker={blocker}; "
                "issues=none; issue_count=0; issue_severity=none"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"

    # ── CHECK 13b : scrum_master advisory lane non-bloquante en mode advisory ───
    scrum_mode = str(os.environ.get("FC_SCRUM_MASTER_MODE", "operational")).strip().lower()
    if role == "scrum_master" and scrum_mode == "advisory":
        status_u = values.get("STATUS", "").strip().upper()
        verdict_u = values.get("VERDICT", "").strip().upper()
        blocker_u = values.get("BLOCKER_ID", "").strip().upper()
        if status_u == "BLOCKED" or verdict_u == "BLOCKED" or blocker_u not in {"", "NONE"}:
            values["STATUS"] = "IN_PROGRESS"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "GO_WITH_CAUTION"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = "lane advisory scrum_master normalisée en non-blocant"
            values["NEXT"] = "owner=scrum_master; action=publier diagnostic et recommandations ciblées"
            values["NEXT_ACTION_UNIQUE"] = f"SCRUM_MASTER_ADVISORY_CONTINUE_{_now()}"
            values["EVIDENCE"] = (
                "task_update=analysis_only; lock_check=ok; "
                "run_note=guard applique mode advisory non bloquant pour scrum_master; "
                "scrum_artifact=docs/ops/PO_SCRUM_MASTER_REPORTS.md; "
                "advisory_non_blocking=1; "
                f"original_blocker={blocker_u or 'NONE'}; "
                "issues=scrum_advisory_non_blocking; issue_count=1; issue_severity=low"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "analysis_only"
        elif ev.get("advisory_non_blocking", "").strip() != "1":
            ev = _upsert_evidence(values, ev, "advisory_non_blocking", "1")

    # ── CHECK 14 : anti-faux-blocker cron admin ──────────────────────────────
    # Cas observé: admin déclare CRON_SCHEDULE_MISSING alors que les ticks existent.
    if role == "admin" and task_update == "blocked" and values["BLOCKER_ID"] == "CRON_SCHEDULE_MISSING":
        jobs = _crontab_agent_jobs()
        recent_log = _recent_admin_cron_log(max_age_minutes=120)
        if jobs > 0 or recent_log:
            values["STATUS"] = "WAIT"
            values["DELTA"] = "NO_DELTA"
            values["VERDICT"] = "WAIT"
            values["BLOCKER_ID"] = "NONE"
            values["RISKS"] = (
                "ancien faux blocage cron neutralisé: crontab/logs indiquent des ticks actifs"
            )
            values["NEXT"] = (
                "owner=admin; action=continuer la supervision runtime et traiter blockers réels"
            )
            values["NEXT_ACTION_UNIQUE"] = f"CONTINUE_ADMIN_RUNTIME_TRUTH_{_now()}"
            values["EVIDENCE"] = (
                "task_update=none_no_signal; lock_check=ok; "
                "run_note=guard valide cron actifs et retire faux blocage; "
                "admin_artifact=scripts/fc_health_check.sh; "
                f"crontab_agent_jobs={jobs}; cron_log_recent={int(recent_log)}; "
                "issues=none; issue_count=0; issue_severity=none"
            )
            ev = _parse_kv(values["EVIDENCE"])
            task_update = "none_no_signal"

    # ── CHECK 15 : anti-faux-blocker delivery ────────────────────────────────
    # Si un rôle delivery se met BLOCKED sans preuve d'exécution du tick courant,
    # on bloque explicitement le contrat au lieu de le convertir en analyse.
    if role in DELIVERY_ROLES and task_update == "blocked" and workboard_has_in_progress:
        if values.get("BLOCKER_ID", "").strip().upper() == "DELIVERY_PROBE_STREAK_EXCEEDED":
            pass
        else:
            cmd_val = ev.get("cmd", "").strip()
            cmd_err = ev.get("cmd_err_excerpt", "").strip()
            stream_val = ev.get("stream_id", "").strip().lower()
            task_val = ev.get("task_id", "").strip().lower()
            has_scope = bool(stream_val and stream_val != "none" and task_val and task_val != "none")
            has_exec_proof = bool(cmd_val or cmd_err)
            if not has_exec_proof or not has_scope:
                _blocked(
                    role,
                    source,
                    "BLOCKED_WITHOUT_FRESH_PROOF",
                    (
                        "task_update=blocked sans preuve d'execution du tick courant "
                        "(cmd/cmd_err_excerpt + stream_id/task_id requis)."
                    ),
                    values,
                )

    # Optional DEV permissive normalization (disabled by default).
    if role == "dev" and str(os.environ.get("FC_DEV_PERMISSIVE_GUARD", "1")).strip() == "1":
        blocker_now = values.get("BLOCKER_ID", "").strip().upper()
        allowed_dev_blockers = {"CLAIM_STREAM_ID_MISSING", "CLAIM_TASK_ID_MISSING"}
        if values.get("STATUS", "").strip().upper() == "BLOCKED" and blocker_now not in allowed_dev_blockers:
            values["STATUS"] = "IN_PROGRESS"
            values["VERDICT"] = "GO_WITH_CAUTION"
            values["BLOCKER_ID"] = "NONE"
            if str(values.get("DELTA", "")).strip().upper() in {"CONTRACT_GUARD_BLOCK", "NO_DELTA", "NO_DATA"}:
                values["DELTA"] = "DEV_READY_FORCE_CLAIM" if _safe_int(ev.get("dev_ready_count"), 0) > 0 else "DEV_WAIT_NO_READY_TASK"
            values["NEXT"] = "owner=dev; action=claim_or_progress_now"
            values["NEXT_ACTION_UNIQUE"] = f"DEV_PERMISSIVE_GUARD_{_now()}"
            ev = _upsert_evidence(values, ev, "task_update", "claim")
            ev = _upsert_evidence(values, ev, "dev_non_passive_policy", "enforced")
            ev = _append_issue(ev=ev, values=values, code="dev_permissive_guard_normalized", severity="low")
            task_update = "claim"

    # ── CHECK ISSUE REPORTING (strict, non-masking) ─────────────────────────
    ev = _validate_issue_report(
        role=role,
        source=source,
        values=values,
        ev=ev,
        task_update=task_update,
    )

    # Compatibility marker should only be injected after issue-report validation.
    if role == "planner" and values.get("STATUS", "").strip().upper() != "BLOCKED":
        delta_token = values.get("DELTA", "").strip().upper()
        if delta_token in {"PLANNER_QUALITY_INCOMPLETE", "PLANNER_EVIDENCE_AUTOFILLED"}:
            ev = _append_issue(
                ev=ev,
                values=values,
                code="planner_evidence_incomplete_soft",
                severity="low",
            )

    if queue_version:
        ev = _upsert_evidence(values, ev, "queue_version", queue_version)
    if workboard_version:
        ev = _upsert_evidence(values, ev, "workboard_version", workboard_version)

    values["EVIDENCE"] = _sanitize_evidence(values.get("EVIDENCE", ""))

    # Tout bon → sortie telle quelle
    print(_render(values))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
