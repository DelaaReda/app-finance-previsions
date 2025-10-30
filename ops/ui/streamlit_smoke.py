#!/usr/bin/env python3
"""
Minimal smoke test for the Streamlit unified skeleton.

Starts the app on a test port and verifies HTTP 200 on root.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests


def wait_for_http(url: str, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2.5)
            if r.status_code == 200:
                return True
        except Exception as e:  # noqa: PERF203
            last_err = e
        time.sleep(0.5)
    if last_err:
        print(f"Last error: {last_err}")
    return False


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    app = repo / "src" / "apps" / "streamlit" / "app.py"
    if not app.exists():
        print(f"App not found: {app}")
        return 2

    port = int(os.getenv("STREAMLIT_PORT", "5566"))
    base = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", f"{repo}/src")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]

    print(f"[smoke] starting: {' '.join(cmd)}")
    p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        ok = wait_for_http(base, timeout=30.0)
        if not ok:
            print("[smoke] server did not become healthy in time")
            return 1
        print("[smoke] GET / -> 200 OK")
        return 0
    finally:
        try:
            p.send_signal(signal.SIGINT)
            p.wait(timeout=5)
        except Exception:
            p.kill()
        print("[smoke] stopped")


if __name__ == "__main__":
    raise SystemExit(main())

