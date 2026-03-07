#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from orchestrator_paths import load_runtime_state, persist_runtime_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read or write orchestration runtime state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--root", default="")

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--root", default="")
    write_parser.add_argument("--lifecycle", required=True, choices=["running", "paused", "maintenance"])
    write_parser.add_argument("--reason", required=True)
    write_parser.add_argument("--execution-mode", default="")
    write_parser.add_argument("--operator-mode", default="")
    write_parser.add_argument("--source", default="manual")

    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else Path(__file__).resolve().parents[2]

    if args.command == "read":
        print(json.dumps(load_runtime_state(root), ensure_ascii=True))
        return 0

    path = persist_runtime_state(
        root,
        lifecycle=args.lifecycle,
        reason=args.reason,
        execution_mode=args.execution_mode,
        operator_mode=args.operator_mode,
        source=args.source,
    )
    print(json.dumps({"ok": True, "path": str(path)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
