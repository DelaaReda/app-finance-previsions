from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.judge.application import judge_endpoint_service


def test_geopolitical_risk_graph_payload_builds_alerts_from_news_feed(monkeypatch):
    news_feed = {
        "articles": [
            {
                "title": "Ukraine sanctions tighten after overnight strikes",
                "summary": "NATO diplomats weigh additional sanctions after conflict escalation.",
                "published_at": "2026-03-10T10:00:00Z",
                "geopolitics": ["ukraine", "nato"],
                "event_types": ["sanctions"],
            },
            {
                "title": "Ukraine conflict disrupts Black Sea routes",
                "summary": "Shipping insurers raise premiums amid conflict concerns.",
                "published_at": "2026-03-10T08:00:00Z",
                "geopolitics": ["ukraine"],
                "event_types": ["general_tension"],
            },
            {
                "title": "Taiwan export controls back in focus",
                "summary": "Chip supply chain jitters return.",
                "published_at": "2026-03-08T08:00:00Z",
                "geopolitics": ["taiwan"],
                "event_types": ["sanctions"],
            },
        ]
    }

    monkeypatch.setattr(judge_endpoint_service, "load_json", lambda key: news_feed if key == "news_feed" else {})

    payload = asyncio.run(
        judge_endpoint_service.get_judge_geopolitical_risk_graph_payload(
            region="ukraine",
            limit=5,
        )
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["filters_applied"]["region"] == "ukraine"
    assert data["stats"]["regions_detected"] == 2
    assert data["traceability"] == {
        "schema_version": "judge_source_trace_v1",
        "weighted_by": "freshness_decay",
        "freshness_unit": "hours",
        "source_trace_count": 3,
    }
    assert data["nodes"][0]["id"] == "ukraine"
    assert data["nodes"][0]["escalation_band"] in {"high", "critical"}
    assert data["nodes"][0]["source_trace"][0]["publisher"] == "unknown"
    assert data["nodes"][0]["source_trace"][0]["freshness_hours"] is not None
    assert any(edge["target"] == "sanctions" for edge in data["edges"])
    assert data["edges"][0]["source_trace"][0]["event"] == "sanctions"
    assert data["edges"][0]["source_trace"][0]["weight"] > 0
    assert data["alerts"][0]["region"] == "ukraine"


def test_geopolitical_risk_graph_payload_returns_never_empty_fallback(monkeypatch):
    def _boom(_key: str):
        raise RuntimeError("snapshot unavailable")

    monkeypatch.setattr(judge_endpoint_service, "load_json", _boom)

    payload = asyncio.run(
        judge_endpoint_service.get_judge_geopolitical_risk_graph_payload(
            region=None,
            limit=3,
        )
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert data["nodes"] == []
    assert data["edges"] == []
    assert data["alerts"] == []
    assert payload["status"] == "degraded"
    assert data["message"] == "Geopolitical risk graph unavailable; fallback returned."


def test_geopolitical_risk_graph_payload_limits_alerts_to_returned_nodes(monkeypatch):
    news_feed = {
        "articles": [
            {
                "title": "Ukraine conflict intensifies",
                "summary": "New military activity raises sanctions risk.",
                "published_at": "2026-03-10T10:00:00Z",
                "geopolitics": ["ukraine"],
                "event_types": ["sanctions", "military"],
            },
            {
                "title": "Taiwan tensions hit chip routes",
                "summary": "Export control chatter returns across the region.",
                "published_at": "2026-03-10T09:00:00Z",
                "geopolitics": ["taiwan"],
                "event_types": ["sanctions", "export_controls"],
            },
        ]
    }

    monkeypatch.setattr(judge_endpoint_service, "load_json", lambda key: news_feed if key == "news_feed" else {})

    payload = asyncio.run(
        judge_endpoint_service.get_judge_geopolitical_risk_graph_payload(
            region=None,
            limit=1,
        )
    )

    assert payload["ok"] is True
    data = payload["data"]
    assert len(data["nodes"]) == 1
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["region"].lower() == data["nodes"][0]["id"]
    assert data["stats"]["alerts_count"] == 1
