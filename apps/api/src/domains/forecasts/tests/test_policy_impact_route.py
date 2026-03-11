from fastapi import FastAPI
from fastapi.testclient import TestClient

from domains.forecasts.api import forecasts as forecasts_route
from domains.forecasts.application import global_signal_mesh_service


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(forecasts_route.router)
    return TestClient(app)


def test_policy_impact_contract_extracts_status_jurisdiction_and_sector(monkeypatch):
    global_signal_mesh_service._POLICY_IMPACT_RESPONSE_CACHE.clear()
    client = _client()
    news_snapshot = {
        "articles": [
            {
                "id": "policy-1",
                "title": "US Congress proposes AI disclosure bill effective on 2026-06-01",
                "summary": "The proposed law would tighten disclosure requirements for cloud and semiconductor firms.",
                "source": "policy_wire",
                "timestamp": "2026-03-10T09:00:00Z",
                "tickers": ["NVDA", "MSFT"],
            },
            {
                "id": "policy-2",
                "title": "European Commission adopted new banking capital rule",
                "summary": "Banks in the European Union face updated lending compliance rules.",
                "source": "eu_policy",
                "timestamp": "2026-03-10T10:00:00Z",
                "tickers": ["SAN", "BNP"],
            },
        ]
    }

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: news_snapshot)

    response = client.get("/forecasts/policy-impact?limit=5")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["engine_id"] == "policy_change_impact_v1"
    assert data["stats"]["policy_article_count"] == 2
    assert data["stats"]["returned_event_count"] == 2
    assert data["timeline"]["proposed_count"] == 1
    assert data["timeline"]["adopted_count"] == 1
    assert {event["jurisdiction"] for event in data["events"]} == {"US", "EU"}
    assert all(event["status"] in {"proposed", "adopted", "effective", "monitoring"} for event in data["events"])
    assert all(isinstance(event["sectors"], list) and event["sectors"] for event in data["events"])
    assert data["provenance"]["fallback_used"] is False


def test_policy_impact_cache_and_debug_bypass(monkeypatch):
    global_signal_mesh_service._POLICY_IMPACT_RESPONSE_CACHE.clear()
    client = _client()
    news_snapshot = {
        "articles": [
            {
                "id": "policy-1",
                "title": "UK Parliament adopted new energy market rule",
                "summary": "The policy changes electricity market oversight.",
                "source": "uk_policy",
                "timestamp": "2026-03-10T11:00:00Z",
                "tickers": ["SHEL"],
            }
        ]
    }

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: news_snapshot)

    first = client.get("/forecasts/policy-impact?jurisdiction=UK")
    second = client.get("/forecasts/policy-impact?jurisdiction=UK")
    debug = client.get("/forecasts/policy-impact?jurisdiction=UK&debug=true")

    assert first.status_code == 200
    assert second.status_code == 200
    assert debug.status_code == 200
    assert first.json()["data"]["cache"]["hit"] is False
    assert second.json()["data"]["cache"]["hit"] is True
    assert debug.json()["data"]["cache"]["hit"] is False
    assert debug.json()["data"]["debug_pipeline"]["cache_bypassed"] is True
