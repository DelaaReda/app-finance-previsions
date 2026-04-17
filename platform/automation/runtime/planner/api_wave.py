from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import load_runtime_state, resolve_orchestrator_read_path, write_orchestrator_json

API_WAVE_EXECUTION_MODE = "api_autonomy_mode"
API_WAVE_MANIFEST_FILE = "api-wave-manifest.json"
API_WAVE_STATE_FILE = "api-wave-state.json"
API_WAVE_STREAM_ID = "API-WAVE"
API_WAVE_SCHEMA_VERSION = "api_wave_state.v1"
API_WAVE_MANIFEST_SCHEMA_VERSION = "api_wave_manifest.v1"

_DEFAULT_UI_PROOF = {
    "kind": "public_ui_smoke",
    "url": "http://3.98.20.77/",
}

DEFAULT_API_WAVE_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "endpoint_id": "copilot_search",
        "domain": "copilot",
        "route_path": "/api/search/tickers",
        "route_module": "apps/api/src/domains/copilot/api/search.py",
        "priority": 10,
        "product_surface": "copilot",
        "shared_contract": "",
        "endpoint_service": "",
        "parity_status": "route_local_mixed_contract",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/search/tickers?q=NVDA&limit=3"],
            "success_condition": "returns search payload with ok=true and data.matches or data.total",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "copilot-search"},
    },
    {
        "endpoint_id": "copilot_universal_search",
        "domain": "copilot",
        "route_path": "/api/search/universal",
        "route_module": "apps/api/src/domains/copilot/api/universal_search.py",
        "priority": 20,
        "product_surface": "copilot",
        "shared_contract": "",
        "endpoint_service": "apps/api/src/domains/copilot/application/universal_search.py",
        "parity_status": "legacy_route_no_shared_service_contract",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/search/universal?q=NVDA&limit=5"],
            "success_condition": "returns search payload with ok=true and data.results",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "copilot-universal-search"},
    },
    {
        "endpoint_id": "forecasts_brief",
        "domain": "forecasts",
        "route_path": "/api/brief/daily",
        "route_module": "apps/api/src/domains/forecasts/api/brief.py",
        "priority": 30,
        "product_surface": "forecasts",
        "shared_contract": "",
        "endpoint_service": "",
        "parity_status": "route_local_contract_needs_judge_metadata",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/brief/daily"],
            "success_condition": "returns brief payload with ok=true and generated_at/source/freshness",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "forecasts-brief"},
    },
    {
        "endpoint_id": "market_data_news_feed",
        "domain": "market_data",
        "route_path": "/api/news/feed",
        "route_module": "apps/api/src/domains/market_data/api/news.py",
        "priority": 40,
        "product_surface": "market_data",
        "shared_contract": "",
        "endpoint_service": "apps/api/src/domains/market_data/application/news_service.py",
        "parity_status": "mixed_route_service_contract",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/news/feed?limit=5"],
            "success_condition": "returns news payload with ok=true and data.articles",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "market-data-news-feed"},
    },
    {
        "endpoint_id": "market_data_stocks",
        "domain": "market_data",
        "route_path": "/api/stocks/prices",
        "route_module": "apps/api/src/domains/market_data/api/stocks.py",
        "priority": 50,
        "product_surface": "market_data",
        "shared_contract": "",
        "endpoint_service": "apps/api/src/domains/market_data/application/stocks_service.py",
        "parity_status": "legacy_route_needs_endpoint_service_parity",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/stocks/prices?ticker=NVDA&interval=1d"],
            "success_condition": "returns prices payload with ok=true and data.points",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "market-data-stocks"},
    },
    {
        "endpoint_id": "market_data_news_impact",
        "domain": "market_data",
        "route_path": "/api/news/analysis",
        "route_module": "apps/api/src/domains/market_data/api/news_impact.py",
        "priority": 60,
        "product_surface": "market_data",
        "shared_contract": "",
        "endpoint_service": "",
        "parity_status": "route_local_contract_needs_metadata",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/news/analysis?tickers=NVDA&limit=5"],
            "success_condition": "returns impact payload with ok=true and data.impact_analysis",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "market-data-news-impact"},
    },
    {
        "endpoint_id": "market_data_news_extra",
        "domain": "market_data",
        "route_path": "/api/news/feed",
        "route_module": "apps/api/src/domains/market_data/api/news_extra.py",
        "priority": 70,
        "product_surface": "market_data",
        "shared_contract": "",
        "endpoint_service": "",
        "parity_status": "duplicate_route_surface_needs_single_service_contract",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/news/feed?tickers=NVDA&limit=5&q=AI"],
            "success_condition": "returns filtered news payload with ok=true and data.articles",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "market-data-news-extra"},
    },
    {
        "endpoint_id": "market_data_analytics",
        "domain": "market_data",
        "route_path": "/api/analytics/predictions",
        "route_module": "apps/api/src/domains/market_data/api/analytics.py",
        "priority": 80,
        "product_surface": "market_data",
        "shared_contract": "",
        "endpoint_service": "",
        "parity_status": "route_local_contract_needs_service_boundary",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/analytics/predictions?ticker=NVDA&limit=5"],
            "success_condition": "returns analytics payload with ok=true and data.accuracy_metrics",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "market-data-analytics"},
    },
    {
        "endpoint_id": "market_data_stocks_client",
        "domain": "market_data",
        "route_path": "/api/stocks/search",
        "route_module": "apps/api/src/domains/market_data/api/stocks_client.py",
        "priority": 90,
        "product_surface": "market_data",
        "shared_contract": "",
        "endpoint_service": "",
        "parity_status": "client_route_needs_shared_contract_metadata",
        "last_public_proof": "",
        "deferred_reason": "",
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/stocks/search?q=NVDA&limit=5"],
            "success_condition": "returns stocks search payload with ok=true and data.results",
        },
        "ui_proof": {**_DEFAULT_UI_PROOF, "label": "market-data-stocks-client"},
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def default_api_wave_manifest() -> dict[str, Any]:
    return {
        "schema_version": API_WAVE_MANIFEST_SCHEMA_VERSION,
        "mode": API_WAVE_EXECUTION_MODE,
        "stream_id": API_WAVE_STREAM_ID,
        "items": copy.deepcopy(list(DEFAULT_API_WAVE_ITEMS)),
        "updated_at": "",
    }


def default_api_wave_state() -> dict[str, Any]:
    return {
        "schema_version": API_WAVE_SCHEMA_VERSION,
        "mode": API_WAVE_EXECUTION_MODE,
        "stream_id": API_WAVE_STREAM_ID,
        "current_endpoint_id": "",
        "current_owner_task_id": "",
        "current_subagent_id": "",
        "current_status": "idle_ready_for_next_endpoint",
        "current_dispatch_backend": "",
        "current_blocked_reason": "",
        "completed_endpoint_ids": [],
        "deferred_endpoint_ids": [],
        "endpoint_attempts": {},
        "last_public_proof_ref": "",
        "last_public_proof_status": "",
        "last_meaningful_delta_at": "",
        "next_endpoint_id": "",
        "updated_at": "",
        "last_transition_at": "",
        "last_dispatch_at": "",
        "last_completion_at": "",
    }


def api_wave_manifest_path(root: Path) -> Path:
    return resolve_orchestrator_read_path(root, API_WAVE_MANIFEST_FILE)


def api_wave_state_path(root: Path) -> Path:
    return resolve_orchestrator_read_path(root, API_WAVE_STATE_FILE)


def save_api_wave_manifest(root: Path, payload: dict[str, Any]) -> Path:
    normalized = default_api_wave_manifest()
    if isinstance(payload, dict):
        normalized.update(payload)
    normalized["schema_version"] = API_WAVE_MANIFEST_SCHEMA_VERSION
    normalized["mode"] = API_WAVE_EXECUTION_MODE
    normalized["stream_id"] = API_WAVE_STREAM_ID
    normalized["updated_at"] = _utc_now()
    items = normalized.get("items")
    normalized["items"] = [dict(item) for item in items] if isinstance(items, list) else []
    return write_orchestrator_json(root, API_WAVE_MANIFEST_FILE, normalized, mirror_docs=False)


def save_api_wave_state(root: Path, payload: dict[str, Any]) -> Path:
    normalized = default_api_wave_state()
    if isinstance(payload, dict):
        normalized.update(payload)
    normalized["schema_version"] = API_WAVE_SCHEMA_VERSION
    normalized["mode"] = API_WAVE_EXECUTION_MODE
    normalized["stream_id"] = API_WAVE_STREAM_ID
    normalized["updated_at"] = _utc_now()
    for key in ("completed_endpoint_ids", "deferred_endpoint_ids"):
        value = normalized.get(key)
        normalized[key] = [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []
    attempts = normalized.get("endpoint_attempts")
    normalized["endpoint_attempts"] = dict(attempts) if isinstance(attempts, dict) else {}
    return write_orchestrator_json(root, API_WAVE_STATE_FILE, normalized, mirror_docs=False)


def load_api_wave_manifest(root: Path, *, persist_defaults: bool = False) -> dict[str, Any]:
    payload = _load_json(api_wave_manifest_path(root))
    if not payload:
        payload = default_api_wave_manifest()
        if persist_defaults:
            save_api_wave_manifest(root, payload)
            return load_api_wave_manifest(root, persist_defaults=False)
        return payload
    items = payload.get("items")
    payload["items"] = [dict(item) for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    payload.setdefault("schema_version", API_WAVE_MANIFEST_SCHEMA_VERSION)
    payload.setdefault("mode", API_WAVE_EXECUTION_MODE)
    payload.setdefault("stream_id", API_WAVE_STREAM_ID)
    return payload


def load_api_wave_state(root: Path, *, persist_defaults: bool = False) -> dict[str, Any]:
    payload = _load_json(api_wave_state_path(root))
    if not payload:
        payload = default_api_wave_state()
        if persist_defaults:
            save_api_wave_state(root, payload)
            return load_api_wave_state(root, persist_defaults=False)
        return payload
    payload.setdefault("schema_version", API_WAVE_SCHEMA_VERSION)
    payload.setdefault("mode", API_WAVE_EXECUTION_MODE)
    payload.setdefault("stream_id", API_WAVE_STREAM_ID)
    for key in ("completed_endpoint_ids", "deferred_endpoint_ids"):
        value = payload.get(key)
        payload[key] = [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []
    attempts = payload.get("endpoint_attempts")
    payload["endpoint_attempts"] = dict(attempts) if isinstance(attempts, dict) else {}
    return payload


def api_wave_mode_enabled(root: Path) -> bool:
    runtime_state = load_runtime_state(root)
    return str(runtime_state.get("execution_mode") or "").strip().lower() == API_WAVE_EXECUTION_MODE


def _manifest_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = manifest.get("items")
    return [dict(item) for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def api_wave_owner_task_id(endpoint_id: str) -> str:
    token = re.sub(r"[^A-Z0-9_]+", "_", str(endpoint_id or "").strip().upper())
    token = re.sub(r"_+", "_", token).strip("_") or "ENDPOINT"
    return f"APIWAVE-{token}-DEV-01"


def _entry_matches_batch(entry: dict[str, Any], batch_id: str) -> bool:
    endpoint_id = str(entry.get("endpoint_id") or "").strip()
    owner_task_id = api_wave_owner_task_id(endpoint_id)
    token = str(batch_id or "").strip()
    return token in {endpoint_id, owner_task_id}


def get_api_wave_entry(manifest: dict[str, Any], endpoint_id: str) -> dict[str, Any] | None:
    token = str(endpoint_id or "").strip()
    if not token:
        return None
    for item in _manifest_items(manifest):
        if str(item.get("endpoint_id") or "").strip() == token:
            return item
    return None


def entry_for_batch_id(root: Path, batch_id: str) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    state = load_api_wave_state(root, persist_defaults=True)
    token = str(batch_id or "").strip()
    if not token:
        return None, manifest, state
    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
    if current_endpoint_id:
        current_entry = get_api_wave_entry(manifest, current_endpoint_id)
        if current_entry and _entry_matches_batch(current_entry, token):
            return current_entry, manifest, state
    for item in _manifest_items(manifest):
        if _entry_matches_batch(item, token):
            return item, manifest, state
    return None, manifest, state


def api_wave_delivery_contract(entry: dict[str, Any]) -> dict[str, Any]:
    endpoint_id = str(entry.get("endpoint_id") or "api_wave_endpoint").strip() or "api_wave_endpoint"
    route_path = str(entry.get("route_path") or "").strip() or "/api/health"
    api_proof = entry.get("api_proof") if isinstance(entry.get("api_proof"), dict) else {}
    ui_proof = entry.get("ui_proof") if isinstance(entry.get("ui_proof"), dict) else {}
    return {
        "value_target": endpoint_id,
        "user_visible_delta": f"judge_parity:{route_path}",
        "api_proof": {
            "kind": str(api_proof.get("kind") or "public_api_smoke").strip() or "public_api_smoke",
            "base_url": str(api_proof.get("base_url") or "http://3.98.20.77").strip() or "http://3.98.20.77",
            "expected_endpoints": list(api_proof.get("expected_endpoints") or [route_path]),
            "success_condition": str(api_proof.get("success_condition") or "returns stable ok=true contract").strip() or "returns stable ok=true contract",
        },
        "ui_proof": {
            "kind": str(ui_proof.get("kind") or _DEFAULT_UI_PROOF["kind"]).strip() or _DEFAULT_UI_PROOF["kind"],
            "url": str(ui_proof.get("url") or _DEFAULT_UI_PROOF["url"]).strip() or _DEFAULT_UI_PROOF["url"],
            "label": str(ui_proof.get("label") or endpoint_id.replace("_", "-")).strip() or endpoint_id.replace("_", "-"),
        },
        "done_when": "public_proof_status=ok && user_visible_delta_confirmed=true",
    }


def select_next_endpoint(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    completed = {str(item).strip() for item in state.get("completed_endpoint_ids", []) if str(item).strip()}
    deferred = {str(item).strip() for item in state.get("deferred_endpoint_ids", []) if str(item).strip()}
    current = str(state.get("current_endpoint_id") or "").strip()
    items = sorted(_manifest_items(manifest), key=lambda item: int(item.get("priority", 999) or 999))
    if current and current not in completed and current not in deferred:
        current_entry = get_api_wave_entry(manifest, current)
        if current_entry is not None:
            return current_entry
    for item in items:
        endpoint_id = str(item.get("endpoint_id") or "").strip()
        if endpoint_id and endpoint_id not in completed and endpoint_id not in deferred:
            return item
    return None


def ensure_current_endpoint(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    state = load_api_wave_state(root, persist_defaults=True)
    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
    current_status = str(state.get("current_status") or "").strip()
    entry = get_api_wave_entry(manifest, current_endpoint_id) if current_endpoint_id else None
    if entry is not None and current_status not in {"completed", "deferred"}:
        state["next_endpoint_id"] = str(entry.get("endpoint_id") or "").strip()
        return manifest, state, entry
    selected = select_next_endpoint(manifest, state)
    if selected is None:
        state["current_endpoint_id"] = ""
        state["current_owner_task_id"] = ""
        state["current_subagent_id"] = ""
        state["current_status"] = "idle_exhausted"
        state["next_endpoint_id"] = ""
        state["current_blocked_reason"] = ""
        state["last_transition_at"] = _utc_now()
        save_api_wave_state(root, state)
        return manifest, load_api_wave_state(root), None
    endpoint_id = str(selected.get("endpoint_id") or "").strip()
    state["current_endpoint_id"] = endpoint_id
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_id)
    state["current_subagent_id"] = ""
    state["current_status"] = "active_delivery"
    state["current_blocked_reason"] = ""
    state["next_endpoint_id"] = endpoint_id
    state["last_transition_at"] = _utc_now()
    save_api_wave_state(root, state)
    return manifest, load_api_wave_state(root), selected


def build_dispatch_message(entry: dict[str, Any]) -> str:
    endpoint_id = str(entry.get("endpoint_id") or "unknown_endpoint").strip()
    route_path = str(entry.get("route_path") or "").strip() or "/api/health"
    route_module = str(entry.get("route_module") or "").strip() or "unknown"
    endpoint_service = str(entry.get("endpoint_service") or "").strip() or "none"
    shared_contract = str(entry.get("shared_contract") or "").strip() or "none"
    product_surface = str(entry.get("product_surface") or "").strip() or str(entry.get("domain") or "product").strip() or "product"
    return (
        f"API_WAVE_ENDPOINT_ID={endpoint_id}\n"
        f"API_WAVE_ROUTE_PATH={route_path}\n"
        f"API_WAVE_ROUTE_MODULE={route_module}\n"
        f"API_WAVE_ENDPOINT_SERVICE={endpoint_service}\n"
        f"API_WAVE_SHARED_CONTRACT={shared_contract}\n"
        f"API_WAVE_PRODUCT_SURFACE={product_surface}\n"
        "API wave mode is active. Deliver one product endpoint end-to-end, not a micro-fix or orchestration proof.\n"
        "Judge remains the canonical model. Reproduce Judge-style contract and layering without refactoring judge.\n"
        "You may complete the endpoint via shared contract if needed, application/* service, endpoint_service, thin route wiring, targeted tests, and public smoke.\n"
        "Reuse judge_like_endpoint and existing metadata/fallback helpers where possible. Do not re-invent a decision engine outside reusable services.\n"
        "Do not redesign frontend; only do minimal wiring if backend is already ready and the UI contract depends on it.\n"
        f"Target route {route_path} in {route_module}. Endpoint service path hint: {endpoint_service}. Shared contract path hint: {shared_contract}.\n"
        "Required output still follows the hard JSON contract, but the delivery slice may span the full endpoint boundary."
    )


def record_dispatch(root: Path, *, endpoint_id: str, subagent_id: str, backend: str) -> dict[str, Any]:
    state = load_api_wave_state(root, persist_defaults=True)
    state["current_endpoint_id"] = str(endpoint_id or "").strip()
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_id)
    state["current_subagent_id"] = str(subagent_id or "").strip()
    state["current_dispatch_backend"] = str(backend or "").strip()
    state["current_status"] = "active_delivery"
    state["current_blocked_reason"] = ""
    state["last_dispatch_at"] = _utc_now()
    state["last_transition_at"] = state["last_dispatch_at"]
    save_api_wave_state(root, state)
    return load_api_wave_state(root)


def record_delivery_ready_for_proof(root: Path, *, endpoint_id: str) -> dict[str, Any]:
    state = load_api_wave_state(root, persist_defaults=True)
    state["current_endpoint_id"] = str(endpoint_id or "").strip()
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_id)
    state["current_subagent_id"] = ""
    state["current_status"] = "verifying_public_proof"
    state["current_blocked_reason"] = ""
    state["last_meaningful_delta_at"] = _utc_now()
    state["last_transition_at"] = state["last_meaningful_delta_at"]
    save_api_wave_state(root, state)
    return load_api_wave_state(root)


def _increment_attempt(state: dict[str, Any], endpoint_id: str) -> int:
    attempts = dict(state.get("endpoint_attempts") or {})
    key = str(endpoint_id or "").strip()
    attempts[key] = int(attempts.get(key, 0) or 0) + 1
    state["endpoint_attempts"] = attempts
    return attempts[key]


def should_defer_blocker(reason: str) -> bool:
    token = " ".join(str(reason or "").lower().split())
    if not token:
        return False
    markers = ("provider", "upstream", "dependency", "external", "timeout", "429", "502", "503", "rate limit", "dns", "connection refused", "unavailable")
    return any(marker in token for marker in markers)


def record_blocked_or_deferred(root: Path, *, endpoint_id: str, reason: str) -> dict[str, Any]:
    state = load_api_wave_state(root, persist_defaults=True)
    endpoint_token = str(endpoint_id or "").strip()
    attempts = _increment_attempt(state, endpoint_token)
    state["current_endpoint_id"] = endpoint_token
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_token)
    state["current_subagent_id"] = ""
    state["current_blocked_reason"] = str(reason or "blocked").strip() or "blocked"
    state["last_transition_at"] = _utc_now()
    state["last_meaningful_delta_at"] = state["last_transition_at"]
    if should_defer_blocker(reason):
        deferred = [item for item in state.get("deferred_endpoint_ids", []) if str(item).strip()]
        if endpoint_token not in deferred:
            deferred.append(endpoint_token)
        state["deferred_endpoint_ids"] = deferred
        state["current_endpoint_id"] = ""
        state["current_owner_task_id"] = ""
        state["current_status"] = "deferred"
        state["next_endpoint_id"] = ""
    else:
        state["current_status"] = "blocked" if attempts < 2 else "blocked_escalate_scrum"
    save_api_wave_state(root, state)
    if should_defer_blocker(reason):
        manifest = load_api_wave_manifest(root, persist_defaults=True)
        items = _manifest_items(manifest)
        for item in items:
            if str(item.get("endpoint_id") or "").strip() == endpoint_token:
                item["deferred_reason"] = str(reason or "deferred").strip() or "deferred"
        manifest["items"] = items
        save_api_wave_manifest(root, manifest)
    return load_api_wave_state(root)


def apply_public_proof_result(root: Path, *, batch_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    entry, manifest, state = entry_for_batch_id(root, batch_id)
    if entry is None:
        return state
    endpoint_id = str(entry.get("endpoint_id") or "").strip()
    proof_ref = str(artifact.get("proof_ref") or "").strip()
    proof_status = str(artifact.get("status") or "").strip() or "unknown"
    state["last_public_proof_ref"] = proof_ref
    state["last_public_proof_status"] = proof_status
    state["last_transition_at"] = _utc_now()
    items = _manifest_items(manifest)
    for item in items:
        if str(item.get("endpoint_id") or "").strip() == endpoint_id:
            item["last_public_proof"] = proof_ref
    manifest["items"] = items
    save_api_wave_manifest(root, manifest)
    if proof_status == "ok" and bool(artifact.get("user_visible_delta_confirmed")):
        completed = [item for item in state.get("completed_endpoint_ids", []) if str(item).strip()]
        if endpoint_id not in completed:
            completed.append(endpoint_id)
        state["completed_endpoint_ids"] = completed
        state["current_endpoint_id"] = ""
        state["current_owner_task_id"] = ""
        state["current_subagent_id"] = ""
        state["current_status"] = "idle_ready_for_next_endpoint"
        state["current_blocked_reason"] = ""
        state["next_endpoint_id"] = ""
        state["last_completion_at"] = _utc_now()
    else:
        state["current_status"] = "verifying_public_proof"
        state["current_endpoint_id"] = endpoint_id
        state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_id)
    save_api_wave_state(root, state)
    return load_api_wave_state(root)
