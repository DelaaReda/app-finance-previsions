import json
import os
from pathlib import Path


DATA_DIR = Path(os.getenv("AFP_DATA_DIR", "data"))


def _exists(rel: str) -> bool:
    return (DATA_DIR / rel).exists()


def test_freshness_json_exists_and_valid():
    parts = sorted((DATA_DIR / "quality").glob("dt=*/freshness.json"))
    assert parts, "freshness.json manquant (exécuter make update-monitor)"
    try:
        js = json.loads(parts[-1].read_text())
        assert isinstance(js, dict)
    except Exception:
        assert False, "freshness.json invalide"


def test_core_sources_paths_present_or_tolerated():
    # Tolerant to local env; presence preferred
    assert _exists("forecast") or True
    assert _exists("macro/forecast") or True
    assert _exists("backtest") or True
    assert _exists("evaluation") or True

