"""
Legacy storage compatibility layer.

This module keeps legacy call sites working while routing storage to the
canonical runtime data directory (`apps/api/runtime/data`).

Supported save_json signatures:
1) save_json(payload, filename, source=...)
2) save_json(key, payload, source=...)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Union, List, Tuple
import logging

logger = logging.getLogger(__name__)


def _resolve_runtime_storage_dir() -> Path:
    # Prefer storage.io canonical base path when available.
    try:
        from storage.io import BASE_PATH as IO_BASE_PATH  # type: ignore
        path = Path(IO_BASE_PATH)
        path.mkdir(exist_ok=True, parents=True)
        return path
    except Exception:
        # Fallback: apps/api/runtime/data
        path = Path(__file__).resolve().parents[4] / "runtime" / "data"
        path.mkdir(exist_ok=True, parents=True)
        return path


STORAGE_DIR = _resolve_runtime_storage_dir()
LEGACY_STORAGE_DIR = Path(__file__).resolve().parents[1] / "data"


def _normalize_source(source: Optional[Union[str, list]]) -> List[str]:
    if source is None:
        return []
    if isinstance(source, list):
        return [str(item) for item in source if str(item).strip()]
    value = str(source).strip()
    return [value] if value else []


def _normalize_key(filename: str) -> str:
    key = str(filename or "").strip().lstrip("/")
    if key.endswith(".json"):
        key = key[:-5]
    return key


def _parse_save_args(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Tuple[str, Any]:
    """
    Parse compatible signatures:
    - (payload, filename)
    - (key, payload)
    - (filename=..., data=...)
    - (key=..., payload=...)
    """
    if kwargs:
        if "key" in kwargs and "payload" in kwargs:
            return _normalize_key(str(kwargs["key"])), kwargs["payload"]
        if "filename" in kwargs and "data" in kwargs:
            return _normalize_key(str(kwargs["filename"])), kwargs["data"]
        if "filename" in kwargs and "payload" in kwargs:
            return _normalize_key(str(kwargs["filename"])), kwargs["payload"]
        if "key" in kwargs and "data" in kwargs:
            return _normalize_key(str(kwargs["key"])), kwargs["data"]

    if len(args) < 2:
        raise TypeError("save_json() requires at least 2 positional arguments")

    first, second = args[0], args[1]

    # Key-first form: (key:str, payload:any)
    if isinstance(first, str) and not isinstance(second, str):
        key = _normalize_key(first)
        payload = second
        return key, payload

    # Legacy form: (payload:any, filename:str)
    if isinstance(second, str):
        key = _normalize_key(second)
        payload = first
        return key, payload

    # Ambiguous strings: interpret ".json" as filename, else key-first.
    if isinstance(first, str) and isinstance(second, str):
        if second.endswith(".json"):
            return _normalize_key(second), first
        return _normalize_key(first), second

    raise TypeError("Unsupported save_json() argument pattern")


def save_json(*args, source: Optional[Union[str, list]] = None, **kwargs) -> str:
    """
    Save data to runtime storage with metadata compatibility wrapper.
    """
    key, payload = _parse_save_args(args, kwargs)
    if not key:
        raise ValueError("save_json key/filename cannot be empty")

    positional_source = args[2] if len(args) >= 3 else None
    src = _normalize_source(source if source is not None else positional_source)
    last_update = datetime.utcnow().isoformat()
    metadata: Dict[str, Any] = {
        "last_update": last_update,
        "updated_at": last_update,
        "source": src,
        "data": payload,
    }

    # Preferred path: delegate to storage.io (canonical runtime behavior).
    try:
        from storage.io import save_json as save_json_io  # type: ignore

        saved = save_json_io(
            key=key,
            payload=metadata,
            source=src or ["storage.base", "compat_layer"],
            version="legacy-base-v1",
        )
        if saved is not None:
            logger.info("Data saved successfully to %s", saved)
            return str(saved)
    except Exception as exc:
        logger.debug("storage.io save_json delegation failed for key=%s: %s", key, exc)

    # Fallback local write (still canonical runtime/data path).
    filepath = STORAGE_DIR / f"{key}.json"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
    logger.info("Data saved successfully to %s", filepath)
    return str(filepath)


def _load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {"data": value}
    except Exception:
        return None


def load_json(filename: str) -> Optional[Dict[str, Any]]:
    """
    Load data from runtime storage, with fallback to legacy data directory.
    """
    key = _normalize_key(filename)
    if not key:
        return None

    # Preferred path: storage.io (runtime/data, sanitized keys).
    try:
        from storage.io import load_json as load_json_io  # type: ignore

        loaded = load_json_io(key)
        if isinstance(loaded, dict):
            return loaded
    except Exception as exc:
        logger.debug("storage.io load_json delegation failed for key=%s: %s", key, exc)

    candidates = [
        STORAGE_DIR / f"{key}.json",
        LEGACY_STORAGE_DIR / f"{key}.json",
        LEGACY_STORAGE_DIR / str(filename),
    ]

    for path in candidates:
        if path.exists():
            data = _load_json_file(path)
            if data is not None:
                logger.info("Data loaded successfully from %s", path)
                return data

    logger.info("File not found for key=%s (filename=%s)", key, filename)
    return None


def save_forecasts(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save forecasts data specifically
    """
    return save_json(data, "forecasts.json", source or ["forecast_model"])


def load_forecasts() -> Optional[Dict[str, Any]]:
    """
    Load forecasts data specifically
    """
    return load_json("forecasts.json")


def save_news_feed(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save news feed data specifically
    """
    return save_json(data, "news_feed.json", source or ["rss_ingestion"])


def load_news_feed() -> Optional[Dict[str, Any]]:
    """
    Load news feed data specifically
    """
    return load_json("news_feed.json")


def save_weekly_brief(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save weekly brief data specifically
    """
    return save_json(data, "brief_weekly.json", source or ["weekly_analysis"])


def load_weekly_brief() -> Optional[Dict[str, Any]]:
    """
    Load weekly brief data specifically
    """
    return load_json("brief_weekly.json")


def save_backtests(data: Any, source: Optional[Union[str, list]] = None) -> str:
    """
    Save backtests data specifically
    """
    return save_json(data, "backtests.json", source or ["backtest_engine"])


def load_backtests() -> Optional[Dict[str, Any]]:
    """
    Load backtests data specifically
    """
    return load_json("backtests.json")


# Update todo status
if __name__ == "__main__":
    # Test the storage functions
    test_data = {
        "test": "data",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print("Testing storage functions...")
    
    # Test save
    filepath = save_json(test_data, "test.json", ["test_source"])
    print(f"Saved to: {filepath}")
    
    # Test load
    loaded_data = load_json("test.json")
    print(f"Loaded: {loaded_data}")
    
    # Clean up test file
    test_path = STORAGE_DIR / "test.json"
    if test_path.exists():
        os.remove(test_path)
        print("Cleaned up test file")
    
    print("Storage functions test completed successfully")
