"""Shared service-level helpers for reusable endpoint business logic.

This module defines a small standard contract used by service modules:
- UTC timestamps
- safe numeric coercion
- source tag normalization
- service response envelope (`ok/data/freshness`)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence


def utc_now_iso() -> str:
    """UTC timestamp in canonical API format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_int(value: Any, default: int = 0) -> int:
    """Bool-safe int cast with default fallback."""
    try:
        if isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Bool-safe float cast with configurable fallback."""
    if value is None:
        return default
    try:
        if isinstance(value, bool):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def ensure_source_list(source: Any, *, default_source: str) -> List[str]:
    """Normalize arbitrary `source` value to a non-empty list[str]."""
    if isinstance(source, list):
        normalized = [str(item).strip() for item in source if str(item).strip()]
        if normalized:
            return normalized
    if isinstance(source, str) and source.strip():
        return [source.strip()]
    return [default_source]


def unwrap_storage_payload(raw: Any) -> Any:
    """Unwrap common storage wrappers used across the backend (`data`/`payload`)."""
    if isinstance(raw, dict):
        if "data" in raw and raw.get("data") is not None:
            return raw.get("data")
        if "payload" in raw and raw.get("payload") is not None:
            return raw.get("payload")
    return raw


def append_source_tag(payload: Dict[str, Any], tag: str, *, default_source: str) -> None:
    """Append source tag once while guaranteeing source list shape."""
    sources = ensure_source_list(payload.get("source"), default_source=default_source)
    if tag not in sources:
        sources.append(tag)
    payload["source"] = sources


def service_response(
    data: Dict[str, Any],
    *,
    freshness: Optional[str] = None,
) -> Dict[str, Any]:
    """Canonical service envelope for API routes."""
    resolved_freshness = (
        freshness
        or str(data.get("freshness") or "")
        or str(data.get("generated_at") or "")
        or utc_now_iso()
    )
    return {
        "ok": True,
        "data": data,
        "freshness": resolved_freshness,
    }


def never_empty_payload(
    *,
    base: Optional[Dict[str, Any]] = None,
    default_source: str,
    source: Optional[Sequence[str]] = None,
    error: Optional[Any] = None,
    message: Optional[str] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a stable never-empty payload with standard metadata."""
    now_iso = generated_at or utc_now_iso()
    payload = dict(base or {})
    payload.setdefault("generated_at", now_iso)

    if source:
        payload["source"] = ensure_source_list(list(source), default_source=default_source)
    else:
        payload["source"] = ensure_source_list(payload.get("source"), default_source=default_source)

    if error is not None:
        payload["error"] = str(error)
    if message:
        payload["message"] = message
    return payload


__all__ = [
    "append_source_tag",
    "ensure_source_list",
    "never_empty_payload",
    "safe_float",
    "safe_int",
    "service_response",
    "unwrap_storage_payload",
    "utc_now_iso",
]
