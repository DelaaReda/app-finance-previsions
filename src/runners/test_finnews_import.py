import importlib.util
import sys
from pathlib import Path
import types


def load_module_from_path(path: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("finnews", path)
    module = importlib.util.module_from_spec(spec)
    # Ensure the loader executes the module in its own namespace
    spec.loader.exec_module(module)
    return module


def test_import_finnews_module():
    p = Path(__file__).resolve().parent.parent / "searxng-local" / "finnews.py"
    mod = load_module_from_path(str(p))
    # basic smoke: ensure key symbols exist
    assert hasattr(mod, "harvest")
    assert hasattr(mod, "fetch_feed_entries")
    assert hasattr(mod, "compile_bool_query")


def test_finnews_pure_functions():
    p = Path(__file__).resolve().parent.parent / "searxng-local" / "finnews.py"
    mod = load_module_from_path(str(p))

    # compile_bool_query should accept simple queries
    q = mod.compile_bool_query('oil AND Ukraine')
    assert callable(q)
    assert q('Oil supply in Ukraine') is True
    assert q('banana harvest') is False

    # enrich_item should return tags, score, entities
    tags, score, ents = mod.enrich_item('Brent soars as sanctions hit oil supply and OPEC decisions')
    assert isinstance(tags, list)
    assert isinstance(score, float)
    assert isinstance(ents, list)
