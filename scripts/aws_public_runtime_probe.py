#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_ROOT = ROOT / "platform" / "automation"
if str(AUTOMATION_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_ROOT))

from runtime.truth.public_runtime_probe import as_json, probe_public_surface


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe public EC2 runtime with restart-aware maintenance detection.")
    parser.add_argument("--url", required=True, help="Public URL to probe")
    parser.add_argument("--timeout", type=float, default=1.5, help="HTTP timeout in seconds")
    parser.add_argument("--maintenance-max-age", type=int, default=300, help="Max age for runtime restart marker")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    payload = probe_public_surface(
        args.url,
        timeout_s=args.timeout,
        maintenance_max_age_s=args.maintenance_max_age,
        maintenance_check=True,
    )
    print(as_json(payload, pretty=args.pretty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
