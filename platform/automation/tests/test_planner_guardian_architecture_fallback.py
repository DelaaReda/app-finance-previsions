from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION_DIR = ROOT / "platform" / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

MODULE_PATH = AUTOMATION_DIR / "planner_guardian.py"
SPEC = importlib.util.spec_from_file_location("fc_planner_guardian_arch_fallback", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_guardian_arch_fallback"] = MODULE
SPEC.loader.exec_module(MODULE)

compute_score = MODULE.compute_score


class PlannerGuardianArchitectureFallbackTests(unittest.TestCase):
    def test_architecture_check_paths_satisfy_architecture_traceability(self) -> None:
        outcome = compute_score(
            {"STATUS": "IN_PROGRESS", "DELTA": "DELIVERY", "BLOCKER_ID": "NONE"},
            {
                "task_update": "complete",
                "planner_artifact": "docs/ops/BATCH-86-ANALYSIS-ARCHITECTURE_AUDIT.md",
                "stream_id": "BATCH-86",
                "task_id": "BATCH-86-ANALYSIS",
                "batch_dependency_policy": "single_batch",
                "vision_alignment": "batch=BATCH-86; target=portfolio_first_brief_with_ranked_actions; impact=unlock_arch_with_canonical_reuse_boundaries",
                "architecture_check": (
                    "layer=apps/api+apps/web; imports_ok=yes; "
                    "path_target=apps/api/src/domains/copilot/api/copilot.py,"
                    "apps/api/src/domains/judge/application/judge_endpoint_service.py,"
                    "apps/web/src/domains/forecasts/components/widgets/copilot-panel.html"
                ),
            },
            {
                "queue_has_ready": 0,
                "workboard_role_has_work": 1,
                "workboard_role_has_in_progress": 1,
                "planner_batch_runway_short": 0,
            },
            {},
        )
        self.assertNotIn("missing_architecture_plan_ref", outcome["issues"])
        self.assertNotIn("missing_architecture_audit", outcome["issues"])
        self.assertNotIn("architecture_audit_missing_paths", outcome["issues"])


if __name__ == "__main__":
    unittest.main()
