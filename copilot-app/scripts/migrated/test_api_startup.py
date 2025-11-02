#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal test to verify that the API can start without import errors.
This test imports the main API module and verifies it can be created without errors.
"""

import sys
import traceback
from pathlib import Path

def test_api_startup():
    """Test that the API can be created without import errors."""
    print("Testing API startup...")
    
    # Add src to path to ensure imports work
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    
    try:
        # Try to import the create_app function from the main API module
        print("Attempting to import create_app from api.main...")
        from api.main import create_app
        print("✓ Successfully imported create_app function")
        
        # Try to create the FastAPI application instance
        print("Attempting to create FastAPI application instance...")
        app = create_app()
        
        if app:
            print("✓ Successfully created FastAPI application instance")
            print(f"✓ App title: {app.title}")
            print(f"✓ App version: {app.version}")
            return True
        else:
            print("✗ Failed to create FastAPI application instance - create_app returned None")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error during API startup test: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("API Startup Test")
    print("Verifying that the API can be created without import errors")
    print("=" * 60)
    
    success = test_api_startup()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ API startup test PASSED!")
        print("The API can be created without import errors.")
    else:
        print("❌ API startup test FAILED!")
        print("There were errors creating the API.")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)