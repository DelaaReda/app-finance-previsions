from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from orchestrator_paths import resolve_orchestrator_read_path


def _first_env(*names: str) -> str:
    for name in names:
        token = str(os.environ.get(name, "") or "").strip()
        if token:
            return token
    return ""


def _bool_env(*names: str, default: bool = False) -> bool:
    token = _first_env(*names)
    if not token:
        return default
    return token.lower() not in {"0", "false", "no", "off"}


def _int_env(*names: str, default: int = 0) -> int:
    token = _first_env(*names)
    if not token:
        return default
    try:
        return int(token)
    except (TypeError, ValueError):
        return default


def _sync_cache_snapshot(root: Path) -> dict[str, Any]:
    path = resolve_orchestrator_read_path(root, "plane-sync-snapshot.json")
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "updated_at": "",
            "modules": 0,
            "work_items": 0,
            "source": "none",
            "last_event": "",
            "last_action": "",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    modules = payload.get("modules", [])
    work_items = payload.get("work_items", [])
    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    return {
        "path": str(path),
        "exists": True,
        "updated_at": str(payload.get("updated_at", "") or ""),
        "modules": len(modules) if isinstance(modules, list) else 0,
        "work_items": len(work_items) if isinstance(work_items, list) else 0,
        "source": str(meta.get("source", "cache") or "cache"),
        "last_event": str(meta.get("last_event", "") or ""),
        "last_action": str(meta.get("last_action", "") or ""),
    }


def build_plane_planning_snapshot(root: Path) -> dict[str, Any]:
    workspace_slug = _first_env("FC_PLANE_WORKSPACE_SLUG", "PLANE_WORKSPACE_SLUG")
    project_id = _first_env("FC_PLANE_PROJECT_ID", "PLANE_PROJECT_ID")
    project_slug = _first_env("FC_PLANE_PROJECT_SLUG", "PLANE_PROJECT_SLUG")
    base_url = _first_env("FC_PLANE_BASE_URL", "PLANE_BASE_URL")
    project_url = _first_env("FC_PLANE_PROJECT_URL", "PLANE_PROJECT_URL")
    mcp_transport = _first_env("FC_PLANE_MCP_TRANSPORT", "PLANE_MCP_TRANSPORT") or "stdio"
    mcp_command = _first_env("FC_PLANE_MCP_COMMAND", "PLANE_MCP_COMMAND")
    mcp_url = _first_env("FC_PLANE_MCP_URL", "PLANE_MCP_URL")
    mcp_enabled = _bool_env("FC_PLANE_MCP_ENABLED", "PLANE_MCP_ENABLED", default=bool(mcp_command or mcp_url))
    webhook_url = _first_env("FC_PLANE_WEBHOOK_URL", "PLANE_WEBHOOK_URL")
    webhook_secret_file = _first_env("FC_PLANE_WEBHOOK_SECRET_FILE", "PLANE_WEBHOOK_SECRET_FILE")
    webhook_secret_path = Path(webhook_secret_file).expanduser() if webhook_secret_file else None
    has_project_identity = bool(workspace_slug and (project_id or project_slug))
    has_transport_target = bool(mcp_command or mcp_url or base_url or project_url)
    reconcile_enabled = _bool_env("FC_PLANE_RECONCILE_ENABLED", "PLANE_RECONCILE_ENABLED", default=bool(base_url))
    reconcile_interval_s = _int_env("FC_PLANE_RECONCILE_INTERVAL_S", "PLANE_RECONCILE_INTERVAL_S", default=300)
    sync_adapter_enabled = _bool_env(
        "FC_PLANE_SYNC_ADAPTER_ENABLED",
        "PLANE_SYNC_ADAPTER_ENABLED",
        default=bool(has_project_identity and (webhook_url or base_url)),
    )
    sync_cache = _sync_cache_snapshot(root)
    if has_project_identity and mcp_enabled and has_transport_target:
        status = "ok"
    elif has_project_identity or has_transport_target or mcp_enabled:
        status = "degraded"
    else:
        status = "unknown"

    return {
        "status": status,
        "planning_source": "plane",
        "front_door": "plane_oss",
        "workspace_slug": workspace_slug,
        "project_id": project_id,
        "project_slug": project_slug,
        "project_url": project_url,
        "base_url": base_url,
        "mcp": {
            "enabled": mcp_enabled,
            "transport": mcp_transport,
            "command_configured": bool(mcp_command),
            "url_configured": bool(mcp_url),
            "target": mcp_url or mcp_command,
            "official_server_expected": True,
        },
        "webhook": {
            "enabled": bool(webhook_url),
            "url": webhook_url,
            "ingest_path": "/api/planning/plane/webhook",
            "secret_file_configured": bool(webhook_secret_file),
            "secret_file_exists": bool(webhook_secret_path and webhook_secret_path.exists()),
        },
        "sync": {
            "adapter_enabled": sync_adapter_enabled,
            "mode": "webhook_first_reconcile_fallback",
            "reconcile_enabled": reconcile_enabled,
            "reconcile_interval_s": reconcile_interval_s,
            "reconcile_target_configured": bool(base_url),
            "cache": sync_cache,
        },
        "runtime_sync": {
            "planner_scheduler": "planner",
            "runtime_truth": "sqlite_langgraph",
            "queue_projection_only": True,
            "workboard_projection_only": True,
            "dual_write_forbidden": True,
        },
        "runtime_independence": {
            "startup_blocks_on_plane": False,
            "degraded_when_unreachable": True,
        },
        "docs_mode": {
            "repo_backlog_docs_authoritative": False,
            "repo_backlog_docs_mode": "reference_only",
            "new_backlog_creation_allowed_in_docs": False,
        },
        "detail": {
            "project_identity_configured": has_project_identity,
            "transport_target_configured": has_transport_target,
            "provider_plane": "planning",
            "webhook_ingest_active": bool(sync_cache.get("exists")),
            "workspace_root": str(root),
        },
    }
