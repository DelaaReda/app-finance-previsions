"""Test module to validate marker.txt existence in qwen runs directory."""
import os
import pytest


def test_marker_file_exists():
    """Test that marker.txt exists in the expected run directory."""
    run_id = "20251212-001810"
    marker_path = f"/Users/venom/Documents/analyse-financiere/copilot-app/backend/.qwen_runs/{run_id}/marker.txt"
    
    assert os.path.exists(marker_path), f"Marker file does not exist at: {marker_path}"
    
    # Verify the file is not empty
    assert os.path.getsize(marker_path) > 0, f"Marker file is empty: {marker_path}"


def test_marker_contains_correct_run_id():
    """Test that marker.txt contains the correct run ID."""
    run_id = "20251212-001810"
    marker_path = f"/Users/venom/Documents/analyse-financiere/copilot-app/backend/.qwen_runs/{run_id}/marker.txt"
    
    assert os.path.exists(marker_path), f"Marker file does not exist at: {marker_path}"
    
    with open(marker_path, 'r') as f:
        content = f.read()
        
    assert f"run_id={run_id}" in content, f"Expected run_id={run_id} not found in marker file"


@pytest.mark.parametrize("run_id", [
    "20251212-001810",
])
def test_marker_format(run_id):
    """Test that marker.txt has the expected format."""
    marker_path = f"/Users/venom/Documents/analyse-financiere/copilot-app/backend/.qwen_runs/{run_id}/marker.txt"
    
    assert os.path.exists(marker_path), f"Marker file does not exist at: {marker_path}"
    
    with open(marker_path, 'r') as f:
        content = f.read().strip()
        
    lines = content.split('\n')
    assert len(lines) >= 2, f"Marker file should have at least 2 lines, got {len(lines)}"
    
    # Check for expected keys
    content_dict = {}
    for line in lines:
        if '=' in line:
            key, value = line.split('=', 1)
            content_dict[key] = value
    
    assert 'run_id' in content_dict, "Missing run_id in marker file"
    assert content_dict['run_id'] == run_id, f"Incorrect run_id in marker file: {content_dict['run_id']}"
    assert 'created_at' in content_dict, "Missing created_at in marker file"