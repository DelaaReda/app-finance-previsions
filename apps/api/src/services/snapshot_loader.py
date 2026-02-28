"""Compatibility snapshot loader helper."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Sequence

from storage.io import load_json as load_json_io
from storage.base import load_json as load_json_base


def _normalize_key_io(key: str) -> str:
    return key[:-5] if key.endswith(".json") else key


def _normalize_key_base(key: str) -> str:
    return key if key.endswith(".json") else f"{key}.json"


def load_snapshot(key: str, aliases: Optional[Sequence[str]] = None) -> Optional[Dict[str, Any]]:
    for candidate in (key, *(aliases or [])):
        data = load_json_io(_normalize_key_io(candidate))
        if data:
            return data
        data = load_json_base(_normalize_key_base(candidate))
        if data:
            return data
    return None


def ensure_snapshot(
    key: str,
    job_runner: Optional[Callable[[], Any]] = None,
    aliases: Optional[Sequence[str]] = None,
) -> Optional[Dict[str, Any]]:
    payload = load_snapshot(key, aliases)
    if payload or not job_runner:
        return payload
    try:
        job_runner()
    except Exception:
        return None
    return load_snapshot(key, aliases)


def resolve_payload(
    snapshot: Optional[Dict[str, Any]],
    candidates: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}

    for path in list(candidates or []) + [""]:
        node = snapshot
        if path:
            for key in path.split("."):
                if not isinstance(node, dict):
                    node = None
                    break
                node = node.get(key)
            if not isinstance(node, dict):
                continue
        if isinstance(node, dict):
            return node
    return snapshot

