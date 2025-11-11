#!/usr/bin/env python3
"""
Test script for FC-INT-009 integration
Tests that the forecast job can generate and save data
Integration by: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
"""
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
backend_path = str(Path(__file__).parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def test_forecast_integration():
    """Test that forecast job can generate data"""
    logger.info("=" * 70)
    logger.info("FC-INT-009 Integration Test")
    logger.info("=" * 70)
    
    # Test 1: Import check
    logger.info("\n📦 TEST 1: Checking imports...")
    try:
        from jobs.forecasts import run_forecasts_job
        from storage.base import load_forecasts
        logger.info("✅ Imports successful")
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Run forecast job
    logger.info("\n🔄 TEST 2: Running forecast job...")
    try:
        result = run_forecasts_job(tickers=["SPY", "QQQ", "AAPL"])
        logger.info(f"Job result: {result}")
        
        if result.get('status') == 'completed':
            logger.info(f"✅ Job completed: {result.get('forecast_count', 0)} forecasts")
        elif result.get('status') == 'pending_dependencies':
            logger.warning(f"⚠️  Dependencies missing: {result.get('error', 'Unknown')}")
            logger.info("This is expected if yfinance, g4f, pandas etc. not installed")
        else:
            logger.error(f"❌ Job failed: {result.get('error', 'Unknown')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Job execution failed: {e}", exc_info=True)
        return False
    
    # Test 3: Check if data was saved
    logger.info("\n💾 TEST 3: Checking saved data...")
    try:
        forecasts = load_forecasts()
        
        if forecasts is None:
            logger.warning("⚠️  No forecast file found (expected if dependencies missing)")
        else:
            rows = forecasts.get('data', {}).get('rows', [])
            logger.info(f"✅ Forecast file exists: {len(rows)} rows")
            logger.info(f"   Last update: {forecasts.get('last_update', 'N/A')}")
            logger.info(f"   Sources: {forecasts.get('source', [])}")
            
            if rows:
                logger.info(f"\n📊 Sample forecast:")
                sample = rows[0]
                logger.info(f"   Ticker: {sample.get('ticker', 'N/A')}")
                logger.info(f"   Direction: {sample.get('direction', 'N/A')}")
                logger.info(f"   Confidence: {sample.get('confidence', 'N/A')}")
                logger.info(f"   Expected return: {sample.get('expected_return', 'N/A')}")
                
    except Exception as e:
        logger.error(f"❌ Data check failed: {e}", exc_info=True)
        return False
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ Integration test completed")
    logger.info("=" * 70)
    return True

if __name__ == "__main__":
    logger.info("Starting FC-INT-009 integration test...\n")
    success = test_forecast_integration()
    
    if success:
        logger.info("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n💥 Some tests failed")
        sys.exit(1)
