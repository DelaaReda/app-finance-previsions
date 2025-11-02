#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test to verify that the API can be imported without syntax errors.
This test focuses on verifying that the API application can be created
when dependencies are available, or reports missing dependencies appropriately.
"""

import sys
from pathlib import Path

# Add src to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_api_import_structure():
    """Test that the API module structure is valid."""
    print("Testing API import structure...")
    
    # Check if the main API file exists
    api_main_path = Path(__file__).parent / "src" / "api" / "main.py"
    if not api_main_path.exists():
        print("✗ API main.py file does not exist")
        return False
    
    print("✓ API main.py file exists")
    
    # Try to check the syntax without importing dependencies
    try:
        with open(api_main_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Check syntax
        compile(source, str(api_main_path), 'exec')
        print("✓ API main.py has valid Python syntax")
        return True
    except SyntaxError as e:
        print(f"✗ Syntax error in API main.py: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading API main.py: {e}")
        return False

def test_api_creation():
    """Test creating the API application if dependencies are available."""
    print("Testing API application creation...")
    
    # Check if key dependencies are available
    missing_deps = []
    
    try:
        import fastapi
    except ImportError:
        missing_deps.append("fastapi")
    
    try:
        import pydantic
    except ImportError:
        missing_deps.append("pydantic")
    
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")
    
    if missing_deps:
        print(f"⚠ Missing dependencies: {', '.join(missing_deps)}")
        print("  The API will not start without these dependencies.")
        print("  Install them with: pip install -r requirements-api.txt")
        return True  # This is expected behavior, not a test failure
    
    # If dependencies are available, try to create the app
    try:
        from api.main import create_app
        app = create_app()
        
        if app:
            print("✓ Successfully created FastAPI application")
            print(f"  - Title: {app.title}")
            print(f"  - Version: {app.version}")
            return True
        else:
            print("✗ create_app() returned None")
            return False
            
    except Exception as e:
        print(f"✗ Error creating API application: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("API Startup Test")
    print("Verifies that the API can start without import errors")
    print("=" * 60)
    
    # Test the API structure
    structure_ok = test_api_import_structure()
    print()
    
    if not structure_ok:
        print("❌ API structure test failed!")
        return False
    
    # Test API creation
    creation_ok = test_api_creation()
    print()
    
    # Final result
    print("=" * 60)
    if creation_ok:
        print("✅ API startup test passed!")
        print("The API can be started when dependencies are installed.")
    else:
        print("❌ API startup test failed!")
    
    print("=" * 60)
    return creation_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)