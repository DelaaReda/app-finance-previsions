from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional


def _run(cmd: list[str], cwd: Optional[str] = None) -> tuple[int, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
    out, _ = p.communicate()
    return p.returncode, out


def current_branch(cwd: Optional[str] = None) -> str:
    rc, out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if rc != 0:
        raise RuntimeError(out)
    return out.strip()


def create_branch(name: str, checkout: bool = True, cwd: Optional[str] = None) -> str:
    # if exists, just checkout
    rc, _ = _run(["git", "rev-parse", "--verify", name], cwd)
    if rc == 0:
        if checkout:
            rc2, out2 = _run(["git", "checkout", name], cwd)
            if rc2 != 0:
                raise RuntimeError(out2)
        return name
    rc, out = _run(["git", "checkout", "-b", name], cwd)
    if rc != 0:
        raise RuntimeError(out)
    return name


def apply_unified_diff(diff_text: str, commit_message: Optional[str] = None, cwd: Optional[str] = None) -> str:
    # Write temp patch and apply with git apply --index
    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False) as f:
        f.write(diff_text)
        tmp = f.name
    try:
        rc, out = _run(["git", "apply", "--index", tmp], cwd)
        if rc != 0:
            raise RuntimeError(out)
        if commit_message:
            rc2, out2 = _run(["git", "commit", "-m", commit_message], cwd)
            if rc2 != 0:
                raise RuntimeError(out2)
        return "OK"
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def commit_all(message: str, cwd: Optional[str] = None) -> str:
    rc, out = _run(["git", "add", "-A"], cwd)
    if rc != 0:
        raise RuntimeError(out)
    rc2, out2 = _run(["git", "commit", "-m", message], cwd)
    if rc2 != 0:
        raise RuntimeError(out2)
    return "OK"

