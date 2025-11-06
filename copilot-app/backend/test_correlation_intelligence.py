"""
Test Correlation Intelligence Service

Validates the correlation intelligence service functionality.

Author: ELENA-39
Task: FC-INT-025
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_correlation_intelligence():
    """Test correlation intelligence service"""
    
    logger.info("=" * 60)
    logger.info("Testing Correlation Intelligence Service")
    logger.info("=" * 60)
    
    try:
        from services.correlation_intelligence_service import get_correlation_intelligence_service
        
        service = get_correlation_intelligence_service()
        logger.info("✅ Service instantiated")
        
        # Test 1: Default universe
        logger.info("\n[TEST 1] Default universe")
        result = await service.generate_correlation_intelligence()
        
        assert 'matrix' in result, "Missing matrix"
        assert 'tickers' in result, "Missing tickers"
        assert 'interesting_pairs' in result, "Missing interesting_pairs"
        assert 'summary' in result, "Missing summary"
        assert 'generated_at' in result, "Missing generated_at"
        
        logger.info(f"✅ Matrix shape: {len(result['matrix'])}x{len(result['matrix'][0]) if result['matrix'] else 0}")
        logger.info(f"✅ Tickers: {result['tickers']}")
        logger.info(f"✅ Interesting pairs: {len(result['interesting_pairs'])}")
        logger.info(f"✅ Summary: {result['summary'][:100]}...")
        
        # Test 2: Custom universe
        logger.info("\n[TEST 2] Custom universe")
        result2 = await service.generate_correlation_intelligence(
            universe=['AAPL', 'MSFT', 'NVDA'],
            window='90d',
            threshold=0.8
        )
        
        assert len(result2['tickers']) == 3, f"Expected 3 tickers, got {len(result2['tickers'])}"
        logger.info(f"✅ Custom universe: {result2['tickers']}")
        logger.info(f"✅ Pairs found: {len(result2['interesting_pairs'])}")
        
        # Test 3: Validate pair structure
        logger.info("\n[TEST 3] Pair structure validation")
        if result['interesting_pairs']:
            pair = result['interesting_pairs'][0]
            
            required_fields = ['ticker1', 'ticker2', 'correlation', 'explanation', 'drivers', 'implications', 'action_type']
            for field in required_fields:
                assert field in pair, f"Missing field: {field}"
            
            logger.info(f"✅ Pair structure valid")
            logger.info(f"   Pair: {pair['ticker1']} <-> {pair['ticker2']}")
            logger.info(f"   Correlation: {pair['correlation']:.2f}")
            logger.info(f"   Explanation: {pair['explanation'][:80]}...")
            logger.info(f"   Drivers: {pair['drivers']}")
            logger.info(f"   Action: {pair['action_type']} - {pair['action_description'][:50]}...")
        
        # Test 4: Cache test
        logger.info("\n[TEST 4] Cache test")
        result3 = await service.generate_correlation_intelligence()
        
        assert result3['generated_at'] == result['generated_at'], "Cache should return same result"
        logger.info(f"✅ Cache working (same timestamp)")
        
        logger.info("\n" + "=" * 60)
        logger.info("ALL TESTS PASSED ✅")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_correlation_intelligence())
    sys.exit(0 if success else 1)
