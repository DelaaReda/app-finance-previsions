import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_macro_series():
    response = client.get("/api/macro/series?ids=SP500")
    assert response.status_code == 200
    data = response.json()
    assert "series" in data
    assert isinstance(data["series"], list)
    if data["series"]:
        assert "id" in data["series"][0]
        assert "points" in data["series"][0]