#!/usr/bin/env python3
"""Normalize `openclaw cron runs` payloads to a stable {"entries":[...]} shape.

The OpenClaw CLI has produced slightly different JSON envelopes across versions.
This helper accepts:
- object envelopes (e.g. {"entries":[...]}, {"runs":[...]}, {"items":[...]})
- raw arrays of run entries
- noisy outputs containing JSON payload after logs
- JSONL streams (one JSON object per line)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Iterable, List, Optional, Sequence, Tuple


RUN_HINT_KEYS = {
    "status",
    "summary",
    "durationMs",
    "runAtMs",
    "ts",
    "jobId",
    "action",
    "usage",
    "error",
}


def is_run_entry(obj: Any) -> bool:
    return isinstance(obj, dict) and bool(set(obj.keys()) & RUN_HINT_KEYS)


def coerce_entries_from_list(items: Sequence[Any]) -> List[dict]:
    entries: List[dict] = []
    for item in items:
        if isinstance(item, dict):
            if is_run_entry(item):
                entries.append(item)
                continue
            nested = item.get("entry")
            if isinstance(nested, dict) and is_run_entry(nested):
                entries.append(nested)
                continue
        if isinstance(item, str):
            stripped = item.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    decoded = json.loads(stripped)
                except Exception:
                    continue
                if is_run_entry(decoded):
                    entries.append(decoded)
    return entries


def get_path(obj: Any, path: Sequence[str]) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def iter_nested_values(obj: Any, depth: int = 0, max_depth: int = 4) -> Iterable[Any]:
    if depth > max_depth:
        return
    if isinstance(obj, dict):
        for value in obj.values():
            yield value
            yield from iter_nested_values(value, depth + 1, max_depth)
    elif isinstance(obj, list):
        for value in obj:
            yield value
            yield from iter_nested_values(value, depth + 1, max_depth)


def extract_entries(obj: Any) -> List[dict]:
    if isinstance(obj, list):
        entries = coerce_entries_from_list(obj)
        if entries:
            return entries

    if isinstance(obj, dict):
        for path in (
            ("entries",),
            ("runs",),
            ("items",),
            ("data", "entries"),
            ("result", "entries"),
            ("payload", "entries"),
            ("data", "runs"),
            ("result", "runs"),
            ("payload", "runs"),
        ):
            candidate = get_path(obj, path)
            if isinstance(candidate, list):
                entries = coerce_entries_from_list(candidate)
                if entries:
                    return entries

        if is_run_entry(obj):
            return [obj]

        for candidate in iter_nested_values(obj):
            if isinstance(candidate, list):
                entries = coerce_entries_from_list(candidate)
                if entries:
                    return entries
            elif is_run_entry(candidate):
                return [candidate]

    return []


def decode_with_raw_scan(text: str) -> Optional[Any]:
    decoder = json.JSONDecoder()
    best_obj: Optional[Any] = None
    best_span = -1
    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            obj, consumed = decoder.raw_decode(text[i:])
        except Exception:
            continue
        if consumed > best_span:
            best_obj = obj
            best_span = consumed
    return best_obj


def decode_jsonl_lines(text: str) -> Optional[Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    out: List[Any] = []
    for line in lines:
        if line[:1] not in "{[":
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, list):
            out.extend(obj)
        else:
            out.append(obj)
    return out if out else None


def parse_payload(raw: str) -> Tuple[Any, str]:
    text = (raw or "").strip()
    if not text:
        return {}, "empty"

    try:
        return json.loads(text), "json"
    except Exception:
        pass

    jsonl = decode_jsonl_lines(text)
    if jsonl is not None:
        return jsonl, "jsonl"

    scanned = decode_with_raw_scan(text)
    if scanned is not None:
        return scanned, "scanned-json"

    return {}, "unparsed"


def normalize_entry(entry: dict) -> dict:
    out = dict(entry)
    if out.get("summary") is None:
        out["summary"] = ""
    if out.get("summary", "") == "" and isinstance(out.get("error"), str):
        out["summary"] = out.get("error", "")

    for key in ("ts", "runAtMs", "durationMs"):
        value = out.get(key)
        if isinstance(value, str) and value.isdigit():
            out[key] = int(value)

    status = str(out.get("status") or "").strip()
    if not status:
        action = str(out.get("action") or "").strip().lower()
        if action == "finished":
            out["status"] = "error" if out.get("error") else "ok"
        else:
            out["status"] = "unknown"

    if "summary" in out and not isinstance(out["summary"], str):
        out["summary"] = str(out["summary"])

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize openclaw cron runs JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when no run entries could be parsed",
    )
    args = parser.parse_args()

    raw = sys.stdin.read()
    payload, source_format = parse_payload(raw)
    entries = [normalize_entry(e) for e in extract_entries(payload)]
    out = {
        "entries": entries,
        "total": len(entries),
        "source_format": source_format,
    }
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")

    if args.strict and not entries:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
