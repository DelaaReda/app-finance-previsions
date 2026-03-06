from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "fc_doctor.sh"


class DoctorJsonContractTests(unittest.TestCase):
    def test_doctor_json_contract_keys(self) -> None:
        cp = subprocess.run(
            ["bash", str(SCRIPT), "--json"],
            text=True,
            capture_output=True,
            check=False,
            cwd=str(ROOT),
        )
        # Doctor can return non-zero based on runtime state; contract still must be valid JSON.
        payload = json.loads((cp.stdout or "").strip() or "{}")

        self.assertIn("status", payload)
        self.assertIn("generated_at", payload)
        self.assertIn("checks", payload)
        self.assertIn("meta", payload)

        self.assertIn(payload["status"], {"ok", "degraded", "error"})

        checks = payload["checks"]
        self.assertIn("workspace_root", checks)
        self.assertIn("scheduler_authority", checks)
        self.assertIn("sessions", checks)
        self.assertIn("locks", checks)
        self.assertIn("queue_workboard", checks)
        self.assertIn("providers", checks)

        workspace = checks["workspace_root"]
        self.assertIn("canonical", workspace)
        self.assertIn("exists", workspace)
        self.assertIn("writable", workspace)

        sessions = checks["sessions"]
        self.assertIn("expected_core", sessions)
        self.assertIn("missing_core", sessions)
        self.assertIn("sessions", sessions)

        meta = payload["meta"]
        self.assertEqual(meta.get("schema_version"), "doctor.v1")
        self.assertIsInstance(meta.get("duration_ms"), int)


if __name__ == "__main__":
    unittest.main()
