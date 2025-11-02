#!/usr/bin/env python3
"""
Smoke test to verify that the Finance Copilot API can start without errors.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_api_startup():
    """Test that the API can be imported and started without errors."""
    try:
        print("🔍 Testing API startup...")
        
        # Try to import the main API module
        from api.main import create_app
        print("✅ API main module imported successfully")
        
        # Try to create the app
        app = create_app()
        print("✅ FastAPI app created successfully")
        
        # Try to get the routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        print(f"✅ Found {len(routes)} API routes")
        
        # Check for critical routes
        critical_routes = [
            '/api/health',
            '/api/brief/weekly',
            '/api/brief/daily',
            '/api/copilot/ask',
            '/api/dashboard/kpis'
        ]
        
        found_routes = [route for route in critical_routes if route in routes]
        missing_routes = [route for route in critical_routes if route not in routes]
        
        print(f"✅ Found {len(found_routes)} critical routes: {found_routes}")
        if missing_routes:
            print(f"⚠️  Missing {len(missing_routes)} critical routes: {missing_routes}")
        
        # Test data access imports
        try:
            from core.data_access import get_close_series, load_macro_forecast_rows, load_news_features
            print("✅ Core data access imports successful")
        except ImportError as e:
            print(f"❌ Core data access import failed: {e}")
            return False
            
        # Test scoring imports
        try:
            from research.scoring import calculate_composite_score, compute_composite_brief
            print("✅ Research scoring imports successful")
        except ImportError as e:
            print(f"❌ Research scoring import failed: {e}")
            return False
            
        # Test RAG store imports
        try:
            from research.rag_store import RAGStore
            print("✅ RAG store imports successful")
        except ImportError as e:
            print(f"❌ RAG store import failed: {e}")
            return False
            
        # Test LLM client imports
        try:
            from research.llm_client import ask_llm
            print("✅ LLM client imports successful")
        except ImportError as e:
            print(f"❌ LLM client import failed: {e}")
            return False
            
        print("\n🎉 API smoke test PASSED!")
        print("   You can now start the API with: python run_api.py")
        return True
        
    except Exception as e:
        print(f"❌ API startup test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_startup()
    sys.exit(0 if success else 1)