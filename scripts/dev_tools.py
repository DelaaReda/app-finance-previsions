"""
Outils de support pour agents (lecture-only) :
- run_pytest_tool() : lance pytest (venv backend si dispo), retourne succès/échec + log tronqué
- run_specific_tests_tool(pattern) : lance pytest -k pattern
- list_endpoints_tool() : tente dister les endpoints FastAPI (best effort)
- search_code_tool(pattern) : recherche simple via ripgrep/grep
- list_todos_tool() : TODO/FIXME dans le repo
- git_status_tool() : git status --short
- git_diff_tool(max_lines) : git diff tronqué
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List

PROJECT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_DIR / "copilot-app" / "backend"
VENV_PY = BACKEND_DIR / ".venv" / "bin" / "python3"


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or PROJECT_DIR),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _python_cmd() -> list[str]:
    if VENV_PY.exists():
        return [str(VENV_PY)]
    return ["python3"]


def run_pytest_tool() -> Dict[str, str]:
    """
    Lance pytest à la racine du projet (ou backend si présent).
    Retourne un dict {ok: "true"/"false", output: "..."} avec log tronqué.
    """
    pytest_cmd = _python_cmd() + ["-m", "pytest", "-q"]
    result = _run(pytest_cmd, cwd=PROJECT_DIR)
    ok = result.returncode == 0
    output = result.stdout or ""
    if len(output) > 4000:
        output = output[:4000] + "\n...[output tronqué]..."
    return {"ok": "true" if ok else "false", "output": output}


def run_specific_tests_tool(pattern: str) -> Dict[str, str]:
    """
    Lance pytest -k <pattern> (lecture-only helper pour les agents).
    """
    pytest_cmd = _python_cmd() + ["-m", "pytest", "-q", "-k", pattern]
    result = _run(pytest_cmd, cwd=PROJECT_DIR)
    ok = result.returncode == 0
    output = result.stdout or ""
    if len(output) > 4000:
        output = output[:4000] + "\n...[output tronqué]..."
    return {"ok": "true" if ok else "false", "output": output}


def git_status_tool() -> str:
    result = _run(["git", "status", "--short"], cwd=PROJECT_DIR)
    return (result.stdout or "").strip()


def git_diff_tool(max_lines: int = 200) -> str:
    result = _run(["git", "diff"], cwd=PROJECT_DIR)
    lines = (result.stdout or "").splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["...[diff tronqué]..."]
    return "\n".join(lines).strip()


def list_endpoints_tool() -> str:
    """
    Tente de lister les endpoints FastAPI en important l'app (best effort).
    Renvoie une chaîne lisible ou un message d'erreur.
    """
    py_cmd = _python_cmd() + [
        "-c",
        (
            "import os\n"
            "from pathlib import Path\n"
            "import json, sys\n"
            "backend = Path(os.getcwd()) / 'copilot-app' / 'backend'\n"
            "os.chdir(backend)\n"
            "sys.path.insert(0, str(backend / 'src'))\n"
            "try:\n"
            "    from api.main import create_app\n"
            "    app = create_app()\n"
            "    routes = []\n"
            "    for r in app.routes:\n"
            "        methods = sorted(getattr(r, 'methods', []) or [])\n"
            "        path = getattr(r, 'path', None)\n"
            "        name = getattr(r, 'name', '')\n"
            "        if path and methods:\n"
            "            routes.append({'path': path, 'methods': methods, 'name': name})\n"
            "    print(json.dumps(routes, ensure_ascii=False, indent=2))\n"
            "except Exception as e:\n"
            "    print(f'error: {e}')\n"
        ),
    ]
    result = _run(py_cmd, cwd=PROJECT_DIR)
    out = (result.stdout or "")
    # Nettoyage léger des warnings applicatifs avant retour
    cleaned_lines = []
    for line in out.splitlines():
        if line.startswith("⚠️"):
            continue
        if line.startswith("Warning:"):
            continue
        if line.startswith("ERROR:"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def search_code_tool(pattern: str, max_lines: int = 400) -> str:
    """
    Recherche un motif texte dans le repo via ripgrep (fallback grep).
    """
    cmd: List[str]
    if subprocess.call(["which", "rg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        cmd = ["rg", "-n", pattern, str(PROJECT_DIR)]
    else:
        cmd = ["grep", "-R", "-n", pattern, str(PROJECT_DIR)]

    result = _run(cmd, cwd=PROJECT_DIR)
    lines = (result.stdout or "").splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["...[résultats tronqués]..."]
    return "\n".join(lines).strip()


def list_todos_tool(max_lines: int = 400) -> str:
    """
    Liste TODO/FIXME dans le repo.
    """
    cmd: List[str]
    if subprocess.call(["which", "rg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        cmd = ["rg", "-n", "(TODO|FIXME)", str(PROJECT_DIR)]
    else:
        cmd = ["grep", "-R", "-n", "-E", "TODO|FIXME", str(PROJECT_DIR)]

    result = _run(cmd, cwd=PROJECT_DIR)
    lines = (result.stdout or "").splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["...[résultats tronqués]..."]
    return "\n".join(lines).strip()


if __name__ == "__main__":
    print("=== git status ===")
    print(git_status_tool() or "(aucun changement)")
    print("\n=== diff (tronqué) ===")
    print(git_diff_tool() or "(diff vide)")
    print("\n=== pytest ===")
    res = run_pytest_tool()
    print(res["output"])
