from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = REPO_ROOT / "apps" / "monitor" / "server.py"
CORE_ROLES = ("planner", "dev", "admin")


def _load_server_module(workspace: Path):
    os.environ["FC_MONITOR_ROOT"] = str(workspace)
    os.environ["FC_MONITOR_STATE_DIR"] = str(workspace / "state")
    os.environ.pop("FC_PLANNER_ORCHESTRATOR_ENABLED", None)
    os.environ.pop("FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY", None)
    os.environ.pop("FC_EXPERIMENTAL_PLANNER_ONLY", None)
    spec = importlib.util.spec_from_file_location(f"fc_monitor_server_never_null_{id(workspace)}", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


class MonitorStatusNeverNullTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps({"features": {"planner_orchestrator": {"enabled": 0, "cron_planner_only": 0}}}),
            encoding="utf-8",
        )
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (orch / "parallel-workstreams.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)
        (self.root / "state").mkdir(parents=True, exist_ok=True)
        self.module = _load_server_module(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_keeps_agents_non_null_and_core_roles_present(self) -> None:
        payload = self.module.status()
        self.assertIsInstance(payload, dict)
        self.assertIsInstance(payload.get("agents"), dict)
        self.assertIn(payload.get("health"), {"DEGRADED", "STALE", "OK", "UNKNOWN"})
        self.assertIn("dispatcher_tshape", payload)
        self.assertIsInstance(payload["dispatcher_tshape"], dict)
        for field in ("active", "target_role", "since_ts", "reason_blocker", "last_action"):
            self.assertIn(field, payload["dispatcher_tshape"])
        self.assertIn("admin_dispatch", payload)
        self.assertIsInstance(payload["admin_dispatch"], dict)
        for field in ("status", "last_action", "last_reason", "dispatch_reason_code", "cooldown_left_s"):
            self.assertIn(field, payload["admin_dispatch"])
        self.assertIn("orchestration", payload)
        self.assertIsInstance(payload["orchestration"], dict)
        for field in (
            "dependency_policy",
            "inter_batch_dependency_count",
            "sanitized_dependencies_24h",
            "planner_non_passive_policy",
            "planner_passive_events_60m",
            "planner_autobatch_24h",
            "planner_quality_score",
            "planner_quality_missing_count",
            "scrum_actions_sent_60m",
            "scrum_message_emit_skip_60m",
            "dev_ready_count",
            "dev_ready_tasks",
            "orchestrator_source",
            "dev_force_claim_events_60m",
        ):
            self.assertIn(field, payload["orchestration"])
        self.assertEqual(payload["orchestration"]["dependency_policy"], "single_batch")
        self.assertEqual(payload["orchestration"]["planner_non_passive_policy"], "enforced")
        self.assertIn("po_scrum_master", payload)
        self.assertIsInstance(payload["po_scrum_master"], dict)
        for field in ("name", "mode", "active", "last_run_age_min", "lock_skip_streak", "source"):
            self.assertIn(field, payload["po_scrum_master"])
        self.assertIn("planner_evidence_quality_score", payload)
        self.assertIn("queue_workboard_integrity", payload)
        self.assertIsInstance(payload["queue_workboard_integrity"], dict)
        for field in ("status", "mismatch_count", "oldest_mismatch_age_s"):
            self.assertIn(field, payload["queue_workboard_integrity"])
        self.assertIn("agent_messages", payload)
        self.assertIsInstance(payload["agent_messages"], dict)
        for field in ("open", "delivered_recent", "actioned_recent", "closed_recent", "posted", "source"):
            self.assertIn(field, payload["agent_messages"])
        self.assertIn("open_by_role", payload["agent_messages"])
        self.assertIn("latest_action_status_by_role", payload["agent_messages"])
        self.assertIn("agent_activity", payload)
        self.assertIsInstance(payload["agent_activity"], dict)
        self.assertIn("roles", payload["agent_activity"])
        self.assertIn("active_helper_count", payload["agent_activity"])
        self.assertIn("monitor_access", payload)
        self.assertIsInstance(payload["monitor_access"], dict)
        for field in ("mode", "canonical_ui_url", "canonical_status_url", "vm_local_ui_url", "vm_local_status_url", "state_file"):
            self.assertIn(field, payload["monitor_access"])
        self.assertIn("delivery_control", payload)
        self.assertIsInstance(payload["delivery_control"], dict)
        for field in ("status", "integrity_status", "future_status", "needs_proof_backfill", "suspicious_completions", "pipeline_counts"):
            self.assertIn(field, payload["delivery_control"])
        self.assertIn("alerts_overview", payload)
        self.assertIsInstance(payload["alerts_overview"], dict)
        for field in ("status", "snapshot_path", "active_count", "suppressed_count", "top_alert", "priority_bands", "suppression_reasons", "pipeline"):
            self.assertIn(field, payload["alerts_overview"])

        agents = payload["agents"]
        for role in CORE_ROLES:
            self.assertIn(role, agents)
            self.assertIsInstance(agents[role], dict)
            for field in ("status", "verdict", "blocker", "tick_age_min", "source"):
                self.assertIn(field, agents[role])
            self.assertIn(role, payload["agent_activity"]["roles"])
            self.assertIsInstance(payload["agent_activity"]["roles"][role], dict)
            for field in ("action_summary", "current_task_id", "recent_events", "active_helpers"):
                self.assertIn(field, payload["agent_activity"]["roles"][role])
            self.assertIn("pending_messages_count", agents[role])
            self.assertIn("last_message_id", agents[role])
            self.assertIn("last_message_action_status", agents[role])
        for field in ("dev_ready_count", "dev_wait_allowed", "dev_wait_reason"):
            self.assertIn(field, agents["dev"])
        for field in ("quality_missing_fields", "quality_autofix_active"):
            self.assertIn(field, agents["planner"])
        for field in ("actions_sent_60m", "last_action_target", "last_action_message_id"):
            self.assertIn(field, agents["scrum_master"])
        self.assertIn("tshape_active", agents["admin"])
        self.assertIn("tshape_target_role", agents["admin"])

        # With no runtime snapshots/ticks available, monitor must not claim OK.
        self.assertEqual(payload.get("health"), "DEGRADED")

        lite_payload = self.module.status(lite=1)
        self.assertIsInstance(lite_payload, dict)
        self.assertIn("layers", lite_payload)
        self.assertEqual(lite_payload["layers"].get("service"), "status_service.v3")
        self.assertTrue(lite_payload["layers"].get("collectors_omitted"))
        self.assertEqual(lite_payload["layers"].get("mode"), "lite")
        self.assertNotIn("collectors", lite_payload["layers"])
        self.assertIn("alerts_overview", lite_payload)
        self.assertIsInstance(lite_payload["alerts_overview"], dict)

    def test_status_surfaces_alert_priority_summary_from_runtime_snapshot(self) -> None:
        alerts_dir = self.root / "apps" / "api" / "runtime" / "data"
        alerts_dir.mkdir(parents=True, exist_ok=True)
        (alerts_dir / "alerts.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-03-13T08:10:00Z",
                    "source": ["job:alerts", "multi_signal_v2"],
                    "alerts": [
                        {
                            "id": "alert-urgent-aapl",
                            "ticker": "AAPL",
                            "summary": "breakout-news:AAPL:3",
                            "severity": "high",
                            "priority_band": "urgent",
                            "priority_rank": 1,
                            "priority_score": 410,
                            "timestamp": "2026-03-13T08:10:00Z",
                        }
                    ],
                    "suppressed_alerts": [
                        {
                            "id": "alert-suppressed-aapl",
                            "ticker": "AAPL",
                            "summary": "breakout-news:AAPL:3",
                            "severity": "high",
                            "priority_band": "urgent",
                            "priority_rank": 2,
                            "priority_score": 390,
                            "timestamp": "2026-03-13T08:06:00Z",
                            "suppression": {"reason": "fatigue_window_duplicate"},
                        }
                    ],
                    "stats": {
                        "priority_bands": {"urgent": 1},
                        "suppression_reasons": {"fatigue_window_duplicate": 1},
                    },
                    "pipeline": {"suppression_window_minutes": 15, "fatigue_threshold": 2},
                    "warnings": ["duplicate_alerts_suppressed"],
                }
            ),
            encoding="utf-8",
        )

        payload = self.module.status()

        alerts_overview = payload["alerts_overview"]
        self.assertEqual(alerts_overview["status"], "ok")
        self.assertEqual(alerts_overview["active_count"], 1)
        self.assertEqual(alerts_overview["suppressed_count"], 1)
        self.assertEqual(alerts_overview["top_alert"]["id"], "alert-urgent-aapl")
        self.assertEqual(alerts_overview["top_alert"]["priority_band"], "urgent")
        self.assertEqual(alerts_overview["priority_bands"], {"urgent": 1})
        self.assertEqual(alerts_overview["suppression_reasons"], {"fatigue_window_duplicate": 1})
        self.assertEqual(alerts_overview["pipeline"]["suppression_window_minutes"], 15)

    def test_status_lite_keeps_queue_summary_when_runtime_is_degraded(self) -> None:
        orch = self.root / "docs" / "operations" / "orchestrator"
        (orch / "priority-queue.json").write_text(
            json.dumps(
                {
                    "active_cycle": {"active_batch_ids": ["BATCH-84"]},
                    "items": [
                        {"id": "BATCH-84", "state": "WAITING_DEP"},
                        {"id": "BATCH-84-PLAN", "state": "READY_PLANNER"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        lite_payload = self.module.status(lite=1)
        self.assertEqual(lite_payload["active_batch"], "BATCH-84")
        self.assertEqual(lite_payload["queue"]["counts"]["WAITING_DEP"], 1)
        self.assertEqual(lite_payload["queue"]["counts"]["READY_PLANNER"], 1)
        self.assertEqual(lite_payload["queue"]["active_cycle"]["active_batch_ids"], ["BATCH-84"])

    def test_runtime_diagnostics_keeps_agents_non_null(self) -> None:
        payload = self.module.runtime_diagnostics()
        self.assertIsInstance(payload, dict)
        self.assertIn("agents", payload)
        self.assertIsInstance(payload["agents"], dict)
        for role in CORE_ROLES:
            self.assertIn(role, payload["agents"])
            self.assertIsInstance(payload["agents"][role], dict)
        self.assertIn("po_scrum_master", payload)
        self.assertIsInstance(payload["po_scrum_master"], dict)
        self.assertIn("agent_messages", payload)
        self.assertIsInstance(payload["agent_messages"], dict)
        self.assertIn("dev_autonomy", payload)
        self.assertIsInstance(payload["dev_autonomy"], dict)
        self.assertIn("admin_dispatch", payload)
        self.assertIsInstance(payload["admin_dispatch"], dict)
        self.assertIn("signals", payload)
        self.assertIsInstance(payload["signals"], dict)
        for field in ("passive_with_ready_streak", "dispatcher_starvation_s"):
            self.assertIn(field, payload["signals"])
        for field in (
            "coaching_state",
            "none_no_signal_streak_24h",
            "delivery_actions_24h",
            "enforced_delivery_count_24h",
            "issue_reporting_ok_rate_24h",
        ):
            self.assertIn(field, payload["dev_autonomy"])

if __name__ == "__main__":
    unittest.main()
