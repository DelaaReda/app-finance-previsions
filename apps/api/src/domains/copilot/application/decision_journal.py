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
PAPER_TRADE_EXECUTION_RECORDS_STORAGE_KEY = "copilot_paper_trade_execution_records"
PAPER_TRADE_EXECUTION_SCHEMA_VERSION = "copilot_paper_trade_execution_v1"

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


def _coerce_trade_side(side: Any) -> str:
    value = str(side or "buy").strip().lower()
    return value if value in {"buy", "sell"} else "buy"


def _coerce_float(value: Any, *, default: float = 0.0, minimum: Optional[float] = None) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


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


def _load_paper_trade_execution_records() -> List[Dict[str, Any]]:
    try:
        store = load_json(PAPER_TRADE_EXECUTION_RECORDS_STORAGE_KEY) or {}
        return list(store.get("records", []))
    except Exception:
        return []


def _save_paper_trade_execution_records(records: List[Dict[str, Any]], freshness: str) -> Optional[Path]:
    payload = {
        "schema_version": PAPER_TRADE_EXECUTION_SCHEMA_VERSION,
        "record_mode": "append_only",
        "count": len(records),
        "records": records,
        "freshness": freshness,
        "source": ["copilot_paper_trade_execution_service"],
    }
    return save_json(
        PAPER_TRADE_EXECUTION_RECORDS_STORAGE_KEY,
        payload,
        source=["copilot_paper_trade_execution_service", "append_only_record"],
        version=PAPER_TRADE_EXECUTION_SCHEMA_VERSION,
    )


def _index_records_by_decision(records: List[Dict[str, Any]], key: str = "decision_id") -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        record_key = str(record.get(key) or "").strip()
        if not record_key:
            continue
        index[record_key].append(record)
    for items in index.values():
        items.sort(key=lambda r: str(r.get("recorded_at", "")), reverse=True)
    return index


def _index_feedback_by_decision(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Build feedback lookup index by decision_id."""
    index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        decision_id = str(record.get("decision_id") or "").strip()
        if not decision_id:
            continue
        index[decision_id].append(record)

    for decision_feedback in index.values():
        decision_feedback.sort(
            key=lambda r: str(r.get("recorded_at", "")),
            reverse=True,
        )

    return index


def _build_execution_quality_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_records = len(records)
    total_fees = 0.0
    total_gross_notional = 0.0
    total_slippage_bps = 0.0
    total_unrealized_pnl = 0.0
    total_unrealized_pnl_percent = 0.0
    profitable_count = 0
    buy_count = 0
    sell_count = 0

    for record in records:
        side = _coerce_trade_side(record.get("side"))
        if side == "buy":
            buy_count += 1
        else:
            sell_count += 1

        fee_amount = _coerce_float(record.get("fee_amount"), minimum=0.0)
        gross_notional = _coerce_float(record.get("gross_notional"), minimum=0.0)
        slippage_bps = _coerce_float(record.get("slippage_bps"), minimum=0.0)
        unrealized_pnl = _coerce_float(record.get("unrealized_pnl"))
        unrealized_pnl_percent = _coerce_float(record.get("unrealized_pnl_percent"))

        total_fees += fee_amount
        total_gross_notional += gross_notional
        total_slippage_bps += slippage_bps
        total_unrealized_pnl += unrealized_pnl
        total_unrealized_pnl_percent += unrealized_pnl_percent
        if unrealized_pnl > 0:
            profitable_count += 1

    return {
        "total_records": total_records,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "win_rate": profitable_count / total_records if total_records > 0 else None,
        "avg_slippage_bps": total_slippage_bps / total_records if total_records > 0 else None,
        "avg_unrealized_pnl": total_unrealized_pnl / total_records if total_records > 0 else None,
        "avg_unrealized_pnl_percent": total_unrealized_pnl_percent / total_records if total_records > 0 else None,
        "total_fees": total_fees,
        "total_gross_notional": total_gross_notional,
    }


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


def execute_paper_trade(
    *,
    decision_id: str,
    ticker: str,
    side: str,
    quantity: float,
    reference_price: float,
    fee_bps: float = 0.0,
    slippage_bps: float = 0.0,
    market_price: Optional[float] = None,
    executed_at: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    now_iso = str(executed_at or utc_now_iso()).strip() or utc_now_iso()
    normalized_ticker = _normalize_tickers([ticker])
    if not decision_id.strip():
        raise ValueError("decision_id is required")
    if not normalized_ticker:
        raise ValueError("ticker is required")
    if _coerce_float(quantity, default=-1.0) <= 0:
        raise ValueError("quantity must be greater than 0")
    if _coerce_float(reference_price, default=-1.0) <= 0:
        raise ValueError("reference_price must be greater than 0")
    if market_price is not None and _coerce_float(market_price, default=-1.0) <= 0:
        raise ValueError("market_price must be greater than 0")
    if _coerce_float(fee_bps, default=-1.0) < 0:
        raise ValueError("fee_bps must be greater than or equal to 0")
    if _coerce_float(slippage_bps, default=-1.0) < 0:
        raise ValueError("slippage_bps must be greater than or equal to 0")

    normalized_side = _coerce_trade_side(side)
    normalized_quantity = _coerce_float(quantity, minimum=0.000001)
    normalized_reference_price = _coerce_float(reference_price, minimum=0.0)
    normalized_market_price = _coerce_float(
        market_price if market_price is not None else normalized_reference_price,
        minimum=0.0,
    )
    normalized_fee_bps = _coerce_float(fee_bps, minimum=0.0)
    normalized_slippage_bps = _coerce_float(slippage_bps, minimum=0.0)

    signed_direction = 1.0 if normalized_side == "buy" else -1.0
    slippage_per_share = normalized_reference_price * (normalized_slippage_bps / 10_000.0)
    assumed_fill_price = normalized_reference_price + (signed_direction * slippage_per_share)
    gross_notional = normalized_quantity * assumed_fill_price
    fee_amount = gross_notional * (normalized_fee_bps / 10_000.0)
    mark_notional = normalized_quantity * normalized_market_price
    unrealized_pnl = ((normalized_market_price - assumed_fill_price) * normalized_quantity * signed_direction) - fee_amount
    unrealized_pnl_percent = (unrealized_pnl / gross_notional) if gross_notional > 0 else 0.0
    execution_id = sha1(f"{decision_id}|{normalized_ticker[0]}|{normalized_side}|{now_iso}".encode()).hexdigest()[:12]

    record = {
        "execution_id": execution_id,
        "decision_id": decision_id.strip(),
        "ticker": normalized_ticker[0],
        "side": normalized_side,
        "quantity": normalized_quantity,
        "reference_price": normalized_reference_price,
        "assumed_fill_price": assumed_fill_price,
        "market_price": normalized_market_price,
        "gross_notional": gross_notional,
        "mark_notional": mark_notional,
        "fee_bps": normalized_fee_bps,
        "slippage_bps": normalized_slippage_bps,
        "fee_amount": fee_amount,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_percent": unrealized_pnl_percent,
        "recorded_at": now_iso,
        "notes": notes or "",
        "source": ["copilot_paper_trade_execution_service"],
    }

    records = _load_paper_trade_execution_records()
    records.append(record)
    saved_path = _save_paper_trade_execution_records(records, now_iso)
    if not saved_path:
        raise RuntimeError("Failed to persist paper trade execution record")

    return {
        "status": "recorded",
        "execution_id": execution_id,
        "decision_id": record["decision_id"],
        "ticker": record["ticker"],
        "side": record["side"],
        "recorded_at": now_iso,
        "fill_assumptions": {
            "reference_price": normalized_reference_price,
            "assumed_fill_price": assumed_fill_price,
            "fee_bps": normalized_fee_bps,
            "slippage_bps": normalized_slippage_bps,
            "fee_amount": fee_amount,
        },
        "position": {
            "quantity": normalized_quantity,
            "gross_notional": gross_notional,
            "mark_notional": mark_notional,
            "market_price": normalized_market_price,
        },
        "pnl": {
            "unrealized": unrealized_pnl,
            "unrealized_percent": unrealized_pnl_percent,
        },
        "store": {
            "storage_key": PAPER_TRADE_EXECUTION_RECORDS_STORAGE_KEY,
            "path": str(saved_path),
            "status": "persisted",
        },
        "source": ["copilot_paper_trade_execution_service"],
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
    feedback_records = _load_outcome_feedback_records()
    feedback_by_decision = _index_feedback_by_decision(feedback_records)
    execution_records = _load_paper_trade_execution_records()
    executions_by_decision = _index_records_by_decision(execution_records)
    
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

    limit_entries = sorted_entries[:limit]
    enriched_entries = []
    for entry in limit_entries:
        decision_id = str(entry.get("decision_id") or "").strip()
        entry_feedback = feedback_by_decision.get(decision_id, [])
        if entry_feedback:
            entry = dict(entry)
            entry["outcome_feedback"] = entry_feedback
        entry_executions = executions_by_decision.get(decision_id, [])
        if entry_executions:
            entry = dict(entry)
            entry["paper_trade_execution"] = {
                "schema_version": PAPER_TRADE_EXECUTION_SCHEMA_VERSION,
                "record_mode": "append_only",
                "count": len(entry_executions),
                "latest_recorded_at": entry_executions[0].get("recorded_at"),
                "execution_quality": _build_execution_quality_metrics(entry_executions),
                "records": entry_executions,
            }
        enriched_entries.append(entry)

    return {
        "schema_version": DECISION_JOURNAL_SCHEMA_VERSION,
        "count": len(all_entries),
        "filtered_count": len(filtered),
        "returned_count": len(limit_entries),
        "entries": enriched_entries,
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
    execution_records = _load_paper_trade_execution_records()
    
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
        "paper_trade_execution": _build_execution_quality_metrics(execution_records),
        "total_feedback_records": len(records),
        "total_paper_trade_records": len(execution_records),
        "freshness": now_iso,
        "source": ["copilot_outcome_feedback_service"],
    }


# Exports
__all__ = [
    "log_copilot_decision",
    "record_outcome_feedback",
    "execute_paper_trade",
    "get_decision_journal",
    "get_outcome_feedback",
    "compute_metrics",
    "DECISION_JOURNAL_STORAGE_KEY",
    "DECISION_OUTCOME_FEEDBACK_RECORDS_STORAGE_KEY",
    "PAPER_TRADE_EXECUTION_RECORDS_STORAGE_KEY",
    "FEEDBACK_HORIZONS",
]
