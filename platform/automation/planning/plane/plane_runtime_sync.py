from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote

THIS_DIR = Path(__file__).resolve().parent
PARENT_DIR = THIS_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from orchestrator_paths import resolve_orchestrator_read_path, write_orchestrator_json
from runtime.core.contracts import OrchestrationEvent, PlannerGraphState
from runtime.truth.event_store import EventStore


_BATCH_RE = re.compile(r"\b(BATCH-\d{2})\b", flags=re.IGNORECASE)
_TASK_RE = re.compile(r"\b(BATCH-\d{2}-[A-Z_]+-\d{2})\b", flags=re.IGNORECASE)

_MODULE_STATE_MAP = {
    "backlog": "PLANNED",
    "planned": "READY",
    "todo": "READY",
    "unstarted": "READY",
    "in_progress": "IN_PROGRESS",
    "started": "IN_PROGRESS",
    "done": "DONE",
    "completed": "DONE",
    "cancelled": "CANCELLED",
    "canceled": "CANCELLED",
}

_WORK_ITEM_STATE_MAP = {
    "backlog": "TODO",
    "planned": "READY",
    "todo": "READY",
    "unstarted": "READY",
    "in_progress": "IN_PROGRESS",
    "started": "IN_PROGRESS",
    "done": "DONE",
    "completed": "DONE",
    "cancelled": "CANCELLED",
    "canceled": "CANCELLED",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_id(event_type: str, *parts: object) -> str:
    seed = "||".join(_token(part) for part in parts if _token(part))
    digest = hashlib.sha256(f"{event_type}||{seed}".encode("utf-8")).hexdigest()[:24]
    return f"{event_type}:{digest}"


def _token(value: object) -> str:
    return str(value or "").strip()


def _lower_token(value: object) -> str:
    return _token(value).lower()


def _first(*values: object) -> str:
    for value in values:
        token = _token(value)
        if token:
            return token
    return ""


def _extract_batch_id(*values: object) -> str:
    for value in values:
        token = _token(value)
        if not token:
            continue
        match = _BATCH_RE.search(token)
        if match:
            return match.group(1).upper()
    return ""


def _extract_task_id(*values: object) -> str:
    for value in values:
        token = _token(value)
        if not token:
            continue
        match = _TASK_RE.search(token)
        if match:
            return match.group(1).upper()
    return ""


def _runtime_kind_from_task_id(task_id: str) -> str:
    token = _token(task_id).upper()
    parts = token.split("-")
    if len(parts) >= 4:
        return "-".join(parts[2:])
    return ""


def _role_from_runtime_kind(task_id: str, explicit_role: object = "") -> str:
    role = _lower_token(explicit_role)
    if role:
        return role
    token = _runtime_kind_from_task_id(task_id)
    if token.startswith("DEV"):
        return "dev"
    if token.startswith("ADMIN"):
        return "admin"
    if token in {"PLAN", "ANALYSIS", "ARCH", "GOV_REVIEW"}:
        return "planner"
    if token.startswith("SCRUM"):
        return "scrum_master"
    return ""


def _queue_state_from_plane(state: object) -> str:
    return _MODULE_STATE_MAP.get(_lower_token(state), "PLANNED")


def _task_state_from_plane(state: object) -> str:
    return _WORK_ITEM_STATE_MAP.get(_lower_token(state), "READY")


def normalize_plane_module(
    module: dict[str, Any],
    *,
    workspace_slug: str = "",
    project_id: str = "",
    project_slug: str = "",
) -> dict[str, Any]:
    module_name = _first(module.get("name"), module.get("title"))
    batch_id = _extract_batch_id(module_name, module.get("identifier"), module.get("batch_id"))
    return {
        "batch_id": batch_id,
        "title": module_name or batch_id,
        "state": _queue_state_from_plane(module.get("state")),
        "plane_workspace_slug": _first(module.get("workspace_slug"), workspace_slug),
        "plane_project_id": _first(module.get("project_id"), project_id),
        "plane_project_slug": _first(module.get("project_slug"), project_slug),
        "plane_module_id": _first(module.get("id"), module.get("module_id")),
        "plane_module_identifier": _first(module.get("identifier"), batch_id),
        "planning_source": "plane",
        "raw_state": _token(module.get("state")),
        "description": _first(module.get("description"), module.get("content")),
        "updated_at": _first(module.get("updated_at"), module.get("created_at"), _now_iso()),
    }


def normalize_plane_work_item(
    item: dict[str, Any],
    *,
    default_batch_id: str = "",
    workspace_slug: str = "",
    project_id: str = "",
    project_slug: str = "",
    module_id: str = "",
    module_identifier: str = "",
) -> dict[str, Any]:
    title = _first(item.get("name"), item.get("title"))
    task_id = _extract_task_id(
        title,
        item.get("identifier"),
        item.get("runtime_task_id"),
        item.get("task_id"),
    )
    runtime_kind = _first(
        item.get("runtime_kind"),
        _runtime_kind_from_task_id(task_id),
    )
    batch_id = _extract_batch_id(
        task_id,
        item.get("batch_id"),
        item.get("module_name"),
        title,
        default_batch_id,
    )
    return {
        "task_id": task_id or _first(item.get("runtime_task_id"), item.get("identifier")),
        "batch_id": batch_id,
        "title": title or task_id,
        "state": _task_state_from_plane(item.get("state")),
        "runtime_kind": runtime_kind,
        "runtime_role": _role_from_runtime_kind(task_id, item.get("runtime_role")),
        "plane_workspace_slug": _first(item.get("workspace_slug"), workspace_slug),
        "plane_project_id": _first(item.get("project_id"), project_id),
        "plane_project_slug": _first(item.get("project_slug"), project_slug),
        "plane_module_id": _first(item.get("module_id"), module_id),
        "plane_module_identifier": _first(item.get("module_identifier"), module_identifier, batch_id),
        "plane_work_item_id": _first(item.get("id"), item.get("work_item_id")),
        "plane_work_item_identifier": _first(item.get("identifier"), task_id),
        "planning_source": "plane",
        "raw_state": _token(item.get("state")),
        "updated_at": _first(item.get("updated_at"), item.get("created_at"), _now_iso()),
    }


def build_runtime_batch_payload(
    module: dict[str, Any],
    work_items: Iterable[dict[str, Any]],
    *,
    workspace_slug: str = "",
    project_id: str = "",
    project_slug: str = "",
) -> dict[str, Any]:
    normalized_module = normalize_plane_module(
        module,
        workspace_slug=workspace_slug,
        project_id=project_id,
        project_slug=project_slug,
    )
    normalized_items = [
        normalize_plane_work_item(
            item,
            default_batch_id=normalized_module["batch_id"],
            workspace_slug=normalized_module["plane_workspace_slug"],
            project_id=normalized_module["plane_project_id"],
            project_slug=normalized_module["plane_project_slug"],
            module_id=normalized_module["plane_module_id"],
            module_identifier=normalized_module["plane_module_identifier"],
        )
        for item in work_items
    ]
    normalized_items.sort(key=lambda row: (_token(row.get("task_id")), _token(row.get("plane_work_item_id"))))
    return {
        **normalized_module,
        "tasks": normalized_items,
    }


def build_projection_bundle(
    modules: Iterable[dict[str, Any]],
    work_items: Iterable[dict[str, Any]],
    *,
    workspace_slug: str = "",
    project_id: str = "",
    project_slug: str = "",
) -> dict[str, Any]:
    module_rows = list(modules)
    item_rows = list(work_items)

    items_by_module_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    items_by_batch_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in item_rows:
        module_id = _first(item.get("module_id"), item.get("plane_module_id"))
        if module_id:
            items_by_module_id[module_id].append(item)
        batch_id = _extract_batch_id(
            item.get("batch_id"),
            item.get("runtime_task_id"),
            item.get("identifier"),
            item.get("name"),
            item.get("title"),
        )
        if batch_id:
            items_by_batch_id[batch_id].append(item)

    runtime_batches: list[dict[str, Any]] = []
    for module in module_rows:
        normalized_module = normalize_plane_module(
            module,
            workspace_slug=workspace_slug,
            project_id=project_id,
            project_slug=project_slug,
        )
        module_items = items_by_module_id.get(normalized_module["plane_module_id"], [])
        if not module_items and normalized_module["batch_id"]:
            module_items = items_by_batch_id.get(normalized_module["batch_id"], [])
        runtime_batches.append(
            build_runtime_batch_payload(
                module,
                module_items,
                workspace_slug=workspace_slug,
                project_id=project_id,
                project_slug=project_slug,
            )
        )

    queue_items: list[dict[str, Any]] = []
    workboard_tasks: list[dict[str, Any]] = []
    for batch in runtime_batches:
        queue_items.append(
            {
                "id": batch["batch_id"],
                "title": batch["title"],
                "state": batch["state"],
                "planning_source": "plane",
                "plane_workspace_slug": batch["plane_workspace_slug"],
                "plane_project_id": batch["plane_project_id"],
                "plane_module_id": batch["plane_module_id"],
                "plane_module_identifier": batch["plane_module_identifier"],
                "projection_source": "runtime_state",
                "updated_at": batch["updated_at"],
            }
        )
        for task in batch.get("tasks", []):
            workboard_tasks.append(
                {
                    "id": task["task_id"],
                    "stream_id": batch["batch_id"],
                    "title": task["title"],
                    "state": task["state"],
                    "assignee": task["runtime_role"],
                    "planning_source": "plane",
                    "runtime_role": task["runtime_role"],
                    "runtime_kind": task["runtime_kind"],
                    "plane_workspace_slug": task["plane_workspace_slug"],
                    "plane_project_id": task["plane_project_id"],
                    "plane_module_id": task["plane_module_id"],
                    "plane_work_item_id": task["plane_work_item_id"],
                    "plane_work_item_identifier": task["plane_work_item_identifier"],
                    "projection_source": "runtime_state",
                    "updated_at": task["updated_at"],
                }
            )

    queue_items.sort(key=lambda row: (_token(row.get("id")), _token(row.get("plane_module_id"))))
    workboard_tasks.sort(key=lambda row: (_token(row.get("stream_id")), _token(row.get("id"))))
    generated_at = _now_iso()
    return {
        "planning_source": "plane",
        "generated_at": generated_at,
        "imports": runtime_batches,
        "queue_projection": {
            "planning_source": "plane",
            "projection_source": "runtime_state",
            "generated_at": generated_at,
            "items": queue_items,
        },
        "workboard_projection": {
            "planning_source": "plane",
            "projection_source": "runtime_state",
            "generated_at": generated_at,
            "tasks": workboard_tasks,
        },
    }


def _graph_status_for_task_state(state: str) -> tuple[str, str, str]:
    token = _token(state).upper()
    if token == "IN_PROGRESS":
        return ("running", "wait_or_collect_result", "collect_or_merge")
    if token == "DONE":
        return ("completed", "close_or_requeue", "none")
    if token == "CANCELLED":
        return ("cancelled", "close_or_requeue", "none")
    return ("pending", "select_actionable_task", "dispatch_or_wait")


def _runtime_queue_ref() -> str:
    return "logs-codex-runs/orchestrator-state/priority-queue.json"


def _runtime_workboard_ref() -> str:
    return "logs-codex-runs/orchestrator-state/parallel-workstreams.json"


def _plane_sync_cache_ref() -> str:
    return "plane-sync-snapshot.json"


def _read_sync_cache(root: Path) -> dict[str, Any]:
    path = resolve_orchestrator_read_path(root, _plane_sync_cache_ref())
    if not path.exists():
        return {"modules": [], "work_items": [], "meta": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    modules = payload.get("modules", [])
    work_items = payload.get("work_items", [])
    meta = payload.get("meta", {})
    return {
        "modules": modules if isinstance(modules, list) else [],
        "work_items": work_items if isinstance(work_items, list) else [],
        "meta": meta if isinstance(meta, dict) else {},
    }


def _plane_secret_token() -> str:
    direct = _first(os.environ.get("FC_PLANE_WEBHOOK_SECRET"), os.environ.get("PLANE_WEBHOOK_SECRET"))
    if direct:
        return direct
    secret_file = _first(os.environ.get("FC_PLANE_WEBHOOK_SECRET_FILE"), os.environ.get("PLANE_WEBHOOK_SECRET_FILE"))
    if not secret_file:
        return ""
    try:
        return Path(secret_file).expanduser().read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _plane_header(headers: Mapping[str, Any], key: str) -> str:
    target = key.lower()
    for header_key, value in headers.items():
        if str(header_key).strip().lower() == target:
            return _token(value)
    return ""


def _verify_plane_signature(raw_body: bytes, headers: Mapping[str, Any]) -> tuple[bool, str]:
    secret = _plane_secret_token()
    if not secret:
        return True, "unconfigured"
    received = _plane_header(headers, "X-Plane-Signature")
    if not received:
        return False, "missing_signature"
    expected = hmac.new(secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        return False, "invalid_signature"
    return True, "verified"


def _upsert_entity(rows: list[dict[str, Any]], entity: dict[str, Any]) -> list[dict[str, Any]]:
    entity_id = _first(entity.get("id"), entity.get("module_id"), entity.get("work_item_id"))
    if not entity_id:
        return rows
    updated: list[dict[str, Any]] = []
    replaced = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = _first(row.get("id"), row.get("module_id"), row.get("work_item_id"))
        if row_id == entity_id:
            updated.append(entity)
            replaced = True
        else:
            updated.append(row)
    if not replaced:
        updated.append(entity)
    return updated


def _delete_entity(rows: list[dict[str, Any]], entity: dict[str, Any]) -> list[dict[str, Any]]:
    entity_id = _first(entity.get("id"), entity.get("module_id"), entity.get("work_item_id"))
    if not entity_id:
        return rows
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = _first(row.get("id"), row.get("module_id"), row.get("work_item_id"))
        if row_id != entity_id:
            filtered.append(row)
    return filtered


def ingest_plane_payload(
    root: Path,
    payload: dict[str, Any],
    *,
    raw_body: bytes | None = None,
    headers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    headers = headers or {}
    if not isinstance(payload, dict):
        raise ValueError("plane_payload_must_be_object")

    cache = _read_sync_cache(root)
    modules = list(cache.get("modules", []))
    work_items = list(cache.get("work_items", []))

    source = _lower_token(payload.get("sync_source")) or "snapshot"
    signature_status = "not_applicable"
    event = ""
    action = ""
    if isinstance(payload.get("modules"), list) and isinstance(payload.get("work_items"), list):
        modules = [row for row in payload.get("modules", []) if isinstance(row, dict)]
        work_items = [row for row in payload.get("work_items", []) if isinstance(row, dict)]
    else:
        source = "webhook"
        raw = raw_body if raw_body is not None else json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        signature_ok, signature_status = _verify_plane_signature(raw, headers)
        if not signature_ok:
            raise ValueError(f"plane_webhook_{signature_status}")
        event = _lower_token(_first(payload.get("event"), _plane_header(headers, "X-Plane-Event")))
        action = _lower_token(payload.get("action"))
        data = payload.get("data", {})
        if not isinstance(data, dict):
            data = {}
        if event == "module":
            modules = _delete_entity(modules, data) if action == "delete" else _upsert_entity(modules, data)
        elif event in {"issue", "work_item", "work-item", "workitem"}:
            work_items = _delete_entity(work_items, data) if action == "delete" else _upsert_entity(work_items, data)
        else:
            return {
                "accepted": False,
                "ignored": True,
                "planning_source": "plane",
                "source": source,
                "signature": signature_status,
                "event": event or "unknown",
                "action": action or "unknown",
                "reason": "unsupported_event",
            }

    workspace_slug = _first(payload.get("workspace_slug"), cache.get("meta", {}).get("workspace_slug"))
    project_id = _first(payload.get("project_id"), cache.get("meta", {}).get("project_id"))
    project_slug = _first(payload.get("project_slug"), cache.get("meta", {}).get("project_slug"))
    bundle = build_projection_bundle(
        modules,
        work_items,
        workspace_slug=workspace_slug,
        project_id=project_id,
        project_slug=project_slug,
    )
    bundle["sync_source"] = source
    if isinstance(bundle.get("queue_projection"), dict):
        bundle["queue_projection"]["sync_source"] = source
    if isinstance(bundle.get("workboard_projection"), dict):
        bundle["workboard_projection"]["sync_source"] = source
    apply_result = apply_projection_bundle(root, bundle)
    write_orchestrator_json(
        root,
        _plane_sync_cache_ref(),
        {
            "planning_source": "plane",
            "updated_at": _now_iso(),
            "modules": modules,
            "work_items": work_items,
            "meta": {
                "workspace_slug": workspace_slug,
                "project_id": project_id,
                "project_slug": project_slug,
                "source": source,
                "signature": signature_status,
                "last_event": event,
                "last_action": action,
            },
        },
    )
    return {
        "accepted": True,
        "ignored": False,
        "planning_source": "plane",
        "source": source,
        "signature": signature_status,
        "event": event or "snapshot",
        "action": action or "sync",
        "modules": len(modules),
        "work_items": len(work_items),
        "apply_result": apply_result,
    }


def _plane_api_base_url(explicit: str = "") -> str:
    return _first(explicit, os.environ.get("FC_PLANE_BASE_URL"), os.environ.get("PLANE_BASE_URL")).rstrip("/")


def _plane_api_key(explicit: str = "") -> str:
    return _first(explicit, os.environ.get("FC_PLANE_API_KEY"), os.environ.get("PLANE_API_KEY"))


def _plane_list_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _plane_next_url(payload: Any, base_url: str) -> str:
    if not isinstance(payload, dict):
        return ""
    next_value = _first(payload.get("next"), payload.get("next_url"))
    if not next_value:
        return ""
    if next_value.startswith("http://") or next_value.startswith("https://"):
        return next_value
    return f"{base_url.rstrip('/')}/{next_value.lstrip('/')}"


def _plane_get_json(url: str, api_key: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "x-api-key": api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _plane_collect_rows(url: str, api_key: str, base_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    next_url = url
    seen: set[str] = set()
    while next_url and next_url not in seen:
        seen.add(next_url)
        payload = _plane_get_json(next_url, api_key)
        rows.extend(_plane_list_rows(payload))
        next_url = _plane_next_url(payload, base_url)
    return rows


def _plane_collect_rows_compat(urls: Iterable[str], api_key: str, base_url: str) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for url in urls:
        target = _token(url)
        if not target:
            continue
        try:
            rows = _plane_collect_rows(target, api_key, base_url)
        except urllib.error.HTTPError as exc:
            if exc.code in {404, 405, 410}:
                last_error = exc
                continue
            raise
        if rows:
            return rows
        return rows
    if last_error is not None:
        raise last_error
    return []


def reconcile_from_plane_api(
    root: Path,
    *,
    workspace_slug: str = "",
    project_id: str = "",
    project_slug: str = "",
    base_url: str = "",
    api_key: str = "",
) -> dict[str, Any]:
    resolved_base_url = _plane_api_base_url(base_url)
    resolved_api_key = _plane_api_key(api_key)
    resolved_workspace_slug = _first(workspace_slug, os.environ.get("FC_PLANE_WORKSPACE_SLUG"), os.environ.get("PLANE_WORKSPACE_SLUG"))
    resolved_project_id = _first(project_id, os.environ.get("FC_PLANE_PROJECT_ID"), os.environ.get("PLANE_PROJECT_ID"))
    resolved_project_slug = _first(project_slug, os.environ.get("FC_PLANE_PROJECT_SLUG"), os.environ.get("PLANE_PROJECT_SLUG"))
    if not resolved_base_url:
        raise ValueError("plane_api_base_url_missing")
    if not resolved_api_key:
        raise ValueError("plane_api_key_missing")
    if not resolved_workspace_slug:
        raise ValueError("plane_workspace_slug_missing")
    if not resolved_project_id:
        raise ValueError("plane_project_id_missing")

    quoted_workspace = quote(resolved_workspace_slug, safe="")
    quoted_project = quote(resolved_project_id, safe="")
    modules_url = f"{resolved_base_url}/api/v1/workspaces/{quoted_workspace}/projects/{quoted_project}/modules/"
    modules = _plane_collect_rows(modules_url, resolved_api_key, resolved_base_url)
    work_items: list[dict[str, Any]] = []
    for module in modules:
        module_id = _first(module.get("id"), module.get("module_id"))
        if not module_id:
            continue
        module_item_urls = (
            f"{resolved_base_url}/api/v1/workspaces/{quoted_workspace}/projects/{quoted_project}/modules/{quote(module_id, safe='')}/work-items/",
            f"{resolved_base_url}/api/v1/workspaces/{quoted_workspace}/projects/{quoted_project}/modules/{quote(module_id, safe='')}/module-issues/",
        )
        for item in _plane_collect_rows_compat(module_item_urls, resolved_api_key, resolved_base_url):
            row = dict(item)
            row.setdefault("module_id", module_id)
            work_items.append(row)

    result = ingest_plane_payload(
        root,
        {
            "sync_source": "reconcile_api",
            "workspace_slug": resolved_workspace_slug,
            "project_id": resolved_project_id,
            "project_slug": resolved_project_slug,
            "modules": modules,
            "work_items": work_items,
        },
    )
    result["source"] = "reconcile_api"
    result["plane_api_base_url"] = resolved_base_url
    return result


def apply_runtime_bundle(root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    store = EventStore(root)
    generated_at = _token(bundle.get("generated_at")) or _now_iso()
    sync_source = _token(bundle.get("sync_source")) or "snapshot"
    imports = bundle.get("imports", [])
    batch_count = 0
    task_count = 0

    for batch in imports:
        if not isinstance(batch, dict):
            continue
        batch_id = _token(batch.get("batch_id"))
        if not batch_id:
            continue
        batch_count += 1
        store.append_event(
            OrchestrationEvent(
                event_id=_event_id(
                    "plane_module_synced",
                    batch_id,
                    batch.get("plane_module_id", ""),
                    batch.get("state", ""),
                    batch.get("updated_at", ""),
                    sync_source,
                ),
                ts=generated_at,
                event_type="plane_module_synced",
                cycle_id=_first(batch.get("plane_module_identifier"), batch_id),
                batch_id=batch_id,
                owner_role="planner",
                payload={
                    "planning_source": "plane",
                    "sync_source": sync_source,
                    "plane_workspace_slug": batch.get("plane_workspace_slug", ""),
                    "plane_project_id": batch.get("plane_project_id", ""),
                    "plane_module_id": batch.get("plane_module_id", ""),
                    "plane_module_identifier": batch.get("plane_module_identifier", ""),
                    "state": batch.get("state", ""),
                    "title": batch.get("title", ""),
                },
            )
        )
        for task in batch.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_id = _token(task.get("task_id"))
            if not task_id:
                continue
            task_count += 1
            graph_status, current_node, next_action = _graph_status_for_task_state(_token(task.get("state")))
            store.upsert_graph_state(
                PlannerGraphState(
                    cycle_id=_first(task.get("plane_module_identifier"), batch.get("plane_module_identifier"), batch_id),
                    batch_id=batch_id,
                    task_id=task_id,
                    task_kind=_token(task.get("runtime_kind")),
                    owner_role="planner",
                    target_role=_token(task.get("runtime_role")),
                    queue_snapshot_ref=_runtime_queue_ref(),
                    workboard_snapshot_ref=_runtime_workboard_ref(),
                    capability_request={
                        "planning_source": "plane",
                        "plane_workspace_slug": task.get("plane_workspace_slug", ""),
                        "plane_project_id": task.get("plane_project_id", ""),
                        "plane_module_id": task.get("plane_module_id", ""),
                        "plane_work_item_id": task.get("plane_work_item_id", ""),
                        "plane_work_item_identifier": task.get("plane_work_item_identifier", ""),
                        "title": task.get("title", ""),
                    },
                    guard_status="ok",
                    runtime_health="ok",
                    next_action=next_action,
                    blocking_issue="none",
                    current_node=current_node,
                    status=graph_status,
                    updated_at=_token(task.get("updated_at")) or generated_at,
                    engine="plane_sync",
                )
            )
            store.append_event(
                OrchestrationEvent(
                    event_id=_event_id(
                        "plane_work_item_synced",
                        task_id,
                        task.get("plane_work_item_id", ""),
                        task.get("state", ""),
                        task.get("updated_at", ""),
                        sync_source,
                    ),
                    ts=generated_at,
                    event_type="plane_work_item_synced",
                    cycle_id=_first(task.get("plane_module_identifier"), batch.get("plane_module_identifier"), batch_id),
                    batch_id=batch_id,
                    task_id=task_id,
                    owner_role="planner",
                    target_role=_token(task.get("runtime_role")),
                    graph_node=current_node,
                    payload={
                        "planning_source": "plane",
                        "sync_source": sync_source,
                        "plane_workspace_slug": task.get("plane_workspace_slug", ""),
                        "plane_project_id": task.get("plane_project_id", ""),
                        "plane_module_id": task.get("plane_module_id", ""),
                        "plane_work_item_id": task.get("plane_work_item_id", ""),
                        "plane_work_item_identifier": task.get("plane_work_item_identifier", ""),
                        "runtime_kind": task.get("runtime_kind", ""),
                        "state": task.get("state", ""),
                        "title": task.get("title", ""),
                    },
                )
            )

    return {
        "planning_source": "plane",
        "sync_source": sync_source,
        "generated_at": generated_at,
        "imports": batch_count,
        "graph_states_upserted": task_count,
        "event_store_updated": True,
    }


def apply_projection_bundle(root: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    runtime_result = apply_runtime_bundle(root, bundle)
    queue_projection = bundle.get("queue_projection", {})
    workboard_projection = bundle.get("workboard_projection", {})
    write_orchestrator_json(root, "priority-queue.json", queue_projection)
    write_orchestrator_json(root, "parallel-workstreams.json", workboard_projection)
    return {
        "planning_source": "plane",
        "sync_source": _token(bundle.get("sync_source")) or "snapshot",
        "generated_at": _now_iso(),
        "runtime_result": runtime_result,
        "queue_items": len(queue_projection.get("items", []) if isinstance(queue_projection, dict) else []),
        "workboard_tasks": len(workboard_projection.get("tasks", []) if isinstance(workboard_projection, dict) else []),
    }


def _read_json_file(path: str) -> Any:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync Plane planning payloads into canonical runtime projections.")
    parser.add_argument("--root", default="")
    parser.add_argument("--modules-file", default="")
    parser.add_argument("--work-items-file", default="")
    parser.add_argument("--workspace-slug", default="")
    parser.add_argument("--project-id", default="")
    parser.add_argument("--project-slug", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--reconcile-api", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[3]
    if args.reconcile_api:
        payload = reconcile_from_plane_api(
            root,
            workspace_slug=args.workspace_slug,
            project_id=args.project_id,
            project_slug=args.project_slug,
            base_url=args.base_url,
            api_key=args.api_key,
        )
        print(json.dumps(payload, ensure_ascii=True))
        return 0

    if not args.modules_file or not args.work_items_file:
        raise SystemExit("modules-file and work-items-file are required unless --reconcile-api is used")
    modules = _read_json_file(args.modules_file)
    work_items = _read_json_file(args.work_items_file)
    if not isinstance(modules, list):
        raise SystemExit("modules-file must contain a JSON list")
    if not isinstance(work_items, list):
        raise SystemExit("work-items-file must contain a JSON list")

    bundle = build_projection_bundle(
        modules,
        work_items,
        workspace_slug=args.workspace_slug,
        project_id=args.project_id,
        project_slug=args.project_slug,
    )
    payload: dict[str, Any] = {
        "planning_source": "plane",
        "imports": len(bundle.get("imports", [])),
        "queue_items": len((bundle.get("queue_projection") or {}).get("items", [])),
        "workboard_tasks": len((bundle.get("workboard_projection") or {}).get("tasks", [])),
        "applied": False,
    }
    if args.apply:
        ingest_result = ingest_plane_payload(
            root,
            {
                "sync_source": "snapshot",
                "workspace_slug": args.workspace_slug,
                "project_id": args.project_id,
                "project_slug": args.project_slug,
                "modules": modules,
                "work_items": work_items,
            },
        )
        payload["apply_result"] = ingest_result.get("apply_result", {})
        payload["ingest_result"] = ingest_result
        payload["applied"] = True
    else:
        payload["bundle"] = bundle
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
