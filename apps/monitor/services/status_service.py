from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from apps.monitor.collectors.runtime_collectors import collect_queue_workboard
from planning.plane.plane_planning import build_plane_planning_snapshot
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot


def _normalize_status(value: object, default: str = "unknown") -> str:
    token = str(value or "").strip().lower()
    if token in {"ok", "degraded", "error", "unknown"}:
        return token
    return default


def _aggregate_status(*values: object) -> str:
    normalized = [_normalize_status(value) for value in values]
    if any(value == "error" for value in normalized):
        return "error"
    if any(value == "degraded" for value in normalized):
        return "degraded"
    if normalized and all(value == "ok" for value in normalized):
        return "ok"
    return "unknown"


def _probe_http_ok(url: str, timeout_s: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, headers={"Accept": "text/html,application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            return 200 <= status < 300
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False
    except Exception:
        return False


def _doctor_payload(payload: dict[str, Any]) -> dict[str, Any]:
    doctor = payload.get("doctor")
    return doctor if isinstance(doctor, dict) else {}


def _doctor_checks(payload: dict[str, Any]) -> dict[str, Any]:
    checks = _doctor_payload(payload).get("checks")
    return checks if isinstance(checks, dict) else {}


def _check_status(checks: dict[str, Any], name: str) -> str:
    raw = checks.get(name)
    if isinstance(raw, dict):
        return _normalize_status(raw.get("status"))
    return "unknown"


def _provider_plane_snapshot(kind: str) -> dict[str, Any]:
    if kind == "app":
        return {
            "status": "unknown",
            "provider_plane": "app",
            "allowed_backends": ["g4f"],
            "note": "Dedicated app provider health is not wired into monitor status yet.",
        }
    return {
        "status": "unknown",
        "provider_plane": "agent",
        "primary_backend": "codex_exec",
        "fallback_backend": "qwen_cli",
        "note": "Dedicated agent provider health is not wired into monitor status yet.",
    }


def _doctor_surface(doctor_payload: dict[str, Any], name: str) -> dict[str, Any]:
    raw = doctor_payload.get(name)
    return raw if isinstance(raw, dict) else {}


def build_status_snapshot(
    root: Path,
    status_builder: Callable[[], dict[str, Any]],
    *,
    include_layers: bool = True,
) -> dict[str, Any]:
    payload = status_builder()
    if not isinstance(payload, dict):
        payload = {}

    checks = _doctor_checks(payload)
    doctor_payload = _doctor_payload(payload)
    runtime_truth_snapshot = build_runtime_truth_snapshot(root, state_limit=12, event_limit=24)
    event_store_primary = bool(runtime_truth_snapshot.get("event_store_primary", False))
    runtime_execution_mode = str(((payload.get("runtime_state") or {}) if isinstance(payload.get("runtime_state"), dict) else {}).get("execution_mode", "") or "").strip()
    providers = checks.get("providers")
    if not isinstance(providers, dict):
        providers = {}
    backend_base_url = str(providers.get("api_base", "http://127.0.0.1:8050") or "http://127.0.0.1:8050").strip() or "http://127.0.0.1:8050"
    backend_probe_url = f"{backend_base_url.rstrip('/')}/api/health"
    backend_status = "ok" if bool(providers.get("api_reachable_effective") or providers.get("api_health_ok")) else ("ok" if _probe_http_ok(backend_probe_url) else "degraded")
    frontend_url = str(
        os.environ.get("FC_FRONTEND_STATUS_URL", "http://127.0.0.1:5173/") or "http://127.0.0.1:5173/"
    ).strip() or "http://127.0.0.1:5173/"
    frontend_status = "ok" if _probe_http_ok(frontend_url) else "degraded"
    doctor_app_runtime = _doctor_surface(doctor_payload, "app_runtime")
    payload["app_runtime"] = {
        "status": _normalize_status(doctor_app_runtime.get("status"), _aggregate_status(backend_status, frontend_status, "ok")),
        "source": str(doctor_app_runtime.get("source", "status_service.v3") or "status_service.v3"),
        "backend_api": {
            "status": _normalize_status(
                (doctor_app_runtime.get("backend_api") or {}).get("status") if isinstance(doctor_app_runtime.get("backend_api"), dict) else backend_status,
                backend_status,
            ),
            "base_url": str(
                ((doctor_app_runtime.get("backend_api") or {}).get("base_url") if isinstance(doctor_app_runtime.get("backend_api"), dict) else "")
                or backend_base_url
            ),
        },
        "frontend": {
            "status": _normalize_status(
                (doctor_app_runtime.get("frontend") or {}).get("status") if isinstance(doctor_app_runtime.get("frontend"), dict) else frontend_status,
                frontend_status,
            ),
            "url": str(
                ((doctor_app_runtime.get("frontend") or {}).get("url") if isinstance(doctor_app_runtime.get("frontend"), dict) else "")
                or frontend_url
            ),
        },
        "monitor": {
            "status": _normalize_status(
                (doctor_app_runtime.get("monitor") or {}).get("status") if isinstance(doctor_app_runtime.get("monitor"), dict) else "ok",
                "ok",
            ),
            "reason": str(
                ((doctor_app_runtime.get("monitor") or {}).get("reason") if isinstance(doctor_app_runtime.get("monitor"), dict) else "")
                or "current_status_endpoint_responded"
            ),
        },
    }
    doctor_product_runtime = _doctor_surface(doctor_payload, "product_runtime")
    payload["product_runtime"] = {
        "status": _normalize_status(doctor_product_runtime.get("status"), payload["app_runtime"]["status"]),
        "source": str(doctor_product_runtime.get("source", "app_runtime") or "app_runtime"),
        "app_first": bool(doctor_product_runtime.get("app_first", True)),
        "agentic_optional": bool(doctor_product_runtime.get("agentic_optional", True)),
        "note": str(
            doctor_product_runtime.get("note")
            or "Primary user-facing runtime status. Agentic or planning degradation must not be read as an app outage."
        ),
    }
    payload["primary_status"] = payload["product_runtime"]["status"]
    payload["primary_status_source"] = "product_runtime"
    doctor_agentic_runtime = _doctor_surface(doctor_payload, "agentic_runtime")
    payload["agentic_runtime"] = {
        "status": _normalize_status(
            doctor_agentic_runtime.get("status"),
            "ok" if event_store_primary and runtime_execution_mode else _aggregate_status(
                _check_status(checks, "runtime_truth"),
                _check_status(checks, "scheduler_authority"),
                _check_status(checks, "sessions"),
            ),
        ),
        "source": str(doctor_agentic_runtime.get("source", "doctor_snapshot") or "doctor_snapshot"),
        "runtime_truth": _normalize_status(doctor_agentic_runtime.get("runtime_truth"), "ok" if event_store_primary else _check_status(checks, "runtime_truth")),
        "scheduler_authority": _normalize_status(doctor_agentic_runtime.get("scheduler_authority"), "ok" if runtime_execution_mode else _check_status(checks, "scheduler_authority")),
        "sessions": _normalize_status(doctor_agentic_runtime.get("sessions"), _check_status(checks, "sessions")),
    }

    planning_detail = _doctor_surface(doctor_payload, "planning_plane")
    fallback_planning_detail = build_plane_planning_snapshot(root) if not planning_detail else {}
    payload["planning_plane"] = {
        "status": _normalize_status(
            planning_detail.get("status")
            or _check_status(checks, "plane_planning")
            or fallback_planning_detail.get("status")
        ),
        **fallback_planning_detail,
        **planning_detail,
    }
    payload["app_providers"] = _provider_plane_snapshot("app")
    payload["agent_providers"] = _provider_plane_snapshot("agent")
    openclaw_gateway = doctor_payload.get("openclaw_gateway")
    if isinstance(openclaw_gateway, dict):
        payload["openclaw_gateway"] = openclaw_gateway
    payload["worker_orphan_count"] = int(doctor_payload.get("worker_orphan_count", 0) or 0)
    worker_orphans = doctor_payload.get("worker_orphans", [])
    if isinstance(worker_orphans, list):
        payload["worker_orphans"] = worker_orphans[:20]

    payload.setdefault("layers", {})
    payload["layers"]["service"] = "status_service.v3"
    if include_layers:
        payload["layers"]["collectors"] = collect_queue_workboard(root)
    else:
        payload["layers"]["collectors_omitted"] = True
        payload["layers"]["mode"] = "lite"
    return payload
