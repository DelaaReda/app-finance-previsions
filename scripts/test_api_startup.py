#!/usr/bin/env python3
"""
Simple test to verify API can start without import errors
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_api_imports():
    """Test that all API modules can be imported without errors."""
    try:
        # Test main API import
        from api.main import create_app
        print("✅ api.main import successful")
        
        # Test data access imports
        from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
        print("✅ core.data_access imports successful")
        
        # Test market data imports
        from core.market_data import get_price_history, get_fundamentals, get_fred_series
        print("✅ core.market_data imports successful")
        
        # Test analytics imports
        from analytics.phase2_technical import compute_indicators, technical_signals
        from analytics.phase3_macro import get_us_macro_bundle, macro_nowcast
        print("✅ analytics imports successful")
        
        # Test research imports
        from research.scoring import calculate_composite_score, compute_composite_brief
        from research.rag_store import RAGStore
        from research.llm_client import ask_llm
        print("✅ research imports successful")
        
        # Test ingestion imports
        from ingestion.finnews import run_pipeline
        print("✅ ingestion imports successful")
        
        # Test API creation
        app = create_app()
        print("✅ API app creation successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints are properly defined."""
    try:
        from api.main import create_app
        app = create_app()
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        # Check for critical endpoints
        critical_endpoints = [
            '/api/health',
            '/api/brief/weekly',
            '/api/brief/daily',
            '/api/copilot/ask',
            '/api/rag/stats'
        ]
        
        found_endpoints = []
        missing_endpoints = []
        
        for endpoint in critical_endpoints:
            if endpoint in routes:
                found_endpoints.append(endpoint)
            else:
                missing_endpoints.append(endpoint)
        
        print(f"✅ Found {len(found_endpoints)} critical endpoints: {found_endpoints}")
        if missing_endpoints:
            print(f"⚠️  Missing {len(missing_endpoints)} critical endpoints: {missing_endpoints}")
        
        return len(missing_endpoints) == 0
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing API imports and endpoints...")
    print("=" * 50)
    
    imports_ok = test_api_imports()
    endpoints_ok = test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    if imports_ok:
        print("✅ All imports successful")
    else:
        print("❌ Some imports failed")
    
    if endpoints_ok:
        print("✅ All critical endpoints found")
    else:
        print("❌ Some critical endpoints missing")
    
    if imports_ok and endpoints_ok:
        print("\n🎉 API is ready to start!")
        sys.exit(0)
    else:
        print("\n⚠️  API needs fixes before starting")
        sys.exit(1)