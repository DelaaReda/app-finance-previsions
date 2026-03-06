#!/usr/bin/env python3
"""Product value and priority guard helpers for planner-orchestrated runtime."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_S = 0.6
FRESHNESS_THRESHOLDS_S = {
    "prices": 12 * 3600,
    "news": 6 * 3600,
    "forecasts": 24 * 3600,
    "backtests": 72 * 3600,
    "brief_daily": 24 * 3600,
}
P0_DATA_KEYS = ("prices", "news", "forecasts")
PRODUCT_KEYWORDS = (
    "copilot",
    "forecast",
    "news",
    "dashboard",
    "brief",
    "ticker",
    "portfolio",
    "market",
    "price",
    "backtest",
    "judge",
    "search",
    "macro",
)
ORCHESTRATION_KEYWORDS = (
    "orchestr",
    "planner",
    "runtime",
    "cron",
    "contract",
    "reconcile",
    "workboard",
    "queue",
    "monitor",
    "guard",
    "migration",
    "batch hygiene",
    "autobatch",
    "message bus",
    "worker bridge",
    "session repair",
    "takeover",
    "lock cleanup",
    "state truth",
)
COMMIT_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _parse_dt(raw: Any) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_s(raw: Any, *, now: datetime | None = None) -> int:
    dt = _parse_dt(raw)
    if dt is None:
        return -1
    current = now or _now()
    return max(0, int((current - dt).total_seconds()))


def _state_from_age(age_s: int, threshold_s: int) -> str:
    if age_s < 0:
        return "unknown"
    if age_s <= threshold_s:
        return "fresh"
    if age_s <= threshold_s * 2:
        return "warm"
    return "stale"


def _snapshot_timestamp(payload: dict[str, Any]) -> str:
    for key in ("last_update", "generated_at", "freshness", "saved_at"):
        token = str(payload.get(key, "")).strip()
        if token:
            return token
    return ""


def _extract_rows(payload: dict[str, Any], *, primary: str, fallback: str) -> list[dict[str, Any]]:
    rows = payload.get(primary)
    if isinstance(rows, list):
        return [item for item in rows if isinstance(item, dict)]
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get(primary)
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        nested = data.get(fallback)
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
    fallback_rows = payload.get(fallback)
    if isinstance(fallback_rows, list):
        return [item for item in fallback_rows if isinstance(item, dict)]
    return []


def _normalize_source(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    token = str(raw or "").strip()
    return [token] if token else []


def _contains_token(markers: list[str], token: str) -> bool:
    token = token.lower()
    return any(token in marker.lower() for marker in markers)


def _probe_json(url: str, *, timeout_s: float) -> tuple[dict[str, Any], float, str]:
    started = _now()
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout_s) as response:
            body = response.read().decode("utf-8", errors="ignore")
        payload = json.loads(body)
        latency_ms = max(0.0, (_now() - started).total_seconds() * 1000.0)
        return payload if isinstance(payload, dict) else {}, latency_ms, ""
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        latency_ms = max(0.0, (_now() - started).total_seconds() * 1000.0)
        return {}, latency_ms, str(exc)
    except Exception as exc:
        latency_ms = max(0.0, (_now() - started).total_seconds() * 1000.0)
        return {}, latency_ms, str(exc)


def _monitor_data_file(root: Path, relative_path: str) -> Path:
    return root / relative_path


def _freshness_entry(root: Path, key: str, relative_path: str, *, now: datetime | None = None) -> dict[str, Any]:
    path = _monitor_data_file(root, relative_path)
    payload = _read_json(path) if path.exists() else {}
    threshold = FRESHNESS_THRESHOLDS_S[key]
    updated_at = _snapshot_timestamp(payload)
    age = _age_s(updated_at, now=now)
    return {
        "path": str(path),
        "exists": path.exists(),
        "updated_at": updated_at or "none",
        "age_s": age,
        "threshold_s": threshold,
        "state": _state_from_age(age, threshold),
    }


def _forecast_metrics(root: Path, *, api_base_url: str | None, timeout_s: float, now: datetime | None = None) -> dict[str, Any]:
    current = now or _now()
    source = "file"
    payload: dict[str, Any] = {}
    probe_error = ""
    if api_base_url:
        probe_payload, _latency_ms, probe_error = _probe_json(
            f"{api_base_url.rstrip('/')}/api/forecasts?limit=5",
            timeout_s=timeout_s,
        )
        if probe_payload:
            payload = probe_payload.get("data") if probe_payload.get("ok") else probe_payload
            if isinstance(payload, dict) and payload:
                source = "api"
    if not payload:
        payload = _read_json(root / "data" / "forecasts.json")

    rows = _extract_rows(payload, primary="rows", fallback="rows")
    source_markers = _normalize_source(payload.get("source"))
    provider_chain = _normalize_source(payload.get("provider_chain"))
    row_markers: list[str] = []
    for row in rows[:10]:
        row_markers.extend(_normalize_source(row.get("source")))
        row_markers.extend(_normalize_source(row.get("model")))
    markers = list(dict.fromkeys([*source_markers, *provider_chain, *row_markers]))
    timestamp = (
        str(payload.get("last_update") or "").strip()
        or str(payload.get("generated_at") or "").strip()
        or str(payload.get("freshness") or "").strip()
    )
    age = int(float(payload.get("freshness_age", -1))) if str(payload.get("freshness_age", "")).strip() else _age_s(timestamp, now=current)
    freshness_status = str(payload.get("freshness_status", "")).strip().lower() or _state_from_age(age, FRESHNESS_THRESHOLDS_S["forecasts"])
    fallback_used = bool(payload.get("fallback_used")) or any(
        token in marker.lower() for marker in markers for token in ("fallback", "mock", "critical_error", "degraded")
    )
    if any(token in marker.lower() for marker in markers for token in ("hashlib", "pseudo", "fake")):
        source_kind = "pseudo"
    elif any(token in marker.lower() for marker in markers for token in ("mock", "fallback")):
        source_kind = "fallback"
    elif any(token in marker.lower() for marker in markers for token in ("simple_momentum", "forecasts_simple")):
        source_kind = "simple_model"
    elif markers:
        source_kind = "model_backed"
    else:
        source_kind = "unknown"
    valid = bool(rows) and source_kind not in {"pseudo", "fallback"}
    quality_degraded = freshness_status == "stale" or bool(fallback_used)
    return {
        "status": "ok" if valid and not quality_degraded else ("degraded" if valid else "error"),
        "probe_source": source,
        "probe_error": probe_error,
        "rows_count": len(rows),
        "fallback_used": bool(fallback_used),
        "freshness_status": freshness_status,
        "freshness_age_s": age,
        "updated_at": timestamp or "none",
        "source_kind": source_kind,
        "source_markers": markers[:8],
        "valid": bool(valid),
    }


def _copilot_metrics(*, api_base_url: str | None, timeout_s: float) -> dict[str, Any]:
    if not api_base_url:
        return {
            "status": "unknown",
            "usable": None,
            "fallback": None,
            "source_count": 0,
            "latency_ms": 0.0,
            "reason": "api_probe_disabled",
        }
    payload, latency_ms, error = _probe_json(
        f"{api_base_url.rstrip('/')}/api/copilot/context",
        timeout_s=timeout_s,
    )
    if not payload:
        return {
            "status": "unknown",
            "usable": None,
            "fallback": None,
            "source_count": 0,
            "latency_ms": round(latency_ms, 3),
            "reason": error or "copilot_probe_failed",
        }
    data = payload.get("data") if payload.get("ok") else payload
    if not isinstance(data, dict):
        data = {}
    markers = []
    markers.extend(_normalize_source(data.get("sources")))
    meta = data.get("metadata")
    if isinstance(meta, dict):
        markers.extend(_normalize_source(meta.get("sources")))
    regime = str(data.get("regime") or data.get("status") or "").strip().lower()
    fallback = regime == "fallback" or _contains_token(markers, "fallback")
    usable = bool(markers) and not fallback
    status = "ok" if usable else ("fallback" if fallback else "degraded")
    return {
        "status": status,
        "usable": bool(usable),
        "fallback": bool(fallback),
        "source_count": len(markers),
        "latency_ms": round(latency_ms, 3),
        "reason": regime or "context_probe",
    }


def _classify_work_text(text: str) -> str:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return "unknown"
    if any(token in lowered for token in ORCHESTRATION_KEYWORDS):
        return "orchestration"
    if any(token in lowered for token in PRODUCT_KEYWORDS):
        return "product"
    return "unknown"


def _delivery_mix(root: Path) -> dict[str, Any]:
    workboard = _read_json(root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json")
    streams = workboard.get("streams", []) if isinstance(workboard, dict) else []
    tasks = workboard.get("tasks", []) if isinstance(workboard, dict) else []
    items: list[dict[str, Any]] = []
    for stream in streams:
        if isinstance(stream, dict):
            items.append(stream)
    for task in tasks:
        if isinstance(task, dict):
            state = str(task.get("state", "")).strip().upper()
            if state not in {"DONE", "CLOSED"}:
                items.append(task)
    product = 0
    orchestration = 0
    unknown = 0
    product_samples: list[str] = []
    orchestration_samples: list[str] = []
    for item in items:
        state = str(item.get("state", "")).strip().upper()
        if state in {"DONE", "CLOSED"}:
            continue
        text = " | ".join(
            [
                str(item.get("title", "")),
                str(item.get("next_action", "")),
                str(item.get("dispatch_lane", "")),
                str(item.get("code", "")),
            ]
        )
        klass = _classify_work_text(text)
        label = str(item.get("id", "")).strip() or str(item.get("title", "")).strip()
        if klass == "product":
            product += 1
            if len(product_samples) < 5 and label:
                product_samples.append(label)
        elif klass == "orchestration":
            orchestration += 1
            if len(orchestration_samples) < 5 and label:
                orchestration_samples.append(label)
        else:
            unknown += 1
    classified = product + orchestration
    return {
        "active_items_total": product + orchestration + unknown,
        "classified_total": classified,
        "product_active_count": product,
        "orchestration_active_count": orchestration,
        "unknown_active_count": unknown,
        "product_ratio": round(product / classified, 3) if classified else 0.0,
        "orchestration_ratio": round(orchestration / classified, 3) if classified else 0.0,
        "product_samples": product_samples,
        "orchestration_samples": orchestration_samples,
    }


def _evaluate_guard(metrics: dict[str, Any]) -> dict[str, Any]:
    blocked_reasons: list[str] = []
    copilot = metrics.get("copilot", {})
    forecasts = metrics.get("forecasts", {})
    freshness = metrics.get("data_freshness", {})

    if copilot.get("status") in {"fallback", "error", "degraded"} and copilot.get("usable") is False:
        blocked_reasons.append("copilot_unusable")
    if not forecasts.get("valid", False):
        blocked_reasons.append("forecasts_invalid")
    for key in P0_DATA_KEYS:
        if str((freshness.get(key) or {}).get("state", "")).lower() == "stale":
            blocked_reasons.append(f"{key}_stale")

    p0_broken = bool(blocked_reasons)
    delivery_mix = metrics.get("delivery_mix", {})
    product_ratio = float(delivery_mix.get("product_ratio") or 0.0)
    orchestration_ratio = float(delivery_mix.get("orchestration_ratio") or 0.0)
    return {
        "status": "blocked" if p0_broken else "ok",
        "p0_broken": p0_broken,
        "blocked_reasons": blocked_reasons,
        "allow_orchestration_autobatch": not p0_broken,
        "needs_product_focus": p0_broken or orchestration_ratio > product_ratio,
    }


def build_product_value_metrics(
    root: Path,
    *,
    api_base_url: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or _now()
    freshness = {
        "prices": _freshness_entry(root, "prices", "data/stocks/prices.json", now=current),
        "news": _freshness_entry(root, "news", "data/news_feed.json", now=current),
        "forecasts": _freshness_entry(root, "forecasts", "data/forecasts.json", now=current),
        "backtests": _freshness_entry(root, "backtests", "data/backtests.json", now=current),
        "brief_daily": _freshness_entry(root, "brief_daily", "data/brief_daily.json", now=current),
    }
    metrics = {
        "generated_at": _iso(current),
        "copilot": _copilot_metrics(api_base_url=api_base_url, timeout_s=timeout_s),
        "forecasts": _forecast_metrics(root, api_base_url=api_base_url, timeout_s=timeout_s, now=current),
        "data_freshness": freshness,
        "delivery_mix": _delivery_mix(root),
    }
    metrics["priority_guard"] = _evaluate_guard(metrics)
    return metrics


def _manifest_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def build_delivery_integrity_metrics(
    root: Path,
    *,
    window_hours: int = 24,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or _now()
    workboard = _read_json(root / "docs" / "operations" / "orchestrator" / "parallel-workstreams.json")
    events = workboard.get("events", []) if isinstance(workboard, dict) else []
    recent: list[dict[str, Any]] = []
    cutoff_epoch = int(current.timestamp()) - int(window_hours * 3600)
    for event in events:
        if not isinstance(event, dict) or str(event.get("kind", "")).strip() != "complete":
            continue
        at_dt = _parse_dt(event.get("at"))
        if at_dt is None or int(at_dt.timestamp()) < cutoff_epoch:
            continue
        recent.append(event)

    with_manifest = 0
    with_tests = 0
    with_commit_evidence = 0
    suspicious: list[str] = []
    for event in recent:
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        task_id = str(details.get("task_id", "")).strip() or "unknown_task"
        proof_manifest = str(details.get("proof_manifest", "")).strip()
        artifact = str(details.get("artifact", "")).strip()
        manifest_path = root / proof_manifest if proof_manifest and not proof_manifest.startswith("/") else Path(proof_manifest or "")
        manifest_text = _manifest_text(manifest_path) if manifest_path.exists() else ""
        if manifest_text:
            with_manifest += 1
        has_tests = 'result: "PASS"' in manifest_text or "tests:" in manifest_text
        has_commit = bool(COMMIT_RE.search(artifact)) or bool(COMMIT_RE.search(manifest_text))
        if has_tests:
            with_tests += 1
        if has_commit:
            with_commit_evidence += 1
        if not manifest_text or not has_tests or not has_commit:
            suspicious.append(task_id)

    total = len(recent)
    status = "ok"
    if total and suspicious:
        status = "degraded"
    return {
        "generated_at": _iso(current),
        "window_hours": int(window_hours),
        "recent_completions": total,
        "proof_manifest_coverage": round(with_manifest / total, 3) if total else 1.0,
        "tests_evidence_coverage": round(with_tests / total, 3) if total else 1.0,
        "commit_evidence_coverage": round(with_commit_evidence / total, 3) if total else 1.0,
        "suspicious_completion_count": len(suspicious),
        "suspicious_task_ids": suspicious[:8],
        "status": status,
    }


def prompt_context(root: Path, *, api_base_url: str | None = None, timeout_s: float = DEFAULT_TIMEOUT_S) -> str:
    metrics = build_product_value_metrics(root, api_base_url=api_base_url, timeout_s=timeout_s)
    guard = metrics.get("priority_guard", {})
    freshness = metrics.get("data_freshness", {})
    freshness_summary = ",".join(
        f"{key}:{(freshness.get(key) or {}).get('state', 'unknown')}"
        for key in ("prices", "news", "forecasts")
    )
    delivery_mix = metrics.get("delivery_mix", {})
    return (
        f"priority_guard={guard.get('status','unknown')}; "
        f"allow_orchestration_autobatch={1 if guard.get('allow_orchestration_autobatch') else 0}; "
        f"blocked_reasons={','.join(guard.get('blocked_reasons', [])) or 'none'}; "
        f"copilot_status={(metrics.get('copilot') or {}).get('status','unknown')}; "
        f"forecasts_status={(metrics.get('forecasts') or {}).get('status','unknown')}; "
        f"freshness={freshness_summary}; "
        f"product_ratio={delivery_mix.get('product_ratio', 0.0)}; "
        f"orchestration_ratio={delivery_mix.get('orchestration_ratio', 0.0)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Planner product priority guard")
    parser.add_argument("--root", default="")
    parser.add_argument("--api-base-url", default="")
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("metrics")
    sub.add_parser("delivery")
    sub.add_parser("prompt-context")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[2]
    api_base_url = args.api_base_url.strip() or None
    if args.cmd == "metrics":
        print(json.dumps(build_product_value_metrics(root, api_base_url=api_base_url, timeout_s=args.timeout_s), ensure_ascii=True))
        return 0
    if args.cmd == "delivery":
        print(json.dumps(build_delivery_integrity_metrics(root), ensure_ascii=True))
        return 0
    print(prompt_context(root, api_base_url=api_base_url, timeout_s=args.timeout_s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
