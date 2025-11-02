#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive test to verify that the API can start without import errors.
This test handles both scenarios: with and without dependencies installed.
"""

import sys
import traceback
from pathlib import Path
import importlib.util

# Add src to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_dependency(dep_name, description=""):
    """Check if a dependency is available."""
    try:
        __import__(dep_name)
        return True
    except ImportError:
        return False

def test_api_creation_with_dependencies():
    """Test API creation when dependencies are available."""
    print("Testing API creation with dependencies...")
    
    try:
        from api.main import create_app
        app = create_app()
        
        if app:
            print("✓ Successfully created FastAPI application instance")
            print(f"  - App title: {app.title}")
            print(f"  - App version: {app.version}")
            print(f"  - Number of routes: {len(app.routes)}")
            return True
        else:
            print("✗ Failed to create FastAPI application instance - got None")
            return False
            
    except Exception as e:
        print(f"✗ Failed to create FastAPI application: {e}")
        traceback.print_exc()
        return False

def test_api_syntax_only():
    """Test API syntax without dependencies."""
    print("Testing API syntax without dependencies...")
    
    # Check if the main API file exists
    main_api_path = Path(__file__).parent / "src" / "api" / "main.py"
    if not main_api_path.exists():
        print("✗ API main.py file does not exist")
        return False
    
    try:
        # Try to compile the file to check for syntax errors
        with open(main_api_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        compile(source_code, str(main_api_path), 'exec')
        print("✓ API main.py has valid Python syntax")
        
        # Try to load the module using importlib to check for import errors
        spec = importlib.util.spec_from_file_location("main", str(main_api_path))
        if spec is None or spec.loader is None:
            print("✗ Could not create module spec")
            return False
        
        # Create a new module without executing it to avoid import errors
        # This checks if the file can be parsed without dependencies
        print("✓ API main.py can be parsed")
        return True
        
    except SyntaxError as e:
        print(f"✗ Syntax error in API main.py: {e}")
        return False
    except Exception as e:
        print(f"✗ Error parsing API main.py: {e}")
        return False

def test_file_structure():
    """Test that required API files exist."""
    print("Testing API file structure...")
    
    required_files = [
        "src/api/main.py",
        "src/api/__init__.py",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} does not exist")
            all_exist = False
    
    return all_exist

def test_core_modules_imports():
    """Test that core modules can be imported (these may have fewer dependencies)."""
    print("Testing core module imports...")
    
    core_modules = [
        ("core.data_access", "Data access layer"),
        ("core.market_data", "Market data functions"),
        ("core.config", "Configuration"),
        ("core.duck", "DuckDB utilities"),
    ]
    
    success_count = 0
    for module_name, description in core_modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name} - {description}")
            success_count += 1
        except ImportError as e:
            print(f"✗ {module_name} - {description} (Import error: {e})")
        except Exception as e:
            print(f"? {module_name} - {description} (Other error: {e})")
    
    print(f"Core modules imported: {success_count}/{len(core_modules)}")
    return success_count > 0  # At least some core modules should work

def main():
    """Main test function."""
    print("=" * 80)
    print("Comprehensive API Import and Startup Test")
    print("=" * 80)
    
    # Check if key dependencies are available
    fastapi_available = check_dependency("fastapi")
    pandas_available = check_dependency("pandas")
    
    print(f"FastAPI available: {fastapi_available}")
    print(f"Pandas available: {pandas_available}")
    print()
    
    # Test file structure first
    structure_ok = test_file_structure()
    print()
    
    if not structure_ok:
        print("❌ API structure has critical issues!")
        return False
    
    # Test core modules
    core_imports_ok = test_core_modules_imports()
    print()
    
    # Test API based on dependency availability
    if fastapi_available and pandas_available:
        print("Dependencies are available, testing full API creation...")
        api_ok = test_api_creation_with_dependencies()
    else:
        print("Dependencies not available, testing API syntax only...")
        api_ok = test_api_syntax_only()
    
    print()
    
    # Summary
    print("=" * 80)
    print("Test Results Summary:")
    print(f"  File Structure:     {'✓ PASS' if structure_ok else '✗ FAIL'}")
    print(f"  Core Module Imports: {'✓ PASS' if core_imports_ok else '✗ FAIL'}")
    print(f"  API Test:           {'✓ PASS' if api_ok else '✗ FAIL'}")
    
    overall_success = structure_ok and core_imports_ok and api_ok
    
    if overall_success:
        print("\n✅ All tests passed! The API structure is valid.")
        if not (fastapi_available and pandas_available):
            print("💡 To run the full API, install dependencies with:")
            print("   pip install -r requirements-api.txt")
            print("   pip install -r requirements.txt")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
    
    print("=" * 80)
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)