"""Additive API envelope helpers for critical routes.

Contract (additive, non-breaking):
- keep historical shape: {"ok": bool, "data": ...}
- add stable edge envelope fields:
  - status: ok|degraded|error
  - error: {code, message, detail?} | None
  - meta: {source, freshness_s, request_id, schema_version, fallback}
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

EDGE_SCHEMA_VERSION = os.getenv("FC_API_EDGE_SCHEMA_VERSION", "fc-edge-v1")


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def edge_enabled(flag_name: str, default: bool = True) -> bool:
    return _env_flag(flag_name, default=default)


def _normalize_source(source: Any) -> list[str]:
    if isinstance(source, list):
        out = [str(item).strip() for item in source if str(item).strip()]
        return out or ["unknown"]
    if isinstance(source, str) and source.strip():
        return [source.strip()]
    return ["unknown"]


def _request_id() -> str:
    return uuid.uuid4().hex[:12]


def _meta(
    *,
    source: Any,
    freshness_s: Optional[int] = None,
    request_id: Optional[str] = None,
    schema_version: Optional[str] = None,
    fallback: bool = False,
) -> Dict[str, Any]:
    return {
        "source": _normalize_source(source),
        "freshness_s": freshness_s,
        "request_id": request_id or _request_id(),
        "schema_version": schema_version or EDGE_SCHEMA_VERSION,
        "fallback": bool(fallback),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _error_payload(code: str, message: str, detail: Any = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "code": str(code or "edge_error").strip() or "edge_error",
        "message": str(message or "Unhandled edge error").strip() or "Unhandled edge error",
    }
    if detail is not None:
        payload["detail"] = detail
    return payload


def edge_ok(
    data: Any,
    *,
    source: Any,
    freshness_s: Optional[int] = None,
    fallback: bool = False,
    request_id: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "data": data,
        "error": None,
        "meta": _meta(
            source=source,
            freshness_s=freshness_s,
            request_id=request_id,
            schema_version=schema_version,
            fallback=fallback,
        ),
    }


def edge_degraded(
    data: Any,
    *,
    code: str,
    message: str,
    detail: Any = None,
    source: Any,
    freshness_s: Optional[int] = None,
    fallback: bool = True,
    request_id: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "status": "degraded",
        "data": data,
        "error": _error_payload(code=code, message=message, detail=detail),
        "meta": _meta(
            source=source,
            freshness_s=freshness_s,
            request_id=request_id,
            schema_version=schema_version,
            fallback=fallback,
        ),
    }


def edge_error(
    data: Any,
    *,
    code: str,
    message: str,
    detail: Any = None,
    source: Any,
    freshness_s: Optional[int] = None,
    fallback: bool = True,
    request_id: Optional[str] = None,
    schema_version: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "status": "error",
        "data": data,
        "error": _error_payload(code=code, message=message, detail=detail),
        "meta": _meta(
            source=source,
            freshness_s=freshness_s,
            request_id=request_id,
            schema_version=schema_version,
            fallback=fallback,
        ),
    }

