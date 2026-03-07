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


_VALID_ENDPOINT_STATUSES = {"ok", "degraded", "error"}
_VALID_VERDICTS = {"buy", "sell", "hold"}
_VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


def ensure_endpoint_metadata(
    payload: Dict[str, Any],
    *,
    default_source: str,
    freshness: Optional[str] = None,
    status: Optional[str] = None,
    error: Optional[Any] = None,
) -> Dict[str, Any]:
    """Ensure stable freshness/error/status metadata for UI-facing payloads."""
    if not isinstance(payload, dict):
        return payload

    now_iso = utc_now_iso()
    generated_at = str(payload.get("generated_at") or now_iso).strip() or now_iso
    payload["generated_at"] = generated_at

    resolved_freshness = str(freshness or payload.get("freshness") or generated_at).strip()
    if not resolved_freshness or resolved_freshness == "error":
        resolved_freshness = generated_at
    payload["freshness"] = resolved_freshness

    raw_error = payload.get("error") if error is None else error
    if raw_error in (None, ""):
        payload["error"] = None
    elif isinstance(raw_error, dict):
        payload["error"] = raw_error
    else:
        payload["error"] = str(raw_error)

    raw_status = str(status or payload.get("status") or "").strip().lower()
    if raw_status not in _VALID_ENDPOINT_STATUSES:
        raw_status = "degraded" if payload["error"] is not None else "ok"
    payload["status"] = raw_status

    warnings = payload.get("warnings")
    if warnings is None:
        payload["warnings"] = []
    elif isinstance(warnings, list):
        payload["warnings"] = warnings
    else:
        payload["warnings"] = [str(warnings)]

    payload["source"] = ensure_source_list(payload.get("source"), default_source=default_source)
    append_source_tag(payload, "metadata_contract_v1", default_source=default_source)
    return payload


def service_response_with_metadata(
    data: Dict[str, Any],
    *,
    default_source: str,
    freshness: Optional[str] = None,
    status: Optional[str] = None,
    error: Optional[Any] = None,
) -> Dict[str, Any]:
    """Canonical response envelope with stable metadata mirrored at the top level."""
    normalized = ensure_endpoint_metadata(
        data,
        default_source=default_source,
        freshness=freshness,
        status=status,
        error=error,
    )
    return {
        "ok": True,
        "data": normalized,
        "freshness": normalized.get("freshness"),
        "status": normalized.get("status"),
        "error": normalized.get("error"),
    }


def coerce_confidence(value: Any, *, default: float = 0.5) -> float:
    """Normalize confidence to a float in [0, 1]. Accepts percent values (0-100)."""
    try:
        if value is None:
            return float(default)
        if isinstance(value, bool):
            return float(default)
        confidence = float(value)
    except (TypeError, ValueError):
        return float(default)

    if confidence > 1.0:
        confidence = confidence / 100.0 if confidence <= 100.0 else 1.0
    if confidence < 0.0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0
    return float(confidence)


def coerce_verdict(value: Any, *, default: str = "hold") -> str:
    """Normalize verdict/action into buy|sell|hold (accepts up/down/flat, long/short)."""
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    if raw in _VALID_VERDICTS:
        return raw
    if raw in {"up", "bullish", "long"}:
        return "buy"
    if raw in {"down", "bearish", "short"}:
        return "sell"
    if raw in {"flat", "neutral", "wait", "none"}:
        return "hold"
    return default


def normalize_risk_level(value: Any, *, default: str = "medium") -> str:
    raw = str(value or "").strip().lower()
    if raw in _VALID_RISK_LEVELS:
        return raw
    return default if default in _VALID_RISK_LEVELS else "medium"


def ensure_decision_contract(
    payload: Dict[str, Any],
    *,
    default_source: str,
    verdict: Any = None,
    confidence: Any = None,
    why: Any = None,
    risk_level: Any = None,
    risk_caveat: Any = None,
    freshness: Any = None,
) -> Dict[str, Any]:
    """Ensure a minimal decision contract for dynamic widgets/facettes.

    Adds/normalizes: verdict, confidence, why, risk (level/caveat), risk_level,
    risk_flag, freshness.
    """
    if not isinstance(payload, dict):
        return payload

    # freshness is duplicated in many payloads; keep whatever exists.
    resolved_freshness = (
        str(freshness or "").strip()
        or str(payload.get("freshness") or "").strip()
        or str(payload.get("generated_at") or "").strip()
    )
    if resolved_freshness:
        payload.setdefault("freshness", resolved_freshness)

    resolved_verdict = coerce_verdict(
        verdict if verdict is not None else payload.get("verdict") or payload.get("action"),
        default="hold",
    )
    payload.setdefault("verdict", resolved_verdict)

    resolved_confidence = coerce_confidence(
        confidence if confidence is not None else payload.get("confidence"),
        default=0.5,
    )
    if "confidence" not in payload:
        payload["confidence"] = resolved_confidence

    resolved_risk_level = normalize_risk_level(
        risk_level
        if risk_level is not None
        else payload.get("risk_level")
        or (payload.get("risk") or {}).get("level")
        if isinstance(payload.get("risk"), dict)
        else payload.get("risk"),
        default="medium",
    )
    payload.setdefault("risk_level", resolved_risk_level)

    risk_flag_val = payload.get("risk_flag")
    if risk_flag_val is None:
        payload["risk_flag"] = resolved_risk_level in {"high", "critical"}

    risk_obj = payload.get("risk")
    if not isinstance(risk_obj, dict):
        risk_obj = {"level": resolved_risk_level, "caveat": ""}
    risk_obj.setdefault("level", resolved_risk_level)
    if risk_caveat is not None and str(risk_caveat).strip():
        risk_obj["caveat"] = str(risk_caveat).strip()
    payload["risk"] = risk_obj

    if "why" not in payload and why is not None:
        if isinstance(why, list):
            payload["why"] = [str(item).strip() for item in why if str(item).strip()]
        else:
            text = str(why).strip()
            payload["why"] = text if text else []

    append_source_tag(payload, "decision_contract_v1", default_source=default_source)
    return payload


__all__ = [
    "append_source_tag",
    "coerce_confidence",
    "coerce_verdict",
    "ensure_endpoint_metadata",
    "ensure_source_list",
    "ensure_decision_contract",
    "never_empty_payload",
    "normalize_risk_level",
    "safe_float",
    "safe_int",
    "service_response",
    "service_response_with_metadata",
    "unwrap_storage_payload",
    "utc_now_iso",
]
