from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict

import pandas as pd


@dataclass
class Tool:
    name: str
    func: Callable[..., Any]
    desc: str

    def call(self, **kwargs) -> Any:
        return self.func(**kwargs)


REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool):
    if tool.name in REGISTRY:
        raise ValueError(f"duplicate tool {tool.name}")
    REGISTRY[tool.name] = tool


# ---- Domain tools (read-only) ----

def _latest(pattern: str) -> Path | None:
    parts = sorted(Path(".").glob(pattern))
    return parts[-1] if parts else None


def load_forecasts(horizon: str | None = None, limit: int = 50) -> Dict[str, Any]:
    p = _latest("data/forecast/dt=*/final.parquet")
    if not p:
        return {"ok": False, "reason": "no_final"}
    df = pd.read_parquet(p)
    if horizon and "horizon" in df.columns:
        df = df[df["horizon"] == horizon]
    cols = [c for c in ["ticker", "horizon", "final_score", "direction", "confidence", "expected_return"] if c in df.columns]
    view = df[cols].head(limit) if cols else df.head(limit)
    return {"ok": True, "path": str(p), "rows": json.loads(view.to_json(orient="records"))}


def load_macro(limit: int = 20) -> Dict[str, Any]:
    p = _latest("data/macro/forecast/dt=*/macro_forecast.parquet")
    if not p:
        return {"ok": False, "reason": "no_macro_forecast"}
    df = pd.read_parquet(p)
    return {"ok": True, "path": str(p), "columns": list(df.columns)[:50], "rows": json.loads(df.head(limit).to_json(orient="records"))}


def freshness_status() -> Dict[str, Any]:
    p = _latest("data/quality/dt=*/freshness.json")
    if not p:
        return {"ok": False, "reason": "no_freshness"}
    try:
        js = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "path": str(p), "checks": js.get("checks", {}), "latest_dt": js.get("latest_dt")}


# Register defaults
register(Tool("load_forecasts", load_forecasts, "Load latest final.parquet, optionally filter by horizon."))
register(Tool("load_macro", load_macro, "Load latest macro_forecast parquet."))
register(Tool("freshness_status", freshness_status, "Load latest freshness.json checks."))

