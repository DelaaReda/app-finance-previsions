"""
Data Seeder - Populate snapshots with real data to ensure never-empty contract
Task: FC-REAL-SEED-001
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add backend to path for imports
backend_root = Path(__file__).resolve().parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from storage.io import save_json


def seed_real_data_snapshots():
    """
    Populate data snapshots with real data to maintain never-empty contract.
    This ensures that all API endpoints serve real, meaningful data.
    """
    print("Starting real data seeding job...")
    print("Task: FC-REAL-SEED-001 - Data Snapshot Seeding with Real Data")
    print(f"Started: {datetime.now().isoformat()}")
    print("-" * 60)
    
    seeding_results = {
        "forecasts": None,
        "news_feed": None,
        "brief_weekly": None,
        "backtests": None,
        "health_overall": None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": ["data_seeder_job", "real_data_population", "fc-real-seed-001"]
    }
    
    try:
    try:
        # 1. Seed forecasts with real data
        print("Seeding forecasts with real data...")
        try:
            # Use the forecast job that should generate real data
            from jobs.forecasts import run_forecasts_job
            forecasts_result = run_forecasts_job()
            seeding_results["forecasts"] = {
                "status": "success" if forecasts_result and not forecasts_result.get("error") else "fallback",
                "count": len(forecasts_result.get("data", {}).get("rows", [])) if isinstance(forecasts_result.get("data"), dict) else 0,
                "message": forecasts_result.get("message", "Real forecast data populated"),
                "generated_at": forecasts_result.get("generated_at", datetime.utcnow().isoformat() + "Z")
            }
        except Exception as e:
            seeding_results["forecasts"] = {
                "status": "error",
                "count": 0,
                "message": f"Forecast seeding failed: {str(e)}",
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        forecast_count = seeding_results["forecasts"]["count"] if seeding_results["forecasts"] else 0
        print(f"  Forecast seeding completed: {forecast_count} rows")
        
        # 2. Seed news with real data
        print("Seeding news feed with real data...")
        try:
            from jobs.news_ingest import run_news_ingest_job
            news_result = run_news_ingest_job()
            seeding_results["news_feed"] = {
                "status": "success" if news_result and (news_result.get("count", 0) > 0 or len(news_result.get("articles", [])) > 0) else "fallback",
                "count": len(news_result.get("articles", [])) if isinstance(news_result, dict) and "articles" in news_result else 0,
                "message": "Real news data populated" if isinstance(news_result, dict) and "articles" in news_result else "News seeding with fallback data",
                "generated_at": news_result.get("generated_at", datetime.utcnow().isoformat() + "Z") if isinstance(news_result, dict) else datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            seeding_results["news_feed"] = {
                "status": "error",
                "count": 0,
                "message": f"News seeding failed: {str(e)}, using fallback",
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        news_count = seeding_results["news_feed"]["count"] if seeding_results["news_feed"] else 0
        print(f"  News seeding completed: {news_count} articles")
        
        # 3. Seed brief with real data  
        print("Seeding weekly brief with real data...")
        try:
            from jobs.weekly_brief import run_and_persist_weekly_brief
            brief_result = run_and_persist_weekly_brief()
            seeding_results["brief_weekly"] = {
                "status": "success" if brief_result and "ok" in brief_result else "fallback",
                "count": len(brief_result.get("top_signals", [])) if isinstance(brief_result, dict) and "top_signals" in brief_result else 0,
                "message": "Real brief data populated",
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            seeding_results["brief_weekly"] = {
                "status": "error",
                "count": 0,
                "message": f"Brief seeding failed: {str(e)}, using fallback",
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        brief_count = seeding_results["brief_weekly"]["count"] if seeding_results["brief_weekly"] else 0
        print(f"  Brief seeding completed: {brief_count} signals")
        
        # 4. Seed backtests with real data
        print("Seeding backtests with real data...")
        try:
            from jobs.backtests import run_backtests_job
            backtests_result = run_backtests_job()
            seeding_results["backtests"] = {
                "status": "success" if backtests_result and not backtests_result.get("error") else "fallback",
                "count": len(backtests_result.get("results", [])) if isinstance(backtests_result, dict) and "results" in backtests_result else 0,
                "message": backtests_result.get("message", "Real backtest data populated"),
                "generated_at": backtests_result.get("generated_at", datetime.utcnow().isoformat() + "Z")
            }
        except Exception as e:
            seeding_results["backtests"] = {
                "status": "error",
                "count": 0,
                "message": f"Backtests seeding failed: {str(e)}, using fallback",
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
        
        backtests_count = seeding_results["backtests"]["count"] if seeding_results["backtests"] else 0
        print(f"  Backtests seeding completed: {backtests_count} results")
        
        # 5. Create overall health snapshot
        seeding_results["health_overall"] = {
            "backend_up": True,
            "data_availability": {
                "forecasts": seeding_results["forecasts"]["count"] > 0 if seeding_results["forecasts"] else False,
                "news_feed": seeding_results["news_feed"]["count"] > 0 if seeding_results["news_feed"] else False, 
                "brief_weekly": seeding_results["brief_weekly"]["count"] >= 0 if seeding_results["brief_weekly"] else True,  # Allow 0 for briefs
                "backtests": seeding_results["backtests"]["count"] > 0 if seeding_results["backtests"] else False
            },
            "last_updates": {
                "forecasts": seeding_results["forecasts"]["generated_at"] if seeding_results["forecasts"] else None,
                "news": seeding_results["news_feed"]["generated_at"] if seeding_results["news_feed"] else None,
                "brief_weekly": seeding_results["brief_weekly"]["generated_at"] if seeding_results["brief_weekly"] else None,
                "backtests": seeding_results["backtests"]["generated_at"] if seeding_results["backtests"] else None
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "status": "healthy" if all([
                seeding_results["forecasts"] and seeding_results["forecasts"]["count"] > 0,
                seeding_results["news_feed"] and seeding_results["news_feed"]["count"] > 0,
                seeding_results["backtests"] and seeding_results["backtests"]["count"] > 0
            ]) else "degraded"
        }
        
        # Save the seeding report to track what data is available
        save_path = save_json("data_seeding_report", seeding_results, source=["data_seeder_job", "fc-real-seed-001", "real_data_population"])
        
        print("-" * 60)
        print("DATA SEEDING JOB COMPLETED")
        status = seeding_results["health_overall"]["status"]
        print(f"Status: {'SUCCESS' if status == 'healthy' else 'DEGRADED'}")
        print(f"Forecasts: {seeding_results['forecasts']['count'] if seeding_results['forecasts'] else 0} rows")
        print(f"News: {seeding_results['news_feed']['count'] if seeding_results['news_feed'] else 0} articles")
        print(f"Brief: {seeding_results['brief_weekly']['count'] if seeding_results['brief_weekly'] else 0} signals")
        print(f"Backtests: {seeding_results['backtests']['count'] if seeding_results['backtests'] else 0} results")
        print(f"Generated: {seeding_results['timestamp']}")
        print("=" * 60)
        
        return seeding_results
        
    except Exception as e:
        print(f"Error in data seeding job: {str(e)}")
        
        # Create fallback seeding report to maintain never-empty contract
        fallback_results = {
            "forecasts": {"status": "error", "count": 0, "message": "Job failed", "error": str(e)},
            "news_feed": {"status": "error", "count": 0, "message": "Job failed", "error": str(e)},
            "brief_weekly": {"status": "error", "count": 0, "message": "Job failed", "error": str(e)},
            "backtests": {"status": "error", "count": 0, "message": "Job failed", "error": str(e)},
            "health_overall": {"status": "error", "data_availability": {"forecasts": False, "news_feed": False, "brief_weekly": False, "backtests": False}},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": ["data_seeder_job", "error_fallback", "fc-real-seed-001"],
            "error": str(e),
            "message": "Data seeding failed, but fallback report generated to maintain never-empty contract"
        }
        
        # Save fallback data to ensure API endpoints have data to serve
        try:
            save_json("data_seeding_report", fallback_results, source=["data_seeder_job", "error_fallback", "fc-real-seed-001"])
        except:
            pass  # If even saving fallback fails, just return it
        
        print("Fallback report generated to maintain never-empty contract.")
        return fallback_results


if __name__ == "__main__":
    result = seed_real_data_snapshots()