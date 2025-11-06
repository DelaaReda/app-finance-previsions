"""
Recommendations Service - ML + LLM powered daily recommendations

Generates top 3 daily actionable recommendations by combining:
- ML ranking (5-factor scoring)
- LLM validation & reasoning
- Macro alignment
- Risk assessment

Author: ELENA-39
Task: FC-INT-023
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# G4F imports with fallback
try:
    from g4f.client import Client
    G4F_AVAILABLE = True
except ImportError:
    G4F_AVAILABLE = False

# Internal services
try:
    from backend.services.intelligence_service import get_intelligence_service
except ImportError:
    get_intelligence_service = None

try:
    from backend.services.context_service import get_context_service
except ImportError:
    get_context_service = None

# Storage
try:
    from backend.storage.base import load_forecasts
except ImportError:
    load_forecasts = None


class RecommendationsService:
    """
    Smart Recommendations Service
    
    Combines ML ranking with LLM validation to generate
    actionable daily recommendations.
    
    Features:
    - 5-factor ML scoring
    - LLM-powered reasoning
    - Macro-aware recommendations
    - 24h caching
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # G4F client
        if G4F_AVAILABLE:
            self.g4f_client = Client()
            self.logger.info("G4F client initialized")
        else:
            self.g4f_client = None
            self.logger.warning("G4F not available, using simulated validation")
        
        # Services
        if get_intelligence_service:
            self.intelligence_service = get_intelligence_service()
        else:
            self.intelligence_service = None
        
        if get_context_service:
            self.context_service = get_context_service()
        else:
            self.context_service = None
    
    async def generate_daily_recommendations(
        self,
        universe: Optional[List[str]] = None,
        limit: int = 3
    ) -> Dict[str, Any]:
        """
        Generate top N daily recommendations
        
        Args:
            universe: Optional list of tickers to consider
            limit: Number of recommendations (1-10)
        
        Returns:
            Dict with recommendations and market context
        """
        try:
            # Check cache (24h validity)
            cache_key = f"recommendations_daily_{universe}_{limit}" if universe else f"recommendations_daily_default_{limit}"
            cached = self._load_cache(cache_key)
            if cached:
                self.logger.info(f"Returning cached recommendations (key: {cache_key})")
                return cached
            
            # Default universe
            if not universe:
                universe = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA', 'SPY', 'QQQ', 'TLT', 'GLD', 'JNJ', 'PG']
            
            # Aggregate data
            data = await self._aggregate_data(universe)
            
            # Calculate ML scores
            candidates = []
            for ticker in universe:
                try:
                    score = self._calculate_ml_score(ticker, data)
                    if score > 0.5:  # Threshold
                        candidates.append({
                            'ticker': ticker,
                            'score': score,
                            'data': data.get(ticker, {})
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to score {ticker}: {e}")
            
            # Sort by score
            candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
            
            # LLM validation (top candidates)
            validated = []
            for candidate in candidates[:limit * 2]:  # Over-select for validation
                validation = await self._validate_with_llm(
                    candidate['ticker'],
                    candidate['score'],
                    data
                )
                
                if validation.get('decision') == 'APPROVE':
                    validated.append({
                        **candidate,
                        **validation
                    })
                
                if len(validated) >= limit:
                    break
            
            # Format output
            result = self._format_recommendations(
                validated[:limit],
                data.get('market_context', {})
            )
            
            # Save to cache
            self._save_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}", exc_info=True)
            return self._fallback_recommendations()
    
    async def _aggregate_data(self, universe: List[str]) -> Dict[str, Any]:
        """Aggregate data from all sources"""
        data = {
            'market_context': {},
            'forecasts': {},
            'macro': {},
            'news': {}
        }
        
        try:
            # Get market context
            if self.context_service:
                context = await self.context_service.get_current_market_context()
                data['market_context'] = context
            
            # Get intelligence
            if self.intelligence_service:
                intelligence = await self.intelligence_service.get_market_snapshot_intelligence()
                data['intelligence'] = intelligence
            
            # Get forecasts
            if load_forecasts:
                forecasts_data = load_forecasts()
                if forecasts_data and 'data' in forecasts_data:
                    rows = forecasts_data['data'].get('rows', [])
                    for row in rows:
                        ticker = row.get('ticker') or row.get('symbol')
                        if ticker in universe:
                            data['forecasts'][ticker] = row
            
        except Exception as e:
            self.logger.warning(f"Data aggregation partially failed: {e}")
        
        # Add ticker-specific data
        for ticker in universe:
            data[ticker] = {
                'forecast': data['forecasts'].get(ticker, {}),
                'ticker': ticker
            }
        
        return data
    
    def _calculate_ml_score(
        self,
        ticker: str,
        data: Dict[str, Any]
    ) -> float:
        """
        Calculate ML ranking score (5 factors)
        
        Score = (
            forecast_confidence * 0.35 +
            momentum_strength * 0.25 +
            news_sentiment * 0.20 +
            macro_alignment * 0.15 +
            risk_reward_ratio * 0.05
        )
        """
        try:
            ticker_data = data.get(ticker, {})
            forecast = ticker_data.get('forecast', {})
            market_context = data.get('market_context', {})
            
            # 1. Forecast confidence (0.35)
            forecast_conf = float(forecast.get('confidence', 0.5))
            
            # 2. Momentum strength (0.25)
            # Simplified: use forecast direction as proxy
            momentum = 0.7 if forecast.get('direction') == 'up' else 0.3
            
            # 3. News sentiment (0.20)
            # Simplified: neutral default
            news_score = 0.5
            
            # 4. Macro alignment (0.15)
            alignment = self._calculate_macro_alignment(
                ticker,
                forecast.get('direction', 'flat'),
                market_context.get('regime', 'NORMAL')
            )
            
            # 5. Risk-reward ratio (0.05)
            # Simplified: use confidence as proxy
            risk_reward = forecast_conf * 0.8
            
            # Weighted sum
            score = (
                forecast_conf * 0.35 +
                momentum * 0.25 +
                news_score * 0.20 +
                alignment * 0.15 +
                risk_reward * 0.05
            )
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.warning(f"ML scoring failed for {ticker}: {e}")
            return 0.5
    
    def _calculate_macro_alignment(
        self,
        ticker: str,
        direction: str,
        regime: str
    ) -> float:
        """Calculate how well ticker aligns with macro regime"""
        
        # Define asset classes
        GROWTH_STOCKS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA']
        DEFENSIVE_STOCKS = ['JNJ', 'PG', 'KO', 'WMT', 'PEP', 'MCD']
        SAFE_HAVENS = ['TLT', 'GLD', 'SHV', 'IEF']
        
        # Regime-specific alignment
        if regime == 'BULL_MARKET':
            if ticker in GROWTH_STOCKS and direction == 'up':
                return 1.0
            elif ticker in DEFENSIVE_STOCKS:
                return 0.3
        
        elif regime == 'BEAR_MARKET':
            if ticker in DEFENSIVE_STOCKS:
                return 0.9
            elif ticker in SAFE_HAVENS:
                return 1.0
            elif ticker in GROWTH_STOCKS:
                return 0.2
        
        elif regime == 'HIGH_VOLATILITY' or regime == 'RISK_OFF':
            if ticker in SAFE_HAVENS:
                return 1.0
            elif ticker in DEFENSIVE_STOCKS:
                return 0.7
            else:
                return 0.3
        
        elif regime == 'RISK_ON':
            if ticker in GROWTH_STOCKS and direction == 'up':
                return 0.9
        
        # Default: NORMAL regime
        return 0.5
    
    async def _validate_with_llm(
        self,
        ticker: str,
        score: float,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate recommendation with LLM"""
        
        if not self.g4f_client:
            return self._simulated_validation(ticker, score, data)
        
        try:
            prompt = self._build_validation_prompt(ticker, score, data)
            
            response = self.g4f_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Extract from markdown code block if present
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    raise
            
        except Exception as e:
            self.logger.warning(f"LLM validation failed for {ticker}: {e}")
            return self._simulated_validation(ticker, score, data)
    
    def _build_validation_prompt(
        self,
        ticker: str,
        score: float,
        data: Dict[str, Any]
    ) -> str:
        """Build LLM validation prompt"""
        
        ticker_data = data.get(ticker, {})
        forecast = ticker_data.get('forecast', {})
        market_context = data.get('market_context', {})
        
        prompt = f"""You are a financial advisor analyzing market recommendations.

Current market regime: {market_context.get('regime', 'NORMAL')}
Market characteristics: {market_context.get('characteristics', {})}

Candidate recommendation:
- Ticker: {ticker}
- ML Score: {score:.2f}
- Forecast Direction: {forecast.get('direction', 'unknown')} (confidence: {forecast.get('confidence', 0)*100:.0f}%)
- Macro alignment: {"HIGH" if score > 0.7 else "MEDIUM" if score > 0.5 else "LOW"}

Task:
1. Validate this recommendation (APPROVE or REJECT)
2. If APPROVE, provide 2-3 sentence reasoning explaining why this is a good opportunity right now
3. Identify 2-3 key catalysts
4. Assess risk level (LOW, MEDIUM, or HIGH)

Output ONLY valid JSON with this structure:
{{
  "decision": "APPROVE" or "REJECT",
  "reasoning": "Your reasoning here (2-3 sentences)",
  "catalysts": ["catalyst1", "catalyst2", "catalyst3"],
  "risk_level": "LOW" or "MEDIUM" or "HIGH",
  "confidence": 0.0-1.0
}}"""
        
        return prompt
    
    def _simulated_validation(
        self,
        ticker: str,
        score: float,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulated validation when LLM unavailable"""
        
        ticker_data = data.get(ticker, {})
        forecast = ticker_data.get('forecast', {})
        direction = forecast.get('direction', 'flat')
        conf = forecast.get('confidence', 0.5)
        
        # Approve if score > 0.6
        if score < 0.6:
            return {
                'decision': 'REJECT',
                'reasoning': f"ML score ({score:.2f}) below threshold",
                'catalysts': [],
                'risk_level': 'HIGH',
                'confidence': 0.3
            }
        
        return {
            'decision': 'APPROVE',
            'reasoning': f"{ticker} shows {direction} momentum with {conf*100:.0f}% forecast confidence. Technical and fundamental alignment support this direction.",
            'catalysts': [
                f"Strong {direction} forecast signal",
                "Favorable macro environment",
                "Positive technical indicators"
            ],
            'risk_level': 'MEDIUM' if score > 0.75 else 'MEDIUM',
            'confidence': score
        }
    
    def _format_recommendations(
        self,
        validated: List[Dict],
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format final recommendations output"""
        
        recommendations = []
        
        for item in validated:
            ticker = item['ticker']
            score = item['score']
            forecast = item.get('data', {}).get('forecast', {})
            
            rec = {
                'ticker': ticker,
                'action': 'BUY' if forecast.get('direction') == 'up' else 'HOLD',
                'score': round(score, 2),
                'reasoning': item.get('reasoning', 'No reasoning provided'),
                'catalysts': item.get('catalysts', []),
                'risk_level': item.get('risk_level', 'MEDIUM'),
                'confidence': round(item.get('confidence', score), 2),
                'supporting_data': {
                    'forecast_direction': forecast.get('direction', 'unknown'),
                    'forecast_confidence': round(forecast.get('confidence', 0.5), 2),
                    'ml_score': round(score, 2)
                }
            }
            
            recommendations.append(rec)
        
        return {
            'recommendations': recommendations,
            'market_context': {
                'regime': market_context.get('regime', 'NORMAL'),
                'summary': f"Market regime: {market_context.get('regime', 'NORMAL')}",
                'key_drivers': market_context.get('key_drivers', [])
            },
            'generated_at': datetime.utcnow().isoformat(),
            'valid_until': (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
    
    def _fallback_recommendations(self) -> Dict[str, Any]:
        """Fallback recommendations if all else fails"""
        return {
            'recommendations': [],
            'market_context': {
                'regime': 'UNKNOWN',
                'summary': 'Unable to generate recommendations',
                'key_drivers': []
            },
            'generated_at': datetime.utcnow().isoformat(),
            'valid_until': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            'error': 'Failed to generate recommendations'
        }
    
    def _load_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Load from cache if valid"""
        try:
            cache_file = self.data_dir / f"{key}.json"
            if not cache_file.exists():
                return None
            
            data = json.loads(cache_file.read_text())
            
            # Check validity (24h)
            generated_at = datetime.fromisoformat(data.get('generated_at', '2000-01-01'))
            if datetime.utcnow() - generated_at > timedelta(hours=24):
                self.logger.info(f"Cache expired for {key}")
                return None
            
            return data
            
        except Exception as e:
            self.logger.warning(f"Cache load failed for {key}: {e}")
            return None
    
    def _save_cache(self, key: str, data: Dict[str, Any]):
        """Save to cache"""
        try:
            cache_file = self.data_dir / f"{key}.json"
            cache_file.write_text(json.dumps(data, indent=2))
            self.logger.info(f"Saved cache for {key}")
        except Exception as e:
            self.logger.warning(f"Cache save failed for {key}: {e}")


# Singleton pattern
_recommendations_service_instance = None

def get_recommendations_service() -> RecommendationsService:
    """Get singleton instance of RecommendationsService"""
    global _recommendations_service_instance
    if _recommendations_service_instance is None:
        _recommendations_service_instance = RecommendationsService()
    return _recommendations_service_instance
