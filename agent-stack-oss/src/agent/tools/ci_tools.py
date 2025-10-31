
from __future__ import annotations
import subprocess, shlex
def _run(cmd: str, timeout: int | None = None) -> tuple[int, str]:
    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate(timeout=timeout)
    return p.returncode, out
def run_pytests() -> dict:
    rc, out = _run("pytest -q")
    return {"rc": rc, "ok": rc == 0, "out": out}
def run_linters() -> dict:
    rc1, out1 = _run("ruff check .")
    rc2, out2 = _run("mypy src")
    return {"ruff": {"rc": rc1, "ok": rc1 == 0, "out": out1},
            "mypy": {"rc": rc2, "ok": rc2 == 0, "out": out2},
            "ok": rc1 == 0 and rc2 == 0}
def build_webapp() -> dict:
    rc, out = _run("bash -lc 'test -d webapp && npm -C webapp ci && npm -C webapp run build || echo skip'")
    return {"rc": rc, "ok": rc == 0, "out": out}
