#!/usr/bin/env python3
"""
Script de lancement de l'API FastAPI.
Usage: python run_api.py
"""
import errno
import sys
from pathlib import Path

# Ajouter le répertoire backend racine et src au path pour permettre les imports corrects
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
src_path = backend_dir / "src"

for path in [project_root, src_path, backend_dir]:
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)

for path in reversed([project_root, src_path, backend_dir]):
    sys.path.insert(0, str(path))

# Définir explicitement PYTHONPATH pour que tous les imports fonctionnent correctement
import os
os.environ['PYTHONPATH'] = ":".join(
    [
        str(project_root),
        str(src_path),
        str(backend_dir),
    ]
)

def _run_uvicorn(reload_enabled: bool = True) -> None:
    import uvicorn

    uvicorn.run(
        "api.main:create_app",
        host="127.0.0.1",
        port=8050,
        reload=reload_enabled,
        factory=True,
        log_level="info",
    )


if __name__ == "__main__":
    print("🚀 Lancement de l'API Finance Copilot...")
    print("📍 URL: http://127.0.0.1:8050")
    print("📖 Docs: http://127.0.0.1:8050/docs")
    print()

    reload_env = os.getenv("FINANCE_COPILOT_RELOAD", "1").strip().lower()
    reload_enabled = reload_env not in {"0", "false", "no"}

    try:
        _run_uvicorn(reload_enabled=reload_enabled)
    except (PermissionError, OSError) as exc:
        err_no = getattr(exc, "errno", None)
        if reload_enabled and err_no in {errno.EPERM, 1}:
            print("⚠️  Reload watcher non autorisé sur cet environnement. Redémarrage sans reload…")
            _run_uvicorn(reload_enabled=False)
        else:
            raise
