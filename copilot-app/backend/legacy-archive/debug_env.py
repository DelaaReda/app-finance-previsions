#!/usr/bin/env python3
"""
Debug script to check environment variables and FRED API functionality
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Explicitly load dotenv from current directory
from dotenv import load_dotenv
load_dotenv()

print("=== Environment Variable Debug ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}...")

print("\n--- Environment Variables ---")
fred_key = os.getenv('FRED_API_KEY')
print(f"FRED_API_KEY: {repr(fred_key)}")
print(f"FRED_API_KEY length: {len(fred_key) if fred_key else 0}")

finnhub_key = os.getenv('FINNHUB_API_KEY')
print(f"FINNHUB_API_KEY: {repr(finnhub_key)}")
print(f"FINNHUB_API_KEY length: {len(finnhub_key) if finnhub_key else 0}")

print("\n--- Testing FRED API Function ---")
try:
    from core.market_data import get_fred_series, _normalize_fred_key
    print(f"Normalized FRED key: {_normalize_fred_key(fred_key)}")
    
    print("Attempting to fetch CPI data...")
    df = get_fred_series('CPIAUCSL')
    print(f"Got DataFrame: {df is not None}")
    if df is not None:
        print(f"Shape: {df.shape}")
        print(f"Has data: {not df.empty}")
        if not df.empty:
            print(f"Latest value: {df.iloc[-1] if len(df) > 0 else 'None'}")
except Exception as e:
    print(f"Error testing FRED API: {e}")
    import traceback
    traceback.print_exc()