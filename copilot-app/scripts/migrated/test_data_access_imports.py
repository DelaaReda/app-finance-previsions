#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify that core data access imports work correctly.
This script tests the main data access modules and functions from the project.
"""

import sys
import traceback
from pathlib import Path

# Add src to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing core data access imports...")

# Test 1: Basic imports
print("\n1. Testing basic imports...")
try:
    from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
    print("✓ Successfully imported from core.data_access")
except Exception as e:
    print(f"✗ Failed to import from core.data_access: {e}")
    traceback.print_exc()

try:
    from core.market_data import get_price_history, get_fundamentals, get_fred_series
    print("✓ Successfully imported from core.market_data")
except Exception as e:
    print(f"✗ Failed to import from core.market_data: {e}")
    traceback.print_exc()

try:
    from analytics.phase3_macro import get_us_macro_bundle, macro_nowcast
    print("✓ Successfully imported from analytics.phase3_macro")
except Exception as e:
    print(f"✗ Failed to import from analytics.phase3_macro: {e}")
    traceback.print_exc()

try:
    from ingestion.finnews import run_pipeline
    print("✓ Successfully imported from ingestion.finnews")
except Exception as e:
    print(f"✗ Failed to import from ingestion.finnews: {e}")
    traceback.print_exc()

# Test 2: Test if yfinance is available (needed for market data)
print("\n2. Testing required dependencies...")
try:
    import yfinance
    print("✓ yfinance is available")
except ImportError:
    print("✗ yfinance is not available - market data functions will fail")

try:
    import pandas
    print("✓ pandas is available")
except ImportError:
    print("✗ pandas is not available - data functions will fail")

try:
    import requests
    print("✓ requests is available")
except ImportError:
    print("✗ requests is not available - web data fetching will fail")

# Test 3: Test function signatures (without calling them to avoid network calls)
print("\n3. Testing function availability...")
functions_to_test = [
    ('get_close_series', 'core.data_access'),
    ('load_macro_forecast_rows', 'core.data_access'),
    ('load_news_features', 'core.data_access'),
    ('get_price_history', 'core.market_data'),
    ('get_fundamentals', 'core.market_data'),
    ('get_fred_series', 'core.market_data'),
    ('get_us_macro_bundle', 'analytics.phase3_macro'),
    ('macro_nowcast', 'analytics.phase3_macro'),
    ('run_pipeline', 'ingestion.finnews'),
]

for func_name, module_name in functions_to_test:
    try:
        # Import the module
        module = __import__(module_name, fromlist=[func_name])
        func = getattr(module, func_name)
        if callable(func):
            print(f"✓ Function {func_name} is available and callable in {module_name}")
        else:
            print(f"✗ {func_name} is not callable in {module_name}")
    except Exception as e:
        print(f"✗ Failed to access function {func_name} in {module_name}: {e}")

# Test 4: Test basic functionality with minimal calls (avoiding network calls)
print("\n4. Testing basic functionality (minimal calls)...")

# Test dataclass availability
try:
    from analytics.phase3_macro import MacroBundle, NowcastView
    print("✓ Successfully imported dataclasses from analytics.phase3_macro")
except Exception as e:
    print(f"✗ Failed to import dataclasses from analytics.phase3_macro: {e}")

# Test core module imports
try:
    import core
    import core.data_access
    import core.market_data
    import core.config
    import core.duck
    print("✓ Successfully imported core modules")
except Exception as e:
    print(f"✗ Failed to import core modules: {e}")

# Test analytics module imports
try:
    import analytics
    import analytics.phase3_macro
    print("✓ Successfully imported analytics modules")
except Exception as e:
    print(f"✗ Failed to import analytics modules: {e}")

# Test ingestion module imports
try:
    import ingestion
    import ingestion.finnews
    print("✓ Successfully imported ingestion modules")
except Exception as e:
    print(f"✗ Failed to import ingestion modules: {e}")

print("\n5. Testing import of additional core utilities...")
try:
    from core import cache, config, data_store, datasets, io_utils, stock_utils
    print("✓ Successfully imported additional core utilities")
except Exception as e:
    print(f"✗ Failed to import additional core utilities: {e}")

print("\nAll import tests completed!")
print("\nNote: This test verifies that imports work correctly.")
print("Actual functionality requires proper API keys and network connectivity.")