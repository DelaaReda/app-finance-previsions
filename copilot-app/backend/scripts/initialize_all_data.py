#!/usr/bin/env python3
"""
Script to initialize all data files by running all jobs
Fixes the root cause: missing data generation
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    try:
        import pandas
    except ImportError:
        missing.append("pandas")
    
    try:
        import yfinance
    except ImportError:
        missing.append("yfinance")
    
    try:
        import g4f
    except ImportError:
        missing.append("g4f")
    
    try:
        import feedparser
    except ImportError:
        missing.append("feedparser")
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("   Install with: pip install " + " ".join(missing))
        return False
    return True

def run_job(name, job_func, *args, **kwargs):
    """Run a job and handle errors"""
    print(f"\n{'='*60}")
    print(f"📊 Running {name}...")
    print(f"{'='*60}")
    
    import logging
    # Suppress verbose G4F warnings during execution
    logging.getLogger('g4f').setLevel(logging.ERROR)
    logging.getLogger('jobs').setLevel(logging.WARNING)
    
    try:
        result = job_func(*args, **kwargs)
        if isinstance(result, dict):
            status = result.get('status', 'unknown')
            count = result.get('forecast_count') or result.get('article_count') or result.get('count', 0)
            print(f"✅ {name} completed: status={status}, count={count}")
            if result.get('error'):
                print(f"   ⚠️  Warning: {result.get('error')}")
            if result.get('status') == 'pending_dependencies':
                print(f"   ⚠️  Note: Some dependencies may be missing")
            return True
        else:
            print(f"✅ {name} completed")
            return True
    except ImportError as e:
        print(f"❌ {name} failed: Missing dependency - {e}")
        print(f"   Install with: pip install pandas yfinance g4f feedparser")
        return False
    except Exception as e:
        print(f"❌ {name} failed: {e}")
        # Only show full traceback for unexpected errors
        if "api_key" not in str(e).lower() and "import" not in str(e).lower():
            import traceback
            traceback.print_exc()
        return False

def main():
    print("🚀 Initializing all data files...")
    print(f"📂 Backend root: {backend_root}")
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return 1
    
    print("\n✅ All dependencies installed")
    
    results = {}
    
    # 1. Forecasts job
    try:
        from jobs.forecasts import run_forecasts_job
        results['forecasts'] = run_job(
            "Forecasts Job",
            run_forecasts_job,
            ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META"]
        )
    except Exception as e:
        print(f"❌ Failed to import forecasts job: {e}")
        results['forecasts'] = False
    
    # 2. News ingest job
    try:
        from jobs.news_ingest import run_news_ingest
        results['news'] = run_job("News Ingest Job", run_news_ingest)
    except Exception as e:
        print(f"❌ Failed to import news job: {e}")
        results['news'] = False
    
    # 3. Market brief job (depends on forecasts + news)
    if results.get('forecasts') or results.get('news'):
        try:
            from jobs.market_brief import run_market_brief_job
            results['brief'] = run_job("Market Brief Job", run_market_brief_job)
        except Exception as e:
            print(f"❌ Failed to import market brief job: {e}")
            results['brief'] = False
    else:
        print("\n⚠️  Skipping Market Brief (requires forecasts or news)")
        results['brief'] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 SUMMARY")
    print(f"{'='*60}")
    for job, success in results.items():
        status = "✅" if success else "❌"
        print(f"   {status} {job.capitalize()}")
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n✅ {success_count}/{total_count} jobs completed successfully")
    
    if success_count == total_count:
        print("\n🎉 All data files initialized!")
        return 0
    else:
        print(f"\n⚠️  {total_count - success_count} job(s) failed - check errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())

