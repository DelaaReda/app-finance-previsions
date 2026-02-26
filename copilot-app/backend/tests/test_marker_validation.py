"""Test module to validate marker.txt files in backend/.qwen_runs."""

from __future__ import annotations

from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = BACKEND_ROOT / ".qwen_runs"
MARKER_PATHS = sorted(RUNS_DIR.glob("*/marker.txt"))


def _parse_marker(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8").strip()
    data: dict[str, str] = {}
    for line in content.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key] = value
    return data


@pytest.mark.skipif(not MARKER_PATHS, reason="No marker.txt found in backend/.qwen_runs")
def test_marker_file_exists():
    """Each discovered marker file must exist and be non-empty."""
    for marker_path in MARKER_PATHS:
        assert marker_path.exists(), f"Marker file missing: {marker_path}"
        assert marker_path.stat().st_size > 0, f"Marker file is empty: {marker_path}"


@pytest.mark.skipif(not MARKER_PATHS, reason="No marker.txt found in backend/.qwen_runs")
def test_marker_contains_matching_run_id():
    """run_id in marker content should match the parent folder name."""
    for marker_path in MARKER_PATHS:
        run_id = marker_path.parent.name
        content = marker_path.read_text(encoding="utf-8")
        assert f"run_id={run_id}" in content, f"Expected run_id={run_id} not found in {marker_path}"


@pytest.mark.skipif(not MARKER_PATHS, reason="No marker.txt found in backend/.qwen_runs")
@pytest.mark.parametrize("marker_path", MARKER_PATHS, ids=lambda p: p.parent.name)
def test_marker_format(marker_path: Path):
    """Marker file should expose stable key/value fields."""
    lines = marker_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 2, f"Marker file should have >=2 lines: {marker_path}"

    content_dict = _parse_marker(marker_path)
    assert "run_id" in content_dict, f"Missing run_id in {marker_path}"
    assert content_dict["run_id"] == marker_path.parent.name, f"Incorrect run_id in {marker_path}"
    assert "created_at" in content_dict, f"Missing created_at in {marker_path}"
