"""
Centralized environment variable loader.
Ensures all modules can access API keys and configuration from copilot-app/.env

Usage:
    from core.env_loader import ensure_env_loaded, get_env
    
    # Ensure .env is loaded (idempotent, safe to call multiple times)
    ensure_env_loaded()
    
    # Get environment variable
    api_key = get_env("FRED_API_KEY")
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_ENV_LOADED = False
_ENV_FILE_PATH = None


def ensure_env_loaded(force_reload: bool = False) -> bool:
    """
    Ensure .env file is loaded from copilot-app/.env (project root).
    
    This function is idempotent - safe to call multiple times.
    It will only load once unless force_reload=True.
    
    Args:
        force_reload: If True, reload .env even if already loaded
        
    Returns:
        True if .env was loaded (or already loaded), False if not found
    """
    global _ENV_LOADED, _ENV_FILE_PATH
    
    if _ENV_LOADED and not force_reload:
        return True
    
    try:
        from dotenv import load_dotenv
    except ImportError:
        # dotenv not available, rely on system env vars
        _ENV_LOADED = True
        return False
    
    # Determine project root (copilot-app/)
    # This file is in backend/src/core/env_loader.py
    # So backend/ is 2 levels up, copilot-app/ is 3 levels up
    current_file = Path(__file__).resolve()
    backend_dir = current_file.parents[2]  # backend/
    project_root = backend_dir.parent  # copilot-app/
    
    # Try multiple locations in priority order
    env_files = [
        project_root / ".env",  # copilot-app/.env (PRIORITY)
        backend_dir / ".env",   # backend/.env
        Path.cwd() / ".env",    # Current working directory
    ]
    
    for env_file in env_files:
        if env_file.exists():
            load_dotenv(env_file, override=False)
            _ENV_FILE_PATH = env_file
            _ENV_LOADED = True
            return True
    
    # Try loading from current directory (may have been set by parent process)
    load_dotenv(override=False)
    _ENV_LOADED = True
    return False


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable, ensuring .env is loaded first.
    
    Args:
        name: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    ensure_env_loaded()
    value = os.getenv(name, default)
    if value:
        return value.strip() if isinstance(value, str) else value
    return default


def get_env_path() -> Optional[Path]:
    """
    Get the path to the loaded .env file.
    
    Returns:
        Path to .env file if loaded, None otherwise
    """
    ensure_env_loaded()
    return _ENV_FILE_PATH


# Auto-load on import
ensure_env_loaded()

