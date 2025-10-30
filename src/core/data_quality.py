# src/core/data_quality.py
from __future__ import annotations
from typing import Dict, Any
import pandas as pd

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