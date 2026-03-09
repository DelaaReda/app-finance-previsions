"""
Copilot Decision Journal - Immutable decision log + outcome feedback loop

Stores every copilot recommendation with:
- timestamp, context, verdict, confidence, horizon
- Outcome tracking at 1d/1w/1m checkpoints
- Hit rate and calibration metrics

B13-T1: Decision journal store
Deliverable: stockage immutable (timestamp, contexte, verdict, confidence, horizon)
Done: >= 95% des réponses copilot journalisées
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, List, Optional

from storage.io import load_json, save_json

try:
    from services.service_standard import (
        utc_now_iso,
        service_response_with_metadata,
        coerce_verdict,
        coerce_confidence,
    )
except Exception:
    from platform.legacy.services.service_standard import (
        utc_now_iso,
        service_response_with_metadata,
        coerce_verdict,
        coerce_confidence,
    )

# Storage keys
DECISION_JOURNAL_STORAGE_KEY = "copilot_decision_journal"
DECISION_JOURNAL_SCHEMA_VERSION = "copilot_decision_journal_v1"
DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY = "copilot_outcome_feedback_records"
DECISION_OUTCOME_FEEDBACK_SCHEMA_VERSION = "copilot_outcome_feedback_v1"

# Feedback horizons
FEEDBACK_HORIZONS = ("1d", "1w", "1m")
_FEEDBACK_DELTAS = {
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
}


def _copilot_decision_journal_dir() -> Path:
    """Get or create decision journal directory."""
    override = str(os.getenv("COPILOT_DECISION_JOURNAL_DIR") or "").strip()
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    try:
        from platform.legacy.core.path_resolver import get_data_directory
        base_dir = get_data_directory()
    except Exception:
        base_dir = Path(__file__).resolve().parents[5] / "runtime" / "data"
    path = base_dir / "copilot_decision_journal"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _decision_entries_dir() -> Path:
    """Get or create immutable entries directory."""
    path = _copilot_decision_journal_dir() / "entries"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _entry_path(decision_id: str) -> Path:
    """Get path for a specific decision entry."""
    return _decision_entries_dir() / f"{decision_id}.json"


def _generate_decision_id(question: str, tickers: List[str], timestamp: str) -> str:
    """Generate unique decision ID from question + scope + timestamp."""
    content = f"{question}|{','.join(sorted(tickers))}|{timestamp}"
    return sha1(content.encode()).hexdigest()[:16]


def _normalize_tickers(tickers: Optional[List[str]]) -> List[str]:
    """Normalize ticker list."""
    return sorted(
        {
            str(item).strip().upper()
            for item in (tickers or [])
            if str(item).strip()
        }
    )


def _coerce_horizon(horizon: Any) -> str:
    """Coerce horizon to valid value."""
    value = str(horizon or "1d").strip().lower()
    return value if value in FEEDBACK_HORIZONS else "1d"


def _load_outcome_feedback_records() -> List[Dict[str, Any]]:
    """Load all outcome feedback records."""
    try:
        store = load_json(DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY) or {}
        return list(store.get("records", []))
    except Exception:
        return []


def _save_outcome_feedback_records(records: List[Dict[str, Any]], freshness: str) -> Optional[Path]:
    """Save outcome feedback records."""
    payload = {
        "schema_version": DECISION_OUTCOME_FEEDBACK_SCHEMA_VERSION,
        "record_mode": "append_only",
        "count": len(records),
        "records": records,
        "freshness": freshness,
        "source": ["copilot_decision_journal_service"],
    }
    return save_json(
        DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY,
        payload,
        source=["copilot_decision_journal_service", "append_only_record"],
        version=DECISION_OUTCOME_FEEDBACK_SCHEMA_VERSION,
    )


def log_copilot_decision(
    *,
    question: str,
    answer: str,
    verdict: str,
    confidence: float,
    tickers: Optional[List[str]] = None,
    horizon: str = "1d",
    reasoning: Optional[str] = None,
    risk_level: str = "medium",
    sources: Optional[List[Dict[str, Any]]] = None,
    model: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Log one copilot decision to immutable journal.
    
    Args:
        question: User question
        answer: Copilot answer
        verdict: buy/sell/hold
        confidence: 0.0-1.0
        tickers: Related tickers
        horizon: 1d/1w/1m
        reasoning: Why this verdict
        risk_level: low/medium/high/critical
        sources: Context sources used
        model: LLM model used
        metadata: Additional metadata
    
    Returns:
        Decision journal entry with decision_id
    """
    now_iso = utc_now_iso()
    normalized_tickers = _normalize_tickers(tickers)
    decision_id = _generate_decision_id(question, normalized_tickers, now_iso)
    
    entry = {
        "decision_id": decision_id,
        "recorded_at": now_iso,
        "question": question,
        "answer": answer,
        "verdict": coerce_verdict(verdict),
        "confidence": coerce_confidence(confidence, default=0.5),
        "horizon": _coerce_horizon(horizon),
        "tickers": normalized_tickers,
        "reasoning": reasoning or "",
        "risk_level": risk_level,
        "sources": sources or [],
        "model": model,
        "metadata": metadata or {},
        "outcome": {
            "status": "pending",
            "checkpoints": {
                "1d": None,
                "1w": None,
                "1m": None,
            }
        }
    }
    
    # Save immutable entry
    entry_path = _entry_path(decision_id)
    try:
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(entry_path, 'w') as f:
            json.dump(entry, f, indent=2)
    except Exception as exc:
        return {
            "status": "degraded",
            "message": f"Failed to persist decision journal entry: {exc}",
            "decision_id": decision_id,
            "source": ["copilot_decision_journal_service", "fallback"],
        }
    
    return {
        "status": "recorded",
        "decision_id": decision_id,
        "recorded_at": now_iso,
        "horizon": entry["horizon"],
        "verdict": entry["verdict"],
        "confidence": entry["confidence"],
        "tickers": entry["tickers"],
        "store": {
            "storage_key": DECISION_JOURNAL_STORAGE_KEY,
            "path": str(entry_path),
            "status": "persisted",
        },
        "source": ["copilot_decision_journal_service"],
    }


def record_outcome_feedback(
    *,
    decision_id: str,
    horizon: str,
    status: str,
    actual_return: Optional[float] = None,
    predicted_return: Optional[float] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record outcome feedback for a decision.
    
    Args:
        decision_id: Decision to update
        horizon: 1d/1w/1m
        status: pending/in_progress/resolved
        actual_return: Actual return achieved
        predicted_return: Predicted return
        notes: Additional notes
    
    Returns:
        Confirmation with record_id
    """
    now_iso = utc_now_iso()
    record_id = sha1(f"{decision_id}|{horizon}|{now_iso}".encode()).hexdigest()[:12]
    
    feedback = {
        "record_id": record_id,
        "decision_id": decision_id,
        "horizon": _coerce_horizon(horizon),
        "status": status,
        "actual_return": actual_return,
        "predicted_return": predicted_return,
        "notes": notes or "",
        "recorded_at": now_iso,
        "source": ["copilot_outcome_feedback_service"],
    }
    
    # Append to records
    records = _load_outcome_feedback_records()
    records.append(feedback)
    
    saved_path = _save_outcome_feedback_records(records, now_iso)
    if not saved_path:
        raise RuntimeError("Failed to persist outcome feedback record")
    
    return {
        "status": "recorded",
        "record_id": record_id,
        "decision_id": decision_id,
        "horizon": feedback["horizon"],
        "recorded_at": now_iso,
        "stored_records": len(records),
        "store": {
            "storage_key": DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY,
            "path": str(saved_path),
            "status": "persisted",
        },
        "source": ["copilot_outcome_feedback_service"],
    }


def get_decision_journal(
    *,
    limit: int = 50,
    tickers: Optional[List[str]] = None,
    horizon: Optional[str] = None,
    verdict: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve decision journal entries.
    
    Args:
        limit: Max entries to return
        tickers: Filter by tickers
        horizon: Filter by horizon
        verdict: Filter by verdict
    
    Returns:
        List of decision entries
    """
    now_iso = utc_now_iso()
    entries_dir = _decision_entries_dir()
    
    if not entries_dir.exists():
        return {
            "count": 0,
            "entries": [],
            "source": ["copilot_decision_journal_service"],
        }
    
    # Load all entries
    all_entries = []
    for entry_file in entries_dir.glob("*.json"):
        try:
            with open(entry_file) as f:
                entry = json.load(f)
                all_entries.append(entry)
        except Exception:
            continue
    
    # Filter
    filtered = all_entries
    if tickers:
        normalized = set(_normalize_tickers(tickers))
        filtered = [e for e in filtered if set(e.get("tickers", [])) & normalized]
    if horizon:
        h = _coerce_horizon(horizon)
        filtered = [e for e in filtered if e.get("horizon") == h]
    if verdict:
        v = coerce_verdict(verdict)
        filtered = [e for e in filtered if e.get("verdict") == v]
    
    # Sort by recorded_at desc
    sorted_entries = sorted(
        filtered,
        key=lambda e: str(e.get("recorded_at", "")),
        reverse=True,
    )
    
    return {
        "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
        "count": len(all_entries),
        "filtered_count": len(filtered),
        "returned_count": len(sorted_entries[:limit]),
        "entries": sorted_entries[:limit],
        "source": ["copilot_decision_journal_service"],
        "freshness": now_iso,
    }


def get_outcome_feedback(
    *,
    decision_id: Optional[str] = None,
    horizon: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    """
    Retrieve outcome feedback records.
    
    Args:
        decision_id: Filter by decision
        horizon: Filter by horizon
        status: Filter by status
        limit: Max records
    
    Returns:
        List of feedback records
    """
    now_iso = utc_now_iso()
    records = _load_outcome_feedback_records()
    
    filtered = records
    if decision_id:
        filtered = [r for r in filtered if r.get("decision_id") == decision_id]
    if horizon:
        h = _coerce_horizon(horizon)
        filtered = [r for r in filtered if r.get("horizon") == h]
    if status:
        filtered = [r for r in filtered if r.get("status") == status]
    
    sorted_records = sorted(
        filtered,
        key=lambda r: str(r.get("recorded_at", "")),
        reverse=True,
    )
    
    return {
        "schema_version": DECISION_OUTCOME_FEEDBACK_SCHEMA_VERSION,
        "record_mode": "append_only",
        "count": len(records),
        "filtered_count": len(filtered),
        "returned_count": len(sorted_records[:limit]),
        "records": sorted_records[:limit],
        "source": ["copilot_outcome_feedback_service"],
        "freshness": now_iso,
    }


def compute_metrics() -> Dict[str, Any]:
    """
    Compute hit rate and calibration metrics.
    
    Returns:
        Metrics summary
    """
    now_iso = utc_now_iso()
    records = _load_outcome_feedback_records()
    
    # Group by horizon
    by_horizon: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        h = r.get("horizon", "1d")
        by_horizon[h].append(r)
    
    metrics = {}
    for horizon in FEEDBACK_HORIZONS:
        horizon_records = by_horizon.get(horizon, [])
        resolved = [r for r in horizon_records if r.get("status") == "resolved"]
        
        hit_count = 0
        total_error = 0.0
        for r in resolved:
            actual = r.get("actual_return")
            predicted = r.get("predicted_return")
            if actual is not None and predicted is not None:
                # Hit if same sign
                if (actual > 0) == (predicted > 0):
                    hit_count += 1
                total_error += abs(actual - predicted)
        
        count = len(resolved)
        metrics[horizon] = {
            "hit_rate": hit_count / count if count > 0 else None,
            "calibration_error": total_error / count if count > 0 else None,
            "resolved_count": count,
            "total_count": len(horizon_records),
        }
    
    return {
        "schema_version": DECISION_OUTCOME_FEEDBACK_SCHEMA_VERSION,
        "metrics": metrics,
        "total_feedback_records": len(records),
        "freshness": now_iso,
        "source": ["copilot_outcome_feedback_service"],
    }


# Exports
__all__ = [
    "log_copilot_decision",
    "record_outcome_feedback",
    "get_decision_journal",
    "get_outcome_feedback",
    "compute_metrics",
    "DECISION_JOURNAL_STORAGE_KEY",
    "DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY",
    "FEEDBACK_HORIZONS",
]
