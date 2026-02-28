"""Data and quality reuse facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import pandas as pd


def run_quality_audit(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    from core.data_quality import run_quality_audit as _run_quality_audit

    return _run_quality_audit(*args, **kwargs)


def run_quality_gate(data: Any, dataset_name: str, min_records: int = 1) -> Tuple[bool, Dict[str, Any]]:
    from core.data_quality import run_quality_gate as _run_quality_gate

    return _run_quality_gate(data=data, dataset_name=dataset_name, min_records=min_records)


def check_timeseries(df: pd.DataFrame, index_col: str = "date") -> Dict[str, Any]:
    from core.data_quality import check_timeseries as _check_timeseries

    return _check_timeseries(df=df, index_col=index_col)


def load_snapshot(key: str, aliases: Optional[Sequence[str]] = None) -> Optional[Dict[str, Any]]:
    from services.snapshot_loader import load_snapshot as _load_snapshot

    return _load_snapshot(key=key, aliases=aliases)


def resolve_snapshot_payload(
    snapshot: Optional[Dict[str, Any]],
    *,
    fallback: Optional[Dict[str, Any]] = None,
    candidates: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    from services.snapshot_loader import resolve_payload as _resolve_payload

    resolved = _resolve_payload(
        snapshot=snapshot,
        candidates=candidates or ("data", "payload"),
    )
    if isinstance(resolved, dict) and resolved:
        return resolved
    return dict(fallback or {})


def get_close_series(ticker: str, interval: str = "1d", limit: int = 252) -> Optional[pd.Series]:
    from core.data_access import get_close_series as _get_close_series

    return _get_close_series(ticker=ticker, interval=interval, limit=limit)


def latest_forecast_date() -> Optional[str]:
    from core.data_access import get_latest_forecast_date as _get_latest_forecast_date

    return _get_latest_forecast_date()


def latest_macro_date() -> Optional[str]:
    from core.data_access import get_latest_macro_date as _get_latest_macro_date

    return _get_latest_macro_date()


def load_json_file(path: str | Path) -> Optional[Dict[str, Any]]:
    from storage.io import load_json as _load_json

    return _load_json(str(path))
