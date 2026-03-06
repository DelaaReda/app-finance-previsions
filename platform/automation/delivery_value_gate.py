#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

CONTRACT_KEYS = ["STATUS", "DELTA", "EVIDENCE", "RISKS", "NEXT", "VERDICT", "BLOCKER_ID", "NEXT_ACTION_UNIQUE"]
PLACEHOLDERS = {"", "none", "n/a", "null", "-", "?", "??", "???", "tbd", "todo", "fixme"}
ARTIFACT_KEYS = {
    "planner": "planner_artifact",
    "dev": "dev_artifact",
    "admin": "admin_artifact",
    "scrum_master": "scrum_artifact",
}
STRICT_DELIVERY_ROLES = {"dev", "admin"}


@dataclass
class GateConfig:
    role: str
    source: str
    history_path: Path
    burst_window_seconds: int = 300
    burst_threshold: int = 3


@dataclass
class GateResult:
    passed: bool
    values: dict[str, str]
    missing: list[str]
    inflation_detected: bool


def _parse_contract(text: str) -> dict[str, str]:
    values = {key: "" for key in CONTRACT_KEYS}
    for raw in text.splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().upper()
        if key in values and not values[key]:
            values[key] = value.strip()
    return values


def _render_contract(values: dict[str, str]) -> str:
    return "\n".join(f"{key}: {values.get(key, ).strip()}" for key in CONTRACT_KEYS) + "\n"


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


def _upsert_evidence(raw: str, key: str, value: str) -> str:
    pairs = _parse_evidence(raw)
    pairs[key.strip().lower()] = value
    preferred = ["task_update", "lock_check", "run_note", "issues", "issue_count", "issue_severity"]
    parts: list[str] = []
    seen: set[str] = set()
    for item in preferred:
        if item in pairs:
            parts.append(f"{item}={pairs[item]}")
            seen.add(item)
    for item in sorted(pairs.keys()):
        if item in seen:
            continue
        parts.append(f"{item}={pairs[item]}")
    return "; ".join(parts)


def _append_issue(raw: str, code: str, severity: str = "low") -> str:
    pairs = _parse_evidence(raw)
    issues_raw = (pairs.get("issues", "") or "").strip().lower()
    if issues_raw in {"", "none"}:
        issue_codes: list[str] = []
    else:
        issue_codes = [token.strip().lower() for token in issues_raw.split(",") if token.strip()]
    if code not in issue_codes:
        issue_codes.append(code)
    sev_rank = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    current = (pairs.get("issue_severity", "none") or "none").strip().lower()
    desired = severity if severity in sev_rank else "low"
    if sev_rank.get(current, 0) < sev_rank[desired]:
        pairs["issue_severity"] = desired
    else:
        pairs["issue_severity"] = current if current in sev_rank else desired
    pairs["issues"] = ",".join(issue_codes) if issue_codes else "none"
    pairs["issue_count"] = str(len(issue_codes))
    preferred = ["task_update", "lock_check", "run_note", "issues", "issue_count", "issue_severity"]
    parts: list[str] = []
    seen: set[str] = set()
    for item in preferred:
        if item in pairs:
            parts.append(f"{item}={pairs[item]}")
            seen.add(item)
    for item in sorted(pairs.keys()):
        if item in seen:
            continue
        parts.append(f"{item}={pairs[item]}")
    return "; ".join(parts)


def _is_placeholder(raw: str) -> bool:
    token = re.sub(r"\s+", "", (raw or "").strip().lower())
    return token in PLACEHOLDERS or bool(re.fullmatch(r"[?.!_~\-]+", token))


def _commit_sha_valid(raw: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", (raw or "").strip().lower()))


def _verify_valid(raw: str) -> bool:
    text = (raw or "").strip().lower()
    if _is_placeholder(text):
        return False
    return any(marker in text for marker in ("before=", "after=", "test=", "proof="))


def _artifact_value(role: str, ev: dict[str, str]) -> str:
    artifact_key = ARTIFACT_KEYS.get(role, "artifact")
    return str(ev.get(artifact_key) or ev.get("artifact") or "").strip()


def _is_doc_only(ev: dict[str, str]) -> bool:
    tests_run = str(ev.get("tests_run", "") or "").strip().lower()
    cmd = str(ev.get("cmd", "") or "").strip().lower()
    return tests_run.startswith("skip(doc_only") or cmd.startswith("skip(doc_only") or cmd.startswith("skip(planner_doc_only")


def _load_history(path: Path) -> list[dict[str, str | int]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def _save_history(path: Path, history: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history[-40:], indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def evaluate_contract(text: str, config: GateConfig, now_epoch: int | None = None) -> GateResult:
    now_epoch = int(now_epoch or time.time())
    values = _parse_contract(text)
    ev = _parse_evidence(values.get("EVIDENCE", ""))
    task_update = str(ev.get("task_update", "") or "").strip().lower()
    if task_update != "complete":
        return GateResult(True, values, [], False)

    missing: list[str] = []
    for field in ("root_cause", "fix_applied", "tests_run", "files_touched", "architecture_check", "vision_alignment"):
        if _is_placeholder(ev.get(field, "")):
            missing.append(field)
    if not _verify_valid(ev.get("verify", "")):
        missing.append("verify")
    if _is_placeholder(_artifact_value(config.role, ev)):
        missing.append("artifact")
    if config.role in STRICT_DELIVERY_ROLES and not _is_doc_only(ev):
        if not _commit_sha_valid(ev.get("commit_sha", "")):
            missing.append("commit_sha")

    history = _load_history(config.history_path)
    history.append(
        {
            "at": now_epoch,
            "role": config.role,
            "source": config.source,
            "task_update": task_update,
            "passed": 1 if not missing else 0,
            "fingerprint": hashlib.sha1(values.get("NEXT_ACTION_UNIQUE", "").encode("utf-8", "ignore")).hexdigest()[:12],
        }
    )
    window_start = now_epoch - config.burst_window_seconds
    recent_failures = [entry for entry in history if int(entry.get("at", 0)) >= window_start and int(entry.get("passed", 0)) == 0]
    inflation_detected = len(recent_failures) >= config.burst_threshold and bool(missing)
    _save_history(config.history_path, history)

    evidence = values.get("EVIDENCE", "")
    if missing:
        evidence = _upsert_evidence(evidence, "delivery_gate", "blocked")
        evidence = _upsert_evidence(evidence, "delivery_gate_missing", ",".join(sorted(set(missing))))
        evidence = _append_issue(evidence, "delivery_value_insufficient", severity="high")
        if inflation_detected:
            evidence = _append_issue(evidence, "delivery_signal_inflation_detected", severity="high")
        values["EVIDENCE"] = evidence
        values["STATUS"] = "BLOCKED"
        values["DELTA"] = "DELIVERY_VALUE_INSUFFICIENT"
        values["VERDICT"] = "BLOCKED"
        values["BLOCKER_ID"] = "DELIVERY_VALUE_INSUFFICIENT"
        values["RISKS"] = "delivery evidence incomplete: " + ",".join(sorted(set(missing)))
        values["NEXT"] = f"owner={config.role}; action=add missing delivery proof then retry complete"
        values["NEXT_ACTION_UNIQUE"] = f"DELIVERY_VALUE_RETRY_{config.role.upper()}_{now_epoch}"
        return GateResult(False, values, sorted(set(missing)), inflation_detected)

    evidence = _upsert_evidence(evidence, "delivery_gate", "pass")
    values["EVIDENCE"] = evidence
    return GateResult(True, values, [], False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delivery value gate for completion contracts")
    parser.add_argument("--role", required=True)
    parser.add_argument("--source", default="unknown")
    parser.add_argument("--history", default=str(Path.home() / ".openclaw" / "cron" / "role-state" / "delivery_value_gate_history.json"))
    parser.add_argument("--contract-file", default="")
    parser.add_argument("--burst-window-seconds", type=int, default=300)
    parser.add_argument("--burst-threshold", type=int, default=3)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.contract_file:
        text = Path(args.contract_file).read_text(encoding="utf-8", errors="ignore")
    else:
        text = sys.stdin.read()
    result = evaluate_contract(
        text,
        GateConfig(
            role=str(args.role).strip().lower(),
            source=str(args.source).strip() or "unknown",
            history_path=Path(args.history).expanduser().resolve(),
            burst_window_seconds=max(60, int(args.burst_window_seconds)),
            burst_threshold=max(2, int(args.burst_threshold)),
        ),
    )
    sys.stdout.write(_render_contract(result.values))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
