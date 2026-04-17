from __future__ import annotations

import copy
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator_paths import load_runtime_state, read_json_file, resolve_orchestrator_write_path

API_WAVE_EXECUTION_MODE = "api_autonomy_mode"
API_WAVE_MODE_ALIASES = {API_WAVE_EXECUTION_MODE, "api_autonomy"}
API_WAVE_BATCH_ID = "BATCH-API"
API_WAVE_STREAM_ID = API_WAVE_BATCH_ID
API_WAVE_SCHEMA_VERSION = "api_wave_state.v1"
API_WAVE_MANIFEST_SCHEMA_VERSION = "api_wave_manifest.v1"
API_WAVE_CANONICAL_MANIFEST_FILE = "platform/automation/config/api_wave_manifest.json"
API_WAVE_LEGACY_MANIFEST_FILE = "platform/automation/config/api_wave_manifest.v1.json"
API_WAVE_ADDITIONAL_MANIFEST_FILE = "platform/automation/config/api_wave_manifest.v1.json"
API_WAVE_CANONICAL_STATE_FILE = "api_wave_state.json"
API_WAVE_LEGACY_STATE_FILE = "api-wave-state.json"
# Backward-compat aliases still imported by runtime truth compatibility paths.
API_WAVE_MANIFEST_FILE = API_WAVE_CANONICAL_MANIFEST_FILE
API_WAVE_STATE_FILE = API_WAVE_CANONICAL_STATE_FILE
API_WAVE_PROOF_DIR = "api-wave-proofs"
PUBLIC_PROOF_OK_MARKERS = (
    "http://3.98.20.77",
    "ec2-3-98-20-77",
    "public ec2",
    "api_health_ok",
    "public api healthy",
    "proof-manifest://",
    "public-proof/",
)

DEFAULT_API_WAVE_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "endpoint_id": "copilot_search",
        "domain": "copilot",
        "route_path": "/api/search/tickers",
        "route_paths": ["/api/search/tickers", "/api/search/global", "/api/search/sectors"],
        "route_module": "apps/api/src/domains/copilot/api/search.py",
        "companion_modules": [],
        "priority": 10,
        "product_surface": "copilot",
        "shared_contract": "packages/contracts/copilot_v1.py",
        "endpoint_service": "apps/api/src/domains/copilot/application/copilot_search_endpoint_service.py",
        "parity_status": "route_local_mixed_contract",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": [
                "/api/search/tickers?q=NVDA&limit=3",
                "/api/search/global?q=NVDA&limit=3",
                "/api/search/sectors?q=AI&limit=3",
            ],
            "success_condition": "returns ok=true plus stable search metadata",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
        "label": "copilot-search",
            "required": False,
        },
    },
    {
        "endpoint_id": "copilot_universal_search",
        "domain": "copilot",
        "route_path": "/api/search/universal",
        "route_paths": ["/api/search/universal"],
        "route_module": "apps/api/src/domains/copilot/api/universal_search.py",
        "companion_modules": [],
        "priority": 20,
        "product_surface": "copilot",
        "shared_contract": "packages/contracts/copilot_v1.py",
        "endpoint_service": "apps/api/src/domains/copilot/application/universal_search.py",
        "parity_status": "legacy_route_no_shared_service_contract",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/search/universal?q=NVDA&limit=5"],
            "success_condition": "returns ok=true and universal search results",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
        "label": "copilot-universal-search",
            "required": False,
        },
    },
    {
        "endpoint_id": "forecasts_brief",
        "domain": "forecasts",
        "route_path": "/api/brief/daily",
        "route_paths": ["/api/brief/daily", "/api/brief/weekly"],
        "route_module": "apps/api/src/domains/forecasts/api/brief.py",
        "companion_modules": [],
        "priority": 30,
        "product_surface": "forecasts",
        "shared_contract": "packages/contracts/forecast_v1.py",
        "endpoint_service": "apps/api/src/domains/forecasts/application/forecasts_brief_endpoint_service.py",
        "parity_status": "route_local_contract_needs_judge_metadata",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/brief/daily", "/api/brief/weekly"],
            "success_condition": "returns ok=true with generated_at, source, and freshness",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
        "label": "forecasts-brief",
            "required": False,
        },
    },
    {
        "endpoint_id": "market_data_news_feed",
        "domain": "market_data",
        "route_path": "/api/news/feed",
        "route_paths": ["/api/news/feed"],
        "route_module": "apps/api/src/domains/market_data/api/news.py",
        "companion_modules": [],
        "priority": 40,
        "product_surface": "market_data",
        "shared_contract": "packages/contracts/market_data.py",
        "endpoint_service": "apps/api/src/domains/market_data/application/news_service.py",
        "parity_status": "mixed_route_service_contract",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/news/feed?tickers=NVDA"],
            "success_condition": "returns ok=true and stable news feed metadata",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
            "label": "market-data-news-feed",
            "required": False,
        },
    },
    {
        "endpoint_id": "market_data_stocks",
        "domain": "market_data",
        "route_path": "/api/stocks/prices",
        "route_paths": ["/api/stocks/prices"],
        "route_module": "apps/api/src/domains/market_data/api/stocks.py",
        "companion_modules": [],
        "priority": 50,
        "product_surface": "market_data",
        "shared_contract": "packages/contracts/market_data.py",
        "endpoint_service": "apps/api/src/domains/market_data/application/stocks_service.py",
        "parity_status": "legacy_route_needs_endpoint_service_parity",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/stocks/prices?ticker=NVDA"],
            "success_condition": "returns ok=true and non-empty price points",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
            "label": "market-data-stocks",
            "required": False,
        },
    },
    {
        "endpoint_id": "market_data_news_impact",
        "domain": "market_data",
        "route_path": "/api/news/analysis",
        "route_paths": ["/api/news/analysis"],
        "route_module": "apps/api/src/domains/market_data/api/news_impact.py",
        "companion_modules": [],
        "priority": 60,
        "product_surface": "market_data",
        "shared_contract": "packages/contracts/market_data.py",
        "endpoint_service": "apps/api/src/domains/market_data/application/market_data_news_impact_endpoint_service.py",
        "parity_status": "route_local_contract_needs_metadata",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/news/analysis?tickers=NVDA"],
            "success_condition": "returns ok=true and impact analysis payload",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
            "label": "market-data-news-impact",
            "required": False,
        },
    },
    {
        "endpoint_id": "market_data_analytics",
        "domain": "market_data",
        "route_path": "/api/analytics/predictions",
        "route_paths": ["/api/analytics/predictions"],
        "route_module": "apps/api/src/domains/market_data/api/analytics.py",
        "companion_modules": [],
        "priority": 80,
        "product_surface": "market_data",
        "shared_contract": "packages/contracts/market_data.py",
        "endpoint_service": "apps/api/src/domains/market_data/application/market_data_analytics_endpoint_service.py",
        "parity_status": "route_local_contract_needs_service_boundary",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/analytics/predictions?ticker=NVDA"],
            "success_condition": "returns ok=true and analytics metadata",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
            "label": "market-data-analytics",
            "required": False,
        },
    },
    {
        "endpoint_id": "market_data_stocks_client",
        "domain": "market_data",
        "route_path": "/api/stocks/search",
        "route_paths": [
            "/api/stocks/search",
            "/api/stocks/universe",
            "/api/stocks/{ticker}",
            "/api/stocks/meta",
        ],
        "route_module": "apps/api/src/domains/market_data/api/stocks_client.py",
        "companion_modules": [],
        "priority": 90,
        "product_surface": "market_data",
        "shared_contract": "packages/contracts/market_data.py",
        "endpoint_service": "apps/api/src/domains/market_data/application/market_data_stocks_client_endpoint_service.py",
        "parity_status": "client_route_needs_shared_contract_metadata",
        "last_public_proof": "none",
        "deferred_reason": "none",
        "selectable": True,
        "api_proof": {
            "kind": "public_api_smoke",
            "base_url": "http://3.98.20.77",
            "expected_endpoints": ["/api/stocks/search?q=NVDA"],
            "success_condition": "returns ok=true and stocks search metadata",
        },
        "ui_proof": {
            "kind": "public_ui_smoke",
            "url": "http://3.98.20.77/",
            "label": "market-data-stocks-client",
            "required": False,
        },
    },
)

DEFER_BLOCKER_MARKERS = (
    "provider",
    "upstream",
    "dependency",
    "external dependency",
    "vendor",
    "datasource",
    "rate_limit",
    "third-party",
)
ADMIN_BLOCKER_MARKERS = (
    "runtime",
    "control-plane",
    "control plane",
    "orchestration",
    "dispatch",
    "planner_runtime_actions",
    "sqlite",
    "queue",
    "workboard",
    "subagent",
    "public proof",
    "public_proof",
    "ec2",
    "api health",
    "smoke",
    "maintenance",
    "healthcheck",
)


def _utc_now(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> Path:
    rendered = json.dumps(payload, ensure_ascii=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(rendered)
        handle.flush()
        temp_path = Path(handle.name)
    temp_path.replace(path)
    return path


def _canonical_endpoint_id(value: Any) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return ""
    token = token.replace(" ", "-").replace("_", "-").replace(".", "-")
    token = re.sub(r"-+", "-", token)
    return token.strip("-")


def _canonical_priority(value: Any) -> str:
    token = str(value or "").strip().upper()
    if token.startswith("P") and token[1:].isdigit():
        return token
    if token.isdigit():
        return f"P{token}"
    return "P9"


def _priority_rank(value: Any) -> int:
    token = _canonical_priority(value)
    if token.startswith("P") and token[1:].isdigit():
        return int(token[1:])
    return 9


def _normalize_endpoint_ids(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        token = _canonical_endpoint_id(item)
        if token and token not in out:
            out.append(token)
    return out


def _normalize_reason_entries(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in raw:
        if isinstance(row, dict):
            endpoint_id = _canonical_endpoint_id(row.get("endpoint_id"))
            reason = str(row.get("reason") or "deferred").strip() or "deferred"
        else:
            endpoint_id = _canonical_endpoint_id(row)
            reason = "deferred"
        if endpoint_id and endpoint_id not in seen:
            out.append({"endpoint_id": endpoint_id, "reason": reason})
            seen.add(endpoint_id)
    return out


def _normalize_string_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        token = _canonical_endpoint_id(key)
        if token:
            out[token] = str(value or "").strip()
    return out


def _normalize_int_map(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        token = _canonical_endpoint_id(key)
        if not token:
            continue
        try:
            out[token] = int(value or 0)
        except Exception:
            out[token] = 0
    return out


def api_wave_manifest_path(root: Path) -> Path:
    primary = Path(root) / API_WAVE_CANONICAL_MANIFEST_FILE
    if primary.exists():
        return primary
    for relative_path in (API_WAVE_LEGACY_MANIFEST_FILE, API_WAVE_ADDITIONAL_MANIFEST_FILE):
        legacy = Path(root) / relative_path
        if legacy.exists():
            return legacy
    return primary


def api_wave_legacy_manifest_path(root: Path) -> Path:
    return Path(root) / API_WAVE_LEGACY_MANIFEST_FILE


def api_wave_state_path(root: Path) -> Path:
    primary = resolve_orchestrator_write_path(root, API_WAVE_CANONICAL_STATE_FILE, create_parent=True)
    if primary.exists():
        return primary
    legacy = resolve_orchestrator_write_path(root, API_WAVE_LEGACY_STATE_FILE, create_parent=True)
    if legacy.exists():
        return legacy
    return primary


def api_wave_owner_task_id(endpoint_id: str) -> str:
    token = _canonical_endpoint_id(endpoint_id).replace(".", "_").upper() or "ENDPOINT"
    return f"APIWAVE-{token}-DEV-01"


def _manifest_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = manifest.get("endpoints")
    if not isinstance(rows, list):
        rows = manifest.get("items")
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _normalize_manifest_item(raw: dict[str, Any], order: int) -> dict[str, Any]:
    route_path = str(raw.get("route_path") or "").strip()
    route_paths = _normalize_endpoint_ids([])
    route_paths_raw = raw.get("route_paths")
    normalized_route_paths: list[str] = []
    if isinstance(route_paths_raw, list):
        for item in route_paths_raw:
            token = str(item or "").strip()
            if token and token not in normalized_route_paths:
                normalized_route_paths.append(token)
    if route_path and route_path not in normalized_route_paths:
        normalized_route_paths.insert(0, route_path)
    api_proof = raw.get("api_proof") if isinstance(raw.get("api_proof"), dict) else {}
    ui_proof = raw.get("ui_proof") if isinstance(raw.get("ui_proof"), dict) else {}
    endpoint_id = _canonical_endpoint_id(raw.get("endpoint_id"))
    public_paths = [
        str(item).strip()
        for item in (raw.get("public_paths") if isinstance(raw.get("public_paths"), list) else normalized_route_paths)
        if str(item).strip()
    ]
    test_targets = [
        str(item).strip()
        for item in (raw.get("test_targets") if isinstance(raw.get("test_targets"), list) else [])
        if str(item).strip()
    ]
    return {
        "endpoint_id": endpoint_id,
        "domain": str(raw.get("domain") or "").strip(),
        "route_path": route_path or (normalized_route_paths[0] if normalized_route_paths else ""),
        "route_paths": normalized_route_paths,
        "route_module": str(raw.get("route_module") or "").strip(),
        "companion_modules": [
            str(item).strip()
            for item in (raw.get("companion_modules") if isinstance(raw.get("companion_modules"), list) else [])
            if str(item).strip()
        ],
        "priority": _canonical_priority(raw.get("priority")),
        "priority_rank": _priority_rank(raw.get("priority")),
        "product_surface": str(raw.get("product_surface") or "").strip(),
        "shared_contract": str(raw.get("shared_contract") or "none").strip() or "none",
        "endpoint_service": str(raw.get("endpoint_service") or "none").strip() or "none",
        "parity_status": str(raw.get("parity_status") or "unknown").strip() or "unknown",
        "last_public_proof": str(raw.get("last_public_proof") or "none").strip() or "none",
        "deferred_reason": str(raw.get("deferred_reason") or "none").strip() or "none",
        "selectable": bool(raw.get("selectable", True)),
        "grouped_under_endpoint_id": _canonical_endpoint_id(raw.get("grouped_under_endpoint_id")),
        "public_smoke_reuse_from": _canonical_endpoint_id(raw.get("public_smoke_reuse_from")),
        "owner_task_id": api_wave_owner_task_id(endpoint_id),
        "stream_id": API_WAVE_STREAM_ID,
        "batch_id": API_WAVE_BATCH_ID,
        "public_paths": public_paths,
        "test_targets": test_targets,
        "api_proof": {
            "kind": str(api_proof.get("kind") or "public_api_smoke").strip() or "public_api_smoke",
            "base_url": str(api_proof.get("base_url") or "http://3.98.20.77").strip() or "http://3.98.20.77",
            "expected_endpoints": [
                str(item).strip()
                for item in (api_proof.get("expected_endpoints") if isinstance(api_proof.get("expected_endpoints"), list) else [])
                if str(item).strip()
            ],
            "success_condition": str(api_proof.get("success_condition") or "returns stable ok=true contract").strip()
            or "returns stable ok=true contract",
        },
        "ui_proof": {
            "kind": str(ui_proof.get("kind") or "public_ui_smoke").strip() or "public_ui_smoke",
            "url": str(ui_proof.get("url") or "http://3.98.20.77/").strip() or "http://3.98.20.77/",
            "label": str(ui_proof.get("label") or endpoint_id.replace("_", "-")).strip() or endpoint_id.replace("_", "-"),
            "required": bool(ui_proof.get("required", False)),
        },
        "order": order,
    }


def _manifest_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        _normalize_manifest_item(raw, idx)
        for idx, raw in enumerate(_manifest_rows(manifest))
        if _canonical_endpoint_id(raw.get("endpoint_id"))
    ]
    items.sort(key=lambda item: (int(item.get("priority_rank") or 9), int(item.get("order") or 0)))
    return items


def default_api_wave_manifest() -> dict[str, Any]:
    items = copy.deepcopy(list(DEFAULT_API_WAVE_ITEMS))
    return {
        "schema_version": API_WAVE_MANIFEST_SCHEMA_VERSION,
        "mode": API_WAVE_EXECUTION_MODE,
        "enabled": False,
        "wave_id": API_WAVE_BATCH_ID,
        "batch_id": API_WAVE_BATCH_ID,
        "stream_id": API_WAVE_STREAM_ID,
        "domains": ["copilot", "forecasts", "market_data"],
        "excluded_domains": ["judge", "dashboard", "monitor", "runtime", "admin", "control_plane"],
        "endpoints": items,
        "items": copy.deepcopy(items),
        "updated_at": "",
    }


def default_api_wave_state() -> dict[str, Any]:
    return {
        "schema_version": API_WAVE_SCHEMA_VERSION,
        "mode": API_WAVE_EXECUTION_MODE,
        "wave_id": API_WAVE_BATCH_ID,
        "wave_batch_id": API_WAVE_BATCH_ID,
        "batch_id": API_WAVE_BATCH_ID,
        "stream_id": API_WAVE_STREAM_ID,
        "current_endpoint_id": "",
        "current_task_id": "",
        "current_owner_task_id": "",
        "current_status": "idle_ready_for_next_endpoint",
        "current_endpoint_status": "idle_ready_for_next_endpoint",
        "current_dispatch_backend": "",
        "current_blocked_reason": "",
        "completed_endpoint_ids": [],
        "deferred_endpoint_ids": [],
        "deferred_endpoints": [],
        "blocked_endpoint_ids": [],
        "parity_status_by_endpoint": {},
        "last_public_proof_by_endpoint": {},
        "deferred_reason_by_endpoint": {},
        "consecutive_non_runtime_blocks": {},
        "consecutive_block_count_by_endpoint": {},
        "no_delta_streak_by_role": {},
        "last_public_proof_ref": "",
        "last_public_proof_status": "",
        "last_meaningful_delta_at": "",
        "last_completed_endpoint_id": "",
        "next_endpoint_id": "",
        "updated_at": "",
        "last_state_change_at": "",
        "last_dispatch_at": "",
        "last_completion_at": "",
        "scrum_escalated_endpoint_ids": [],
        "last_observed_task_status": "",
        "last_observed_task_updated_at": "",
        "last_observed_blocking_issue": "",
        "last_proof_ref": "",
        "completed_endpoints": [],
        "blocked_streaks": {},
    }


def _normalize_manifest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = default_api_wave_manifest()
    if isinstance(payload, dict):
        normalized.update(payload)
    items = _manifest_items(normalized)
    normalized["schema_version"] = API_WAVE_MANIFEST_SCHEMA_VERSION
    normalized["mode"] = API_WAVE_EXECUTION_MODE
    normalized["wave_id"] = API_WAVE_BATCH_ID
    normalized["batch_id"] = API_WAVE_BATCH_ID
    normalized["stream_id"] = API_WAVE_STREAM_ID
    normalized["enabled"] = bool(normalized.get("enabled", True))
    normalized["endpoints"] = items
    normalized["items"] = copy.deepcopy(items)
    return normalized


def _normalize_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = default_api_wave_state()
    if isinstance(payload, dict):
        normalized.update(payload)
    normalized["schema_version"] = API_WAVE_SCHEMA_VERSION
    normalized["mode"] = API_WAVE_EXECUTION_MODE
    normalized["wave_id"] = API_WAVE_BATCH_ID
    normalized["wave_batch_id"] = API_WAVE_BATCH_ID
    normalized["batch_id"] = API_WAVE_BATCH_ID
    normalized["stream_id"] = API_WAVE_STREAM_ID
    normalized["current_endpoint_id"] = _canonical_endpoint_id(normalized.get("current_endpoint_id"))
    normalized["current_task_id"] = str(normalized.get("current_task_id") or normalized.get("current_owner_task_id") or "").strip()
    normalized["current_owner_task_id"] = str(normalized.get("current_owner_task_id") or normalized.get("current_task_id") or "").strip()
    if normalized["current_endpoint_id"]:
        expected_owner_task_id = api_wave_owner_task_id(normalized["current_endpoint_id"])
        normalized["current_owner_task_id"] = expected_owner_task_id
        normalized["current_task_id"] = expected_owner_task_id
    normalized["current_status"] = (
        str(normalized.get("current_status") or normalized.get("current_endpoint_status") or "idle_ready_for_next_endpoint").strip()
        or "idle_ready_for_next_endpoint"
    )
    normalized["current_endpoint_status"] = normalized["current_status"]
    normalized["completed_endpoint_ids"] = _normalize_endpoint_ids(normalized.get("completed_endpoint_ids"))
    normalized["deferred_endpoint_ids"] = _normalize_endpoint_ids(normalized.get("deferred_endpoint_ids"))
    normalized["deferred_endpoints"] = _normalize_reason_entries(normalized.get("deferred_endpoints"))
    normalized["blocked_endpoint_ids"] = _normalize_endpoint_ids(normalized.get("blocked_endpoint_ids"))
    normalized["parity_status_by_endpoint"] = _normalize_string_map(normalized.get("parity_status_by_endpoint"))
    normalized["last_public_proof_by_endpoint"] = _normalize_string_map(normalized.get("last_public_proof_by_endpoint"))
    normalized["deferred_reason_by_endpoint"] = _normalize_string_map(normalized.get("deferred_reason_by_endpoint"))
    blocks = normalized.get("consecutive_non_runtime_blocks")
    if not isinstance(blocks, dict):
        blocks = normalized.get("consecutive_block_count_by_endpoint")
    normalized["consecutive_non_runtime_blocks"] = _normalize_int_map(blocks)
    normalized["consecutive_block_count_by_endpoint"] = dict(normalized["consecutive_non_runtime_blocks"])
    normalized["no_delta_streak_by_role"] = _normalize_int_map(normalized.get("no_delta_streak_by_role"))
    normalized["scrum_escalated_endpoint_ids"] = _normalize_endpoint_ids(normalized.get("scrum_escalated_endpoint_ids"))
    normalized["last_public_proof_ref"] = str(
        normalized.get("last_public_proof_ref") or normalized.get("last_proof_ref") or ""
    ).strip()
    normalized["last_proof_ref"] = normalized["last_public_proof_ref"]
    normalized["last_completed_endpoint_id"] = _canonical_endpoint_id(normalized.get("last_completed_endpoint_id"))
    normalized["next_endpoint_id"] = _canonical_endpoint_id(normalized.get("next_endpoint_id"))
    normalized["completed_endpoints"] = list(normalized["completed_endpoint_ids"])
    normalized["blocked_streaks"] = dict(normalized["consecutive_non_runtime_blocks"])
    return normalized


def load_api_wave_manifest(root: Path, *, persist_defaults: bool = False) -> dict[str, Any]:
    payload = read_json_file(api_wave_manifest_path(root))
    if not isinstance(payload, dict):
        payload = default_api_wave_manifest()
        if persist_defaults:
            save_api_wave_manifest(root, payload)
    return _normalize_manifest_payload(payload)


def save_api_wave_manifest(root: Path, payload: dict[str, Any]) -> Path:
    normalized = _normalize_manifest_payload(payload)
    normalized["updated_at"] = _utc_now()
    _atomic_write_json(api_wave_legacy_manifest_path(root), normalized)
    return _atomic_write_json(api_wave_manifest_path(root), normalized)


def load_api_wave_state(root: Path, *, persist_defaults: bool = False) -> dict[str, Any]:
    payload = read_json_file(api_wave_state_path(root))
    if not isinstance(payload, dict):
        payload = default_api_wave_state()
        if persist_defaults:
            save_api_wave_state(root, payload)
    return _normalize_state_payload(payload)


def save_api_wave_state(root: Path, payload: dict[str, Any]) -> Path:
    normalized = _normalize_state_payload(payload)
    normalized["updated_at"] = _utc_now()
    canonical = resolve_orchestrator_write_path(root, API_WAVE_CANONICAL_STATE_FILE, create_parent=True)
    legacy = resolve_orchestrator_write_path(root, API_WAVE_LEGACY_STATE_FILE, create_parent=True)
    _atomic_write_json(legacy, normalized)
    return _atomic_write_json(canonical, normalized)


def api_wave_mode_enabled(root: Path) -> bool:
    runtime_state = load_runtime_state(root)
    execution_mode = str(runtime_state.get("execution_mode") or "").strip().lower()
    if execution_mode:
        return execution_mode in API_WAVE_MODE_ALIASES
    manifest = load_api_wave_manifest(root, persist_defaults=False)
    return bool(manifest.get("enabled", False))


def get_api_wave_entry(manifest: dict[str, Any], endpoint_id: str) -> dict[str, Any] | None:
    token = _canonical_endpoint_id(endpoint_id)
    if not token:
        return None
    for item in _manifest_items(manifest):
        if _canonical_endpoint_id(item.get("endpoint_id")) == token:
            return item
    return None


def entry_for_batch_id(root: Path, batch_id: str) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    state = load_api_wave_state(root, persist_defaults=True)
    token = str(batch_id or "").strip().upper()
    if not token:
        return None, manifest, state
    current_entry = get_api_wave_entry(manifest, state.get("current_endpoint_id"))
    next_entry = get_api_wave_entry(manifest, state.get("next_endpoint_id"))
    if token in {API_WAVE_BATCH_ID, "BATCH-API", "API-WAVE"}:
        return current_entry or next_entry, manifest, state
    for item in _manifest_items(manifest):
        endpoint_id = str(item.get("endpoint_id") or "").strip()
        owner_task_id = api_wave_owner_task_id(endpoint_id)
        if token in {
            endpoint_id.upper(),
            endpoint_id.replace("_", "-").upper(),
            owner_task_id.upper(),
        }:
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
            "success_condition": str(api_proof.get("success_condition") or "returns stable ok=true contract").strip()
            or "returns stable ok=true contract",
        },
        "ui_proof": {
            "kind": str(ui_proof.get("kind") or "public_ui_smoke").strip() or "public_ui_smoke",
            "url": str(ui_proof.get("url") or "http://3.98.20.77/").strip() or "http://3.98.20.77/",
            "label": str(ui_proof.get("label") or endpoint_id.replace("_", "-")).strip() or endpoint_id.replace("_", "-"),
            "required": bool(ui_proof.get("required", False)),
        },
        "done_when": "public_proof_status=ok && user_visible_delta_confirmed=true",
    }


def _completed_ids(state: dict[str, Any]) -> set[str]:
    return set(_normalize_endpoint_ids(state.get("completed_endpoint_ids")))


def _deferred_ids(state: dict[str, Any]) -> set[str]:
    return set(_normalize_endpoint_ids(state.get("deferred_endpoint_ids")))


def select_next_endpoint(manifest: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    completed = _completed_ids(state)
    deferred = _deferred_ids(state)
    current = _canonical_endpoint_id(state.get("current_endpoint_id"))
    items = _manifest_items(manifest)
    if current and current not in completed and current not in deferred:
        current_entry = get_api_wave_entry(manifest, current)
        if current_entry is not None:
            return current_entry
    for item in items:
        endpoint_id = _canonical_endpoint_id(item.get("endpoint_id"))
        if not endpoint_id or endpoint_id in completed or endpoint_id in deferred:
            continue
        if not bool(item.get("selectable", True)):
            continue
        return item
    return None


def _next_selectable_after(manifest: dict[str, Any], state: dict[str, Any], current_endpoint_id: str) -> str:
    current = _canonical_endpoint_id(current_endpoint_id)
    completed = _completed_ids(state)
    deferred = _deferred_ids(state)
    for item in _manifest_items(manifest):
        endpoint_id = _canonical_endpoint_id(item.get("endpoint_id"))
        if (
            endpoint_id
            and endpoint_id != current
            and endpoint_id not in completed
            and endpoint_id not in deferred
            and bool(item.get("selectable", True))
        ):
            return endpoint_id
    return ""


def api_wave_proof_path(root: Path, endpoint_id: str) -> Path:
    token = _canonical_endpoint_id(endpoint_id).replace(".", "__")
    token = re.sub(r"[^a-z0-9_]+", "_", token)
    token = re.sub(r"_+", "_", token).strip("_") or "unknown"
    return resolve_orchestrator_write_path(root, f"{API_WAVE_PROOF_DIR}/{token}.json", create_parent=True)


def load_api_wave_proof(root: Path, endpoint_id: str) -> dict[str, Any]:
    payload = read_json_file(api_wave_proof_path(root, endpoint_id))
    return payload if isinstance(payload, dict) else {}


def persist_api_wave_proof(root: Path, endpoint_id: str, payload: dict[str, Any]) -> Path:
    artifact = dict(payload) if isinstance(payload, dict) else {}
    artifact["endpoint_id"] = _canonical_endpoint_id(endpoint_id)
    artifact["timestamp"] = str(artifact.get("timestamp") or _utc_now()).strip() or _utc_now()
    proof_ref = str(artifact.get("proof_ref") or "").strip()
    if not proof_ref:
        artifact["proof_ref"] = str(api_wave_proof_path(root, endpoint_id))
    return _atomic_write_json(api_wave_proof_path(root, endpoint_id), artifact)


def ensure_current_endpoint(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    state = load_api_wave_state(root, persist_defaults=True)
    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
    current_status = str(state.get("current_status") or "").strip().lower()
    entry = get_api_wave_entry(manifest, current_endpoint_id) if current_endpoint_id else None
    if entry is not None and current_status not in {"completed", "deferred", "idle_exhausted"}:
        state["next_endpoint_id"] = _next_selectable_after(manifest, state, current_endpoint_id)
        save_api_wave_state(root, state)
        return manifest, load_api_wave_state(root), entry
    selected = select_next_endpoint(manifest, state)
    if selected is None:
        state["current_endpoint_id"] = ""
        state["current_task_id"] = ""
        state["current_owner_task_id"] = ""
        state["current_status"] = "idle_exhausted"
        state["current_endpoint_status"] = "idle_exhausted"
        state["next_endpoint_id"] = ""
        state["current_blocked_reason"] = ""
        state["last_state_change_at"] = _utc_now()
        save_api_wave_state(root, state)
        return manifest, load_api_wave_state(root), None
    endpoint_id = str(selected.get("endpoint_id") or "").strip()
    owner_task_id = api_wave_owner_task_id(endpoint_id)
    state["current_endpoint_id"] = endpoint_id
    state["current_task_id"] = owner_task_id
    state["current_owner_task_id"] = owner_task_id
    state["current_status"] = "ready_for_dispatch"
    state["current_endpoint_status"] = "ready_for_dispatch"
    state["current_blocked_reason"] = ""
    state["next_endpoint_id"] = _next_selectable_after(manifest, state, endpoint_id)
    state["last_state_change_at"] = _utc_now()
    save_api_wave_state(root, state)
    return manifest, load_api_wave_state(root), selected


def should_defer_blocker(reason: str) -> bool:
    token = " ".join(str(reason or "").lower().split())
    return bool(token) and any(marker in token for marker in DEFER_BLOCKER_MARKERS)


def _should_route_admin(reason: str) -> bool:
    token = " ".join(str(reason or "").lower().split())
    return bool(token) and any(marker in token for marker in ADMIN_BLOCKER_MARKERS)


def _update_manifest_endpoint(
    manifest: dict[str, Any],
    endpoint_id: str,
    *,
    last_public_proof: str | None = None,
    deferred_reason: str | None = None,
    parity_status: str | None = None,
) -> dict[str, Any]:
    items = _manifest_items(manifest)
    endpoint_token = _canonical_endpoint_id(endpoint_id)
    for item in items:
        if _canonical_endpoint_id(item.get("endpoint_id")) != endpoint_token:
            continue
        if last_public_proof is not None:
            item["last_public_proof"] = str(last_public_proof or "none").strip() or "none"
        if deferred_reason is not None:
            item["deferred_reason"] = str(deferred_reason or "none").strip() or "none"
        if parity_status is not None:
            item["parity_status"] = str(parity_status or "unknown").strip() or "unknown"
    manifest["endpoints"] = items
    manifest["items"] = copy.deepcopy(items)
    return manifest


def record_dispatch(root: Path, *, endpoint_id: str, subagent_id: str, backend: str) -> dict[str, Any]:
    state = load_api_wave_state(root, persist_defaults=True)
    endpoint_token = _canonical_endpoint_id(endpoint_id)
    state["current_endpoint_id"] = endpoint_token
    state["current_task_id"] = api_wave_owner_task_id(endpoint_token)
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_token)
    state["current_dispatch_backend"] = str(backend or "").strip()
    state["current_status"] = "active_delivery"
    state["current_endpoint_status"] = "active_delivery"
    state["current_blocked_reason"] = ""
    state["last_dispatch_at"] = _utc_now()
    state["last_state_change_at"] = state["last_dispatch_at"]
    state["blocked_endpoint_ids"] = [item for item in _normalize_endpoint_ids(state.get("blocked_endpoint_ids")) if item != endpoint_token]
    save_api_wave_state(root, state)
    return load_api_wave_state(root)


def record_delivery_ready_for_proof(root: Path, *, endpoint_id: str) -> dict[str, Any]:
    state = load_api_wave_state(root, persist_defaults=True)
    endpoint_token = _canonical_endpoint_id(endpoint_id)
    state["current_endpoint_id"] = endpoint_token
    state["current_task_id"] = api_wave_owner_task_id(endpoint_token)
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_token)
    state["current_status"] = "verifying_public_proof"
    state["current_endpoint_status"] = "verifying_public_proof"
    state["current_blocked_reason"] = ""
    state["last_meaningful_delta_at"] = _utc_now()
    state["last_state_change_at"] = state["last_meaningful_delta_at"]
    save_api_wave_state(root, state)
    return load_api_wave_state(root)


def _mark_deferred(
    root: Path,
    *,
    state: dict[str, Any],
    manifest: dict[str, Any],
    endpoint_token: str,
    reason: str,
) -> dict[str, Any]:
    deferred_ids = _normalize_endpoint_ids(state.get("deferred_endpoint_ids"))
    if endpoint_token not in deferred_ids:
        deferred_ids.append(endpoint_token)
    deferred_endpoints = _normalize_reason_entries(state.get("deferred_endpoints"))
    if not any(row["endpoint_id"] == endpoint_token for row in deferred_endpoints):
        deferred_endpoints.append({"endpoint_id": endpoint_token, "reason": reason})
    deferred_reason_map = _normalize_string_map(state.get("deferred_reason_by_endpoint"))
    deferred_reason_map[endpoint_token] = reason
    blocked_ids = [item for item in _normalize_endpoint_ids(state.get("blocked_endpoint_ids")) if item != endpoint_token]
    state["deferred_endpoint_ids"] = deferred_ids
    state["deferred_endpoints"] = deferred_endpoints
    state["deferred_reason_by_endpoint"] = deferred_reason_map
    state["blocked_endpoint_ids"] = blocked_ids
    state["current_endpoint_id"] = ""
    state["current_task_id"] = ""
    state["current_owner_task_id"] = ""
    state["current_status"] = "deferred"
    state["current_endpoint_status"] = "deferred"
    state["current_blocked_reason"] = reason
    state["next_endpoint_id"] = ""
    state["last_state_change_at"] = _utc_now()
    save_api_wave_state(root, state)
    save_api_wave_manifest(root, _update_manifest_endpoint(manifest, endpoint_token, deferred_reason=reason))
    ensure_current_endpoint(root)
    return load_api_wave_state(root)


def record_blocked_or_deferred(root: Path, *, endpoint_id: str, reason: str) -> dict[str, Any]:
    state = load_api_wave_state(root, persist_defaults=True)
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    endpoint_token = _canonical_endpoint_id(endpoint_id)
    reason_token = str(reason or "blocked").strip() or "blocked"
    blocked_ids = _normalize_endpoint_ids(state.get("blocked_endpoint_ids"))
    if endpoint_token not in blocked_ids:
        blocked_ids.append(endpoint_token)
    state["blocked_endpoint_ids"] = blocked_ids
    state["current_endpoint_id"] = endpoint_token
    state["current_task_id"] = api_wave_owner_task_id(endpoint_token)
    state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_token)
    state["current_blocked_reason"] = reason_token
    state["last_meaningful_delta_at"] = _utc_now()
    state["last_state_change_at"] = state["last_meaningful_delta_at"]

    if should_defer_blocker(reason_token):
        return _mark_deferred(root, state=state, manifest=manifest, endpoint_token=endpoint_token, reason=reason_token)

    if _should_route_admin(reason_token):
        state["current_status"] = "blocked_route_admin"
        state["current_endpoint_status"] = "blocked_route_admin"
        save_api_wave_state(root, state)
        return load_api_wave_state(root)

    counts = _normalize_int_map(state.get("consecutive_non_runtime_blocks"))
    counts[endpoint_token] = int(counts.get(endpoint_token, 0) or 0) + 1
    state["consecutive_non_runtime_blocks"] = counts
    state["consecutive_block_count_by_endpoint"] = dict(counts)
    if counts[endpoint_token] >= 3:
        return _mark_deferred(root, state=state, manifest=manifest, endpoint_token=endpoint_token, reason=reason_token)
    if counts[endpoint_token] >= 2:
        escalated = _normalize_endpoint_ids(state.get("scrum_escalated_endpoint_ids"))
        if endpoint_token not in escalated:
            escalated.append(endpoint_token)
        state["scrum_escalated_endpoint_ids"] = escalated
        state["current_status"] = "blocked_escalate_scrum"
        state["current_endpoint_status"] = "blocked_escalate_scrum"
    else:
        state["current_status"] = "blocked"
        state["current_endpoint_status"] = "blocked"
    save_api_wave_state(root, state)
    return load_api_wave_state(root)


def apply_public_proof_result(root: Path, *, batch_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    entry, manifest, state = entry_for_batch_id(root, batch_id)
    if entry is None:
        return state
    endpoint_id = str(entry.get("endpoint_id") or "").strip()
    endpoint_token = _canonical_endpoint_id(endpoint_id)
    proof_ref = str(artifact.get("proof_ref") or "").strip()
    proof_status = str(artifact.get("status") or "").strip().lower() or "unknown"
    proof_map = _normalize_string_map(state.get("last_public_proof_by_endpoint"))
    proof_map[endpoint_token] = proof_ref or "none"
    parity_map = _normalize_string_map(state.get("parity_status_by_endpoint"))
    parity_map[endpoint_token] = "public_proof_ok" if proof_status == "ok" else "public_proof_pending"
    state["last_public_proof_by_endpoint"] = proof_map
    state["parity_status_by_endpoint"] = parity_map
    state["last_public_proof_ref"] = proof_ref
    state["last_public_proof_status"] = proof_status
    state["last_state_change_at"] = _utc_now()

    manifest = _update_manifest_endpoint(
        manifest,
        endpoint_token,
        last_public_proof=proof_ref or "none",
        deferred_reason="none",
        parity_status="public_proof_ok" if proof_status == "ok" else str(entry.get("parity_status") or "unknown"),
    )

    inherited_completion_ids: list[str] = []
    for item in _manifest_items(manifest):
        item_token = _canonical_endpoint_id(item.get("endpoint_id"))
        if (
            _canonical_endpoint_id(item.get("grouped_under_endpoint_id")) == endpoint_token
            or _canonical_endpoint_id(item.get("public_smoke_reuse_from")) == endpoint_token
        ):
            inherited_completion_ids.append(item_token)
            proof_map[item_token] = proof_ref or "none"
            parity_map[item_token] = "public_proof_ok" if proof_status == "ok" else str(item.get("parity_status") or "unknown")
            manifest = _update_manifest_endpoint(
                manifest,
                item_token,
                last_public_proof=proof_ref or "none",
                deferred_reason=str(item.get("deferred_reason") or "none"),
                parity_status=parity_map[item_token],
            )

    save_api_wave_manifest(root, manifest)
    state["last_public_proof_by_endpoint"] = proof_map
    state["parity_status_by_endpoint"] = parity_map

    if proof_status == "ok" and bool(artifact.get("user_visible_delta_confirmed")):
        completed = _normalize_endpoint_ids(state.get("completed_endpoint_ids"))
        for item in [endpoint_token, *inherited_completion_ids]:
            if item and item not in completed:
                completed.append(item)
        state["completed_endpoint_ids"] = completed
        state["current_endpoint_id"] = ""
        state["current_task_id"] = ""
        state["current_owner_task_id"] = ""
        state["current_status"] = "idle_ready_for_next_endpoint"
        state["current_endpoint_status"] = "idle_ready_for_next_endpoint"
        state["current_blocked_reason"] = ""
        state["last_completed_endpoint_id"] = endpoint_token
        state["next_endpoint_id"] = ""
        state["last_completion_at"] = _utc_now()
        state["blocked_endpoint_ids"] = [
            item
            for item in _normalize_endpoint_ids(state.get("blocked_endpoint_ids"))
            if item not in {endpoint_token, *inherited_completion_ids}
        ]
        counts = _normalize_int_map(state.get("consecutive_non_runtime_blocks"))
        for item in [endpoint_token, *inherited_completion_ids]:
            counts.pop(item, None)
        state["consecutive_non_runtime_blocks"] = counts
        state["consecutive_block_count_by_endpoint"] = dict(counts)
        deferred_ids = [item for item in _normalize_endpoint_ids(state.get("deferred_endpoint_ids")) if item not in inherited_completion_ids]
        state["deferred_endpoint_ids"] = deferred_ids
    else:
        state["current_status"] = "verifying_public_proof"
        state["current_endpoint_status"] = "verifying_public_proof"
        state["current_endpoint_id"] = endpoint_token
        state["current_task_id"] = api_wave_owner_task_id(endpoint_token)
        state["current_owner_task_id"] = api_wave_owner_task_id(endpoint_token)

    save_api_wave_state(root, state)
    if proof_status == "ok" and bool(artifact.get("user_visible_delta_confirmed")):
        ensure_current_endpoint(root)
    return load_api_wave_state(root)


def _latest_task_state(states: list[dict[str, Any]], owner_task_id: str) -> dict[str, Any] | None:
    target = str(owner_task_id or "").strip()
    if not target:
        return None
    for row in states:
        if str(row.get("task_id") or "").strip() == target:
            return row
    return None


def _state_has_public_proof_ok(row: dict[str, Any] | None) -> bool:
    if not isinstance(row, dict):
        return False
    haystack = " | ".join(
        str(row.get(key) or "")
        for key in ("artifact", "verify", "proof_manifest", "summary")
    ).lower()
    return any(marker in haystack for marker in PUBLIC_PROOF_OK_MARKERS)


def build_api_wave_snapshot(
    root: Path,
    *,
    delivery_state: dict[str, Any] | None = None,
    normalized_states: list[dict[str, Any]] | None = None,
    prior_state: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = Path(root)
    delivery = delivery_state if isinstance(delivery_state, dict) else {}
    manifest = load_api_wave_manifest(root, persist_defaults=True)
    enabled = api_wave_mode_enabled(root)
    state = load_api_wave_state(root, persist_defaults=True)
    if isinstance(prior_state, dict):
        merged = dict(prior_state)
        merged.update(state)
        state = _normalize_state_payload(merged)

    latest_states = normalized_states if isinstance(normalized_states, list) else []
    completed_endpoint_ids = _normalize_endpoint_ids(state.get("completed_endpoint_ids"))
    deferred_endpoint_ids = _normalize_endpoint_ids(state.get("deferred_endpoint_ids"))
    blocked_endpoint_ids = _normalize_endpoint_ids(state.get("blocked_endpoint_ids"))
    parity_status_by_endpoint = _normalize_string_map(state.get("parity_status_by_endpoint"))
    last_public_proof_by_endpoint = _normalize_string_map(state.get("last_public_proof_by_endpoint"))
    deferred_reason_by_endpoint = _normalize_string_map(state.get("deferred_reason_by_endpoint"))
    consecutive_block_count_by_endpoint = _normalize_int_map(
        state.get("consecutive_block_count_by_endpoint")
    )
    no_delta_streak_by_role = _normalize_int_map(state.get("no_delta_streak_by_role"))

    current_endpoint_id = str(state.get("current_endpoint_id") or "").strip()
    current_task_id = str(
        state.get("current_task_id") or state.get("current_owner_task_id") or ""
    ).strip()
    current_status = str(
        state.get("current_status") or "idle_ready_for_next_endpoint"
    ).strip().lower()
    last_public_proof_ref = str(
        state.get("last_public_proof_ref") or state.get("last_proof_ref") or "none"
    ).strip() or "none"

    if current_endpoint_id:
        latest_state = _latest_task_state(
            latest_states,
            current_task_id or api_wave_owner_task_id(current_endpoint_id),
        )
        latest_status = str((latest_state or {}).get("status") or "").strip().lower()
        if latest_status in {"ready_to_merge", "merged", "completed", "done"} and _state_has_public_proof_ok(latest_state):
            endpoint_token = _canonical_endpoint_id(current_endpoint_id)
            if endpoint_token and endpoint_token not in completed_endpoint_ids:
                completed_endpoint_ids.append(endpoint_token)
            last_public_proof_ref = (
                str((latest_state or {}).get("proof_manifest") or "").strip()
                or str((latest_state or {}).get("artifact") or "").strip()
                or str((latest_state or {}).get("verify") or "").strip()
                or last_public_proof_ref
            )
            if endpoint_token:
                last_public_proof_by_endpoint[endpoint_token] = last_public_proof_ref or "none"
                parity_status_by_endpoint[endpoint_token] = "public_proof_ok"
            current_endpoint_id = ""
            current_task_id = ""
            current_status = "idle_ready_for_next_endpoint"

    if enabled:
        _, refreshed_state, current_entry = ensure_current_endpoint(root)
    else:
        refreshed_state = load_api_wave_state(root, persist_defaults=True)
        current_entry = None
    state.update(refreshed_state)

    current_endpoint_id = str(
        state.get("current_endpoint_id") or current_endpoint_id or ""
    ).strip()
    current_task_id = str(
        state.get("current_task_id")
        or state.get("current_owner_task_id")
        or current_task_id
        or ""
    ).strip()
    current_status = str(
        state.get("current_status") or current_status or "idle_ready_for_next_endpoint"
    ).strip().lower()
    current_entry = current_entry or get_api_wave_entry(manifest, current_endpoint_id)
    next_entry = select_next_endpoint(
        manifest,
        {
            "current_endpoint_id": current_endpoint_id,
            "completed_endpoint_ids": completed_endpoint_ids,
            "deferred_endpoint_ids": deferred_endpoint_ids,
            "blocked_endpoint_ids": blocked_endpoint_ids,
        },
    )
    if (
        current_entry is not None
        and next_entry is not None
        and _canonical_endpoint_id(next_entry.get("endpoint_id"))
        == _canonical_endpoint_id(current_entry.get("endpoint_id"))
    ):
        next_entry = None

    active_batch_id = str(delivery.get("active_batch_id") or "").strip()
    ec2_reachable = bool(delivery.get("ec2_reachable", False))
    if current_status in {"blocked", "blocked_route_admin", "blocked_escalate_scrum"}:
        dispatch_ready = False
    else:
        dispatch_ready = bool(
            enabled
            and current_entry is not None
            and ec2_reachable
            and not active_batch_id
            and current_status
            not in {"verifying_public_proof", "deferred", "idle_exhausted", "active_delivery"}
        )

    manifest_items = _manifest_items(manifest)
    for item in manifest_items:
        endpoint_token = _canonical_endpoint_id(item.get("endpoint_id"))
        if not endpoint_token:
            continue
        parity_status_by_endpoint.setdefault(
            endpoint_token, str(item.get("parity_status") or "unknown").strip() or "unknown"
        )
        proof_ref = str(item.get("last_public_proof") or "").strip()
        if proof_ref:
            last_public_proof_by_endpoint.setdefault(endpoint_token, proof_ref)
        deferred_reason = str(item.get("deferred_reason") or "").strip()
        if deferred_reason and deferred_reason.lower() not in {"", "none"}:
            deferred_reason_by_endpoint.setdefault(endpoint_token, deferred_reason)

    blocked_endpoint_ids = sorted(
        endpoint_id
        for endpoint_id, count in consecutive_block_count_by_endpoint.items()
        if int(count or 0) > 0 and endpoint_id not in set(deferred_endpoint_ids)
    )

    state["completed_endpoint_ids"] = completed_endpoint_ids
    state["deferred_endpoint_ids"] = deferred_endpoint_ids
    state["blocked_endpoint_ids"] = blocked_endpoint_ids
    state["parity_status_by_endpoint"] = parity_status_by_endpoint
    state["last_public_proof_by_endpoint"] = last_public_proof_by_endpoint
    state["deferred_reason_by_endpoint"] = deferred_reason_by_endpoint
    state["consecutive_block_count_by_endpoint"] = consecutive_block_count_by_endpoint
    state["no_delta_streak_by_role"] = no_delta_streak_by_role
    state["last_public_proof_ref"] = last_public_proof_ref
    state["last_proof_ref"] = last_public_proof_ref
    state["wave_batch_id"] = API_WAVE_BATCH_ID
    state["next_endpoint_id"] = str((next_entry or {}).get("endpoint_id") or "").strip()
    state["last_state_change_at"] = str(
        state.get("last_state_change_at") or state.get("updated_at") or _utc_now(now)
    ).strip()
    save_api_wave_state(root, state)
    state = load_api_wave_state(root, persist_defaults=True)

    reason = (
        "disabled"
        if not enabled
        else "external_outage"
        if not ec2_reachable
        else "waiting_active_batch"
        if active_batch_id
        else "waiting_public_proof"
        if current_status == "verifying_public_proof"
        else "dispatch_ready"
        if dispatch_ready
        else "route_admin"
        if current_status == "blocked_route_admin"
        else "blocked"
        if current_status in {"blocked", "blocked_escalate_scrum"}
        else "active_delivery"
        if current_status in {"active_delivery", "running"}
        else "idle"
    )

    selectable_remaining = [
        _canonical_endpoint_id(item.get("endpoint_id"))
        for item in manifest_items
        if bool(item.get("selectable", True))
        and _canonical_endpoint_id(item.get("endpoint_id"))
        not in set(completed_endpoint_ids) | set(deferred_endpoint_ids)
    ]
    if current_status in {"active_delivery", "running", "verifying_public_proof", "blocked", "blocked_route_admin", "blocked_escalate_scrum"} and current_entry is not None:
        remaining_count = max(1, len(selectable_remaining))
    else:
        remaining_count = max(
            0,
            len(
                [
                    endpoint_id
                    for endpoint_id in selectable_remaining
                    if endpoint_id
                    != _canonical_endpoint_id((current_entry or {}).get("endpoint_id"))
                ]
            ),
        )

    return {
        "enabled": enabled,
        "mode": API_WAVE_EXECUTION_MODE,
        "wave_id": API_WAVE_STREAM_ID,
        "wave_batch_id": API_WAVE_BATCH_ID,
        "stream_id": API_WAVE_STREAM_ID,
        "manifest_path": str(api_wave_manifest_path(root)),
        "state_path": str(api_wave_state_path(root)),
        "manifest_version": str(
            manifest.get("schema_version") or API_WAVE_MANIFEST_SCHEMA_VERSION
        ).strip()
        or API_WAVE_MANIFEST_SCHEMA_VERSION,
        "state_version": API_WAVE_SCHEMA_VERSION,
        "state": state,
        "current_endpoint": current_entry,
        "current_endpoint_id": str(
            (current_entry or {}).get("endpoint_id") or current_endpoint_id or ""
        ).strip()
        or None,
        "current_task_id": current_task_id or None,
        "current_status": current_status or "idle_ready_for_next_endpoint",
        "current_proof_status": str(state.get("last_public_proof_status") or "none").strip() or "none",
        "next_endpoint": next_entry,
        "next_endpoint_id": str((next_entry or {}).get("endpoint_id") or "").strip() or None,
        "dispatch_ready": dispatch_ready,
        "completed_endpoint_ids": completed_endpoint_ids,
        "completed_endpoints": completed_endpoint_ids,
        "deferred_endpoint_ids": deferred_endpoint_ids,
        "deferred_endpoints": [
            {"endpoint_id": endpoint_id, "reason": deferred_reason_by_endpoint.get(endpoint_id, "deferred")}
            for endpoint_id in deferred_endpoint_ids
        ],
        "blocked_endpoint_ids": blocked_endpoint_ids,
        "parity_status_by_endpoint": parity_status_by_endpoint,
        "last_public_proof_by_endpoint": last_public_proof_by_endpoint,
        "deferred_reason_by_endpoint": deferred_reason_by_endpoint,
        "consecutive_block_count_by_endpoint": consecutive_block_count_by_endpoint,
        "no_delta_streak_by_role": no_delta_streak_by_role,
        "last_proof_ref": last_public_proof_ref or "none",
        "last_state_change_at": str(
            state.get("last_state_change_at") or state.get("updated_at") or _utc_now(now)
        ).strip()
        or _utc_now(now),
        "remaining_count": remaining_count,
        "total_count": len(selectable_remaining),
        "reason": reason,
        "generated_at": _utc_now(now),
    }
