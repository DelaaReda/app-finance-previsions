#!/usr/bin/env python3
"""
Validate and Generate All Required Data Files
Ensures all necessary data is present for the dashboard and API endpoints
Includes LLM Judge data generation for non-empty pages
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Max age before forecasts are considered stale (hours)
FORECASTS_MAX_AGE_HOURS = int(os.getenv("FORECASTS_MAX_AGE_HOURS", "24") or "24")

# Add backend to path
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

# Suppress verbose G4F warnings
logging.getLogger('g4f').setLevel(logging.ERROR)

try:
    from core.sentry_runtime import install_global_excepthook, init_sentry, set_job_context, capture_exception
except Exception:  # pragma: no cover
    def install_global_excepthook(job_name: str) -> bool:
        return False

    def init_sentry(component: str) -> bool:
        return False

    def set_job_context(job_name: str, **context: Any) -> None:
        return None

    def capture_exception(exc: BaseException, *, job_name: str | None = None, context: Dict[str, Any] | None = None) -> None:
        return None

def check_data_file(file_key: str, min_items: int = 1) -> tuple:
    """Check if a data file exists and has minimum required items"""
    try:
        from storage.io import load_json
        data = load_json(file_key)
        
        if not data:
            return False, None
        
        # Check for different data structures
        rows = data.get('rows', [])
        nested_data = data.get('data', {}) if isinstance(data.get('data'), dict) else {}
        if not rows:
            rows = nested_data.get('rows', [])
        if not rows:
            rows = data.get('articles', [])
        if not rows:
            rows = nested_data.get('articles', [])
        if not rows:
            rows = data.get('series', [])
        if not rows:
            rows = nested_data.get('series', [])
        if not rows:
            rows = data.get('signals', [])
        if not rows:
            rows = nested_data.get('signals', [])
        if not rows:
            rows = data.get('risks', [])
        if not rows:
            rows = nested_data.get('risks', [])
        
        # If tickers dict exists (prices cache)
        if not rows and isinstance(data.get("tickers"), dict):
            rows = list(data.get("tickers", {}).values())

        # If data is a list directly
        if isinstance(data, list):
            rows = data
        
        has_enough = len(rows) >= min_items
        return has_enough, data
    except Exception as e:
        logger.debug(f"Error checking {file_key}: {e}")
        return False, None


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        s = str(ts).strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _is_stale(data: Dict[str, Any], max_age_hours: int) -> bool:
    if not isinstance(data, dict):
        return True
    ts = data.get("freshness") or data.get("generated_at") or data.get("saved_at")
    dt = _parse_iso(ts)
    if not dt:
        return True
    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    return age_hours > max(1, int(max_age_hours))

def generate_forecasts() -> bool:
    """Generate forecasts data"""
    try:
        try:
            from jobs.forecasts import run_forecasts_job  # type: ignore
        except ImportError:
            from jobs.forecasts_simple import run_forecasts_job  # type: ignore
        tickers = ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META"]
        result = run_forecasts_job(tickers)
        if result and result.get('status') == 'completed':
            count = result.get('forecast_count', 0)
            logger.info(f"✅ Generated {count} forecasts")
            return count > 0
        return False
    except Exception as e:
        logger.error(f"❌ Failed to generate forecasts: {e}")
        return False

def generate_news() -> bool:
    """Generate news feed data"""
    try:
        from jobs.news_ingest import run_news_ingest
        result = run_news_ingest()
        if result:
            count = result.get('article_count', result.get('count', 0))
            logger.info(f"✅ Generated {count} news articles")
            return count > 0
        return False
    except Exception as e:
        logger.error(f"❌ Failed to generate news: {e}")
        return False

def generate_macro() -> bool:
    """Generate macro series data"""
    try:
        # Run macro snapshot job
        import subprocess
        script_path = backend_root / "jobs" / "macro_series_snapshot.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                logger.info("✅ Generated macro series data")
                return True
            else:
                logger.warning(f"⚠️  Macro job returned code {result.returncode}")
                return False
        return False
    except Exception as e:
        logger.error(f"❌ Failed to generate macro: {e}")
        return False

def generate_market_intelligence() -> bool:
    """Generate market intelligence snapshot"""
    try:
        import subprocess
        script_path = backend_root / "jobs" / "market_intelligence_snapshot.py"
        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                logger.info("✅ Generated market intelligence data")
                return True
        return False
    except Exception as e:
        logger.debug(f"Market intelligence generation not available: {e}")
        return False

def generate_prices() -> bool:
    """Generate cached stock prices for evaluation"""
    try:
        from jobs.stocks_prices_refresh import run_stocks_prices_job
        result = run_stocks_prices_job(force=True, timeframe="1y")
        status = (result or {}).get("status")
        return status in {"completed", "cached"}
    except Exception as e:
        logger.error(f"❌ Failed to generate prices: {e}")
        return False

def generate_brief() -> bool:
    """Generate market brief data"""
    try:
        from jobs.market_brief import run_market_brief_job
        result = run_market_brief_job()
        if result:
            logger.info("✅ Generated market brief")
            return True
        return False
    except Exception as e:
        logger.debug(f"Market brief generation not available: {e}")
        return False

def generate_judge_quality() -> bool:
    """Generate judge quality report snapshot"""
    try:
        from jobs.judge_quality_report import run_judge_quality_report
        report = run_judge_quality_report(horizon_days=5, min_samples=20)
        return bool(report)
    except Exception as e:
        logger.error(f"❌ Failed to generate judge quality report: {e}")
        return False

def generate_llm_judge_data() -> bool:
    """Generate LLM Judge data for non-empty pages"""
    try:
        # Try to call the LLM judge endpoint internally
        from storage.io import load_json, save_json
        
        # First check if we have forecasts to judge
        forecasts = load_json("forecasts")
        if not forecasts or not forecasts.get('rows', []):
            logger.warning("⚠️  No forecasts available for LLM Judge, skipping")
            return False
        
        # Create a simple judge result based on forecasts
        forecast_rows = forecasts.get('rows', [])
        
        # Generate judge data structure
        judge_data = {
            "ok": True,
            "rows": [],
            "derived": {
                "stats": {
                    "total": len(forecast_rows),
                    "ups": sum(1 for f in forecast_rows if f.get('direction') == 'up'),
                    "downs": sum(1 for f in forecast_rows if f.get('direction') == 'down'),
                    "flats": sum(1 for f in forecast_rows if f.get('direction') == 'flat'),
                    "avg_confidence": sum(f.get('confidence', 0) for f in forecast_rows) / len(forecast_rows) if forecast_rows else 0,
                    "avg_expected_return": sum(f.get('expected_return', 0) for f in forecast_rows) / len(forecast_rows) if forecast_rows else 0,
                }
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "model_used": "default",
            "source": "forecasts_derived"
        }
        
        # Add top picks based on confidence and expected return
        sorted_forecasts = sorted(
            forecast_rows,
            key=lambda x: (x.get('confidence', 0) * x.get('expected_return', 0)),
            reverse=True
        )
        
        for forecast in sorted_forecasts[:10]:  # Top 10
            judge_data["rows"].append({
                "ticker": forecast.get('ticker'),
                "direction": forecast.get('direction'),
                "confidence": forecast.get('confidence', 0),
                "expected_return": forecast.get('expected_return', 0),
                "horizon": forecast.get('horizon', '1d'),
                "reasoning": f"ML model predicts {forecast.get('direction', 'neutral')} with {forecast.get('confidence', 0):.0%} confidence",
                "risk_level": "low" if forecast.get('confidence', 0) > 0.7 else "medium" if forecast.get('confidence', 0) > 0.5 else "high"
            })
        
        # Save judge data
        save_json("llm_judge", judge_data, source=["job:validate_and_generate_data", "llm_judge"])
        logger.info(f"✅ Generated LLM Judge data with {len(judge_data['rows'])} rows")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to generate LLM Judge data: {e}")
        return False

def validate_and_generate_all() -> Dict[str, Any]:
    """Validate all required data files and generate missing ones"""
    logger.info("🔍 Validating all required data files...")
    init_sentry("validate_and_generate_data")
    
    # Required data files with minimum items
    required_files = {
        "forecasts": {"min_items": 1, "generator": generate_forecasts},
        "news_feed": {"min_items": 1, "generator": generate_news},
        "macro_series": {"min_items": 1, "generator": generate_macro},
    }
    
    # Optional but recommended files
    optional_files = {
        "market_intelligence": {"min_items": 0, "generator": generate_market_intelligence},
        "brief_weekly": {"min_items": 0, "generator": generate_brief},
        "brief_daily": {"min_items": 0, "generator": generate_brief},
        "llm_judge": {"min_items": 0, "generator": generate_llm_judge_data},
        "stocks/prices": {"min_items": 1, "generator": generate_prices},
        "judge_quality": {"min_items": 0, "generator": generate_judge_quality},
        # Ensure KPIs aren’t empty: persist minimal backtests snapshot
        "backtests": {"min_items": 0, "generator": lambda: __import__('jobs.backtests_simple', fromlist=['run_backtests_simple']).run_backtests_simple()},
    }
    
    results = {
        "validated": {},
        "generated": {},
        "stale": [],
        "missing": [],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    set_job_context(
        "validate_and_generate_data",
        required_count=len(required_files),
        optional_count=len(optional_files),
        forecasts_max_age_hours=FORECASTS_MAX_AGE_HOURS,
    )
    
    # Check required files
    for file_key, config in required_files.items():
        exists, data = check_data_file(file_key, config["min_items"])
        if file_key == "forecasts" and exists and _is_stale(data or {}, FORECASTS_MAX_AGE_HOURS):
            logger.warning(f"⚠️  {file_key} is stale (> {FORECASTS_MAX_AGE_HOURS}h), regenerating...")
            results["stale"].append(file_key)
            exists = False

        results["validated"][file_key] = exists
        
        if not exists:
            logger.warning(f"⚠️  {file_key} is missing or empty, generating...")
            generated = config["generator"]()
            results["generated"][file_key] = generated
            if not generated:
                results["missing"].append(file_key)
        else:
            logger.info(f"✅ {file_key} exists and is valid")
            results["generated"][file_key] = False  # Already exists
    
    # Check optional files
    for file_key, config in optional_files.items():
        exists, data = check_data_file(file_key, config["min_items"])
        results["validated"][file_key] = exists
        
        if not exists:
            logger.info(f"ℹ️  {file_key} is missing, generating (optional)...")
            generated = config["generator"]()
            results["generated"][file_key] = generated
        else:
            logger.info(f"✅ {file_key} exists")
            results["generated"][file_key] = False
    
    return results

def main():
    """Main entry point"""
    print("🚀 Validating and generating all required data files...")
    print(f"📂 Backend root: {backend_root}")
    print(f"⏰ Started at: {datetime.now().isoformat()}\n")
    init_sentry("validate_and_generate_data")
    try:
        results = validate_and_generate_all()
    except Exception as exc:
        capture_exception(exc, job_name="validate_and_generate_data", context={"stage": "main"})
        raise
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 SUMMARY")
    print(f"{'='*60}")
    
    validated_count = sum(1 for v in results["validated"].values() if v)
    total_required = len([k for k in results["validated"].keys() if k in ["forecasts", "news_feed", "macro_series"]])
    generated_count = sum(1 for v in results["generated"].values() if v)
    missing_count = len(results["missing"])
    
    print(f"✅ Validated: {validated_count}/{total_required} required files")
    print(f"🔄 Generated: {generated_count} new files")
    if missing_count > 0:
        print(f"❌ Missing: {missing_count} files could not be generated")
        print(f"   Files: {', '.join(results['missing'])}")
    
    if missing_count == 0:
        print("\n🎉 All required data files are present!")
        return 0
    else:
        print(f"\n⚠️  {missing_count} required file(s) are still missing")
        return 1

if __name__ == "__main__":
    install_global_excepthook("validate_and_generate_data")
    sys.exit(main())
