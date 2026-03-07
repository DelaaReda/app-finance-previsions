from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from domains.copilot.api import search as search_route


def test_search_tickers_nominal_exposes_stable_metadata():
    payload = asyncio.run(
        search_route.search_tickers(q="AAPL", limit=10, sector=None)
    )

    assert payload["ok"] is True
    assert payload["status"] == "ok"
    assert payload["error"] is None
    assert payload["freshness"] == payload["data"]["freshness"]
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["error"] is None
    assert payload["data"]["matches"]


def test_search_tickers_fallback_exposes_stable_metadata(monkeypatch):
    def fail_match(*_args, **_kwargs):
        raise RuntimeError("search matching failed")

    monkeypatch.setattr(search_route, "fuzzy_match", fail_match)

    payload = asyncio.run(
        search_route.search_tickers(q="AAPL", limit=10, sector=None)
    )

    assert payload["ok"] is True
    assert payload["status"] == "degraded"
    assert "search matching failed" in str(payload["error"])
    assert payload["freshness"] == payload["data"]["freshness"]
    assert payload["data"]["status"] == "degraded"
    assert "search matching failed" in str(payload["data"]["error"])
    assert payload["data"]["matches"] == []
