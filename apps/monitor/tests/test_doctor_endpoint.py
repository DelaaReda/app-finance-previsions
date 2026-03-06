from __future__ import annotations

import unittest

from apps.monitor.api.http import build_monitor_router


class MonitorDoctorEndpointTests(unittest.TestCase):
    def test_doctor_endpoints_exposed_by_monitor_api_layer(self) -> None:
        def _status():
            return {"health": "OK"}

        def _diag():
            return {"status": "ok"}

        def _doctor(refresh: int):
            return {"status": "ok", "refresh": int(refresh)}

        def _doctor_latest():
            return {"status": "ok", "latest": True}

        router = build_monitor_router(
            status_handler=_status,
            runtime_diagnostics_handler=_diag,
            doctor_handler=_doctor,
            doctor_latest_handler=_doctor_latest,
        )
        endpoints = {
            route.path: route.endpoint
            for route in router.routes
            if hasattr(route, "path") and hasattr(route, "endpoint")
        }
        self.assertIn("/api/status", endpoints)
        self.assertIn("/api/runtime-diagnostics", endpoints)
        self.assertIn("/api/doctor", endpoints)
        self.assertIn("/api/doctor/latest", endpoints)

        self.assertEqual(endpoints["/api/status"]().get("health"), "OK")
        self.assertEqual(endpoints["/api/runtime-diagnostics"]().get("status"), "ok")
        self.assertEqual(endpoints["/api/doctor"](refresh=1).get("refresh"), 1)
        self.assertTrue(endpoints["/api/doctor/latest"]().get("latest"))


if __name__ == "__main__":
    unittest.main()
