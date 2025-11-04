from fastapi import APIRouter
from core.response import ok
from storage.io import last_updates_info
from pathlib import Path
import time

router = APIRouter()

@router.get("/health")
def health():
    # Check if backend is up by confirming basic services
    backend_up = True  # If we can respond, backend is up
    
    # Get data directory info
    data_dir = Path(__file__).resolve().parents[3] / "data"  # backend/api/routes/../.. -> backend/data
    data_paths = {}
    if data_dir.exists():
        for item in data_dir.iterdir():
            if item.is_dir():
                data_paths[item.name] = str(item)
            elif item.is_file() and item.suffix in ['.json', '.parquet', '.csv']:
                data_paths[item.name] = str(item)
    
    return ok({
        "status": "ok", 
        "backend_up": backend_up,
        "last_updates": last_updates_info(),
        "data_paths": data_paths,
        "timestamp": int(time.time())
    })