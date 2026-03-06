from __future__ import annotations

from pathlib import Path

from apps.monitor.src.collectors import detect_data_source


def test_detect_data_source_unknown_when_no_files(tmp_path: Path):
    source, freshness = detect_data_source([], tmp_path / "missing.json")
    assert source == "unknown"
    assert freshness == -1


def test_detect_data_source_runtime_snapshot(tmp_path: Path):
    p = tmp_path / "runtime.log"
    p.write_text("ok", encoding="utf-8")
    source, freshness = detect_data_source([p], tmp_path / "kpi.jsonl")
    assert source == "runtime_snapshot"
    assert freshness >= 0
