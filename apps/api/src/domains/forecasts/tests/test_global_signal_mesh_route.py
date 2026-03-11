from fastapi.testclient import TestClient

from api.main import create_app
from domains.forecasts.application.global_signal_mesh_service import (
    _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE,
    _INSIDER_BEHAVIOR_RESPONSE_CACHE,
    _POLICY_IMPACT_RESPONSE_CACHE,
    build_global_signal_mesh_payload,
)
from domains.forecasts.application import global_signal_mesh_service


def _client() -> TestClient:
    return TestClient(create_app())


def test_global_signal_mesh_contract_exposes_provenance_and_license_metadata():
    client = _client()

    response = client.get("/api/forecasts/global-signal-mesh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True

    data = payload["data"]
    assert data["mesh_id"] == "free_global_signal_mesh"
    assert data["stats"]["source_count"] >= 1
    assert data["stats"]["nominal_source_count"] >= 1
    assert "license_class_counts" in data["stats"]
    assert data["coverage"]["free_nominal_path_only"] is True
    assert data["provenance"]["source"] == data["source"]
    assert data["provenance"]["fallback_used"] is False

    first = data["sources_catalog"][0]
    assert first["source_id"].startswith("SRC-")
    assert first["free_tier_status"] == "NO_KEY"
    assert first["license_class"]
    assert first["license_or_terms_url"].startswith("https://")
    assert isinstance(first["fallback_source_ids"], list)
    assert first["provenance"]["registry_source"] == "FREE_DATA_SOURCE_KEY_MATRIX"


def test_global_signal_mesh_debug_bypasses_cache_and_can_include_non_nominal_sources():
    client = _client()

    response = client.get("/api/forecasts/global-signal-mesh?include_non_nominal=true&debug=true")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["filters_applied"]["include_non_nominal"] is True
    assert data["cache"]["hit"] is False
    assert data["debug_pipeline"]["cache_bypassed"] is True
    assert data["stats"]["source_count"] > data["stats"]["nominal_source_count"]


def test_global_signal_mesh_repeated_calls_return_cache_hit_for_same_params():
    client = _client()
    _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE.clear()

    first = client.get("/api/forecasts/global-signal-mesh")
    second = client.get("/api/forecasts/global-signal-mesh")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["cache"]["hit"] is False
    assert second.json()["data"]["cache"]["hit"] is True
    assert second.json()["data"]["stats"] == first.json()["data"]["stats"]


def test_global_signal_mesh_cache_returns_isolated_nested_payloads():
    _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE.clear()

    first = build_global_signal_mesh_payload()
    first["provenance"]["source"].append("mutated")
    first["sources_catalog"][0]["provenance"]["registry_source"] = "mutated"

    second = build_global_signal_mesh_payload()

    assert second["cache"]["hit"] is True
    assert second["provenance"]["source"] == [
        "forecasts_global_signal_mesh",
        "free_data_source_registry",
    ]
    assert second["sources_catalog"][0]["provenance"]["registry_source"] == (
        "FREE_DATA_SOURCE_KEY_MATRIX"
    )


def test_policy_impact_contract_extracts_status_jurisdiction_and_sector(monkeypatch):
    client = _client()
    _POLICY_IMPACT_RESPONSE_CACHE.clear()

    news_snapshot = {
        "articles": [
            {
                "id": "policy-1",
                "title": "US Congress advances AI disclosure bill effective on 2026-06-01",
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

    response = client.get("/api/forecasts/policy-impact?limit=5")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["engine_id"] == "policy_change_impact_v1"
    assert data["stats"]["policy_article_count"] == 2
    assert data["stats"]["returned_event_count"] == 2
    assert data["timeline"]["proposed_count"] == 1
    assert data["timeline"]["adopted_count"] == 1
    assert data["events"][0]["jurisdiction"] in {"US", "EU"}
    assert data["events"][0]["status"] in {"proposed", "adopted", "effective", "monitoring"}
    assert isinstance(data["events"][0]["sectors"], list)
    assert data["provenance"]["fallback_used"] is False


def test_policy_impact_cache_and_debug_bypass(monkeypatch):
    client = _client()
    _POLICY_IMPACT_RESPONSE_CACHE.clear()

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

    first = client.get("/api/forecasts/policy-impact?jurisdiction=UK")
    second = client.get("/api/forecasts/policy-impact?jurisdiction=UK")
    debug = client.get("/api/forecasts/policy-impact?jurisdiction=UK&debug=true")

    assert first.status_code == 200
    assert second.status_code == 200
    assert debug.status_code == 200
    assert first.json()["data"]["cache"]["hit"] is False
    assert second.json()["data"]["cache"]["hit"] is True
    assert debug.json()["data"]["cache"]["hit"] is False
    assert debug.json()["data"]["debug_pipeline"]["cache_bypassed"] is True


def test_insider_behavior_contract_exposes_uncertainty_guardrails_and_provenance(monkeypatch):
    client = _client()
    _INSIDER_BEHAVIOR_RESPONSE_CACHE.clear()

    ownership_snapshot = {
        "tickers": {
            "NVDA": {
                "ticker": "NVDA",
                "asof_utc": "2026-03-10T12:00:00Z",
                "sources_used": ["SEC EDGAR"],
                "insiders": {
                    "aggregates": {
                        "window_30d": {"buys": 4, "sells": 1, "net_trades": 3},
                        "window_90d": {"buys": 6, "sells": 2, "net_trades": 4},
                    }
                },
            },
            "TSLA": {
                "ticker": "TSLA",
                "asof_utc": "2026-03-10T12:00:00Z",
                "sources_used": ["SEC EDGAR"],
                "insiders": {
                    "aggregates": {
                        "window_30d": {"buys": 0, "sells": 0, "net_trades": 0},
                        "window_90d": {"buys": 0, "sells": 0, "net_trades": 0},
                    }
                },
            },
        }
    }

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: ownership_snapshot)

    response = client.get("/api/forecasts/insider-behavior?tickers=NVDA,TSLA&limit=5")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["engine_id"] == "insider_behavior_intelligence_v1"
    assert data["stats"]["snapshot_row_count"] == 2
    assert data["stats"]["returned_signal_count"] == 2
    assert data["guardrails"]["deterministic_language_allowed"] is False
    assert data["provenance"]["fallback_used"] is False
    assert data["signals"][0]["provenance"]["filing_source"] == "public_form4"
    assert data["signals"][0]["uncertainty"]["level"] in {"low", "medium", "high"}
    assert "should be combined with other layers" in data["signals"][0]["summary"]


def test_insider_behavior_cache_and_debug_bypass(monkeypatch):
    client = _client()
    _INSIDER_BEHAVIOR_RESPONSE_CACHE.clear()

    ownership_snapshot = {
        "rows": [
            {
                "ticker": "MSFT",
                "asof_utc": "2026-03-10T12:00:00Z",
                "insiders": {
                    "aggregates": {
                        "window_30d": {"buys": 1, "sells": 3, "net_trades": -2},
                        "window_90d": {"buys": 3, "sells": 5, "net_trades": -2},
                    }
                },
            }
        ]
    }

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: ownership_snapshot)

    first = client.get("/api/forecasts/insider-behavior?tickers=MSFT")
    second = client.get("/api/forecasts/insider-behavior?tickers=MSFT")
    debug = client.get("/api/forecasts/insider-behavior?tickers=MSFT&debug=true")

    assert first.status_code == 200
    assert second.status_code == 200
    assert debug.status_code == 200
    assert first.json()["data"]["cache"]["hit"] is False
    assert second.json()["data"]["cache"]["hit"] is True
    assert debug.json()["data"]["cache"]["hit"] is False
    assert debug.json()["data"]["debug_pipeline"]["cache_bypassed"] is True
