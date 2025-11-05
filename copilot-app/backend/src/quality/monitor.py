"""
Quality Monitor System - Check freshness, availability and integrity of data

This module implements the FC-QM-MONITOR task to create a quality monitoring system
that verifies endpoints follow never-empty patterns and maintains data integrity.
"""
import asyncio
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
import os
from pathlib import Path

class QualityMonitor:
    """Monitors data quality across all endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8050"):
        self.base_url = base_url
        self.endpoints_to_check = [
            "/api/health",
            "/api/news/feed", 
            "/api/forecasts",
            "/api/brief/weekly",
            "/api/backtests"
        ]
        
    def check_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Check a single endpoint for never-empty compliance."""
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code != 200:
                return {
                    "endpoint": endpoint,
                    "status": "FAIL",
                    "code": response.status_code,
                    "message": f"HTTP {response.status_code}",
                    "duration_ms": duration_ms,
                    "freshness": None,
                    "data_valid": False
                }
            
            try:
                data = response.json()
                # Check never-empty compliance
                data_valid = self._check_never_empty_compliance(data, endpoint)
                
                # Extract freshness info if available
                freshness = self._extract_freshness(data)
                
                return {
                    "endpoint": endpoint,
                    "status": "OK",
                    "code": 200,
                    "message": "Success",
                    "duration_ms": duration_ms,
                    "freshness": freshness,
                    "data_valid": data_valid,
                    "error": None
                }
                
            except json.JSONDecodeError:
                return {
                    "endpoint": endpoint,
                    "status": "FAIL",
                    "code": 200,  # Still 200 but invalid JSON
                    "message": "Invalid JSON response",
                    "duration_ms": duration_ms,
                    "freshness": None,
                    "data_valid": False
                }
                
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "endpoint": endpoint,
                "status": "FAIL",
                "code": None,
                "message": str(e),
                "duration_ms": duration_ms,
                "freshness": None,
                "data_valid": False
            }
    
    def _check_never_empty_compliance(self, data: Dict[str, Any], endpoint: str) -> bool:
        """Check if data follows never-empty pattern."""
        # Check that response has required structure
        if 'ok' not in data:
            return False
            
        if 'data' not in data:
            return False
            
        # For endpoints that return lists, ensure they're not None (but can be empty [])
        if endpoint in ['/api/news/feed', '/api/forecasts', '/api/backtests']:
            if 'data' in data and isinstance(data['data'], dict):
                # Check common collection fields
                for field in ['articles', 'rows', 'results', 'items']:
                    if field in data['data']:
                        if data['data'][field] is None:
                            return False  # Never should be None, can be []
        
        return True
    
    def _extract_freshness(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract freshness timestamp from response."""
        if 'data' in data and isinstance(data['data'], dict):
            # Look for common freshness fields
            for field in ['last_update', 'freshness', 'timestamp', 'last_updated']:
                if field in data['data']:
                    return data['data'][field]
        
        return None
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run quality checks on all endpoints."""
        results = {
            "checks": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "overall_status": "GREEN",  # GREEN, YELLOW, RED
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        all_passed = True
        
        for endpoint in self.endpoints_to_check:
            check_result = self.check_endpoint(endpoint)
            results["checks"].append(check_result)
            
            if check_result["status"] == "FAIL" or not check_result["data_valid"]:
                all_passed = False
                
        results["summary"]["total"] = len(self.endpoints_to_check)
        results["summary"]["passed"] = sum(1 for check in results["checks"] 
                                         if check["status"] == "OK" and check["data_valid"])
        results["summary"]["failed"] = results["summary"]["total"] - results["summary"]["passed"]
        
        if results["summary"]["failed"] > 0:
            results["summary"]["overall_status"] = "RED"
        elif results["summary"]["passed"] < results["summary"]["total"]:
            results["summary"]["overall_status"] = "YELLOW"
        else:
            results["summary"]["overall_status"] = "GREEN"
            
        return results
    
    def save_quality_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save quality report to file."""
        if filename is None:
            filename = f"quality_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
        reports_dir = Path("data/quality/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = reports_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
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


if __name__ == "__main__":
    print("Running quality checks...")
    results = run_quality_check()
    print(f"Quality check completed. Overall status: {results['summary']['overall_status']}")
    print(f"Passed: {results['summary']['passed']}/{results['summary']['total']}")
    print(f"Report saved to: {results['report_saved_to']}")