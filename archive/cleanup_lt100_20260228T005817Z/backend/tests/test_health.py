"""
Tests pour l'endpoint /api/health
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import create_app


@pytest.fixture
def client():
    """Fixture pour le client de test FastAPI"""
    app = create_app()
    return TestClient(app)


def test_health_returns_ok_status(client):
    """Test que l'endpoint /api/health retourne un statut HTTP 200"""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_response_format(client):
    """Test que la réponse contient bien les champs 'status' et 'version'"""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data


def test_health_status_value(client):
    """Test que le champ status est égal à 'ok'"""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "ok"


def test_health_version_value(client):
    """Test que le champ version est égal à '1.0.0'"""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["version"] == "1.0.0"


def test_health_multiple_requests(client):
    """Test la cohérence de la réponse lors de plusieurs appels successifs"""
    for _ in range(3):
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data


def test_health_response_time(client):
    """Test que l'endpoint répond dans un délai raisonnable (< 100ms)"""
    import time
    
    start_time = time.time()
    response = client.get("/api/health")
    elapsed = (time.time() - start_time) * 1000  # Convertir en millisecondes
    
    assert response.status_code == 200
    assert elapsed < 100  # Moins de 100ms