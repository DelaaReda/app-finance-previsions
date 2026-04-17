#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "role_runtime_context.py"
RUNNER_SCRIPT = ROOT / "automation" / "cron_tmux_role_runner.sh"

if str(ROOT / "automation") not in sys.path:
    sys.path.insert(0, str(ROOT / "automation"))

from role_runtime_context import queue_summary


class RoleRuntimeContextTests(unittest.TestCase):
    def test_queue_summary_keeps_closed_pipeline_out_of_short_runway_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td)
            payload = {
                "streams": [
                    {"id": "BATCH-88", "state": "DONE"},
                    {"id": "BATCH-89", "state": "CLOSED"},
                ]
            }
            queue_path = state_dir / "priority-queue.json"
            (state_dir / "parallel-workstreams.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")

            summary = queue_summary(queue_path)

            self.assertEqual(summary["top_level_total"], "2")
            self.assertEqual(summary["top_level_non_closed"], "0")
            self.assertEqual(summary["planner_batch_runway_short"], "0")

    def test_builds_context_with_queue_and_directives(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "docs/orchestrator-ops").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/product/planning").mkdir(parents=True, exist_ok=True)
            (workspace / "logs-codex-runs/orchestrator-state").mkdir(parents=True, exist_ok=True)
            (workspace / "state").mkdir(parents=True, exist_ok=True)
            (workspace / "memory/agents").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/ops").mkdir(parents=True, exist_ok=True)
            (workspace / "logs").mkdir(parents=True, exist_ok=True)

            queue = {
                "items": [
                    {
                        "id": "BATCH-02",
                        "title": "Implement status propagation",
                        "state": "READY",
                        "next_action": "DISPATCH_BATCH02",
                    },
                    {
                        "id": "BATCH-01",
                        "title": "Previous gate",
                        "state": "BLOCKED",
                        "blocker_id": "NEEDS_QA",
                    },
                ]
            }
            (workspace / "logs-codex-runs/orchestrator-state/priority-queue.json").write_text(
                json.dumps(queue), encoding="utf-8"
            )
            (workspace / "docs/product/planning/WORKSTATE.md").write_text(
                "Working on orchestration status and channel impacts.\n", encoding="utf-8"
            )
            (workspace / "state/dev.last_contract").write_text(
                "STATUS: IN_PROGRESS\nDELTA: DEV_TICK\nNEXT_ACTION_UNIQUE: DEV_ACTION\n", encoding="utf-8"
            )
            (workspace / "state/qa.last_contract").write_text(
                "STATUS: IN_PROGRESS\nDELTA: QA_TICK\nNEXT_ACTION_UNIQUE: QA_ACTION\n", encoding="utf-8"
            )
            (workspace / "memory/agents/dev.md").write_text("# dev\n- recent note\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_CHAT.md").write_text("chat line\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md").write_text("iter line\n", encoding="utf-8")
            (workspace / "logs/dev.live.log").write_text("trace line\n", encoding="utf-8")
            (workspace / "docs/ops/DIRECTIVE_BUS.jsonl").write_text(
                json.dumps(
                    {
                        "id": "DIR-001",
                        "kind": "policy",
                        "msg": "prioritize batch02",
                        "targets": ["dev"],
                        "ts": "2026-02-27T10:00:00Z",
                        "expires_at": "2026-12-31T00:00:00Z",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (workspace / "docs/ops/AGENT_MESSAGE_BUS.jsonl").write_text(
                json.dumps(
                    {
                        "event": "message_posted",
                        "ts": "2026-02-27T10:05:00Z",
                        "message_id": "MSG_20260227T100500Z_1001",
                        "from": "admin",
                        "targets": ["dev"],
                        "priority": "high",
                        "sticky": True,
                        "ttl_min": 10080,
                        "expires_at": "2026-12-31T00:00:00Z",
                        "msg": "focus api contract first",
                        "status": "open",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "dev",
                    str(workspace),
                    str(workspace / "state"),
                    str(workspace / "memory/agents"),
                    str(workspace / "docs/ops/ADMIN_TEAM_CHAT.md"),
                    str(workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md"),
                    str(workspace / "docs/ops/DIRECTIVE_BUS.jsonl"),
                    str(workspace / "logs/dev.live.log"),
                    str(workspace / "state/dev.last_contract"),
                    "queue_v_test",
                    "workboard_v_test",
                    "1",
                    "0",
                    "0",
                    str(workspace / "docs/ops/AGENT_MESSAGE_BUS.jsonl"),
                    "5",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            out = cp.stdout.strip()
            self.assertIn("RUNTIME_CONTEXT:", out)
            self.assertIn("queue_has_ready=1", out)
            self.assertIn("ready_items=BATCH-02:Implement status propagation", out)
            self.assertIn("blocked_items=BATCH-01:NEEDS_QA", out)
            self.assertIn("workboard_role_has_ready=0", out)
            # DEV wait is role-scoped: global queue READY does not force dev claim.
            self.assertIn("dev_wait_allowed=1", out)
            self.assertIn("self_last_contract=self:status=IN_PROGRESS", out)
            self.assertIn("peer_contracts=qa:status=IN_PROGRESS", out)
            self.assertIn("directives_tail=DIR-001:policy:prioritize batch02", out)

    def test_context_injects_only_undelivered_agent_messages(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "docs/orchestrator-ops").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/product/planning").mkdir(parents=True, exist_ok=True)
            (workspace / "state").mkdir(parents=True, exist_ok=True)
            (workspace / "memory/agents").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/ops").mkdir(parents=True, exist_ok=True)
            (workspace / "logs").mkdir(parents=True, exist_ok=True)

            (workspace / "docs/orchestrator-ops/priority-queue.json").write_text(
                json.dumps({"items": []}), encoding="utf-8"
            )
            (workspace / "docs/product/planning/WORKSTATE.md").write_text("none\n", encoding="utf-8")
            (workspace / "state/dev.last_contract").write_text(
                "STATUS: IN_PROGRESS\nDELTA: DEV_TICK\nNEXT_ACTION_UNIQUE: DEV_ACTION\n", encoding="utf-8"
            )
            (workspace / "memory/agents/dev.md").write_text("# dev\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_CHAT.md").write_text("chat line\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md").write_text("iter line\n", encoding="utf-8")
            (workspace / "logs/dev.live.log").write_text("trace line\n", encoding="utf-8")
            (workspace / "docs/ops/DIRECTIVE_BUS.jsonl").write_text("", encoding="utf-8")

            bus_lines = [
                {
                    "event": "message_posted",
                    "ts": "2026-03-04T12:00:00Z",
                    "message_id": "MSG_TEST_DEV_OPEN",
                    "from": "admin",
                    "targets": ["dev"],
                    "priority": "high",
                    "sticky": True,
                    "ttl_min": 10080,
                    "expires_at": "2027-03-04T12:00:00Z",
                    "msg": "corriger le contrat channels_read",
                },
                {
                    "event": "message_posted",
                    "ts": "2026-03-04T12:01:00Z",
                    "message_id": "MSG_TEST_DEV_DONE",
                    "from": "admin",
                    "targets": ["dev"],
                    "priority": "normal",
                    "sticky": True,
                    "ttl_min": 10080,
                    "expires_at": "2027-03-04T12:01:00Z",
                    "msg": "old message",
                },
                {
                    "event": "message_delivered",
                    "ts": "2026-03-04T12:02:00Z",
                    "message_id": "MSG_TEST_DEV_DONE",
                    "role": "dev",
                    "tick_id": "T123",
                },
                {
                    "event": "message_posted",
                    "ts": "2026-03-04T12:03:00Z",
                    "message_id": "MSG_TEST_DEV_CLOSED",
                    "from": "admin",
                    "targets": ["dev"],
                    "priority": "normal",
                    "sticky": True,
                    "ttl_min": 10080,
                    "expires_at": "2027-03-04T12:03:00Z",
                    "msg": "already closed",
                },
                {
                    "event": "message_closed",
                    "ts": "2026-03-04T12:04:00Z",
                    "message_id": "MSG_TEST_DEV_CLOSED",
                    "reason": "resolved_by_operator",
                },
            ]
            bus_path = workspace / "docs/ops/AGENT_MESSAGE_BUS.jsonl"
            bus_path.write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in bus_lines) + "\n",
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "dev",
                    str(workspace),
                    str(workspace / "state"),
                    str(workspace / "memory/agents"),
                    str(workspace / "docs/ops/ADMIN_TEAM_CHAT.md"),
                    str(workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md"),
                    str(workspace / "docs/ops/DIRECTIVE_BUS.jsonl"),
                    str(workspace / "logs/dev.live.log"),
                    str(workspace / "state/dev.last_contract"),
                    "queue_v_test",
                    "workboard_v_test",
                    "0",
                    "0",
                    "0",
                    str(bus_path),
                    "3",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            out = cp.stdout.strip()
            self.assertIn("agent_messages_tail=MSG:MSG_TEST_DEV_OPEN:from=admin:corriger le contrat channels_read", out)
            self.assertIn("agent_message_ids=MSG_TEST_DEV_OPEN", out)
            self.assertIn("dev_wait_allowed=1", out)
            self.assertNotIn("MSG_TEST_DEV_DONE", out)
            self.assertNotIn("MSG_TEST_DEV_CLOSED", out)

    def test_runner_contains_planner_preflight_sync_contract(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_PLANNER_PREFLIGHT_SYNC", text)
        self.assertIn("TMUX_ROLE_PLANNER_PREFLIGHT_SYNC_TIMEOUT_SECONDS", text)
        self.assertIn("TMUX_ROLE_PLANNER_DEP_POLICY_ENFORCE", text)
        self.assertIn("planner_preflight_sync_if_needed()", text)
        self.assertIn(
            'python3 platform/automation/runtime/planner/planner_runtime_actions.py sanitize-dependencies --queue ${CANONICAL_QUEUE_FILE} --all-batches',
            text,
        )
        self.assertIn(
            'python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --queue ${CANONICAL_QUEUE_FILE}',
            text,
        )
        self.assertIn(
            'python3 platform/automation/runtime/planner/planner_runtime_actions.py reconcile-state --queue ${CANONICAL_QUEUE_FILE}',
            text,
        )
        self.assertIn(
            'python3 platform/automation/runtime/planner/planner_runtime_actions.py planner-autobatch --queue ${CANONICAL_QUEUE_FILE} --reason idle_no_ready --cooldown-s ${TMUX_ROLE_PLANNER_IDLE_AUTOBATCH_COOLDOWN_S} --allow-active-queued',
            text,
        )
        self.assertIn(
            'python3 platform/automation/runtime/planner/planner_runtime_actions.py complete --role planner --task <task_id>',
            text,
        )
        self.assertIn("PLANNER_AUTOBATCH_ATTEMPTED", text)
        self.assertIn("PLANNER_AUTOBATCH_RC", text)
        self.assertIn("PLANNER_AUTOBATCH_BATCH_ID", text)
        self.assertIn("PLANNER_DEP_SANITIZE_ATTEMPTED", text)
        self.assertIn("PLANNER_DEP_DECOUPLED_TOTAL", text)
        self.assertIn("PLANNER_DEP_WAITING_RECLASSIFIED", text)
        self.assertIn("PLANNER_DEP_SANITIZE_RC", text)
        self.assertIn("PLANNER_SYNC_PRIORITY_ATTEMPTED", text)
        self.assertIn("PLANNER_SYNC_PRIORITY_STREAMS_CREATED", text)
        self.assertIn("PLANNER_SYNC_PRIORITY_TASKS_CREATED", text)
        self.assertIn(
            "Source de vérité runtime: SQLite/planner graph; priority-queue.json et parallel-workstreams.json sous logs-codex-runs/orchestrator-state restent uniquement des projections compatibles de travail.",
            text,
        )

    def test_runner_contains_planner_anti_passivity_reconcile_logic(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_PLANNER_NEVER_WAIT", text)
        self.assertIn("TMUX_ROLE_PLANNER_IDLE_AUTOBATCH", text)
        self.assertIn('task_update in {"none_no_ready", "none_no_signal"}', text)
        self.assertIn('values["DELTA"] = "PLANNER_PROGRESS_REQUIRED"', text)
        self.assertIn('values["NEXT"] = "owner=planner; action=claim READY planner task or create one auto batch now"', text)
        self.assertIn('evidence_pairs["planner_action_required"] = "create_or_claim"', text)
        self.assertIn('evidence_pairs["planner_runtime_exception"] = "1"', text)

    def test_runner_contains_planner_dependency_policy_reconcile_logic(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("queue_waiting_dep = 0", text)
        self.assertIn('values["DELTA"] = "DEPENDENCY_POLICY_ENFORCEMENT_REQUIRED"', text)
        self.assertIn(
            'values["NEXT"] = "owner=planner; action=run sanitize-dependencies then sync-priority and regroup into same batch tasks"',
            text,
        )
        self.assertIn('evidence_pairs["planner_action_required"] = "dependency_regroup"', text)
        self.assertIn("batch_dependency_policy", text)

    def test_runner_contains_dev_channels_impact_requirements(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("Si task_update=analysis_only|none_no_ready|none_no_signal: ajouter obligatoirement channels_read, impact_assessment, impact_action.", text)
        self.assertIn("- si task_update in {analysis_only,none_no_ready,none_no_signal}: channels_read + impact_assessment + impact_action obligatoires", text)
        self.assertIn("load_dev_adaptive_coaching_prompt()", text)
        self.assertIn("DEV_COACHING_CHANNELS_READ", text)
        self.assertIn("DEV_COACHING_ANTI_STALL", text)

    def test_runner_contains_admin_tshape_takeover_runtime_contract(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_ENABLED", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_TRIGGER", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_SCOPE", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_EXIT_POLICY", text)
        self.assertIn("ADMIN_TSHAPE_STATE_FILE", text)
        self.assertIn("admin_tshape_preflight_if_needed()", text)
        self.assertIn("admin.tshape.state.json", text)
        self.assertIn("python3 platform/automation/runtime/planner/planner_runtime_actions.py sync-priority --queue logs-codex-runs/orchestrator-state/priority-queue.json", text)
        self.assertIn("python3 platform/automation/runtime/planner/planner_runtime_actions.py enforce-sla --board ${CANONICAL_WORKBOARD_FILE} --queue ${CANONICAL_QUEUE_FILE} --apply", text)
        self.assertIn('values["DELTA"] = "READY_ITEM_AVAILABLE_RUNTIME_CONTEXT"', text)
        self.assertIn('values["NEXT"] = f"owner=admin; action=execute takeover on {target} until blocker resolved"', text)
        self.assertIn('"takeover_mode"', text)
        self.assertIn('"takeover_target_role"', text)
        self.assertIn('"takeover_reason"', text)
        self.assertIn('"takeover_actions"', text)
        self.assertIn('"takeover_exit_condition"', text)

    def test_runner_contains_fallback_channels_autofill_contract(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("FALLBACK_CHANNELS_ISSUE_CODE", text)
        self.assertIn("channels_read=${FALLBACK_CHANNELS_READ}", text)
        self.assertIn("impact_assessment=${FALLBACK_IMPACT_ASSESSMENT}", text)
        self.assertIn("impact_action=${FALLBACK_IMPACT_ACTION}", text)
        self.assertIn("issues=signal_unparseable,${FALLBACK_CHANNELS_ISSUE_CODE}", text)
        self.assertIn("issues=rate_limit_detected,${FALLBACK_CHANNELS_ISSUE_CODE}", text)

    def test_runner_contains_actionability_fallback_telemetry(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_ACTIONABILITY_FORCE_THRESHOLD", text)
        self.assertIn("ACTIONABILITY_FORCE_THRESHOLD", text)
        self.assertIn('evidence_pairs.setdefault("fallback_reason", "passive_no_signal_on_active_lane")', text)
        self.assertIn('evidence_pairs.setdefault("fallback_count_window", str(no_delta_count_window))', text)
        self.assertIn('evidence_pairs.setdefault("actionability_state", "monitor_only")', text)
        self.assertIn('evidence_pairs["actionability_state"] = "forced_actionable_step"', text)
        self.assertIn('fallback_reason=checkpoint_signal_unparseable', text)
        self.assertIn('fallback_count_window=${FAIL_COUNT}/${RECOVERY_THRESHOLD}', text)
        self.assertIn('actionability_state=fallback_checkpoint', text)

    def test_runner_contains_agent_message_emit_and_ack_close_flow(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("message_to_<planner|dev|admin>", text)
        self.assertIn("extract_message_bus_intents_from_evidence()", text)
        self.assertIn("agent_msg_emit", text)
        self.assertIn("agent_msg_deliver", text)
        self.assertIn("agent_msg_action", text)
        self.assertIn("agent_msg_close", text)
        self.assertIn("message_ack=MSG-001:resolved", text)

    def test_runner_contains_admin_tshape_takeover_contract(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_ENABLED", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_TRIGGER", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_BLOCKED_THRESHOLD", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_SCOPE", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_EXIT_POLICY", text)
        self.assertIn("TMUX_ROLE_ADMIN_TSHAPE_ALLOWED_TARGETS", text)
        self.assertIn("admin_tshape_preflight_if_needed()", text)
        self.assertIn("takeover_mode=1", text)
        self.assertIn("takeover_target_role=<planner|dev>", text)
        self.assertIn("takeover_reason=<blocker_id>", text)
        self.assertIn("takeover_actions=<sync|claim|complete|handoff>", text)
        self.assertIn("takeover_exit_condition=resolved", text)
        self.assertIn("admin_artifact=<preuve>", text)
        self.assertIn("admin.tshape.state.json", text)
        self.assertIn("blocked_roles", text)

    def test_runner_reconcile_forces_takeover_on_admin_passive_output(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("admin_tshape_active = str(sys.argv[19] or \"0\").strip() == \"1\"", text)
        self.assertIn("if role == \"admin\":", text)
        self.assertIn("if admin_tshape_active:", text)
        self.assertIn("if task_update in {\"none_no_ready\", \"none_no_signal\"}:", text)
        self.assertIn("values[\"DELTA\"] = \"READY_ITEM_AVAILABLE_RUNTIME_CONTEXT\"", text)
        self.assertIn("values[\"NEXT\"] = f\"owner=admin; action=execute takeover on {target} until blocker resolved\"", text)
        self.assertIn("evidence_pairs[\"takeover_actions\"] = \"sync,claim,complete,handoff\"", text)
        self.assertIn("values[\"BLOCKER_ID\"] = \"NONE\"", text)

    def test_runner_session_not_ready_falls_back_to_codex_exec(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_SESSION_NOT_READY_FALLBACK_CODEX", text)
        self.assertIn("SESSION_NOT_READY_FALLBACK_CODEX", text)
        self.assertIn("session_not_ready_fallback_codex", text)
        self.assertIn("codex_exec_prompt_once", text)
        self.assertIn("return 43", text)

    def test_context_includes_agent_message_tail_and_ids(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "docs/orchestrator-ops").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/product/planning").mkdir(parents=True, exist_ok=True)
            (workspace / "state").mkdir(parents=True, exist_ok=True)
            (workspace / "memory/agents").mkdir(parents=True, exist_ok=True)
            (workspace / "docs/ops").mkdir(parents=True, exist_ok=True)
            (workspace / "logs").mkdir(parents=True, exist_ok=True)

            (workspace / "docs/orchestrator-ops/priority-queue.json").write_text(
                json.dumps({"items": []}), encoding="utf-8"
            )
            (workspace / "docs/product/planning/WORKSTATE.md").write_text("runtime context\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_CHAT.md").write_text("chat\n", encoding="utf-8")
            (workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md").write_text("iter\n", encoding="utf-8")
            (workspace / "state/dev.last_contract").write_text(
                "STATUS: PASS\nDELTA: NO_DELTA\nNEXT_ACTION_UNIQUE: owner=dev; action=none\n",
                encoding="utf-8",
            )
            message_bus = workspace / "docs/ops/AGENT_MESSAGE_BUS.jsonl"
            message_bus.write_text(
                json.dumps(
                    {
                        "event": "message_posted",
                        "message_id": "MSG_20260304T120000Z_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                        "ts_utc": "2026-03-04T12:00:00Z",
                        "source": "po_scrum_master",
                        "targets": ["dev"],
                        "priority": "high",
                        "sticky": True,
                        "ttl_min": 120,
                        "expires_at_utc": "2099-01-01T00:00:00Z",
                        "payload": "fix contract parse",
                        "role": "",
                        "tick_id": "",
                        "action_status": "",
                        "note": "",
                        "close_reason": "",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "dev",
                    str(workspace),
                    str(workspace / "state"),
                    str(workspace / "memory/agents"),
                    str(workspace / "docs/ops/ADMIN_TEAM_CHAT.md"),
                    str(workspace / "docs/ops/ADMIN_TEAM_ITERATIONS.md"),
                    str(workspace / "docs/ops/DIRECTIVE_BUS.jsonl"),
                    str(workspace / "logs/dev.live.log"),
                    str(workspace / "state/dev.last_contract"),
                    "queue_v_test",
                    "workboard_v_test",
                    "0",
                    "0",
                    "0",
                    str(message_bus),
                    "10",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stderr)
            out = cp.stdout.strip()
            self.assertIn("agent_messages_tail=", out)
            self.assertIn("MSG_20260304T120000Z_01ARZ3NDEKTSV4RRFFQ69G5FAV", out)
            self.assertIn("agent_message_ids=MSG_20260304T120000Z_01ARZ3NDEKTSV4RRFFQ69G5FAV", out)

    def test_runner_contains_agent_message_bus_integration(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("AGENT_MESSAGE_BUS_FILE", text)
        self.assertIn("AGENT_MESSAGE_BUS_ENABLED", text)
        self.assertIn("AGENT_MESSAGE_MAX_ACTIVE_PER_ROLE", text)
        self.assertIn("record_agent_message_receipts", text)
        self.assertIn("extract_message_bus_intents_from_evidence", text)
        self.assertIn("agent_message_ids", text)
        self.assertIn("message_ack", text)

    def test_runner_contains_po_scrum_master_manual_mode_flag(self) -> None:
        text = RUNNER_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("TMUX_ROLE_ENABLE_PO_SCRUM_MASTER", text)
        self.assertIn("ROLE=scrum_master", text)
        self.assertIn("po_scrum_master", text)
        self.assertIn("Ne jamais émettre un hard blocker", text)


if __name__ == "__main__":
    unittest.main()
