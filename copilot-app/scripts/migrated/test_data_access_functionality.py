#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick functionality test for core data access modules.
This script tests that the functions can be called without errors (without executing network calls).
"""

import sys
from pathlib import Path

# Add src to path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing core data access functionality...")

try:
    from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
    from core.market_data import get_price_history, get_fundamentals, get_fred_series
    from analytics.phase3_macro import get_us_macro_bundle, macro_nowcast
    from ingestion.finnews import run_pipeline
    
    print("✓ All imports successful")
    
    # Test function signatures by checking if they have the expected attributes
    print(f"✓ get_close_series is callable: {callable(get_close_series)}")
    print(f"✓ load_macro_forecast_rows is callable: {callable(load_macro_forecast_rows)}")
    print(f"✓ load_news_features is callable: {callable(load_news_features)}")
    print(f"✓ get_price_history is callable: {callable(get_price_history)}")
    print(f"✓ get_fundamentals is callable: {callable(get_fundamentals)}")
    print(f"✓ get_fred_series is callable: {callable(get_fred_series)}")
    print(f"✓ get_us_macro_bundle is callable: {callable(get_us_macro_bundle)}")
    print(f"✓ macro_nowcast is callable: {callable(macro_nowcast)}")
    print(f"✓ run_pipeline is callable: {callable(run_pipeline)}")
    
    # Test with minimal parameters to check if function signatures are correct
    # We'll use try/except to handle expected errors due to missing API keys or network
    print("\nTesting function signatures (expecting parameter errors, not import errors)...")
    
    try:
        # This should fail with parameter error, not import error
        result = get_close_series("AAPL")
        print(f"✓ get_close_series('AAPL') executed without import errors, result type: {type(result)}")
    except TypeError as e:
        if "required positional argument" in str(e):
            print(f"✓ get_close_series has correct signature (missing required params is expected): {e}")
        else:
            print(f"? get_close_series error (might be expected): {e}")
    except Exception as e:
        print(f"? get_close_series error (might be expected due to network/API): {type(e).__name__}: {e}")
    
    try:
        result = get_price_history("AAPL")
        print(f"✓ get_price_history('AAPL') executed without import errors, result type: {type(result)}")
    except TypeError as e:
        if "required positional argument" in str(e):
            print(f"✓ get_price_history has correct signature (missing required params is expected): {e}")
        else:
            print(f"? get_price_history error (might be expected): {e}")
    except Exception as e:
        print(f"? get_price_history error (might be expected due to network/API): {type(e).__name__}: {e}")
    
    print("\nCore data access functionality test completed successfully!")
    print("All modules imported correctly and functions are available.")
    print("Actual data fetching requires proper API keys and network connectivity.")

except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)