#!/usr/bin/env python3
from __future__ import annotations

"""Compatibility entrypoint.

Historically the safety gate could be called from `scripts/`. The canonical
implementation now lives in `platform/policies/command_safety_gate.py`.
"""

from pathlib import Path
import runpy
import sys


def main() -> int:
    script_path = Path(__file__).resolve().parent.parent / "platform" / "policies" / "command_safety_gate.py"
    if not script_path.exists():
        print(f"command_safety_gate not found: {script_path}", file=sys.stderr)
        return 2

    # Keep canonical path evaluation aligned for workspace checks.
    normalized_args = sys.argv[:]
    for idx, arg in enumerate(normalized_args):
        if arg == "--workdir" and idx + 1 < len(normalized_args):
            normalized_args[idx + 1] = str(Path(normalized_args[idx + 1]).expanduser().resolve())
            break
    sys.argv = normalized_args
    runpy.run_path(str(script_path), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
