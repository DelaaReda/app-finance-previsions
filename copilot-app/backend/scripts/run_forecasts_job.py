#!/usr/bin/env python3
"""
Script to manually run the forecasts job and generate forecasts.json
This fixes the root cause: missing data generation
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

def main():
    print("🚀 Running forecasts job to generate data/forecasts.json...")
    print(f"📂 Backend root: {backend_root}")
    
    try:
        from jobs.forecasts import run_forecasts_job
        from storage.io import load_json
        
        # Check current state
        current = load_json("forecasts")
        if current and current.get("rows"):
            print(f"⚠️  Found existing forecasts: {len(current.get('rows', []))} rows")
            print("   Will regenerate...")
        
        # Run the job
        print("\n📊 Generating forecasts for SPY, QQQ, AAPL, MSFT, TSLA, NVDA...")
        print("   (This may take a moment as it uses LLM validation...)")
        
        import logging
        # Suppress verbose G4F warnings during execution
        logging.getLogger('g4f').setLevel(logging.ERROR)
        
        result = run_forecasts_job(["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA"])
        
        print(f"\n✅ Job completed!")
        print(f"   Status: {result.get('status')}")
        print(f"   Forecast count: {result.get('forecast_count')}")
        
        if result.get('error'):
            print(f"   ⚠️  Error: {result.get('error')}")
        
        if result.get('status') == 'pending_dependencies':
            print(f"\n   ⚠️  Note: Some dependencies may be missing")
            print(f"   Install with: pip install pandas yfinance g4f")
        
        # Verify the file was created
        forecasts_file = backend_root / "data" / "forecasts.json"
        if forecasts_file.exists():
            from storage.io import load_json
            saved = load_json("forecasts")
            if saved and saved.get("rows"):
                print(f"\n✅ Verified: forecasts.json contains {len(saved.get('rows', []))} forecasts")
                return 0
            else:
                print(f"\n❌ Error: forecasts.json exists but is empty or invalid")
                return 1
        else:
            print(f"\n❌ Error: forecasts.json was not created")
            return 1
            
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("   Missing dependencies. Install with:")
        print("   pip install pandas yfinance g4f")
        return 1
    except Exception as e:
        print(f"\n❌ Job failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

