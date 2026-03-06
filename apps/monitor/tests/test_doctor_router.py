from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.monitor.src.api import create_doctor_router


def test_doctor_router_routes():
    app = FastAPI()

    def _snapshot(refresh: bool):
        return {"status": "ok", "refresh": refresh}

    app.include_router(create_doctor_router(_snapshot))
    c = TestClient(app)
    assert c.get("/api/doctor").status_code == 200
    assert c.get("/api/doctor?refresh=1").json()["refresh"] is True
    assert c.get("/api/doctor/latest").status_code == 200
