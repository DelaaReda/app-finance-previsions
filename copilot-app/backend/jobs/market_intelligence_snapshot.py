#!/usr/bin/env python3
"""
Generate and persist the latest Market Intelligence & Context snapshots.
This job loads the persisted datasets (forecasts, brief, news) and writes
the aggregated snapshot/context to data/intelligence_snapshot.json etc.,
so the API can serve them instantly.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.intelligence_service import (  # noqa: E402
    get_market_intelligence_snapshot,
    get_market_context_snapshot,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Persist market intelligence snapshots")
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print snapshots to stdout after writing cache",
    )
    args = parser.parse_args(argv)

    snapshot = get_market_intelligence_snapshot(use_cache=False, persist=True)
    context = get_market_context_snapshot(use_cache=False, persist=True)

    if args.stdout:
        print("=== intelligence snapshot ===")
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        print("=== market context ===")
        print(json.dumps(context, ensure_ascii=False, indent=2))
    else:
        print("Market intelligence snapshot persisted.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
