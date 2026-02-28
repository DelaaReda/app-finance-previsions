"""
Backend Path Resolver - Finance Copilot System
Ensures consistent path resolution regardless of working directory changes by uvicorn/processes
Task: FC-REAL-DATA-001 - Data Path & Storage Fix
"""
import os
from pathlib import Path
import sys

# Define base paths with multiple fallbacks to ensure resilience
def _get_backend_root():
    """Find the backend root directory using multiple fallback strategies."""
    # Strategy 1: Try to resolve from this file's location
    try:
        current_file_path = Path(__file__).resolve()
        # Navigate up from backend/core/path_resolver.py to backend/
        backend_root = current_file_path.parents[1]  # Go up from core/ -> backend/
        if (backend_root / "data").exists() or (backend_root / "api").exists():
            return backend_root
    except:
        pass
    
    # Strategy 2: Try from current working directory
    try:
        cwd = Path.cwd().resolve()
        if (cwd / "data").exists() or (cwd / "api").exists():
            return cwd
    except:
        pass
    
    # Strategy 3: Try from sys.path
    try:
        for path_str in sys.path:
            path_obj = Path(path_str).resolve()
            if "backend" in str(path_obj) and (path_obj / "data").exists():
                return path_obj
    except:
        pass
    
    # Strategy 4: Try to find from known starting points
    try:
        # Walk up the directory tree from current file
        current = Path(__file__).resolve()
        for _ in range(5):  # Max 5 levels up
            if (current / "data").exists() and (current / "api").exists():
                return current
            if current.parent == current:  # Reached root
                break
            current = current.parent
    except:
        pass
    
    # If all else fails, return current directory
    return Path.cwd().resolve()

# Find the backend root at module load time
_BACKEND_ROOT = _get_backend_root()
DATA_DIR = _BACKEND_ROOT / "data"
LOGS_DIR = _BACKEND_ROOT / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True, parents=True)
LOGS_DIR.mkdir(exist_ok=True, parents=True)

def get_data_path(filename: str) -> Path:
    """
    Get the absolute path to a data file in the backend/data directory.
    
    Args:
        filename: Name of the file (with or without .json extension)
        
    Returns:
        Absolute Path object to the data file
    """
    # Ensure the filename ends with .json if not already specified
    if not filename.lower().endswith('.json'):
        filename = f"{filename}.json"
    
    # Return path in data directory
    return DATA_DIR / filename

def get_backend_root() -> Path:
    """Return the resolved backend root directory."""
    return _BACKEND_ROOT

def get_data_directory() -> Path:
    """Return the resolved data directory."""
    return DATA_DIR

def ensure_directories() -> None:
    """Ensure that required directories exist."""
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    LOGS_DIR.mkdir(exist_ok=True, parents=True)

# Export constants
BACKEND_ROOT = _BACKEND_ROOT
STORAGE_PATH = DATA_DIR

# Test path resolution on import
if __name__ == "__main__":
    print(f"Backend root: {_BACKEND_ROOT}")
    print(f"Data dir: {DATA_DIR}")
    print(f"Does data dir exist? {DATA_DIR.exists()}")
    print(f"Sample path (forecasts.json): {get_data_path('forecasts')}")
