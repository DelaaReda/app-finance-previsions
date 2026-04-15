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
SPEC = importlib.util.spec_from_file_location("fc_planner_guardian", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["fc_planner_guardian"] = MODULE
SPEC.loader.exec_module(MODULE)


compute_score = MODULE.compute_score
build_prompt_patches = MODULE.build_prompt_patches


class PlannerGuardianTests(unittest.TestCase):
    def test_missing_dependency_policy_without_inter_batch_dependency_is_not_flagged(self) -> None:
        outcome = compute_score(
            {"STATUS": "ACTIVE", "DELTA": "PROGRESS", "BLOCKER_ID": "none"},
            {
                "task_update": "claim",
                "planner_artifact": "artifact://planner",
                "stream_id": "VB-04",
                "task_id": "VB-04-PLAN",
                "batch_dependency_policy": "single_batch",
            },
            {"queue_has_ready": 0, "workboard_role_has_work": 1, "workboard_role_has_in_progress": 0, "planner_batch_runway_short": 0},
            {},
        )
        self.assertNotIn("dependency_policy_not_enforced", outcome["issues"])

    def test_inter_batch_dependency_without_single_batch_policy_is_flagged(self) -> None:
        outcome = compute_score(
            {"STATUS": "ACTIVE", "DELTA": "PROGRESS", "BLOCKER_ID": "none"},
            {
                "task_update": "claim",
                "planner_artifact": "artifact://planner",
                "stream_id": "VB-04",
                "task_id": "VB-04-PLAN",
                "batch_depends_on": "VB-03",
            },
            {"queue_has_ready": 0, "workboard_role_has_work": 1, "workboard_role_has_in_progress": 0, "planner_batch_runway_short": 0},
            {},
        )
        self.assertIn("inter_batch_dependency_detected", outcome["issues"])
        self.assertIn("dependency_policy_not_enforced", outcome["issues"])

    def test_build_prompt_patches_emits_novelty_target_patch_for_hard_guard(self) -> None:
        patches = build_prompt_patches(
            ["delivery_value_insufficient"],
            {
                "planner_hard_guard_active": True,
                "planner_hard_guard_reason": "stagnation_requires_novelty_target",
                "novelty_target_workflow": {"required_fields": ["novelty_target", "user_visible_delta"]},
            },
            {},
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertIn("novelty_target_first", patch_ids)

    def test_build_prompt_patches_emits_follow_active_task_patch(self) -> None:
        patches = build_prompt_patches(
            ["planner_orchestrator_admin_route_mismatch"],
            {
                "active_task_id": "BATCH-84-ADMIN-01",
                "active_task_role": "admin",
                "active_task_state": "IN_PROGRESS",
            },
            {},
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertIn("follow_canonical_active_task", patch_ids)


if __name__ == "__main__":
    unittest.main()
