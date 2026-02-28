from __future__ import annotations

import json
import time
from pathlib import Path

from src.tools.make import run_make


def run_pipeline(step_budget: int = 1) -> dict:
    """Minimal sequential orchestrator (no external deps).

    Steps (best‑effort):
    - update-monitor (freshness)
    - equity-forecast → forecast-aggregate
    - macro-forecast
    - llm-summary-run
    - ui-health (optional; best effort)
    """
    results = {"steps": []}
    def _do(name, target):
        r = run_make(target)
        results["steps"].append({"name": name, **r})
        return r["rc"] == 0

    # Limit runs per invocation (guardrail)
    budget = max(1, step_budget)
    steps = [
        ("freshness", "update-monitor"),
        ("equity", "equity-forecast"),
        ("aggregate", "forecast-aggregate"),
        ("macro", "macro-forecast"),
        ("llm_summary", "llm-summary-run"),
        ("ui_health", "ui-health"),
    ]
    for i, (name, target) in enumerate(steps, start=1):
        if i > budget:
            break
        try:
            _do(name, target)
        except Exception as e:
            results["steps"].append({"name": name, "rc": 1, "out": str(e), "duration_ms": 0})

    # Write a small summary artifact
    outdir = Path("data/agents_runs"); outdir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d%H%M%S")
    (outdir / f"run_{ts}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main():
    print(json.dumps(run_pipeline(step_budget=6), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

