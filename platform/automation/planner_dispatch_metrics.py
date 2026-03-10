#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path


ACTIVE_STATUSES = {"spawned", "running"}
SUCCESS_STATUSES = {"completed", "merged", "done", "pass", "ok", "success"}
BLOCKED_STATUSES = {"blocked"}
DONE_STATES = {"done", "closed"}
FALLBACK_MARKERS = ("falling back to embedded", "failovererror", "gateway agent failed")
INVALID_RESULT_MARKERS = (
    "invalid_subagent_result",
    "subagent_invalid_result",
    "start_banner_only",
    "empty_payload",
    "delivery_evidence_incomplete",
    "missing bearer or basic authentication",
    "401 unauthorized",
    "unexpected status 401 unauthorized",
    "transport channel",
    "worker quit with fatal",
    "failed to refresh available models",
    "openai codex v0.",
    "research preview",
    "session id:",
)
TIMEOUT_LIKE_MARKERS = ("timeout", "timed out", "stale_no_result", "deadline", "no result")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_iso(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _recent_sort_key(item: dict[str, Any]) -> float:
    for key in ("last_update_at", "merged_at", "finished_at", "created_at"):
        dt = _parse_iso(item.get(key))
        if dt is not None:
            return dt.timestamp()
    return 0.0


def _is_fallback_like(root: Path, subagent_id: str) -> bool:
    raw_path = resolve_orchestrator_read_path(root, f"planner-subagents-results/{subagent_id}.raw.txt")
    raw_text = _read_text(raw_path).lower()
    return any(marker in raw_text for marker in FALLBACK_MARKERS)


def _failure_mode(item: dict[str, Any]) -> str:
    token = " | ".join(
        [
            str(item.get("blocking_issue", "")),
            str(item.get("summary", "")),
        ]
    ).strip().lower()
    if any(marker in token for marker in INVALID_RESULT_MARKERS):
        return "invalid_result"
    if any(marker in token for marker in TIMEOUT_LIKE_MARKERS):
        return "timeout"
    return "other" if token else "unknown"


def _delivery_delta(item: dict[str, Any]) -> str:
    artifact = str(item.get("artifact", "")).strip().lower()
    if artifact and artifact not in {"none", "n/a", "na"}:
        return "artifact_delta"
    files_touched = str(item.get("files_touched", "")).strip().lower()
    if files_touched and files_touched not in {"none", "n/a", "na"}:
        return "code_delta"
    tests_run = str(item.get("tests_run", "")).strip().lower()
    if tests_run and tests_run not in {"none", "n/a", "na", "skip(no_tests)", "skip(no_code_runtime_fix)"}:
        return "test_delta"
    verify = str(item.get("verify", "")).strip().lower()
    if verify and verify not in {"none", "n/a", "na"}:
        return "verify_delta"
    summary = str(item.get("summary", "")).strip().lower()
    if "contract_snapshot" in summary:
        return "contract_snapshot"
    return "none"


def build_planner_dispatch_metrics(root: Path, *, recent_limit: int = 12) -> dict[str, Any]:
    registry_path = resolve_orchestrator_read_path(root, "planner-subagents-registry.json")
    payload = _read_json(registry_path) if registry_path.exists() else {}
    rows = payload.get("subagents", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
    text = "" if summary is None else str(summary)
    lowered = text.strip().lower()
    if not lowered:
        return None
    if "contract_snapshot" in lowered or "bridge_result" in lowered or lowered.startswith("noop:"):
        return None
    token_markers = (
        ("artifact_delta", ("artifact_delta", "artifact delta", "artifact:", "artifact/", "evidence/", "proof published")),
        ("code_delta", ("code_delta", "code delta", "patch", "diff", "changed file", "files changed", "wrote ")),
        ("test_delta", ("test_delta", "test delta", "pytest", "unit test", "integration test", "tests passed", "test pass")),
        ("verify_delta", ("verify_delta", "verify delta", "verified", "verification", "validated", "verdict: pass", "gate pass")),
    )
    for label, markers in token_markers:
        if any(marker in lowered for marker in markers):
            return label
    return None

