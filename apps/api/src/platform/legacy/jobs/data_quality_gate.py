"""
Quality Gate Job - Runs quality checks on data files and ensures never-empty contract
Task: FC-DATA-007
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict

# Add backend to path for imports
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up 2 levels to backend/
sys.path.insert(0, backend_root)

from core.data_quality import run_quality_audit, run_quality_gate
from storage.io import save_json
try:
    from storage.io import load_json
except Exception:  # pragma: no cover
    from storage.base import load_json  # type: ignore


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _unwrap_storage_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _load_provider_gap_warnings() -> Dict[str, Any]:
    warnings: Dict[str, Any] = {}

    news_stats = _unwrap_storage_payload(load_json("provider_fallback_news") or {})
    macro_stats_payload = _unwrap_storage_payload(load_json("provider_fallback_macro") or {})
    macro_stats = macro_stats_payload.get("macro") if isinstance(macro_stats_payload, dict) else {}
    if not isinstance(macro_stats, dict):
        macro_stats = {}

    yahoo_empty_total = int(news_stats.get("yahoo_empty_events_total") or 0)
    yahoo_empty_by_ticker = news_stats.get("yahoo_empty_by_ticker")
    if not isinstance(yahoo_empty_by_ticker, dict):
        yahoo_empty_by_ticker = {}

    macro_attempted_total = int(macro_stats.get("fred_empty_fallback_attempted_total") or 0)
    macro_recovered_total = int(macro_stats.get("fred_empty_fallback_recovered_total") or 0)
    macro_failed_total = int(macro_stats.get("fred_empty_fallback_failed_total") or 0)
    macro_by_series = macro_stats.get("fred_empty_fallback_by_series")
    if not isinstance(macro_by_series, dict):
        macro_by_series = {}

    provider_gaps = {
        "news": {
            "yahoo_empty_events_total": yahoo_empty_total,
            "yahoo_empty_by_ticker": yahoo_empty_by_ticker,
        },
        "macro": {
            "fred_empty_fallback_attempted_total": macro_attempted_total,
            "fred_empty_fallback_recovered_total": macro_recovered_total,
            "fred_empty_fallback_failed_total": macro_failed_total,
            "fred_empty_fallback_by_series": macro_by_series,
        },
    }
    provider_gaps["has_non_blocking_warnings"] = bool(
        yahoo_empty_total > 0 or macro_attempted_total > 0
    )
    warnings["provider_gaps"] = provider_gaps
    return warnings


def run_data_quality_job():
    """
    Run the comprehensive data quality job to validate all data files
    """
    print("Starting data quality validation job...")
    print("Task: FC-DATA-007 - Data quality checks (gate)")
    
    try:
        # Run comprehensive audit
        audit_results = run_quality_audit()
        
        warnings = _load_provider_gap_warnings()
        provider_gaps = warnings.get("provider_gaps") if isinstance(warnings, dict) else {}
        if not isinstance(provider_gaps, dict):
            provider_gaps = {}

        # Save results to persistent storage
        result_payload = {
            "audit_results": audit_results,
            "job_execution_time": _utc_now_iso(),
            "job_type": "data_quality_audit",
            "task_id": "FC-DATA-007",
            # Provider fallbacks are informational (non-blocking) when recovered.
            "warnings": warnings,
            "non_blocking_warnings": bool(provider_gaps.get("has_non_blocking_warnings")),
            "degraded_flag": bool((audit_results or {}).get("degraded_flag", False)),
        }
        save_json("quality_report", result_payload, source=["quality_job", "data_validation", "fc-data-007"])
        
        print(f"Data quality job completed successfully.")
        print(f"  Files checked: {audit_results['summary']['total_files_checked']}")
        print(f"  Files passed: {audit_results['summary']['files_passed']}")
        print(f"  Files failed: {audit_results['summary']['files_failed']}")
        print(f"  Overall quality: {audit_results['summary']['overall_quality_score']:.2f}%")
        print(f"  Degraded domains: {', '.join(audit_results['summary']['degraded_domains'])}")
        if provider_gaps.get("has_non_blocking_warnings"):
            print("  Provider gap warnings: present (non-blocking)")
        
        return result_payload
        
    except Exception as e:
        print(f"Error in data quality job: {str(e)}")
        
        # Create fallback results to maintain never-empty contract
        fallback_warnings = _load_provider_gap_warnings()
        fallback_results = {
            "audit_results": {
                "summary": {
                    "total_files_checked": 0,
                    "files_passed": 0,
                    "files_failed": 0,
                    "overall_quality_score": 0.0,
                    "degraded_domains": [],
                    "checked_at": _utc_now_iso()
                },
                "checks": {},
                "degraded_flag": True
            },
            "job_execution_time": _utc_now_iso(),
            "job_type": "data_quality_audit_fallback",
            "task_id": "FC-DATA-007",
            "warnings": fallback_warnings,
            "non_blocking_warnings": bool(
                (fallback_warnings.get("provider_gaps") or {}).get("has_non_blocking_warnings")
            ),
            "degraded_flag": True,
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
