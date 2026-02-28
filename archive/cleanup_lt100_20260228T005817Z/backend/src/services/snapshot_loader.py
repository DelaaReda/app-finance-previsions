"""Utilities to load cached JSON snapshots with safe fallbacks.
Keeps a single place where API routes can request cached datasets
and (optionally) trigger the job responsible for refreshing them."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Sequence

try:  # storage.io uses key names without extension
    from storage.io import load_json as load_json_io  # type: ignore
except Exception:  # pragma: no cover - optional dependency in some envs
    load_json_io = None

try:  # legacy storage.base helper expects filenames with .json
    from storage.base import load_json as load_json_base  # type: ignore
except Exception:  # pragma: no cover
    load_json_base = None


logger = logging.getLogger(__name__)


def _io_key(key: str) -> str:
    return key[:-5] if key.endswith(".json") else key


def _base_key(key: str) -> str:
    return key if key.endswith(".json") else f"{key}.json"


def load_snapshot(key: str, aliases: Optional[Sequence[str]] = None) -> Optional[Dict[str, Any]]:
    """Return the first snapshot that exists across storage backends."""
    candidates = [key, *(aliases or [])]
    for candidate in candidates:
        if load_json_io:
            try:
                data = load_json_io(_io_key(candidate))  # type: ignore[misc]
            except Exception as exc:  # pragma: no cover - log and continue
                logger.debug("snapshot_loader io read failed for %s: %s", candidate, exc)
            else:
                if data:
                    return data
        if load_json_base:
            try:
                data = load_json_base(_base_key(candidate))  # type: ignore[misc]
            except Exception as exc:  # pragma: no cover
                logger.debug("snapshot_loader base read failed for %s: %s", candidate, exc)
            else:
                if data:
                    return data
    return None


def ensure_snapshot(
    key: str,
    job_runner: Optional[Callable[[], Any]] = None,
    aliases: Optional[Sequence[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Load a snapshot, optionally triggering the producing job once if missing."""
    data = load_snapshot(key, aliases)
    if data or not job_runner:
        return data

    try:
        job_runner()
    except Exception as exc:  # pragma: no cover - job may fail but API should not crash
        logger.warning("Snapshot job %s failed for key %s: %s", getattr(job_runner, "__name__", job_runner), key, exc)
        return None

    return load_snapshot(key, aliases)


def resolve_payload(
    snapshot: Optional[Dict[str, Any]],
    candidates: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Pick the first nested dict described by dot-notated candidate paths."""
    if not isinstance(snapshot, dict):
        return {}

    paths = list(candidates or [])
    # Always allow direct snapshot as fallback
    paths.append("")

    for path in paths:
        node: Any = snapshot
        if path:
            for key in path.split('.'):
                if not isinstance(node, dict):
                    node = None
                    break
                node = node.get(key)
            if not isinstance(node, dict):
                continue
        if isinstance(node, dict):
            return node

    return snapshot
