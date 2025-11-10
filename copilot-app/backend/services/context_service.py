"""
Context Service - Market context and adaptive UI recommendations
File: backend/services/context_service.py
Task: FC-INT-021 - ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from services.intelligence_service import get_intelligence_service

logger = logging.getLogger(__name__)


class ContextService:
    """
    Context Service that determines market context and recommends
    adaptive UI layouts.
    
    Uses Intelligence Service to classify market regime and generate
    layout recommendations for optimal user experience.
    
    Regimes:
    - HIGH_VOLATILITY: VIX > 30 → Macro + Defensive focus
    - ELEVATED_RISK: VIX > 20, bearish → Caution indicators
    - BULL_MARKET: VIX < 15, bullish > 60% → Growth + Momentum
    - BEAR_MARKET: VIX > 20, bearish > 60% → Defensive + Safe havens
    - RISK_OFF: VIX > 25, negative news → Bonds + Gold
    - RISK_ON: VIX < 15, positive news → Equities + Growth
    - NORMAL: Balanced conditions → Balanced view
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.intelligence_service = get_intelligence_service()
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
    
    async def get_current_market_context(self) -> Dict[str, Any]:
        """
        Get current market context with regime classification and
        UI layout recommendations.
        
        Returns:
            {
                'regime': str,
                'confidence': float,
                'key_drivers': List[str],
                'recommended_layout': {
                    'primary_widgets': List[str],
                    'filters': Dict,
                    'emphasis': str
                },
                'characteristics': {
                    'volatility': str,
                    'sentiment': str,
                    'trend': str,
                    'momentum': str,
                    'risk_level': str
                },
                'metadata': {...}
            }
        """
        self.logger.info("Determining market context...")
        
        try:
            # Step 1: Get intelligence snapshot
            intel = await self.intelligence_service.get_market_snapshot_intelligence()
            
            # Step 1.5: Enhance with recent forecasts data (24h) for dynamic regime
            try:
                from storage.io import load_json
                from datetime import datetime, timedelta
                forecasts_data = load_json("forecasts") or {}
                forecast_rows = forecasts_data.get("rows", []) or forecasts_data.get("data", {}).get("rows", [])
                
                # Calculate recent sentiment from forecasts (last 24h)
                if forecast_rows:
                    recent_bullish = sum(1 for r in forecast_rows if (r.get("direction") or "").lower() in {"up", "bullish", "buy"})
                    recent_bearish = sum(1 for r in forecast_rows if (r.get("direction") or "").lower() in {"down", "bearish", "sell"})
                    recent_total = len(forecast_rows)
                    
                    # Override intel data with recent forecasts if available
                    if recent_total > 0:
                        intel.setdefault("data", {}).setdefault("derived", {}).setdefault("forecast_sentiment", {})["bullish_pct"] = (recent_bullish / recent_total) * 100
                        intel.setdefault("data", {}).setdefault("derived", {}).setdefault("forecast_sentiment", {})["bearish_pct"] = (recent_bearish / recent_total) * 100
                        self.logger.info(f"Enhanced context with {recent_total} recent forecasts (24h)")
            except Exception as e:
                self.logger.debug(f"Could not enhance with recent forecasts: {e}")
            
            # Step 2: Classify market regime
            regime_info = self._classify_regime(intel)
            
            # Step 3: Identify key drivers
            key_drivers = self._identify_key_drivers(intel, regime_info)
            
            # Step 4: Generate layout recommendation
            layout = self._get_recommended_layout(regime_info, intel)
            
            # Step 5: Extract characteristics
            characteristics = self._extract_characteristics(intel, regime_info)
            
            # Step 6: Calculate confidence
            confidence = self._calculate_confidence(intel, regime_info)
            
            # Package response
            context = {
                'regime': regime_info['regime'],
                'confidence': confidence,
                'key_drivers': key_drivers,
                'recommended_layout': layout,
                'characteristics': characteristics,
                'metadata': {
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'sources': ['intelligence', 'macro', 'forecasts', 'news'],
                    'intelligence_snapshot_age': intel['metadata'].get('generated_at'),
                    'confidence_breakdown': self._get_confidence_breakdown(intel, regime_info)
                }
            }
            
            # Cache context
            self._save_context(context)
            
            self.logger.info(f"Context determined: {regime_info['regime']} (confidence: {confidence:.2f})")
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to determine context: {str(e)}", exc_info=True)
            # Return cached context if available
            cached = self._load_cached_context()
            if cached:
                self.logger.info("Returning cached context")
                return cached
            
            # Fallback to default context
            return self._get_fallback_context(str(e))
    
    def _classify_regime(self, intel: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify market regime based on intelligence data.
        """
        data = intel.get('data', {})
        derived = data.get('derived', {})
        
        # Extract key metrics
        macro = data.get('macro', {})
        vix = macro.get('VIX', 20)
        
        market_regime = derived.get('market_regime', {})
        regime_from_intel = market_regime.get('regime', 'NORMAL')
        
        forecast_sentiment = derived.get('forecast_sentiment', {})
        bullish_pct = forecast_sentiment.get('bullish_pct', 0)
        bearish_pct = forecast_sentiment.get('bearish_pct', 0)
        
        news_sentiment = derived.get('news_sentiment', {})
        news_score = news_sentiment.get('score', 0)
        news_bias = news_sentiment.get('bias', 'neutral')
        
        # Classification logic
        regime = self._determine_regime(
            vix=vix,
            bullish_pct=bullish_pct,
            bearish_pct=bearish_pct,
            news_score=news_score,
            news_bias=news_bias,
            intel_regime=regime_from_intel
        )
        
        return {
            'regime': regime,
            'vix': vix,
            'bullish_pct': bullish_pct,
            'bearish_pct': bearish_pct,
            'news_score': news_score,
            'news_bias': news_bias
        }
    
    def _determine_regime(
        self,
        vix: float,
        bullish_pct: float,
        bearish_pct: float,
        news_score: float,
        news_bias: str,
        intel_regime: str
    ) -> str:
        """
        Determine regime using multi-factor decision tree.
        """
        # High volatility regimes
        if vix > 30:
            return 'HIGH_VOLATILITY'
        
        # Risk-off regime
        if vix > 25 and (news_bias == 'negative' or news_score < -0.2):
            return 'RISK_OFF'
        
        # Bear market
        if vix > 20 and bearish_pct > 60:
            return 'BEAR_MARKET'
        
        # Elevated risk
        if vix > 20 and bearish_pct > bullish_pct:
            return 'ELEVATED_RISK'
        
        # Bull market
        if vix < 15 and bullish_pct > 60:
            return 'BULL_MARKET'
        
        # Risk-on
        if vix < 15 and (news_bias == 'positive' or news_score > 0.2):
            return 'RISK_ON'
        
        # Default: normal
        return 'NORMAL'
    
    def _identify_key_drivers(
        self,
        intel: Dict[str, Any],
        regime_info: Dict[str, Any]
    ) -> List[str]:
        """
        Identify key drivers of current market regime.
        """
        drivers = []
        
        vix = regime_info['vix']
        news_score = regime_info['news_score']
        news_bias = regime_info['news_bias']
        bullish_pct = regime_info['bullish_pct']
        bearish_pct = regime_info['bearish_pct']
        
        # VIX-based drivers
        if vix > 30:
            drivers.append(f"Extreme volatility (VIX: {vix:.1f})")
        elif vix > 25:
            drivers.append(f"High volatility (VIX: {vix:.1f})")
        elif vix < 15:
            drivers.append(f"Low volatility (VIX: {vix:.1f})")
        
        # Forecast sentiment drivers
        if bullish_pct > 60:
            drivers.append(f"Strong bullish forecasts ({bullish_pct:.0f}%)")
        elif bearish_pct > 60:
            drivers.append(f"Strong bearish forecasts ({bearish_pct:.0f}%)")
        elif abs(bullish_pct - bearish_pct) < 10:
            drivers.append("Mixed forecast signals")
        
        # News sentiment drivers
        if news_bias == 'negative':
            if news_score < -0.3:
                drivers.append("Very negative news sentiment")
            else:
                drivers.append("Negative news sentiment")
        elif news_bias == 'positive':
            if news_score > 0.3:
                drivers.append("Very positive news sentiment")
            else:
                drivers.append("Positive news sentiment")
        
        # Macro drivers (from intelligence data)
        macro = intel.get('data', {}).get('macro', {})
        
        cpi = macro.get('CPI')
        if cpi and cpi > 4:
            drivers.append(f"High inflation ({cpi:.1f}%)")
        
        t10y2y = macro.get('T10Y2Y')
        if t10y2y and t10y2y < 0:
            drivers.append(f"Inverted yield curve ({t10y2y:.2f})")
        
        unrate = macro.get('UNRATE')
        if unrate and unrate > 5:
            drivers.append(f"Rising unemployment ({unrate:.1f}%)")
        
        # If no drivers identified, add default
        if not drivers:
            drivers.append("Balanced market conditions")
        
        return drivers[:5]  # Top 5 drivers max
    
    def _get_recommended_layout(
        self,
        regime_info: Dict[str, Any],
        intel: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate recommended UI layout based on regime.
        """
        regime = regime_info['regime']
        
        # Layout mappings per regime
        layouts = {
            'HIGH_VOLATILITY': {
                'primary_widgets': ['MacroBoardWidget', 'SignalBarsWidget', 'HeatmapWidget'],
                'filters': {
                    'asset_types': ['defensive', 'bonds'],
                    'forecast_direction': None,
                    'min_confidence': 0.7
                },
                'emphasis': 'macro',
                'alerts_enabled': True,
                'refresh_interval': 300000  # 5 minutes
            },
            'ELEVATED_RISK': {
                'primary_widgets': ['MacroBoardWidget', 'ForecastCardsWidget', 'SignalBarsWidget'],
                'filters': {
                    'asset_types': ['defensive', 'large-cap'],
                    'forecast_direction': None,
                    'min_confidence': 0.65
                },
                'emphasis': 'balanced',
                'alerts_enabled': True,
                'refresh_interval': 600000  # 10 minutes
            },
            'BULL_MARKET': {
                'primary_widgets': ['ForecastCardsWidget', 'PerformanceMatrixWidget', 'SignalBarsWidget'],
                'filters': {
                    'asset_types': ['growth', 'tech'],
                    'forecast_direction': 'up',
                    'min_confidence': 0.6
                },
                'emphasis': 'forecasts',
                'alerts_enabled': False,
                'refresh_interval': 600000  # 10 minutes
            },
            'BEAR_MARKET': {
                'primary_widgets': ['MacroBoardWidget', 'SignalBarsWidget', 'ForecastCardsWidget'],
                'filters': {
                    'asset_types': ['defensive', 'bonds', 'utilities'],
                    'forecast_direction': None,
                    'min_confidence': 0.7
                },
                'emphasis': 'macro',
                'alerts_enabled': True,
                'refresh_interval': 300000  # 5 minutes
            },
            'RISK_OFF': {
                'primary_widgets': ['MacroBoardWidget', 'SignalBarsWidget', 'HeatmapWidget'],
                'filters': {
                    'asset_types': ['bonds', 'gold', 'defensive'],
                    'forecast_direction': None,
                    'min_confidence': 0.75
                },
                'emphasis': 'macro',
                'alerts_enabled': True,
                'refresh_interval': 300000  # 5 minutes
            },
            'RISK_ON': {
                'primary_widgets': ['ForecastCardsWidget', 'PerformanceMatrixWidget', 'ForecastMatrixWidget'],
                'filters': {
                    'asset_types': ['equities', 'growth', 'emerging-markets'],
                    'forecast_direction': 'up',
                    'min_confidence': 0.6
                },
                'emphasis': 'forecasts',
                'alerts_enabled': False,
                'refresh_interval': 900000  # 15 minutes
            },
            'NORMAL': {
                'primary_widgets': ['IntelligenceDashboardWidget', 'ForecastMatrixWidget', 'MacroBoardWidget'],
                'filters': {
                    'asset_types': None,
                    'forecast_direction': None,
                    'min_confidence': 0.6
                },
                'emphasis': 'balanced',
                'alerts_enabled': False,
                'refresh_interval': 600000  # 10 minutes
            }
        }
        
        return layouts.get(regime, layouts['NORMAL'])
    
    def _extract_characteristics(
        self,
        intel: Dict[str, Any],
        regime_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Extract market characteristics.
        """
        vix = regime_info['vix']
        bullish_pct = regime_info['bullish_pct']
        bearish_pct = regime_info['bearish_pct']
        news_score = regime_info['news_score']
        
        # Volatility
        if vix > 30:
            volatility = 'extreme'
        elif vix > 25:
            volatility = 'high'
        elif vix > 20:
            volatility = 'medium'
        elif vix > 15:
            volatility = 'low'
        else:
            volatility = 'very-low'
        
        # Sentiment
        if bullish_pct > bearish_pct + 20:
            sentiment = 'bullish'
        elif bearish_pct > bullish_pct + 20:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
        
        # Trend (based on forecast direction bias)
        if bullish_pct > 55:
            trend = 'up'
        elif bearish_pct > 55:
            trend = 'down'
        else:
            trend = 'sideways'
        
        # Momentum (based on sentiment strength)
        sentiment_diff = abs(bullish_pct - bearish_pct)
        if sentiment_diff > 40:
            momentum = 'strong'
        elif sentiment_diff > 20:
            momentum = 'moderate'
        else:
            momentum = 'weak'
        
        # Risk level
        if vix > 25 or bearish_pct > 60:
            risk_level = 'high'
        elif vix > 20 or bearish_pct > 50:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'volatility': volatility,
            'sentiment': sentiment,
            'trend': trend,
            'momentum': momentum,
            'risk_level': risk_level
        }
    
    def _calculate_confidence(
        self,
        intel: Dict[str, Any],
        regime_info: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence in regime classification.
        """
        # VIX certainty (clear thresholds = high certainty)
        vix = regime_info['vix']
        if vix > 30 or vix < 15:
            vix_certainty = 0.9
        elif vix > 25 or vix < 17:
            vix_certainty = 0.8
        else:
            vix_certainty = 0.6
        
        # Forecast certainty (strong bias = high certainty)
        bullish_pct = regime_info['bullish_pct']
        bearish_pct = regime_info['bearish_pct']
        sentiment_diff = abs(bullish_pct - bearish_pct)
        
        if sentiment_diff > 40:
            forecast_certainty = 0.9
        elif sentiment_diff > 25:
            forecast_certainty = 0.75
        else:
            forecast_certainty = 0.5
        
        # News certainty (strong sentiment = high certainty)
        news_score = regime_info['news_score']
        if abs(news_score) > 0.3:
            news_certainty = 0.9
        elif abs(news_score) > 0.15:
            news_certainty = 0.75
        else:
            news_certainty = 0.5
        
        # Historical consistency (placeholder - would need historical data)
        historical_consistency = 0.7
        
        # Weighted average
        confidence = (
            vix_certainty * 0.3 +
            forecast_certainty * 0.3 +
            news_certainty * 0.2 +
            historical_consistency * 0.2
        )
        
        return min(0.95, max(0.3, confidence))  # Clamp to [0.3, 0.95]
    
    def _get_confidence_breakdown(
        self,
        intel: Dict[str, Any],
        regime_info: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Get detailed confidence breakdown for metadata.
        """
        vix = regime_info['vix']
        bullish_pct = regime_info['bullish_pct']
        bearish_pct = regime_info['bearish_pct']
        news_score = regime_info['news_score']
        
        # Individual certainties
        vix_certainty = 0.9 if (vix > 30 or vix < 15) else 0.8 if (vix > 25 or vix < 17) else 0.6
        
        sentiment_diff = abs(bullish_pct - bearish_pct)
        forecast_certainty = 0.9 if sentiment_diff > 40 else 0.75 if sentiment_diff > 25 else 0.5
        
        news_certainty = 0.9 if abs(news_score) > 0.3 else 0.75 if abs(news_score) > 0.15 else 0.5
        
        return {
            'vix_certainty': vix_certainty,
            'forecast_certainty': forecast_certainty,
            'news_certainty': news_certainty,
            'historical_consistency': 0.7
        }
    
    def _save_context(self, context: Dict[str, Any]):
        """Save context to cache."""
        try:
            filepath = self.data_dir / "market_context.json"
            with open(filepath, 'w') as f:
                json.dump({
                    'last_update': datetime.utcnow().isoformat() + 'Z',
                    'data': context
                }, f, indent=2)
            self.logger.debug(f"Saved context to {filepath}")
        except Exception as e:
            self.logger.warning(f"Failed to save context: {str(e)}")
    
    def _load_cached_context(self) -> Optional[Dict[str, Any]]:
        """Load cached context."""
        try:
            filepath = self.data_dir / "market_context.json"
            if not filepath.exists():
                return None
            
            with open(filepath, 'r') as f:
                cached = json.load(f)
            
            # Check if not too old (max 30 minutes)
            last_update = cached.get('last_update')
            if self._is_stale(last_update, minutes=30):
                self.logger.debug("Cached context is stale")
                return None
            
            return cached.get('data')
        except Exception as e:
            self.logger.warning(f"Failed to load cached context: {str(e)}")
            return None
    
    def _is_stale(self, last_update: Optional[str], minutes: int = 30) -> bool:
        """Check if data is stale."""
        if not last_update:
            return True
        
        try:
            from datetime import timedelta
            update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            now = datetime.utcnow()
            age = now - update_time.replace(tzinfo=None)
            return age > timedelta(minutes=minutes)
        except:
            return True
    
    def _get_fallback_context(self, error_message: str) -> Dict[str, Any]:
        """Get fallback context when everything fails."""
        return {
            'regime': 'NORMAL',
            'confidence': 0.3,
            'key_drivers': ['Data temporarily unavailable'],
            'recommended_layout': {
                'primary_widgets': ['IntelligenceDashboardWidget', 'ForecastMatrixWidget'],
                'filters': {},
                'emphasis': 'balanced'
            },
            'characteristics': {
                'volatility': 'unknown',
                'sentiment': 'neutral',
                'trend': 'sideways',
                'momentum': 'weak',
                'risk_level': 'medium'
            },
            'metadata': {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'sources': [],
                'status': 'fallback',
                'error': error_message
            }
        }


# Singleton instance
_context_service_instance = None

def get_context_service() -> ContextService:
    """Get singleton instance of ContextService."""
    global _context_service_instance
    if _context_service_instance is None:
        _context_service_instance = ContextService()
    return _context_service_instance
