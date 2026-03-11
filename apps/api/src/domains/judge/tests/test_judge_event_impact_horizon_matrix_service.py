from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application import judge_endpoint_service


def test_event_impact_horizon_matrix_builds_cross_horizon_rows(monkeypatch):
    news_feed = {
        "articles": [
            {
                "title": "Nvidia guidance raises AI capex expectations",
                "summary": "Management lifts guidance as demand stays strong.",
                "published_at": "2026-03-10T10:00:00Z",
                "event_types": ["guidance"],
                "sentiment_score": 0.45,
            },
            {
                "title": "Fresh sanctions pressure shipping routes",
                "summary": "Freight routes face renewed compliance friction.",
                "published_at": "2026-03-10T08:00:00Z",
                "event_types": ["sanctions"],
                "sentiment_score": -0.35,
            },
        ]
    }

    monkeypatch.setattr(
        judge_endpoint_service,
        "load_json",
        lambda key: news_feed if key == "news_feed" else {},
    )

    payload = asyncio.run(
        judge_endpoint_service.get_judge_event_impact_horizon_matrix_payload(
            event_type=None,
            limit=5,
        )
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["stats"]["event_types_returned"] == 2
    assert data["stats"]["horizons"] == ["1d", "1w", "1m"]
    first_row = data["matrix"][0]
    assert {"1d", "1w", "1m"} == set(first_row["horizons"].keys())
    assert first_row["horizons"]["1d"]["impact_score"] > 0
    assert first_row["horizons"]["1w"]["impact_band"] in {"minimal", "low", "medium", "high"}
    assert first_row["dominant_horizon"] in {"1d", "1w", "1m"}
    assert "signal" in first_row["interpretation"]
    assert data["templates"]["cross_horizon_divergence"]


def test_event_impact_horizon_matrix_filters_event_type(monkeypatch):
    news_feed = {
        "articles": [
            {
                "title": "Earnings beat resets expectations",
                "published_at": "2026-03-10T10:00:00Z",
                "event_types": ["earnings"],
            },
            {
                "title": "Merger spread widens on regulatory concerns",
                "published_at": "2026-03-10T09:00:00Z",
                "event_types": ["merger"],
            },
        ]
    }

    monkeypatch.setattr(
        judge_endpoint_service,
        "load_json",
        lambda key: news_feed if key == "news_feed" else {},
    )

    payload = asyncio.run(
        judge_endpoint_service.get_judge_event_impact_horizon_matrix_payload(
            event_type="merger",
            limit=5,
        )
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["filters_applied"]["event_type"] == "merger"
    assert len(data["matrix"]) == 1
    assert data["matrix"][0]["event_type"] == "merger"
    assert data["matrix"][0]["interpretation"].startswith("merger has its strongest")


def test_event_impact_horizon_matrix_returns_never_empty_fallback(monkeypatch):
    def _boom(_key: str):
        raise RuntimeError("snapshot unavailable")

    monkeypatch.setattr(judge_endpoint_service, "load_json", _boom)

    payload = asyncio.run(
        judge_endpoint_service.get_judge_event_impact_horizon_matrix_payload(
            event_type=None,
            limit=3,
        )
    )

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    data = payload["data"]
    assert data["matrix"] == []
    assert data["stats"]["event_types_returned"] == 0
    assert data["message"] == "Event impact horizon matrix unavailable; fallback returned."
