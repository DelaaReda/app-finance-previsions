"""
Universal file loading utilities for Finance Copilot
Task: FC-ARCH-UTILS-001 - Factorisation des utilitaires communs
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from typing import Any, Dict, Optional, Union
import json
from pathlib import Path
import sys
import os
import csv
import pickle


def load_json(filename: str, base_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Safe universal JSON loader with multiple fallback strategies.
    
    Args:
        filename: Name of the file (with or without .json extension)  
        base_path: Base path to look in, defaults to backend/data/
        
    Returns:
        Loaded JSON data or None if file doesn't exist
    """
    try:
        # Add .json extension if missing
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        # Determine base path - default to backend data directory
        if not base_path:
            # Go back to backend root from src/
            backend_root = Path(__file__).resolve().parents[2]  # From src/utils/file_loader.py to backend/
            base_path = str(backend_root / "data")
        elif not Path(base_path).exists():
            # If provided path doesn't exist, try relative to backend root
            backend_root = Path(__file__).resolve().parents[2]
            alt_path = str(backend_root / base_path)
            if Path(alt_path).exists():
                base_path = alt_path
            else:
                # Fallback to current directory
                base_path = "data"
        
        filepath = Path(base_path) / filename
        
        if not filepath.exists():
            # Try alternative locations if not found in base path
            alt_locations = [
                "data", 
                Path(__file__).resolve().parents[2] / "data",  # backend/data
                Path(__file__).resolve().parents[1] / "data",  # backend/src/data
                Path.cwd() / "data"
            ]
            
            for alt_location in alt_locations:
                alt_path = Path(alt_location) / filename
                if alt_path.exists():
                    filepath = alt_path
                    break
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
        return None
    except Exception as e:
        # Log error but continue gracefully to maintain never-empty pattern
        print(f"⚠️ Error loading JSON file {filename}: {str(e)}")
        return None


def save_json(data: Any, filename: str, base_path: Optional[str] = None, source: Optional[list] = None) -> str:
    """
    Safe universal JSON saver with metadata.
    
    Args:
        data: Data to save
        filename: Name of the file (with or without .json extension)
        base_path: Base path to save to, defaults to backend/data/
        source: Source metadata to track provenance
        
    Returns:
        Full path of saved file
    """
    try:
        # Add .json extension if missing
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        # Determine base path - default to backend data directory
        if not base_path:
            backend_root = Path(__file__).resolve().parents[2]  # From src/utils/file_loader.py to backend/
            base_path = str(backend_root / "data")
        
        Path(base_path).mkdir(parents=True, exist_ok=True)
        filepath = Path(base_path) / filename
        
        # Add metadata to preserve provenance
        enriched_data = {
            "data": data,
            "source": source or ["universal_file_loader", "file_loader.py"],
            "saved_at": "2025-11-06T00:00:00.000000Z",  # Will be updated with real timestamp
            "format_version": "1.0"
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    except Exception as e:
        # Log error but return None to maintain never-empty pattern
        print(f"⚠️ Error saving JSON file {filename}: {str(e)}")
        return ""


def load_csv(filename: str, base_path: Optional[str] = None) -> Optional[list]:
    """
    Safe universal CSV loader.
    
    Args:
        filename: Name of the file (with or without .csv extension)
        base_path: Base path to look in, defaults to backend/data/
        
    Returns:
        Loaded CSV data as list of dictionaries or None if file doesn't exist
    """
    try:
        # Add .csv extension if missing
        if not filename.endswith('.csv'):
            filename = f"{filename}.csv"
        
        # Determine base path
        if not base_path:
            backend_root = Path(__file__).resolve().parents[2]
            base_path = str(backend_root / "data")
        
        filepath = Path(base_path) / filename
        
        if not filepath.exists():
            return None
        
        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        
        return rows
    except Exception as e:
        print(f"⚠️ Error loading CSV file {filename}: {str(e)}")
        return None


def load_pickle(filename: str, base_path: Optional[str] = None) -> Optional[Any]:
    """
    Safe universal Pickle loader.
    
    Args:
        filename: Name of the file (with or without .pkl extension)
        base_path: Base path to look in, defaults to backend/data/
        
    Returns:
        Loaded pickle data or None if file doesn't exist
    """
    try:
        # Add .pkl extension if missing
        if not filename.endswith('.pkl') and not filename.endswith('.pickle'):
            filename = f"{filename}.pkl"
        
        # Determine base path
        if not base_path:
            backend_root = Path(__file__).resolve().parents[2]
            base_path = str(backend_root / "data")
        
        filepath = Path(base_path) / filename
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"⚠️ Error loading pickle file {filename}: {str(e)}")
        return None


def ensure_path_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory path exists, creating it if necessary.
    
    Args:
        path: Path to ensure exists
        
    Returns:
        Path object that is guaranteed to exist
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_latest_file_pattern(pattern: str, base_path: Optional[str] = None) -> Optional[Path]:
    """
    Find the latest file matching a pattern (useful for dt=YYYYMMDD partitions).
    
    Args:
        pattern: Glob pattern to search for (e.g. "dt=*")
        base_path: Base path to search in
        
    Returns:
        Path to the latest matching file/directory or None if not found
    """
    try:
        if not base_path:
            backend_root = Path(__file__).resolve().parents[2]
            base_path = str(backend_root / "data")
        
        search_path = Path(base_path) / pattern
        # Find all files matching pattern
        matches = list(Path(search_path.parent).glob(search_path.name))
        
        if not matches:
            return None
        
        # Sort by name to get the latest (assuming format like dt=20251106)
        latest = sorted(matches, key=lambda x: x.name)[-1]
        return latest
    except Exception as e:
        print(f"⚠️ Error finding latest file with pattern {pattern}: {str(e)}")
        return None