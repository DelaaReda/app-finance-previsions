"""
Initialize data for immediate availability
Runs forecasts and news jobs ONCE to populate data/ folder
Integration by: ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
Task: FC-INT-009 - Ensure data is available on first startup
"""
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def initialize_all_data():
    """
    Run all jobs once to initialize data files
    This ensures API never returns empty on first start
    """
    logger.info("🚀 Initializing all data files for Finance Copilot...")
    
    results = {}
    
    # Initialize forecasts
    try:
        logger.info("=" * 60)
        logger.info("1/2 Running forecasts job...")
        logger.info("=" * 60)
        
        from jobs.forecasts import run_forecasts_job
        forecast_result = run_forecasts_job()
        
        results['forecasts'] = forecast_result
        
        if forecast_result.get('status') == 'completed':
            logger.info(f"✅ Forecasts: {forecast_result.get('forecast_count', 0)} generated successfully")
        elif forecast_result.get('status') == 'pending_dependencies':
            logger.warning(f"⚠️  Forecasts: Dependencies missing - {forecast_result.get('error', 'Unknown')}")
        else:
            logger.error(f"❌ Forecasts: Failed - {forecast_result.get('error', 'Unknown')}")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize forecasts: {str(e)}", exc_info=True)
        results['forecasts'] = {
            "status": "error",
            "error": str(e)
        }
    
    # Initialize news (when implemented)
    try:
        logger.info("=" * 60)
        logger.info("2/2 Running news ingestion job...")
        logger.info("=" * 60)
        
        from jobs.news_ingest import run_news_ingest
        news_result = run_news_ingest()
        
        results['news'] = news_result
        
        if news_result.get('status') == 'completed':
            logger.info(f"✅ News: {news_result.get('processed_count', 0)} articles processed")
        else:
            logger.warning(f"⚠️  News: Not yet implemented (stub active)")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize news: {str(e)}", exc_info=True)
        results['news'] = {
            "status": "error",
            "error": str(e)
        }
    
    logger.info("=" * 60)
    logger.info("🎉 Data initialization complete!")
    logger.info("=" * 60)
    
    # Print summary
    logger.info("\n📊 SUMMARY:")
    for key, value in results.items():
        status = value.get('status', 'unknown')
        logger.info(f"  - {key.upper()}: {status}")
    
    return results

if __name__ == "__main__":
    """
    Run this script manually to initialize data:
    
    cd /workspace/copilot-app/backend
    python jobs/initialize_data.py
    
    Or from workspace root:
    python copilot-app/backend/jobs/initialize_data.py
    """
    logger.info("Running data initialization script...")
    logger.info(f"Working directory: {Path.cwd()}")
    logger.info(f"Backend path: {backend_path}")
    
    try:
        results = initialize_all_data()
        
        # Exit with appropriate code
        all_success = all(
            r.get('status') in ['completed', 'pending_dependencies'] 
            for r in results.values()
        )
        
        if all_success:
            logger.info("\n✅ Initialization script completed successfully")
            sys.exit(0)
        else:
            logger.error("\n❌ Some jobs failed during initialization")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n💥 Initialization script failed: {str(e)}", exc_info=True)
        sys.exit(1)
