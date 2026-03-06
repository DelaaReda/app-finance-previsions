#!/usr/bin/env python3
"""Publish normalized per-role execution monitoring artifacts."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_KEYS = {
    "STATUS",
    "DELTA",
    "EVIDENCE",
    "RISKS",
    "NEXT",
    "VERDICT",
    "BLOCKER_ID",
    "NEXT_ACTION_UNIQUE",
}

DEFAULT_QUEUE_FILE = Path(os.environ.get("EXEC_MONITOR_QUEUE_FILE", "docs/orchestrator-ops/priority-queue.json"))
DEFAULT_WORKBOARD_FILE = Path(
    os.environ.get("EXEC_MONITOR_WORKBOARD_FILE", "docs/orchestrator-ops/parallel-workstreams.json")
)
ISSUE_CODE_RE = re.compile(r"^[a-z0-9_]{3,64}$")
ISSUE_SEVERITIES = {"none", "low", "medium", "high", "critical"}
ISSUE_BLOCKED_MIN_SEVERITIES = {"medium", "high", "critical"}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def one_line(value: str, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[:limit]
    return text


def none_like(value: str) -> bool:
    token = re.sub(r"[\s_/\-]+", "", str(value or "").strip().lower())
    return token in {"", "none", "na", "null"}


def source_version(prefix: str, path: Path) -> str:
    try:
        stat = path.stat()
        digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
        return f"{prefix}_{int(stat.st_mtime)}_{digest}"
    except Exception:
        return ""


def stale_context_record(record: dict[str, str], queue_version: str, workboard_version: str) -> bool:
    record_queue = str(record.get("queue_version", "")).strip()
    record_workboard = str(record.get("workboard_version", "")).strip()
    queue_mismatch = bool(queue_version and record_queue and record_queue != queue_version)
    workboard_mismatch = bool(workboard_version and record_workboard and record_workboard != workboard_version)
    return queue_mismatch or workboard_mismatch


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


def parse_evidence_kv(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for fragment in raw.split(";"):
        if "=" not in fragment:
            continue
        key, value = fragment.split("=", 1)
        key_norm = key.strip().lower()
        if not key_norm or key_norm in out:
            continue
        out[key_norm] = value.strip()
    return out


def _safe_int(raw: str, default: int = 0) -> int:
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def normalize_issue_reporting(
    evidence_kv: dict[str, str], *, blocker_id: str = "", task_update: str = ""
) -> dict[str, object]:
    missing: list[str] = []
    errors: list[str] = []

    for key in ("issues", "issue_count", "issue_severity"):
        if key not in evidence_kv:
            missing.append(key)

    issues_raw = (evidence_kv.get("issues", "none") or "none").strip()
    issue_count_raw = (evidence_kv.get("issue_count", "0") or "0").strip()
    issue_severity = (evidence_kv.get("issue_severity", "none") or "none").strip().lower()

    issue_codes: list[str] = []
    invalid_codes: list[str] = []
    issues_is_none = issues_raw.lower() == "none"
    if not issues_is_none:
        for token in issues_raw.split(","):
            code = token.strip().lower()
            if not code:
                continue
            if ISSUE_CODE_RE.fullmatch(code):
                issue_codes.append(code)
            else:
                invalid_codes.append(code)
        if invalid_codes:
            errors.append("invalid_codes")
        if not issue_codes:
            errors.append("no_valid_issue_code")
            issue_codes = ["issue_report_invalid"]

    if not re.fullmatch(r"\d+", issue_count_raw):
        errors.append("issue_count_invalid")
    issue_count = _safe_int(issue_count_raw, 0)

    if issue_severity not in ISSUE_SEVERITIES:
        errors.append("issue_severity_invalid")

    if issues_is_none:
        if issue_count != 0 or issue_severity != "none":
            errors.append("none_inconsistent")
    else:
        if issue_count <= 0:
            errors.append("count_non_positive")
        if issue_count != len(issue_codes):
            errors.append("count_mismatch")
        if issue_severity == "none":
            errors.append("severity_none_with_issues")

    blocker_present = not none_like(blocker_id)
    if task_update == "blocked" or blocker_present:
        if issues_is_none or issue_count < 1 or issue_severity not in ISSUE_BLOCKED_MIN_SEVERITIES:
            errors.append("blocked_without_issue_report")

    if issues_is_none:
        issues_norm = "none"
        issue_codes = []
        issue_count = 0
        issue_severity = "none" if issue_severity in ISSUE_SEVERITIES else "none"
    else:
        issues_norm = ",".join(issue_codes)
        if issue_count <= 0:
            issue_count = len(issue_codes)
        if issue_severity not in ISSUE_SEVERITIES:
            issue_severity = "medium"

    issue_reporting_ok = (not missing) and (not errors)
    return {
        "issues": one_line(issues_norm or "none"),
        "issue_count": int(issue_count),
        "issue_severity": issue_severity,
        "issue_codes": issue_codes,
        "issue_reporting_ok": issue_reporting_ok,
        "issue_reporting_errors": sorted(set(missing + errors)),
    }


def build_record(role: str, source: str, values: dict[str, str], evidence_kv: dict[str, str]) -> dict[str, object]:
    ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    task_update = one_line(evidence_kv.get("task_update", "none_no_signal") or "none_no_signal")
    issue_report = normalize_issue_reporting(
        evidence_kv,
        blocker_id=values.get("BLOCKER_ID", ""),
        task_update=task_update.lower(),
    )
    return {
        "ts_utc": ts_utc,
        "role": role,
        "source": source,
        "status": one_line(values.get("STATUS", "")),
        "delta": one_line(values.get("DELTA", "")),
        "verdict": one_line(values.get("VERDICT", "")),
        "blocker_id": one_line(values.get("BLOCKER_ID", "")),
        "next_action_unique": one_line(values.get("NEXT_ACTION_UNIQUE", "")),
        "next": one_line(values.get("NEXT", ""), 420),
        "task_update": task_update,
        "exec_report": one_line(evidence_kv.get("exec_report", "none") or "none"),
        "issues": str(issue_report.get("issues", "none")),
        "issue_count": int(issue_report.get("issue_count", 0)),
        "issue_severity": str(issue_report.get("issue_severity", "none")),
        "issue_codes": issue_report.get("issue_codes", []),
        "issue_reporting_ok": bool(issue_report.get("issue_reporting_ok", False)),
        "issue_reporting_errors": issue_report.get("issue_reporting_errors", []),
        "suggestions": one_line(evidence_kv.get("suggestions", "none") or "none"),
        "stream_id": one_line(evidence_kv.get("stream_id", "none") or "none"),
        "task_id": one_line(evidence_kv.get("task_id", "none") or "none"),
        "tool_request": one_line(evidence_kv.get("tool_request", "none") or "none"),
        "skill_request": one_line(evidence_kv.get("skill_request", "none") or "none"),
        "tools_used": one_line(evidence_kv.get("tools_used", ""), 420),
        "channels_read": one_line(evidence_kv.get("channels_read", ""), 200),
        "impact_assessment": one_line(evidence_kv.get("impact_assessment", ""), 120),
        "impact_action": one_line(evidence_kv.get("impact_action", ""), 220),
        "queue_version": one_line(evidence_kv.get("queue_version", ""), 120),
        "workboard_version": one_line(evidence_kv.get("workboard_version", ""), 120),
    }


def update_latest(latest_path: Path, role: str, record: dict[str, str]) -> None:
    latest: dict[str, object] = {}
    if latest_path.exists():
        try:
            loaded = json.loads(read_text(latest_path))
            if isinstance(loaded, dict):
                latest = loaded
        except Exception:
            latest = {}
    roles = latest.get("roles")
    if not isinstance(roles, dict):
        roles = {}
    roles[role] = record
    latest["roles"] = roles
    latest["updated_at_utc"] = record["ts_utc"]

    queue_version = source_version("queue", DEFAULT_QUEUE_FILE)
    workboard_version = source_version("workboard", DEFAULT_WORKBOARD_FILE)
    stale_context_roles = sorted(
        name
        for name, data in roles.items()
        if isinstance(data, dict) and stale_context_record(data, queue_version, workboard_version)
    )
    stale_context_set = set(stale_context_roles)
    active_roles = {
        name: data for name, data in roles.items() if isinstance(data, dict) and name not in stale_context_set
    }

    process_issue_re = re.compile(
        r"permission_denied|tmux_reply_unparseable|unparseable|channels_probe_.*permission_denied|publicat.*channels.*none|no_usable_tmpdir|tmpdir|role_contract_errors|exec_report_missing|issues_summary_missing|suggestions_summary_missing|delivery_target_missing|model_not_allowed|thinking_not_max",
        re.I,
    )
    flow_gap_re = re.compile(
        r"no_slot|absence_slot|slot_.*absent|queue_ready_not_dispatched",
        re.I,
    )

    issue_roles = sorted(
        name for name, data in active_roles.items() if int(data.get("issue_count", 0) or 0) > 0
    )
    issue_reporting_missing_roles = sorted(
        name for name, data in active_roles.items() if not bool(data.get("issue_reporting_ok", False))
    )
    critical_issue_roles = sorted(
        name
        for name, data in active_roles.items()
        if str(data.get("issue_severity", "")).strip().lower() == "critical"
    )
    process_issue_roles = sorted(
        name
        for name, data in active_roles.items()
        if int(data.get("issue_count", 0) or 0) > 0
        and process_issue_re.search(str(data.get("issues", "")) or "")
    )
    flow_gap_roles = sorted(
        name
        for name, data in active_roles.items()
        if int(data.get("issue_count", 0) or 0) > 0
        and flow_gap_re.search(str(data.get("issues", "")) or "")
    )
    delivery_probe_roles = sorted(
        name
        for name, data in active_roles.items()
        if "DELIVERY_PROBE_INCONSISTENT_CONTINUE" in str(data.get("delta", "")).upper()
    )

    process_issue_roles = sorted(set(process_issue_roles + delivery_probe_roles))
    delivery_gap_roles = sorted([r for r in issue_roles if r not in set(process_issue_roles)])
    blocker_roles = sorted(
        name for name, data in active_roles.items() if not none_like(str(data.get("blocker_id", "")))
    )
    request_roles = sorted(
        name
        for name, data in active_roles.items()
        if (
            not none_like(str(data.get("tool_request", "")))
            or not none_like(str(data.get("skill_request", "")))
        )
    )
    latest["summary"] = {
        "roles_total": len(roles),
        "fresh_roles_total": len(active_roles),
        "stale_context_open": len(stale_context_roles),
        "issues_open": len(issue_roles),
        "issue_reports_open": len(issue_roles),
        "issue_reporting_missing_count": len(issue_reporting_missing_roles),
        "issue_reporting_missing_roles": issue_reporting_missing_roles[:8],
        "critical_count": len(critical_issue_roles),
        "critical_issue_roles": critical_issue_roles[:8],
        "process_issues_open": len(process_issue_roles),
        "delivery_gaps_open": len(delivery_gap_roles),
        "delivery_probe_loops_open": len(delivery_probe_roles),
        "flow_gaps_open": len(flow_gap_roles),
        "blockers_open": len(blocker_roles),
        "tool_skill_requests_open": len(request_roles),
        "issue_roles": issue_roles[:8],
        "process_issue_roles": process_issue_roles[:8],
        "delivery_probe_roles": delivery_probe_roles[:8],
        "flow_gap_roles": flow_gap_roles[:8],
        "delivery_gap_roles": delivery_gap_roles[:8],
        "blocker_roles": blocker_roles[:8],
        "tool_skill_request_roles": request_roles[:8],
        "stale_context_roles": stale_context_roles[:8],
        "context_versions": {
            "queue_version": queue_version or "unknown",
            "workboard_version": workboard_version or "unknown",
        },
    }
    latest_path.write_text(json.dumps(latest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def append_tool_request(
    role: str,
    source: str,
    record: dict[str, str],
    tool_md_path: Path,
    tool_events_path: Path,
    state_dir: Path,
) -> None:
    has_tool_request = not none_like(record.get("tool_request", ""))
    has_skill_request = not none_like(record.get("skill_request", ""))
    if not (has_tool_request or has_skill_request):
        return

    if not tool_md_path.exists():
        tool_md_path.write_text(
            "# Agent Tool/Skill Requests\n\n"
            "- Auto-generated requests from role contracts (`EVIDENCE`).\n"
            "- Format: `[ts] [role] tool_request=...; skill_request=...; stream_id=...; task_id=...; source=...`\n\n",
            encoding="utf-8",
        )

    fp_input = "|".join(
        [
            role,
            str(record.get("tool_request", "")),
            str(record.get("skill_request", "")),
            str(record.get("stream_id", "")),
            str(record.get("task_id", "")),
            str(record.get("issues", "")),
        ]
    )
    fingerprint = hashlib.sha256(fp_input.encode("utf-8")).hexdigest()
    fp_file = state_dir / f"{role}.last_tool_request_fingerprint"
    previous_fp = read_text(fp_file).strip()
    if fingerprint == previous_fp:
        return

    line = (
        f"- [{record['ts_utc']}] [{role}] "
        f"tool_request={record.get('tool_request') or 'none'}; "
        f"skill_request={record.get('skill_request') or 'none'}; "
        f"stream_id={record.get('stream_id') or 'none'}; "
        f"task_id={record.get('task_id') or 'none'}; "
        f"source={source}; "
        f"issues={record.get('issues') or 'none'}; "
        f"suggestion={record.get('suggestions') or 'none'}.\n"
    )
    with tool_md_path.open("a", encoding="utf-8") as md_file:
        md_file.write(line)
    with tool_events_path.open("a", encoding="utf-8") as events_file:
        events_file.write(json.dumps(record, ensure_ascii=True) + "\n")
    fp_file.write_text(fingerprint + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 9:
        print(
            "usage: role_execution_monitoring.py <role> <source> <payload_file> <latest_file> <events_file> <tool_md_file> <tool_events_file> <state_dir>",
            file=sys.stderr,
        )
        return 2

    role = sys.argv[1]
    source = sys.argv[2]
    payload_path = Path(sys.argv[3])
    latest_path = Path(sys.argv[4])
    events_path = Path(sys.argv[5])
    tool_md_path = Path(sys.argv[6])
    tool_events_path = Path(sys.argv[7])
    state_dir = Path(sys.argv[8])

    text = read_text(payload_path)
    values = parse_contract(text)
    evidence_kv = parse_evidence_kv(values.get("EVIDENCE", ""))
    record = build_record(role, source, values, evidence_kv)

    state_dir.mkdir(parents=True, exist_ok=True)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    tool_md_path.parent.mkdir(parents=True, exist_ok=True)
    tool_events_path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = state_dir / "executor-monitoring.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        with events_path.open("a", encoding="utf-8") as events_fh:
            events_fh.write(json.dumps(record, ensure_ascii=True) + "\n")
        update_latest(latest_path, role, record)
        append_tool_request(role, source, record, tool_md_path, tool_events_path, state_dir)
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
