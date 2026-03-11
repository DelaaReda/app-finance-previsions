"""Reusable service entrypoints for Judge API endpoints.

Routes stay orchestration-only and delegate payload creation to this module.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from pathlib import Path
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional

from storage.io import load_json, save_json

try:
    from services.judge_quality import build_judge_quality_report  # type: ignore
except Exception:  # pragma: no cover
    build_judge_quality_report = None  # type: ignore

try:
    from services.service_standard import (
        append_source_tag,
        coerce_confidence,
        coerce_verdict,
        ensure_endpoint_metadata,
        ensure_source_list,
        ensure_decision_contract,
        normalize_risk_level,
        safe_int,
        service_response_with_metadata,
        utc_now_iso,
    )
except Exception:  # pragma: no cover
    from src.services.service_standard import (  # type: ignore
        append_source_tag,
        coerce_confidence,
        coerce_verdict,
        ensure_endpoint_metadata,
        ensure_source_list,
        ensure_decision_contract,
        normalize_risk_level,
        safe_int,
        service_response_with_metadata,
        utc_now_iso,
    )

try:
    from core.ticker_normalization import normalize_ticker  # type: ignore
    from core.ticker_normalization import normalize_tickers  # type: ignore
except Exception:  # pragma: no cover
    from platform.legacy.core.ticker_normalization import (  # type: ignore
        normalize_ticker,
        normalize_tickers,
    )

try:
    from platform.legacy.research.versioned_notes import VersionedNotesStore  # type: ignore
except Exception:  # pragma: no cover
    VersionedNotesStore = None  # type: ignore

# Keep legacy imports and flattened imports in sync for test monkeypatching and callers.
if __name__ == "domains.judge.application.judge_endpoint_service":
    sys.modules.setdefault(
        "services.judge_endpoint_service",
        sys.modules[__name__],
    )
elif __name__ == "services.judge_endpoint_service":
    sys.modules.setdefault(
        "domains.judge.application.judge_endpoint_service",
        sys.modules[__name__],
    )


JudgeVerdictsComputeFn = Callable[..., Awaitable[Dict[str, Any]]]
DECISION_JOURNAL_STORAGE_KEY = "decision_journal"
DECISION_JOURNAL_SCHEMA_VERSION = "decision_journal_v1"
DECISION_JOURNAL_FEEDBACK_HORIZONS = ("1d", "1w", "1m")
DECISION_JOURNAL_IMMUTABLE_ENTRY_KEY_PREFIX = f"{DECISION_JOURNAL_STORAGE_KEY}/entries"
DECISION_JOURNAL_IMMUTABLE_ENTRY_PATH_PREFIX = "runtime/data/decision_journal/entries"
DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY = "judge_decision_outcome_feedback_records"
DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION = "decision_outcome_feedback_records_v1"
_DECISION_JOURNAL_FEEDBACK_DELTAS = {
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
}
_FEEDBACK_STATUS_ALIASES = {
    "pending": "pending",
    "open": "in_progress",
    "recorded": "in_progress",
    "in_progress": "in_progress",
    "in-progress": "in_progress",
    "resolved": "resolved",
    "done": "resolved",
    "complete": "resolved",
    "completed": "resolved",
    "closed": "resolved",
}


def _default_risk_levels() -> List[str]:
    return ["low", "medium", "high", "critical"]


def _decision_journal_dir() -> Path:
    override = str(os.getenv("JUDGE_DECISION_JOURNAL_DIR") or "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    try:
        from platform.legacy.core.path_resolver import get_data_directory  # type: ignore

        base_dir = get_data_directory()
    except Exception:  # pragma: no cover
        base_dir = Path(__file__).resolve().parents[4] / "runtime" / "data"
    path = base_dir / "decision_journal"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _decision_journal_store() -> VersionedNotesStore:
    if VersionedNotesStore is None:
        raise RuntimeError("VersionedNotesStore unavailable")
    return VersionedNotesStore(storage_dir=str(_decision_journal_dir()))


def _decision_journal_entries_dir() -> Path:
    path = _decision_journal_dir() / "entries"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _decision_journal_entry_path(decision_id: str) -> Path:
    return _decision_journal_entries_dir() / f"{decision_id}.json"


def _coerce_text_list(*values: Any) -> List[str]:
    items: List[str] = []
    seen = set()
    for value in values:
        if isinstance(value, list):
            for raw_item in value:
                text = str(raw_item or "").strip()
                if not text:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                items.append(text)
            continue
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _build_strategy_playbook(verdict: Dict[str, Any], *, profile: str) -> Dict[str, Any]:
    """Project a Judge verdict into a minimal strategy playbook payload."""
    ticker = normalize_ticker(str(verdict.get("ticker") or "").strip()) or "UNKNOWN"

    go_no_go = verdict.get("go_no_go") or {}
    decision = str(go_no_go.get("decision") or "").strip().lower() if isinstance(go_no_go, dict) else ""
    if decision in {"go", "buy", "long"}:
        decision = "go"
    elif decision in {"no_go", "sell", "short", "no-go"}:
        decision = "no_go"
    elif not decision:
        confidence = _coerce_float(verdict.get("confidence"), 0.0)
        expected_return = _coerce_float(verdict.get("expected_return"), 0.0)
        if confidence >= 0.6 and expected_return >= 0:
            decision = "go"
        elif confidence <= 0.4 and expected_return <= 0:
            decision = "no_go"
        else:
            decision = "hold"

    summary = verdict.get("summary") or verdict.get("reasoning") or []
    if isinstance(summary, str):
        summary = [summary]
    if not isinstance(summary, list):
        summary = []

    expected_return = _coerce_float(verdict.get("expected_return"), 0.0)
    confidence = _coerce_float(verdict.get("confidence"), 0.0)
    risk_level = str(verdict.get("risk_level") or "medium").strip().lower()
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = "medium"
    horizon = str(verdict.get("horizon") or "1w").strip() or "1w"
    playbook_id = f"{ticker}:{horizon}:{decision}:{profile}"
    reasons = _coerce_text_list((go_no_go or {}).get("reasons", [])) if isinstance(go_no_go, dict) else []
    raw_impacts = verdict.get("impacts") if isinstance(verdict.get("impacts"), dict) else {}
    scenarios = verdict.get("scenarios") if isinstance(verdict.get("scenarios"), list) else []
    risks = verdict.get("risks") if isinstance(verdict.get("risks"), list) else []

    conflicts: List[str] = _coerce_text_list(verdict.get("conflicts", []))
    if decision == "go" and risk_level in {"high", "critical"}:
        conflicts.append("risk_profile_too_aggressive")
    if decision == "no_go" and expected_return > 0.03:
        conflicts.append("positive_signal_overridden_by_filters")

    # Divergence visibility: when inferred signal logic and conflict-gated playbook decision disagree,
    # we intentionally expose this as a conflict for explainability.
    signal_signal = None
    if expected_return >= 0 and confidence >= 0.6:
        signal_signal = "go"
    elif expected_return <= 0 and confidence <= 0.4:
        signal_signal = "no_go"
    else:
        signal_signal = "hold"

    if signal_signal != decision:
        conflicts.append("signal_divergence")

    # Preserve upstream conflict hints and keep response stable/deterministic.
    seen_conflicts = set()
    normalized_conflicts: List[str] = []
    for conflict in conflicts:
        if not isinstance(conflict, str):
            continue
        normalized = str(conflict).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen_conflicts:
            continue
        seen_conflicts.add(key)
        normalized_conflicts.append(normalized)

    return {
        "playbook_id": playbook_id,
        "ticker": ticker,
        "horizon": horizon,
        "profile": profile,
        "decision": decision,
        "confidence": round(confidence, 4),
        "expected_return": round(expected_return, 6),
        "risk_level": risk_level,
        "summary": _coerce_text_list(summary)[:2],
        "recommended_actions": _coerce_text_list(verdict.get("actions") or []),
        "data_needed": _coerce_text_list(verdict.get("data_needed") or []),
        "evidence": {
            "scenario_count": len(scenarios),
            "risk_count": len(risks),
            "impact_keys": sorted(raw_impacts.keys()),
        },
        "reasons": reasons,
        "conflicts": normalized_conflicts,
        "decision_id": verdict.get("decision_id"),
    }


def _fallback_horizon(*, profile: str, verdict: Dict[str, Any]) -> str:
    raw_horizon = str(
        verdict.get("horizon")
        or (verdict.get("ml_prior") or {}).get("horizon")
        or ""
    ).strip()
    if raw_horizon:
        return raw_horizon

    profile_text = str(profile or "").strip().lower()
    for candidate in ("1d", "1w", "1m", "3m", "6m", "1y"):
        if candidate in profile_text:
            return candidate
    return "1w"


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_utc_datetime(value: Any) -> datetime:
    text = str(value or "").strip()
    if text:
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _utc_datetime_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_outcome_feedback(captured_at: str) -> Dict[str, Any]:
    captured_at_dt = _parse_utc_datetime(captured_at)
    checkpoints: List[Dict[str, Any]] = []
    for horizon in DECISION_JOURNAL_FEEDBACK_HORIZONS:
        due_at = _utc_datetime_iso(
            captured_at_dt + _DECISION_JOURNAL_FEEDBACK_DELTAS[horizon]
        )
        checkpoints.append(
            {
                "horizon": horizon,
                "status": "pending",
                "due_at": due_at,
                "record_mode": "separate_record",
            }
        )

    next_checkpoint = checkpoints[0] if checkpoints else None
    return {
        "schema_version": "decision_outcome_feedback_v1",
        "status": "pending",
        "update_mode": "separate_records",
        "latest_feedback_at": None,
        "next_checkpoint": next_checkpoint,
        "checkpoints": checkpoints,
    }


def _normalize_feedback_status(raw_status: Any) -> Optional[str]:
    text = str(raw_status or "").strip().lower()
    if not text:
        return None
    return _FEEDBACK_STATUS_ALIASES.get(text, text)


def _coerce_feedback_status(raw_status: Any, *, has_measurement: bool = False) -> str:
    normalized = _normalize_feedback_status(raw_status)
    if normalized in {"pending", "in_progress", "resolved"}:
        return normalized
    return "resolved" if has_measurement else "in_progress"


def _coerce_feedback_horizon(raw_horizon: Any) -> str:
    raw = str(raw_horizon or "").strip().lower()
    if raw in DECISION_JOURNAL_FEEDBACK_HORIZONS:
        return raw
    return ""


def _coerce_outcome_feedback_payload(payload: Dict[str, Any], *, now_iso: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("feedback must be an object")

    decision_id = str(payload.get("decision_id") or "").strip()
    if not decision_id:
        raise ValueError("decision_id is required")

    horizon = _coerce_feedback_horizon(payload.get("horizon"))
    if not horizon:
        raise ValueError(
            "horizon is required and must be one of 1d, 1w, 1m"
        )

    outcome = payload.get("outcome")
    if isinstance(outcome, str):
        outcome_text = outcome.strip().lower()
    elif outcome is not None:
        outcome_text = str(outcome).strip()
    else:
        outcome_text = None

    recorded_at_raw = str(payload.get("recorded_at") or now_iso).strip() or now_iso
    recorded_at = _utc_datetime_iso(_parse_utc_datetime(recorded_at_raw))

    notes = str(payload.get("notes") or "").strip() or None
    actual_return = _safe_float(payload.get("actual_return"))
    has_measurement = outcome_text is not None or actual_return is not None
    record = {
        "schema_version": DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION,
        "record_id": sha1(
            f"{decision_id}|{horizon}|{recorded_at}".encode("utf-8")
        ).hexdigest()[:16],
        "decision_id": decision_id,
        "horizon": horizon,
        "status": _coerce_feedback_status(
            payload.get("status"),
            has_measurement=has_measurement,
        ),
        "outcome": outcome_text,
        "recorded_at": recorded_at,
    }

    if actual_return is not None:
        record["actual_return"] = actual_return
    if notes is not None:
        record["notes"] = notes
    return record


def _load_outcome_feedback_records() -> List[Dict[str, Any]]:
    store = load_json(DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY) or {}
    if not isinstance(store, dict):
        return []
    records = store.get("records")
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _build_outcome_feedback_store_payload(
    records: List[Dict[str, Any]],
    *,
    freshness: str,
) -> Dict[str, Any]:
    return {
        "schema_version": DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION,
        "record_mode": "append_only",
        "count": len(records),
        "updated_at": freshness,
        "records": records,
    }


def _build_feedback_records_by_decision(
    records: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Index feedback records by decision id + horizon with latest timestamp."""

    indexed: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for record in records:
        if not isinstance(record, dict):
            continue

        decision_id = str(record.get("decision_id") or "").strip()
        horizon = _coerce_feedback_horizon(record.get("horizon"))
        if not decision_id or not horizon:
            continue

        recorded_at = str(record.get("recorded_at") or "").strip()
        if not recorded_at:
            continue

        current = indexed[decision_id].get(horizon)
        if not isinstance(current, dict):
            indexed[decision_id][horizon] = dict(record)
            continue

        current_recorded_at = str(current.get("recorded_at") or "").strip()
        if not current_recorded_at:
            indexed[decision_id][horizon] = dict(record)
            continue

        if _parse_utc_datetime(recorded_at) <= _parse_utc_datetime(current_recorded_at):
            continue
        indexed[decision_id][horizon] = dict(record)

    return indexed


def _attach_feedback_records_to_journal_entry(
    entry: Dict[str, Any],
    feedback_by_decision: Dict[str, Dict[str, Dict[str, Any]]],
) -> int:
    """Apply latest feedback records to one journal entry.

    Returns remaining pending checkpoints.
    """
    if not isinstance(entry, dict):
        return 0

    feedback = entry.get("outcome_feedback")
    if not isinstance(feedback, dict):
        return 0

    decision_id = str(entry.get("decision_id") or "").strip()
    if not decision_id:
        return 0

    checkpoints = feedback.get("checkpoints")
    if not isinstance(checkpoints, list):
        return 0

    by_horizon = feedback_by_decision.get(decision_id, {})
    latest_feedback_at: Optional[datetime] = None
    next_checkpoint = None
    pending_count = 0

    for checkpoint in checkpoints:
        if not isinstance(checkpoint, dict):
            continue

        horizon = str(checkpoint.get("horizon") or "").strip()
        record = by_horizon.get(horizon)
        if isinstance(record, dict):
            checkpoint["status"] = _coerce_feedback_status(record.get("status"))
            if record.get("outcome") is not None:
                checkpoint["outcome"] = str(record.get("outcome")).strip()
            if record.get("actual_return") is not None:
                checkpoint["actual_return"] = _safe_float(record.get("actual_return"))
            if record.get("notes") is not None:
                checkpoint["notes"] = str(record.get("notes")).strip()

            recorded_at = str(record.get("recorded_at") or "").strip()
            checkpoint["recorded_at"] = recorded_at
            parsed_recorded_at = _parse_utc_datetime(recorded_at)
            if latest_feedback_at is None or parsed_recorded_at > latest_feedback_at:
                latest_feedback_at = parsed_recorded_at

        if str(checkpoint.get("status") or "").strip().lower() == "pending":
            pending_count += 1
            if next_checkpoint is None:
                next_checkpoint = checkpoint

    if latest_feedback_at is not None:
        feedback["latest_feedback_at"] = _utc_datetime_iso(latest_feedback_at)

    feedback["next_checkpoint"] = next_checkpoint
    total_checkpoints = len([c for c in checkpoints if isinstance(c, dict)])
    if latest_feedback_at is None:
        # Keep original pending default when there is no historical feedback.
        if not feedback.get("status"):
            feedback["status"] = "pending"
    elif pending_count == 0:
        feedback["status"] = "resolved"
    else:
        feedback["status"] = "in_progress"
    if (feedback.get("status") or "") == "pending" and total_checkpoints == pending_count and latest_feedback_at is None:
        feedback["next_checkpoint"] = feedback.get("next_checkpoint")
    return pending_count


async def append_judge_decision_outcome_feedback(
    *,
    feedback: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist outcome feedback as an append-only decision feedback record."""
    now_iso = utc_now_iso()
    try:
        record = _coerce_outcome_feedback_payload(feedback, now_iso=now_iso)
        records = list(_load_outcome_feedback_records())
        records.append(record)

        payload = _build_outcome_feedback_store_payload(records, freshness=now_iso)
        saved_path = save_json(
            DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY,
            payload,
            source=["judge_outcome_feedback_service", "append_only_record"],
            version=DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION,
        )
        if not saved_path:
            raise RuntimeError(
                "failed to persist judge outcome feedback record"
            )

        return service_response_with_metadata(
            {
                "schema_version": DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION,
                "status": "recorded",
                "decision_id": record["decision_id"],
                "horizon": record["horizon"],
                "record_id": record["record_id"],
                "recorded_at": record["recorded_at"],
                "stored_records": len(records),
                "feedback": record,
                "store": {
                    "storage_key": DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY,
                    "status": "persisted",
                    "path": str(saved_path),
                },
                "source": ["judge_outcome_feedback_service"],
            },
            default_source="judge_outcome_feedback_service",
            freshness=record["recorded_at"],
            status="ok",
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "schema_version": DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION,
                "status": "degraded",
                "message": "Unable to record decision outcome feedback.",
                "error": str(exc),
                "stored_records": 0,
                "source": ["judge_outcome_feedback_service", "fallback"],
            },
            default_source="judge_outcome_feedback_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_decision_outcome_feedback(
    *,
    decision_id: Optional[str] = None,
    horizon: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    """Return persisted decision outcome feedback records with optional filters."""
    now_iso = utc_now_iso()
    try:
        records = list(_load_outcome_feedback_records())
        normalized_decision_id = str(decision_id or "").strip()
        normalized_horizon = _coerce_feedback_horizon(horizon) if horizon else ""
        if horizon and not normalized_horizon:
            raise ValueError("horizon must be one of 1d, 1w, 1m")
        normalized_status = _normalize_feedback_status(status_filter)

        filtered_records = records
        if normalized_decision_id:
            filtered_records = [
                item
                for item in filtered_records
                if str(item.get("decision_id") or "").strip() == normalized_decision_id
            ]
        if normalized_horizon:
            filtered_records = [
                item
                for item in filtered_records
                if str(item.get("horizon") or "").strip() == normalized_horizon
            ]
        if normalized_status:
            filtered_records = [
                item
                for item in filtered_records
                if _coerce_feedback_status(item.get("status")) == normalized_status
            ]

        try:
            max_items = max(1, int(limit))
        except Exception:
            max_items = 200

        ordered_records = sorted(
            filtered_records,
            key=lambda record: str(record.get("recorded_at") or ""),
            reverse=True,
        )
        returned_records = ordered_records[:max_items]

        return service_response_with_metadata(
            {
                "schema_version": DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION,
                "record_mode": "append_only",
                "filters": {
                    "decision_id": normalized_decision_id or None,
                    "horizon": normalized_horizon or None,
                    "status": normalized_status or None,
                },
                "count": len(records),
                "filtered_count": len(filtered_records),
                "returned_count": len(returned_records),
                "records": returned_records,
            },
            default_source="judge_outcome_feedback_service",
            freshness=now_iso,
            status="ok",
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "schema_version": DECISION_OUTCOME_FEEDBACK_RECORDS_SCHEMA_VERSION,
                "record_mode": "append_only",
                "filters": {
                    "decision_id": str(decision_id or "").strip() or None,
                    "horizon": horizon or None,
                    "status": str(status_filter or "").strip() or None,
                },
                "count": 0,
                "filtered_count": 0,
                "returned_count": 0,
                "records": [],
                "message": "Unable to read decision outcome feedback records.",
                "error": str(exc),
                "source": ["judge_outcome_feedback_service", "fallback"],
            },
            default_source="judge_outcome_feedback_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_decision_journal_payload(
    *,
    decision_id: Optional[str] = None,
    profile: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    """Return stored decision journal entries with latest outcome feedback projection."""
    now_iso = utc_now_iso()
    try:
        raw_payload = load_json(DECISION_JOURNAL_STORAGE_KEY) or {}
        raw_entries = raw_payload.get("entries")
        if not isinstance(raw_entries, list):
            raw_entries = []

        normalized_decision_id = str(decision_id or "").strip()
        normalized_profile = str(profile or "").strip().lower()
        normalized_status = _normalize_feedback_status(status_filter)

        try:
            max_items = max(1, int(limit))
        except Exception:
            max_items = 200

        feedback_by_decision = {}
        try:
            feedback_by_decision = _build_feedback_records_by_decision(
                list(_load_outcome_feedback_records())
            )
        except Exception:
            feedback_by_decision = {}

        entries: List[Dict[str, Any]] = []
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            journal_entry = dict(entry)
            _attach_feedback_records_to_journal_entry(
                journal_entry,
                feedback_by_decision=feedback_by_decision,
            )
            entries.append(journal_entry)

        if normalized_decision_id:
            entries = [
                entry
                for entry in entries
                if str(entry.get("decision_id") or "").strip() == normalized_decision_id
            ]
        if normalized_profile:
            entries = [
                entry
                for entry in entries
                if str(entry.get("profile") or "").strip().lower() == normalized_profile
            ]
        if normalized_status:
            entries = [
                entry
                for entry in entries
                if str(((entry.get("outcome_feedback") or {}).get("status") or "")).strip().lower()
                == normalized_status
            ]

        entries.sort(
            key=lambda entry: str(entry.get("recorded_at") or entry.get("captured_at") or ""),
            reverse=True,
        )
        returned_entries = entries[:max_items]
        pending_feedback_records = sum(
            len(
                [
                    checkpoint
                    for checkpoint in (entry.get("outcome_feedback") or {}).get("checkpoints", [])
                    if str((checkpoint or {}).get("status") or "").strip().lower()
                    == "pending"
                ]
            )
            for entry in returned_entries
            if isinstance(entry, dict)
        )

        return service_response_with_metadata(
            {
                "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
                "record_mode": "append_only",
                "filters": {
                    "decision_id": normalized_decision_id or None,
                    "profile": normalized_profile or None,
                    "status": normalized_status or None,
                },
                "count": len(raw_entries),
                "filtered_count": len(entries),
                "returned_count": len(returned_entries),
                "feedback_loop": {
                    "schema_version": "decision_outcome_feedback_v1",
                    "tracked_horizons": list(DECISION_JOURNAL_FEEDBACK_HORIZONS),
                    "update_mode": "separate_records",
                    "pending_feedback_records": pending_feedback_records,
                },
                "entries": returned_entries,
            },
            default_source="judge_decision_journal_service",
            freshness=now_iso,
            status="ok",
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
                "record_mode": "append_only",
                "filters": {
                    "decision_id": str(decision_id or "").strip() or None,
                    "profile": str(profile or "").strip() or None,
                    "status": str(status_filter or "").strip() or None,
                },
                "count": 0,
                "filtered_count": 0,
                "returned_count": 0,
                "entries": [],
                "feedback_loop": {
                    "schema_version": "decision_outcome_feedback_v1",
                    "tracked_horizons": list(DECISION_JOURNAL_FEEDBACK_HORIZONS),
                    "update_mode": "separate_records",
                    "pending_feedback_records": 0,
                },
                "source": ["judge_decision_journal_service", "fallback"],
                "message": "Unable to read judge decision journal.",
                "error": str(exc),
            },
            default_source="judge_decision_journal_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


def _build_journal_entry(
    verdict: Dict[str, Any],
    *,
    profile: str,
    fallback_generated_at: str,
    default_sources: List[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(verdict, dict):
        return None

    captured_at = str(
        verdict.get("generated_at")
        or (verdict.get("meta") or {}).get("generated_at")
        or fallback_generated_at
        or utc_now_iso()
    ).strip() or utc_now_iso()
    ticker = str(verdict.get("ticker") or "UNKNOWN").strip().upper() or "UNKNOWN"
    action = coerce_verdict(
        verdict.get("verdict") or verdict.get("action") or verdict.get("direction"),
        default="hold",
    )
    confidence = coerce_confidence(verdict.get("confidence"), default=0.5)
    why = _coerce_text_list(
        verdict.get("why"),
        verdict.get("summary"),
        verdict.get("reasoning"),
    ) or ["Decision generated from judge verdict payload."]

    risk_payload = verdict.get("risk") if isinstance(verdict.get("risk"), dict) else {}
    risk_level = normalize_risk_level(
        verdict.get("risk_level") or risk_payload.get("level"),
        default="medium",
    )
    risk_caveat = str(
        risk_payload.get("caveat")
        or verdict.get("risk_caveat")
        or verdict.get("risk_reason")
        or ""
    ).strip()
    sources = ensure_source_list(
        verdict.get("source") or (verdict.get("meta") or {}).get("source") or default_sources,
        default_source="judge_endpoint_service",
    )
    horizon = _fallback_horizon(profile=profile, verdict=verdict)
    expected_return = _safe_float(verdict.get("expected_return"))
    if expected_return is None:
        ml_prior = verdict.get("ml_prior")
        if isinstance(ml_prior, dict):
            expected_return = _safe_float(ml_prior.get("pred_return"))
    score = _safe_float(verdict.get("score"))
    if score is None:
        phase_scores = verdict.get("phase_scores")
        if isinstance(phase_scores, dict):
            score = _safe_float(phase_scores.get("fusion"))
    explicit_decision_id = str(verdict.get("decision_id") or "").strip()
    if explicit_decision_id:
        decision_id = explicit_decision_id
    else:
        decision_basis = "|".join(
            [
                ticker,
                horizon,
                action,
                captured_at,
                str(profile or "").strip().lower() or "default",
            ]
        )
        decision_id = f"judge_{sha1(decision_basis.encode('utf-8')).hexdigest()[:16]}"

    return {
        "decision_id": decision_id,
        "date": captured_at[:10],
        "captured_at": captured_at,
        "ticker": ticker,
        "action": action,
        "confidence": confidence,
        "horizon": horizon,
        "why": why,
        "risk": {
            "level": risk_level,
            "caveat": risk_caveat,
        },
        "prediction": {
            "expected_return": expected_return,
            "score": score,
        },
        "outcome_feedback": _build_outcome_feedback(captured_at),
        "sources": sources,
        "profile": str(profile or "").strip() or "default",
    }


def _serialize_stored_decision_note(note: Any) -> Dict[str, Any]:
    metadata = dict(note.metadata) if isinstance(getattr(note, "metadata", None), dict) else {}
    version = note.versions[-1] if getattr(note, "versions", None) else None
    captured_at = str(
        metadata.get("captured_at")
        or metadata.get("recorded_at")
        or note.created_at
        or utc_now_iso()
    ).strip() or utc_now_iso()
    entry = {
        "decision_id": str(
            metadata.get("decision_id")
            or metadata.get("note_id")
            or note.note_id
        ),
        "date": str(metadata.get("date") or captured_at[:10]),
        "captured_at": captured_at,
        "recorded_at": str(metadata.get("recorded_at") or captured_at),
        "ticker": str(metadata.get("ticker") or note.ticker or "UNKNOWN").strip().upper() or "UNKNOWN",
        "action": coerce_verdict(metadata.get("action") or metadata.get("verdict"), default="hold"),
        "confidence": coerce_confidence(metadata.get("confidence"), default=0.5),
        "horizon": str(metadata.get("horizon") or "1w").strip() or "1w",
        "why": _coerce_text_list(metadata.get("why")),
        "risk": (
            dict(metadata.get("risk"))
            if isinstance(metadata.get("risk"), dict)
            else {
                "level": normalize_risk_level(metadata.get("risk_level"), default="medium"),
                "caveat": str(metadata.get("risk_caveat") or "").strip(),
            }
        ),
        "prediction": (
            dict(metadata.get("prediction"))
            if isinstance(metadata.get("prediction"), dict)
            else {
                "expected_return": _safe_float(metadata.get("expected_return")),
                "score": _safe_float(metadata.get("score")),
            }
        ),
        "outcome_feedback": (
            dict(metadata.get("outcome_feedback"))
            if isinstance(metadata.get("outcome_feedback"), dict)
            else _build_outcome_feedback(captured_at)
        ),
        "sources": ensure_source_list(
            metadata.get("sources") or getattr(version, "references", None),
            default_source="judge_decision_journal_service",
        ),
        "profile": str(metadata.get("profile") or "manual").strip() or "manual",
        "provenance": str(metadata.get("provenance") or "manual").strip() or "manual",
        "recommendation_id": metadata.get("recommendation_id"),
        "context": metadata.get("context") if isinstance(metadata.get("context"), dict) else {},
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "title": note.title,
        "summary": getattr(version, "summary", "") or note.title,
        "note_id": note.note_id,
        "source": ["judge_decision_journal_service"],
    }
    ensure_decision_contract(
        entry,
        default_source="judge_decision_journal_service",
        verdict=entry.get("action"),
        confidence=entry.get("confidence"),
        why=entry.get("why"),
        risk_level=(entry.get("risk") or {}).get("level"),
        risk_caveat=(entry.get("risk") or {}).get("caveat"),
        freshness=entry.get("recorded_at"),
    )
    return entry


def _attach_decision_journal_projection(
    data: Dict[str, Any],
    *,
    profile: str,
    freshness: Optional[str],
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data

    verdicts = data.get("verdicts")
    if not isinstance(verdicts, list):
        verdicts = data.get("items")
    if not isinstance(verdicts, list):
        verdicts = []
        data["verdicts"] = verdicts

    generated_at = str(freshness or data.get("generated_at") or utc_now_iso()).strip() or utc_now_iso()
    default_sources = ensure_source_list(
        data.get("source"),
        default_source="judge_endpoint_service",
    )
    entries: List[Dict[str, Any]] = []
    try:
        feedback_by_decision = _build_feedback_records_by_decision(
            list(_load_outcome_feedback_records())
        )
    except Exception:
        feedback_by_decision = {}

    for verdict in verdicts:
        entry = _build_journal_entry(
            verdict,
            profile=profile,
            fallback_generated_at=generated_at,
            default_sources=default_sources,
        )
        if entry is None:
            continue
        verdict.setdefault("decision_id", entry["decision_id"])
        _attach_feedback_records_to_journal_entry(
            entry,
            feedback_by_decision=feedback_by_decision,
        )
        entries.append(entry)

    pending_feedback_records = sum(
        len(
            [
                checkpoint
                for checkpoint in (entry.get("outcome_feedback") or {}).get("checkpoints", [])
                if str((checkpoint or {}).get("status") or "").strip().lower()
                == "pending"
            ]
        )
        for entry in entries
        if isinstance(entry, dict)
    )
    store = _persist_decision_journal_entries(entries, generated_at=generated_at)
    data["decision_journal"] = {
        "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
        "generated_at": generated_at,
        "count": len(entries),
        "append_only": True,
        "link_field": "decision_id",
        "outcomes_update_mode": "separate_records",
        "feedback_horizons": list(DECISION_JOURNAL_FEEDBACK_HORIZONS),
        "feedback_loop": {
            "schema_version": "decision_outcome_feedback_v1",
            "update_mode": "separate_records",
            "tracked_horizons": list(DECISION_JOURNAL_FEEDBACK_HORIZONS),
            "pending_entries": len(entries),
            "pending_feedback_records": pending_feedback_records,
        },
        "entries": entries,
        "store": store,
    }
    append_source_tag(
        data,
        "decision_journal_projection_v1",
        default_source="judge_endpoint_service",
    )
    append_source_tag(
        data,
        "decision_outcome_feedback_v1",
        default_source="judge_endpoint_service",
    )
    store_status = str(store.get("status") or "").strip().lower()
    append_source_tag(
        data,
        (
            "decision_journal_store_v1"
            if store_status in {"persisted", "skipped"}
            else "decision_journal_store_degraded"
        ),
        default_source="judge_endpoint_service",
    )
    if store_status not in {"persisted", "skipped"}:
        warnings = data.get("warnings")
        if not isinstance(warnings, list):
            warnings = [] if warnings in (None, "") else [str(warnings)]
        warning = "decision_journal_store_unavailable"
        if warning not in warnings:
            warnings.append(warning)
        data["warnings"] = warnings
    return data


def _persist_decision_journal_entries(
    entries: List[Dict[str, Any]],
    *,
    generated_at: str,
) -> Dict[str, Any]:
    immutable_store = _persist_immutable_decision_journal_entries(
        entries,
        generated_at=generated_at,
    )
    if not entries:
        return {
            "status": "skipped",
            "storage_key": DECISION_JOURNAL_STORAGE_KEY,
            "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
            "persisted_count": 0,
            "total_entries": 0,
            "path": None,
            "immutable_store": immutable_store,
        }

    try:
        existing_payload = load_json(DECISION_JOURNAL_STORAGE_KEY) or {}
        existing_entries_raw = existing_payload.get("entries") if isinstance(existing_payload, dict) else []
        existing_entries = [
            entry
            for entry in existing_entries_raw
            if isinstance(entry, dict)
        ]
        existing_ids = {
            str(entry.get("decision_id") or "").strip()
            for entry in existing_entries
            if str(entry.get("decision_id") or "").strip()
        }
        new_entries: List[Dict[str, Any]] = []
        for entry in entries:
            decision_id = str(entry.get("decision_id") or "").strip()
            if not decision_id or decision_id in existing_ids:
                continue
            existing_ids.add(decision_id)
            new_entries.append(entry)

        merged_entries = existing_entries + new_entries
        saved_path = save_json(
            DECISION_JOURNAL_STORAGE_KEY,
            {
                "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
                "generated_at": generated_at,
                "count": len(merged_entries),
                "append_only": True,
                "link_field": "decision_id",
                "outcomes_update_mode": "separate_records",
                "feedback_horizons": list(DECISION_JOURNAL_FEEDBACK_HORIZONS),
                "entries": merged_entries,
            },
            source=["judge_endpoint_service", "decision_journal_store_v1"],
            version=DECISION_JOURNAL_SCHEMA_VERSION,
        )
        if not saved_path:
            return {
                "status": "degraded",
                "storage_key": DECISION_JOURNAL_STORAGE_KEY,
                "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
                "persisted_count": 0,
                "total_entries": len(merged_entries),
                "path": None,
                "immutable_store": immutable_store,
            }
        return {
            "status": (
                "persisted"
                if immutable_store.get("status") != "degraded"
                else "degraded"
            ),
            "storage_key": DECISION_JOURNAL_STORAGE_KEY,
            "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
            "persisted_count": len(new_entries),
            "total_entries": len(merged_entries),
            "path": str(saved_path),
            "immutable_store": immutable_store,
        }
    except Exception:
        return {
            "status": "degraded",
            "storage_key": DECISION_JOURNAL_STORAGE_KEY,
            "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
            "persisted_count": 0,
            "total_entries": 0,
            "path": None,
            "immutable_store": immutable_store,
        }


def _persist_immutable_decision_journal_entries(
    entries: List[Dict[str, Any]],
    *,
    generated_at: str,
) -> Dict[str, Any]:
    if not entries:
        return {
            "status": "skipped",
            "storage_key_prefix": DECISION_JOURNAL_IMMUTABLE_ENTRY_KEY_PREFIX,
            "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
            "path_prefix": DECISION_JOURNAL_IMMUTABLE_ENTRY_PATH_PREFIX,
            "persisted_count": 0,
            "existing_count": 0,
            "failed_count": 0,
        }

    persisted_count = 0
    existing_count = 0
    failed_count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        decision_id = str(entry.get("decision_id") or "").strip()
        if not decision_id:
            failed_count += 1
            continue

        if _decision_journal_entry_path(decision_id).exists():
            existing_count += 1
            continue

        save_result = save_json(
            f"{DECISION_JOURNAL_IMMUTABLE_ENTRY_KEY_PREFIX}/{decision_id}",
            {
                "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
                "record_mode": "immutable_snapshot",
                "append_only": True,
                "decision_id": decision_id,
                "generated_at": generated_at,
                "captured_at": str(entry.get("captured_at") or generated_at).strip()
                or generated_at,
                "ticker": str(entry.get("ticker") or "UNKNOWN").strip().upper()
                or "UNKNOWN",
                "action": coerce_verdict(entry.get("action"), default="hold"),
                "confidence": coerce_confidence(entry.get("confidence"), default=0.5),
                "horizon": str(entry.get("horizon") or "1w").strip() or "1w",
                "profile": str(entry.get("profile") or "default").strip() or "default",
                "prediction": (
                    dict(entry.get("prediction"))
                    if isinstance(entry.get("prediction"), dict)
                    else {}
                ),
                "risk": (
                    dict(entry.get("risk"))
                    if isinstance(entry.get("risk"), dict)
                    else {}
                ),
                "outcome_feedback": (
                    dict(entry.get("outcome_feedback"))
                    if isinstance(entry.get("outcome_feedback"), dict)
                    else {}
                ),
                "snapshot": dict(entry),
            },
            source=[
                "judge_endpoint_service",
                "decision_journal_store_v1",
                "immutable_snapshot",
            ],
            version=DECISION_JOURNAL_SCHEMA_VERSION,
        )
        if not save_result:
            failed_count += 1
            continue
        persisted_count += 1

    status = "persisted"
    if failed_count > 0:
        status = "degraded"
    elif persisted_count == 0 and existing_count > 0:
        status = "already_persisted"
    elif persisted_count == 0:
        status = "skipped"

    return {
        "status": status,
        "storage_key_prefix": DECISION_JOURNAL_IMMUTABLE_ENTRY_KEY_PREFIX,
        "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
        "path_prefix": DECISION_JOURNAL_IMMUTABLE_ENTRY_PATH_PREFIX,
        "persisted_count": persisted_count,
        "existing_count": existing_count,
        "failed_count": failed_count,
    }


async def get_judge_verdicts_payload(
    *,
    limit: int,
    min_confidence: float,
    ticker: Optional[List[str]],
    portfolio_id: Optional[str] = None,
    sort_by: Any,
    sort_order: Any,
    profile: str,
    debug: bool,
    debug_full: bool,
    x_debug_token: Optional[str],
    compute_verdicts_fn: JudgeVerdictsComputeFn,
) -> Dict[str, Any]:
    """Delegate heavy verdict generation to the provided reusable compute function."""
    response = await compute_verdicts_fn(
        limit=limit,
        min_confidence=min_confidence,
        ticker=ticker,
        portfolio_id=portfolio_id,
        sort_by=sort_by,
        sort_order=sort_order,
        profile=profile,
        debug=debug,
        debug_full=debug_full,
        x_debug_token=x_debug_token,
    )
    if not isinstance(response, dict):
        return response

    data = response.get("data")
    if not isinstance(data, dict):
        return response

    verdicts = data.get("verdicts")
    head = verdicts[0] if isinstance(verdicts, list) and verdicts and isinstance(verdicts[0], dict) else {}
    ensure_decision_contract(
        data,
        default_source="judge_endpoint_service",
        verdict=head.get("verdict") or head.get("action"),
        confidence=head.get("confidence"),
        why=head.get("why") or head.get("reasoning"),
        risk_level=head.get("risk_level") or head.get("risk"),
        risk_caveat=head.get("risk_caveat") or head.get("risk_reason"),
        freshness=response.get("freshness") or data.get("generated_at"),
    )
    _attach_decision_journal_projection(
        data,
        profile=profile,
        freshness=response.get("freshness") or data.get("generated_at"),
    )
    ensure_endpoint_metadata(
        data,
        default_source="judge_endpoint_service",
        freshness=response.get("freshness") or data.get("generated_at"),
    )
    return service_response_with_metadata(
        data,
        default_source="judge_endpoint_service",
        freshness=data.get("freshness"),
        status=data.get("status"),
        error=data.get("error"),
    )


async def get_judge_strategy_playbooks_payload(
    *,
    limit: int,
    min_confidence: float,
    ticker: Optional[List[str]],
    portfolio_id: Optional[str] = None,
    sort_by: Any,
    sort_order: Any,
    profile: str,
    debug: bool,
    debug_full: bool,
    x_debug_token: Optional[str],
    compute_verdicts_fn: JudgeVerdictsComputeFn,
) -> Dict[str, Any]:
    """Build strategy playbooks from verdict payload with stable, never-empty contract."""
    normalized_tickers = normalize_tickers(ticker or [])
    verdict_payload = await get_judge_verdicts_payload(
        limit=limit,
        min_confidence=min_confidence,
        ticker=ticker,
        portfolio_id=portfolio_id,
        sort_by=sort_by,
        sort_order=sort_order,
        profile=profile,
        debug=debug,
        debug_full=debug_full,
        x_debug_token=x_debug_token,
        compute_verdicts_fn=compute_verdicts_fn,
    )

    if not isinstance(verdict_payload, dict):
        return verdict_payload

    data = verdict_payload.get("data")
    if not isinstance(data, dict):
        return verdict_payload

    verdicts = data.get("verdicts")
    if not isinstance(verdicts, list):
        verdicts = data.get("items")
    if not isinstance(verdicts, list):
        verdicts = []

    playbooks = [
        _build_strategy_playbook(verdict, profile=profile)
        for verdict in verdicts
        if isinstance(verdict, dict)
    ]

    now_iso = utc_now_iso()
    response_data = {
        **data,
        "playbooks": playbooks,
        "count": len(playbooks),
        "generated_at": data.get("generated_at") or now_iso,
    }
    response_data["filters_applied"] = {
        "min_confidence": min_confidence,
        "tickers": normalized_tickers,
        "sort_by": str(sort_by),
        "sort_order": str(sort_order),
        "limit": limit,
        "profile": profile,
    }
    response_data["stats"] = {
        "go_count": len([p for p in playbooks if p.get("decision") == "go"]),
        "no_go_count": len([p for p in playbooks if p.get("decision") == "no_go"]),
        "avg_confidence": (
            sum(p.get("confidence", 0.0) for p in playbooks) / len(playbooks)
            if playbooks
            else 0.0
        ),
    }
    response_data.pop("verdicts", None)

    if debug:
        response_data["judge_source"] = {
            "data_count": len(verdicts),
            "source": data.get("source"),
            "status": verdict_payload.get("status"),
            "error": verdict_payload.get("error"),
        }
        if isinstance(data.get("debug_pipeline"), list):
            response_data["debug_pipeline"] = data.get("debug_pipeline")
        if isinstance(data.get("verdicts_raw"), list):
            response_data["verdicts_raw"] = data.get("verdicts_raw")
        debug_payload = []
        debug_llm_res = []
        for verdict_entry in verdicts:
            verdict_debug_payload = verdict_entry.get("debug_payload")
            verdict_debug_llm_res = verdict_entry.get("debug_llm_res")
            if isinstance(verdict_debug_payload, (dict, list)):
                debug_payload.append(verdict_debug_payload)
            if isinstance(verdict_debug_llm_res, (dict, list)):
                debug_llm_res.append(verdict_debug_llm_res)
        response_data["debug_payload"] = debug_payload
        response_data["debug_llm_res"] = debug_llm_res

    response_data.setdefault("source", ["judge_strategy_playbook_route"])
    append_source_tag(
        response_data,
        "judge_strategy_playbook_route",
        default_source="judge_strategy_playbook_route",
    )

    return service_response_with_metadata(
        response_data,
        default_source="judge_strategy_playbook_route",
        freshness=verdict_payload.get("freshness")
        or response_data.get("generated_at")
        or now_iso,
        status=verdict_payload.get("status"),
        error=verdict_payload.get("error"),
    )


async def get_judge_quality_payload(
    *,
    horizon_days: int,
    min_samples: int,
) -> Dict[str, Any]:
    """Rolling quality metrics for judge/forecast predictive performance."""
    now_iso = utc_now_iso()
    try:
        if not build_judge_quality_report:
            return service_response_with_metadata(
                {
                    "as_of": now_iso,
                    "horizon_days": horizon_days,
                    "min_samples": min_samples,
                    "overall": {"n": 0, "sample_status": "insufficient"},
                    "windows": {},
                    "recommendation": {
                        "status": "unavailable",
                        "message": "Judge quality service unavailable in this runtime.",
                    },
                },
                default_source="judge_quality_service",
                freshness=now_iso,
            )

        report = build_judge_quality_report(
            horizon_days=horizon_days,
            min_samples=min_samples,
        )
        freshness = report.get("as_of") or now_iso
        return service_response_with_metadata(
            report,
            default_source="judge_quality_service",
            freshness=str(freshness),
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "as_of": now_iso,
                "horizon_days": horizon_days,
                "min_samples": min_samples,
                "overall": {"n": 0, "sample_status": "insufficient"},
                "windows": {},
                "recommendation": {
                    "status": "error",
                    "message": "Judge quality computation failed.",
                },
                "error": str(exc),
            },
            default_source="judge_quality_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_quality_history_payload(
    *,
    horizon_days: int,
    min_samples: int,
    limit: int,
) -> Dict[str, Any]:
    """Historical quality snapshots for one (horizon, min_samples) scope."""
    now_iso = utc_now_iso()
    try:
        payload = load_json("judge_quality_tracking") or {}
        points = payload.get("points") if isinstance(payload, dict) else []
        points = points if isinstance(points, list) else []

        filtered = [
            point
            for point in points
            if isinstance(point, dict)
            and safe_int(point.get("horizon_days"), -1) == int(horizon_days)
            and safe_int(point.get("min_samples"), -1) == int(min_samples)
        ]
        filtered.sort(key=lambda point: str(point.get("as_of") or ""))
        filtered = filtered[-int(limit) :]
        latest = filtered[-1] if filtered else None

        return service_response_with_metadata(
            {
                "as_of": now_iso,
                "scope": {
                    "horizon_days": int(horizon_days),
                    "min_samples": int(min_samples),
                },
                "count": len(filtered),
                "latest": latest,
                "points": filtered,
            },
            default_source="judge_quality_history_service",
            freshness=str((latest or {}).get("as_of", now_iso)),
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "as_of": now_iso,
                "scope": {
                    "horizon_days": int(horizon_days),
                    "min_samples": int(min_samples),
                },
                "count": 0,
                "latest": None,
                "points": [],
                "error": str(exc),
                "message": "Judge quality history unavailable; fallback returned.",
            },
            default_source="judge_quality_history_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_options_payload(
    *,
    risk_levels_fn: Optional[Callable[[], List[str]]] = None,
) -> Dict[str, Any]:
    """Options payload for judge UI (never-empty)."""
    now_iso = utc_now_iso()
    try:
        risk_levels = (
            risk_levels_fn() if callable(risk_levels_fn) else _default_risk_levels()
        )
        options = {
            "sort_options": [
                {"value": "confidence", "label": "Confiance"},
                {"value": "expected_return", "label": "Retour attendu"},
                {"value": "risk_level", "label": "Niveau de risque"},
                {"value": "timestamp", "label": "Date de generation"},
            ],
            "risk_levels": risk_levels,
            "confidence_thresholds": [
                {"label": "Toutes", "value": 0.0},
                {"label": "Haute confiance (0.7+)", "value": 0.7},
                {"label": "Tres haute confiance (0.8+)", "value": 0.8},
                {"label": "Excellente confiance (0.9+)", "value": 0.9},
            ],
            "generated_at": now_iso,
            "source": ["judge_options_service", "ui_helper_data", "merged"],
        }
        return service_response_with_metadata(
            options,
            default_source="judge_options_service",
            freshness=now_iso,
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "sort_options": [
                    {"value": "confidence", "label": "Confiance"},
                    {"value": "expected_return", "label": "Retour attendu"},
                ],
                "risk_levels": _default_risk_levels(),
                "confidence_thresholds": [
                    {"label": "Toutes", "value": 0.0},
                    {"label": "Haute confiance (0.7+)", "value": 0.7},
                ],
                "generated_at": now_iso,
                "error": str(exc),
                "message": (
                    "Judge options endpoint failed but fallback returned "
                    "to maintain never-empty contract"
                ),
            },
            default_source="judge_options_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


__all__ = [
    "JudgeVerdictsComputeFn",
    "get_judge_verdicts_payload",
    "get_judge_quality_payload",
    "get_judge_quality_history_payload",
    "get_judge_options_payload",
    "get_judge_decision_journal_payload",
    "append_judge_decision_outcome_feedback",
    "get_judge_decision_outcome_feedback",
]
