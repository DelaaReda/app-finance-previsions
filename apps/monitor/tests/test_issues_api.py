#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = REPO_ROOT / "apps" / "monitor" / "server.py"


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_server_module(workspace: Path):
    os.environ["FC_MONITOR_ROOT"] = str(workspace)
    os.environ["FC_MONITOR_STATE_DIR"] = str(workspace / "state")
    os.environ["FC_MONITOR_ITERATION_ISSUES_EVENTS_FILE"] = str(
        workspace / "docs" / "operations" / "orchestrator" / "agent-iteration-issues.jsonl"
    )
    os.environ["FC_MONITOR_ITERATION_ISSUES_LATEST_FILE"] = str(
        workspace / "docs" / "operations" / "orchestrator" / "agent-iteration-issues-latest.json"
    )
    spec = importlib.util.spec_from_file_location(f"fc_monitor_server_test_{id(workspace)}", SERVER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except ModuleNotFoundError as exc:
        if str(exc).startswith("No module named 'fastapi'"):
            raise unittest.SkipTest("fastapi not installed in current Python runtime")
        raise
    return module


class MonitorIssuesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        orch = self.root / "docs" / "operations" / "orchestrator"
        orch.mkdir(parents=True, exist_ok=True)
        (orch / "priority-queue.json").write_text('{"items":[]}\n', encoding="utf-8")
        (orch / "parallel-workstreams.json").write_text('{"tasks":[]}\n', encoding="utf-8")
        (self.root / "logs-codex-runs" / "fc-ticks").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "role-runner").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "dev-parent").mkdir(parents=True, exist_ok=True)
        (self.root / "state").mkdir(parents=True, exist_ok=True)
        (self.root / "logs-codex-runs" / "dev-parent" / "latest.json").write_text(
            json.dumps(
                {
                    "coaching_state": "RECOVERING",
                    "channels_missing_streak_24h": 1,
                    "none_signal_streak_24h": 2,
                    "contract_guard_block_count_24h": 1,
                    "issue_reporting_ok_rate_24h": 96,
                    "delivery_actions_24h": 3,
                    "enforced_delivery_count_24h": 1,
                    "stall_recovery_rate_24h": 80,
                    "ready_seen_without_claim_24h": 2,
                },
                ensure_ascii=True,
            ),
            encoding="utf-8",
        )

        now = datetime.now(timezone.utc)
        rows = [
            {
                "ts_utc": _iso(now - timedelta(minutes=8)),
                "tick_id": "P1",
                "role": "planner",
                "agent_bin": "codex",
                "channel": "tmux",
                "source": "primary_structured",
                "status": "IN_PROGRESS",
                "verdict": "GO_WITH_CAUTION",
                "rc_primary": 124,
                "rc_retry": 124,
                "rc_final": 124,
                "issue_status": "has_issues",
                "issue_count": 1,
                "max_severity": "WARN",
                "issues": [{"code": "TIMEOUT_124", "severity": "WARN"}],
                "next_action": "retry",
                "queue_version": "qv1",
                "workboard_version": "wv1",
            },
            {
                "ts_utc": _iso(now - timedelta(minutes=5)),
                "tick_id": "P2",
                "role": "planner",
                "agent_bin": "codex",
                "channel": "tmux",
                "source": "retry_structured",
                "status": "IN_PROGRESS",
                "verdict": "GO",
                "rc_primary": 0,
                "rc_retry": 0,
                "rc_final": 0,
                "issue_status": "none",
                "issue_count": 0,
                "max_severity": "INFO",
                "issues": [],
                "next_action": "continue",
                "queue_version": "qv1",
                "workboard_version": "wv1",
            },
            {
                "ts_utc": _iso(now - timedelta(minutes=3)),
                "tick_id": "A1",
                "role": "admin",
                "agent_bin": "codex",
                "channel": "tmux",
                "source": "fallback_checkpoint",
                "status": "IN_PROGRESS",
                "verdict": "GO_WITH_CAUTION",
                "rc_primary": 1,
                "rc_retry": 1,
                "rc_final": 1,
                "issue_status": "has_issues",
                "issue_count": 2,
                "max_severity": "CRITICAL",
                "issues": [
                    {"code": "PERMISSION_OP_NOT_PERMITTED", "severity": "CRITICAL"},
                    {"code": "CHECKPOINT_FALLBACK", "severity": "ERROR"},
                ],
                "next_action": "fix_paths",
                "queue_version": "qv1",
                "workboard_version": "wv1",
            },
            {
                "ts_utc": _iso(now - timedelta(minutes=2)),
                "tick_id": "D1",
                "role": "dev",
                "agent_bin": "codex",
                "channel": "tmux",
                "source": "primary_structured",
                "status": "IN_PROGRESS",
                "verdict": "GO",
                "rc_primary": 0,
                "rc_retry": 0,
                "rc_final": 0,
                "issue_status": "none",
                "issue_count": 0,
                "max_severity": "INFO",
                "issues": [],
                "next_action": "continue",
                "queue_version": "qv1",
                "workboard_version": "wv1",
            },
        ]
        issues_file = orch / "agent-iteration-issues.jsonl"
        issues_file.write_text("\n".join(json.dumps(r, ensure_ascii=True) for r in rows) + "\n", encoding="utf-8")
        (orch / "agent-iteration-issues-latest.json").write_text(
            json.dumps({"roles": {"planner": rows[1], "admin": rows[2], "dev": rows[3]}}, ensure_ascii=True),
            encoding="utf-8",
        )
        self.module = _load_server_module(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_issues_feed_filters_role_and_severity(self) -> None:
        planner_only = self.module.issues_feed(role="planner", severity="", window_min=120, n=50)
        self.assertGreaterEqual(planner_only["count"], 2)
        self.assertTrue(all(str(row.get("role")) == "planner" for row in planner_only["items"]))

        critical_only = self.module.issues_feed(role="", severity="CRITICAL", window_min=120, n=50)
        self.assertEqual(critical_only["count"], 1)
        self.assertEqual(critical_only["items"][0]["role"], "admin")
        self.assertEqual(critical_only["items"][0]["max_severity"], "CRITICAL")

    def test_issues_summary_has_expected_counts_and_mttr(self) -> None:
        summary = self.module.issues_summary(window_min=120)
        totals = summary["totals_by_severity"]
        self.assertEqual(totals["WARN"], 1)
        self.assertEqual(totals["CRITICAL"], 1)
        self.assertIn("planner", summary["roles_touched"])
        self.assertIn("admin", summary["roles_touched"])
        self.assertIn("planner", summary["mttr_estimated_by_role"])
        self.assertIsNotNone(summary["mttr_estimated_by_role"]["planner"])
        top_codes = {entry["code"] for entry in summary["top_codes"]}
        self.assertIn("TIMEOUT_124", top_codes)

    def test_status_is_enriched_with_issue_fields(self) -> None:
        data = self.module.status()
        self.assertIn("issues_recent_by_role", data)
        self.assertIn("critical_open_count", data)
        self.assertIn("issue_publication_gap_roles", data)
        self.assertIn("last_issue_by_role", data)
        self.assertEqual(data["critical_open_count"], 1)
        self.assertIn("planner", data["issues_recent_by_role"])
        self.assertGreaterEqual(sum(int(v) for v in data["issues_recent_by_role"].values()), 1)

    def test_dashboard_html_contains_issue_panel_and_severity_styles(self) -> None:
        html = self.module.HTML
        self.assertIn("Execution Issues Feed", html)
        self.assertIn(".issue-row.error", html)
        self.assertIn(".issue-row.warn", html)
        self.assertIn(".issue-row.critical", html)
        self.assertIn("issues_60m", html)

    def test_agent_insights_exposes_dev_parent_metrics(self) -> None:
        previous_state = self.module.STATE
        try:
            self.module.STATE = self.root / "state"
            payload = self.module.agent_insights()
        finally:
            self.module.STATE = previous_state
        self.assertIn("dev", payload["agents"])
        dev = payload["agents"]["dev"]
        self.assertEqual(dev["coaching_state"], "RECOVERING")
        self.assertEqual(dev["channels_missing_streak_24h"], 1)
        self.assertEqual(dev["none_signal_streak_24h"], 2)
        self.assertEqual(dev["contract_guard_block_count_24h"], 1)
        self.assertEqual(dev["issue_reporting_ok_rate_24h"], 96)
        self.assertIn("dev_autonomy", dev)
        self.assertEqual(dev["dev_autonomy"]["delivery_actions_24h"], 3)
        self.assertEqual(dev["dev_autonomy"]["enforced_delivery_count_24h"], 1)
        self.assertEqual(dev["dev_autonomy"]["stall_recovery_rate_24h"], 80)
        self.assertEqual(dev["dev_autonomy"]["ready_seen_without_claim_24h"], 2)


if __name__ == "__main__":
    unittest.main()
