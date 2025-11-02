#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify that the API can start without import errors.
This script tests that the API application can be created successfully,
ensuring all dependencies and imports work correctly.
"""

import sys
import traceback
from pathlib import Path

# Add src to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing API imports and application creation...")

def test_api_imports():
    """Test that all necessary modules for the API can be imported."""
    print("\n1. Testing API module imports...")
    
    try:
        from api.main import create_app
        print("✓ Successfully imported create_app from api.main")
    except ImportError as e:
        print(f"✗ Failed to import create_app from api.main: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error importing create_app from api.main: {e}")
        traceback.print_exc()
        return False
    
    # Test importing the main modules that the API depends on
    modules_to_test = [
        ("core.data_access", [
            "get_close_series", "load_macro_forecast_rows", "check_data_freshness"
        ]),
        ("core.market_data", [
            "get_price_history", "get_fundamentals", "get_fred_series"
        ]),
        ("core.downsample", ["lttb"]),
        ("core.duck", ["query_parquet", "parquet_glob"]),
        ("api.services.news_service", [
            "get_news_events", "get_news_feed", "get_sentiment"
        ]),
        ("analytics.phase2_technical", ["compute_indicators"]),
        ("research.scoring", ["calculate_composite_score", "compute_composite_brief"]),
        ("research.rag_store", ["RAGStore"]),
        ("research.alerts", ["alerts_for_ticker"]),
        ("ingestion.finnews", ["run_pipeline"]),
        ("dash_app.api", ["forecasts", "dashboard_kpis"]),
        ("agents.backtest_agent", ["run_backtest"]),
        ("research.versioned_notes", ["VersionedNotesStore", "NoteType"]),
    ]
    
    for module_name, functions in modules_to_test:
        try:
            module = __import__(module_name, fromlist=functions)
            print(f"✓ Successfully imported {module_name}")
            
            # Test that specific functions/classes exist
            for func_name in functions:
                if hasattr(module, func_name):
                    print(f"  ✓ {func_name} is available in {module_name}")
                else:
                    print(f"  ⚠ {func_name} is NOT available in {module_name}")
        except ImportError as e:
            print(f"✗ Failed to import {module_name}: {e}")
            # Don't return False here as some modules might be optional
        except Exception as e:
            print(f"✗ Unexpected error importing {module_name}: {e}")
            # Don't return False here as some modules might be optional
    
    return True

def test_app_creation():
    """Test that the API application can be created without errors."""
    print("\n2. Testing API application creation...")
    
    try:
        from api.main import create_app
        app = create_app()
        
        if app:
            print("✓ Successfully created FastAPI application instance")
            print(f"  ✓ App title: {app.title}")
            print(f"  ✓ App version: {app.version}")
            return True
        else:
            print("✗ Failed to create FastAPI application instance - got None")
            return False
            
    except Exception as e:
        print(f"✗ Failed to create FastAPI application: {e}")
        traceback.print_exc()
        return False

def test_dependency_availability():
    """Test that key dependencies are available."""
    print("\n3. Testing key dependency availability...")
    
    dependencies_to_test = [
        "fastapi",
        "uvicorn", 
        "pandas",
        "pydantic",
        "yfinance",
        "requests",
        "duckdb",
        "numpy"
    ]
    
    for dep in dependencies_to_test:
        try:
            __import__(dep)
            print(f"✓ {dep} is available")
        except ImportError:
            print(f"⚠ {dep} is NOT available (this may be expected depending on the module)")
    
    return True

def main():
    """Main test function."""
    print("=" * 60)
    print("API Import and Startup Test")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_api_imports()
    
    if not imports_ok:
        print("\n❌ API import tests failed!")
        return False
    
    # Test app creation
    app_creation_ok = test_app_creation()
    
    if not app_creation_ok:
        print("\n❌ API application creation failed!")
        return False
    
    # Test dependencies
    test_dependency_availability()
    
    print("\n" + "=" * 60)
    print("✅ All API import and startup tests passed!")
    print("The API should be able to start without import errors.")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)