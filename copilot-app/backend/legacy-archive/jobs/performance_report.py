"""
Performance Report Job - Generates ML model performance reports
Task: FC-P2-018
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Any

from models.performance_tracker import performance_tracker
from storage.base import save_json

def run_performance_report_job():
    """
    Generate model performance report and save to persistent storage
    """
    print("Running model performance report job...")
    
    try:
        # Get current performance report
        report = performance_tracker.get_performance_report()
        
        # Add job metadata
        report_with_meta = {
            "data": report,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "job_id": f"perf_report_{int(datetime.utcnow().timestamp())}",
            "source": ["ml_performance_tracker", "live_metrics", "fc-p2-018"],
            "version": "1.0.0"
        }
        
        # Save to persistent storage
        result_path = save_json("ml_performance.json", report_with_meta, source=["ml_performance_job", "fc-p2-018"])
        
        print(f"Performance report generated successfully and saved to {result_path}")
        print(f"Report contains metrics for {len(report['summary']['models_tracked'])} models")
        print(f"Total predictions tracked: {report['summary']['total_predictions']}")
        
        return report_with_meta
        
    except Exception as e:
        print(f"Error generating performance report: {str(e)}")
        
        # Return fallback report in case of error to maintain never-empty contract
        fallback_report = {
            "data": {
                "summary": {
                    "total_predictions": 0,
                    "evaluated_predictions": 0,
                    "evaluation_rate": 0.0,
                    "models_tracked": [],
                    "tickers_covered": [],
                    "horizons_covered": [],
                    "avg_confidence": 0.0
                },
                "overall_metrics": {
                    "classification_metrics": {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "hit_rate": 0.0, "sample_size": 0},
                    "regression_metrics": {"mse": 0.0, "rmse": 0.0, "mae": 0.0, "mape": 0.0, "direction_accuracy": 0.0, "sample_size": 0},
                    "sharpe_ratio": 0.0,
                    "sortino_ratio": 0.0,
                    "total_predictions": 0,
                    "evaluated_predictions": 0,
                    "avg_confidence": 0.0,
                    "calculated_at": datetime.utcnow().isoformat() + "Z"
                },
                "model_performance": {},
                "metrics_history": [],
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "last_update": None
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "job_id": f"perf_report_fallback_{int(datetime.utcnow().timestamp())}",
            "source": ["ml_performance_tracker", "fallback", "fc-p2-018"],
            "version": "1.0.0",
            "error": str(e)
        }
        
        # Still save the fallback data to ensure the endpoint has something to serve
        save_json("ml_performance.json", fallback_report, source=["ml_performance_job", "error_fallback", "fc-p2-018"])
        return fallback_report


if __name__ == "__main__":
    result = run_performance_report_job()
    print("Performance report job completed.")