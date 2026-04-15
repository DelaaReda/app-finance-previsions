from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = REPO_ROOT / "apps" / "monitor" / "server.py"


def _load_server_module(workspace: Path, state_dir: Path):
    os.environ["FC_MONITOR_ROOT"] = str(workspace)
    os.environ["FC_MONITOR_STATE_DIR"] = str(state_dir)
    os.environ.pop("FC_PLANNER_ORCHESTRATOR_ENABLED", None)
    os.environ.pop("FC_PLANNER_ORCHESTRATOR_CRON_PLANNER_ONLY", None)
    os.environ.pop("FC_EXPERIMENTAL_PLANNER_ONLY", None)
    spec = importlib.util.spec_from_file_location(
        f"fc_monitor_server_planner_dev_policy_{id(workspace)}", SERVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed")
        raise
    return module


class MonitorStatusPlannerDevPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.state = self.root / "state"
        self.state.mkdir(parents=True, exist_ok=True)
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps({"features": {"planner_orchestrator": {"enabled": 0, "cron_planner_only": 0}}}),
            encoding="utf-8",
        )

        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text(
            json.dumps({"items": [{"id": "BATCH-10", "state": "READY"}]}), encoding="utf-8"
        )
        (orch / "parallel-workstreams.json").write_text(
            json.dumps({"tasks": []}), encoding="utf-8"
        )
        (orch / "agent-iteration-issues.jsonl").write_text("", encoding="utf-8")

        (self.root / "docs" / "ops").mkdir(parents=True, exist_ok=True)
        (self.root / "docs" / "ops" / "AGENT_MESSAGE_BUS.jsonl").write_text("", encoding="utf-8")
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)

        (self.state / "planner_autonomy_state.json").write_text(
            json.dumps(
                {
                    "active": True,
                    "since_ts": "2026-03-05T18:00:00Z",
                    "last_action": "create_and_claim",
                    "last_outcome": "resolved",
                    "policy_enforced": True,
                    "wait_forbidden": True,
                },
                ensure_ascii=True,
            ),
            encoding="utf-8",
        )
        self.module = _load_server_module(self.root, self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_status_exposes_planner_and_dev_policy_fields(self) -> None:
        contracts = {
            "planner": {
                "STATUS": "WAIT",
                "VERDICT": "PASS",
                "DELTA": "NO_DELTA",
                "BLOCKER_ID": "NONE",
                "EVIDENCE": "task_update=none_no_signal; issues=planner_passivity_corrected",
            },
            "dev": {
                "STATUS": "WAIT",
                "VERDICT": "PASS",
                "DELTA": "DEV_WAIT_NO_READY_TASK",
                "BLOCKER_ID": "NONE",
                "EVIDENCE": "task_update=none_no_ready",
            },
            "admin": {
                "STATUS": "IN_PROGRESS",
                "VERDICT": "PASS",
                "DELTA": "NO_DELTA",
                "BLOCKER_ID": "NONE",
            },
        }
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(self.module, "rate_limits", lambda: []), mock.patch.object(
            self.module,
            "_multi_agent_policy_snapshot",
            lambda root: {
                "runtime_mode": "worker_first",
                "allow_runtime_explorer": False,
                "runtime_explorer_default": "disabled",
                "interactive_recent_explorer_sessions": 2,
                "interactive_recent_explorer_agents": [{"nickname": "Averroes"}],
                "note": "Runtime planner is worker-first.",
            },
        ):
            payload = self.module.status()

        self.assertEqual(payload.get("execution_mode"), "parallel_roles")
        self.assertEqual(payload.get("core_roles"), ["planner", "dev", "admin", "scrum_master"])
        self.assertTrue(payload.get("planner_policy_enforced"))
        self.assertIn("delivery_integrity", payload)
        self.assertIn("delivery_control", payload)
        self.assertIn("product_value_metrics", payload)
        self.assertIn("multi_agent_policy", payload)
        self.assertIn("planner_subagents", payload)
        self.assertIn("planner_dispatch", payload)
        self.assertEqual(payload.get("multi_agent_policy", {}).get("runtime_mode"), "worker_first")
        self.assertEqual(payload.get("multi_agent_policy", {}).get("runtime_explorer_default"), "disabled")
        self.assertIn("recent_success_rate", payload.get("planner_subagents", {}))
        self.assertEqual(payload.get("planner_dispatch", {}).get("ready_dev_count"), 0)
        self.assertEqual(payload.get("planner_dispatch", {}).get("status"), "dispatch_needed")
        self.assertIn("future_status", payload.get("delivery_control", {}))
        self.assertEqual(payload.get("planner_autonomy_last_action"), "create_and_claim")
        self.assertEqual(payload.get("planner_autonomy_last_outcome"), "resolved")
        self.assertEqual(payload.get("dev_wait_reason"), "no_dev_ready_task")

        planner = payload.get("agents", {}).get("planner", {})
        self.assertEqual(planner.get("status"), "IN_PROGRESS")
        self.assertEqual(planner.get("delta"), "PLANNER_AUTONOMY_ENFORCED")

        dev = payload.get("agents", {}).get("dev", {})
        self.assertEqual(dev.get("dev_wait_reason"), "no_dev_ready_task")


    def test_status_prefers_live_planner_capability_truth(self) -> None:
        orch = self.root / "docs" / "operations" / "orchestrator"
        (orch / "parallel-workstreams.json").write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "BATCH-13-DEV-02",
                            "stream_id": "BATCH-13",
                            "state": "BLOCKED",
                            "assignee": "dev",
                            "role": "dev",
                            "current_step": "progress:contract_snapshot",
                            "updated_at": "2026-03-09T12:38:29Z",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        contracts = {
            "planner": {"STATUS": "IN_PROGRESS", "VERDICT": "GO_WITH_CAUTION", "DELTA": "PLANNER_DISPATCH_ACTIVE", "BLOCKER_ID": "NONE", "NEXT": "owner=planner; action=stale legacy", "EVIDENCE": "task_update=none"},
            "dev": {},
            "admin": {},
        }
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 3900), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(self.module, "rate_limits", lambda: []), mock.patch.object(
            self.module, "_planner_subagents_snapshot",
            lambda: {
                "enabled": True,
                "cron_planner_only": True,
                "active_count": 1,
                "active": [{"target_role": "dev", "owner_task_id": "BATCH-13-DEV-02", "status": "running", "last_update_at": "2026-03-09T12:38:32Z"}],
                "recent": [],
                "recent_total": 0,
                "recent_success_count": 0,
                "recent_failed_count": 0,
                "recent_blocked_count": 0,
                "recent_fallback_like_count": 0,
                "recent_invalid_result_count": 0,
                "recent_timeout_like_count": 0,
                "recent_success_rate": 1.0,
                "recent_by_role": {},
                "latest_status": "running",
                "latest_fallback_like": False,
                "latest_failure_mode": "none",
                "latest_owner_task_id": "BATCH-13-DEV-02",
                "latest_update_at": "2026-03-09T12:38:32Z",
                "recovering": False,
                "stalled_capability_count": 0,
                "takeover_required_count": 0,
                "recovery_required_count": 0,
                "long_running_dev_count": 0,
                "dev_no_progress_count": 0,
                "dev_orphaned_count": 0,
                "dev_invalid_result_count": 0,
                "status": "ok",
                "registry_path": "planner-subagents-registry.json",
            },
        ):
            payload = self.module.status()

        planner = payload.get("agents", {}).get("planner", {})
        self.assertEqual(planner.get("source"), "planner_capability")
        self.assertEqual(planner.get("next"), "owner=dev; action=continue BATCH-13-DEV-02 via capability dispatch")
        self.assertEqual(planner.get("tick_age_min"), -1)
        self.assertEqual(planner.get("schedule"), "planner-owned")

    def test_runtime_diagnostics_emits_policy_findings(self) -> None:
        status_snapshot = {
            "health": "OK",
            "data_freshness_s": 30,
            "data_source": "runtime_logs",
            "planner_policy_enforced": True,
            "planner_autonomy_last_action": "create_and_claim",
            "planner_autonomy_last_outcome": "resolved",
            "dev_wait_reason": "no_dev_ready_task",
            "agents": {
                "planner": {"status": "IN_PROGRESS", "verdict": "GO_WITH_CAUTION", "delta": "PLANNER_AUTONOMY_ENFORCED", "blocker": "NONE"},
                "dev": {"status": "WAIT", "verdict": "PASS", "delta": "DEV_WAIT_NO_READY_TASK", "blocker": "NONE"},
                "admin": {"status": "IN_PROGRESS", "verdict": "PASS", "delta": "NO_DELTA", "blocker": "NONE"},
            },
            "issue_publication_gap_roles": [],
            "dev_parent": {},
            "dispatcher_tshape": {},
            "admin_autonomy": {"active": False, "needs_human_review_by_role": {"planner": False, "dev": False}},
            "queue": {"state_counts": {"READY": 0, "WAITING_DEP": 0, "IN_PROGRESS": 0}},
            "po_scrum_master": {},
            "agent_messages": {},
        }
        with mock.patch.object(self.module, "status", lambda: status_snapshot), mock.patch.object(
            self.module, "contract", lambda role: {"EVIDENCE": "issues=planner_passivity_corrected"} if role == "planner" else {}
        ):
            payload = self.module.runtime_diagnostics()

        findings = payload.get("top_findings", [])
        ids = {str(item.get("id")) for item in findings if isinstance(item, dict)}
        self.assertIn("PLANNER_PASSIVITY_VIOLATION_CORRECTED", ids)
        self.assertIn("DEV_WAIT_NO_READY_TASK", ids)
        self.assertIn("PLANNER_AUTONOMY_CREATE_CLAIM", ids)


    def test_status_autoheals_admin_runtime_stale_blocker(self) -> None:
        contracts = {
            "planner": {"STATUS": "IN_PROGRESS", "VERDICT": "GO_WITH_CAUTION", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=claim"},
            "dev": {"STATUS": "WAIT", "VERDICT": "PASS", "DELTA": "DEV_WAIT_NO_READY_TASK", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=none_no_ready"},
            "admin": {
                "STATUS": "BLOCKED",
                "VERDICT": "BLOCKED",
                "DELTA": "RUNTIME_DOWN_BLOCKS_READY_QUEUE",
                "BLOCKER_ID": "RUNTIME_DOWN",
                "EVIDENCE": "task_update=blocked",
            },
        }
        doctor = {
            "status": "ok",
            "checks": {
                "providers": {
                    "status": "ok",
                    "detail": {
                        "api_health_ok": True,
                        "monitor_status_ok": True,
                    },
                }
            },
        }
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(self.module, "rate_limits", lambda: []), mock.patch.object(
            self.module, "doctor_snapshot", lambda force_refresh=False: doctor
        ), mock.patch.object(self.module, "_probe_http_ok", lambda url: True):
            payload = self.module.status()

        admin = payload.get("agents", {}).get("admin", {})
        self.assertEqual(admin.get("status"), "PASS")
        self.assertEqual(admin.get("verdict"), "PASS")
        self.assertEqual(admin.get("blocker"), "NONE")
        self.assertEqual(str(admin.get("delta", "")).upper(), "RUNTIME_VERIFIED_OK")

    def test_status_exposes_health_snapshot_and_critical_widget_health(self) -> None:
        latest_snapshot = {
            "roles": {},
            "velocity": {},
            "summary": {},
            "health_snapshot": {
                "ts_utc": "2026-03-08T16:54:00Z",
                "health": "OK",
                "scheduled_roles": ["planner"],
            },
            "critical_widget_health": {
                "ts_utc": "2026-03-08T16:54:00Z",
                "state": "ok",
                "widgets": {"hero": {"state": "ok"}},
            },
        }
        contracts = {
            "planner": {"STATUS": "IN_PROGRESS", "VERDICT": "GO_WITH_CAUTION", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=claim"},
            "dev": {"STATUS": "WAIT", "VERDICT": "PASS", "DELTA": "DEV_WAIT_NO_READY_TASK", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=none_no_ready"},
            "admin": {"STATUS": "IN_PROGRESS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE"},
        }
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: latest_snapshot
        ), mock.patch.object(self.module, "rate_limits", lambda: []):
            payload = self.module.status()

        self.assertEqual(payload.get("health_snapshot", {}).get("health"), "OK")
        self.assertEqual(payload.get("health_snapshot", {}).get("scheduled_roles"), ["planner"])
        self.assertEqual(payload.get("critical_widget_health", {}).get("state"), "ok")
        self.assertEqual(payload.get("critical_widget_health", {}).get("widgets", {}).get("hero", {}).get("state"), "ok")

    def test_status_ready_dev_metrics_come_from_workboard_runtime(self) -> None:
        orch = self.root / "docs" / "operations" / "orchestrator"
        (orch / "priority-queue.json").write_text(
            json.dumps({"items": [{"id": "BATCH-10", "state": "READY_PLANNER"}]}), encoding="utf-8"
        )
        (orch / "parallel-workstreams.json").write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "BATCH-10-DEV-01",
                            "stream_id": "BATCH-10",
                            "state": "READY",
                            "assignee": "dev",
                            "title": "Implement endpoint",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        contracts = {
            "planner": {"STATUS": "IN_PROGRESS", "VERDICT": "GO_WITH_CAUTION", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=claim"},
            "dev": {"STATUS": "WAIT", "VERDICT": "PASS", "DELTA": "DEV_WAIT_NO_READY_TASK", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=none_no_ready"},
            "admin": {"STATUS": "IN_PROGRESS", "VERDICT": "PASS", "DELTA": "NO_DELTA", "BLOCKER_ID": "NONE", "EVIDENCE": "task_update=none_no_signal"},
        }
        with mock.patch.object(self.module, "active_roles", lambda: ("planner", "dev", "admin")), mock.patch.object(
            self.module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(self.module, "tick_age", lambda role: 1), mock.patch.object(
            self.module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(self.module, "rate_limits", lambda: []):
            payload = self.module.status()

        queue = payload.get("queue", {})
        self.assertEqual(queue.get("ready_dev_source"), "workboard_runtime")
        self.assertEqual(queue.get("dev_ready_task_count"), 1)
        self.assertEqual(queue.get("dev_claimable_ready_count"), 1)
        self.assertEqual(queue.get("ready_dev_count"), 1)

    def test_status_uses_planner_only_core_roles_when_planner_experimental(self) -> None:
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
            encoding="utf-8",
        )
        (self.root / "logs-codex-runs" / "fc-ticks" / "scrum_master.tick.log").write_text(
            "2026-03-06T19:00:00 [END] role=scrum_master rc=0\n",
            encoding="utf-8",
        )
        module = _load_server_module(self.root, self.state)
        contracts = {
            "planner": {
                "STATUS": "IN_PROGRESS",
                "VERDICT": "PASS",
                "DELTA": "NO_DELTA",
                "BLOCKER_ID": "NONE",
                "EVIDENCE": "task_update=claim",
            }
        }
        with mock.patch.object(module, "active_roles", lambda: ("planner",)), mock.patch.object(
            module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(module, "tick_age", lambda role: 1), mock.patch.object(
            module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(module, "rate_limits", lambda: []):
            payload = module.status()

        self.assertEqual(payload.get("planner_dispatch", {}).get("status"), "dispatch_needed")
        self.assertEqual(payload.get("planner_dispatch", {}).get("lifecycle"), "running")

        self.assertEqual(payload.get("execution_mode"), "planner_experimental")
        self.assertEqual(payload.get("scheduler_roles"), ["planner"])
        self.assertEqual(payload.get("roles"), ["planner", "dev", "admin", "scrum_master"])
        self.assertEqual(payload.get("capability_roles"), ["dev", "admin", "scrum_master"])
        self.assertEqual(payload.get("health_breakdown", {}).get("core_roles"), ["planner"])
        self.assertEqual(payload.get("agents_incomplete"), [])
        self.assertNotIn("dev", payload.get("health_breakdown", {}).get("by_role", {}))
        self.assertIn("scrum_master", payload.get("roles", []))

    def test_planner_only_status_ignores_legacy_discovered_admin_role(self) -> None:
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
            encoding="utf-8",
        )
        module = _load_server_module(self.root, self.state)
        contracts = {
            "planner": {
                "STATUS": "IN_PROGRESS",
                "VERDICT": "PASS",
                "DELTA": "NO_DELTA",
                "BLOCKER_ID": "NONE",
                "EVIDENCE": "task_update=claim",
            }
        }
        with mock.patch.object(module, "_roles_from_crontab", lambda: ("planner", "admin")), mock.patch.object(
            module, "_roles_from_topology", lambda: ("planner", "admin")
        ), mock.patch.object(module, "contract", lambda role: contracts.get(role, {})), mock.patch.object(
            module, "tick_age", lambda role: 1
        ), mock.patch.object(
            module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(module, "rate_limits", lambda: []):
            payload = module.status()

        self.assertEqual(payload.get("roles"), ["planner"])
        admin_agent = payload.get("agents", {}).get("admin", {})
        self.assertEqual(admin_agent.get("source"), "planner_capability")
        self.assertEqual(admin_agent.get("status"), "IDLE")
        self.assertEqual(admin_agent.get("delta"), "NO_ACTIVE_CAPABILITY")

    def test_status_reports_paused_runtime_state_explicitly(self) -> None:
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
            encoding="utf-8",
        )
        runtime_state_dir = self.root / "logs-codex-runs" / "orchestrator-state"
        runtime_state_dir.mkdir(parents=True, exist_ok=True)
        (runtime_state_dir / "runtime-state.json").write_text(
            json.dumps(
                {
                    "lifecycle": "paused",
                    "reason": "operator_paused_runtime",
                    "execution_mode": "planner_experimental",
                    "operator_mode": "paused",
                    "source": "unit_test",
                }
            ),
            encoding="utf-8",
        )

        module = _load_server_module(self.root, self.state)
        with mock.patch.object(module, "active_roles", lambda: ("planner",)), mock.patch.object(
            module, "contract", lambda role: {}
        ), mock.patch.object(module, "tick_age", lambda role: -1), mock.patch.object(
            module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(module, "rate_limits", lambda: []), mock.patch.object(
            module, "doctor_snapshot", lambda force_refresh=False: {"status": "ok", "checks": {}}
        ):
            payload = module.status()

        self.assertEqual(payload.get("health"), "PAUSED")
        self.assertEqual(payload.get("runtime_state", {}).get("lifecycle"), "paused")
        self.assertEqual(payload.get("agents", {}).get("planner", {}).get("status"), "PAUSED")

    def test_status_softens_stale_planner_claim_failure_when_dispatch_is_active(self) -> None:
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
            encoding="utf-8",
        )
        runtime_state_dir = self.root / "logs-codex-runs" / "orchestrator-state"
        runtime_state_dir.mkdir(parents=True, exist_ok=True)
        (runtime_state_dir / "runtime-state.json").write_text(
            json.dumps(
                {
                    "lifecycle": "running",
                    "execution_mode": "planner_experimental",
                    "operator_mode": "planner-experimental",
                    "source": "unit_test",
                }
            ),
            encoding="utf-8",
        )
        orch = self.root / "docs" / "operations" / "orchestrator"
        (orch / "parallel-workstreams.json").write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "BATCH-28-DEV-01",
                            "stream_id": "BATCH-28",
                            "state": "IN_PROGRESS",
                            "assignee": "dev",
                            "title": "Dispatch active",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        module = _load_server_module(self.root, self.state)
        contracts = {
            "planner": {
                "STATUS": "BLOCKED",
                "VERDICT": "BLOCKED",
                "DELTA": "SYNC_PRIORITY_THEN_CLAIM_FAILED",
                "BLOCKER_ID": "PLANNER_NO_READY_TASK_AFTER_SYNC",
                "EVIDENCE": "task_update=blocked",
            }
        }
        with mock.patch.object(module, "active_roles", lambda: ("planner",)), mock.patch.object(
            module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(module, "tick_age", lambda role: 1), mock.patch.object(
            module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(module, "rate_limits", lambda: []), mock.patch.object(
            module, "doctor_snapshot", lambda force_refresh=False: {"status": "ok", "checks": {}}
        ):
            payload = module.status()

        planner = payload.get("agents", {}).get("planner", {})
        self.assertEqual(planner.get("status"), "IN_PROGRESS")
        self.assertEqual(planner.get("blocker"), "NONE")
        self.assertEqual(planner.get("delta"), "PLANNER_DISPATCH_ACTIVE")

    def test_status_softens_delivery_value_planner_block_when_dispatch_is_active(self) -> None:
        cfg_dir = self.root / "platform" / "config" / "runner"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "runner.v1.yaml").write_text(
            json.dumps({"features": {"planner_orchestrator": {"enabled": 1, "cron_planner_only": 1}}}),
            encoding="utf-8",
        )
        runtime_state_dir = self.root / "logs-codex-runs" / "orchestrator-state"
        runtime_state_dir.mkdir(parents=True, exist_ok=True)
        (runtime_state_dir / "runtime-state.json").write_text(
            json.dumps(
                {
                    "lifecycle": "running",
                    "execution_mode": "planner_experimental",
                    "operator_mode": "planner-experimental",
                    "source": "unit_test",
                }
            ),
            encoding="utf-8",
        )
        orch = self.root / "docs" / "operations" / "orchestrator"
        (orch / "parallel-workstreams.json").write_text(
            json.dumps(
                {
                    "tasks": [
                        {
                            "id": "BATCH-28-DEV-01",
                            "stream_id": "BATCH-28",
                            "state": "IN_PROGRESS",
                            "assignee": "dev",
                            "title": "Dispatch active",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        module = _load_server_module(self.root, self.state)
        contracts = {
            "planner": {
                "STATUS": "BLOCKED",
                "VERDICT": "BLOCKED",
                "DELTA": "DELIVERY_VALUE_INSUFFICIENT",
                "BLOCKER_ID": "DELIVERY_VALUE_INSUFFICIENT",
                "EVIDENCE": "task_update=complete",
            }
        }
        with mock.patch.object(module, "active_roles", lambda: ("planner",)), mock.patch.object(
            module, "contract", lambda role: contracts.get(role, {})
        ), mock.patch.object(module, "tick_age", lambda role: 1), mock.patch.object(
            module, "monitor_latest_snapshot", lambda: {"roles": {}, "velocity": {}, "summary": {}, "health_snapshot": {}}
        ), mock.patch.object(module, "rate_limits", lambda: []), mock.patch.object(
            module, "doctor_snapshot", lambda force_refresh=False: {"status": "ok", "checks": {}}
        ):
            payload = module.status()

        planner = payload.get("agents", {}).get("planner", {})
        self.assertEqual(planner.get("status"), "IN_PROGRESS")
        self.assertEqual(planner.get("blocker"), "NONE")
        self.assertEqual(planner.get("delta"), "PLANNER_DISPATCH_ACTIVE")


if __name__ == "__main__":
    unittest.main()
