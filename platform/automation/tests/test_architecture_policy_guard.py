from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from platform.policies.architecture_policy_guard import evaluate_repo


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _bootstrap_active_docs(root: Path, extra_links: list[str] | None = None) -> None:
    extra_links = extra_links or []
    _write(
        root / "docs/ops/ACTIVE_DOCS_INDEX.md",
        "\n".join(
            [
                "# Active docs",
                "",
                "- [Canonical Runtime Mode](docs/ops/CANONICAL_RUNTIME_MODE.md)",
                "- [Active Docs Index](docs/ops/ACTIVE_DOCS_INDEX.md)",
                "- [Boundary](docs/ops/APP_VS_AGENT_PROVIDER_BOUNDARY.md)",
                "- [Commit Policy](docs/ops/COMMIT_ONLY_WORKFLOW_POLICY.md)",
                *extra_links,
                "",
            ]
        ),
    )
    _write(root / "docs/ops/CANONICAL_RUNTIME_MODE.md", "status: active\n")
    _write(root / "docs/ops/APP_VS_AGENT_PROVIDER_BOUNDARY.md", "status: active\n")
    _write(root / "docs/ops/COMMIT_ONLY_WORKFLOW_POLICY.md", "status: active\n")


class ArchitecturePolicyGuardTests(unittest.TestCase):
    def test_active_doc_cannot_couple_finance_copilot_to_openclaw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bootstrap_active_docs(root, extra_links=["- [Bad](docs/ops/BAD.md)"])
            _write(
                root / "docs/ops/BAD.md",
                "status: active\n\n- finance-copilot.sh start requires OpenClaw gateway healthy before launch.\n",
            )

            payload = evaluate_repo(root)

            self.assertEqual(payload["status"], "degraded")
            self.assertTrue(
                any(item["code"] == "active_doc_couples_finance_copilot_to_openclaw" for item in payload["violations"])
            )

    def test_active_doc_can_reference_both_without_dependency_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _bootstrap_active_docs(root, extra_links=["- [Note](docs/ops/NOTE.md)"])
            _write(
                root / "docs/ops/NOTE.md",
                "\n".join(
                    [
                        "status: active",
                        "",
                        "- finance-copilot.sh start is the canonical launcher.",
                        "- OpenClaw remains operator-plane infrastructure only.",
                        "",
                    ]
                ),
            )

            payload = evaluate_repo(root)

            self.assertEqual(payload["status"], "ok")
            self.assertFalse(
                any(item["code"] == "active_doc_couples_finance_copilot_to_openclaw" for item in payload["violations"])
            )
