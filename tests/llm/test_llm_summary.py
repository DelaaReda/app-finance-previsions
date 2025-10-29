import json
from pathlib import Path
from typing import List

import pytest


def _fake_summary_json() -> str:
    # Minimal JSON conforming to src/agents/llm/schemas.LLMEnsembleSummary
    return json.dumps({
        "asof": "2025-10-28T00:00:00Z",
        "regime": "neutral",
        "risk_level": "medium",
        "outlook_days_7": "modérément haussier",
        "outlook_days_30": "neutre",
        "key_drivers": ["cpi", "yield_curve"],
        "contributors": [
            {"source": "equity", "model": "baseline", "horizon": "7d", "symbol": "AAPL", "score": 0.7}
        ],
    })


def test_run_llm_summary_writes_partition(tmp_path, monkeypatch):
    # Arrange
    from src.agents.llm import arbiter_agent

    class _DummyLLM:
        def generate(self, messages: List[dict], **kwargs) -> str:
            return _fake_summary_json()

    monkeypatch.setattr("src.agents.llm.runtime.LLMClient", lambda *a, **k: _DummyLLM())

    save_base = str(tmp_path / "data" / "llm_summary")

    # Act
    summary = arbiter_agent.run_llm_summary(save_base=save_base)

    # Assert: file exists under dt=YYYYMMDDHH/summary.json
    outdir_candidates = sorted((Path(save_base)).glob("dt=*/summary.json"))
    assert outdir_candidates, "no summary.json written"
    # Validate minimal fields
    assert summary.asof
    assert isinstance(summary.key_drivers, list)
