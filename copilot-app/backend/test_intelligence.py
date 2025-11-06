#!/usr/bin/env python3
"""
Test Intelligence Service
File: backend/test_intelligence.py
Task: FC-INT-020 - ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

async def test_intelligence_service():
    """Test the intelligence service."""
    print("=" * 60)
    print("Testing Intelligence Service (FC-INT-020)")
    print("=" * 60)
    
    try:
        from services.intelligence_service import get_intelligence_service
        
        print("\n1. Creating intelligence service instance...")
        service = get_intelligence_service()
        print("✅ Service instance created")
        
        print("\n2. Generating market intelligence snapshot...")
        snapshot = await service.get_market_snapshot_intelligence()
        print("✅ Snapshot generated")
        
        print("\n3. Validating snapshot structure...")
        
        # Check top-level keys
        assert 'data' in snapshot, "Missing 'data' key"
        assert 'insights' in snapshot, "Missing 'insights' key"
        assert 'metadata' in snapshot, "Missing 'metadata' key"
        print("✅ Top-level structure valid")
        
        # Check data section
        data = snapshot['data']
        assert 'forecasts' in data, "Missing 'forecasts' in data"
        assert 'macro' in data, "Missing 'macro' in data"
        assert 'news' in data, "Missing 'news' in data"
        assert 'derived' in data, "Missing 'derived' in data"
        print(f"✅ Data section valid (forecasts: {len(data['forecasts'])}, news: {len(data['news'])})")
        
        # Check insights section
        insights = snapshot['insights']
        assert 'market_regime' in insights, "Missing 'market_regime' in insights"
        assert 'opportunities' in insights, "Missing 'opportunities' in insights"
        assert 'risks' in insights, "Missing 'risks' in insights"
        assert 'summary' in insights, "Missing 'summary' in insights"
        print(f"✅ Insights section valid")
        
        # Display insights
        print("\n4. Generated Insights:")
        print(f"   Market Regime: {insights['market_regime'].get('regime', 'N/A')}")
        print(f"   Regime Explanation: {insights['market_regime'].get('explanation', 'N/A')}")
        print(f"   Opportunities: {len(insights['opportunities'])}")
        for opp in insights['opportunities'][:3]:
            print(f"      - {opp.get('ticker', 'N/A')}: {opp.get('reasoning', 'N/A')[:60]}...")
        print(f"   Risks: {len(insights['risks'])}")
        for risk in insights['risks']:
            print(f"      - {risk.get('type', 'N/A')}: {risk.get('description', 'N/A')[:60]}...")
        print(f"   Summary: {insights['summary'][:150]}...")
        
        # Check metadata
        metadata = snapshot['metadata']
        assert 'generated_at' in metadata, "Missing 'generated_at' in metadata"
        assert 'freshness' in metadata, "Missing 'freshness' in metadata"
        print(f"\n✅ Metadata valid (generated_at: {metadata['generated_at']})")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nIntelligence Service is functional!")
        print("Endpoint available at: /api/intelligence/snapshot")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_intelligence_service())
    sys.exit(0 if success else 1)
