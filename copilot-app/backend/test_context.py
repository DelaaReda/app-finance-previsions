#!/usr/bin/env python3
"""
Test Context Service
File: backend/test_context.py
Task: FC-INT-021 - ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

async def test_context_service():
    """Test the context service."""
    print("=" * 60)
    print("Testing Context Service (FC-INT-021)")
    print("=" * 60)
    
    try:
        from services.context_service import get_context_service
        
        print("\n1. Creating context service instance...")
        service = get_context_service()
        print("✅ Service instance created")
        
        print("\n2. Getting current market context...")
        context = await service.get_current_market_context()
        print("✅ Context retrieved")
        
        print("\n3. Validating context structure...")
        
        # Check top-level keys
        assert 'regime' in context, "Missing 'regime' key"
        assert 'confidence' in context, "Missing 'confidence' key"
        assert 'key_drivers' in context, "Missing 'key_drivers' key"
        assert 'recommended_layout' in context, "Missing 'recommended_layout' key"
        assert 'characteristics' in context, "Missing 'characteristics' key"
        assert 'metadata' in context, "Missing 'metadata' key"
        print("✅ Top-level structure valid")
        
        # Check regime
        regime = context['regime']
        valid_regimes = [
            'HIGH_VOLATILITY', 'ELEVATED_RISK', 'BULL_MARKET', 
            'BEAR_MARKET', 'RISK_OFF', 'RISK_ON', 'NORMAL'
        ]
        assert regime in valid_regimes, f"Invalid regime: {regime}"
        print(f"✅ Regime valid: {regime}")
        
        # Check confidence
        confidence = context['confidence']
        assert 0 <= confidence <= 1, f"Invalid confidence: {confidence}"
        print(f"✅ Confidence valid: {confidence:.2f}")
        
        # Check key drivers
        drivers = context['key_drivers']
        assert isinstance(drivers, list), "key_drivers must be a list"
        assert len(drivers) > 0, "key_drivers must not be empty"
        print(f"✅ Key drivers: {len(drivers)} identified")
        for driver in drivers:
            print(f"   - {driver}")
        
        # Check recommended layout
        layout = context['recommended_layout']
        assert 'primary_widgets' in layout, "Missing 'primary_widgets'"
        assert 'filters' in layout, "Missing 'filters'"
        assert 'emphasis' in layout, "Missing 'emphasis'"
        print(f"✅ Recommended layout valid")
        print(f"   Primary widgets: {', '.join(layout['primary_widgets'])}")
        print(f"   Emphasis: {layout['emphasis']}")
        if layout['filters']:
            print(f"   Filters: {layout['filters']}")
        
        # Check characteristics
        chars = context['characteristics']
        assert 'volatility' in chars, "Missing 'volatility'"
        assert 'sentiment' in chars, "Missing 'sentiment'"
        assert 'trend' in chars, "Missing 'trend'"
        assert 'momentum' in chars, "Missing 'momentum'"
        assert 'risk_level' in chars, "Missing 'risk_level'"
        print(f"✅ Characteristics valid")
        print(f"   Volatility: {chars['volatility']}")
        print(f"   Sentiment: {chars['sentiment']}")
        print(f"   Trend: {chars['trend']}")
        print(f"   Momentum: {chars['momentum']}")
        print(f"   Risk Level: {chars['risk_level']}")
        
        # Check metadata
        metadata = context['metadata']
        assert 'generated_at' in metadata, "Missing 'generated_at'"
        assert 'sources' in metadata, "Missing 'sources'"
        assert 'confidence_breakdown' in metadata, "Missing 'confidence_breakdown'"
        print(f"✅ Metadata valid")
        print(f"   Generated at: {metadata['generated_at']}")
        
        # Validate confidence breakdown
        breakdown = metadata['confidence_breakdown']
        assert 'vix_certainty' in breakdown
        assert 'forecast_certainty' in breakdown
        assert 'news_certainty' in breakdown
        print(f"✅ Confidence breakdown:")
        print(f"   VIX certainty: {breakdown['vix_certainty']:.2f}")
        print(f"   Forecast certainty: {breakdown['forecast_certainty']:.2f}")
        print(f"   News certainty: {breakdown['news_certainty']:.2f}")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print(f"\n🎯 Market Context: {regime}")
        print(f"📊 Confidence: {confidence:.0%}")
        print(f"🎨 Recommended UI: {layout['emphasis']} emphasis")
        print(f"🔧 Widgets: {len(layout['primary_widgets'])} primary")
        print("\nContext Service is functional!")
        print("Endpoint available at: /api/context/current")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_context_service())
    sys.exit(0 if success else 1)
