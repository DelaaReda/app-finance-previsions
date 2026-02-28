"""
Quality Monitor - Core module for system quality checks

Implements the FC-QM-MONITOR task to create a comprehensive quality monitoring system
that verifies data freshness, availability, and integrity across all endpoints.
"""
import asyncio
import time
import requests
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class QualityMonitor:
    """Monitors data quality across all endpoints and systems."""
    
    def __init__(self, base_url: str = "http://localhost:8050"):
        self.base_url = base_url
        self.endpoints_to_check = [
            "/api/health",
            "/api/news/feed", 
            "/api/forecasts",
            "/api/brief/daily",
            "/api/brief/weekly",
            "/api/backtests",
            "/api/macro/series",
            "/api/stocks/prices"
        ]
        
    def check_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Check a single endpoint for never-empty compliance and data quality."""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=15)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "freshness": None,
                "data_valid": False,
                "is_empty": True,
                "has_proper_structure": False,
                "last_update": None,
                "source": [],
                "error": None
            }
            
            if response.status_code != 200:
                result["error"] = f"HTTP {response.status_code}"
                return result
            
            try:
                data = response.json()
                
                # Check for proper structure {ok: bool, data: {...}}
                if "ok" in data and "data" in data:
                    result["has_proper_structure"] = True
                    
                    # Check if data follows never-empty patterns
                    if self._check_never_empty_compliance(data, endpoint):
                        result["data_valid"] = True
                        result["is_empty"] = False
                        result["freshness"] = self._extract_freshness(data)
                        result["last_update"] = self._extract_timestamp(data)
                        result["source"] = self._extract_source(data)
                    else:
                        result["error"] = "Data structure violates never-empty pattern"
                        
                else:
                    result["error"] = "Response missing required structure {ok, data}"
                    
            except json.JSONDecodeError:
                result["error"] = "Invalid JSON response"
            
            return result
                
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "endpoint": endpoint,
                "status_code": None,
                "duration_ms": duration_ms,
                "freshness": None,
                "data_valid": False,
                "is_empty": True,
                "has_proper_structure": False,
                "last_update": None,
                "source": [],
                "error": str(e)
            }
    
    def _check_never_empty_compliance(self, data: Dict[str, Any], endpoint: str) -> bool:
        """Check if data follows never-empty pattern."""
        if 'data' not in data:
            return False
            
        data_payload = data['data']
        
        # For endpoints that return collections, ensure they're never None (can be empty [])
        if endpoint in ['/api/news/feed', '/api/forecasts', '/api/brief/daily', '/api/brief/weekly', '/api/backtests']:
            if isinstance(data_payload, dict):
                # Check common collection fields
                for field in ['articles', 'rows', 'items', 'results', 'signals', 'risks', 'picks']:
                    if field in data_payload:
                        field_value = data_payload[field]
                        # Ensure collections are never None - they can be [] but not None
                        if field_value is None:
                            return False
                        # If it's a nested dict with a 'rows' field, check that too
                        if isinstance(field_value, dict) and 'rows' in field_value:
                            if field_value['rows'] is None:
                                return False
                            
        return True
    
    def _extract_freshness(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract freshness indicator from response."""
        if 'data' in data and isinstance(data['data'], dict):
            # Look for common freshness fields
            for field in ['freshness', 'freshness_status', 'stale', 'fresh']:
                if field in data['data']:
                    return str(data['data'][field])
            # Look for last_update
            for field in ['last_update', 'last_updated', 'lastUpdate', 'timestamp']:
                if field in data['data']:
                    return str(data['data'][field])
        
        # Check top level too
        for field in ['freshness', 'last_update', 'timestamp']:
            if field in data:
                return str(data[field])
                
        return None
    
    def _extract_timestamp(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract timestamp from response."""
        if 'data' in data and isinstance(data['data'], dict):
            for field in ['timestamp', 'last_update', 'last_updated', 'generated_at', 'last_generated']:
                if field in data['data']:
                    return str(data['data'][field])
        
        return None
    
    def _extract_source(self, data: Dict[str, Any]) -> List[str]:
        """Extract source information from response."""
        sources = []
        if 'data' in data and isinstance(data['data'], dict):
            for field in ['source', 'sources', 'src', 'origin', 'provider']:
                if field in data['data']:
                    field_val = data['data'][field]
                    if isinstance(field_val, list):
                        sources.extend(field_val)
                    elif isinstance(field_val, str):
                        sources.append(field_val)
        
        return sources
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run comprehensive quality checks on all endpoints."""
        results = {
            "checks": [],
            "summary": {
                "total": 0,
                "valid": 0,
                "invalid": 0,
                "empty": 0,
                "malformed": 0,
                "overall_status": "GREEN",  # GREEN, YELLOW, RED
                "timestamp": datetime.utcnow().isoformat(),
                "quality_score": 0.0
            },
            "statistics": {
                "avg_response_time": 0,
                "max_response_time": 0,
                "slow_endpoints": []
            }
        }
        
        all_responses = []
        total_duration = 0
        
        for endpoint in self.endpoints_to_check:
            check_result = self.check_endpoint(endpoint)
            results["checks"].append(check_result)
            all_responses.append(check_result)
            
            if check_result["duration_ms"] > total_duration:
                total_duration = check_result["duration_ms"]
        
        # Calculate summary statistics
        results["summary"]["total"] = len(self.endpoints_to_check)
        results["summary"]["valid"] = sum(1 for check in results["checks"] 
                                        if check["has_proper_structure"] and check["data_valid"])
        results["summary"]["invalid"] = sum(1 for check in results["checks"] 
                                          if not check["has_proper_structure"])
        results["summary"]["malformed"] = sum(1 for check in results["checks"] 
                                            if check["error"] is not None and "structure" in str(check["error"]).lower())
        results["summary"]["empty"] = sum(1 for check in results["checks"] 
                                        if check["is_empty"] and check["data_valid"] == False)
        
        # Calculate response time statistics
        durations = [check["duration_ms"] for check in results["checks"] if check["duration_ms"] is not None]
        if durations:
            results["statistics"]["avg_response_time"] = round(sum(durations) / len(durations), 2)
            results["statistics"]["max_response_time"] = max(durations)
            results["statistics"]["slow_endpoints"] = [
                check["endpoint"] for check in results["checks"] 
                if check["duration_ms"] and check["duration_ms"] > 1000  # Slow if > 1s
            ]
        
        # Calculate quality score (0-100)
        if results["summary"]["total"] > 0:
            score = (results["summary"]["valid"] / results["summary"]["total"]) * 100
            results["summary"]["quality_score"] = round(score, 2)
        
        # Determine overall status
        if results["summary"]["invalid"] > 0 or results["summary"]["malformed"] > 0:
            results["summary"]["overall_status"] = "RED"
        elif results["summary"]["empty"] > 0 or results["summary"]["quality_score"] < 75:
            results["summary"]["overall_status"] = "YELLOW"
        else:
            results["summary"]["overall_status"] = "GREEN"
            
        return results
    
    def save_quality_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save quality report to file with proper metadata."""
        if filename is None:
            filename = f"quality_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
        reports_dir = Path("data/quality/reports") 
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = reports_dir / filename
        
        # Add metadata to the report
        report_with_meta = {
            "report_metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "generator": "QualityMonitor",
                "version": "1.0.0",
                "type": "quality_assessment"
            },
            "quality_results": results
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_with_meta, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Quality report saved to {file_path}")
        return str(file_path)
    
    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Get the latest quality report."""
        reports_dir = Path("data/quality/reports")
        if not reports_dir.exists():
            return None
            
        report_files = list(reports_dir.glob("quality_report_*.json"))
        if not report_files:
            return None
            
        latest_file = max(report_files, key=lambda x: x.stat().st_mtime)
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)


def run_quality_check() -> Dict[str, Any]:
    """Run a single quality check and return results."""
    monitor = QualityMonitor()
    results = monitor.run_all_checks()
    
    # Save the report
    report_path = monitor.save_quality_report(results)
    results["report_saved_to"] = report_path
    
    return results


def get_system_health_status() -> Dict[str, Any]:
    """Get high-level health status for system monitoring."""
    results = run_quality_check()
    
    health = {
        "status": results["summary"]["overall_status"],
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "total_endpoints": results["summary"]["total"],
            "healthy_endpoints": results["summary"]["valid"],
            "quality_percentage": results["summary"]["quality_score"],
            "average_response_time_ms": results["statistics"]["avg_response_time"],
            "system_integrity": results["summary"]["overall_status"]
        },
        "details": {
            "valid_endpoints": [check["endpoint"] for check in results["checks"] if check["data_valid"]],
            "problematic_endpoints": [check["endpoint"] for check in results["checks"] if not check["data_valid"]]
        }
    }
    
    return health


if __name__ == "__main__":
    print("Running quality checks...")
    results = run_quality_check()
    print(f"Quality check completed. Overall status: {results['summary']['overall_status']}")
    print(f"Quality score: {results['summary']['quality_score']}/100")
    print(f"Passed: {results['summary']['valid']}/{results['summary']['total']}")
    print(f"Report saved to: {results['report_saved_to']}")