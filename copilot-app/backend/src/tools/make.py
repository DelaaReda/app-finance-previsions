from __future__ import annotations

import subprocess
import time
from typing import Dict, List, Optional


def run_make(target: str, args: Optional[List[str]] = None, timeout: int = 900, cwd: Optional[str] = None) -> Dict:
    """Run a Makefile target and capture result.

    Returns a dict: {"rc": int, "duration_ms": int, "out": str}.
    """
    cmd = ["make", target] + (args or [])
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out = "[timeout] killed after %ss" % (timeout,)
    dur = int((time.time() - t0) * 1000)
    return {"rc": p.returncode, "duration_ms": dur, "out": out[-40000:]}

