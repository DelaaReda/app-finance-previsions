from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
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
parse_runtime_context = MODULE.parse_runtime_context
canonical_active_snapshot = MODULE.canonical_active_snapshot
summarize_contract_for_publication = MODULE.summarize_contract_for_publication
maybe_emit_directive = MODULE.maybe_emit_directive
update_streaks = MODULE.update_streaks
recommendations = MODULE.recommendations


class PlannerGuardianTests(unittest.TestCase):
    def test_parse_runtime_context_reads_top_level_counts(self) -> None:
        runtime = parse_runtime_context(
            "queue_has_ready=0 top_level_total=84 top_level_non_closed=0 top_level_ready=0 "
            "planner_batch_runway_short=1 workboard_role_has_work=0 workboard_role_has_in_progress=0"
        )
        self.assertEqual(runtime["top_level_total"], 84)
        self.assertEqual(runtime["top_level_non_closed"], 0)
        self.assertEqual(runtime["top_level_ready"], 0)

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
        patch = next(patch for patch in patches if patch["id"] == "follow_canonical_active_task")
        self.assertIn("planner_subagent_manager.py collect", patch["instruction"])
        self.assertIn("planner_runtime_actions.py handoff-ack|handoff-close", patch["instruction"])
        self.assertIn("debloque la lane active", patch["instruction"])
        self.assertNotIn("route bloquante", patch["instruction"])

    def test_api_wave_idle_runtime_prefers_dispatch_over_autobatch(self) -> None:
        patches = build_prompt_patches(
            ["planner_passive_forbidden_violation", "planner_autobatch_missing_when_idle"],
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "projection_decision_reason": "runtime_idle_no_active_cycle",
                "product_delivery_state": {
                    "phase": "idle_ready_for_next_batch",
                    "next_batch_eligible": True,
                    "api_wave": {
                        "enabled": True,
                        "dispatch_ready": True,
                        "current_endpoint": {"endpoint_id": "copilot_search"},
                    },
                },
            },
            {"ready_idle_streak": 3},
            {},
            {
                "queue_has_ready": 0,
                "workboard_role_has_work": 0,
                "workboard_role_has_in_progress": 0,
                "top_level_non_closed": 0,
            },
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertIn("dispatch_api_wave_now", patch_ids)
        self.assertNotIn("continue_api_wave_now", patch_ids)
        self.assertNotIn("open_next_batch_now", patch_ids)
        self.assertNotIn("claim_or_autobatch_now", patch_ids)

    def test_ready_downstream_patch_dispatches_instead_of_collecting(self) -> None:
        patches = build_prompt_patches(
            ["ready_but_none_task_update"],
            {
                "active_task_id": "BATCH-95-DEV-03",
                "active_task_role": "dev",
                "active_task_state": "READY_DEV",
            },
            {},
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertIn("follow_canonical_active_task", patch_ids)
        self.assertNotIn("claim_or_autobatch_now", patch_ids)
        patch = next(patch for patch in patches if patch["id"] == "follow_canonical_active_task")
        self.assertIn("planner_subagent_manager.py run", patch["instruction"])
        self.assertNotIn("planner_subagent_manager.py collect", patch["instruction"])
        self.assertNotIn("handoff-ack|handoff-close", patch["instruction"])
        self.assertIn("lane READY", patch["instruction"])

    def test_downstream_active_task_suppresses_claim_or_autobatch_patch(self) -> None:
        patches = build_prompt_patches(
            ["planner_passive_forbidden_violation"],
            {
                "active_task_id": "BATCH-84-ADMIN-01",
                "active_task_role": "admin",
                "active_task_state": "IN_PROGRESS",
            },
            {"ready_idle_streak": 4},
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertNotIn("claim_or_autobatch_now", patch_ids)

    def test_hard_guard_suppresses_claim_or_autobatch_patch(self) -> None:
        patches = build_prompt_patches(
            ["planner_passive_forbidden_violation", "delivery_value_insufficient"],
            {
                "planner_hard_guard_active": True,
                "planner_hard_guard_reason": "stagnation_requires_novelty_target",
                "novelty_target_workflow": {"required_fields": ["novelty_target", "user_visible_delta"]},
            },
            {"ready_idle_streak": 3},
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertIn("novelty_target_first", patch_ids)
        self.assertNotIn("claim_or_autobatch_now", patch_ids)

    def test_no_canonical_work_suppresses_claim_or_autobatch_patch(self) -> None:
        patches = build_prompt_patches(
            ["planner_passive_forbidden_violation", "planner_autobatch_missing_when_idle"],
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
            },
            {"ready_idle_streak": 3},
            {},
            {
                "queue_has_ready": 0,
                "workboard_role_has_work": 0,
                "workboard_role_has_in_progress": 0,
                "top_level_non_closed": 0,
            },
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertNotIn("claim_or_autobatch_now", patch_ids)

    def test_downstream_collect_tick_does_not_require_planner_close_traceability(self) -> None:
        outcome = compute_score(
            {"STATUS": "IN_PROGRESS", "DELTA": "PLANNER_DISPATCH_ACTIVE", "BLOCKER_ID": "NONE"},
            {
                "task_update": "blocked",
                "planner_artifact": "logs-codex-runs/orchestrator-state/planner-graph-events.jsonl",
                "stream_id": "BATCH-86",
                "task_id": "BATCH-86-DEV-03",
                "batch_dependency_policy": "single_batch",
            },
            {
                "queue_has_ready": 0,
                "workboard_role_has_work": 0,
                "workboard_role_has_in_progress": 0,
                "planner_batch_runway_short": 1,
            },
            {
                "active_task_id": "BATCH-86-DEV-03",
                "active_task_role": "dev",
                "active_task_state": "IN_PROGRESS",
            },
        )
        self.assertNotIn("missing_architecture_plan_ref", outcome["issues"])
        self.assertNotIn("missing_vision_alignment", outcome["issues"])
        self.assertNotIn("missing_architecture_audit", outcome["issues"])

    def test_closed_runway_does_not_force_autobatch_or_batch_creation(self) -> None:
        outcome = compute_score(
            {"STATUS": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
            {
                "task_update": "none_no_signal",
                "planner_artifact": "logs-codex-runs/orchestrator-state/planner-graph-events.jsonl",
                "batch_dependency_policy": "single_batch",
            },
            {
                "queue_has_ready": 0,
                "workboard_role_has_work": 0,
                "workboard_role_has_in_progress": 0,
                "top_level_total": 84,
                "top_level_non_closed": 0,
                "top_level_ready": 0,
                "planner_batch_runway_short": 1,
            },
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
            },
        )
        self.assertNotIn("planner_autobatch_missing_when_idle", outcome["issues"])
        self.assertNotIn("runway_short_without_batch_creation", outcome["issues"])
        self.assertNotIn("planner_passive_forbidden_violation", outcome["issues"])
        self.assertNotIn("dependency_policy_not_enforced", outcome["issues"])

    def test_no_canonical_work_suppresses_immediate_directive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bus_file = tmp / "directive_bus.jsonl"
            state_dir = tmp / "state"
            maybe_emit_directive(
                role="planner",
                source="primary_structured",
                streaks={"ready_idle_streak": 0, "low_score_streak": 0, "runway_no_batch_streak": 0, "handoff_same_task_streak": 0},
                issues=["planner_passive_forbidden_violation", "planner_autobatch_missing_when_idle"],
                score=45,
                canonical={
                    "active_batch_ids": [],
                    "active_task_id": "",
                    "active_task_role": "",
                    "active_task_state": "",
                    "active_task_blocked_reason": "",
                },
                runtime={
                    "queue_has_ready": 0,
                    "workboard_role_has_work": 0,
                    "workboard_role_has_in_progress": 0,
                    "top_level_non_closed": 0,
                },
                bus_file=bus_file,
                state_dir=state_dir,
            )
            self.assertFalse(bus_file.exists())

    def test_downstream_active_task_suppresses_planner_delivery_proof_patch(self) -> None:
        patches = build_prompt_patches(
            ["missing_architecture_plan_ref", "missing_vision_alignment"],
            {
                "active_task_id": "BATCH-86-DEV-03",
                "active_task_role": "dev",
                "active_task_state": "IN_PROGRESS",
            },
            {},
        )
        patch_ids = [patch["id"] for patch in patches]
        self.assertNotIn("planner_delivery_proof_complete", patch_ids)

    def test_planner_delivery_proof_patch_forbids_analysis_only_on_ready_planner_work(self) -> None:
        patches = build_prompt_patches(
            ["planner_quality_autofill_missing"],
            {
                "active_task_id": "BATCH-91-GOV_REVIEW",
                "active_task_role": "planner",
                "active_task_state": "READY_PLANNER",
            },
            {},
        )

        patch = next(patch for patch in patches if patch["id"] == "planner_delivery_proof_complete")
        self.assertIn("relance complete dans le meme tick", patch["instruction"])
        self.assertIn("pas de sortie analysis_only/none_no_signal", patch["instruction"])

    def test_ready_planner_claim_does_not_emit_soft_proof_backfill_patch(self) -> None:
        patches = build_prompt_patches(
            [
                "missing_architecture_plan_ref",
                "missing_vision_alignment",
                "missing_architecture_audit",
            ],
            {
                "active_task_id": "BATCH-91-GOV_REVIEW",
                "active_task_role": "planner",
                "active_task_state": "READY_PLANNER",
            },
            {},
            {"task_update": "claim"},
        )

        patch_ids = [patch["id"] for patch in patches]
        self.assertNotIn("planner_delivery_proof_complete", patch_ids)

    def test_canonical_active_snapshot_prefers_in_progress_planner_over_waiting_dep_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state_dir = root / "logs-codex-runs" / "orchestrator-state"
            state_dir.mkdir(parents=True, exist_ok=True)
            latest = state_dir / "planner-guardian-latest.json"
            latest.write_text("{}", encoding="utf-8")
            (state_dir / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {
                            "active_batch_ids": ["BATCH-87"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            (state_dir / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-87-ARCH",
                                "stream_id": "BATCH-87",
                                "role": "planner",
                                "state": "IN_PROGRESS",
                            },
                            {
                                "id": "BATCH-87-ADMIN-01",
                                "stream_id": "BATCH-87",
                                "role": "admin",
                                "state": "WAITING_DEP",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            canonical = canonical_active_snapshot(latest)

            self.assertEqual(canonical["active_task_id"], "BATCH-87-ARCH")
            self.assertEqual(canonical["active_task_role"], "planner")
            self.assertEqual(canonical["active_task_state"], "IN_PROGRESS")

    def test_summary_resets_stale_dispatch_when_canonical_runtime_is_idle(self) -> None:
        summary = summarize_contract_for_publication(
            {
                "STATUS": "IN_PROGRESS",
                "DELTA": "PLANNER_DISPATCH_ACTIVE_BATCH-88-ADMIN-01",
                "VERDICT": "GO_WITH_CAUTION",
                "BLOCKER_ID": "local_monitor_7779_contract_unstable",
                "NEXT_ACTION_UNIQUE": "collect_planner_admin_335c573bb6_P1776266157_23277",
            },
            {
                "task_update": "handoff",
                "planner_artifact": "logs-codex-runs/orchestrator-state/legacy/planner-subagents-events.jsonl",
            },
            {
                "queue_has_ready": 0,
                "workboard_role_has_work": 0,
                "workboard_role_has_in_progress": 0,
                "top_level_non_closed": 0,
            },
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_state": "",
                "active_task_role": "",
                "projection_decision_capable": True,
            },
        )

        self.assertEqual(summary["status"], "IDLE")
        self.assertEqual(summary["delta"], "NO_ACTIVE_CANONICAL_WORK")
        self.assertEqual(summary["verdict"], "PASS")
        self.assertEqual(summary["blocker_id"], "NONE")
        self.assertEqual(summary["next_action_unique"], "none")
        self.assertEqual(summary["task_update"], "none_no_ready")
        self.assertEqual(summary["planner_artifact"], "canonical_runtime_truth_idle")

    def test_summary_resets_stale_dispatch_when_canonical_idle_beats_projected_ready_counts(self) -> None:
        summary = summarize_contract_for_publication(
            {
                "STATUS": "BLOCKED",
                "DELTA": "PLANNER_RUNTIME_ACTIONS_FAILED",
                "VERDICT": "BLOCKED",
                "BLOCKER_ID": "PLANNER_RUNTIME_ACTIONS_FAILED",
                "NEXT_ACTION_UNIQUE": "PLANNER_RUNTIME_ACTIONS_FAILED",
            },
            {
                "task_update": "blocked",
                "planner_artifact": "",
            },
            {
                "queue_has_ready": 1,
                "workboard_role_has_work": 1,
                "workboard_role_has_in_progress": 0,
                "top_level_non_closed": 1,
            },
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_state": "",
                "active_task_role": "",
                "projection_decision_capable": True,
                "projection_decision_reason": "runtime_idle_no_active_cycle",
            },
        )

        self.assertEqual(summary["status"], "IDLE")
        self.assertEqual(summary["delta"], "NO_ACTIVE_CANONICAL_WORK")
        self.assertEqual(summary["blocker_id"], "NONE")
        self.assertEqual(summary["task_update"], "none_no_ready")
        self.assertEqual(summary["planner_artifact"], "canonical_runtime_truth_idle")

    def test_idle_canonical_runtime_ignores_projected_ready_penalties(self) -> None:
        outcome = compute_score(
            {
                "STATUS": "BLOCKED",
                "DELTA": "PLANNER_RUNTIME_ACTIONS_FAILED",
                "BLOCKER_ID": "PLANNER_RUNTIME_ACTIONS_FAILED",
            },
            {
                "task_update": "blocked",
                "planner_artifact": "",
            },
            {
                "queue_has_ready": 1,
                "workboard_role_has_work": 1,
                "workboard_role_has_ready": 1,
                "workboard_role_has_in_progress": 0,
                "top_level_total": 92,
                "top_level_non_closed": 1,
                "top_level_ready": 1,
                "planner_batch_runway_short": 0,
            },
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "projection_decision_capable": True,
                "projection_decision_reason": "runtime_idle_no_active_cycle",
            },
        )

        self.assertNotIn("missing_planner_artifact", outcome["issues"])
        self.assertNotIn("dependency_policy_not_enforced", outcome["issues"])

    def test_idle_canonical_runtime_suppresses_ready_penalties_for_none_no_ready(self) -> None:
        outcome = compute_score(
            {
                "STATUS": "IDLE",
                "DELTA": "NO_ACTIVE_CANONICAL_WORK",
                "BLOCKER_ID": "NONE",
            },
            {
                "task_update": "none_no_ready",
                "planner_artifact": "canonical_runtime_truth_idle",
            },
            {
                "queue_has_ready": 1,
                "workboard_role_has_work": 1,
                "workboard_role_has_ready": 1,
                "workboard_role_has_in_progress": 0,
                "top_level_total": 95,
                "top_level_non_closed": 1,
                "top_level_ready": 1,
                "planner_batch_runway_short": 0,
            },
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "projection_decision_capable": True,
                "projection_decision_reason": "runtime_idle_no_active_cycle",
            },
        )

        self.assertNotIn("ready_but_no_delta", outcome["issues"])
        self.assertNotIn("ready_but_none_task_update", outcome["issues"])
        self.assertNotIn("planner_passive_forbidden_violation", outcome["issues"])

    def test_idle_canonical_runtime_resets_ready_idle_streak(self) -> None:
        streaks, meta = update_streaks(
            {"streaks": {"ready_idle_streak": 2, "low_score_streak": 0, "runway_no_batch_streak": 0}},
            {
                "queue_has_ready": 1,
                "workboard_role_has_work": 1,
                "workboard_role_has_in_progress": 0,
                "top_level_non_closed": 1,
            },
            {"DELTA": "NO_ACTIVE_CANONICAL_WORK"},
            {"task_update": "none_no_ready"},
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "projection_decision_reason": "runtime_idle_no_active_cycle",
            },
            100,
        )

        self.assertEqual(streaks["ready_idle_streak"], 0)
        self.assertEqual(meta["_last_handoff_task"], "")

    def test_idle_canonical_runtime_returns_no_claim_recommendation(self) -> None:
        recos = recommendations(
            ["ready_but_no_delta", "ready_but_none_task_update"],
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "projection_decision_reason": "runtime_idle_no_active_cycle",
            },
        )

        self.assertEqual(recos, [])

    def test_idle_ready_delivery_state_opens_next_batch_recommendation(self) -> None:
        recos = recommendations(
            ["residue_detected"],
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "product_delivery_state": {
                    "phase": "idle_ready_for_next_batch",
                    "next_batch_eligible": True,
                },
            },
        )

        self.assertEqual(
            recos,
            ["Aucun batch canonique actif: ouvrir le prochain batch eligible maintenant via sync-priority + planner-autobatch + claim."],
        )

    def test_product_done_ops_dirty_opens_next_batch_recommendation(self) -> None:
        recos = recommendations(
            ["residue_detected"],
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "product_delivery_state": {
                    "phase": "product_done_ops_dirty",
                    "next_batch_eligible": True,
                },
            },
        )

        self.assertEqual(
            recos,
            ["Aucun batch canonique actif: ouvrir le prochain batch eligible maintenant via sync-priority + planner-autobatch + claim."],
        )

    def test_idle_canonical_runtime_marks_projection_noise_as_residue(self) -> None:
        outcome = compute_score(
            {
                "STATUS": "IDLE",
                "DELTA": "NO_ACTIVE_CANONICAL_WORK",
                "BLOCKER_ID": "NONE",
            },
            {
                "task_update": "none_no_ready",
                "planner_artifact": "canonical_runtime_truth_idle",
            },
            {
                "queue_has_ready": 1,
                "workboard_role_has_work": 1,
                "workboard_role_has_ready": 1,
                "workboard_role_has_in_progress": 0,
                "top_level_total": 95,
                "top_level_non_closed": 1,
                "top_level_ready": 1,
                "planner_batch_runway_short": 0,
            },
            {
                "active_batch_ids": [],
                "active_task_id": "",
                "active_task_role": "",
                "active_task_state": "",
                "projection_decision_capable": True,
                "projection_decision_reason": "runtime_idle_no_active_cycle",
            },
        )

        self.assertIn("residue_detected", outcome["issues"])
        self.assertNotIn("planner_passive_forbidden_violation", outcome["issues"])

    def test_canonical_active_snapshot_ignores_stale_projection_when_runtime_idle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state_dir = root / "logs-codex-runs" / "orchestrator-state"
            state_dir.mkdir(parents=True, exist_ok=True)
            latest = state_dir / "planner-guardian-latest.json"
            latest.write_text("{}", encoding="utf-8")
            (state_dir / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-91"]},
                        "meta": {
                            "workboard_decision_capable": False,
                            "workboard_decision_capability_reason": "projection_missing_operational_fields",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (state_dir / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "meta": {
                            "decision_capable": False,
                            "decision_capability_reason": "projection_missing_operational_fields",
                        },
                        "tasks": [
                            {
                                "id": "BATCH-91-ARCH",
                                "stream_id": "BATCH-91",
                                "role": "planner",
                                "state": "READY_PLANNER",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(
                MODULE,
                "build_runtime_truth_snapshot",
                return_value={
                    "event_store_primary": True,
                    "graph_state_count": 0,
                    "recent_event_count": 0,
                    "product_delivery_state": {
                        "active_batch_id": None,
                        "phase": "idle_ready_for_next_batch",
                    },
                },
            ):
                canonical = canonical_active_snapshot(latest)

            self.assertEqual(canonical["active_batch_ids"], [])
            self.assertEqual(canonical["active_task_id"], "")
            self.assertEqual(canonical["active_task_role"], "")
            self.assertFalse(canonical["projection_secondary_only"])
            self.assertFalse(canonical["projection_decision_capable"])

    def test_canonical_active_snapshot_ignores_ready_planner_projection_without_active_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state_dir = root / "logs-codex-runs" / "orchestrator-state"
            state_dir.mkdir(parents=True, exist_ok=True)
            latest = state_dir / "planner-guardian-latest.json"
            latest.write_text("{}", encoding="utf-8")
            (state_dir / "priority-queue.json").write_text(
                json.dumps({"active_cycle": {"active_batch_ids": []}}),
                encoding="utf-8",
            )
            (state_dir / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-92-ANALYSIS",
                                "stream_id": "BATCH-92",
                                "role": "planner",
                                "state": "READY_PLANNER",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(
                MODULE,
                "build_runtime_truth_snapshot",
                return_value={
                    "event_store_primary": True,
                    "graph_state_count": 0,
                    "recent_event_count": 0,
                },
            ):
                canonical = canonical_active_snapshot(latest)

            self.assertEqual(canonical["active_batch_ids"], [])
            self.assertEqual(canonical["active_task_id"], "")
            self.assertEqual(canonical["active_task_role"], "")
            self.assertEqual(canonical["projection_decision_reason"], "runtime_idle_no_active_cycle")
            self.assertFalse(canonical["projection_secondary_only"])

    def test_canonical_active_snapshot_ignores_stale_projection_after_product_close(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state_dir = root / "logs-codex-runs" / "orchestrator-state"
            state_dir.mkdir(parents=True, exist_ok=True)
            latest = state_dir / "planner-guardian-latest.json"
            latest.write_text("{}", encoding="utf-8")
            (state_dir / "priority-queue.json").write_text(
                json.dumps(
                    {
                        "active_cycle": {"active_batch_ids": ["BATCH-97"]},
                        "meta": {
                            "workboard_decision_capable": False,
                            "workboard_decision_capability_reason": "projection_missing_operational_fields",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (state_dir / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "meta": {
                            "decision_capable": False,
                            "decision_capability_reason": "projection_missing_operational_fields",
                        },
                        "tasks": [
                            {
                                "id": "BATCH-97-ANALYSIS",
                                "stream_id": "BATCH-97",
                                "role": "planner",
                                "state": "READY_PLANNER",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(
                MODULE,
                "build_runtime_truth_snapshot",
                return_value={
                    "event_store_primary": True,
                    "graph_state_count": 1,
                    "recent_event_count": 1,
                    "product_delivery_state": {
                        "active_batch_id": None,
                        "phase": "product_done_ops_dirty",
                        "next_batch_eligible": True,
                    },
                },
            ):
                canonical = canonical_active_snapshot(latest)

            self.assertEqual(canonical["active_batch_ids"], [])
            self.assertEqual(canonical["active_task_id"], "")
            self.assertEqual(canonical["active_task_role"], "")
            self.assertEqual(canonical["projection_decision_reason"], "runtime_idle_no_active_cycle")


if __name__ == "__main__":
    unittest.main()
