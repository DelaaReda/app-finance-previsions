"""
Quality Service - Provides quality metrics and health checks as per FC-QM-MONITOR task

Implements quality monitoring that checks for never-empty compliance, freshness, 
and data integrity across all endpoints.
"""
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
from ..quality.monitor import QualityMonitor


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
        checks = await self.run_comprehensive_check()
        
        # Extract key metrics
        health = {
            "status": checks["summary"]["overall_status"],
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_checks": checks["summary"]["total"],
                "passed_checks": checks["summary"]["passed"],
                "failed_checks": checks["summary"]["failed"],
                "success_rate": checks["summary"]["passed"] / checks["summary"]["total"] if checks["summary"]["total"] > 0 else 0
            },
            "checks": checks["checks"]
        }
        
        return health
    
    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Retrieve the latest quality report."""
        return self.monitor.get_latest_report()


# Singleton instance
quality_service = QualityService()