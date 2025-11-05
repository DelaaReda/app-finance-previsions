"""
Quality Service Layer - Implements quality metrics and validation services as per FC-QM-MONITOR
"""
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
from ..quality.monitor import QualityMonitor, run_quality_check, get_system_health_status


class QualityService:
    """Provides quality metrics and validation services."""
    
    def __init__(self):
        self.monitor = QualityMonitor()
    
    async def run_comprehensive_check(self) -> Dict[str, Any]:
        """Run comprehensive quality check."""
        loop = asyncio.get_event_loop()
        # Run the synchronous check in a thread pool
        result = await loop.run_in_executor(None, self.monitor.run_all_checks)
        return result
    
    async def get_endpoint_quality(self, endpoint: str) -> Dict[str, Any]:
        """Get quality metrics for a specific endpoint."""
        loop = asyncio.get_event_loop()
        # Run the synchronous check in a thread pool
        result = await loop.run_in_executor(None, self.monitor.check_endpoint, endpoint)
        return result
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system quality health."""
        loop = asyncio.get_event_loop()
        # Run the synchronous check in a thread pool
        result = await loop.run_in_executor(None, get_system_health_status)
        
        # Format the result to match our standard {ok, data} contract
        return {
            "ok": True,
            "data": result,
            "freshness": result["timestamp"],
            "source": ["quality_monitor"],
            "last_update": result["timestamp"]
        }
    
    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Retrieve the latest quality report."""
        return self.monitor.get_latest_report()

    async def get_endpoint_compliance_status(self, endpoint: str) -> Dict[str, Any]:
        """Get compliance status for a specific endpoint with never-empty and other quality standards."""
        quality_result = await self.get_endpoint_quality(endpoint)
        
        compliance_status = {
            "endpoint": endpoint,
            "compliant": quality_result.get("has_proper_structure", False) and quality_result.get("data_valid", False),
            "issues": [],
            "quality_metrics": {
                "has_correct_structure": quality_result.get("has_proper_structure", False),
                "never_empty_compliant": not quality_result.get("is_empty", True),
                "response_time_ms": quality_result.get("duration_ms"),
                "freshness": quality_result.get("freshness"),
                "data_integrity": quality_result.get("data_valid", False)
            }
        }
        
        # Identify non-compliance issues
        if not quality_result.get("has_proper_structure"):
            compliance_status["issues"].append("Missing {ok, data} structure")
        if quality_result.get("is_empty", True) and not quality_result.get("data_valid", False):
            compliance_status["issues"].append("Violates never-empty pattern")
        if quality_result.get("error"):
            compliance_status["issues"].append(f"Runtime error: {quality_result['error']}")
            
        return {
            "ok": True,
            "data": compliance_status,
            "freshness": datetime.utcnow().isoformat(),
            "source": ["quality_compliance_checker"],
            "last_update": datetime.utcnow().isoformat()
        }


# Singleton instance
quality_service = QualityService()