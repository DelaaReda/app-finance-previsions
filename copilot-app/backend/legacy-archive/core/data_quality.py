"""
Data Quality Checks System
Task: FC-DATA-007 - Data quality checks (gate)
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DataQualityValidator:
    """
    Data quality validator that checks schema, required fields, and null ratios
    """
    
    def __init__(self):
        self.quality_standards = {
            # Standards for different data domains
            "forecasts": {
                "required_fields": ["rows", "generated_at", "source", "count"],
                "required_nested_fields": {
                    "rows": ["ticker", "horizon", "direction", "confidence", "expected_return"]
                },
                "max_null_ratio": 0.1  # Max 10% null values
            },
            "news": {
                "required_fields": ["articles", "generated_at", "source", "count"],
                "required_nested_fields": {
                    "articles": ["title", "link", "pubDate", "source", "tickers"]
                },
                "max_null_ratio": 0.15  # Max 15% null values for news
            },
            "macro": {
                "required_fields": ["series", "generated_at", "source", "count"],
                "required_nested_fields": {
                    "series": ["id", "title", "data", "last_update"]
                },
                "max_null_ratio": 0.05  # Max 5% null values for macro
            },
            "stocks": {
                "required_fields": ["rows", "generated_at", "source", "count"],
                "required_nested_fields": {
                    "rows": ["ticker", "current_price", "change_percent", "volume"]
                },
                "max_null_ratio": 0.1  # Max 10% null values
            },
            "brief": {
                "required_fields": ["summary", "top_signals", "top_risks", "generated_at", "source"],
                "required_nested_fields": {
                    "top_signals": ["ticker", "score", "reason"],
                    "top_risks": ["ticker", "score", "reason"]
                },
                "max_null_ratio": 0.1  # Max 10% null values
            },
            "backtests": {
                "required_fields": ["results", "params", "generated_at", "source"],
                "required_nested_fields": {
                    "results": ["n_trades", "avg_return", "hit_rate"]
                },
                "max_null_ratio": 0.1  # Max 10% null values
            }
        }
    
    def check_schema_compliance(self, data: Dict[str, Any], data_type: str) -> Tuple[bool, List[str]]:
        """
        Check if data complies with expected schema for the data type
        """
        errors = []
        
        if not isinstance(data, dict):
            errors.append(f"Data should be a dictionary, got {type(data).__name__}")
            return False, errors
        
        if data_type not in self.quality_standards:
            errors.append(f"Unknown data type: {data_type}")
            return False, errors
        
        standard = self.quality_standards[data_type]
        
        # Check required top-level fields
        for field in standard["required_fields"]:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check required nested fields if they exist
        for container, fields in standard["required_nested_fields"].items():
            if container in data and isinstance(data.get(container), list):
                container_data = data[container]
                for i, item in enumerate(container_data):
                    if isinstance(item, dict):
                        for field in fields:
                            if field not in item or item[field] is None:
                                errors.append(f"Missing required nested field in {container}[{i}]: {field}")
        
        is_compliant = len(errors) == 0
        return is_compliant, errors
    
    def calculate_null_ratios(self, data: Dict[str, Any], data_type: str) -> Dict[str, float]:
        """
        Calculate null/invalid value ratios for important fields
        """
        null_ratios = {}
        
        if data_type not in self.quality_standards:
            return null_ratios
        
        standard = self.quality_standards[data_type]
        
        for container, fields in standard["required_nested_fields"].items():
            if container in data and isinstance(data[container], list):
                container_data = data[container]
                for field in fields:
                    values = [item.get(field) for item in container_data if isinstance(item, dict)]
                    total = len(values)
                    if total > 0:
                        null_count = sum(1 for v in values if v is None or (isinstance(v, str) and v in ['', 'nan', 'NaN', 'null', 'None']))
                        null_ratios[f"{container}.{field}"] = null_count / total if total > 0 else 0.0
        
        return null_ratios
    
    def validate_data_quality(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        Validate data quality and return comprehensive report
        """
        schema_ok, schema_errors = self.check_schema_compliance(data, data_type)
        null_ratios = self.calculate_null_ratios(data, data_type)
        
        # Check if any null ratio exceeds the threshold
        exceeded_thresholds = []
        max_null_ratio = self.quality_standards.get(data_type, {}).get("max_null_ratio", 0.1)
        
        for field, ratio in null_ratios.items():
            if ratio > max_null_ratio:
                exceeded_thresholds.append({
                    "field": field,
                    "ratio": ratio,
                    "threshold": max_null_ratio
                })
        
        quality_ok = schema_ok and len(exceeded_thresholds) == 0
        
        return {
            "quality_ok": quality_ok,
            "schema_check": {
                "ok": schema_ok,
                "errors": schema_errors
            },
            "null_ratios": null_ratios,
            "exceeded_thresholds": exceeded_thresholds,
            "schema_valid": schema_ok,
            "data_volume_sufficient": "count" in data and data.get("count", 0) > 0,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "validator_version": "1.0.0",
            "data_type": data_type
        }
    
    def validate_file(self, file_path: str, data_type: str) -> Dict[str, Any]:
        """
        Validate data from a file
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    "quality_ok": False,
                    "error": "File not found",
                    "details": f"File {file_path} does not exist",
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                    "data_type": data_type,
                    "validator_version": "1.0.0"
                }
            
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                
            # If the file contains wrapped data (with metadata), extract the payload
            if isinstance(raw_data, dict) and "data" in raw_data:
                payload = raw_data["data"]
            elif isinstance(raw_data, dict) and "payload" in raw_data:
                payload = raw_data["payload"]
            elif isinstance(raw_data, dict) and ("articles" in raw_data or "rows" in raw_data):
                # Direct data format (common for news/forecasts)
                payload = raw_data
            else:
                payload = raw_data
            
            return self.validate_data_quality(payload, data_type)
            
        except FileNotFoundError:
            return {
                "quality_ok": False,
                "error": "File not found",
                "details": f"File {file_path} does not exist",
                "checked_at": datetime.utcnow().isoformat() + "Z",
                "data_type": data_type,
                "validator_version": "1.0.0"
            }
        except json.JSONDecodeError as e:
            return {
                "quality_ok": False,
                "error": "JSON decode error",
                "details": str(e),
                "checked_at": datetime.utcnow().isoformat() + "Z",
                "data_type": data_type,
                "validator_version": "1.0.0"
            }
        except Exception as e:
            return {
                "quality_ok": False,
                "error": "Validation error",
                "details": str(e),
                "checked_at": datetime.utcnow().isoformat() + "Z",
                "data_type": data_type,
                "validator_version": "1.0.0"
            }


class QualityService:
    """
    Service to run quality checks across data files and generate reports
    """
    
    def __init__(self):
        self.validator = DataQualityValidator()
        self.data_dir = Path(__file__).resolve().parents[2] / "data"
    
    def run_comprehensive_quality_check(self) -> Dict[str, Any]:
        """
        Run quality checks across all data files
        """
        quality_report = {
            "summary": {
                "total_files_checked": 0,
                "files_passed": 0,
                "files_failed": 0,
                "overall_quality_score": 0.0,
                "degraded_domains": [],
                "checked_at": datetime.utcnow().isoformat() + "Z"
            },
            "checks": {},
            "degraded_flag": False
        }
        
        # Define the data files to check
        data_files = [
            ("forecasts.json", "forecasts"),
            ("news_feed.json", "news"),
            ("macro_series.json", "macro"),
            ("stock_prices.json", "stocks"),
            ("brief_weekly.json", "brief"),
            ("brief_daily.json", "brief"),
            ("backtests.json", "backtests")
        ]
        
        for filename, data_type in data_files:
            file_path = self.data_dir / filename
            
            if file_path.exists():
                check_result = self.validator.validate_file(str(file_path), data_type)
                quality_report["checks"][filename] = check_result
                quality_report["summary"]["total_files_checked"] += 1
                
                if check_result.get("quality_ok", False):
                    quality_report["summary"]["files_passed"] += 1
                else:
                    quality_report["summary"]["files_failed"] += 1
                    if data_type not in quality_report["summary"]["degraded_domains"]:
                        quality_report["summary"]["degraded_domains"].append(data_type)
                    quality_report["degraded_flag"] = True
            else:
                # File doesn't exist but we should still track it
                quality_report["checks"][filename] = {
                    "quality_ok": False,
                    "error": "File not found",
                    "details": f"File {filename} does not exist in data directory",
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                    "data_type": data_type,
                    "validator_version": "1.0.0"
                }
                quality_report["summary"]["total_files_checked"] += 1
                quality_report["summary"]["files_failed"] += 1
                if data_type not in quality_report["summary"]["degraded_domains"]:
                    quality_report["summary"]["degraded_domains"].append(data_type)
                quality_report["degraded_flag"] = True
        
        # Calculate overall quality score
        total = quality_report["summary"]["total_files_checked"]
        passed = quality_report["summary"]["files_passed"]
        quality_report["summary"]["overall_quality_score"] = (passed / total * 100) if total > 0 else 0.0
        
        return quality_report
    
    def run_quality_gate(self, data: Dict[str, Any], data_type: str, save_report: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        Run quality gate check - return True if data passes quality checks, False otherwise
        """
        quality_result = self.validator.validate_data_quality(data, data_type)
        
        if save_report:
            # Save the quality report to track history
            reports_dir = Path(__file__).resolve().parents[2] / "data" / "quality_reports"
            reports_dir.mkdir(exist_ok=True)
            
            report_filename = f"quality_report_{data_type}_{int(datetime.utcnow().timestamp())}.json"
            report_path = reports_dir / report_filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(quality_result, f, indent=2)
        
        return quality_result["quality_ok"], quality_result


# Global instance for quality validation
data_quality_validator = DataQualityValidator()
quality_service = QualityService()

# Convenience functions for external use
def validate_data(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """
    Validate data quality for a specific data type
    """
    return data_quality_validator.validate_data_quality(data, data_type)

def validate_file(file_path: str, data_type: str) -> Dict[str, Any]:
    """
    Validate data quality from a file path
    """
    return data_quality_validator.validate_file(file_path, data_type)

def run_quality_audit() -> Dict[str, Any]:
    """
    Run comprehensive quality audit across all data files
    """
    return quality_service.run_comprehensive_quality_check()

def run_quality_gate(data: Dict[str, Any], data_type: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Run quality gate - returns (pass, quality_report)
    """
    return quality_service.run_quality_gate(data, data_type)