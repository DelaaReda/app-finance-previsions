from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd


DEFAULT_AUDIT_TARGETS: Dict[str, Dict[str, Any]] = {
    "forecasts": {"path": "forecasts.json", "min_records": 1},
    "news": {"path": "news_feed.json", "min_records": 20},
    "macro": {"path": "macro_series.json", "min_records": 1},
    "stocks": {"path": "stocks/prices.json", "min_records": 5},
    "brief": {"path": "brief_weekly.json", "min_records": 1},
    "backtests": {"path": "backtests.json", "min_records": 1},
    "judge": {"path": "judge_quality.json", "min_records": 1},
}

TIMESTAMP_KEYS = (
    "timestamp",
    "generated_at",
    "saved_at",
    "freshness",
    "last_update",
    "as_of",
    "asof",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_data_dir(data_dir: str | Path | None = None) -> Path:
    if data_dir is not None:
        return Path(data_dir).resolve()

    try:
        from .path_resolver import get_data_directory  # local import to avoid circular issues

        return Path(get_data_directory()).resolve()
    except Exception:
        return Path(__file__).resolve().parents[2] / "data"


def _read_json(path: Path) -> Tuple[Any, str | None]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh), None
    except Exception as exc:
        return None, str(exc)


def _extract_record_count(payload: Any) -> int:
    if payload is None:
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("rows", "results", "articles", "items", "signals"):
            value = payload.get(key)
            if isinstance(value, (list, dict)):
                return len(value)
        if "series" in payload:
            series = payload.get("series")
            if isinstance(series, (list, dict)):
                return len(series)
        if "tickers" in payload:
            tickers = payload.get("tickers")
            if isinstance(tickers, dict):
                return len(tickers)
        nested = payload.get("data")
        if isinstance(nested, (list, dict)):
            nested_count = _extract_record_count(nested)
            if nested_count > 0:
                return nested_count
        nested_counts = [_extract_record_count(v) for v in payload.values() if isinstance(v, (list, dict))]
        if nested_counts:
            return max(nested_counts)
        return len(payload)
    return 1


def _find_timestamp(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in TIMESTAMP_KEYS:
        value = payload.get(key)
        if value:
            return str(value)
    nested = payload.get("data")
    if isinstance(nested, dict):
        for key in TIMESTAMP_KEYS:
            value = nested.get(key)
            if value:
                return str(value)
    return None


def check_timeseries(df: pd.DataFrame, index_col: str = "date") -> Dict[str, Any]:
    out = {"ok": True, "issues": []}
    if df is None or df.empty:
        out["ok"] = False
        out["issues"].append("empty")
        return out
    s = df[index_col] if index_col in df else df.index
    if s.is_monotonic_increasing is False:
        out["ok"] = False
        out["issues"].append("not_monotonic")
    if df.duplicated(subset=[index_col]).any() if index_col in df else df.index.duplicated().any():
        out["ok"] = False
        out["issues"].append("duplicates")
    null_ratio = float(df.isna().mean().mean())
    if null_ratio > 0.2:
        out["issues"].append(f"high_null_ratio={null_ratio:.2f}")
    return out


def run_quality_gate(data: Any, dataset_name: str, min_records: int = 1) -> Tuple[bool, Dict[str, Any]]:
    min_records = max(1, int(min_records))
    structure_ok = isinstance(data, (dict, list))
    record_count = _extract_record_count(data) if structure_ok else 0
    non_empty = record_count > 0
    min_records_ok = record_count >= min_records
    has_timestamp = _find_timestamp(data) is not None if structure_ok else False

    issues = []
    if not structure_ok:
        issues.append("invalid_structure")
    if not non_empty:
        issues.append("empty_payload")
    if structure_ok and not min_records_ok:
        issues.append(f"insufficient_records<{min_records}")
    if structure_ok and not has_timestamp:
        issues.append("missing_timestamp")

    checks = {
        "structure_ok": structure_ok,
        "non_empty": non_empty,
        "min_records_ok": min_records_ok,
        "has_timestamp": has_timestamp,
        "record_count": record_count,
        "min_records_required": min_records,
    }

    passes = structure_ok and non_empty and min_records_ok
    return passes, {
        "dataset": dataset_name,
        "passes": passes,
        "checked_at": _utc_now_iso(),
        "checks": checks,
        "issues": issues,
    }


def run_quality_audit(
    data_dir: str | Path | None = None, min_records_by_dataset: Dict[str, int] | None = None
) -> Dict[str, Any]:
    base = _resolve_data_dir(data_dir)
    checks: Dict[str, Dict[str, Any]] = {}
    degraded_domains = []
    files_passed = 0
    files_failed = 0

    thresholds = dict((k, int(v.get("min_records", 1))) for k, v in DEFAULT_AUDIT_TARGETS.items())
    if min_records_by_dataset:
        thresholds.update({k: max(1, int(v)) for k, v in min_records_by_dataset.items()})

    for domain, target in DEFAULT_AUDIT_TARGETS.items():
        rel_path = Path(target["path"])
        full_path = base / rel_path
        min_records = thresholds.get(domain, int(target.get("min_records", 1)))

        if not full_path.exists():
            files_failed += 1
            degraded_domains.append(domain)
            checks[domain] = {
                "dataset": domain,
                "path": str(rel_path),
                "passes": False,
                "checked_at": _utc_now_iso(),
                "checks": {
                    "structure_ok": False,
                    "non_empty": False,
                    "min_records_ok": False,
                    "has_timestamp": False,
                    "record_count": 0,
                    "min_records_required": min_records,
                },
                "issues": ["missing_file"],
            }
            continue

        payload, load_error = _read_json(full_path)
        if load_error:
            files_failed += 1
            degraded_domains.append(domain)
            checks[domain] = {
                "dataset": domain,
                "path": str(rel_path),
                "passes": False,
                "checked_at": _utc_now_iso(),
                "checks": {
                    "structure_ok": False,
                    "non_empty": False,
                    "min_records_ok": False,
                    "has_timestamp": False,
                    "record_count": 0,
                    "min_records_required": min_records,
                },
                "issues": [f"json_load_error:{load_error}"],
            }
            continue

        passes, report = run_quality_gate(payload, domain, min_records=min_records)
        report["path"] = str(rel_path)
        checks[domain] = report
        if passes:
            files_passed += 1
        else:
            files_failed += 1
            degraded_domains.append(domain)

    total_files_checked = len(DEFAULT_AUDIT_TARGETS)
    overall_quality_score = round((files_passed / total_files_checked) * 100, 2) if total_files_checked else 0.0

    return {
        "summary": {
            "total_files_checked": total_files_checked,
            "files_passed": files_passed,
            "files_failed": files_failed,
            "overall_quality_score": overall_quality_score,
            "degraded_domains": degraded_domains,
            "checked_at": _utc_now_iso(),
        },
        "checks": checks,
        "degraded_flag": files_failed > 0,
    }
