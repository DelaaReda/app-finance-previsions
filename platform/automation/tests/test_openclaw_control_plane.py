from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "openclaw_control_plane.py"
SPEC = importlib.util.spec_from_file_location("fc_openclaw_control_plane", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_openclaw_control_plane"] = MODULE
SPEC.loader.exec_module(MODULE)


sync_control_plane = MODULE.sync_control_plane


class OpenClawControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config_path = self.root / ".openclaw" / "openclaw.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "agents": {
                "defaults": {
                    "model": {"primary": "openai-codex/gpt-5.2"},
                    "workspace": "/home/venom/shared/analyse-financiere",
                },
                "list": [
                    {"id": "main"},
                    {"id": "planner"},
                    {"id": "admin-agents"},
                    {"id": "dev"},
                    {"id": "planner_dev_probe_local"},
                ],
            }
        }
        self.config_path.write_text(json.dumps(payload), encoding="utf-8")
        for agent_id in ("admin-agents", "dev", "planner_dev_probe_local"):
            (self.root / ".openclaw" / "agents" / agent_id / "agent").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_sync_control_plane_prunes_legacy_agents_and_aligns_defaults(self) -> None:
        result = sync_control_plane(
            config_path=self.config_path,
            workspace="/home/venom/analyse-financiere",
            primary_model="codex-cli/gpt-5.4",
            apply=True,
            prune_dirs=True,
            reset_kept_dirs=False,
        )
        self.assertTrue(result["ok"])
        self.assertIn("admin-agents", result["removed_ids"])
        self.assertIn("dev", result["removed_ids"])
        reloaded = json.loads(self.config_path.read_text(encoding="utf-8"))
        defaults = reloaded["agents"]["defaults"]
        self.assertEqual(defaults["model"]["primary"], "codex-cli/gpt-5.4")
        self.assertIn("/home/venom/analyse-financiere/logs-codex-runs/openclaw-control-plane/default", defaults["workspace"])
        ids = [row["id"] for row in reloaded["agents"]["list"]]
        self.assertEqual(ids, ["main", "planner", "adminapp-codex", "clawsentinel"])
        self.assertTrue(reloaded["agents"]["list"][1]["workspace"].endswith("/openclaw-control-plane/planner"))
        self.assertFalse((self.root / ".openclaw" / "agents" / "admin-agents").exists())
        self.assertFalse((self.root / ".openclaw" / "agents" / "dev").exists())

    def test_sync_control_plane_can_reset_kept_agent_dirs(self) -> None:
        for agent_id in ("planner", "adminapp-codex", "clawsentinel"):
            (self.root / ".openclaw" / "agents" / agent_id / "agent").mkdir(parents=True, exist_ok=True)
        result = sync_control_plane(
            config_path=self.config_path,
            workspace="/home/venom/analyse-financiere",
            primary_model="codex-cli/gpt-5.4",
            apply=True,
            prune_dirs=False,
            reset_kept_dirs=True,
        )
        self.assertIn("planner", result["reset_dirs"])
        self.assertFalse((self.root / ".openclaw" / "agents" / "planner").exists())


if __name__ == "__main__":
    unittest.main()
