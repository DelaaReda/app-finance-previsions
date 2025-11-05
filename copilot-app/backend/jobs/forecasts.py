"""
Forecast Job - Orchestrates the hybrid ML+LLM forecasting pipeline
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from models.ml_forecast import run_forecast_generation
from models.llm_ranker import run_llm_ranking
from storage.io import save_json

# Directory for data storage
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(exist_ok=True)


def run_forecasts_job():
    """
    Main forecast job that:
    1. Generates forecasts using ML model
    2. Ranks forecasts using LLM
    3. Saves results to persistent storage
    """
    print("[INFO] Starting forecasts generation job...")
    
    try:
        # Step 1: Generate forecasts with ML model
        print("[INFO] Generating base forecasts with ML model...")
        base_forecasts = run_forecast_generation()
        
        print(f"[INFO] Generated {len(base_forecasts)} base forecasts")
        
        # Step 2: Rank forecasts with LLM
        print("[INFO] Ranking forecasts with LLM...")
        ranked_forecasts = run_llm_ranking()
        
        print(f"[INFO] Ranked {len(ranked_forecasts)} forecasts with LLM")
        
        # Step 3: Prepare final payload
        final_payload = {
            "rows": ranked_forecasts,
            "count": len(ranked_forecasts),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "model_version": "hybrid_v1_ml_llm",
            "pipeline": {
                "ml_model": "technical_indicators_v1",
                "llm_model": "g4f_ranker_v1",
                "processed_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        # Step 4: Save to persistent storage
        save_json("forecasts", final_payload, source=["job:forecast_hybrid_v1", "ml_model", "llm_ranker"])
        
        print(f"[SUCCESS] Forecasts job completed. Saved {len(ranked_forecasts)} forecasts to storage.")
        return final_payload
        
    except Exception as e:
        print(f"[ERROR] Forecasts job failed: {str(e)}")
        # Return empty payload on failure, but log the error
        error_payload = {
            "rows": [],
            "count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
            "model_version": "hybrid_v1_ml_llm",
            "pipeline": {
                "ml_model": "technical_indicators_v1",
                "llm_model": "g4f_ranker_v1",
                "processed_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        # Still save error state to maintain never-empty pattern
        save_json("forecasts", error_payload, source=["job:forecast_hybrid_v1", "error_fallback"])
        return error_payload


def get_latest_forecasts():
    """
    Retrieve the latest forecasts from persistent storage
    """
    from storage.io import load_json
    
    forecasts_snapshot = load_json("forecasts")
    if forecasts_snapshot:
        # If forecasts_snapshot has a payload key, return that
        if "payload" in forecasts_snapshot:
            return forecasts_snapshot["payload"]
        else:
            # Otherwise return the whole object with safe defaults
            return {
                "rows": forecasts_snapshot.get("rows", []),
                "count": forecasts_snapshot.get("count", 0),
                "generated_at": forecasts_snapshot.get("generated_at", datetime.utcnow().isoformat() + "Z"),
                "model_version": forecasts_snapshot.get("model_version", "hybrid_v1_ml_llm"),
                "pipeline": forecasts_snapshot.get("pipeline", {
                    "ml_model": "technical_indicators_v1",
                    "llm_model": "g4f_ranker_v1",
                    "processed_at": forecasts_snapshot.get("generated_at", datetime.utcnow().isoformat() + "Z")
                })
            }
    else:
        # Return empty structure if no forecasts available
        return {
            "rows": [],
            "count": 0,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "model_version": "hybrid_v1_ml_llm",
            "pipeline": {
                "ml_model": "technical_indicators_v1",
                "llm_model": "g4f_ranker_v1",
                "processed_at": None
            }
        }


if __name__ == "__main__":
    # Run standalone for testing
    result = run_forecasts_job()
    print(f"Job completed with {result['count']} forecasts")