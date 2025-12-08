"""
Generic storage module for persistent caching.

This module provides save/load functions for JSON data with metadata
like last_update timestamp and source information to ensure never-empty
responses as per the never-empty rule.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

def save_json(key: str, data: Any, sources: Optional[List[str]] = None) -> bool:
    """
    Save data to a JSON file with freshness metadata.
    
    Args:
        key: The cache key (will be used as filename)
        data: The data to save
        sources: List of data sources (APIs, files, etc.) used to generate the data
    
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Ensure the data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # Prepare the data with metadata
        payload = {
            "data": data,
            "last_update": datetime.now().isoformat(),
            "source": sources or [],
            "freshness": "fresh"  # Current freshness status
        }
        
        # Save to file
        file_path = os.path.join(data_dir, f"{key}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully saved data to {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving JSON data for key {key}: {str(e)}")
        return False


def load_json(key: str) -> Optional[Dict[str, Any]]:
    """
    Load data from a JSON file with freshness metadata.
    
    Args:
        key: The cache key (filename without extension)
    
    Returns:
        Dict with data, last_update, source, and freshness info, or None if not found
    """
    try:
        # Try to load from file
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        file_path = os.path.join(data_dir, f"{key}.json")
        
        if not os.path.exists(file_path):
            logger.info(f"Cache file not found for key: {key}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        
        # Calculate freshness
        last_update_str = payload.get("last_update", "")
        if last_update_str:
            try:
                last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                now = datetime.now(last_update.tzinfo) if last_update.tzinfo else datetime.now()
                time_diff = (now - last_update).total_seconds()
                
                # Mark as stale if older than 1 hour
                payload["freshness"] = "stale" if time_diff > 3600 else "fresh"
            except ValueError:
                payload["freshness"] = "unknown"
        
        logger.info(f"Successfully loaded data from {file_path}")
        return payload
        
    except Exception as e:
        logger.error(f"Error loading JSON data for key {key}: {str(e)}")
        return None