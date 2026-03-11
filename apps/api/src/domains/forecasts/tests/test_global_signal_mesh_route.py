from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import create_app
from api.routes import forecasts as forecasts_api
from domains.forecasts.application.global_signal_mesh_service import (
    _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE,
    _INSIDER_BEHAVIOR_RESPONSE_CACHE,
    _MACRO_REGIME_RESPONSE_CACHE,
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
    assert "freshness_expected_counts" in data["observability"]
    assert data["observability"]["nominal_coverage_ratio"] > 0
    assert data["provenance"]["source"] == data["source"]
    assert data["provenance"]["fallback_used"] is False

    first = data["sources_catalog"][0]
    assert first["source_id"].startswith("SRC-")
    assert first["free_tier_status"] == "NO_KEY"
    assert first["license_class"]
    assert first["license_or_terms_url"].startswith("https://")
    assert isinstance(first["fallback_source_ids"], list)
    assert first["health"]["nominal_status"] in {"nominal", "fallback_only"}
    assert first["health"]["has_fallback"] == bool(first["fallback_source_ids"])
    assert first["health"]["freshness_expected"] == first["freshness_expected"]
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


def test_global_signal_mesh_fallback_keeps_observability_contract(monkeypatch):
    _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE.clear()

    monkeypatch.setattr(
        forecasts_api,
        "build_global_signal_mesh_payload",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    app = FastAPI()
    app.include_router(forecasts_api.router)
    client = TestClient(app)

    response = client.get("/forecasts/global-signal-mesh")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["provenance"]["fallback_used"] is True
    assert data["observability"] == {
        "freshness_expected_counts": {},
        "nominal_coverage_ratio": 0.0,
        "nominal_sources_without_fallback": [],
    }


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


def test_insider_behavior_returns_conservative_placeholder_when_snapshot_missing(monkeypatch):
    client = _client()
    _INSIDER_BEHAVIOR_RESPONSE_CACHE.clear()

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: {})

    response = client.get("/api/forecasts/insider-behavior?tickers=NVDA&limit=5")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["stats"]["snapshot_row_count"] == 0
    assert data["stats"]["returned_signal_count"] == 1
    assert data["provenance"]["fallback_used"] is True
    assert "no_ownership_snapshot_rows" in data["warnings"]
    assert data["signals"][0]["ticker"] == "NVDA"
    assert data["signals"][0]["stance"] == "insufficient_evidence"
    assert data["signals"][0]["uncertainty"]["level"] == "high"


def test_macro_regime_hierarchy_contract_exposes_world_continent_country(monkeypatch):
    client = _client()
    _MACRO_REGIME_RESPONSE_CACHE.clear()

    news_snapshot = {
        "articles": [
            {
                "title": "Global growth stabilizes as rate cuts near",
                "summary": "World demand stays positive but fragile.",
                "source": "macro_wire",
                "timestamp": "2026-03-10T09:00:00Z",
            },
            {
                "title": "North America capex cycle remains resilient",
                "summary": "Regional investment and consumer demand stay firm.",
                "source": "regional_wire",
                "timestamp": "2026-03-10T10:00:00Z",
            },
            {
                "title": "US inflation cools while labor demand stays healthy",
                "summary": "The United States keeps a soft landing bias.",
                "source": "country_wire",
                "timestamp": "2026-03-10T11:00:00Z",
            },
        ]
    }

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: news_snapshot)
    monkeypatch.setattr(
        global_signal_mesh_service,
        "_llm_macro_narrative",
        lambda levels, horizon: {"used": False, "status": "unavailable"},
    )

    response = client.get("/api/forecasts/macro-regime-hierarchy?country=US&continent=north_america")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["forecast_id"] == "macro_regime_hierarchy_v1"
    assert [level["scope"] for level in data["levels"]] == ["world", "continent", "country"]
    assert data["levels"][1]["entity"] == "north_america"
    assert data["levels"][2]["entity"] == "US"
    assert "pairs" in data["consistency"]
    assert data["stats"]["level_count"] == 3
    assert data["provenance"]["llm_used"] is False
    assert "llm_narrative_fallback" in data["warnings"]
    assert data["cache"]["hit"] is False


def test_macro_regime_hierarchy_cache_and_debug_pipeline(monkeypatch):
    client = _client()
    _MACRO_REGIME_RESPONSE_CACHE.clear()

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: {"articles": []})
    monkeypatch.setattr(
        global_signal_mesh_service,
        "_llm_macro_narrative",
        lambda levels, horizon: {
            "used": True,
            "status": "ok",
            "model": "test-model",
            "provider": "test-provider",
            "payload": {
                "summary": "LLM hierarchy summary",
                "regime_bias": "soft_landing_bias",
                "key_risks": ["policy repricing"],
                "consistency_call": "aligned",
            },
        },
    )

    first = client.get("/api/forecasts/macro-regime-hierarchy?country=US")
    second = client.get("/api/forecasts/macro-regime-hierarchy?country=US")
    debug = client.get("/api/forecasts/macro-regime-hierarchy?country=US&debug=true")

    assert first.status_code == 200
    assert second.status_code == 200
    assert debug.status_code == 200
    assert first.json()["data"]["cache"]["hit"] is False
    assert second.json()["data"]["cache"]["hit"] is True
    assert second.json()["data"]["narrative"]["summary"] == "LLM hierarchy summary"
    assert second.json()["data"]["provenance"]["llm_model"] == "test-model"
    assert debug.json()["data"]["cache"]["hit"] is False
    assert debug.json()["data"]["debug_pipeline"]["cache_bypassed"] is True
    assert debug.json()["data"]["debug_pipeline"]["llm_status"] == "ok"


def test_batch46_country_continent_world_forecast_coverage(monkeypatch):
    """BATCH-46-DEV-01: Validate hierarchical macro regime forecasts at all levels.
    
    Acceptance criteria:
    - Country, continent, world forecasts available with confidence
    - Contradictions flagged with consistency diagnostics
    - Free data source provenance attached
    """
    client = _client()
    _MACRO_REGIME_RESPONSE_CACHE.clear()

    news_snapshot = {
        "articles": [
            {
                "title": "Global growth stabilizes with disinflation progress",
                "summary": "World economy shows resilience despite geopolitical risks.",
                "source": "macro_wire",
                "timestamp": "2026-03-10T08:00:00Z",
            },
            {
                "title": "European recovery remains fragile amid energy concerns",
                "summary": "EU economy stabilizing from weak base with ECB policy support.",
                "source": "regional_wire",
                "timestamp": "2026-03-10T09:00:00Z",
            },
            {
                "title": "Germany industrial output shows soft patch",
                "summary": "German manufacturing faces headwinds from energy costs.",
                "source": "country_wire",
                "timestamp": "2026-03-10T10:00:00Z",
            },
        ]
    }

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: news_snapshot)
    monkeypatch.setattr(
        global_signal_mesh_service,
        "_llm_macro_narrative",
        lambda levels, horizon: {"used": False, "status": "unavailable"},
    )

    response = client.get("/api/forecasts/macro-regime-hierarchy?country=Germany&continent=europe")

    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["forecast_id"] == "macro_regime_hierarchy_v1"
    
    levels = data["levels"]
    assert len(levels) == 3
    
    scopes = [level["scope"] for level in levels]
    assert scopes == ["world", "continent", "country"]
    
    entities = [level["entity"] for level in levels]
    assert entities[0] == "world"
    assert entities[1] == "europe"
    assert entities[2] == "GERMANY"
    
    for level in levels:
        assert "regime" in level
        assert "confidence" in level
        assert isinstance(level["confidence"], float)
        assert 0.0 <= level["confidence"] <= 1.0
        assert "summary" in level
        assert "drivers" in level
        assert isinstance(level["drivers"], list)
        assert "risks" in level
        assert isinstance(level["risks"], list)
        assert "score" in level
        assert isinstance(level["score"], (int, float))
    
    consistency = data["consistency"]
    assert "has_contradictions" in consistency
    assert isinstance(consistency["has_contradictions"], bool)
    assert "pairs" in consistency
    assert isinstance(consistency["pairs"], list)
    assert "contradiction_count" in consistency
    assert isinstance(consistency["contradiction_count"], int)
    assert "alignment_status" in consistency
    assert consistency["alignment_status"] in {"aligned", "contradiction"}

    assert "confidence" in data
    assert isinstance(data["confidence"], float)
    assert 0.0 <= data["confidence"] <= 1.0

    narrative = data["narrative"]
    assert "summary" in narrative
    assert "regime_bias" in narrative
    assert "key_risks" in narrative
    assert "consistency_call" in narrative
    assert narrative["consistency_call"] in {"aligned", "contradiction"}
    
    assert data["stats"]["level_count"] == 3
    assert "news_signal_count" in data["stats"]
    assert "coverage_source_count" in data["stats"]
    assert data["stats"]["hierarchy_confidence"] == data["confidence"]
    
    provenance = data["provenance"]
    assert "source" in provenance
    assert "forecasts_macro_regime_hierarchy" in provenance["source"]
    assert "free_data_source_registry" in provenance["source"]
    assert "llm_used" in provenance
    assert "fallback_used" in provenance
    assert "sla" in provenance
    
    assert "warnings" in data
    assert isinstance(data["warnings"], list)
    assert "llm_narrative_fallback" in data["warnings"]
    
    assert data["cache"]["hit"] is False


def test_batch46_multi_country_forecast_consistency(monkeypatch):
    """BATCH-46-DEV-01: Verify forecasts work across multiple countries/continents."""
    client = _client()
    _MACRO_REGIME_RESPONSE_CACHE.clear()

    monkeypatch.setattr(global_signal_mesh_service, "load_json", lambda _key: {"articles": []})
    monkeypatch.setattr(
        global_signal_mesh_service,
        "_llm_macro_narrative",
        lambda levels, horizon: {"used": False, "status": "unavailable"},
    )

    test_cases = [
        ("US", "north_america", "United States"),
        ("CHINA", "asia", "China"),
        ("GERMANY", "europe", "Germany"),
        ("BRAZIL", "latin_america", "Brazil"),
        ("SOUTH AFRICA", "africa", "South Africa"),
    ]

    for country_code, expected_continent, country_name in test_cases:
        _MACRO_REGIME_RESPONSE_CACHE.clear()
        
        response = client.get(f"/api/forecasts/macro-regime-hierarchy?country={country_code}")
        
        assert response.status_code == 200, f"Failed for {country_name}"
        data = response.json()["data"]
        
        assert data["forecast_id"] == "macro_regime_hierarchy_v1"
        assert len(data["levels"]) == 3
        
        country_level = data["levels"][2]
        assert country_level["scope"] == "country"
        assert country_level["entity"] == country_code
        assert "regime" in country_level
        assert "confidence" in country_level
        assert 0.0 <= country_level["confidence"] <= 1.0
        
        continent_level = data["levels"][1]
        assert continent_level["scope"] == "continent"
        assert continent_level["entity"] == expected_continent
        
        world_level = data["levels"][0]
        assert world_level["scope"] == "world"
        assert world_level["entity"] == "world"
        
        assert "consistency" in data
        assert "has_contradictions" in data["consistency"]
