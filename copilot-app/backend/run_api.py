#!/usr/bin/env python3
"""
Script de lancement de l'API FastAPI.
Usage: python run_api.py
"""
import errno
import sys
import os
from pathlib import Path

# Load .env file if present (copilot-app/.env)
try:
    from dotenv import load_dotenv
    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent  # copilot-app/
    # Try to load from copilot-app/.env first (project root)
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
        print(f"✅ Loaded .env from: {env_file}")
    else:
        # Fallback to backend/.env
        env_file = backend_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)
            print(f"✅ Loaded .env from: {env_file}")
        else:
            # Try current directory
            load_dotenv(override=False)
except ImportError:
    pass  # dotenv not available, use system env vars

# Ajouter le répertoire backend racine et src au path pour permettre les imports corrects
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
src_path = backend_dir / "src"

for path in [project_root, backend_dir, src_path]:
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)

for path in reversed([project_root, backend_dir, src_path]):
    sys.path.insert(0, str(path))

# Définir explicitement PYTHONPATH pour que tous les imports fonctionnent correctement
import os
os.environ['PYTHONPATH'] = ":".join(
    [
        str(backend_dir),
        str(src_path),
        str(project_root),
    ]
)

def _run_uvicorn(reload_enabled: bool = True) -> None:
    import uvicorn

    uvicorn.run(
        # Prefer the full featured API in src.api.main, fallback to api.main
        "src.api.main:create_app",
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
            # Fallback to legacy app path if src.api.main is unavailable
            try:
                import uvicorn
                uvicorn.run(
                    "api.main:create_app",
                    host="127.0.0.1",
                    port=8050,
                    reload=False,
                    factory=True,
                    log_level="info",
                )
            except Exception:
                raise
