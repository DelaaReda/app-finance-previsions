"""
Brief routes exposing daily/weekly market briefs generated offline.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter

from core.response import ok
from storage import io as storage_io

router = APIRouter()


def _trim_summary(value: Any, *, limit: int = 200) -> str:
    summary = str(value or "").strip()
    words = summary.split()
    if len(words) > limit:
        return " ".join(words[:limit])
    return summary


def _normalize_list(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list) and value:
            return list(value)
    for value in values:
        if isinstance(value, list):
            return []
    return []


def _normalize_source_list(*values: Any) -> list[str]:
    for value in values:
        if isinstance(value, (list, tuple)):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                return items
        token = str(value or "").strip()
        if token:
            return [token]
    return []


def _looks_like_brief_payload(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for key in (
        "summary",
        "market_regime",
        "market_sentiment",
        "regime",
        "top_opportunities",
        "top_signals",
        "top_risks",
        "sources",
        "source",
    ):
        candidate = value.get(key)
        if isinstance(candidate, list) and candidate:
            return True
        if isinstance(candidate, dict) and candidate:
            return True
        if str(candidate or "").strip():
            return True
    return False


def _load_brief_snapshot(key: str, section: str) -> Optional[Dict[str, Any]]:
    snapshot = storage_io.load_json(key)
    if not snapshot:
        return None
    if not isinstance(snapshot, dict):
        return None

    payload = snapshot.get("data")
    if isinstance(payload, dict):
        scoped = payload.get(section)
        if _looks_like_brief_payload(scoped):
            return scoped
        if _looks_like_brief_payload(payload):
            return dict(payload)

    scoped = snapshot.get(section)
    if _looks_like_brief_payload(scoped):
        return scoped
    if _looks_like_brief_payload(snapshot):
        return dict(snapshot)
    return None


def _normalize_brief_payload(
    brief: Dict[str, Any],
    *,
    default_source: str,
    degraded_reason: Optional[str] = None,
) -> Dict[str, Any]:
    payload = dict(brief or {})

    summary_seed = payload.get("summary") or payload.get("title")
    if summary_seed:
        summary = _trim_summary(summary_seed)
    else:
        summary = "Brief summary unavailable."
        degraded_reason = degraded_reason or "summary_missing"

    market_regime = str(
        payload.get("market_regime")
        or payload.get("market_sentiment")
        or payload.get("regime")
        or "UNKNOWN"
    ).strip() or "UNKNOWN"
    source_list = _normalize_source_list(payload.get("sources"), payload.get("source"), default_source)

    macro_signals = _normalize_list(payload.get("macro_signals"), payload.get("macro"))

    sector_rotation = payload.get("sector_rotation", {"top": [], "bottom": []})
    if not isinstance(sector_rotation, dict):
        sector_rotation = {"top": [], "bottom": []}
    sector_rotation.setdefault("top", [])
    sector_rotation.setdefault("bottom", [])

    top_opportunities = _normalize_list(
        payload.get("top_opportunities"),
        payload.get("top_signals"),
        payload.get("picks"),
    )
    top_risks = _normalize_list(payload.get("top_risks"))
    suppressed_risks = _normalize_list(payload.get("suppressed_risks"))
    alerting_metadata = payload.get("alerting_metadata")
    if not isinstance(alerting_metadata, dict):
        alerting_metadata = {}

    generated_at = str(payload.get("generated_at") or "").strip()
    if not generated_at:
        generated_at = datetime.utcnow().isoformat() + "Z"
    freshness = str(payload.get("freshness") or generated_at).strip() or generated_at

    payload["summary"] = summary
    payload["market_sentiment"] = market_regime
    payload["market_regime"] = market_regime
    payload["regime"] = market_regime
    payload["top_signals"] = top_opportunities
    payload["top_opportunities"] = top_opportunities
    payload["top_risks"] = top_risks
    payload["suppressed_risks"] = suppressed_risks
    payload["alerting_metadata"] = alerting_metadata
    payload["key_events"] = _normalize_list(payload.get("key_events"))
    payload["macro_signals"] = macro_signals
    payload["sector_rotation"] = sector_rotation
    payload["generated_at"] = generated_at
    payload["freshness"] = freshness
    payload["sources"] = source_list
    payload["source"] = source_list
    payload["degraded"] = degraded_reason is not None
    payload["degraded_reason"] = degraded_reason
    return payload


def _fallback_brief(message: str, *, source_token: str) -> Dict[str, Any]:
    generated_at = datetime.utcnow().isoformat() + "Z"
    return {
        "summary": message,
        "market_regime": "UNKNOWN",
        "top_opportunities": [],
        "top_risks": [],
        "suppressed_risks": [],
        "alerting_metadata": {},
        "key_events": [],
        "macro_signals": [],
        "sector_rotation": {"top": [], "bottom": []},
        "generated_at": generated_at,
        "freshness": generated_at,
        "source": [source_token],
        "sources": [source_token],
    }


@router.get("/brief/daily")
def get_daily_brief() -> Dict[str, Any]:
    brief = _load_brief_snapshot("brief_daily", "daily")
    if brief:
        return ok(_normalize_brief_payload(brief, default_source="brief_daily"))

    weekly_fallback = _load_brief_snapshot("brief_weekly", "weekly")
    if weekly_fallback:
        return ok(
            _normalize_brief_payload(
                weekly_fallback,
                default_source="brief_weekly",
                degraded_reason="daily_snapshot_missing_using_weekly",
            )
        )

    return ok(
        _normalize_brief_payload(
            _fallback_brief("No daily brief available yet.", source_token="fallback_empty"),
            default_source="fallback_empty",
            degraded_reason="daily_snapshot_missing",
        )
    )


@router.get("/brief/weekly")
def get_weekly_brief() -> Dict[str, Any]:
    brief = _load_brief_snapshot("brief_weekly", "weekly")
    if not brief:
        brief = _fallback_brief("No weekly brief available yet.", source_token="fallback_empty")
        return ok(
            _normalize_brief_payload(
                brief,
                default_source="fallback_empty",
                degraded_reason="weekly_snapshot_missing",
            )
        )
    return ok(_normalize_brief_payload(brief, default_source="brief_weekly"))


brief_router = router
