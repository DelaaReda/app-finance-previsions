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
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

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
    from platform.legacy.taxonomy.news_taxonomy import (  # type: ignore
        classify_event,
        tag_geopolitics,
    )
except Exception:  # pragma: no cover
    def classify_event(_text: str) -> List[str]:
        return []

    def tag_geopolitics(_text: str) -> List[str]:
        return []

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
JUDGE_POLICY_STORAGE_KEY = "judge_personal_policy"
JUDGE_POLICY_SCHEMA_VERSION = "judge_personal_policy_v1"
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


def _resolve_copilot_services():
    try:
        from importlib import import_module
    except Exception:  # pragma: no cover
        import_module = None  # type: ignore

    if import_module is None:
        return None, None

    try:
        copilot_service = import_module("domains.copilot.application.copilot_service")
    except Exception:
        try:
            copilot_service = import_module("services")
        except Exception:
            copilot_service = None

    try:
        context_service_module = import_module("domains.copilot.application.context_service")
        context_service_cls = getattr(context_service_module, "ContextService", None)
    except Exception:
        try:
            context_service_module = import_module("services.context_service")
            context_service_cls = getattr(context_service_module, "ContextService", None)
        except Exception:
            context_service_cls = None

    return copilot_service, context_service_cls


def _resolve_personal_finance_scope(
    *,
    scope: Optional[Dict[str, Any]],
    tickers: Optional[List[str]],
) -> Optional[Dict[str, List[str]]]:
    normalized_tickers = normalize_tickers(tickers or [])
    if scope is None:
        scope = None
    resolved_scope: Optional[Dict[str, List[str]]] = (
        dict(scope) if isinstance(scope, dict) else None
    )
    if normalized_tickers:
        if resolved_scope is None:
            resolved_scope = {"tickers": normalized_tickers}
        else:
            resolved_scope["tickers"] = normalized_tickers

    return resolved_scope


def _rewrite_personal_finance_start_targets(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload

    rewritten = dict(payload)
    target_map = {
        "/copilot": "/personal-finance",
        "copilot": "/personal-finance",
        "/copilot/": "/personal-finance",
        "copilot/": "/personal-finance",
        "/copilot/ask": "/personal-finance/ask",
        "copilot/ask": "/personal-finance/ask",
    }

    for key in ("ask", "open"):
        items = rewritten.get(key)
        if not isinstance(items, list):
            continue
        updated_items: List[Any] = []
        for item in items:
            if not isinstance(item, dict):
                updated_items.append(item)
                continue
            normalized_target = str(item.get("target") or "").strip().lower()
            if normalized_target.startswith("/copilot/") and normalized_target not in {"/copilot/ask"}:
                mapped_target = "/personal-finance"
            elif normalized_target.startswith("copilot/") and normalized_target not in {"copilot/ask"}:
                mapped_target = "/personal-finance"
            else:
                mapped_target = target_map.get(normalized_target)
            if mapped_target:
                updated_item = dict(item)
                updated_item["target"] = mapped_target
                updated_items.append(updated_item)
                continue
            updated_items.append(item)
        rewritten[key] = updated_items

    return rewritten


def _default_risk_levels() -> List[str]:
    return ["low", "medium", "high", "critical"]


def _judge_profiles_dir_candidates() -> List[Path]:
    api_root = Path(__file__).resolve().parents[4]
    candidates = [
        api_root / "runtime" / "data" / "judge_profiles",
        Path("data") / "judge_profiles",
    ]
    unique: List[Path] = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def _list_judge_profile_options() -> List[Dict[str, str]]:
    names: List[str] = []
    seen = set()
    for candidate_dir in _judge_profiles_dir_candidates():
        if not candidate_dir.is_dir():
            continue
        for profile_path in sorted(candidate_dir.glob("*.yaml")):
            profile_name = profile_path.stem.strip()
            if not profile_name:
                continue
            if profile_name in seen:
                continue
            seen.add(profile_name)
            names.append(profile_name)

    if "equity_1w" in names:
        names = ["equity_1w"] + [name for name in names if name != "equity_1w"]
    elif not names:
        names = ["equity_1w"]

    return [
        {
            "value": profile_name,
            "label": profile_name.replace("_", " ").title(),
        }
        for profile_name in names
    ]


def _risk_level_rank(level: Any) -> int:
    normalized = normalize_risk_level(level, default="medium")
    try:
        return _default_risk_levels().index(normalized)
    except ValueError:
        return _default_risk_levels().index("medium")


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


REBALANCE_DEFAULT_FEE_BPS = max(
    0.0,
    _coerce_float(os.getenv("JUDGE_REBALANCE_FEE_BPS"), 5.0),
)
REBALANCE_DEFAULT_SLIPPAGE_BPS = max(
    0.0,
    _coerce_float(os.getenv("JUDGE_REBALANCE_SLIPPAGE_BPS"), 10.0),
)
REBALANCE_SHORT_TERM_TAX_RATE = min(
    1.0,
    max(0.0, _coerce_float(os.getenv("JUDGE_REBALANCE_SHORT_TERM_TAX_RATE"), 0.30)),
)
REBALANCE_LONG_TERM_TAX_RATE = min(
    1.0,
    max(0.0, _coerce_float(os.getenv("JUDGE_REBALANCE_LONG_TERM_TAX_RATE"), 0.15)),
)


def _load_personal_policy() -> Dict[str, Any]:
    raw = load_json(JUDGE_POLICY_STORAGE_KEY)
    if not isinstance(raw, dict):
        return {}
    policy = dict(raw)
    if not policy.get("schema_version"):
        policy["schema_version"] = JUDGE_POLICY_SCHEMA_VERSION
    return policy


def _normalize_personal_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    excluded_tickers = [
        ticker
        for ticker in normalize_tickers(policy.get("excluded_tickers") or [])
        if ticker
    ]
    blocked_actions = []
    for value in policy.get("blocked_actions") or []:
        action = coerce_verdict(value, default="")
        if action in {"buy", "sell", "hold"} and action not in blocked_actions:
            blocked_actions.append(action)
    max_risk_level = normalize_risk_level(
        policy.get("max_risk_level"),
        default="critical",
    )
    return {
        "schema_version": str(policy.get("schema_version") or JUDGE_POLICY_SCHEMA_VERSION),
        "policy_id": str(policy.get("policy_id") or "default").strip() or "default",
        "policy_version": str(policy.get("policy_version") or "v1").strip() or "v1",
        "updated_at": str(policy.get("updated_at") or utc_now_iso()).strip() or utc_now_iso(),
        "excluded_tickers": excluded_tickers,
        "blocked_actions": blocked_actions,
        "max_risk_level": max_risk_level,
    }


def _apply_personal_policy_guardrails(
    data: Dict[str, Any],
    *,
    freshness: Optional[str],
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data
    verdicts = data.get("verdicts")
    if not isinstance(verdicts, list):
        return data

    policy = _normalize_personal_policy(_load_personal_policy())
    has_rules = bool(
        policy["excluded_tickers"]
        or policy["blocked_actions"]
        or policy["max_risk_level"] != "critical"
    )
    if not has_rules:
        return data

    evaluated_at = str(freshness or data.get("generated_at") or utc_now_iso()).strip() or utc_now_iso()
    blocked_tickers = set(policy["excluded_tickers"])
    blocked_actions = set(policy["blocked_actions"])
    max_risk_rank = _risk_level_rank(policy["max_risk_level"])
    downgraded_count = 0
    violation_count = 0

    for verdict in verdicts:
        if not isinstance(verdict, dict):
            continue
        ticker = normalize_ticker(verdict.get("ticker") or "") or "UNKNOWN"
        original_action = coerce_verdict(
            verdict.get("verdict") or verdict.get("action") or verdict.get("direction"),
            default="hold",
        )
        risk_level = normalize_risk_level(verdict.get("risk_level"), default="medium")
        violations: List[Dict[str, Any]] = []

        if ticker in blocked_tickers:
            violations.append(
                {
                    "code": "ticker_excluded",
                    "field": "ticker",
                    "message": f"{ticker} is excluded by personal policy.",
                }
            )
        if original_action in blocked_actions:
            violations.append(
                {
                    "code": "action_blocked",
                    "field": "action",
                    "message": f"{original_action} is blocked by personal policy.",
                }
            )
        if _risk_level_rank(risk_level) > max_risk_rank:
            violations.append(
                {
                    "code": "risk_above_limit",
                    "field": "risk_level",
                    "message": f"{risk_level} exceeds personal max risk {policy['max_risk_level']}.",
                }
            )

        effective_action = original_action
        status = "ok"
        if violations:
            violation_count += len(violations)
            status = "violated"
            if original_action in {"buy", "sell"}:
                effective_action = "hold"
                verdict["verdict"] = "hold"
                verdict["action"] = "hold"
                downgraded_count += 1
            warnings = verdict.get("warnings")
            if not isinstance(warnings, list):
                warnings = [] if warnings in (None, "") else [str(warnings)]
            if "policy_guardrail_violation" not in warnings:
                warnings.append("policy_guardrail_violation")
            verdict["warnings"] = warnings
            verdict["policy_override_reason"] = "; ".join(v["message"] for v in violations)

        verdict["policy_guardrails"] = {
            "schema_version": "judge_policy_guardrail_result_v1",
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
            "evaluated_at": evaluated_at,
            "status": status,
            "original_action": original_action,
            "effective_action": effective_action,
            "violations": violations,
        }

    data["policy_guardrails"] = {
        "schema_version": "judge_policy_guardrail_projection_v1",
        "evaluated_at": evaluated_at,
        "policy": policy,
        "summary": {
            "verdict_count": len([v for v in verdicts if isinstance(v, dict)]),
            "violations_count": violation_count,
            "downgraded_count": downgraded_count,
        },
    }
    append_source_tag(
        data,
        "judge_policy_guardrail_projection_v1",
        default_source="judge_endpoint_service",
    )
    if violation_count:
        warnings = data.get("warnings")
        if not isinstance(warnings, list):
            warnings = [] if warnings in (None, "") else [str(warnings)]
        if "policy_guardrail_violation" not in warnings:
            warnings.append("policy_guardrail_violation")
        data["warnings"] = warnings
    return data


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _as_freshness_hours(value: Any) -> Optional[float]:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return round(
        max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds()) / 3600.0,
        3,
    )


def _normalize_source_link(value: Any) -> Tuple[Optional[str], str]:
    url = str(value or "").strip()
    if not url:
        return None, "missing"
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url, "ok"
    return url, "invalid"


def _normalize_trace_source_items(verdict: Dict[str, Any]) -> List[Dict[str, Any]]:
    meta = verdict.get("meta") if isinstance(verdict.get("meta"), dict) else {}
    debug_payload = verdict.get("debug_payload") if isinstance(verdict.get("debug_payload"), dict) else {}
    attachments = verdict.get("attachments") if isinstance(verdict.get("attachments"), list) else []
    news_items = debug_payload.get("news") if isinstance(debug_payload.get("news"), list) else []
    source_tags = ensure_source_list(
        verdict.get("source") or meta.get("source"),
        default_source="judge_endpoint_service",
    )

    normalized: List[Dict[str, Any]] = []
    seen = set()

    for idx, tag in enumerate(source_tags):
        source_id = f"source_tag:{tag}"
        normalized.append(
            {
                "source_id": source_id,
                "label": tag,
                "kind": "source_tag",
                "weight": round(1.0 / max(1, len(source_tags)), 4),
                "quality_score": None,
                "freshness": {
                    "timestamp": None,
                    "age_hours": None,
                },
                "trace": {
                    "origin": "verdict.source",
                    "position": idx,
                },
            }
        )
        seen.add(source_id)

    for idx, item in enumerate(news_items):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("headline") or "").strip()
        if not title:
            continue
        source_name = str(item.get("source") or "news").strip() or "news"
        timestamp = item.get("ts") or item.get("timestamp") or item.get("published_at") or item.get("date")
        age_hours = item.get("age_hours")
        if age_hours is None:
            age_hours = _as_freshness_hours(timestamp)
        freshness_hours = _coerce_float(age_hours, default=24.0)
        sent_abs = abs(_coerce_float(item.get("sent"), default=0.0))
        weight = round(max(0.05, 1.0 / (1.0 + freshness_hours / 24.0) + sent_abs * 0.15), 4)
        quality_score = round(max(0.0, min(1.0, 1.0 / (1.0 + freshness_hours / 48.0) + sent_abs * 0.1)), 4)
        source_id = f"news:{sha1(f'{source_name}|{title}'.encode('utf-8')).hexdigest()[:12]}"
        source_url, link_status = _normalize_source_link(item.get("url") or item.get("link"))
        if source_id in seen:
            continue
        normalized.append(
            {
                "source_id": source_id,
                "label": title,
                "kind": "news_item",
                "weight": weight,
                "quality_score": quality_score,
                "freshness": {
                    "timestamp": timestamp,
                    "age_hours": freshness_hours if freshness_hours is not None else None,
                },
                "trace": {
                    "origin": "debug_payload.news",
                    "publisher": source_name,
                    "position": idx,
                },
                "url": source_url,
                "link_status": link_status,
            }
        )
        seen.add(source_id)

    for idx, item in enumerate(attachments):
        if not isinstance(item, dict):
            continue
        label = str(item.get("title") or item.get("label") or item.get("name") or item.get("type") or "").strip()
        if not label:
            continue
        source_id = f"attachment:{sha1(label.encode('utf-8')).hexdigest()[:12]}"
        if source_id in seen:
            continue
        quality_score = round(max(0.0, min(1.0, _coerce_float(item.get("confidence"), default=0.6))), 4)
        normalized.append(
            {
                "source_id": source_id,
                "label": label,
                "kind": "attachment",
                "weight": round(max(0.05, quality_score), 4),
                "quality_score": quality_score,
                "freshness": {
                    "timestamp": item.get("generated_at") or meta.get("generated_at"),
                    "age_hours": _as_freshness_hours(item.get("generated_at") or meta.get("generated_at")),
                },
                "trace": {
                    "origin": "verdict.attachments",
                    "position": idx,
                },
            }
        )
        seen.add(source_id)

    return normalized


def _build_explainability_graph(
    verdicts: List[Dict[str, Any]],
    *,
    freshness: Optional[str],
) -> Dict[str, Any]:
    generated_at = str(freshness or utc_now_iso()).strip() or utc_now_iso()
    graph_nodes: List[Dict[str, Any]] = []
    graph_edges: List[Dict[str, Any]] = []
    traceability: List[Dict[str, Any]] = []
    graph_stats = {
        "verdict_count": 0,
        "source_count": 0,
        "edge_count": 0,
        "stale_source_count": 0,
        "broken_source_count": 0,
        "avg_source_weight": 0.0,
    }
    source_node_ids = set()
    total_weight = 0.0
    weighted_source_count = 0

    for index, verdict in enumerate(verdicts):
        if not isinstance(verdict, dict):
            continue
        verdict_ticker = str(verdict.get("ticker") or f"VERDICT_{index + 1}").strip().upper() or f"VERDICT_{index + 1}"
        verdict_id = str(verdict.get("decision_id") or f"verdict:{verdict_ticker}:{index}").strip()
        verdict_weight = round(max(0.0, min(1.0, _coerce_float(verdict.get("confidence"), default=0.0))), 4)
        graph_nodes.append(
            {
                "id": verdict_id,
                "label": verdict_ticker,
                "kind": "verdict",
                "ticker": verdict_ticker,
                "weight": verdict_weight,
                "freshness": {
                    "timestamp": verdict.get("generated_at") or freshness,
                    "age_hours": _as_freshness_hours(verdict.get("generated_at") or freshness),
                },
            }
        )
        graph_stats["verdict_count"] += 1

        sources = _normalize_trace_source_items(verdict)
        supporting_sources: List[Dict[str, Any]] = []
        for source in sources:
            source_id = str(source.get("source_id") or "").strip()
            if not source_id:
                continue
            node_id = f"source:{source_id}"
            freshness_meta = source.get("freshness") if isinstance(source.get("freshness"), dict) else {}
            age_hours = freshness_meta.get("age_hours")
            age_hours_value = _coerce_float(age_hours, default=-1.0)
            if node_id not in source_node_ids:
                graph_nodes.append(
                    {
                        "id": node_id,
                        "label": source.get("label"),
                        "kind": source.get("kind"),
                        "weight": source.get("weight"),
                        "quality_score": source.get("quality_score"),
                        "freshness": freshness_meta,
                    }
                )
                source_node_ids.add(node_id)
                graph_stats["source_count"] += 1
            edge_weight = round(max(0.0, min(1.0, _coerce_float(source.get("weight"), default=0.0))), 4)
            graph_edges.append(
                {
                    "from": node_id,
                    "to": verdict_id,
                    "relationship": "supports",
                    "weight": edge_weight,
                    "trace": source.get("trace") or {},
                }
            )
            total_weight += edge_weight
            weighted_source_count += 1
            if age_hours_value >= 72.0:
                graph_stats["stale_source_count"] += 1
            if source.get("link_status") == "invalid":
                graph_stats["broken_source_count"] += 1
            supporting_sources.append(
                {
                    "source_id": source_id,
                    "label": source.get("label"),
                    "kind": source.get("kind"),
                    "weight": edge_weight,
                    "quality_score": source.get("quality_score"),
                    "freshness": freshness_meta,
                    "trace": source.get("trace") or {},
                    "url": source.get("url"),
                    "link_status": source.get("link_status") or "missing",
                }
            )

        traceability.append(
            {
                "verdict_id": verdict_id,
                "ticker": verdict_ticker,
                "supporting_sources": supporting_sources,
                "primary_source_count": len(supporting_sources),
                "freshness": {
                    "generated_at": verdict.get("generated_at") or freshness or generated_at,
                    "age_hours": _as_freshness_hours(verdict.get("generated_at") or freshness or generated_at),
                },
            }
        )

    graph_stats["edge_count"] = len(graph_edges)
    if weighted_source_count:
        graph_stats["avg_source_weight"] = round(total_weight / weighted_source_count, 4)

    return {
        "schema_version": "judge_explainability_graph_v1",
        "generated_at": generated_at,
        "graph": {
            "nodes": graph_nodes,
            "edges": graph_edges,
        },
        "source_traceability": traceability,
        "stats": graph_stats,
    }


def _article_geopolitical_tags(article: Dict[str, Any]) -> List[str]:
    seeded = _coerce_text_list(article.get("geopolitics"), article.get("regions"))
    if seeded:
        return seeded
    text = " ".join(
        str(article.get(field) or "").strip()
        for field in ("title", "headline", "summary", "description", "raw_text")
    ).strip()
    return _coerce_text_list(tag_geopolitics(text))


def _article_event_tags(article: Dict[str, Any]) -> List[str]:
    seeded = _coerce_text_list(article.get("event_types"), article.get("events"))
    if seeded:
        return seeded
    text = " ".join(
        str(article.get(field) or "").strip()
        for field in ("title", "headline", "summary", "description", "raw_text")
    ).strip()
    return _coerce_text_list(classify_event(text))


def _compute_escalation_score(*, article_count: int, event_count: int, recent_count: int) -> float:
    raw = min(1.0, (article_count * 0.18) + (event_count * 0.12) + (recent_count * 0.22))
    return round(raw, 4)


def _escalation_band(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


_EVENT_HORIZON_MATRIX_PRIORS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "earnings": {
        "1d": {"impact_score": 0.92, "bias": "volatile", "template": "Earnings shocks usually dominate the next session before guidance clarity settles."},
        "1w": {"impact_score": 0.68, "bias": "directional", "template": "One-week impact usually reflects guidance digestion and estimate revisions."},
        "1m": {"impact_score": 0.41, "bias": "mean_reverting", "template": "One-month impact usually fades unless the earnings release changes the medium-term thesis."},
    },
    "sanctions": {
        "1d": {"impact_score": 0.59, "bias": "risk_off", "template": "Sanctions headlines create immediate repricing, especially in exposed supply chains."},
        "1w": {"impact_score": 0.77, "bias": "persistent", "template": "One-week impact often grows while counterparties reprice logistics and compliance risk."},
        "1m": {"impact_score": 0.82, "bias": "persistent", "template": "One-month impact stays elevated when sanctions alter capital flows or trade routes."},
    },
    "export_controls": {
        "1d": {"impact_score": 0.54, "bias": "risk_off", "template": "Export-control headlines hit exposed names quickly, but first-day moves can be noisy."},
        "1w": {"impact_score": 0.74, "bias": "persistent", "template": "One-week impact usually expands as supplier and customer dependencies are repriced."},
        "1m": {"impact_score": 0.79, "bias": "persistent", "template": "One-month impact remains elevated when restrictions force a durable supply-chain reset."},
    },
    "guidance": {
        "1d": {"impact_score": 0.81, "bias": "directional", "template": "Guidance changes tend to re-anchor expectations immediately."},
        "1w": {"impact_score": 0.71, "bias": "directional", "template": "One-week impact persists while analysts and positioning catch up."},
        "1m": {"impact_score": 0.56, "bias": "persistent", "template": "One-month impact holds when guidance implies a genuine trend change."},
    },
    "merger": {
        "1d": {"impact_score": 0.88, "bias": "event_locked", "template": "M&A headlines usually gap on day one as spread traders set the first price."},
        "1w": {"impact_score": 0.63, "bias": "deal_spread", "template": "One-week impact depends on deal certainty, financing, and regulatory read-through."},
        "1m": {"impact_score": 0.52, "bias": "deal_spread", "template": "One-month impact compresses unless the event changes long-run industry structure."},
    },
    "general_tension": {
        "1d": {"impact_score": 0.42, "bias": "risk_off", "template": "General tensions usually create a modest immediate risk-off response."},
        "1w": {"impact_score": 0.58, "bias": "persistent", "template": "One-week impact depends on whether tensions escalate into policy or supply disruption."},
        "1m": {"impact_score": 0.49, "bias": "uncertain", "template": "One-month impact often fades unless the tension becomes a concrete economic constraint."},
    },
}
_EVENT_HORIZON_KEYS: Tuple[str, ...] = ("1d", "1w", "1m")


def _impact_band(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    if score >= 0.3:
        return "low"
    return "minimal"


def _resolve_event_horizon_prior(event_tag: str) -> Dict[str, Dict[str, Any]]:
    normalized = str(event_tag or "").strip().lower() or "general_tension"
    return _EVENT_HORIZON_MATRIX_PRIORS.get(
        normalized,
        _EVENT_HORIZON_MATRIX_PRIORS["general_tension"],
    )


def _build_event_horizon_interpretation(
    *,
    event_type: str,
    horizons: Dict[str, Dict[str, Any]],
    divergence: float,
) -> Dict[str, Any]:
    dominant_horizon = max(
        _EVENT_HORIZON_KEYS,
        key=lambda horizon_key: float(horizons[horizon_key]["impact_score"]),
    )
    shortest_score = float(horizons["1d"]["impact_score"])
    longest_score = float(horizons["1m"]["impact_score"])
    if divergence >= 0.2:
        outlook = "Immediate repricing and slower confirmation are diverging."
    elif longest_score > shortest_score:
        outlook = "The setup looks more durable than the day-one reaction."
    elif shortest_score > longest_score:
        outlook = "The move looks front-loaded and may fade over longer horizons."
    else:
        outlook = "The event path stays aligned across short and longer horizons."

    band = horizons[dominant_horizon]["impact_band"]
    bias = str(horizons[dominant_horizon]["bias"] or "").replace("_", " ").strip()
    summary = (
        f"{str(event_type or 'event').replace('_', ' ')} has its strongest "
        f"{dominant_horizon} signal with {band} conviction and a {bias or 'neutral'} bias. {outlook}"
    )
    return {
        "dominant_horizon": dominant_horizon,
        "summary": summary.strip(),
    }


def _build_event_horizon_alert(
    *,
    row: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    dominant_horizon = str(row.get("dominant_horizon") or "").strip() or "1w"
    horizons = row.get("horizons") if isinstance(row.get("horizons"), dict) else {}
    dominant_snapshot = (
        horizons.get(dominant_horizon)
        if isinstance(horizons.get(dominant_horizon), dict)
        else {}
    )
    impact_score = _coerce_float(dominant_snapshot.get("impact_score"), 0.0)
    recent_count = safe_int(row.get("recent_count"), 0)
    article_count = safe_int(row.get("article_count"), 0)
    divergence = _coerce_float(row.get("cross_horizon_divergence"), 0.0)
    sentiment_bias = _coerce_float(row.get("sentiment_bias"), 0.0)
    if recent_count <= 0:
        return None

    urgency = None
    if impact_score >= 0.75 or divergence >= 0.2:
        urgency = "high"
    elif impact_score >= 0.6 or article_count >= 2:
        urgency = "elevated"
    if urgency is None:
        return None

    if divergence >= 0.2:
        recommended_action = (
            "Validate whether the short-term shock is becoming a durable thesis change before resizing exposure."
        )
    elif dominant_horizon == "1d":
        recommended_action = (
            "Monitor immediate repricing and tighten near-term risk limits while the event digests."
        )
    elif dominant_horizon == "1w":
        recommended_action = (
            "Review one-week exposure for follow-through while the signal remains elevated."
        )
    else:
        recommended_action = (
            "Reassess medium-term positioning if the signal persists beyond the initial headline reaction."
        )
    if sentiment_bias <= -0.2 and "downside hedges" not in recommended_action.lower():
        recommended_action = (
            f"{recommended_action.rstrip('.')} Keep downside hedges live while sentiment stays risk-off."
        )

    sample_headlines = row.get("sample_headlines") if isinstance(row.get("sample_headlines"), list) else []
    sample_headline = str(sample_headlines[0]).strip() if sample_headlines else None
    if not sample_headline:
        sample_headline = None

    return {
        "event_type": str(row.get("event_type") or "").strip() or "general_tension",
        "urgency": urgency,
        "impact_band": str(dominant_snapshot.get("impact_band") or "low"),
        "impact_score": round(impact_score, 4),
        "dominant_horizon": dominant_horizon,
        "cross_horizon_divergence": round(divergence, 4),
        "article_count": article_count,
        "recent_count": recent_count,
        "sentiment_bias": round(sentiment_bias, 4),
        "timestamp": row.get("latest_at"),
        "interpretation": str(row.get("interpretation") or "").strip() or None,
        "recommended_action": recommended_action,
        "sample_headline": sample_headline,
    }


def _build_event_impact_horizon_matrix_payload(
    *,
    event_type: Optional[str],
    limit: int,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    event_filter = str(event_type or "").strip().lower()
    articles_payload = load_json("news_feed") or {}
    articles = articles_payload.get("articles") if isinstance(articles_payload, dict) else []
    articles = articles if isinstance(articles, list) else []

    warnings: List[str] = []
    matrix_state: Dict[str, Dict[str, Any]] = {}

    for article in articles:
        if not isinstance(article, dict):
            continue
        event_tags = _article_event_tags(article) or ["general_tension"]
        if event_filter and event_filter not in {tag.lower() for tag in event_tags}:
            continue

        published_at = _parse_datetime(
            article.get("published_at")
            or article.get("timestamp")
            or article.get("ts")
            or article.get("date")
        )
        recency_multiplier = 0.7
        if published_at is None:
            warnings.append("missing_article_timestamp")
        else:
            age_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
            recency_multiplier = 1.0 if age_hours <= 24 else 0.85 if age_hours <= 72 else 0.65

        raw_sentiment = article.get("sentiment_score") or article.get("sent") or article.get("sentiment")
        try:
            sentiment_value = float(raw_sentiment)
        except Exception:
            sentiment_value = 0.0

        headline = str(article.get("title") or article.get("headline") or "").strip()
        for tag in event_tags:
            normalized_tag = str(tag or "").strip().lower() or "general_tension"
            state = matrix_state.setdefault(
                normalized_tag,
                {
                    "event_type": normalized_tag,
                    "article_count": 0,
                    "recent_count": 0,
                    "sentiment_sum": 0.0,
                    "latest_at": None,
                    "sample_headlines": [],
                },
            )
            state["article_count"] += 1
            state["sentiment_sum"] += sentiment_value
            if recency_multiplier >= 0.85:
                state["recent_count"] += 1
            if isinstance(published_at, datetime):
                latest_at = state.get("latest_at")
                if latest_at is None or published_at > latest_at:
                    state["latest_at"] = published_at
            if headline and len(state["sample_headlines"]) < 3:
                state["sample_headlines"].append(headline)

    matrix: List[Dict[str, Any]] = []
    for event_key, state in matrix_state.items():
        priors = _resolve_event_horizon_prior(event_key)
        avg_sentiment = state["sentiment_sum"] / state["article_count"] if state["article_count"] else 0.0
        sentiment_bias = round(max(-1.0, min(1.0, avg_sentiment)), 4)
        horizons: Dict[str, Dict[str, Any]] = {}
        impact_curve: List[float] = []
        for horizon_key in _EVENT_HORIZON_KEYS:
            prior = priors[horizon_key]
            article_multiplier = min(1.35, 0.85 + (state["article_count"] * 0.08))
            recent_multiplier = 1.0 if state["recent_count"] else 0.82
            sentiment_multiplier = 1.0 + (min(abs(sentiment_bias), 0.6) * 0.15)
            score = min(
                1.0,
                float(prior["impact_score"]) * article_multiplier * recent_multiplier * sentiment_multiplier,
            )
            score = round(score, 4)
            impact_curve.append(score)
            horizons[horizon_key] = {
                "impact_score": score,
                "impact_band": _impact_band(score),
                "bias": prior["bias"],
                "template": prior["template"],
            }

        divergence = round(max(impact_curve) - min(impact_curve), 4) if impact_curve else 0.0
        interpretation = _build_event_horizon_interpretation(
            event_type=event_key,
            horizons=horizons,
            divergence=divergence,
        )
        matrix.append(
            {
                "event_type": event_key,
                "article_count": state["article_count"],
                "recent_count": state["recent_count"],
                "sentiment_bias": sentiment_bias,
                "cross_horizon_divergence": divergence,
                "dominant_horizon": interpretation["dominant_horizon"],
                "interpretation": interpretation["summary"],
                "latest_at": (
                    state["latest_at"].isoformat()
                    if isinstance(state.get("latest_at"), datetime)
                    else None
                ),
                "horizons": horizons,
                "sample_headlines": state["sample_headlines"],
            }
        )

    matrix.sort(
        key=lambda item: (
            -float(item["horizons"]["1w"]["impact_score"]),
            -int(item["article_count"]),
            str(item["event_type"]),
        )
    )
    matrix = matrix[:limit]

    alerts = [
        alert
        for alert in (
            _build_event_horizon_alert(row=row)
            for row in matrix
        )
        if alert is not None
    ]
    alerts.sort(
        key=lambda item: (
            0 if item["urgency"] == "high" else 1,
            -float(item["impact_score"]),
            str(item["event_type"]),
        )
    )

    dominant_template = (
        "Cross-horizon divergence is highest when the event creates immediate repricing but slower fundamental confirmation."
        if any(float(row["cross_horizon_divergence"]) >= 0.2 for row in matrix)
        else "Cross-horizon impact stays relatively aligned when the event path is already well understood."
    )

    dedup_warnings: List[str] = []
    seen_warnings = set()
    for warning in warnings:
        if warning in seen_warnings:
            continue
        seen_warnings.add(warning)
        dedup_warnings.append(warning)

    source = ["judge_event_impact_horizon_matrix_service", "news_feed_snapshot"]
    if not articles:
        source.append("news_feed_fallback")

    return {
        "generated_at": now_iso,
        "freshness": now_iso,
        "source": source,
        "filters_applied": {
            "event_type": event_filter or None,
            "limit": limit,
        },
        "stats": {
            "article_count": len(articles),
            "event_types_returned": len(matrix),
            "alerts_count": len(alerts),
            "horizons": list(_EVENT_HORIZON_KEYS),
        },
        "matrix": matrix,
        "alerts": alerts,
        "templates": {
            "cross_horizon_divergence": dominant_template,
        },
        "warnings": dedup_warnings,
    }


def _build_geopolitical_graph_payload(*, region: Optional[str], limit: int) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    articles_payload = load_json("news_feed") or {}
    articles = articles_payload.get("articles") if isinstance(articles_payload, dict) else []
    articles = articles if isinstance(articles, list) else []
    region_filter = str(region or "").strip().lower()

    regions: Dict[str, Dict[str, Any]] = {}
    event_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    warnings: List[str] = []

    def _trace_article(
        *,
        article: Dict[str, Any],
        published_at: Optional[datetime],
        region_tag: str,
        event_tag: Optional[str],
    ) -> Dict[str, Any]:
        freshness_hours = None
        if isinstance(published_at, datetime):
            freshness_hours = round(max(0.0, (now - published_at).total_seconds() / 3600.0), 2)
        return {
            "title": str(article.get("title") or article.get("headline") or "").strip() or "untitled",
            "publisher": str(article.get("source") or article.get("publisher") or "unknown").strip() or "unknown",
            "published_at": published_at.isoformat() if isinstance(published_at, datetime) else None,
            "freshness_hours": freshness_hours,
            "region": region_tag,
            "event": event_tag,
            "url": str(article.get("url") or article.get("link") or "").strip() or None,
            "weight": 1.0 if freshness_hours is None else round(max(0.1, 1.0 - min(freshness_hours, 72.0) / 72.0), 3),
        }

    for article in articles:
        if not isinstance(article, dict):
            continue
        geo_tags = _article_geopolitical_tags(article)
        if not geo_tags:
            continue
        if region_filter and region_filter not in {tag.lower() for tag in geo_tags}:
            continue

        event_tags = _article_event_tags(article)
        published_at = _parse_datetime(
            article.get("published_at")
            or article.get("timestamp")
            or article.get("ts")
            or article.get("date")
        )
        is_recent = False
        if published_at is None:
            warnings.append("missing_article_timestamp")
        else:
            is_recent = (now - published_at) <= timedelta(hours=24)
        article_title = str(article.get("title") or article.get("headline") or "").strip()

        for geo_tag in geo_tags:
            key = geo_tag.lower()
            region_state = regions.setdefault(
                key,
                {
                    "id": key,
                    "label": geo_tag,
                    "article_count": 0,
                    "recent_count": 0,
                    "event_count": 0,
                    "latest_at": None,
                    "sample_headlines": [],
                    "source_trace": [],
                },
            )
            region_state["article_count"] += 1
            region_state["event_count"] += len(event_tags)
            if is_recent:
                region_state["recent_count"] += 1
            if article_title and len(region_state["sample_headlines"]) < 3:
                region_state["sample_headlines"].append(article_title)
            if published_at is not None:
                latest_at = region_state.get("latest_at")
                if latest_at is None or published_at > latest_at:
                    region_state["latest_at"] = published_at
            if len(region_state["source_trace"]) < 3:
                region_state["source_trace"].append(
                    _trace_article(
                        article=article,
                        published_at=published_at,
                        region_tag=geo_tag,
                        event_tag=None,
                    )
                )

            for event_tag in event_tags or ["general_tension"]:
                pair_key = (key, str(event_tag).strip().lower())
                pair_state = event_pairs.setdefault(
                    pair_key,
                    {
                        "source": key,
                        "target": str(event_tag).strip().lower(),
                        "article_count": 0,
                        "recent_count": 0,
                        "source_trace": [],
                    },
                )
                pair_state["article_count"] += 1
                if is_recent:
                    pair_state["recent_count"] += 1
                if len(pair_state["source_trace"]) < 3:
                    pair_state["source_trace"].append(
                        _trace_article(
                            article=article,
                            published_at=published_at,
                            region_tag=geo_tag,
                            event_tag=str(event_tag).strip().lower(),
                        )
                    )

    nodes = []
    alerts_by_region: Dict[str, Dict[str, Any]] = {}
    for state in regions.values():
        escalation_score = _compute_escalation_score(
            article_count=state["article_count"],
            event_count=state["event_count"],
            recent_count=state["recent_count"],
        )
        latest_at = state["latest_at"]
        node = {
            "id": state["id"],
            "label": state["label"],
            "kind": "region",
            "article_count": state["article_count"],
            "recent_count": state["recent_count"],
            "event_count": state["event_count"],
            "escalation_score": escalation_score,
            "escalation_band": _escalation_band(escalation_score),
            "latest_at": latest_at.isoformat() if isinstance(latest_at, datetime) else None,
            "sample_headlines": state["sample_headlines"],
            "source_trace": state["source_trace"],
        }
        nodes.append(node)
        if node["escalation_band"] in {"high", "critical"}:
            alerts_by_region[node["id"]] = {
                "region": node["label"],
                "escalation_band": node["escalation_band"],
                "escalation_score": node["escalation_score"],
                "timestamp": node["latest_at"] or now_iso,
            }

    nodes.sort(key=lambda item: (-float(item["escalation_score"]), str(item["label"])))
    nodes = nodes[:limit]
    allowed_ids = {node["id"] for node in nodes}
    alerts = [alerts_by_region[node_id] for node_id in allowed_ids if node_id in alerts_by_region]
    alerts.sort(key=lambda item: (-float(item["escalation_score"]), str(item["region"])))

    edges = [
        {
            "source": pair["source"],
            "target": pair["target"],
            "kind": "region_to_event",
            "weight": pair["article_count"],
            "recent_weight": pair["recent_count"],
            "source_trace": pair["source_trace"],
        }
        for pair in event_pairs.values()
        if pair["source"] in allowed_ids
    ]
    edges.sort(key=lambda item: (-int(item["weight"]), item["source"], item["target"]))

    dedup_warnings = []
    seen_warnings = set()
    for warning in warnings:
        if warning in seen_warnings:
            continue
        seen_warnings.add(warning)
        dedup_warnings.append(warning)

    source = ["judge_geopolitical_risk_graph_service", "news_feed_snapshot"]
    if not articles:
        source.append("news_feed_fallback")

    return {
        "generated_at": now_iso,
        "freshness": now_iso,
        "source": source,
        "filters_applied": {
            "region": region_filter or None,
            "limit": limit,
        },
        "stats": {
            "article_count": len(articles),
            "regions_detected": len(regions),
            "edges_returned": len(edges),
            "alerts_count": len(alerts),
        },
        "traceability": {
            "schema_version": "judge_source_trace_v1",
            "weighted_by": "freshness_decay",
            "freshness_unit": "hours",
            "source_trace_count": sum(len(node.get("source_trace") or []) for node in nodes),
        },
        "nodes": nodes,
        "edges": edges,
        "alerts": alerts,
        "warnings": dedup_warnings,
    }


def _extract_saved_portfolio_context(verdict: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(verdict, dict):
        return {}

    direct_context = verdict.get("portfolio_context")
    if isinstance(direct_context, dict):
        return direct_context

    meta = verdict.get("meta") if isinstance(verdict.get("meta"), dict) else {}
    if isinstance(meta.get("portfolio_context"), dict):
        return meta.get("portfolio_context") or {}

    debug_payload = (
        verdict.get("debug_payload")
        if isinstance(verdict.get("debug_payload"), dict)
        else {}
    )
    features = (
        debug_payload.get("features")
        if isinstance(debug_payload.get("features"), dict)
        else {}
    )
    if isinstance(features.get("portfolio_context"), dict):
        return features.get("portfolio_context") or {}

    debug_meta = (
        debug_payload.get("meta")
        if isinstance(debug_payload.get("meta"), dict)
        else {}
    )
    if isinstance(debug_meta.get("portfolio_context"), dict):
        return debug_meta.get("portfolio_context") or {}

    return {}


def _normalize_portfolio_weights(raw_weights: Any) -> Dict[str, float]:
    if not isinstance(raw_weights, dict):
        return {}

    normalized: Dict[str, float] = {}
    numeric_values: List[float] = []
    for raw_symbol, raw_weight in raw_weights.items():
        symbol = normalize_ticker(raw_symbol or "")
        if not symbol:
            continue
        try:
            weight = float(raw_weight)
        except Exception:
            continue
        if weight < 0:
            continue
        normalized[symbol] = weight
        numeric_values.append(weight)

    if not normalized:
        return {}

    scale = 100.0 if sum(numeric_values) <= 1.5 else 1.0
    return {
        symbol: round(weight * scale, 2)
        for symbol, weight in normalized.items()
    }


def _estimate_rebalance_turnover(weights: Dict[str, float]) -> float:
    if len(weights) < 2:
        return 0.0
    total_weight = sum(
        weight
        for weight in weights.values()
        if isinstance(weight, (int, float))
    )
    if total_weight <= 0:
        return 0.0
    target_weight = total_weight / len(weights)
    turnover = sum(abs(float(weight) - target_weight) for weight in weights.values()) / 2.0
    return round(turnover, 2)


def _estimate_rebalance_risk_delta(
    *,
    portfolio_context: Dict[str, Any],
    proposed_risk_level: str,
) -> int:
    current_risk_level = str(portfolio_context.get("risk_level") or "").strip().lower()
    if current_risk_level not in {"low", "medium", "high", "critical"}:
        return 0
    return _risk_level_rank(proposed_risk_level) - _risk_level_rank(current_risk_level)


def _estimate_rebalance_cost_awareness(
    *,
    turnover_pct: float,
    expected_return_pct: float,
    horizon: str,
) -> Dict[str, Any]:
    normalized_turnover_pct = max(0.0, _coerce_float(turnover_pct, 0.0))
    normalized_expected_return_pct = _coerce_float(expected_return_pct, 0.0)
    normalized_horizon = str(horizon or "").strip().lower()
    tax_bucket = "short_term" if normalized_horizon in {"1d", "1w", "1m", "3m"} else "long_term"
    tax_rate = (
        REBALANCE_SHORT_TERM_TAX_RATE
        if tax_bucket == "short_term"
        else REBALANCE_LONG_TERM_TAX_RATE
    )

    turnover_ratio = normalized_turnover_pct / 100.0
    trading_cost_pct = turnover_ratio * (
        (REBALANCE_DEFAULT_FEE_BPS + REBALANCE_DEFAULT_SLIPPAGE_BPS) / 10_000.0
    )
    estimated_tax_drag_pct = max(0.0, turnover_ratio * normalized_expected_return_pct * tax_rate)
    total_cost_pct = trading_cost_pct + estimated_tax_drag_pct
    net_expected_return_pct = normalized_expected_return_pct - total_cost_pct

    return {
        "turnover_pct": round(normalized_turnover_pct, 2),
        "gross_expected_return_pct": round(normalized_expected_return_pct, 6),
        "net_expected_return_pct": round(net_expected_return_pct, 6),
        "trading_cost_pct": round(trading_cost_pct, 6),
        "estimated_tax_drag_pct": round(estimated_tax_drag_pct, 6),
        "total_cost_pct": round(total_cost_pct, 6),
        "fee_bps": round(REBALANCE_DEFAULT_FEE_BPS, 2),
        "slippage_bps": round(REBALANCE_DEFAULT_SLIPPAGE_BPS, 2),
        "tax_rate_assumption": round(tax_rate, 4),
        "tax_bucket": tax_bucket,
        "trading_cost_bps": round(trading_cost_pct * 10_000.0, 1),
        "estimated_tax_drag_bps": round(estimated_tax_drag_pct * 10_000.0, 1),
        "total_cost_bps": round(total_cost_pct * 10_000.0, 1),
    }


def _build_strategy_playbook(verdict: Dict[str, Any], *, profile: str) -> Dict[str, Any]:
    """Project a Judge verdict into a minimal strategy playbook payload."""
    ticker = normalize_ticker(str(verdict.get("ticker") or "").strip()) or "UNKNOWN"
    policy_guardrails = (
        verdict.get("policy_guardrails")
        if isinstance(verdict.get("policy_guardrails"), dict)
        else {}
    )

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

    portfolio_context = _extract_saved_portfolio_context(verdict)
    portfolio_weights = _normalize_portfolio_weights(portfolio_context.get("weights"))
    turnover = _estimate_rebalance_turnover(portfolio_weights)
    expected_return = _coerce_float(verdict.get("expected_return"), 0.0)
    confidence = _coerce_float(verdict.get("confidence"), 0.0)
    risk_level = str(verdict.get("risk_level") or "medium").strip().lower()
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = "medium"
    horizon = str(verdict.get("horizon") or "1w").strip() or "1w"
    reasons = _coerce_text_list((go_no_go or {}).get("reasons", [])) if isinstance(go_no_go, dict) else []
    raw_impacts = verdict.get("impacts") if isinstance(verdict.get("impacts"), dict) else {}
    scenarios = verdict.get("scenarios") if isinstance(verdict.get("scenarios"), list) else []
    risks = verdict.get("risks") if isinstance(verdict.get("risks"), list) else []
    forecast_fusion = verdict.get("forecast_fusion") if isinstance(verdict.get("forecast_fusion"), dict) else None

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

    guardrail_status = str(policy_guardrails.get("status") or "").strip().lower()
    effective_action = coerce_verdict(
        policy_guardrails.get("effective_action"),
        default="",
    )
    if guardrail_status == "violated":
        conflicts.append("policy_guardrail_violation")
        if effective_action in {"hold"}:
            decision = "hold"
        elif effective_action in {"sell"}:
            decision = "no_go"

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

    playbook_id = f"{ticker}:{horizon}:{decision}:{profile}"

    return {
        "playbook_id": playbook_id,
        "ticker": ticker,
        "horizon": horizon,
        "profile": profile,
        "decision": decision,
        "confidence": round(confidence, 4),
        "expected_return": round(expected_return, 6),
        "risk_level": risk_level,
        "turnover": turnover,
        "risk_delta": _estimate_rebalance_risk_delta(
            portfolio_context=portfolio_context,
            proposed_risk_level=risk_level,
        ),
        "cost_awareness": _estimate_rebalance_cost_awareness(
            turnover_pct=turnover,
            expected_return_pct=expected_return,
            horizon=horizon,
        ),
        "summary": _coerce_text_list(summary)[:2],
        "recommended_actions": _coerce_text_list(verdict.get("actions") or []),
        "data_needed": _coerce_text_list(verdict.get("data_needed") or []),
        "evidence": {
            "scenario_count": len(scenarios),
            "risk_count": len(risks),
            "impact_keys": sorted(raw_impacts.keys()),
        },
        "forecast_fusion": forecast_fusion,
        "reasons": reasons,
        "conflicts": normalized_conflicts,
        "decision_id": verdict.get("decision_id"),
        "policy_guardrails": {
            "status": guardrail_status or "ok",
            "policy_id": policy_guardrails.get("policy_id"),
            "policy_version": policy_guardrails.get("policy_version"),
            "effective_action": effective_action or None,
            "violation_count": len(
                [
                    violation
                    for violation in policy_guardrails.get("violations", [])
                    if isinstance(violation, dict)
                ]
            ),
        },
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
        existing_entries_raw = (
            existing_payload.get("entries") if isinstance(existing_payload, dict) else []
        )
        if not isinstance(existing_entries_raw, list):
            existing_entries_raw = []
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
    if isinstance(verdicts, list):
        for verdict in verdicts:
            if not isinstance(verdict, dict):
                continue
            why_items = verdict.get("why")
            normalized_why: List[str] = []
            if isinstance(why_items, list):
                normalized_why = [
                    str(item).strip()
                    for item in why_items
                    if str(item).strip()
                ]
            elif str(why_items or "").strip():
                normalized_why = [str(why_items).strip()]

            if not normalized_why:
                reasoning = verdict.get("reasoning")
                if isinstance(reasoning, list):
                    normalized_why.extend(
                        str(item).strip()
                        for item in reasoning
                        if str(item).strip()
                    )
                elif str(reasoning or "").strip():
                    normalized_why.append(str(reasoning).strip())

            if not normalized_why:
                go_no_go = verdict.get("go_no_go")
                if isinstance(go_no_go, dict):
                    reasons = go_no_go.get("reasons")
                    if isinstance(reasons, list):
                        reason_line = ", ".join(
                            str(item).strip()
                            for item in reasons
                            if str(item).strip()
                        )
                        if reason_line:
                            normalized_why.append(f"Gate assessment: {reason_line}.")

            if not normalized_why:
                expected_return = verdict.get("expected_return")
                try:
                    expected_return_value = float(expected_return)
                except (TypeError, ValueError):
                    expected_return_value = None
                if expected_return_value is not None:
                    normalized_why.append(
                        f"Expected return over horizon: {expected_return_value * 100.0:.2f}%."
                    )

            risk_level = str(
                verdict.get("risk_level")
                or (verdict.get("risk") or {}).get("level")
                or ""
            ).strip()
            if risk_level and all(
                risk_level.lower() not in item.lower() for item in normalized_why
            ):
                normalized_why.append(f"Risk level assessed as {risk_level}.")

            if not normalized_why:
                normalized_why = [
                    "Decision derived from judge forecast, policy guardrails, and available market context."
                ]

            verdict["why"] = normalized_why[:3]
            if not verdict.get("reasoning"):
                verdict["reasoning"] = list(verdict["why"])

    _apply_personal_policy_guardrails(
        data,
        freshness=response.get("freshness") or data.get("generated_at"),
    )
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
    if isinstance(verdicts, list):
        data["explainability"] = _build_explainability_graph(
            [entry for entry in verdicts if isinstance(entry, dict)],
            freshness=response.get("freshness") or data.get("generated_at"),
        )
        append_source_tag(
            data,
            "judge_explainability_graph_v1",
            default_source="judge_endpoint_service",
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _build_sector_company_transmission_row(verdict: Dict[str, Any]) -> Dict[str, Any]:
    ticker = normalize_ticker(verdict.get("ticker") or "")
    fundamentals = verdict.get("fundamentals") if isinstance(verdict.get("fundamentals"), dict) else {}
    meta = verdict.get("meta") if isinstance(verdict.get("meta"), dict) else {}
    sector = str(
        verdict.get("sector")
        or fundamentals.get("sector")
        or meta.get("sector")
        or "unknown"
    ).strip() or "unknown"
    confidence_before = coerce_confidence(verdict.get("confidence"), default=0.0)
    expected_return = _safe_float(verdict.get("expected_return"), 0.0)
    impacts = verdict.get("impacts") if isinstance(verdict.get("impacts"), dict) else {}
    equity_impacts = impacts.get("equity") if isinstance(impacts.get("equity"), list) else []
    summary_items = verdict.get("summary") if isinstance(verdict.get("summary"), list) else []
    evidence = _coerce_text_list([sector], equity_impacts, summary_items[:1])

    sector_alignment = 0.55
    if sector != "unknown":
        sector_alignment += 0.15
    if equity_impacts:
        sector_alignment += 0.15
    if expected_return != 0.0:
        sector_alignment += min(0.15, abs(expected_return) * 5.0)
    sector_alignment = max(0.0, min(1.0, sector_alignment))

    transmission_factor = round(
        max(0.05, min(1.0, (confidence_before * 0.55) + (sector_alignment * 0.45))),
        4,
    )
    transmission_confidence = round(
        max(
            0.0,
            min(
                1.0,
                confidence_before
                * (0.92 if sector != "unknown" else 0.62)
                * (0.95 if equity_impacts else 0.82),
            ),
        ),
        4,
    )
    transmission_uncertainty = round(max(0.0, min(1.0, 1.0 - transmission_confidence)), 4)
    confidence_after = round(
        max(0.0, min(1.0, confidence_before * (1.0 - (transmission_uncertainty * 0.35)))),
        4,
    )

    return {
        "ticker": ticker,
        "sector": sector,
        "horizon": verdict.get("horizon") or "1w",
        "company_direction": coerce_verdict(
            verdict.get("verdict") or verdict.get("action") or verdict.get("direction"),
            default="hold",
        ),
        "expected_return": expected_return,
        "risk_level": normalize_risk_level(verdict.get("risk_level"), default="medium"),
        "confidence_before_transmission": round(confidence_before, 4),
        "transmission_factor": transmission_factor,
        "transmission_confidence": transmission_confidence,
        "transmission_uncertainty": transmission_uncertainty,
        "confidence_after_transmission": confidence_after,
        "impact_decomposition": {
            "sector_tailwind_weight": round(max(0.0, min(1.0, transmission_factor * 0.6)), 4),
            "idiosyncratic_weight": round(max(0.0, min(1.0, 1.0 - (transmission_factor * 0.6))), 4),
        },
        "sector_signal_evidence": evidence,
    }


async def get_judge_sector_company_transmission_payload(
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
    """Build a company-layer view with sector transmission metadata from Judge verdicts."""
    now_iso = utc_now_iso()
    normalized_tickers = normalize_tickers(ticker or [])
    try:
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
        data = verdict_payload.get("data") if isinstance(verdict_payload, dict) else {}
        verdicts = data.get("verdicts") if isinstance(data, dict) and isinstance(data.get("verdicts"), list) else []
        rows = [
            _build_sector_company_transmission_row(verdict)
            for verdict in verdicts
            if isinstance(verdict, dict)
        ]
        response_data = {
            "rows": rows,
            "count": len(rows),
            "generated_at": data.get("generated_at") if isinstance(data, dict) else now_iso,
            "filters_applied": {
                "min_confidence": min_confidence,
                "tickers": normalized_tickers,
                "sort_by": str(sort_by),
                "sort_order": str(sort_order),
                "limit": limit,
                "profile": profile,
            },
            "stats": {
                "sector_coverage_count": len([row for row in rows if row.get("sector") != "unknown"]),
                "avg_transmission_factor": round(
                    sum(row["transmission_factor"] for row in rows) / len(rows),
                    4,
                ) if rows else 0.0,
                "avg_confidence_after_transmission": round(
                    sum(row["confidence_after_transmission"] for row in rows) / len(rows),
                    4,
                ) if rows else 0.0,
                "high_uncertainty_count": len(
                    [row for row in rows if row.get("transmission_uncertainty", 0.0) >= 0.4]
                ),
            },
            "warnings": [],
            "source": ensure_source_list(
                data.get("source") if isinstance(data, dict) else None,
                default_source="judge_sector_company_transmission_route",
            ),
        }
        append_source_tag(
            response_data,
            "judge_sector_company_transmission_route",
            default_source="judge_sector_company_transmission_route",
        )
        if debug:
            response_data["judge_source"] = {
                "count": len(verdicts),
                "freshness": verdict_payload.get("freshness"),
                "status": verdict_payload.get("status"),
                "error": verdict_payload.get("error"),
            }
        return service_response_with_metadata(
            response_data,
            default_source="judge_sector_company_transmission_route",
            freshness=verdict_payload.get("freshness") or response_data.get("generated_at") or now_iso,
            status=verdict_payload.get("status"),
            error=verdict_payload.get("error"),
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "rows": [],
                "count": 0,
                "generated_at": now_iso,
                "filters_applied": {
                    "min_confidence": min_confidence,
                    "tickers": normalized_tickers,
                    "sort_by": str(sort_by),
                    "sort_order": str(sort_order),
                    "limit": limit,
                    "profile": profile,
                },
                "stats": {
                    "sector_coverage_count": 0,
                    "avg_transmission_factor": 0.0,
                    "avg_confidence_after_transmission": 0.0,
                    "high_uncertainty_count": 0,
                },
                "warnings": [],
                "source": [
                    "judge_sector_company_transmission_route",
                    "judge_sector_company_transmission_fallback",
                ],
                "error": str(exc),
                "message": "Sector-to-company transmission unavailable; fallback returned.",
            },
            default_source="judge_sector_company_transmission_route",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
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
            "profiles": _list_judge_profile_options(),
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
                "profiles": _list_judge_profile_options(),
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


async def get_judge_personal_finance_start_payload(
    *,
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build personal-finance copilot starter payload used by judge API routes."""
    now_iso = utc_now_iso()
    normalized_tickers = normalize_tickers(tickers or [])
    scope = {"tickers": normalized_tickers} if normalized_tickers else None

    try:
        copilot_service, context_service_cls = _resolve_copilot_services()
        if copilot_service is None:
            raise RuntimeError("Copilot service unavailable")

        if hasattr(copilot_service, "build_context_payload"):
            payload = await copilot_service.build_context_payload(
                context_service_cls=context_service_cls,
                scope=scope,
            )
        else:
            payload = {}

        copilot_start = (
            payload.get("copilot_start")
            if isinstance(payload, dict)
            else None
        )
        if not isinstance(copilot_start, dict) or not copilot_start:
            build_start_payload = getattr(
                copilot_service,
                "_build_copilot_start_payload",
                None,
            ) or getattr(copilot_service, "_legacy_copilot_start_payload", None)
            if callable(build_start_payload):
                copilot_start = build_start_payload(
                    daily_brief=payload.get("daily_brief") if isinstance(payload, dict) else None,
                    entry_points=payload.get("entry_points") if isinstance(payload, dict) else None,
                    scope=scope,
                )
            else:
                daily_brief = {
                    "summary": "No daily brief available yet.",
                    "market_sentiment": "UNKNOWN",
                    "top_signals": [],
                    "top_risks": [],
                    "macro_signals": [],
                    "sector_rotation": {"top": [], "bottom": []},
                    "generated_at": now_iso,
                    "freshness": now_iso,
                    "source": ["judge_personal_finance_fallback"],
                }
                copilot_start = {
                    "brief_of_day": daily_brief,
                    "ask": [],
                    "open": [],
                }

        resolved_start = _rewrite_personal_finance_start_targets(copilot_start)
        resolved_start = dict(resolved_start) if isinstance(resolved_start, dict) else {}
        brief = (
            dict(resolved_start.get("brief_of_day"))
            if isinstance(resolved_start.get("brief_of_day"), dict)
            else {}
        )
        ask_items = [dict(item) for item in resolved_start.get("ask") if isinstance(item, dict)]
        open_items = [dict(item) for item in resolved_start.get("open") if isinstance(item, dict)]

        # Ensure the start screen always exposes at least one actionable ask/open entry.
        # This protects the UX contract when upstream copilot payloads are sparse.
        if (not ask_items or not open_items) and not copilot_start is None:
            build_start_payload = getattr(
                copilot_service,
                "_build_copilot_start_payload",
                None,
            ) or getattr(copilot_service, "_legacy_copilot_start_payload", None)
            if callable(build_start_payload):
                fallback_start = build_start_payload(
                    daily_brief=payload.get("daily_brief") if isinstance(payload, dict) else None,
                    entry_points=payload.get("entry_points") if isinstance(payload, dict) else None,
                    scope=scope,
                )
                fallback_items = (
                    dict(fallback_start)
                    if isinstance(fallback_start, dict)
                    else {}
                )
                fallback_start = _rewrite_personal_finance_start_targets(fallback_items)
                if not ask_items:
                    ask_items = [
                        dict(item)
                        for item in fallback_start.get("ask", [])
                        if isinstance(item, dict)
                    ]
                if not open_items:
                    open_items = [
                        dict(item)
                        for item in fallback_start.get("open", [])
                        if isinstance(item, dict)
                    ]

        result: Dict[str, Any] = {
            "brief_of_day": brief,
            "ask": ask_items,
            "open": open_items,
            "generated_at": brief.get("generated_at") or now_iso,
            "freshness": brief.get("freshness") or brief.get("generated_at") or now_iso,
            "source": ensure_source_list(
                (payload.get("source") if isinstance(payload, dict) else None),
                default_source="judge_personal_finance_start_service",
            ),
            "sources": ensure_source_list(
                (payload.get("sources") if isinstance(payload, dict) else None),
                default_source="judge_personal_finance_start_service",
            ),
            "filters_applied": {"tickers": list(normalized_tickers)},
            "stats": {
                "ask_count": len(ask_items),
                "open_count": len(open_items),
            },
            "warnings": [],
        }

        if (payload or {}).get("context_influence") is not None:
            result["context_influence"] = payload.get("context_influence")
        if (payload or {}).get("portfolio_context") is not None:
            result["portfolio_context"] = payload.get("portfolio_context")
        if (payload or {}).get("regime_detection") is not None:
            result["regime_detection"] = payload.get("regime_detection")
        if (payload or {}).get("allocation_drift_alerts") is not None:
            result["allocation_drift_alerts"] = payload.get("allocation_drift_alerts")
        if not (result.get("source") or [])[0:1] and not result.get("sources"):
            result["source"] = ["judge_personal_finance_start_service", "copilot_route_fallback"]
            result["sources"] = ["judge_personal_finance_start_service", "copilot_route_fallback"]

        if (payload or {}).get("regime") == "fallback":
            result.setdefault("warnings", []).append("Market context service temporarily unavailable.")

        return service_response_with_metadata(
            result,
            default_source="judge_personal_finance_start_service",
            freshness=result.get("freshness"),
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "brief_of_day": {
                    "summary": "No daily brief available yet.",
                    "market_sentiment": "UNKNOWN",
                    "top_signals": [],
                    "top_risks": [],
                    "macro_signals": [],
                    "sector_rotation": {"top": [], "bottom": []},
                    "generated_at": now_iso,
                    "freshness": now_iso,
                    "source": ["judge_personal_finance_fallback"],
                },
                "ask": [],
                "open": [],
                "generated_at": now_iso,
                "freshness": now_iso,
                "source": ["judge_personal_finance_start_service", "critical_error_fallback"],
                "sources": ["judge_personal_finance_start_service", "critical_error_fallback"],
                "filters_applied": {"tickers": list(normalized_tickers)},
                "stats": {
                    "ask_count": 0,
                    "open_count": 0,
                },
                "warnings": ["Fell back to judge personal finance starter defaults."],
                "error": str(exc),
                "message": "personal-finance start fallback response",
            },
            default_source="judge_personal_finance_start_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_personal_finance_context_payload(
    *,
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Proxy personal-finance context payload from copilot context stack."""
    now_iso = utc_now_iso()
    normalized_tickers = normalize_tickers(tickers or [])
    scope = {"tickers": normalized_tickers} if normalized_tickers else None

    try:
        copilot_service, context_service_cls = _resolve_copilot_services()
        if copilot_service is None:
            raise RuntimeError("Copilot service unavailable")

        payload = await copilot_service.build_context_payload(
            context_service_cls=context_service_cls,
            scope=scope,
        )
        if not isinstance(payload, dict):
            raise TypeError("Invalid copilot context payload")

        if payload.get("regime") == "fallback":
            payload.setdefault("note", "Market context service temporarily unavailable.")

        return service_response_with_metadata(
            payload,
            default_source="judge_personal_finance_context_service",
            freshness=payload.get("freshness") or payload.get("generated_at") or now_iso,
        )
    except Exception as exc:
        fallback: Dict[str, Any] = {
            "note": "Market context service temporarily unavailable.",
            "daily_brief": {"summary": "Market context unavailable.", "generated_at": now_iso, "freshness": now_iso},
            "entry_points": [],
            "scope_tickers": list(normalized_tickers),
        }
        return service_response_with_metadata(
            fallback,
            default_source="judge_personal_finance_context_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_personal_finance_ask_payload(
    *,
    question: str,
    scope: Optional[Dict[str, Any]] = None,
    tickers: Optional[List[str]] = None,
    max_sources: Optional[int] = 5,
    context_years: Optional[int] = 5,
) -> Dict[str, Any]:
    """Proxy personal-finance ask payload from copilot ask stack."""
    now_iso = utc_now_iso()
    resolved_scope = _resolve_personal_finance_scope(
        scope=scope,
        tickers=tickers,
    )
    normalized_tickers = normalize_tickers(tickers or [])
    try:
        copilot_service, context_service_cls = _resolve_copilot_services()
        if copilot_service is None:
            raise RuntimeError("Copilot service unavailable")

        payload = await copilot_service.build_ask_payload(
            question=question,
            scope=resolved_scope,
            tickers=normalized_tickers,
            max_sources=max_sources,
            context_years=context_years,
            context_service_cls=context_service_cls,
        )
        if not isinstance(payload, dict):
            raise TypeError("Invalid copilot ask payload")

        return service_response_with_metadata(
            payload,
            default_source="judge_personal_finance_ask_service",
            freshness=payload.get("freshness") or payload.get("generated_at") or now_iso,
        )
    except Exception as exc:
        payload = {
            "answer": f"Copilot unavailable: {exc}",
            "action": "hold",
            "verdict": "hold",
            "why": ["Le service Ask est temporairement indisponible."],
            "risk": {"level": "high", "caveat": "Service copilot indisponible."},
            "risk_level": "high",
            "sources": [],
            "citations": [],
            "model": "judge_personal_finance_ask_fallback",
            "confidence": 0.0,
            "generated_at": now_iso,
            "freshness": now_iso,
            "sources_count": 0,
            "quality_status": "error",
            "requirements_met": {"min_sources_2": False, "quality_threshold": False},
            "question": question,
            "warnings": ["Copilot ask backend temporarily unavailable."],
            "error": str(exc),
        }
        return service_response_with_metadata(
            payload,
            default_source="judge_personal_finance_ask_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_geopolitical_risk_graph_payload(
    *,
    region: Optional[str],
    limit: int,
) -> Dict[str, Any]:
    """Build a stable geopolitical risk graph from persisted news snapshots."""
    now_iso = utc_now_iso()
    try:
        payload = _build_geopolitical_graph_payload(region=region, limit=limit)
        return service_response_with_metadata(
            payload,
            default_source="judge_geopolitical_risk_graph_service",
            freshness=payload.get("freshness") or now_iso,
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "generated_at": now_iso,
                "freshness": now_iso,
                "source": [
                    "judge_geopolitical_risk_graph_service",
                    "geopolitical_risk_graph_fallback",
                ],
                "filters_applied": {
                    "region": str(region or "").strip().lower() or None,
                    "limit": limit,
                },
                "stats": {
                    "article_count": 0,
                    "regions_detected": 0,
                    "edges_returned": 0,
                    "alerts_count": 0,
                },
                "nodes": [],
                "edges": [],
                "alerts": [],
                "warnings": [],
                "error": str(exc),
                "message": "Geopolitical risk graph unavailable; fallback returned.",
            },
            default_source="judge_geopolitical_risk_graph_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


async def get_judge_event_impact_horizon_matrix_payload(
    *,
    event_type: Optional[str],
    limit: int,
) -> Dict[str, Any]:
    now_iso = utc_now_iso()
    try:
        payload = _build_event_impact_horizon_matrix_payload(
            event_type=event_type,
            limit=limit,
        )
        return service_response_with_metadata(
            payload,
            default_source="judge_event_impact_horizon_matrix_service",
            freshness=payload.get("freshness") or now_iso,
        )
    except Exception as exc:
        return service_response_with_metadata(
            {
                "generated_at": now_iso,
                "freshness": now_iso,
                "source": [
                    "judge_event_impact_horizon_matrix_service",
                    "event_impact_horizon_matrix_fallback",
                ],
                "filters_applied": {
                    "event_type": str(event_type or "").strip().lower() or None,
                    "limit": limit,
                },
                "stats": {
                    "article_count": 0,
                    "event_types_returned": 0,
                    "alerts_count": 0,
                    "horizons": list(_EVENT_HORIZON_KEYS),
                },
                "matrix": [],
                "alerts": [],
                "templates": {
                    "cross_horizon_divergence": "Event horizon matrix unavailable; no interpretation template generated.",
                },
                "warnings": [],
                "error": str(exc),
                "message": "Event impact horizon matrix unavailable; fallback returned.",
            },
            default_source="judge_event_impact_horizon_matrix_service",
            freshness=now_iso,
            status="degraded",
            error=str(exc),
        )


__all__ = [
    "JudgeVerdictsComputeFn",
    "get_judge_sector_company_transmission_payload",
    "get_judge_verdicts_payload",
    "get_judge_quality_payload",
    "get_judge_quality_history_payload",
    "get_judge_options_payload",
    "get_judge_geopolitical_risk_graph_payload",
    "get_judge_event_impact_horizon_matrix_payload",
    "get_judge_decision_journal_payload",
    "append_judge_decision_outcome_feedback",
    "get_judge_decision_outcome_feedback",
]
