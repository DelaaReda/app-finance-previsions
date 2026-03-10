from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "platform" / "automation" / "product_priority_guard.py"
SPEC = importlib.util.spec_from_file_location("product_priority_guard_test_module", MODULE_PATH)
assert SPEC and SPEC.loader
product_priority_guard = importlib.util.module_from_spec(SPEC)
sys.modules["product_priority_guard_test_module"] = product_priority_guard
SPEC.loader.exec_module(product_priority_guard)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


class ProductPriorityGuardTests(unittest.TestCase):
    def test_product_priority_guard_blocks_when_p0_product_is_broken(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data" / "stocks").mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)

            (root / "data" / "forecasts.json").write_text(
                json.dumps(
                    {
                        "generated_at": _iso(now),
                        "last_update": _iso(now),
                        "source": ["forecasts_route", "critical_error_fallback"],
                        "data": {"rows": [{"ticker": "AAPL", "source": ["critical_error_fallback"]}]},
                    }
                ),
                encoding="utf-8",
            )
            for rel in ("news_feed.json", "brief_daily.json", "backtests.json", "stocks/prices.json"):
                path = root / "data" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({"generated_at": _iso(now), "last_update": _iso(now), "data": {}}),
                    encoding="utf-8",
                )
            orch = root / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "parallel-workstreams.json").write_text(json.dumps({"streams": [], "tasks": []}), encoding="utf-8")

            with patch.object(
                product_priority_guard,
                "_copilot_metrics",
                return_value={"status": "fallback", "usable": False, "fallback": True, "source_count": 0},
            ):
                metrics = product_priority_guard.build_product_value_metrics(root, api_base_url=None, now=now)

            guard = metrics["priority_guard"]
            self.assertEqual(guard["status"], "blocked")
            self.assertTrue(guard["p0_broken"])
            self.assertIn("copilot_unusable", guard["blocked_reasons"])
            self.assertIn("forecasts_invalid", guard["blocked_reasons"])

    def test_delivery_mix_exposes_product_vs_orchestration_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "streams": [
                            {"id": "BATCH-10", "state": "READY", "title": "Improve copilot answer quality"},
                            {"id": "BATCH-11", "state": "IN_PROGRESS", "title": "Fix runtime contract guard"},
                        ],
                        "tasks": [
                            {"id": "BATCH-10-DEV-01", "state": "READY", "title": "Patch forecast endpoint", "code": "DEV"},
                            {"id": "BATCH-11-PLAN", "state": "IN_PROGRESS", "title": "Clean cron lock orchestration", "code": "PLAN"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            for rel in ("data/forecasts.json", "data/news_feed.json", "data/brief_daily.json", "data/backtests.json", "data/stocks/prices.json"):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"generated_at": _iso(datetime.now(timezone.utc))}), encoding="utf-8")

            with patch.object(
                product_priority_guard,
                "_copilot_metrics",
                return_value={"status": "ok", "usable": True, "fallback": False, "source_count": 3},
            ):
                metrics = product_priority_guard.build_product_value_metrics(root, api_base_url=None)

            mix = metrics["delivery_mix"]
            self.assertEqual(mix["product_active_count"], 2)
            self.assertEqual(mix["orchestration_active_count"], 2)
            self.assertEqual(mix["classified_total"], 4)
            self.assertAlmostEqual(mix["product_ratio"], 0.5, places=3)

    def test_forecasts_can_be_degraded_but_still_valid_when_model_backed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            now = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)
            (root / "data" / "stocks").mkdir(parents=True, exist_ok=True)
            (root / "data" / "forecasts.json").write_text(
                json.dumps(
                    {
                        "generated_at": _iso(now),
                        "last_update": _iso(now),
                        "freshness_status": "stale",
                        "freshness_age": 1200,
                        "source": ["forecasts_route", "job:forecasts_simple", "yahoo_finance", "forecasts_storage"],
                        "provider_chain": ["simple_momentum_v1", "job:forecasts_simple", "yahoo_finance"],
                        "fallback_used": True,
                        "rows": [{"ticker": "AAPL", "source": ["job:forecasts_simple", "yahoo_finance"]}],
                    }
                ),
                encoding="utf-8",
            )
            for rel in ("news_feed.json", "brief_daily.json", "backtests.json", "stocks/prices.json"):
                path = root / "data" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({"generated_at": _iso(now), "last_update": _iso(now), "data": {}}),
                    encoding="utf-8",
                )
            orch = root / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "parallel-workstreams.json").write_text(json.dumps({"streams": [], "tasks": []}), encoding="utf-8")

            with patch.object(
                product_priority_guard,
                "_copilot_metrics",
                return_value={"status": "ok", "usable": True, "fallback": False, "source_count": 3},
            ):
                metrics = product_priority_guard.build_product_value_metrics(root, api_base_url=None, now=now)

            self.assertEqual(metrics["forecasts"]["status"], "degraded")
            self.assertTrue(metrics["forecasts"]["valid"])
            self.assertEqual(metrics["priority_guard"]["status"], "ok")

    def test_news_freshness_matches_ingestion_contract_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            now = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)
            stale_news = now - timedelta(minutes=61)
            (root / "data" / "stocks").mkdir(parents=True, exist_ok=True)

            (root / "data" / "forecasts.json").write_text(
                json.dumps(
                    {
                        "generated_at": _iso(now),
                        "last_update": _iso(now),
                        "source": ["forecasts_route"],
                        "rows": [{"ticker": "AAPL"}],
                    }
                ),
                encoding="utf-8",
            )
            (root / "data" / "news_feed.json").write_text(
                json.dumps(
                    {
                        "generated_at": _iso(stale_news),
                        "last_update": _iso(stale_news),
                        "articles": [],
                    }
                ),
                encoding="utf-8",
            )
            for rel in ("brief_daily.json", "backtests.json", "stocks/prices.json"):
                path = root / "data" / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps({"generated_at": _iso(now), "last_update": _iso(now), "data": {}}),
                    encoding="utf-8",
                )
            orch = root / "docs" / "operations" / "orchestrator"
            orch.mkdir(parents=True, exist_ok=True)
            (orch / "parallel-workstreams.json").write_text(json.dumps({"streams": [], "tasks": []}), encoding="utf-8")

            with patch.object(
                product_priority_guard,
                "_copilot_metrics",
                return_value={"status": "ok", "usable": True, "fallback": False, "source_count": 3},
            ):
                metrics = product_priority_guard.build_product_value_metrics(root, api_base_url=None, now=now)

            self.assertEqual(metrics["data_freshness"]["news"]["threshold_s"], 1800)
            self.assertEqual(metrics["data_freshness"]["news"]["state"], "stale")
            self.assertIn("news_stale", metrics["priority_guard"]["blocked_reasons"])

    def test_delivery_integrity_detects_missing_commit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 6, 12, 0, tzinfo=timezone.utc)

            proof_ok = proofs / "proof-ok.yaml"
            proof_ok.write_text(
                'validations:\n  tests:\n    - result: "PASS"\noutputs:\n  artifacts:\n    - "abcdef1"\n',
                encoding="utf-8",
            )
            proof_bad = proofs / "proof-bad.yaml"
            proof_bad.write_text(
                'validations:\n  tests:\n    - result: "PASS"\noutputs:\n  artifacts:\n    - "docs/notes.md"\n',
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(hours=1)),
                                "details": {
                                    "task_id": "BATCH-10-DEV-01",
                                    "artifact": "abcdef1",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/proof-ok.yaml",
                                },
                            },
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=30)),
                                "details": {
                                    "task_id": "BATCH-11-DEV-01",
                                    "artifact": "docs/notes.md",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/proof-bad.yaml",
                                },
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "degraded")
            self.assertEqual(metrics["recent_completions"], 2)
            self.assertEqual(metrics["suspicious_completion_count"], 1)
            self.assertIn("BATCH-11-DEV-01", metrics["suspicious_task_ids"])

    def test_delivery_integrity_ignores_planner_doc_only_completions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-58" / "BATCH-58-ANALYSIS"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 7, 2, 30, tzinfo=timezone.utc)

            proof_doc = proofs / "proof-doc.yaml"
            proof_doc.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        '      evidence: "NONE(planner_doc_only)"',
                        'outputs:',
                        '  artifacts:',
                        '    - "docs/operations/orchestrator/proofs/BATCH-58-ANALYSIS.md"',
                    ]
                ),
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-58-ANALYSIS",
                                "role": "planner",
                                "artifact": "docs/operations/orchestrator/proofs/BATCH-58-ANALYSIS.md",
                                "commit_sha": "NONE(doc_only)",
                                "tests_run": "SKIP(planner_doc_only)",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=5)),
                                "details": {
                                    "task_id": "BATCH-58-ANALYSIS",
                                    "artifact": "docs/operations/orchestrator/proofs/BATCH-58-ANALYSIS.md",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-58/BATCH-58-ANALYSIS/proof-doc.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["recent_completions"], 0)
            self.assertEqual(metrics["suspicious_completion_count"], 0)

    def test_delivery_integrity_ignores_planner_workboard_only_completions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-60" / "BATCH-60-PLAN"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 8, 21, 45, tzinfo=timezone.utc)

            proof_doc = proofs / "proof-workboard.yaml"
            proof_doc.write_text(
                '\n'.join(
                    [
                        'execution:',
                        '  commands:',
                        '    - cmd: "SKIP(planner_workboard_only)"',
                        'validations:',
                        '  tests:',
                        '    - result: "SKIP"',
                        '      evidence: "SKIP(planner_workboard_only)"',
                        'outputs:',
                        '  artifacts:',
                        '    - "docs/operations/orchestrator/parallel-workstreams.json"',
                    ]
                ),
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-60-PLAN",
                                "role": "planner",
                                "title": "Build a personal finance copilot [PLAN]",
                                "artifact": "docs/operations/orchestrator/parallel-workstreams.json",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=5)),
                                "details": {
                                    "task_id": "BATCH-60-PLAN",
                                    "artifact": "docs/operations/orchestrator/parallel-workstreams.json",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-60/BATCH-60-PLAN/proof-workboard.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["recent_completions"], 0)
            self.assertEqual(metrics["browser_proof_required_count"], 0)
            self.assertEqual(metrics["suspicious_completion_count"], 0)

    def test_delivery_integrity_accepts_task_commit_sha_without_manifest_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-27" / "BATCH-27-DEV-02"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 7, 3, 0, tzinfo=timezone.utc)

            proof_file = proofs / "proof-task-commit.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        '      evidence: "node --check apps/web/src/domains/forecasts/pages/app.js"',
                        'outputs:',
                        '  artifacts:',
                        '    - "apps/web/src/domains/forecasts/pages/app.js"',
                    ]
                ),
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-27-DEV-02",
                                "role": "dev",
                                "state": "DONE",
                                "artifact": "apps/web/src/domains/forecasts/pages/app.js",
                                "commit_sha": "554932d6b8215db60ff9c802f6d94ad11f036a7b",
                                "tests_run": "node --check apps/web/src/domains/forecasts/pages/app.js",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=5)),
                                "details": {
                                    "task_id": "BATCH-27-DEV-02",
                                    "artifact": "apps/web/src/domains/forecasts/pages/app.js",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-27/BATCH-27-DEV-02/proof-task-commit.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["recent_completions"], 1)
            self.assertEqual(metrics["suspicious_completion_count"], 0)

    def test_delivery_integrity_requires_browser_proof_for_web_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-90" / "BATCH-90-DEV-01"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 7, 6, 0, tzinfo=timezone.utc)

            proof_file = proofs / "proof-web.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'outputs:',
                        '  artifacts:',
                        '    - "apps/web/src/pages/dashboard.js"',
                    ]
                ),
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-90-DEV-01",
                                "role": "dev",
                                "state": "DONE",
                                "title": "Update dashboard UI",
                                "artifact": "apps/web/src/pages/dashboard.js",
                                "commit_sha": "abcdef1234567",
                                "tests_run": "npm test -- dashboard",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=5)),
                                "details": {
                                    "task_id": "BATCH-90-DEV-01",
                                    "artifact": "apps/web/src/pages/dashboard.js",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-90/BATCH-90-DEV-01/proof-web.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["browser_proof_required_count"], 1)
            self.assertEqual(metrics["browser_proof_present_count"], 0)
            self.assertIn("BATCH-90-DEV-01", metrics["browser_proof_missing_task_ids"])

    def test_delivery_integrity_does_not_treat_build_as_ui_keyword(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-92" / "BATCH-92-PLAN"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 7, 6, 10, tzinfo=timezone.utc)

            proof_file = proofs / "proof-plan.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        '      evidence: "planner audit"',
                        'outputs:',
                        '  artifacts:',
                        '    - "docs/product/PRODUCT_VISION.md"',
                    ]
                ),
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-92-PLAN",
                                "role": "planner",
                                "state": "DONE",
                                "title": "Build the next planner brief",
                                "artifact": "docs/product/PRODUCT_VISION.md",
                                "commit_sha": "NONE(doc_only)",
                                "tests_run": "SKIP(planner_doc_only)",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=5)),
                                "details": {
                                    "task_id": "BATCH-92-PLAN",
                                    "artifact": "docs/product/PRODUCT_VISION.md",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-92/BATCH-92-PLAN/proof-plan.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["browser_proof_required_count"], 0)

    def test_delivery_integrity_accepts_browser_proof_for_web_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-91" / "BATCH-91-DEV-01"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 7, 6, 5, tzinfo=timezone.utc)

            proof_file = proofs / "proof-web.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'browser_proof=logs-codex-runs/browser-smoke/20260307T060500Z-dashboard.json',
                        'outputs:',
                        '  artifacts:',
                        '    - "apps/monitor/server.py"',
                    ]
                ),
                encoding="utf-8",
            )

            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-91-DEV-01",
                                "role": "dev",
                                "state": "DONE",
                                "title": "Refine monitor dashboard panel",
                                "artifact": "apps/monitor/server.py",
                                "commit_sha": "abcdef1234567",
                                "tests_run": "pytest apps/monitor/tests",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=5)),
                                "details": {
                                    "task_id": "BATCH-91-DEV-01",
                                    "artifact": "apps/monitor/server.py",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-91/BATCH-91-DEV-01/proof-web.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["browser_proof_required_count"], 1)
            self.assertEqual(metrics["browser_proof_present_count"], 1)

    def test_delivery_control_separates_historical_browser_debt_from_future_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 8, 20, 0, tzinfo=timezone.utc)

            old_proof = proofs / "old-web.yaml"
            old_proof.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'outputs:',
                        '  artifacts:',
                        '    - "apps/web/src/pages/dashboard.js"',
                    ]
                ),
                encoding="utf-8",
            )
            new_proof = proofs / "new-api.yaml"
            new_proof.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'outputs:',
                        '  artifacts:',
                        '    - "apps/api/src/service.py"',
                    ]
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-90-DEV-01",
                                "role": "dev",
                                "state": "DONE",
                                "title": "Update dashboard UI",
                                "artifact": "apps/web/src/pages/dashboard.js",
                                "commit_sha": "abcdef1234567",
                                "tests_run": "npm test -- dashboard",
                            },
                            {
                                "id": "BATCH-99-DEV-01",
                                "role": "dev",
                                "state": "DONE",
                                "title": "Patch API contract",
                                "artifact": "apps/api/src/service.py",
                                "commit_sha": "fedcba9876543",
                                "tests_run": "pytest -q",
                                "qa_status": "completed",
                            },
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(datetime(2026, 3, 8, 18, 30, tzinfo=timezone.utc)),
                                "details": {
                                    "task_id": "BATCH-90-DEV-01",
                                    "artifact": "apps/web/src/pages/dashboard.js",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/old-web.yaml",
                                },
                            },
                            {
                                "kind": "complete",
                                "at": _iso(datetime(2026, 3, 8, 19, 30, tzinfo=timezone.utc)),
                                "details": {
                                    "task_id": "BATCH-99-DEV-01",
                                    "artifact": "apps/api/src/service.py",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/new-api.yaml",
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_control_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["integrity_status"], "ok")
            self.assertEqual(metrics["historical_debt"]["count"], 1)
            self.assertEqual(metrics["browser_proof_pipeline"]["status"], "ok")

    def test_delivery_control_marks_future_qa_and_browser_pipeline_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 8, 20, 5, tzinfo=timezone.utc)

            proof_file = proofs / "future-web.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'outputs:',
                        '  artifacts:',
                        '    - "apps/monitor/server.py"',
                    ]
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-100-DEV-01",
                                "role": "dev",
                                "state": "DONE",
                                "title": "Refine monitor panel",
                                "artifact": "apps/monitor/server.py",
                                "commit_sha": "abcdef1234567",
                                "tests_run": "pytest apps/monitor/tests",
                                "qa_status": "running",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(datetime(2026, 3, 8, 19, 45, tzinfo=timezone.utc)),
                                "details": {
                                    "task_id": "BATCH-100-DEV-01",
                                    "artifact": "apps/monitor/server.py",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/future-web.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_control_metrics(root, now=now)
            self.assertEqual(metrics["status"], "degraded")
            self.assertEqual(metrics["qa_review_pipeline"]["status"], "degraded")
            self.assertEqual(metrics["browser_proof_pipeline"]["status"], "degraded")
            self.assertEqual(metrics["pipeline_counts"]["qa_review_pending_count"], 1)
            self.assertEqual(metrics["pipeline_counts"]["browser_validation_pending_count"], 1)

    def test_delivery_integrity_accepts_admin_runtime_no_code_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-27" / "BATCH-27-ADMIN-01"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 8, 21, 0, tzinfo=timezone.utc)

            proof_file = proofs / "proof-runtime.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'outputs:',
                        '  artifacts:',
                        '    - "logs/runtime/admin-repair.log"',
                    ]
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-27-ADMIN-01",
                                "role": "admin",
                                "state": "DONE",
                                "title": "Repair runtime session state",
                                "artifact": "logs/runtime/admin-repair.log",
                                "verify": "before=broken; after=healthy; test=doctor",
                                "tests_run": "bash scripts/fc_doctor.sh",
                                "completion_mode": "runtime_no_code",
                                "no_code_change_reason": "runtime_repair_no_code_change",
                                "runtime_artifact": "logs/runtime/admin-repair.log",
                                "commit_sha": "NONE(runtime_no_code)",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=5)),
                                "details": {
                                    "task_id": "BATCH-27-ADMIN-01",
                                    "artifact": "logs/runtime/admin-repair.log",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-27/BATCH-27-ADMIN-01/proof-runtime.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["suspicious_completion_count"], 0)

    def test_delivery_integrity_infers_admin_runtime_no_code_from_skip_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs" / "BATCH-28" / "BATCH-28-ADMIN-01"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 8, 21, 20, tzinfo=timezone.utc)

            proof_file = proofs / "proof-runtime.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'outputs:',
                        '  artifacts:',
                        '    - "docs/operations/orchestrator/proofs/runtime-gate/runtime-e2e.json"',
                    ]
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-28-ADMIN-01",
                                "role": "admin",
                                "state": "DONE",
                                "title": "Release gate runtime validation",
                                "artifact": "docs/operations/orchestrator/proofs/runtime-gate/runtime-e2e.json",
                                "verify": "before=stale; after=healthy; test=runtime_gate",
                                "tests_run": "bash scripts/runtime_e2e_gate.sh",
                                "commit_sha": "SKIP(no code/config change)",
                            }
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(now - timedelta(minutes=3)),
                                "details": {
                                    "task_id": "BATCH-28-ADMIN-01",
                                    "artifact": "docs/operations/orchestrator/proofs/runtime-gate/runtime-e2e.json",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/BATCH-28/BATCH-28-ADMIN-01/proof-runtime.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_integrity_metrics(root, now=now)
            self.assertEqual(metrics["status"], "ok")
            self.assertEqual(metrics["suspicious_completion_count"], 0)

    def test_delivery_control_exposes_historical_browser_backfill_and_capability_stalls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            orch = root / "docs" / "operations" / "orchestrator"
            proofs = orch / "proofs"
            proofs.mkdir(parents=True, exist_ok=True)
            now = datetime(2026, 3, 8, 21, 10, tzinfo=timezone.utc)

            proof_file = proofs / "historical-web.yaml"
            proof_file.write_text(
                '\n'.join(
                    [
                        'validations:',
                        '  tests:',
                        '    - result: "PASS"',
                        'outputs:',
                        '  artifacts:',
                        '    - "apps/monitor/server.py"',
                    ]
                ),
                encoding="utf-8",
            )
            (orch / "parallel-workstreams.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "BATCH-91-DEV-01",
                                "role": "dev",
                                "state": "DONE",
                                "title": "Refine monitor dashboard",
                                "artifact": "apps/monitor/server.py",
                                "commit_sha": "abcdef1234567",
                                "tests_run": "pytest apps/monitor/tests",
                            },
                            {
                                "id": "BATCH-27-ADMIN-01",
                                "role": "admin",
                                "state": "READY",
                                "title": "Repair runtime drift",
                                "stalled_capability_reason": "admin_timeout_streak:2",
                                "admin_timeout_streak": 2,
                                "planner_takeover_required": True,
                            },
                        ],
                        "events": [
                            {
                                "kind": "complete",
                                "at": _iso(datetime(2026, 3, 8, 18, 30, tzinfo=timezone.utc)),
                                "details": {
                                    "task_id": "BATCH-91-DEV-01",
                                    "artifact": "apps/monitor/server.py",
                                    "proof_manifest": "docs/operations/orchestrator/proofs/historical-web.yaml",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            metrics = product_priority_guard.build_delivery_control_metrics(root, now=now)
            self.assertEqual(metrics["browser_proof_backfill_queue"]["count"], 1)
            self.assertEqual(metrics["capability_stall_summary"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
