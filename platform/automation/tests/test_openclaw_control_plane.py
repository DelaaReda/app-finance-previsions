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

MODULE_PATH = AUTOMATION_DIR / "operator" / "openclaw" / "openclaw_control_plane.py"
SPEC = importlib.util.spec_from_file_location("fc_openclaw_control_plane", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_openclaw_control_plane"] = MODULE
SPEC.loader.exec_module(MODULE)


sync_control_plane = MODULE.sync_control_plane
validate_bridge = MODULE.validate_bridge


class OpenClawControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config_path = self.root / ".openclaw" / "openclaw.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        skills_root = self.root / "skills"
        for skill_name in MODULE.CANONICAL_OPENCLAW_SKILLS:
            skill_dir = skills_root / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# {skill_name}\n", encoding="utf-8")
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
        workspace = str(self.root)
        with patch.object(MODULE, "CANONICAL_MAIN_WORKSPACE", str(self.root)):
            result = sync_control_plane(
                config_path=self.config_path,
                workspace=workspace,
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
        self.assertIn("/logs-codex-runs/openclaw-control-plane/default", defaults["workspace"])
        self.assertEqual(defaults["cliBackends"]["codex-cli"]["command"], "codex")
        self.assertEqual(
            defaults["cliBackends"]["codex-cli"]["resumeArgs"],
            ["exec", "resume", "{sessionId}", "--skip-git-repo-check"],
        )
        ids = [row["id"] for row in reloaded["agents"]["list"]]
        self.assertEqual(ids, ["main", "planner", "adminapp-codex", "clawsentinel"])
        self.assertTrue(reloaded["agents"]["list"][1]["workspace"].endswith("/openclaw-control-plane/planner"))
        self.assertFalse((self.root / ".openclaw" / "agents" / "admin-agents").exists())
        self.assertFalse((self.root / ".openclaw" / "agents" / "dev").exists())
        for skill_name in MODULE.CANONICAL_OPENCLAW_SKILLS:
            planner_skill = self.root / "logs-codex-runs" / "openclaw-control-plane" / "planner" / "skills" / skill_name
            self.assertTrue(planner_skill.is_symlink(), planner_skill)
        for skill_name in MODULE.CANONICAL_OPENCLAW_SKILLS:
            main_skill = self.root / "skills" / skill_name
            self.assertTrue(main_skill.exists(), main_skill)

    def test_sync_control_plane_can_reset_kept_agent_dirs(self) -> None:
        for agent_id in ("planner", "adminapp-codex", "clawsentinel"):
            (self.root / ".openclaw" / "agents" / agent_id / "agent").mkdir(parents=True, exist_ok=True)
        result = sync_control_plane(
            config_path=self.config_path,
            workspace=str(self.root),
            primary_model="codex-cli/gpt-5.4",
            apply=True,
            prune_dirs=False,
            reset_kept_dirs=True,
        )
        self.assertIn("planner", result["reset_dirs"])
        self.assertFalse((self.root / ".openclaw" / "agents" / "planner").exists())

    def test_validate_bridge_requires_two_successful_attempts(self) -> None:
        class Proc:
            def __init__(self, rc: int, stdout: str, stderr: str = "") -> None:
                self.returncode = rc
                self.stdout = stdout
                self.stderr = stderr

        with patch.object(MODULE.subprocess, "run", side_effect=[Proc(0, '{"result":{"payloads":[{"text":"OK"}]}}'), Proc(0, '{"result":{"payloads":[{"text":"OK"}]}}')]):
            result = validate_bridge("planner", 30)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["attempts"]), 2)


if __name__ == "__main__":
    unittest.main()
