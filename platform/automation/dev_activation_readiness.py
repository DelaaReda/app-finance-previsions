#!/usr/bin/env python3
"""Preflight gate before enabling planner-driven development."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from orchestrator_paths import resolve_orchestrator_write_path


DEFAULT_MONITOR_BASE = "http://3.98.20.77:8080"
PLANNER_DISPATCH_SUCCESS_STATUSES = {"complete", "completed", "merged", "done", "pass", "ok", "success"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _probe_json(url: str, *, timeout_s: float) -> tuple[dict[str, Any], str]:
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        return payload if isinstance(payload, dict) else {}, ""
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {}, str(exc)


def _validate_bridge(root: Path, *, timeout_s: int) -> tuple[dict[str, Any], str]:
    cmd = [
        sys.executable,
        str(root / "platform" / "automation" / "operator" / "openclaw" / "openclaw_control_plane.py"),
        "--validate-bridge",
        "--validate-agent",
        "planner",
        "--validate-timeout",
        str(int(timeout_s)),
    ]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=max(int(timeout_s) + 20, 30),
            check=False,
        )
    except Exception as exc:
        return {}, str(exc)
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        return {}, stderr or stdout or f"bridge_validation_rc={completed.returncode}"
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        return {}, f"invalid_bridge_json:{exc}"
    if not isinstance(payload, dict):
        return {}, "invalid_bridge_payload"
    return payload, stderr


def _planner_dispatch_check(planner_dispatch: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    status = str(planner_dispatch.get("status", "unknown") or "unknown").strip().lower()
    latest_status = str(planner_dispatch.get("latest_status", "") or "").strip().lower()
    latest_fallback_like = bool(planner_dispatch.get("latest_fallback_like"))
    if status in {"degraded", "error"}:
        reasons.append(f"planner_dispatch_status={status}")
    if bool(planner_dispatch.get("needs_dispatch")):
        reasons.append("planner_dispatch_needed")
    if bool(planner_dispatch.get("stalled_ready_dev")):
        reasons.append("ready_dev_stalled")
    if int(planner_dispatch.get("recent_failed_count", 0) or 0) > 0 and latest_status not in {"", *PLANNER_DISPATCH_SUCCESS_STATUSES}:
        reasons.append("recent_dispatch_failed")
    if latest_fallback_like:
        reasons.append("recent_dispatch_fallback_like")
    if reasons:
        return "blocked", reasons
    return "ok", []


def _bridge_is_live_via_dispatch(planner_dispatch: dict[str, Any]) -> bool:
    status = str(planner_dispatch.get("status", "unknown") or "unknown").strip().lower()
    active_subagents = int(planner_dispatch.get("active_subagents", 0) or 0)
    latest_fallback_like = bool(planner_dispatch.get("latest_fallback_like"))
    return active_subagents > 0 and status in {"active", "ok"} and not latest_fallback_like


def _priority_guard_check(priority_guard: dict[str, Any]) -> tuple[str, list[str]]:
    status = str(priority_guard.get("status", "unknown") or "unknown").strip().lower()
    reasons = [str(item).strip() for item in priority_guard.get("blocked_reasons", []) if str(item).strip()]
    if status in {"blocked", "error", "degraded"} or reasons:
        return "blocked", reasons or [f"priority_guard_status={status}"]
    return "ok", []


def _recommended_actions(blockers: list[str]) -> list[str]:
    actions: list[str] = []
    if "news_stale" in blockers:
        actions.append("refresh news pipeline via the canonical data-refresh path before enabling development")
    if "planner_dispatch_needed" in blockers or "ready_dev_stalled" in blockers:
        actions.append("clear the stalled READY_DEV backlog by dispatching the first dev capability task before cutover")
    if "planner_dispatch_status=degraded" in blockers or "recent_dispatch_fallback_like" in blockers:
        actions.append("run one clean planner capability dispatch after bridge validation so monitor history is no longer degraded by fallback-like events")
    if "doctor_not_ok" in blockers:
        actions.append("rerun doctor after product freshness and planner dispatch are green")
    if "openclaw_bridge_not_ready" in blockers:
        actions.append("repair OpenClaw/Codex bridge validation before any activation")
    return actions


def build_readiness(
    root: Path,
    *,
    monitor_base_url: str = DEFAULT_MONITOR_BASE,
    timeout_s: float = 8.0,
    validate_bridge: bool = True,
    bridge_timeout_s: int = 45,
) -> dict[str, Any]:
    status_payload, status_error = _probe_json(f"{monitor_base_url.rstrip('/')}/api/status", timeout_s=timeout_s)
    doctor_payload, doctor_error = _probe_json(
        f"{monitor_base_url.rstrip('/')}/api/doctor?refresh=1", timeout_s=max(timeout_s, 12.0)
    )

    checks: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []

    if not status_payload:
        checks["monitor"] = {"status": "blocked", "detail": {"error": status_error or "status_unavailable"}}
        blockers.append("monitor_unavailable")
        readiness = {
            "at": _iso_now(),
            "root": str(root),
            "ready": False,
            "status": "blocked",
            "blockers": blockers,
            "checks": checks,
        }
        return readiness

    runtime_state = status_payload.get("runtime_state", {}) if isinstance(status_payload.get("runtime_state"), dict) else {}
    lifecycle = str(runtime_state.get("lifecycle", "unknown") or "unknown").strip().lower()
    execution_mode = str(status_payload.get("execution_mode", "") or "").strip()
    checks["runtime_mode"] = {
        "status": "ok" if lifecycle == "running" and execution_mode == "planner_experimental" else "blocked",
        "detail": {
            "lifecycle": lifecycle,
            "execution_mode": execution_mode,
        },
    }
    if checks["runtime_mode"]["status"] != "ok":
        blockers.append("runtime_mode_not_ready")

    delivery_integrity = status_payload.get("delivery_integrity", {}) if isinstance(status_payload.get("delivery_integrity"), dict) else {}
    delivery_status = str(delivery_integrity.get("status", "unknown") or "unknown").strip().lower()
    checks["delivery_integrity"] = {
        "status": "ok" if delivery_status == "ok" else "blocked",
        "detail": {"status": delivery_status},
    }
    if checks["delivery_integrity"]["status"] != "ok":
        blockers.append("delivery_integrity_not_ok")

    product_metrics = status_payload.get("product_value_metrics", {}) if isinstance(status_payload.get("product_value_metrics"), dict) else {}
    priority_guard = product_metrics.get("priority_guard", {}) if isinstance(product_metrics.get("priority_guard"), dict) else {}
    priority_status, priority_reasons = _priority_guard_check(priority_guard)
    checks["product_priority_guard"] = {
        "status": priority_status,
        "detail": {
            "status": priority_guard.get("status", "unknown"),
            "blocked_reasons": priority_reasons,
        },
    }
    if priority_status != "ok":
        blockers.extend(priority_reasons or ["product_priority_guard_blocked"])

    planner_dispatch = status_payload.get("planner_dispatch", {}) if isinstance(status_payload.get("planner_dispatch"), dict) else {}
    planner_dispatch_status, planner_dispatch_reasons = _planner_dispatch_check(planner_dispatch)
    checks["planner_dispatch"] = {
        "status": planner_dispatch_status,
        "detail": {
            "status": planner_dispatch.get("status", "unknown"),
            "reasons": planner_dispatch_reasons,
            "ready_dev_count": int(planner_dispatch.get("ready_dev_count", 0) or 0),
            "active_subagents": int(planner_dispatch.get("active_subagents", 0) or 0),
        },
    }
    if planner_dispatch_status != "ok":
        blockers.extend(planner_dispatch_reasons)

    doctor_status = str(doctor_payload.get("status", "unknown") or "unknown").strip().lower() if doctor_payload else "unknown"
    checks["doctor"] = {
        "status": "ok" if doctor_status == "ok" else "blocked",
        "detail": {
            "status": doctor_status,
            "error": doctor_error,
        },
    }
    if checks["doctor"]["status"] != "ok":
        blockers.append("doctor_not_ok")

    if validate_bridge and _bridge_is_live_via_dispatch(planner_dispatch):
        checks["openclaw_bridge"] = {
            "status": "ok",
            "detail": {
                "source": "live_planner_dispatch",
                "active_subagents": int(planner_dispatch.get("active_subagents", 0) or 0),
                "planner_dispatch_status": str(planner_dispatch.get("status", "unknown") or "unknown"),
            },
        }
    elif validate_bridge:
        bridge_payload, bridge_error = _validate_bridge(root, timeout_s=bridge_timeout_s)
        bridge_ok = bool(bridge_payload.get("ok")) and bool((bridge_payload.get("bridge_validation") or {}).get("ok"))
        checks["openclaw_bridge"] = {
            "status": "ok" if bridge_ok else "blocked",
            "detail": bridge_payload if bridge_payload else {"error": bridge_error or "bridge_validation_failed"},
        }
        if not bridge_ok:
            blockers.append("openclaw_bridge_not_ready")
    else:
        checks["openclaw_bridge"] = {"status": "skipped", "detail": {"validate_bridge": False}}

    ready = not blockers
    readiness = {
        "at": _iso_now(),
        "root": str(root),
        "ready": ready,
        "status": "ok" if ready else "blocked",
        "blockers": blockers,
        "recommended_actions": _recommended_actions(blockers),
        "checks": checks,
    }
    return readiness


def _write_report(root: Path, payload: dict[str, Any]) -> Path:
    report_path = resolve_orchestrator_write_path(root, "dev-activation-readiness.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight gate before enabling planner-driven development.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--monitor-base-url", default=DEFAULT_MONITOR_BASE)
    parser.add_argument("--timeout-s", type=float, default=8.0)
    parser.add_argument("--bridge-timeout-s", type=int, default=45)
    parser.add_argument("--skip-bridge", action="store_true")
    parser.add_argument("--write-report", action="store_true", help="Persist the JSON report in runtime state.")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).absolute()
    payload = build_readiness(
        root,
        monitor_base_url=args.monitor_base_url,
        timeout_s=args.timeout_s,
        validate_bridge=not args.skip_bridge,
        bridge_timeout_s=args.bridge_timeout_s,
    )
    if args.write_report:
        payload["report_path"] = str(_write_report(root, payload))
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
