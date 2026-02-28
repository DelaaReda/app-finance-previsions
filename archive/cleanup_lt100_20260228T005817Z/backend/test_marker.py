import os
import pytest

def test_marker_exists():
    marker_path = "/Users/venom/Documents/analyse-financiere/copilot-app/backend/.qwen_runs/20251212-001810/marker.txt"
    assert os.path.exists(marker_path), f"Le fichier marker {marker_path} n'existe pas"