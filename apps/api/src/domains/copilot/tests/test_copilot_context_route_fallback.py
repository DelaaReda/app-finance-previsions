import sys
from pathlib import Path

from fastapi.testclient import TestClient

SRC_PATH = Path(__file__).resolve().parents[3]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from api.main import create_app
from domains.copilot.application import copilot_service
from storage import io as storage_io


def _client() -> TestClient:
    app = create_app()
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()
    return TestClient(app)


def test_copilot_context_route_fallback_keeps_brief_and_entry_points(monkeypatch):
    async def _raise_context_error(*_args, **_kwargs):
        raise RuntimeError("copilot context unavailable")

    fallback_brief = {
        "summary": "No daily brief available yet.",
        "market_sentiment": "UNKNOWN",
        "top_signals": [],
        "top_risks": [],
        "macro_signals": [],
        "sector_rotation": {"top": [], "bottom": []},
        "generated_at": "2026-03-09T06:00:00Z",
        "freshness": "2026-03-09T06:00:00Z",
        "source": ["copilot_daily_brief_fallback"],
    }
    fallback_entry_points = [
        {
            "id": "brief_of_day",
            "kind": "open",
            "label": "Brief du jour",
            "target": "/brief/daily",
        },
        {
            "id": "ask_copilot",
            "kind": "ask",
            "label": "Poser une question",
            "target": "/copilot/ask",
        },
    ]

    monkeypatch.setattr(copilot_service, "build_context_payload", _raise_context_error)
    monkeypatch.setattr(copilot_service, "_load_daily_brief_payload", lambda: dict(fallback_brief))
    monkeypatch.setattr(copilot_service, "_build_copilot_entry_points", lambda scope=None: [dict(item) for item in fallback_entry_points])
    monkeypatch.setattr(storage_io, "load_json", lambda _key: None)

    client = _client()
    response = client.get("/api/copilot/context")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert data.get("note") == "Market context service temporarily unavailable."

    daily_brief = data.get("daily_brief") or {}
    assert "No daily brief available yet." in (daily_brief.get("summary") or "")
    assert "copilot_daily_brief_fallback" in (daily_brief.get("source") or [])

    entry_points = data.get("entry_points") or []
    assert [item.get("id") for item in entry_points[:2]] == ["brief_of_day", "ask_copilot"]
    assert [item.get("kind") for item in entry_points[:2]] == ["open", "ask"]

    copilot_start = data.get("copilot_start") or {}
    assert copilot_start.get("brief_of_day", {}).get("summary") == "No daily brief available yet."
    assert [item.get("id") for item in copilot_start.get("ask", [])] == [
        "portfolio_today",
        "market_theme",
        "nvda_memo",
    ]
    assert [item.get("id") for item in copilot_start.get("open", [])] == [
        "market",
        "opportunities",
        "copilot",
    ]


def test_copilot_context_route_passes_scope_tickers_to_service(monkeypatch):
    captured = {}

    async def _fake_build_context_payload(*_args, **kwargs):
        captured["scope"] = kwargs.get("scope")
        return {
            "daily_brief": {
                "summary": "Scoped brief ready.",
                "source": ["copilot_context_test"],
            },
            "entry_points": [],
            "copilot_start": {},
            "scope_tickers": kwargs.get("scope", {}).get("tickers", []),
        }

    monkeypatch.setattr(copilot_service, "build_context_payload", _fake_build_context_payload)

    client = _client()
    response = client.get("/api/copilot/context?tickers=nvda&tickers=msft")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    assert captured.get("scope") == {"tickers": ["NVDA", "MSFT"]}
    assert payload.get("data", {}).get("scope_tickers") == ["NVDA", "MSFT"]


def test_copilot_context_route_fallback_keeps_scope_tickers_in_copilot_start(monkeypatch):
    async def _raise_context_error(*_args, **_kwargs):
        raise RuntimeError("copilot context unavailable")

    monkeypatch.setattr(copilot_service, "build_context_payload", _raise_context_error)
    monkeypatch.setattr(
        copilot_service,
        "_load_daily_brief_payload",
        lambda: {
            "summary": "Fallback daily brief.",
            "market_sentiment": "MIXED",
            "top_signals": [],
            "top_risks": [],
            "macro_signals": [],
            "sector_rotation": {"top": [], "bottom": []},
            "generated_at": "2026-03-09T06:00:00Z",
            "freshness": "2026-03-09T06:00:00Z",
            "source": ["copilot_daily_brief_fallback"],
        },
    )
    monkeypatch.setattr(storage_io, "load_json", lambda _key: None)

    client = _client()
    response = client.get("/api/copilot/context?tickers=nvda&tickers=msft")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True

    data = payload.get("data") or {}
    assert data.get("scope_tickers") == ["NVDA", "MSFT"]
    assert data.get("note") == "Market context service temporarily unavailable."

    copilot_start = data.get("copilot_start") or {}
    assert copilot_start.get("brief_of_day", {}).get("summary") == "Fallback daily brief."
    assert [item.get("id") for item in copilot_start.get("ask", [])] == [
        "portfolio_today",
        "market_theme",
        "nvda_memo",
    ]
    assert copilot_start.get("ask", [])[0].get("prefill", {}).get("tickers") == ["MSFT", "NVDA"]


def test_copilot_start_route_is_mounted_in_runtime_app(monkeypatch):
    captured = {}

    async def _fake_build_context_payload(*_args, **kwargs):
        captured["scope"] = kwargs.get("scope")
        return {
            "copilot_start": {
                "brief_of_day": {
                    "summary": "Daily brief ready.",
                    "generated_at": "2026-03-09T10:00:00Z",
                    "freshness": "2026-03-09T10:00:00Z",
                    "source": ["copilot_start_runtime_test"],
                },
                "ask": [
                    {"id": "portfolio_today", "target": "/copilot/ask"},
                ],
                "open": [
                    {"id": "brief_of_day", "target": "/brief/daily"},
                    {"id": "open_copilot", "target": "/copilot"},
                ],
            }
        }

    monkeypatch.setattr(copilot_service, "build_context_payload", _fake_build_context_payload)

    client = _client()
    response = client.get("/api/copilot/start?tickers=nvda&tickers=msft&tickers=NVDA")

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    assert captured.get("scope") == {"tickers": ["NVDA", "MSFT"]}

    data = payload.get("data") or {}
    assert data.get("brief_of_day", {}).get("summary") == "Daily brief ready."
    assert [item.get("id") for item in data.get("ask", [])] == ["portfolio_today"]
    assert [item.get("id") for item in data.get("open", [])] == [
        "open_msft",
        "open_nvda",
        "brief_of_day",
        "open_copilot",
    ]
    # Tickers are normalized (sorted alphabetically)
    assert sorted(data.get("filters_applied", {}).get("tickers", [])) == ["MSFT", "NVDA"]
    assert data.get("stats") == {"ask_count": 1, "open_count": 4}
    assert sorted(data.get("scope_tickers")) == ["MSFT", "NVDA"]
    assert "copilot_start_route" in (data.get("source") or [])
