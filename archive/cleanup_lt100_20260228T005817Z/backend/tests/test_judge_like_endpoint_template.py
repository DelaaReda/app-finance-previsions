from __future__ import annotations

import asyncio

from src.api.templates.judge_like_endpoint import (
    append_source_tag,
    compute_singleflight,
    response_cache_get,
    response_cache_set,
    stable_cache_key,
)


def test_stable_cache_key_is_deterministic():
    key_1 = stable_cache_key("ns", {"b": 2, "a": 1})
    key_2 = stable_cache_key("ns", {"a": 1, "b": 2})
    assert key_1 == key_2


def test_response_cache_roundtrip_and_hit_metadata():
    cache_store = {}
    payload = {"source": ["forecasts_route"], "count": 1}
    response_cache_set(cache_store, "k1", payload, max_entries=2)

    cached = response_cache_get(
        cache_store,
        "k1",
        ttl_seconds=120,
        hit_source_tag="forecasts_cache_hit",
        default_source="forecasts_route",
    )
    assert cached is not None
    assert cached["cache"]["hit"] is True
    assert cached["cache"]["ttl_seconds"] == 120
    assert "forecasts_cache_hit" in (cached.get("source") or [])
    # ensure smart-copy path does not mutate stored cache source
    cached_again = response_cache_get(
        cache_store,
        "k1",
        ttl_seconds=120,
        hit_source_tag="forecasts_cache_hit",
        default_source="forecasts_route",
    )
    assert cached_again is not None
    assert (cached_again.get("source") or []).count("forecasts_cache_hit") == 1


def test_append_source_tag_adds_once():
    payload = {"source": ["forecasts_route"]}
    append_source_tag(payload, "tag_a", default_source="forecasts_route")
    append_source_tag(payload, "tag_a", default_source="forecasts_route")
    assert payload["source"].count("tag_a") == 1


def test_singleflight_runs_compute_once():
    inflight = {}
    lock = asyncio.Lock()
    calls = {"count": 0}

    async def compute_once():
        calls["count"] += 1
        await asyncio.sleep(0.02)
        return {"ok": True}

    async def run_batch():
        return await asyncio.gather(
            compute_singleflight(inflight, lock, "k1", compute_once),
            compute_singleflight(inflight, lock, "k1", compute_once),
            compute_singleflight(inflight, lock, "k1", compute_once),
        )

    results = asyncio.run(run_batch())
    leaders = [is_leader for _, is_leader in results]
    payloads = [payload for payload, _ in results]

    assert calls["count"] == 1
    assert leaders.count(True) == 1
    assert all(item == {"ok": True} for item in payloads)
