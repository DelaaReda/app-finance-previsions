
from __future__ import annotations

import shlex
import subprocess

from ..config import AgentConfig
def _run(cmd: str, input_text: str | None = None, cwd: str | None = None) -> tuple[int, str]:
    p = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
    out, _ = p.communicate(input=input_text)
    return p.returncode, out
def current_branch() -> str:
    rc, out = _run("git rev-parse --abbrev-ref HEAD")
    return out.strip() if rc == 0 else ""
def ensure_safe_branch(cfg: AgentConfig | None = None) -> None:
    cfg = cfg or AgentConfig()
    br = current_branch()
    if not br:
        raise RuntimeError(
            "Impossible de déterminer la branche Git. Créez une branche feature avant d'exécuter l'agent."
        )
    if br == "local-branch":
        raise RuntimeError(
            "La branche 'local-branch' est réservée. Créez une branche dédiée dont le nom commence par"
            f" '{cfg.safe_branch_prefix}'."
        )
    if not br.startswith(cfg.safe_branch_prefix):
        raise RuntimeError(
            f"Branche '{br}' non autorisée. Utilisez un nom qui commence par '{cfg.safe_branch_prefix}'."
        )
def apply_patch_text(unified_diff: str) -> bool:
    rc, out = _run("git apply --index -p0", input_text=unified_diff)
    return rc == 0
def commit_all(message: str) -> bool:
    safe = message.replace("\\", "\\\\").replace("\"", "\\\"")
    cmd = f"bash -lc \"git add -A && git commit -m \\\"{safe}\\\"\""
    rc, _ = _run(cmd)
    return rc == 0
def restore_worktree() -> None:
    _run("git reset --hard")
