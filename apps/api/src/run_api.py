"""Backward-compatible backend entrypoint."""

from __future__ import annotations

if __name__ == "__main__":
    import runpy
    runpy.run_module("platform.run_api", run_name="__main__")
else:
    # Direct import keeps a stable module graph and avoids file-path shims.
    from platform.run_api import *  # type: ignore  # noqa: F401,F403
