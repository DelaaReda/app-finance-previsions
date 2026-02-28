"""Judge-like endpoint helpers.

Reusable primitives for API routes that must follow the same quality bar as
`/api/judge`: deterministic cache keys, cache metadata, single-flight
concurrency guard, and stable source tagging.
"""

from __future__ import annotations

import asyncio
import json
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stable_cache_key(namespace: str, payload: Dict[str, Any]) -> str:
    key_obj = {"v": namespace, **payload}
    return json.dumps(key_obj, sort_keys=True, separators=(",", ":"))


def append_source_tag(data: Dict[str, Any], tag: str, *, default_source: str) -> None:
    source = data.get("source")
    if isinstance(source, list):
        if tag not in source:
            source.append(tag)
        return
    data["source"] = [default_source, tag]


def response_cache_get(
    cache_store: Dict[str, Dict[str, Any]],
    key: str,
    *,
    ttl_seconds: int,
    hit_source_tag: str,
    default_source: str,
    copy_mode: str = "smart",
) -> Dict[str, Any] | None:
    now = time.time()
    entry = cache_store.get(key)
    if not entry:
        return None
    ts = float(entry.get("ts", 0.0))
    if ttl_seconds > 0 and (now - ts) > ttl_seconds:
        cache_store.pop(key, None)
        return None

    stored = entry.get("data") or {}
    if copy_mode == "deep":
        payload = deepcopy(stored)
    else:
        # Smart copy: keep heavy immutable payload parts (rows/stats) by reference,
        # but isolate fields we mutate for hit metadata/source tagging.
        payload = dict(stored)
        source = payload.get("source")
        if isinstance(source, list):
            payload["source"] = list(source)
        cache_meta_existing = payload.get("cache")
        if isinstance(cache_meta_existing, dict):
            payload["cache"] = dict(cache_meta_existing)
        else:
            payload["cache"] = {}
    age_seconds = max(0.0, now - ts)
    cache_meta = payload.get("cache")
    if not isinstance(cache_meta, dict):
        cache_meta = {}
    cache_meta.update(
        {
            "hit": True,
            "age_seconds": round(age_seconds, 3),
            "ttl_seconds": int(ttl_seconds),
        }
    )
    payload["cache"] = cache_meta
    append_source_tag(payload, hit_source_tag, default_source=default_source)
    return payload


def response_cache_set(
    cache_store: Dict[str, Dict[str, Any]],
    key: str,
    payload: Dict[str, Any],
    *,
    max_entries: int,
) -> None:
    cache_store[key] = {"ts": time.time(), "data": deepcopy(payload)}
    if len(cache_store) <= max_entries:
        return

    old_keys = sorted(cache_store.keys(), key=lambda k: float(cache_store[k].get("ts", 0.0)))
    drop_count = len(cache_store) - max_entries
    for stale_key in old_keys[:drop_count]:
        cache_store.pop(stale_key, None)


async def compute_singleflight(
    inflight: Dict[str, asyncio.Task],
    inflight_lock: asyncio.Lock,
    key: str,
    compute_fn: Callable[[], Awaitable[Dict[str, Any]]],
) -> Tuple[Dict[str, Any], bool]:
    """Compute payload once for concurrent identical requests.

    Returns `(payload, is_leader)`.
    """
    async with inflight_lock:
        task = inflight.get(key)
        if task is None:
            task = asyncio.create_task(compute_fn())
            inflight[key] = task
            is_leader = True
        else:
            is_leader = False

    try:
        result = await task
        return result, is_leader
    finally:
        if is_leader:
            async with inflight_lock:
                inflight.pop(key, None)
