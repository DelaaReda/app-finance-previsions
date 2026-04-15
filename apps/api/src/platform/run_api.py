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

# Ajouter le répertoire backend racine au path pour permettre les imports corrects
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent

# Ensure import resolution prefers backend/ modules first.
for path in [project_root, backend_dir]:
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)

# Desired order: backend_dir (1st), project_root (2nd)
for path in [project_root, backend_dir]:
    sys.path.insert(0, str(path))

# Définir explicitement PYTHONPATH pour que tous les imports fonctionnent correctement
import os
os.environ['PYTHONPATH'] = ":".join([
    str(backend_dir),
    str(project_root),
])

def _run_uvicorn(reload_enabled: bool = True) -> None:
    import uvicorn
    # (imports verified via tests; avoid noisy debug output in production)

    # Prefer the full featured API in api.main, fallback handled below
    import os as _os
    from pathlib import Path as _Path
    _src = _Path(__file__).resolve().parents[1]
    _reload_dirs = [str(_src)] if reload_enabled else None
    worker_count = 1
    if not reload_enabled:
        # The backend owns startup jobs and local runtime state; a multi-worker
        # default duplicates that work and has proven unstable in the VM runtime.
        default_workers = 1
        worker_token = str(_os.getenv("FINANCE_COPILOT_API_WORKERS", str(default_workers)) or str(default_workers)).strip()
        try:
            worker_count = max(1, min(3, int(worker_token)))
        except Exception:
            worker_count = default_workers
    uvicorn.run(
        "api.main:create_app",
        host="127.0.0.1",
        port=8050,
        reload=reload_enabled,
        reload_dirs=_reload_dirs,
        factory=True,
        workers=worker_count,
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
            # Fallback to stable app path
            import uvicorn
            uvicorn.run(
                "api.main:create_app",
                host="127.0.0.1",
                port=8050,
                reload=False,
                factory=True,
                log_level="info",
            )
