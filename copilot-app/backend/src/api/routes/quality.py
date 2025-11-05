"""
Quality API Routes - Implements /api/quality endpoints per FC-QM-MONITOR task
"""
from fastapi import APIRouter
from typing import Dict, Any, Optional
from ..services.quality_service import quality_service

router = APIRouter()

@router.get("/api/quality/checks")
async def quality_checks() -> Dict[str, Any]:
    """
    Get real-time quality metrics for the system.
    
    Returns quality assessments of data freshness, never-empty compliance,
    and endpoint availability.
    """
    try:
        health = await quality_service.get_system_health()
        return health
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "data": None,
            "freshness": None,
            "source": ["quality_monitor_error"],
            "last_update": None
        }


@router.get("/api/quality/endpoint/{endpoint:path}")
async def quality_endpoint_check(endpoint: str) -> Dict[str, Any]:
    """
    Get quality metrics for a specific endpoint.
    
    Path parameter 'endpoint' should be the endpoint path without /api prefix.
    For example: 'forecasts', 'news/feed', 'brief/weekly'
    """
    try:
        # Reconstruct full path
        full_endpoint = f"/api/{endpoint}"
        quality_data = await quality_service.get_endpoint_quality(full_endpoint)
        
        return {
            "ok": True,
            "data": quality_data,
            "freshness": quality_data.get("freshness") or quality_data.get("timestamp") or None,
            "source": ["quality_monitor"],
            "last_update": quality_data.get("timestamp") or quality_data.get("last_update") or None
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to check quality for endpoint {endpoint}: {str(e)}",
            "data": None,
            "freshness": None,
            "source": ["quality_monitor_error"],
            "last_update": None
        }


@router.get("/api/quality/latest-report")
async def quality_latest_report() -> Dict[str, Any]:
    """
    Get the latest saved quality report.
    """
    try:
        latest_report = quality_service.get_latest_report()
        
        if latest_report:
            return {
                "ok": True,
                "data": latest_report,
                "freshness": latest_report.get("report_metadata", {}).get("created_at"),
                "source": ["quality_monitor", "saved_report"],
                "last_update": latest_report.get("report_metadata", {}).get("created_at")
            }
        else:
            return {
                "ok": True,
                "data": {
                    "message": "No quality reports found",
                    "hint": "Run a quality check first to generate reports"
                },
                "freshness": None,
                "source": ["quality_monitor"],
                "last_update": None
            }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "data": None,
            "freshness": None,
            "source": ["quality_monitor_error"],
            "last_update": None
        }


@router.get("/api/quality/compliance/{endpoint:path}")
async def quality_compliance_check(endpoint: str) -> Dict[str, Any]:
    """
    Get compliance status for a specific endpoint regarding quality standards (never-empty, structure, etc.)
    """
    try:
        # Reconstruct full path
        full_endpoint = f"/api/{endpoint}"
        compliance_status = await quality_service.get_endpoint_compliance_status(full_endpoint)
        
        return compliance_status
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to check compliance for endpoint {endpoint}: {str(e)}",
            "data": None,
            "freshness": None,
            "source": ["quality_monitor_error"],
            "last_update": None
        }


@router.post("/api/quality/run-check")
async def quality_run_check() -> Dict[str, Any]:
    """
    Trigger a new quality check and return results.
    """
    try:
        checks = await quality_service.run_comprehensive_check()
        
        return {
            "ok": True,
            "data": {
                "checks": checks,
                "message": "Quality check completed and saved"
            },
            "freshness": checks["summary"]["timestamp"],
            "source": ["quality_monitor", "manual_trigger"],
            "last_update": checks["summary"]["timestamp"]
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "data": None,
            "freshness": None,
            "source": ["quality_monitor_error"],
            "last_update": None
        }