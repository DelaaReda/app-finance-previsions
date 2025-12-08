"""
Quality Gate Job - Runs quality checks on data files and ensures never-empty contract
Task: FC-DATA-007
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
import sys
import os
from datetime import datetime

# Add backend to path for imports
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up 2 levels to backend/
sys.path.insert(0, backend_root)

from core.data_quality import run_quality_audit, run_quality_gate
from storage.io import save_json


def run_data_quality_job():
    """
    Run the comprehensive data quality job to validate all data files
    """
    print("Starting data quality validation job...")
    print("Task: FC-DATA-007 - Data quality checks (gate)")
    
    try:
        # Run comprehensive audit
        audit_results = run_quality_audit()
        
        # Save results to persistent storage
        save_json("quality_report", {
            "audit_results": audit_results,
            "job_execution_time": datetime.utcnow().isoformat() + "Z",
            "job_type": "data_quality_audit",
            "task_id": "FC-DATA-007"
        }, source=["quality_job", "data_validation", "fc-data-007"])
        
        print(f"Data quality job completed successfully.")
        print(f"  Files checked: {audit_results['summary']['total_files_checked']}")
        print(f"  Files passed: {audit_results['summary']['files_passed']}")
        print(f"  Files failed: {audit_results['summary']['files_failed']}")
        print(f"  Overall quality: {audit_results['summary']['overall_quality_score']:.2f}%")
        print(f"  Degraded domains: {', '.join(audit_results['summary']['degraded_domains'])}")
        
        return audit_results
        
    except Exception as e:
        print(f"Error in data quality job: {str(e)}")
        
        # Create fallback results to maintain never-empty contract
        fallback_results = {
            "audit_results": {
                "summary": {
                    "total_files_checked": 0,
                    "files_passed": 0,
                    "files_failed": 0,
                    "overall_quality_score": 0.0,
                    "degraded_domains": [],
                    "checked_at": datetime.utcnow().isoformat() + "Z"
                },
                "checks": {},
                "degraded_flag": True
            },
            "job_execution_time": datetime.utcnow().isoformat() + "Z",
            "job_type": "data_quality_audit_fallback",
            "task_id": "FC-DATA-007",
            "error": str(e),
            "message": "Data quality job failed, but fallback report generated to maintain never-empty contract"
        }
        
        # Save fallback results to ensure endpoint has data to serve
        save_json("quality_report", fallback_results, source=["quality_job", "error_fallback", "fc-data-007"])
        
        return fallback_results


def validate_single_dataset(dataset_name: str, data: dict):
    """
    Validate a single dataset and apply quality gate
    """
    print(f"Validating {dataset_name} dataset...")
    
    # Run quality gate check
    passes, quality_report = run_quality_gate(data, dataset_name)
    
    if passes:
        print(f"✓ {dataset_name} passed quality checks")
        return True, quality_report
    else:
        print(f"✗ {dataset_name} failed quality checks - applying fallback")
        return False, quality_report


if __name__ == "__main__":
    print("="*60)
    print("DATA QUALITY VALIDATION JOB")
    print("Task: FC-DATA-007 - Data quality checks (gate)")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*60)
    
    result = run_data_quality_job()
    
    print("="*60)
    print("DATA QUALITY JOB COMPLETED")
    if 'audit_results' in result:
        print(f"Status: {'SUCCESS' if result['audit_results']['summary']['overall_quality_score'] > 0 else 'FALLBACK'}")
        print(f"Generated: {result['job_execution_time']}")
    else:
        print("Status: ERROR")
        print(f"Generated: {result.get('job_execution_time', datetime.now().isoformat())}")
    print("="*60)