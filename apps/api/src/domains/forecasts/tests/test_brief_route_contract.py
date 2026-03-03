from fastapi.testclient import TestClient

from api.main import create_app
from storage import io as storage_io


def _client() -> TestClient:
    return TestClient(create_app())


def test_brief_daily_contract_includes_macro_and_sector_and_short_summary(monkeypatch):
    snapshot = {
        "data": {
            "daily": {
                "title": "Brief quotidien",
                "summary": "mot " * 250,
                "market_sentiment": "MIXED",
                "top_signals": [],
                "top_risks": [],
                "picks": [],
                "macro_signals": [
                    {"topic": "Fed", "state": "neutral", "score": 0.1, "confidence": 0.8},
                ],
                "sector_rotation": {
                    "top": [{"sector": "or", "momentum": 0.7, "direction": "up"}],
                    "bottom": [{"sector": "energie", "momentum": -0.4, "direction": "down"}],
                },
                "sources": ["tests"],
                "generated_at": "2026-03-01T10:00:00Z",
                "freshness": "fresh",
                "source": ["test_fixture"],
            }
        }
    }

    monkeypatch.setattr(storage_io, "load_json", lambda _key: snapshot)

    client = _client()
    response = client.get("/api/brief/daily")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert isinstance(data.get("macro_signals"), list)
    assert isinstance(data.get("sector_rotation"), dict)
    assert isinstance(data["sector_rotation"].get("top"), list)
    assert isinstance(data["sector_rotation"].get("bottom"), list)

    summary_words = len(str(data.get("summary", "")).split())
    assert summary_words <= 200
