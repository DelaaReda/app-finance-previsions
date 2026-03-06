#!/usr/bin/env python3
"""Publish per-iteration structured issue records for role runners."""

from __future__ import annotations

import fcntl
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


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

SEVERITY_ORDER = {"INFO": 0, "WARN": 1, "ERROR": 2, "CRITICAL": 3}
SEVERITY_NAMES = ["INFO", "WARN", "ERROR", "CRITICAL"]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def parse_contract(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        match = re.match(r"^\s*([A-Z_]+)\s*:\s*(.*)$", raw.strip())
        if not match:
            continue
        key = match.group(1).upper()
        if key in CONTRACT_KEYS and key not in values:
            values[key] = match.group(2).strip()
    return values


def parse_evidence(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in (raw or "").split(";"):
        seg = part.strip()
        if not seg or "=" not in seg:
            continue
        key, value = seg.split("=", 1)
        key_norm = key.strip().lower()
        if key_norm and key_norm not in out:
            out[key_norm] = value.strip()
    return out


def one_line(value: Any, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[:limit]
    return text


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def parse_ts_utc(raw: str) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _severity_to_impact(severity: str, issue_count: int = 1) -> str:
    sev = str(severity or "WARN").upper()
    if sev == "CRITICAL":
        return "critical"
    if sev == "ERROR":
        return "high" if issue_count > 1 else "medium"
    if sev == "WARN":
        return "medium"
    return "low"


def _category_for_code(code: str) -> str:
    up = str(code or "").upper()
    if up.startswith("TIMEOUT_"):
        return "RUNTIME_TIMEOUT"
    if up.startswith("SESSION_NOT_READY_"):
        return "RUNTIME_SESSION"
    if up.startswith("REASONING_VARIANT"):
        return "CONFIG_VALIDATION"
    if up.startswith("BROKEN_PIPE"):
        return "RUNTIME_IO"
    if up.startswith("RATE_LIMIT_PROBE"):
        return "QUOTA"
    if up.startswith("CHECKPOINT_FALLBACK"):
        return "CONTROL_FLOW"
    if up.startswith("PERMISSION_"):
        return "PERMISSIONS"
    if up.startswith("CONTRACT_PARSE"):
        return "CONTRACT"
    return "RUNTIME"


def _error_type_for_code(code: str) -> str:
    up = str(code or "").lower()
    if "timeout" in up:
        return "timeout"
    if "session" in up:
        return "session"
    if "pipe" in up:
        return "broken_pipe"
    if "rate_limit" in up:
        return "rate_limit"
    if "reasoning" in up:
        return "reasoning_variant"
    if "parse" in up:
        return "contract_parse"
    if "fallback" in up:
        return "checkpoint_fallback"
    if "permission" in up:
        return "permission"
    return "runtime"


def issue(
    code: str,
    severity: str,
    symptom: str,
    root_cause: str,
    action_taken: str,
    recoverable: bool,
    issue_ts: str = "",
    source: str = "unknown",
    blocker: bool = False,
    impact: str = "",
    category: str = "",
    error_type: str = "",
    level: str = "",
) -> dict[str, Any]:
    sev = severity.upper()
    if sev not in SEVERITY_ORDER:
        sev = "WARN"
    if not level:
        level = "ERROR" if sev in {"ERROR", "CRITICAL"} else "WARN" if sev == "WARN" else "INFO"
    level = str(level or "").strip().upper()
    if level not in {"ERROR", "WARN", "INFO", "ACTION"}:
        level = "INFO"
    impact = str(impact or _severity_to_impact(sev, 1)).strip().lower()
    if impact not in {"low", "medium", "high", "critical"}:
        impact = "medium"
    issue_ts = str(issue_ts or "").strip()
    if issue_ts:
        parsed_ts = parse_ts_utc(issue_ts)
        if parsed_ts is None:
            issue_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            issue_ts = parsed_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        issue_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    category = str(category or _category_for_code(code)).upper()
    error_type = str(error_type or _error_type_for_code(code)).lower()
    return {
        "code": code,
        "severity": sev,
        "symptom": one_line(symptom, 220),
        "root_cause": one_line(root_cause, 220),
        "action_taken": one_line(action_taken, 240),
        "recoverable": bool(recoverable),
        "category": category,
        "source": one_line(source, 80) or "unknown",
        "ts": issue_ts,
        "blocker": bool(blocker),
        "impact": impact,
        "level": level,
        "error_type": error_type,
    }


def maybe_add_issue(
    items: list[dict[str, Any]],
    code: str,
    severity: str,
    symptom: str,
    root_cause: str,
    action_taken: str,
    recoverable: bool,
    issue_ts: str = "",
    source: str = "unknown",
    blocker: bool = False,
    impact: str = "",
    category: str = "",
    error_type: str = "",
    level: str = "",
) -> None:
    if any(existing.get("code") == code for existing in items):
        return
    items.append(
        issue(
            code=code,
            severity=severity,
            symptom=symptom,
            root_cause=root_cause,
            action_taken=action_taken,
            recoverable=recoverable,
            issue_ts=issue_ts,
            source=source,
            blocker=blocker,
            impact=impact,
            category=category,
            error_type=error_type,
            level=level,
        )
    )


def classify_issues(
    tick_id: str,
    source: str,
    evidence: dict[str, str],
    rc_primary: int,
    rc_retry: int,
    rc_final: int,
    rc_codex: int,
    raw_primary: str,
    raw_retry: str,
    raw_codex: str,
    trace_events_text: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issue_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tick_token = str(tick_id or "").strip()
    scoped_trace_lines: list[str] = []
    if trace_events_text:
        lines = [ln for ln in trace_events_text.splitlines() if ln.strip()]
        if tick_token:
            scoped_trace_lines = [ln for ln in lines if tick_token in ln][-80:]
        if not scoped_trace_lines:
            scoped_trace_lines = lines[-40:]
    scoped_trace = "\n".join(scoped_trace_lines)
    meta_text = "\n".join(
        [
            str(source or ""),
            str(evidence.get("issues", "")),
            str(evidence.get("run_note", "")),
            str(evidence.get("fallback_mode", "")),
        ]
    )
    meta_l = meta_text.lower()
    signal_text = "\n".join(
        [
            str(raw_primary or ""),
            str(raw_retry or ""),
            str(raw_codex or ""),
            scoped_trace,
        ]
    )
    signal_l = signal_text.lower()
    rc_values = {rc_primary, rc_retry, rc_final, rc_codex}

    timeout_signal = bool(
        124 in rc_values
        or re.search(r"\brc=124\b", signal_l)
        or re.search(r"\b(timed out|timeout reached|deadline exceeded|command timed out)\b", signal_l)
    )
    if timeout_signal:
        maybe_add_issue(
            issues,
            "TIMEOUT_124",
            "ERROR" if rc_final != 0 else "WARN",
            "Prompt timeout detected (rc=124).",
            "Execution exceeded timeout window for one or more stages.",
            "Retry path/fallback attempted; tune timeout and reduce prompt payload.",
            True,
            issue_ts=issue_ts,
            source=source,
            blocker=rc_final != 0,
            impact="high" if rc_final != 0 else "low",
            category="RUNTIME_TIMEOUT",
            error_type="timeout",
            level="ERROR" if rc_final != 0 else "WARN",
        )

    if 43 in rc_values or "session_not_ready" in signal_l:
        maybe_add_issue(
            issues,
            "SESSION_NOT_READY_43",
            "ERROR" if rc_final != 0 else "WARN",
            "Runner session not ready (rc=43).",
            "tmux/session channel unavailable or not initialized.",
            "Session recovery triggered; ensure session bootstrap before prompt dispatch.",
            True,
            issue_ts=issue_ts,
            source=source,
            blocker=rc_final != 0,
            impact="high" if rc_final != 0 else "medium",
            category="RUNTIME_SESSION",
            error_type="session_not_ready",
            level="ERROR" if rc_final != 0 else "WARN",
        )

    if re.search(r"unknown variant .*model_reasoning_effort|model_reasoning_effort", signal_text, re.I):
        maybe_add_issue(
            issues,
            "REASONING_VARIANT_INVALID",
            "ERROR",
            "Unsupported reasoning effort variant.",
            "Agent/model settings mismatch for model_reasoning_effort.",
            "Clamp reasoning level to supported variants for current model/channel.",
            False,
            issue_ts=issue_ts,
            source=source,
            blocker=True,
            impact="high",
            category="CONFIG_VALIDATION",
            error_type="reasoning_variant",
            level="ERROR",
        )

    if "broken pipe" in signal_l or "write error: broken pipe" in signal_l:
        maybe_add_issue(
            issues,
            "BROKEN_PIPE",
            "ERROR" if rc_final != 0 else "WARN",
            "Broken pipe while streaming prompt/output.",
            "tmux/pipe write channel interrupted during runner execution.",
            "Switch to stable channel fallback and retry with reduced stream payload.",
            True,
            issue_ts=issue_ts,
            source=source,
            blocker=rc_final != 0,
            impact="high" if rc_final != 0 else "medium",
            category="RUNTIME_IO",
            error_type="broken_pipe",
            level="ERROR" if rc_final != 0 else "WARN",
        )

    if "rate_limit_probe_error" in signal_l or "rate_limit_gate" in str(source or "").lower():
        maybe_add_issue(
            issues,
            "RATE_LIMIT_PROBE_ERROR",
            "WARN" if rc_final == 0 else "ERROR",
            "Rate-limit probe or gate triggered.",
            "Provider quota/rate-limit probe failed or temporary backoff engaged.",
            "Apply cooldown, retry later, or route to fallback model.",
            True,
            issue_ts=issue_ts,
            source=source,
            blocker=rc_final != 0,
            impact="high" if rc_final != 0 else "medium",
            category="QUOTA",
            error_type="rate_limit",
            level="ERROR" if rc_final != 0 else "WARN",
        )

    if (
        "checkpoint_fallback" in str(source or "").lower()
        or "fallback_checkpoint" in str(source or "").lower()
        or "fallback_mode=checkpoint" in meta_l
        or "checkpoint_fallback" in signal_l
    ):
        maybe_add_issue(
            issues,
            "CHECKPOINT_FALLBACK",
            "WARN" if rc_final == 0 else "ERROR",
            "Checkpoint fallback output emitted.",
            "Primary/retry/fallback outputs were not exploitable as contract output.",
            "Continue lane with checkpoint contract and investigate raw outputs.",
            True,
            issue_ts=issue_ts,
            source=source,
            blocker=False,
            impact="low" if rc_final == 0 else "medium",
            category="CONTROL_FLOW",
            error_type="checkpoint_fallback",
            level="WARN",
        )

    if re.search(r"operation not permitted|permission denied|cannot create directory", signal_text, re.I):
        maybe_add_issue(
            issues,
            "PERMISSION_OP_NOT_PERMITTED",
            "ERROR",
            "Permission/system operation denied.",
            "Workspace/path permissions prevent required file operations.",
            "Use writable canonical workspace paths and fix directory ownership/mount policy.",
            False,
            issue_ts=issue_ts,
            source=source,
            blocker=True,
            impact="critical",
            category="PERMISSIONS",
            error_type="permission",
            level="ERROR",
        )

    if (
        "signal_unparseable" in meta_l
        or "contract_parse_failed" in meta_l
        or "unparseable" in meta_l
        or "tick_mismatch=" in signal_l
    ):
        maybe_add_issue(
            issues,
            "CONTRACT_PARSE_FAILED",
            "ERROR" if rc_final != 0 else "WARN",
            "Contract normalization/parse failed for runner output.",
            "Output did not match strict contract schema or signal parsing failed.",
            "Fallback/checkpoint contract issued and parser guard retained for next tick.",
            True,
            issue_ts=issue_ts,
            source=source,
            blocker=rc_final != 0,
            impact="high" if rc_final != 0 else "medium",
            category="CONTRACT",
            error_type="contract_parse",
            level="ERROR" if rc_final != 0 else "WARN",
        )

    return issues


def escalate_critical_if_needed(
    events_path: Path,
    role: str,
    now_dt: datetime,
    issues: list[dict[str, Any]],
) -> None:
    if not issues:
        return
    if not events_path.exists():
        return

    window_start = now_dt - timedelta(minutes=60)
    code_counts = Counter()

    for line in read_text(events_path).splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except Exception:
            continue
        if not isinstance(record, dict):
            continue
        if str(record.get("role", "")) != role:
            continue
        if str(record.get("issue_status", "none")) != "has_issues":
            continue
        ts = parse_ts_utc(str(record.get("ts_utc", "")))
        if ts is None or ts < window_start:
            continue
        for item in record.get("issues", []):
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", "")).strip()
            if code:
                code_counts[code] += 1

    for item in issues:
        code = str(item.get("code", "")).strip()
        if not code:
            continue
        if code_counts[code] >= 2:
            item["severity"] = "CRITICAL"


def max_severity(issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "INFO"
    best = "INFO"
    for it in issues:
        sev = str(it.get("severity", "INFO")).upper()
        if SEVERITY_ORDER.get(sev, 0) > SEVERITY_ORDER.get(best, 0):
            best = sev
    return best


def build_record(
    role: str,
    source: str,
    tick_id: str,
    agent_bin: str,
    channel: str,
    contract_text: str,
    evidence: dict[str, str],
    queue_version_arg: str,
    workboard_version_arg: str,
    rc_primary: int,
    rc_retry: int,
    rc_final: int,
    rc_codex: int,
    raw_primary: str,
    raw_retry: str,
    raw_codex: str,
    trace_events_text: str,
    evidence_paths: list[str],
    events_path: Path,
) -> dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    ts_utc = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    values = parse_contract(contract_text)

    issues = classify_issues(
        tick_id=tick_id,
        source=source,
        evidence=evidence,
        rc_primary=rc_primary,
        rc_retry=rc_retry,
        rc_final=rc_final,
        rc_codex=rc_codex,
        raw_primary=raw_primary,
        raw_retry=raw_retry,
        raw_codex=raw_codex,
        trace_events_text=trace_events_text,
    )
    escalate_critical_if_needed(events_path, role, now_dt, issues)

    status = one_line(values.get("STATUS", ""), 120)
    verdict = one_line(values.get("VERDICT", ""), 120)
    issue_state = "has_issues" if issues else "none"
    mx = max_severity(issues)

    next_action = one_line(
        values.get("NEXT_ACTION_UNIQUE", "")
        or evidence.get("next_action_unique", "")
        or values.get("NEXT", ""),
        240,
    )
    if not next_action:
        next_action = "continue_next_tick"

    queue_version = one_line(evidence.get("queue_version", "") or queue_version_arg, 140)
    workboard_version = one_line(evidence.get("workboard_version", "") or workboard_version_arg, 140)

    return {
        "ts_utc": ts_utc,
        "tick_id": one_line(tick_id, 80) or "unknown",
        "role": role,
        "agent_bin": one_line(agent_bin, 60) or "unknown",
        "channel": one_line(channel, 80) or "unknown",
        "source": one_line(source, 120) or "unknown",
        "status": status or "UNKNOWN",
        "verdict": verdict or "UNKNOWN",
        "rc_primary": rc_primary,
        "rc_retry": rc_retry,
        "rc_final": rc_final,
        "issue_status": issue_state,
        "issue_count": len(issues),
        "max_severity": mx,
        "issues": issues,
        "next_action": next_action,
        "evidence_paths": [p for p in evidence_paths if p],
        "queue_version": queue_version,
        "workboard_version": workboard_version,
    }


def update_latest(latest_path: Path, role: str, record: dict[str, Any]) -> None:
    data: dict[str, Any] = {}
    if latest_path.exists():
        try:
            loaded = json.loads(read_text(latest_path))
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}

    roles = data.get("roles")
    if not isinstance(roles, dict):
        roles = {}
    roles[role] = record
    data["roles"] = roles
    data["updated_at_utc"] = record.get("ts_utc", "")

    has_issues_roles = [name for name, rec in roles.items() if isinstance(rec, dict) and rec.get("issue_status") == "has_issues"]
    critical_open = [
        name
        for name, rec in roles.items()
        if isinstance(rec, dict)
        and rec.get("issue_status") == "has_issues"
        and str(rec.get("max_severity", "INFO")).upper() == "CRITICAL"
    ]
    data["summary"] = {
        "roles_total": len(roles),
        "has_issues_roles": sorted(has_issues_roles),
        "critical_open_count": len(critical_open),
    }

    latest_path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 20:
        print(
            (
                "usage: iteration_issue_report.py <role> <source> <payload_file> <latest_file> <events_file> "
                "<state_dir> <tick_id> <agent_bin> <channel> <rc_primary> <rc_retry> <rc_final> <rc_codex> "
                "<raw_primary_file> <raw_retry_file> <raw_codex_file> <trace_events_file> <queue_version> <workboard_version>"
            ),
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1]
    source = sys.argv[2]
    payload_file = Path(sys.argv[3])
    latest_file = Path(sys.argv[4])
    events_file = Path(sys.argv[5])
    state_dir = Path(sys.argv[6])
    tick_id = sys.argv[7]
    agent_bin = sys.argv[8]
    channel = sys.argv[9]
    rc_primary = parse_int(sys.argv[10], 0)
    rc_retry = parse_int(sys.argv[11], 0)
    rc_final = parse_int(sys.argv[12], 0)
    rc_codex = parse_int(sys.argv[13], -1)
    raw_primary_file = Path(sys.argv[14])
    raw_retry_file = Path(sys.argv[15])
    raw_codex_file = Path(sys.argv[16])
    trace_events_file = Path(sys.argv[17])
    queue_version = sys.argv[18]
    workboard_version = sys.argv[19]

    contract_text = read_text(payload_file)
    evidence = parse_evidence(parse_contract(contract_text).get("EVIDENCE", ""))
    raw_primary = read_text(raw_primary_file)
    raw_retry = read_text(raw_retry_file)
    raw_codex = read_text(raw_codex_file)
    trace_events_text = read_text(trace_events_file)
    evidence_paths = [str(payload_file), str(raw_primary_file), str(raw_retry_file), str(raw_codex_file), str(trace_events_file)]

    state_dir.mkdir(parents=True, exist_ok=True)
    latest_file.parent.mkdir(parents=True, exist_ok=True)
    events_file.parent.mkdir(parents=True, exist_ok=True)

    record = build_record(
        role=role,
        source=source,
        tick_id=tick_id,
        agent_bin=agent_bin,
        channel=channel,
        contract_text=contract_text,
        evidence=evidence,
        queue_version_arg=queue_version,
        workboard_version_arg=workboard_version,
        rc_primary=rc_primary,
        rc_retry=rc_retry,
        rc_final=rc_final,
        rc_codex=rc_codex,
        raw_primary=raw_primary,
        raw_retry=raw_retry,
        raw_codex=raw_codex,
        trace_events_text=trace_events_text,
        evidence_paths=evidence_paths,
        events_path=events_file,
    )

    lock_file = state_dir / "iteration-issues.lock"
    with lock_file.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        with events_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        update_latest(latest_file, role, record)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
