"""
Test script for Recommendations Service

Tests the RecommendationsService class and its methods.

Author: ELENA-39
Task: FC-INT-023
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from services.recommendations_service import RecommendationsService


async def test_recommendations_service():
    """Test RecommendationsService"""
    
    print("=" * 60)
    print("Testing RecommendationsService")
    print("=" * 60)
    
    service = RecommendationsService()
    
    # Test 1: Service instantiation
    print("\n✅ Test 1: Service instantiation")
    print(f"   G4F available: {service.g4f_client is not None}")
    print(f"   Intelligence service: {service.intelligence_service is not None}")
    print(f"   Context service: {service.context_service is not None}")
    
    # Test 2: Default recommendations
    print("\n🧪 Test 2: Generate default recommendations")
    try:
        recs = await service.generate_daily_recommendations()
        
        print(f"✅ Default recommendations generated")
        print(f"   Recommendations count: {len(recs.get('recommendations', []))}")
        print(f"   Market regime: {recs.get('market_context', {}).get('regime')}")
        print(f"   Generated at: {recs.get('generated_at')}")
        print(f"   Valid until: {recs.get('valid_until')}")
        
        # Print first recommendation if available
        if recs.get('recommendations'):
            first_rec = recs['recommendations'][0]
            print(f"\n   First recommendation:")
            print(f"   - Ticker: {first_rec.get('ticker')}")
            print(f"   - Action: {first_rec.get('action')}")
            print(f"   - Score: {first_rec.get('score')}")
            print(f"   - Risk: {first_rec.get('risk_level')}")
            print(f"   - Reasoning: {first_rec.get('reasoning')[:80]}...")
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Custom universe
    print("\n🧪 Test 3: Generate recommendations with custom universe")
    try:
        recs = await service.generate_daily_recommendations(
            universe=['AAPL', 'MSFT', 'NVDA', 'TSLA'],
            limit=2
        )
        
        print(f"✅ Custom universe recommendations generated")
        print(f"   Recommendations count: {len(recs.get('recommendations', []))}")
        
        for i, rec in enumerate(recs.get('recommendations', []), 1):
            print(f"\n   Recommendation {i}:")
            print(f"   - Ticker: {rec.get('ticker')}")
            print(f"   - Score: {rec.get('score')}")
            print(f"   - Confidence: {rec.get('confidence')}")
        
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Structure validation
    print("\n🧪 Test 4: Validate response structure")
    try:
        recs = await service.generate_daily_recommendations(limit=1)
        
        assert 'recommendations' in recs, "Missing 'recommendations' key"
        assert 'market_context' in recs, "Missing 'market_context' key"
        assert 'generated_at' in recs, "Missing 'generated_at' key"
        assert 'valid_until' in recs, "Missing 'valid_until' key"
        
        assert isinstance(recs['recommendations'], list), "'recommendations' should be a list"
        assert len(recs['recommendations']) <= 1, f"Expected max 1 recommendation, got {len(recs['recommendations'])}"
        
        if recs['recommendations']:
            rec = recs['recommendations'][0]
            required_fields = ['ticker', 'action', 'score', 'reasoning', 'risk_level', 'confidence']
            for field in required_fields:
                assert field in rec, f"Missing required field: {field}"
        
        print("✅ Response structure valid")
        print(f"   All required fields present")
        
    except AssertionError as e:
        print(f"❌ Test 4 failed: {e}")
    except Exception as e:
        print(f"❌ Test 4 failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Caching
    print("\n🧪 Test 5: Test caching mechanism")
    try:
        # First call
        recs1 = await service.generate_daily_recommendations(universe=['AAPL'], limit=1)
        gen_time1 = recs1.get('generated_at')
        
        # Second call (should be cached)
        recs2 = await service.generate_daily_recommendations(universe=['AAPL'], limit=1)
        gen_time2 = recs2.get('generated_at')
        
        if gen_time1 == gen_time2:
            print("✅ Caching working (same generated_at timestamp)")
        else:
            print("⚠️  Caching may not be working (different timestamps)")
        
        print(f"   First call: {gen_time1}")
        print(f"   Second call: {gen_time2}")
        
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_recommendations_service())
