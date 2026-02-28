#!/usr/bin/env python3
"""Normalize tmux pane stream into readable text logs.

This script is intended to run as a tmux `pipe-pane` consumer.
It strips ANSI/control noise while preserving human-readable content.
"""

from __future__ import annotations

import re
import sys


OSC_RE = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")
CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ESC_RE = re.compile(r"\x1b[@-Z\\-_]")
CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
BOX_CHARS_RE = re.compile(r"[┌┐└┘├┤─│╭╮╰╯…·]+")
SPACE_RE = re.compile(r"\s+")
DROP_EXACT_SNIPPETS = (
    "openai codex",
    "/model to change",
    "directory: ~/analyse-financiere",
    "model: gpt-5.3-",
    "model: loading",
)


def clean_chunk(text: str) -> str:
    if not text:
        return ""
    out = text.replace("\r", "\n")
    out = OSC_RE.sub("", out)
    out = CSI_RE.sub("", out)
    out = ESC_RE.sub("", out)
    out = CTRL_RE.sub("", out)
    return out


def clean_line(line: str) -> str:
    s = line or ""
    s = BOX_CHARS_RE.sub(" ", s)
    s = s.replace("›", " ")
    s = s.replace("100% context left", " ")
    s = SPACE_RE.sub(" ", s).strip()
    if not s:
        return ""
    low = s.lower()
    if low == "clear":
        return ""
    if low.startswith("tip:"):
        return ""
    if any(snippet in low for snippet in DROP_EXACT_SNIPPETS):
        return ""
    return s


def main() -> int:
    # Read streaming input and flush aggressively to keep near real-time logs.
    last = ""
    for chunk in sys.stdin:
        cleaned = clean_chunk(chunk)
        if not cleaned:
            continue
        for raw_line in cleaned.splitlines():
            line = clean_line(raw_line)
            if not line:
                continue
            if line == last:
                continue
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
            last = line
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
