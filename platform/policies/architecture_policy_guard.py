#!/usr/bin/env python3
from __future__ import annotations

"""Legacy compatibility shim.

This file remains importable for older callers, but the canonical guard lives in
`architectural_policy_guard.py` and must be the only place extended going
forward.
"""

from architectural_policy_guard import evaluate_repo, main

__all__ = ["evaluate_repo", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
