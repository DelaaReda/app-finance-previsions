from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"


def _load_server_module():
    spec = importlib.util.spec_from_file_location("fc_monitor_server_test", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


def _base_status():
    return {
        "data_freshness_s": 42,
        "data_source": "runtime_snapshot",
        "dispatcher_tshape": {
            "active": False,
            "target_role": "",
            "reason_blocker": "NONE",
            "age_min": -1,
            "since_ts": "",
            "last_action": "idle",
            "resolved": True,
        },
        "agents": {
            "planner": {},
            "dev": {},
            "admin": {},
        },
        "po_scrum_master": {
            "name": "po_scrum_master",
            "mode": "scheduled_advisory",
            "active": False,
            "last_run_age_min": -1,
            "source": "monitor_snapshot",
        },
        "agent_messages": {
            "open": 0,
            "delivered": 0,
            "actioned": 0,
            "closed": 0,
            "expired": 0,
            "posted": 0,
            "source": "docs/ops/AGENT_MESSAGE_BUS.jsonl",
        },
        "orchestration": {
            "dependency_policy": "single_batch",
            "inter_batch_dependency_count": 0,
            "sanitized_dependencies_24h": 0,
            "planner_non_passive_policy": "enforced",
            "planner_passive_events_60m": 0,
            "planner_autobatch_24h": 0,
            "planner_quality_score": 100,
            "planner_quality_missing_count": 0,
            "scrum_actions_sent_60m": 0,
            "scrum_message_emit_skip_60m": 0,
            "dev_ready_count": 0,
            "dev_ready_tasks": [],
            "orchestrator_source": "canonical",
            "dev_force_claim_events_60m": 0,
        },
    }


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_runtime_diagnostics_does_not_raise_finding_for_inactive_advisory_lane(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            status_payload = _base_status()
            status_payload["po_scrum_master"] = {
                "name": "po_scrum_master",
                "mode": "scheduled_advisory",
                "active": False,
                "status": "BLOCKED",
                "verdict": "BLOCKED",
                "blocker": "ADVISORY_NOTE",
                "source": "runtime_contract",
            }

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", lambda: status_payload), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            titles = [str(item.get("title", "")) for item in payload.get("top_findings", [])]
            self.assertFalse(any("scrum" in title.lower() for title in titles), msg=titles)

    def test_runtime_diagnostics_does_not_raise_finding_for_advisory_blocker(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            status_payload = _base_status()
            status_payload["po_scrum_master"] = {
                "name": "po_scrum_master",
                "mode": "scheduled_advisory",
                "active": True,
                "status": "BLOCKED",
                "verdict": "BLOCKED",
                "blocker": "ADVISORY_NOTE",
                "source": "runtime_contract",
            }

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", lambda: status_payload), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            titles = [str(item.get("title", "")) for item in payload.get("top_findings", [])]
            self.assertFalse(any("po_scrum_master" in title.lower() for title in titles), msg=titles)

    def test_runtime_diagnostics_marks_historical_permission_as_info(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)

            old_ts = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S+0000")
            (logs_root / "role-recovery.log").write_text(
                f"{old_ts} mkdir: cannot create directory '/home/venom/shared/logs-codex-runs': Operation not permitted\n",
                encoding="utf-8",
            )
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", _base_status), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            signals = payload["signals"]
            self.assertEqual(signals["permission_errors_recent"], 0)
            self.assertEqual(signals["permission_errors_historical"], 1)
            self.assertTrue(signals["permission_last_error_ts"])
            self.assertGreaterEqual(signals["permission_last_error_age_min"], 0)
            self.assertIn("po_scrum_master", payload)
            self.assertIn("agent_messages", payload)

            historical = next(
                finding for finding in payload["top_findings"] if "historical" in finding["title"].lower()
            )
            self.assertEqual(historical["severity"], "info")

    def test_runtime_diagnostics_does_not_prioritize_historical_permission(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)

            old_ts = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S+0000")
            recent_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            (logs_root / "role-recovery.log").write_text(
                f"{old_ts} mkdir: cannot create directory '/home/venom/shared/logs-codex-runs': Operation not permitted\n",
                encoding="utf-8",
            )
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text(
                f"{recent_ts} role=admin event=retry_prompt_end detail=tick=R123 rc=124 bytes=100\n",
                encoding="utf-8",
            )

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", _base_status), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            findings = payload["top_findings"]
            self.assertTrue(findings)
            self.assertNotIn("historical", findings[0]["title"].lower())

    def test_runtime_diagnostics_flags_long_tshape_takeover(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            status_payload = _base_status()
            status_payload["dispatcher_tshape"] = {
                "active": True,
                "target_role": "dev",
                "reason_blocker": "RUNTIME_BLOCK",
                "age_min": 180,
                "since_ts": "2026-03-03T00:00:00Z",
                "last_action": "sync,handoff",
                "resolved": False,
            }

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", lambda: status_payload), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            finding = next(
                f for f in payload["top_findings"] if f.get("title") == "T_SHAPE_TAKEOVER_ACTIVE"
            )
            self.assertEqual(finding.get("severity"), "high")
            self.assertIn("dev", finding.get("detail", ""))

    def test_runtime_diagnostics_reports_tshape_takeover_when_active(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            old_since = (datetime.now(timezone.utc) - timedelta(minutes=130)).strftime("%Y-%m-%dT%H:%M:%SZ")
            status_payload = _base_status()
            status_payload["dispatcher_tshape"] = {
                "active": True,
                "target_role": "dev",
                "since_ts": old_since,
                "reason_blocker": "CHANNELS_READ_MISSING",
                "last_action": "takeover_preflight_ok",
                "resolved": False,
                "age_min": 130,
            }

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", lambda: status_payload), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            signals = payload["signals"]
            self.assertTrue(signals["tshape_takeover_active"])
            self.assertEqual(signals["tshape_takeover_target_role"], "dev")
            self.assertEqual(signals["tshape_takeover_reason_blocker"], "CHANNELS_READ_MISSING")
            self.assertGreaterEqual(signals["tshape_takeover_age_min"], 90)
            self.assertTrue(
                any(f["title"] == "T_SHAPE_TAKEOVER_ACTIVE" for f in payload["top_findings"]),
                msg=f"findings={payload['top_findings']}",
            )

    def test_runtime_diagnostics_flags_planner_quality_as_warning(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            status_payload = _base_status()
            status_payload["orchestration"]["planner_quality_missing_count"] = 2
            status_payload["orchestration"]["planner_quality_score"] = 50

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", lambda: status_payload), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            finding = next(
                f for f in payload["top_findings"] if f.get("id") == "PLANNER_QUALITY_INCOMPLETE"
            )
            self.assertEqual(finding.get("severity"), "warn")

    def test_runtime_diagnostics_exposes_dev_stall_loop_high(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            status_payload = _base_status()
            status_payload["dev_parent"] = {
                "coaching_state": "STALLED",
                "none_signal_streak_24h": 8,
                "delivery_actions_24h": 0,
                "enforced_delivery_count_24h": 2,
                "issue_reporting_ok_rate_24h": 74,
            }

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", lambda: status_payload), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            finding = next(f for f in payload["top_findings"] if f.get("id") == "DEV_STALL_LOOP")
            self.assertEqual(finding["severity"], "high")
            self.assertIn("STALLED", finding["detail"])
            self.assertEqual(payload["signals"]["dev_coaching_state"], "STALLED")
            self.assertEqual(payload["signals"]["dev_none_no_signal_streak_24h"], 8)
            self.assertIn("dev_autonomy", payload)
            self.assertEqual(payload["dev_autonomy"]["delivery_actions_24h"], 0)

    def test_runtime_diagnostics_exposes_dev_stall_loop_warn(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")

            status_payload = _base_status()
            status_payload["dev_parent"] = {
                "coaching_state": "RECOVERING",
                "none_signal_streak_24h": 4,
                "delivery_actions_24h": 2,
                "enforced_delivery_count_24h": 1,
                "issue_reporting_ok_rate_24h": 96,
            }

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "RUNTIME_DIAG_RECENT_MINUTES", 90
            ), mock.patch.object(server, "status", lambda: status_payload), mock.patch.object(
                server, "contract", lambda _role: {}
            ):
                payload = server.runtime_diagnostics()

            finding = next(f for f in payload["top_findings"] if f.get("id") == "DEV_STALL_LOOP")
            self.assertEqual(finding["severity"], "warn")
            self.assertIn("none_no_signal_streak_24h=4", finding["detail"])

    def test_runtime_diagnostics_exposes_dispatch_starvation_and_passive_streak(self):
        server = _load_server_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            logs_root = root / "logs-codex-runs"
            (logs_root / "role-runner").mkdir(parents=True, exist_ok=True)
            (logs_root / "fc-ticks").mkdir(parents=True, exist_ok=True)
            (logs_root / "role-recovery.log").write_text("", encoding="utf-8")
            (logs_root / "health-snapshot.log").write_text("", encoding="utf-8")
            (logs_root / "vm-resume.log").write_text("", encoding="utf-8")
            (logs_root / "role-runner" / "admin.events.log").write_text("", encoding="utf-8")
            (logs_root / "fc-ticks" / "admin.dispatch.log").write_text(
                "2026-03-06T05:00:00Z dispatch_result status=NOOP reason=no_dispatch_needed_takeover_0 dispatch_reason_code=NO_ACTION stream_fairness_slot=0\n",
                encoding="utf-8",
            )
            state = root / "state"
            state.mkdir(parents=True, exist_ok=True)
            (state / "dev.last_contract").write_text(
                "STATUS: IN_PROGRESS\n"
                "DELTA: READY_ITEM_AVAILABLE_RUNTIME_CONTEXT\n"
                "EVIDENCE: task_update=none_no_signal; lock_check=ok; passive_with_ready_streak=3\n",
                encoding="utf-8",
            )

            status_payload = _base_status()
            status_payload["admin_dispatch"] = {
                "status": "noop",
                "last_action": "noop",
                "last_reason": "no_dispatch_needed_takeover_0",
                "dispatch_reason_code": "NO_ACTION",
                "autonomy_reason_code": "NO_BLOCKED_ROLES",
                "stream_fairness_slot": 0,
                "cooldown_left_s": 0,
                "last_result_ts": "2026-03-06T05:00:00Z",
                "last_result_age_s": 120,
            }

            with mock.patch.object(server, "ROOT", root), mock.patch.object(
                server, "STATE", state
            ), mock.patch.object(server, "RUNTIME_DIAG_RECENT_MINUTES", 90), mock.patch.object(
                server, "status", lambda: status_payload
            ):
                payload = server.runtime_diagnostics()

            self.assertGreaterEqual(payload["signals"]["dispatcher_starvation_s"], 0)
            self.assertEqual(payload["signals"]["passive_with_ready_streak"], 3)


if __name__ == "__main__":
    unittest.main()
