#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from json import JSONDecodeError
from typing import Any, Iterable


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def iter_json_objects(text: str) -> Iterable[dict[str, Any]]:
    clean = strip_ansi(text)
    decoder = json.JSONDecoder()
    idx = 0
    size = len(clean)
    while idx < size:
        start = clean.find("{", idx)
        if start < 0:
            break
        try:
            obj, end = decoder.raw_decode(clean, start)
        except JSONDecodeError:
            idx = start + 1
            continue
        if isinstance(obj, dict):
            yield obj
        idx = max(end, start + 1)


def _text_from_content(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        return text
    if isinstance(value, list):
        parts = [_text_from_content(part) for part in value]
        parts = [part for part in parts if part]
        return "\n".join(parts).strip()
    if not isinstance(value, dict):
        return ""

    direct_text = value.get("text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    delta = value.get("delta")
    if isinstance(delta, str) and delta.strip():
        return delta.strip()

    content = value.get("content")
    if content is not None:
        content_text = _text_from_content(content)
        if content_text:
            return content_text

    for key in ("item", "message", "data", "output"):
        nested = value.get(key)
        nested_text = _text_from_content(nested)
        if nested_text:
            return nested_text

    return ""


def extract_thread_id(text: str) -> str:
    thread_id = ""
    for obj in iter_json_objects(text):
        if obj.get("type") == "thread.started":
            tid = obj.get("thread_id")
            if isinstance(tid, str) and tid.strip():
                thread_id = tid.strip()
    return thread_id


def extract_message(text: str) -> str:
    message = ""
    for obj in iter_json_objects(text):
        obj_type = str(obj.get("type") or "")
        candidate = ""

        if obj_type == "item.completed":
            item = obj.get("item")
            if isinstance(item, dict):
                item_type = str(item.get("type") or "")
                if item_type in {"agent_message", "message", "assistant_message", "output_text"}:
                    candidate = _text_from_content(item)
        elif obj_type in {
            "response.output_text.delta",
            "response.output_text.done",
            "message.completed",
            "message.delta",
            "assistant_message",
            "agent_message",
            "output_text",
        }:
            candidate = _text_from_content(obj)

        if candidate:
            message = candidate

    return message


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"thread", "message"}:
        print("Usage: codex_exec_stream.py <thread|message>", file=sys.stderr)
        return 2

    payload = sys.stdin.read()
    if argv[1] == "thread":
        result = extract_thread_id(payload)
    else:
        result = extract_message(payload)
    if result:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
