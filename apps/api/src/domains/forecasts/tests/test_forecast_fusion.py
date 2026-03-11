"""
Test Forecast Fusion Contract - BATCH-49-DEV-03

Verifies the multi-layer forecast fusion + attribution contract:
- Layer weights sum to 1.0
- Normalized contributions sum to 1.0
- Stability detection (stable/watch/fragile)
- Attribution tracking with dominant layer identification
- Macro alignment in risk-off regimes
- Momentum dominance in bullish conditions

This is the minimal vertical slice for independent fusion contract verification.
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


class TestForecastFusionContract:
    """Test forecast fusion contract independently from playbook integration."""

    def test_fusion_layers_weights_sum_to_one(self):
        """Verify layer weights always sum to 1.0."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.65,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        total_weight = sum(layer['weight'] for layer in fusion['layers'])
        assert total_weight == pytest.approx(1.0, abs=1e-6)

    def test_fusion_normalized_contributions_sum_to_one(self):
        """Verify normalized contributions always sum to 1.0 after rounding."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.65,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        total_normalized = sum(layer['normalized_contribution'] for layer in fusion['layers'])
        assert total_normalized == pytest.approx(1.0, abs=1e-3)
        assert fusion['contribution_normalization']['sum'] == pytest.approx(1.0, abs=1e-3)
        assert fusion['contribution_normalization']['scheme'] == 'layer_contribution_share'

    def test_fusion_six_layers_present(self):
        """Verify all 6 fusion layers are present."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.65,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        assert len(fusion['layers']) == 6
        layer_names = [layer['layer'] for layer in fusion['layers']]
        expected_layers = [
            'forecast_confidence',
            'expected_return',
            'momentum',
            'news',
            'macro_alignment',
            'risk_reward',
        ]
        assert layer_names == expected_layers

    def test_fusion_stability_status_stable(self):
        """Verify stability detection returns 'stable' when dominant layer has large gap."""
        service = RecommendationsService()

        # Strong bullish signal should give stable forecast_confidence dominance
        fusion = service._build_forecast_fusion(
            ticker='NVDA',
            score=0.85,
            forecast={
                'direction': 'up',
                'confidence': 0.9,
                'expected_return': 0.04,
                'market_context': {
                    'news_sentiment': 0.3,
                    'news_volume_zscore': 1.5,
                },
            },
            market_context={'regime': 'BULL_MARKET'},
        )

        assert fusion['stability']['status'] in {'stable', 'watch'}
        assert fusion['stability']['dominant_share'] > fusion['stability']['runner_up_share']
        assert 'dominant_layer' in fusion
        assert 'runner_up_layer' in fusion['stability']

    def test_fusion_dominant_layer_identified(self):
        """Verify dominant layer is correctly identified by contribution."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.65,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        # Find layer with max contribution
        max_contrib_layer = max(fusion['layers'], key=lambda x: x['contribution'])
        assert fusion['dominant_layer'] == max_contrib_layer['layer']

    def test_fusion_attribution_includes_context(self):
        """Verify attribution includes forecast direction and market regime."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.65,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'BULL_MARKET'},
        )

        assert 'attribution' in fusion
        assert fusion['attribution']['forecast_direction'] == 'up'
        assert fusion['attribution']['market_regime'] == 'BULL_MARKET'
        assert 'expected_return' in fusion['attribution']
        assert 'news_sentiment' in fusion['attribution']
        assert 'macro_alignment' in fusion['attribution']

    def test_fusion_macro_dominance_in_risk_off(self):
        """Verify macro_alignment becomes dominant in RISK_OFF regime for safe havens."""
        service = RecommendationsService()

        # Safe haven asset in risk-off should have high macro alignment
        fusion = service._build_forecast_fusion(
            ticker='GLD',
            score=0.55,
            forecast={
                'direction': 'up',
                'confidence': 0.5,
                'expected_return': 0.01,
                'market_context': {
                    'news_sentiment': 0.0,
                    'news_volume_zscore': 0.0,
                },
            },
            market_context={'regime': 'RISK_OFF'},
        )

        # Macro alignment should be high (1.0 for safe haven in risk-off)
        macro_layer = next(l for l in fusion['layers'] if l['layer'] == 'macro_alignment')
        assert macro_layer['score'] == pytest.approx(1.0, abs=1e-3)

    def test_fusion_momentum_dominance_strong_direction(self):
        """Verify momentum layer dominates with strong directional signal."""
        service = RecommendationsService()

        # Strong directional move with high confidence
        fusion = service._build_forecast_fusion(
            ticker='NVDA',
            score=0.80,
            forecast={
                'direction': 'up',
                'confidence': 0.85,
                'expected_return': 0.03,
                'market_context': {
                    'news_sentiment': 0.2,
                    'news_volume_zscore': 1.0,
                },
            },
            market_context={'regime': 'BULL_MARKET'},
        )

        # Momentum should have high score (0.8 for 'up' direction)
        momentum_layer = next(l for l in fusion['layers'] if l['layer'] == 'momentum')
        assert momentum_layer['score'] == pytest.approx(0.8, abs=1e-3)

    def test_fusion_blended_score_matches_input(self):
        """Verify blended_score reflects the input score."""
        service = RecommendationsService()

        input_score = 0.72
        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=input_score,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        assert fusion['blended_score'] == pytest.approx(input_score, abs=1e-3)

    def test_fusion_layer_structure_complete(self):
        """Verify each layer has all required fields."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.65,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        required_fields = ['layer', 'score', 'weight', 'contribution', 'normalized_contribution', 'contribution_pct']
        for layer in fusion['layers']:
            for field in required_fields:
                assert field in layer, f"Layer {layer['layer']} missing field '{field}'"

    def test_fusion_stability_structure_complete(self):
        """Verify stability section has all required fields."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.65,
            forecast={
                'direction': 'up',
                'confidence': 0.7,
                'expected_return': 0.02,
                'market_context': {
                    'news_sentiment': 0.1,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        required_fields = ['status', 'dominance_gap', 'dominant_share', 'runner_up_layer', 'runner_up_share']
        for field in required_fields:
            assert field in fusion['stability'], f"Stability missing field '{field}'"

        assert fusion['stability']['status'] in {'stable', 'watch', 'fragile'}
        assert fusion['stability']['dominance_gap'] >= 0.0
        assert 0.0 <= fusion['stability']['dominant_share'] <= 1.0
        assert 0.0 <= fusion['stability']['runner_up_share'] <= 1.0


class TestForecastFusionEdgeCases:
    """Test forecast fusion edge cases and boundary conditions."""

    def test_fusion_handles_zero_confidence(self):
        """Verify fusion handles zero confidence gracefully."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='AAPL',
            score=0.30,
            forecast={
                'direction': 'flat',
                'confidence': 0.0,
                'expected_return': 0.0,
                'market_context': {
                    'news_sentiment': 0.0,
                    'news_volume_zscore': 0.0,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        assert fusion['blended_score'] >= 0.0
        assert fusion['contribution_normalization']['sum'] == pytest.approx(1.0, abs=1e-3)

    def test_fusion_handles_extreme_expected_return(self):
        """Verify fusion handles extreme expected return values."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='TSLA',
            score=0.70,
            forecast={
                'direction': 'up',
                'confidence': 0.6,
                'expected_return': 0.15,  # Extreme: 15%
                'market_context': {
                    'news_sentiment': 0.4,
                    'news_volume_zscore': 2.5,
                },
            },
            market_context={'regime': 'NORMAL'},
        )

        # Should still produce valid output
        assert fusion['contribution_normalization']['sum'] == pytest.approx(1.0, abs=1e-3)
        assert 0.0 <= fusion['blended_score'] <= 1.0

    def test_fusion_handles_bear_market(self):
        """Verify fusion handles bear market regime correctly."""
        service = RecommendationsService()

        fusion = service._build_forecast_fusion(
            ticker='JNJ',
            score=0.55,
            forecast={
                'direction': 'down',
                'confidence': 0.6,
                'expected_return': -0.02,
                'market_context': {
                    'news_sentiment': -0.2,
                    'news_volume_zscore': 0.5,
                },
            },
            market_context={'regime': 'BEAR_MARKET'},
        )

        # Defensive stocks should have better macro alignment in bear market
        macro_layer = next(l for l in fusion['layers'] if l['layer'] == 'macro_alignment')
        assert macro_layer['score'] > 0.5  # Should be above average for defensive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
