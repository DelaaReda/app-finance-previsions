"""
Test Recommendations + Playbooks Integration - BATCH-15-DEV-02

Verifies that recommendations are enriched with strategy playbook context:
- playbook_id
- conflict_warning
- playbook_context

This is the minimal vertical slice for the Strategy Playbooks Engine.
"""
import pytest
import sys
from pathlib import Path

# Add src to path for imports
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from typing import Dict, Any

from domains.forecasts.application.recommendations_service import RecommendationsService
from domains.copilot.application.playbook_resolver import PlaybookResolver
from domains.copilot.domain.playbook import MarketRegime, RiskProfile


class TestRecommendationsPlaybookIntegration:
    """Test that recommendations service enriches output with playbook context."""

    def test_recommendations_service_has_playbook_resolver(self):
        """Verify RecommendationsService initializes with playbook resolver."""
        service = RecommendationsService()
        assert service.playbook_resolver is not None
        assert isinstance(service.playbook_resolver, PlaybookResolver)

    def test_format_recommendations_enriched_with_playbook_id(self):
        """Test formatted recommendations include playbook_id."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'AAPL',
                'score': 0.75,
                'reasoning': 'Strong momentum',
                'catalysts': ['Tech rally'],
                'risk_level': 'MEDIUM',
                'confidence': 0.8,
                'data': {
                    'forecast': {
                        'direction': 'up',
                        'confidence': 0.75
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'BULL_MARKET',
            'key_drivers': ['Tech earnings']
        }
        
        result = service._format_recommendations(validated, market_context)
        
        assert 'recommendations' in result
        assert len(result['recommendations']) > 0
        
        rec = result['recommendations'][0]
        assert 'playbook_id' in rec
        assert rec['playbook_id'] == 'bull_moderate_001'

    def test_format_recommendations_includes_conflict_warning(self):
        """Test formatted recommendations include conflict_warning structure."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'AAPL',
                'score': 0.75,
                'data': {
                    'forecast': {
                        'direction': 'up',
                        'confidence': 0.75
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'BEAR_MARKET',
            'key_drivers': ['Market decline']
        }
        
        result = service._format_recommendations(validated, market_context)
        
        rec = result['recommendations'][0]
        assert 'conflict_warning' in rec
        assert isinstance(rec['conflict_warning'], dict)
        assert 'detected' in rec['conflict_warning']

    def test_format_recommendations_includes_playbook_context(self):
        """Test formatted recommendations include playbook_context summary."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'SPY',
                'score': 0.65,
                'data': {
                    'forecast': {
                        'direction': 'flat',
                        'confidence': 0.6
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'NORMAL',
            'key_drivers': ['Balanced market']
        }
        
        result = service._format_recommendations(validated, market_context)
        
        rec = result['recommendations'][0]
        assert 'playbook_context' in rec
        assert 'name' in rec['playbook_context']
        assert 'description' in rec['playbook_context']
        assert 'guardrails' in rec['playbook_context']

    def test_bull_market_recommendations_get_bull_playbook(self):
        """Test bull market regime resolves to bull playbook."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'NVDA',
                'score': 0.85,
                'data': {
                    'forecast': {
                        'direction': 'up',
                        'confidence': 0.8
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'BULL_MARKET',
            'key_drivers': ['AI boom']
        }
        
        result = service._format_recommendations(validated, market_context)
        rec = result['recommendations'][0]
        
        assert rec['playbook_id'] == 'bull_moderate_001'
        assert rec['playbook_context']['name'] == 'Bull Market Growth Strategy'

    def test_bear_market_recommendations_get_bear_playbook(self):
        """Test bear market regime resolves to bear playbook."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'JNJ',
                'score': 0.60,
                'data': {
                    'forecast': {
                        'direction': 'down',
                        'confidence': 0.65
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'BEAR_MARKET',
            'key_drivers': ['Recession fears']
        }
        
        result = service._format_recommendations(validated, market_context)
        rec = result['recommendations'][0]
        
        assert rec['playbook_id'] == 'bear_moderate_001'
        assert rec['playbook_context']['name'] == 'Bear Market Defensive Strategy'

    def test_risk_off_recommendations_get_risk_off_playbook(self):
        """Test risk_off regime resolves to risk_off playbook."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'GLD',
                'score': 0.70,
                'data': {
                    'forecast': {
                        'direction': 'up',
                        'confidence': 0.7
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'RISK_OFF',
            'key_drivers': ['Geopolitical tension']
        }
        
        result = service._format_recommendations(validated, market_context)
        rec = result['recommendations'][0]
        
        assert rec['playbook_id'] == 'risk_off_moderate_001'
        assert rec['playbook_context']['name'] == 'Risk-Off Balanced Defense'

    def test_conflict_detection_bullish_signal_in_bear_market(self):
        """Test conflict detected when bullish signal in bear market playbook."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'TSLA',
                'score': 0.72,
                'data': {
                    'forecast': {
                        'direction': 'up',  # Bullish signal
                        'confidence': 0.7
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'BEAR_MARKET',
            'key_drivers': ['Downtrend']
        }
        
        result = service._format_recommendations(validated, market_context)
        rec = result['recommendations'][0]
        
        # Bear market playbook should conflict with bullish signal
        assert rec['conflict_warning']['detected'] is True

    def test_fallback_recommendations_still_include_playbook_id(self):
        """Fallback payloads must keep playbook metadata for acceptance."""
        service = RecommendationsService()

        result = service._fallback_recommendations()

        assert result['status'] == 'fallback'
        assert len(result['recommendations']) == 3
        assert all('playbook_id' in rec for rec in result['recommendations'])
        assert all('playbook_context' in rec for rec in result['recommendations'])
        assert all(rec['conflict_warning']['detected'] is False for rec in result['recommendations'])

    def test_no_conflict_neutral_signal(self):
        """Test no conflict when signal is neutral."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'AAPL',
                'score': 0.55,
                'data': {
                    'forecast': {
                        'direction': 'flat',  # Neutral signal
                        'confidence': 0.5
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'NORMAL',
            'key_drivers': ['Sideways market']
        }
        
        result = service._format_recommendations(validated, market_context)
        rec = result['recommendations'][0]
        
        # Neutral signal should not trigger conflict
        assert rec['conflict_warning']['detected'] is False


class TestPlaybookEnrichmentStructure:
    """Test the structure of playbook enrichment matches API contract."""

    def test_enriched_recommendation_structure(self):
        """Verify enriched recommendation has all required fields."""
        service = RecommendationsService()
        
        validated = [
            {
                'ticker': 'MSFT',
                'score': 0.78,
                'reasoning': 'Cloud growth',
                'catalysts': ['Azure earnings'],
                'risk_level': 'MEDIUM',
                'confidence': 0.75,
                'data': {
                    'forecast': {
                        'direction': 'up',
                        'confidence': 0.7
                    }
                }
            }
        ]
        
        market_context = {
            'regime': 'BULL_MARKET',
            'key_drivers': ['Tech rally']
        }
        
        result = service._format_recommendations(validated, market_context)
        rec = result['recommendations'][0]
        
        # Original fields preserved
        assert 'ticker' in rec
        assert 'score' in rec
        assert 'reasoning' in rec
        assert 'catalysts' in rec
        assert 'risk_level' in rec
        assert 'confidence' in rec
        assert 'supporting_data' in rec
        
        # Playbook enrichment added
        assert 'playbook_id' in rec
        assert 'conflict_warning' in rec
        assert 'playbook_context' in rec
        
        # Conflict warning structure
        assert 'detected' in rec['conflict_warning']
        
        # Playbook context structure
        assert 'name' in rec['playbook_context']
        assert 'description' in rec['playbook_context']
        assert 'guardrails' in rec['playbook_context']
        assert 'forecast_fusion' in rec
        assert rec['forecast_fusion']['blended_score'] == pytest.approx(0.78, abs=1e-3)
        assert rec['forecast_fusion']['dominant_layer'] == 'forecast_confidence'
        assert rec['forecast_fusion']['attribution']['market_regime'] == 'BULL_MARKET'
        assert len(rec['forecast_fusion']['layers']) == 6
        assert rec['forecast_fusion']['contribution_normalization']['scheme'] == 'layer_contribution_share'
        assert rec['forecast_fusion']['contribution_normalization']['sum'] == pytest.approx(1.0, abs=1e-3)
        assert rec['forecast_fusion']['stability']['status'] == 'watch'
        assert rec['forecast_fusion']['stability']['dominant_share'] > rec['forecast_fusion']['stability']['runner_up_share']
        assert rec['supporting_data']['forecast_fusion'] == rec['forecast_fusion']

    def test_forecast_fusion_tracks_macro_dominance_for_safe_haven(self):
        """Safe havens in risk-off should expose macro attribution as dominant."""
        service = RecommendationsService()

        validated = [
            {
                'ticker': 'GLD',
                'score': 0.14,
                'data': {
                    'forecast': {
                        'direction': 'down',
                        'confidence': 0.0,
                        'expected_return': -0.05,
                        'market_context': {
                            'news_sentiment': 0.0,
                            'news_volume_zscore': 0.0,
                        },
                    }
                }
            }
        ]

        market_context = {
            'regime': 'RISK_OFF',
            'key_drivers': ['Flight to safety']
        }

        result = service._format_recommendations(validated, market_context)
        fusion = result['recommendations'][0]['forecast_fusion']

        assert fusion['dominant_layer'] == 'macro_alignment'
        assert fusion['attribution']['macro_alignment'] == pytest.approx(1.0, abs=1e-3)
        assert fusion['stability']['runner_up_layer'] in {'expected_return', 'news'}
        assert fusion['stability']['dominant_share'] > fusion['stability']['runner_up_share']
        assert fusion['contribution_normalization']['sum'] == pytest.approx(1.0, abs=1e-3)
        assert sum(layer['normalized_contribution'] for layer in fusion['layers']) == pytest.approx(1.0, abs=1e-3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
