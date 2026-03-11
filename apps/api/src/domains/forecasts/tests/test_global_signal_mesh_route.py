from fastapi.testclient import TestClient

from api.main import create_app


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

