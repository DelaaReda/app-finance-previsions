"""
BATCH-84-DEV-03: Live Market Data Enhancement Tests

Tests for the live market data enhancement feature that adds VIX, SPY, QQQ
data to the daily brief payload.
"""
import pytest
from typing import Dict, Any
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timezone
import os


class TestFetchLiveMarketIndicators:
    """Tests for _fetch_live_market_indicators function."""

    def test_fetch_live_market_indicators_success(self):
        """Should fetch VIX, SPY, QQQ data successfully."""
        from domains.copilot.application.copilot_service import _fetch_live_market_indicators
        
        # Mock price history data
        mock_spy_df = pd.DataFrame({
            'Close': [450.0, 455.0]  # +1.11% change
        }, index=pd.date_range('2026-03-23', periods=2))
        
        mock_vix_df = pd.DataFrame({
            'Close': [18.5]
        }, index=pd.date_range('2026-03-24', periods=1))
        
        with patch.dict(os.environ, {"FC_COPILOT_LIVE_MARKET_DATA": "1"}):
            with patch('domains.copilot.application.copilot_service.get_price_history') as mock_get_price:
                mock_get_price.side_effect = lambda symbol, **kwargs: (
                    mock_vix_df if symbol == '^VIX' else 
                    mock_spy_df if symbol == 'SPY' else
                    mock_spy_df if symbol == 'QQQ' else None
                )
                
                result = _fetch_live_market_indicators()
                
                assert result['vix'] == 18.5
                assert result['spy_change'] == pytest.approx(1.11, rel=0.01)
                assert result['qqq_change'] == pytest.approx(1.11, rel=0.01)
                assert result['market_status'] in ['open', 'closed', 'unknown']
                assert result['fetched_at'] is not None
                assert result['source'] == 'live_market_data'
                assert result.get('degraded') == False

    def test_fetch_live_market_indicators_fallback_when_service_unavailable(self):
        """Should return fallback when get_price_history is not available."""
        with patch.dict(os.environ, {"FC_COPILOT_LIVE_MARKET_DATA": "1"}):
            with patch('domains.copilot.application.copilot_service.get_price_history', None):
                from domains.copilot.application.copilot_service import _fetch_live_market_indicators
                
                result = _fetch_live_market_indicators()
                
                assert result['vix'] is None
                assert result['spy_change'] is None
                assert result['qqq_change'] is None
                assert result['degraded'] == True
                assert 'Live data fetch failed' in result.get('degraded_reason', '')

    def test_fetch_live_market_indicators_partial_data(self):
        """Should handle partial data fetch (some tickers fail)."""
        from domains.copilot.application.copilot_service import _fetch_live_market_indicators
        
        mock_spy_df = pd.DataFrame({
            'Close': [450.0, 455.0]
        }, index=pd.date_range('2026-03-23', periods=2))
        
        with patch.dict(os.environ, {"FC_COPILOT_LIVE_MARKET_DATA": "1"}):
            with patch('domains.copilot.application.copilot_service.get_price_history') as mock_get_price:
                # Only SPY succeeds, VIX and QQQ fail
                mock_get_price.side_effect = lambda symbol, **kwargs: (
                    mock_spy_df if symbol == 'SPY' else None
                )
                
                result = _fetch_live_market_indicators()
                
                assert result['vix'] is None
                assert result['spy_change'] == pytest.approx(1.11, rel=0.01)
                assert result['qqq_change'] is None
                # Should not be marked as fully degraded since we got some data
                assert result.get('degraded') == False

    def test_fetch_live_market_indicators_empty_dataframe(self):
        """Should handle empty dataframes gracefully."""
        from domains.copilot.application.copilot_service import _fetch_live_market_indicators
        
        empty_df = pd.DataFrame()
        
        with patch.dict(os.environ, {"FC_COPILOT_LIVE_MARKET_DATA": "1"}):
            with patch('domains.copilot.application.copilot_service.get_price_history') as mock_get_price:
                mock_get_price.return_value = empty_df
                
                result = _fetch_live_market_indicators()
                
                assert result['vix'] is None
                assert result['spy_change'] is None
                assert result['qqq_change'] is None
                assert result['degraded'] == True


class TestEnhanceBriefWithLiveData:
    """Tests for _enhance_brief_with_live_data function."""

    def test_enhance_brief_adds_live_market_data(self):
        """Should add live_market_data section to brief."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {
            'summary': 'Market is stable today.',
            'market_sentiment': 'NEUTRAL',
        }
        
        live_data = {
            'vix': 18.5,
            'spy_change': 1.2,
            'qqq_change': 0.8,
            'market_status': 'open',
        }
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'live_market_data' in enhanced
        assert enhanced['live_market_data']['vix'] == 18.5
        assert enhanced['live_market_data']['spy_change'] == 1.2

    def test_enhance_brief_updates_summary_with_live_context(self):
        """Should prepend live context to summary when data available."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {
            'summary': 'Market is stable today.',
        }
        
        live_data = {
            'vix': 22.0,  # High VIX
            'spy_change': -1.5,  # Down market
        }
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert enhanced['summary'].startswith('[Live:')
        assert 'VIX=22.0' in enhanced['summary']
        assert 'S&P 500' in enhanced['summary']
        assert 'Market is stable today.' in enhanced['summary']

    def test_enhance_brief_handles_missing_summary(self):
        """Should handle brief without existing summary."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {}
        live_data = {'vix': 15.0, 'spy_change': 0.5}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'live_market_data' in enhanced
        # Should not crash when summary is missing

    def test_enhance_brief_preserves_original_fields(self):
        """Should preserve all original brief fields."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {
            'summary': 'Original summary',
            'market_sentiment': 'BULLISH',
            'top_signals': ['Signal 1'],
            'top_risks': ['Risk 1'],
        }
        
        live_data = {'vix': 18.0}
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert enhanced['summary'] is not None
        assert enhanced['market_sentiment'] == 'BULLISH'
        assert enhanced['top_signals'] == ['Signal 1']
        assert enhanced['top_risks'] == ['Risk 1']
        assert enhanced['live_market_data'] is not None

    def test_enhance_brief_with_empty_live_data(self):
        """Should handle empty live data gracefully."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        live_data = {}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        # Should not crash, may or may not add live_market_data
        assert isinstance(enhanced, dict)

    def test_enhance_brief_with_none_live_data(self):
        """Should handle None live data gracefully."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        
        enhanced = _enhance_brief_with_live_data(brief, None)
        
        assert enhanced == brief


class TestLoadDailyBriefPayloadWithLiveData:
    """Integration tests for _load_daily_brief_payload with live data enhancement."""

    def test_load_daily_brief_includes_live_data_when_available(self):
        """Should include live market data in loaded brief."""
        from domains.copilot.application.copilot_service import _load_daily_brief_payload
        
        mock_brief_snapshot = {
            'data': {
                'daily': {
                    'summary': 'Test brief summary',
                    'market_sentiment': 'BULLISH',
                    'top_signals': ['Tech rally continues'],
                    'top_risks': ['Inflation concerns'],
                }
            }
        }
        
        mock_spy_df = pd.DataFrame({'Close': [450.0, 455.0]})
        mock_vix_df = pd.DataFrame({'Close': [18.0]})
        
        with patch.dict(os.environ, {"FC_COPILOT_LIVE_MARKET_DATA": "1"}):
            with patch('domains.copilot.application.copilot_service.storage_io') as mock_io:
                mock_io.load_json.return_value = mock_brief_snapshot
                
                with patch('domains.copilot.application.copilot_service.get_price_history') as mock_price:
                    mock_price.side_effect = lambda symbol, **kwargs: (
                        mock_vix_df if symbol == '^VIX' else mock_spy_df
                    )
                    
                    result = _load_daily_brief_payload()
                    
                    assert result['summary'] is not None
                    assert result['market_sentiment'] == 'BULLISH'
                    # Live data should be included
                    assert 'live_market_data' in result or 'live_market_data' in str(result.get('source', []))

    def test_load_daily_brief_fallback_when_no_snapshot(self):
        """Should return fallback when no snapshot available."""
        from domains.copilot.application.copilot_service import _load_daily_brief_payload
        
        with patch('domains.copilot.application.copilot_service.storage_io') as mock_io:
            mock_io.load_json.return_value = None
            
            result = _load_daily_brief_payload()
            
            assert result['summary'] == 'No daily brief available yet.'
            assert result['market_sentiment'] == 'UNKNOWN'


class TestVIXInterpretation:
    """Tests for VIX level interpretation in live data enhancement."""

    def test_vix_high_interpretation(self):
        """VIX > 20 should be interpreted as 'elevé' (high)."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        live_data = {'vix': 25.0}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'VIX=25.0 (élevé)' in enhanced['summary']

    def test_vix_low_interpretation(self):
        """VIX < 15 should be interpreted as 'bas' (low)."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        live_data = {'vix': 12.0}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'VIX=12.0 (bas)' in enhanced['summary']

    def test_vix_normal_interpretation(self):
        """VIX 15-20 should be interpreted as 'normal'."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        live_data = {'vix': 17.5}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'VIX=17.5 (normal)' in enhanced['summary']


class TestSPYDirectionInterpretation:
    """Tests for S&P 500 direction interpretation."""

    def test_spy_bullish(self):
        """SPY change > 0.5% should be 'haussier' (bullish)."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        live_data = {'spy_change': 1.2}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'S&P 500 haussier' in enhanced['summary']

    def test_spy_bearish(self):
        """SPY change < -0.5% should be 'baissier' (bearish)."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        live_data = {'spy_change': -1.2}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'S&P 500 baissier' in enhanced['summary']

    def test_spy_stable(self):
        """SPY change between -0.5% and 0.5% should be 'stable'."""
        from domains.copilot.application.copilot_service import _enhance_brief_with_live_data
        
        brief = {'summary': 'Test'}
        live_data = {'spy_change': 0.2}
        
        enhanced = _enhance_brief_with_live_data(brief, live_data)
        
        assert 'S&P 500 stable' in enhanced['summary']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
