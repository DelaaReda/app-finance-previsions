from __future__ import annotations

import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from apps.monitor.collectors.runtime_collectors import collect_queue_workboard
from planning.plane.plane_planning import build_plane_planning_snapshot
from runtime.truth.public_runtime_probe import probe_public_surface
from runtime.truth.runtime_truth_reader import build_runtime_truth_snapshot, load_product_delivery_state


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


def _merge_live_with_doctor(live_status: object, doctor_status: object) -> str:
    live = _normalize_status(live_status)
    doctor = _normalize_status(doctor_status)
    if doctor in {"error", "degraded"}:
        return doctor
    if live in {"error", "degraded"}:
        return live
    if doctor == "ok" or live == "ok":
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


def _app_only_monitor_host(payload: dict[str, Any]) -> bool:
    monitor_host = payload.get("monitor_host")
    if isinstance(monitor_host, dict):
        profile = str(monitor_host.get("profile", "") or "").strip().lower()
        control_plane_location = str(monitor_host.get("control_plane_location", "") or "").strip().lower()
        if profile == "app_only" or control_plane_location == "remote_vm":
            return True
    token = str(os.environ.get("FC_CONTROL_PLANE_LOCATION", "") or "").strip().lower()
    return token in {"remote", "remote_vm", "aws_ec2_app", "ec2_app_host"}


def _systemd_unit_probe(unit: str, verb: str) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            ["systemctl", "--user", verb, unit],
            text=True,
            capture_output=True,
            check=False,
            timeout=1.0,
        )
    except Exception as exc:
        return {
            "ok": False,
            "unit": unit,
            "verb": verb,
            "rc": -1,
            "output": str(exc),
        }
    output = (cp.stdout or cp.stderr or "").strip()
    return {
        "ok": cp.returncode == 0,
        "unit": unit,
        "verb": verb,
        "rc": cp.returncode,
        "output": output,
    }


def _normalize_openclaw_gateway(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {}

    normalized = dict(detail)
    expected_unit = "openclaw-gateway.service"
    active_probe = normalized.get("service_active_probe")
    enabled_probe = normalized.get("service_enabled_probe")
    active_unit = str(active_probe.get("unit", "") or "").strip() if isinstance(active_probe, dict) else ""
    enabled_unit = str(enabled_probe.get("unit", "") or "").strip() if isinstance(enabled_probe, dict) else ""
    should_reprobe = active_unit == "openclaw.service" or enabled_unit == "openclaw.service"

    if should_reprobe:
        corrected_active_probe = _systemd_unit_probe(expected_unit, "is-active")
        corrected_enabled_probe = _systemd_unit_probe(expected_unit, "is-enabled")
        normalized["service_active_probe"] = corrected_active_probe
        normalized["service_enabled_probe"] = corrected_enabled_probe
        normalized["service_active"] = bool(corrected_active_probe.get("ok"))
        normalized["service_enabled"] = bool(corrected_enabled_probe.get("ok"))
        normalized["service_unit"] = expected_unit
        normalized["service_probe_corrected"] = True
        normalized["service_probe_original_unit"] = "openclaw.service"
    else:
        normalized["service_unit"] = str(normalized.get("service_unit", expected_unit) or expected_unit)

    return normalized


def _collector_queue_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    queue = snapshot.get("queue")
    if not isinstance(queue, dict):
        return {"active_batch": None, "counts": {}, "active_cycle": {}}
    active_cycle = queue.get("active_cycle")
    active_cycle = active_cycle if isinstance(active_cycle, dict) else {}
    items = queue.get("items")
    items = items if isinstance(items, list) else []
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state", "") or "").strip()
        if not state:
            continue
        counts[state] = counts.get(state, 0) + 1
    active_batch_ids = active_cycle.get("active_batch_ids")
    active_batch = None
    if isinstance(active_batch_ids, list):
        for batch_id in active_batch_ids:
            token = str(batch_id or "").strip()
            if token:
                active_batch = token
                break
    return {
        "active_batch": active_batch,
        "counts": counts,
        "active_cycle": active_cycle,
    }


def _literal_delivery_control(delivery_state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(delivery_state, dict):
        return {}
    return dict(delivery_state)


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
    doctor_overall_status = _normalize_status(
        doctor_payload.get("overall_status") or doctor_payload.get("status"),
        "unknown",
    )
    runtime_execution_mode = str(((payload.get("runtime_state") or {}) if isinstance(payload.get("runtime_state"), dict) else {}).get("execution_mode", "") or "").strip()
    app_only_monitor_host = _app_only_monitor_host(payload)
    providers = checks.get("providers")
    if not isinstance(providers, dict):
        providers = {}
    default_public_app = str(
        os.environ.get("FC_API_BASE_URL")
        or os.environ.get("FC_PUBLIC_APP_BASE_URL")
        or "http://3.98.20.77"
    ).strip() or "http://3.98.20.77"
    backend_base_url = str(providers.get("api_base", default_public_app) or default_public_app).strip() or default_public_app
    backend_probe_candidates = (
        f"{backend_base_url.rstrip('/')}/api/status",
        f"{backend_base_url.rstrip('/')}/api/health",
    )
    backend_probe_url = backend_probe_candidates[0]
    backend_probe_ok = False
    backend_probe: dict[str, Any] = {}
    for candidate in backend_probe_candidates:
        backend_probe_url = candidate
        backend_probe = probe_public_surface(candidate, timeout_s=1.5)
        if backend_probe.get("http_ok") or backend_probe.get("maintenance_active"):
            backend_probe_ok = bool(backend_probe.get("http_ok"))
            break
    backend_probe_maintenance = bool(backend_probe.get("maintenance_active"))
    backend_status = "ok" if bool(providers.get("api_reachable_effective") or providers.get("api_health_ok")) else ("ok" if backend_probe_ok else "degraded")
    frontend_url = str(
        os.environ.get("FC_FRONTEND_STATUS_URL")
        or os.environ.get("FC_PUBLIC_APP_BASE_URL")
        or "http://3.98.20.77/"
    ).strip() or "http://3.98.20.77/"
    frontend_status = "ok" if _probe_http_ok(frontend_url) else "degraded"
    runtime_truth_snapshot = build_runtime_truth_snapshot(
        root,
        state_limit=12,
        event_limit=24,
        ec2_reachable=True if (backend_probe_ok or backend_probe_maintenance) else False,
        public_probe_status="ok" if backend_probe_ok else ("degraded" if backend_probe_maintenance else "error"),
        maintenance_active=backend_probe_maintenance,
        maintenance_details=backend_probe,
    )
    event_store_primary = bool(runtime_truth_snapshot.get("event_store_primary", False))
    delivery_state = load_product_delivery_state(root)
    if not isinstance(delivery_state, dict) or not delivery_state:
        delivery_state = runtime_truth_snapshot.get("product_delivery_state")
    if not isinstance(delivery_state, dict):
        delivery_state = {}
    doctor_app_runtime = _doctor_surface(doctor_payload, "app_runtime")
    doctor_app_status = _normalize_status(doctor_app_runtime.get("status"))
    doctor_backend_status = _normalize_status(
        (doctor_app_runtime.get("backend_api") or {}).get("status") if isinstance(doctor_app_runtime.get("backend_api"), dict) else backend_status,
        backend_status,
    )
    doctor_frontend_status = _normalize_status(
        (doctor_app_runtime.get("frontend") or {}).get("status") if isinstance(doctor_app_runtime.get("frontend"), dict) else frontend_status,
        frontend_status,
    )
    effective_backend_status = _merge_live_with_doctor(backend_status, doctor_backend_status)
    effective_frontend_status = _merge_live_with_doctor(frontend_status, doctor_frontend_status)
    effective_app_status = _merge_live_with_doctor(
        _aggregate_status(effective_backend_status, effective_frontend_status),
        doctor_app_status,
    )
    app_runtime_source = str(doctor_app_runtime.get("source", "status_service.v3") or "status_service.v3")
    payload["app_runtime"] = {
        "status": effective_app_status,
        "source": "doctor_consensus" if doctor_app_status in {"degraded", "error"} else app_runtime_source,
        "backend_api": {
            "status": effective_backend_status,
            "base_url": str(
                ((doctor_app_runtime.get("backend_api") or {}).get("base_url") if isinstance(doctor_app_runtime.get("backend_api"), dict) else "")
                or backend_base_url
            ),
        },
        "frontend": {
            "status": effective_frontend_status,
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
    if doctor_app_status in {"degraded", "error"}:
        payload["app_runtime"]["live_probe_status"] = _aggregate_status(backend_status, frontend_status)
        payload["app_runtime"]["doctor_status"] = doctor_app_status
    doctor_product_runtime = _doctor_surface(doctor_payload, "product_runtime")
    effective_product_runtime_status = _merge_live_with_doctor(
        payload["app_runtime"]["status"],
        doctor_product_runtime.get("status"),
    )
    payload["product_runtime"] = {
        "status": effective_product_runtime_status,
        "source": str(doctor_product_runtime.get("source", "app_runtime") or "app_runtime"),
        "app_first": bool(doctor_product_runtime.get("app_first", True)),
        "agentic_optional": bool(doctor_product_runtime.get("agentic_optional", True)),
        "note": str(
            doctor_product_runtime.get("note")
            or "Primary user-facing runtime status. Agentic or planning degradation must not be read as an app outage."
        ),
    }
    payload["product_runtime"]["doctor_overall_status"] = doctor_overall_status
    payload["primary_status"] = payload["product_runtime"]["status"]
    payload["primary_status_source"] = "product_runtime"
    payload["doctor_overall_status"] = doctor_overall_status
    payload["doctor_overall_status_source"] = "fc_doctor"
    doctor_agentic_runtime = _doctor_surface(doctor_payload, "agentic_runtime")
    agentic_runtime_payload = {
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
    if app_only_monitor_host:
        payload["agentic_runtime"] = {
            "status": "ok",
            "source": "remote_vm_advisory",
            "runtime_truth": "ok",
            "scheduler_authority": "ok",
            "sessions": "ok",
            "advisory_only": True,
            "control_plane_location": "remote_vm",
            "note": "Remote orchestration control-plane checks are advisory on this app-only host.",
            "remote_snapshot": agentic_runtime_payload,
        }
    else:
        payload["agentic_runtime"] = agentic_runtime_payload

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
        payload["openclaw_gateway"] = _normalize_openclaw_gateway(openclaw_gateway)
    if app_only_monitor_host:
        remote_openclaw_gateway = payload.get("openclaw_gateway", {})
        if not isinstance(remote_openclaw_gateway, dict):
            remote_openclaw_gateway = {}
        payload["openclaw_gateway"] = {
            "status": "ok",
            "source": "remote_vm_advisory",
            "advisory_only": True,
            "control_plane_location": "remote_vm",
            "note": "OpenClaw lives on the orchestration host and is advisory on this app-only host.",
            "remote_snapshot": remote_openclaw_gateway,
        }
    payload["worker_orphan_count"] = int(doctor_payload.get("worker_orphan_count", 0) or 0)
    worker_orphans = doctor_payload.get("worker_orphans", [])
    if isinstance(worker_orphans, list):
        payload["worker_orphans"] = worker_orphans[:20]

    advisory_delivery_control = payload.get("delivery_control_advisory")
    if not isinstance(advisory_delivery_control, dict):
        advisory_delivery_control = payload.get("delivery_control")
    if not isinstance(advisory_delivery_control, dict):
        advisory_delivery_control = {}

    payload.setdefault("layers", {})
    payload["layers"]["service"] = "status_service.v3"
    payload["delivery_control_advisory"] = dict(advisory_delivery_control)
    payload["delivery_control"] = _literal_delivery_control(delivery_state)
    payload["status_semantics"] = {
        "overall_status": {
            "field": "doctor_overall_status",
            "status": doctor_overall_status,
            "meaning": "doctor_overall_control_plane",
        },
        "product_runtime": {
            "field": "product_runtime.status",
            "status": payload["product_runtime"]["status"],
            "meaning": "user_facing_runtime",
        },
        "backend_runtime": {
            "field": "app_runtime.backend_api.status",
            "status": payload["app_runtime"]["backend_api"]["status"],
            "meaning": "backend_api_runtime",
        },
        "agentic_runtime": {
            "field": "agentic_runtime.status",
            "status": payload["agentic_runtime"]["status"],
            "meaning": "delivery_control_plane",
        },
        "planning_plane": {
            "field": "planning_plane.status",
            "status": payload["planning_plane"]["status"],
            "meaning": "planner_governance_plane",
        },
        "note": (
            "doctor_overall_status tracks fc_doctor overall control-plane health; "
            "product_runtime.status remains the app-first user-facing runtime signal."
        ),
    }
    runtime_state = payload.get("runtime_state")
    runtime_lifecycle = str((runtime_state.get("lifecycle") if isinstance(runtime_state, dict) else "") or "").strip().lower()
    if runtime_lifecycle == "paused":
        payload["health"] = "PAUSED"
    elif app_only_monitor_host:
        payload["health"] = str(payload["product_runtime"]["status"] or "unknown").upper()
        payload["status_semantics"]["agentic_runtime"]["advisory_only"] = True
        payload["status_semantics"]["note"] = (
            "doctor_overall_status tracks control-plane health; on the EC2 app-only host, "
            "agentic/planning/operator surfaces are advisory and public health follows product_runtime.status."
        )
        payload["issue_publication_gap_roles"] = []
        issue_reporting = payload.get("issue_reporting")
        if isinstance(issue_reporting, dict):
            issue_reporting["roles_missing_report"] = []
            issue_reporting["advisory_only"] = True
    collector_snapshot = collect_queue_workboard(root)
    queue_summary = _collector_queue_summary(collector_snapshot)
    queue_payload = payload.get("queue")
    if not isinstance(queue_payload, dict):
        queue_payload = {}
        payload["queue"] = queue_payload
    queue_payload.setdefault("counts", queue_summary["counts"])
    queue_payload.setdefault("active_cycle", queue_summary["active_cycle"])
    payload["active_batch"] = delivery_state.get("active_batch_id") if event_store_primary else None
    agents_payload = payload.get("agents")
    if not isinstance(agents_payload, dict):
        agents_payload = {}
        payload["agents"] = agents_payload
    operator_mode = str(((payload.get("runtime_state") or {}) if isinstance(payload.get("runtime_state"), dict) else {}).get("operator_mode", "") or "").strip().lower()
    if "roles" not in agents_payload or agents_payload.get("roles") is None:
        if operator_mode == "planner-only":
            agents_payload["roles"] = ["planner"]
    if "core_roles" not in agents_payload or agents_payload.get("core_roles") is None:
        if operator_mode == "planner-only":
            agents_payload["core_roles"] = ["planner"]
    if include_layers:
        payload["layers"]["collectors"] = collector_snapshot
    else:
        payload["layers"]["collectors_omitted"] = True
        payload["layers"]["mode"] = "lite"
    return payload
