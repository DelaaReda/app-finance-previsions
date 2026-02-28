from __future__ import annotations

import reuse.data as data_reuse
import reuse.forecasting as forecast_reuse
import reuse.judge as judge_reuse
import reuse.llm as llm_reuse


def test_reuse_llm_mode_wrapper_explicit_mode():
    assert llm_reuse.resolve_llm_mode("dev") == "dev"
    assert llm_reuse.resolve_llm_mode("best") == "best"


def test_reuse_judge_cache_key_is_stable():
    payload = {"ticker": "AAPL", "horizon": "7d"}
    key1 = judge_reuse.stable_cache_key("judge_v1", payload)
    key2 = judge_reuse.stable_cache_key("judge_v1", {"horizon": "7d", "ticker": "AAPL"})
    assert key1 == key2
    assert "judge_v1" in key1


def test_reuse_judge_news_scoring_smoke():
    rows = [
        {"title": "x", "timestamp": "2026-01-01T00:00:00Z", "sentiment_score": 0.2},
        {"title": "y", "timestamp": "2026-01-02T00:00:00Z", "sentiment_score": -0.4},
    ]
    scored = judge_reuse.score_judge_news(rows, cap=2)
    assert isinstance(scored, list)
    assert len(scored) <= 2


def test_reuse_data_quality_gate_smoke():
    ok, report = data_reuse.run_quality_gate(
        data=[{"x": 1}, {"x": 2}],
        dataset_name="unit-test",
        min_records=1,
    )
    assert ok is True
    assert isinstance(report, dict)
    assert report.get("dataset") == "unit-test"


def test_reuse_data_payload_resolver_smoke():
    out = data_reuse.resolve_snapshot_payload({"data": {"a": 1}}, fallback={"a": 0})
    assert out == {"a": 1}
    out2 = data_reuse.resolve_snapshot_payload(None, fallback={"a": 0})
    assert out2 == {"a": 0}


def test_reuse_forecasting_facade_exports_exist():
    assert callable(forecast_reuse.build_fundamental_view)
    assert callable(forecast_reuse.build_technical_view)
    assert callable(forecast_reuse.build_macro_view)
    assert callable(forecast_reuse.build_sentiment_view)
    assert callable(forecast_reuse.run_fusion)
