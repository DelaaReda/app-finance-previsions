from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "browser_smoke.py"
SPEC = importlib.util.spec_from_file_location("fc_browser_smoke", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_browser_smoke"] = MODULE
SPEC.loader.exec_module(MODULE)


run_browser_smoke = MODULE.run_browser_smoke


class BrowserSmokeTests(unittest.TestCase):
    def test_run_browser_smoke_writes_proof_and_copies_screenshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            screenshot_src = root / "source.png"
            screenshot_src.write_text("png", encoding="utf-8")

            payloads = [
                (0, {}, ""),  # start
                (0, {"running": True, "cdpReady": True}, ""),  # status
                (0, {"targetId": "abc123", "url": "https://example.com/"}, ""),  # open
                (0, {"ok": True}, ""),  # wait
                (0, {"snapshot": [{"ref": "1", "text": "hello"}]}, ""),  # snapshot
                (0, {"items": []}, ""),  # console
                (0, {"items": []}, ""),  # errors
                (0, {"path": str(screenshot_src), "targetId": "abc123", "url": "https://example.com/"}, ""),  # screenshot
                (0, {"ok": True}, ""),  # close
            ]

            with patch.object(MODULE, "_run_browser", side_effect=payloads):
                proof = run_browser_smoke(
                    url="https://example.com/",
                    root=root,
                    label="monitor-home",
                    timeout_seconds=15,
                )

            proof_path = Path(proof["proof_path"])
            self.assertTrue(proof_path.exists())
            on_disk = json.loads(proof_path.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["proof_kind"], "openclaw_browser_smoke")
            self.assertTrue(Path(proof["screenshot_copy"]).exists())


if __name__ == "__main__":
    unittest.main()
