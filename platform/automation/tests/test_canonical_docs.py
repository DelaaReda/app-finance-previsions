from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CANONICAL_DOCS = [
    ROOT / "docs" / "ops" / "AGENT_WORKSPACE_INDEX.md",
    ROOT / "docs" / "ops" / "CURRENT_ARCHITECTURE_ENTRYPOINTS.md",
    ROOT / "docs" / "ops" / "PLANNER_ORCHESTRATOR_TARGET_SPEC.md",
    ROOT / "docs" / "product" / "planning" / "PLANNER_ORCHESTRATOR_EXECUTION_BATCHES.md",
]


class CanonicalDocsTests(unittest.TestCase):
    def test_canonical_docs_have_metadata_header(self) -> None:
        for path in CANONICAL_DOCS:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), msg=f"missing front matter: {path}")
            self.assertIn("status: canonical", text, msg=f"missing canonical status: {path}")
            self.assertIn("last_verified:", text, msg=f"missing last_verified: {path}")

    def test_canonical_docs_avoid_removed_legacy_reference(self) -> None:
        for path in CANONICAL_DOCS:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("platform.legacy.jobs.forecasts", text, msg=f"legacy runtime reference leaked into {path}")


if __name__ == "__main__":
    unittest.main()
