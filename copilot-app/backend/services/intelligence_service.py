"""
Intelligence Service - Aggregate data and generate LLM insights
File: backend/services/intelligence_service.py
Task: FC-INT-020 - ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

try:
    from g4f.client import Client
    G4F_AVAILABLE = True
except ImportError:
    G4F_AVAILABLE = False
    logging.warning("G4F not available - LLM insights will be simulated")

from storage.base import load_forecasts, load_json
from services.cache_layer import load_or_compute

logger = logging.getLogger(__name__)


class IntelligenceService:
    """
    Intelligence Service that aggregates all data sources and generates
    contextual insights using G4F LLM.
    
    Combines:
    - Forecasts (ML + LLM predictions)
    - Macro indicators (CPI, VIX, yields, unemployment)
    - News sentiment
    - Stock prices and volatility
    
    Generates:
    - Market regime analysis
    - Top opportunities identification
    - Key risks assessment
    - Contextual explanations
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if G4F_AVAILABLE:
            self.g4f_client = Client()
        else:
            self.g4f_client = None
        
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
    
    async def get_market_snapshot_intelligence(self) -> Dict[str, Any]:
        """
        Get comprehensive market intelligence snapshot.
        
        Returns:
            {
                'data': {
                    'forecasts': [...],
                    'macro': {...},
                    'news': [...],
                    'stocks': {...}
                },
                'insights': {
                    'market_regime': {...},
                    'opportunities': [...],
                    'risks': [...],
                    'summary': str
                },
                'metadata': {
                    'generated_at': str,
                    'freshness': {...}
                }
            }
        """
        self.logger.info("Generating market intelligence snapshot...")
        
        try:
            # Step 1: Aggregate all data sources in parallel
            data = await self._aggregate_data_sources()
            
            # Step 2: Generate LLM insights
            insights = await self._generate_llm_insights(data)
            
            # Step 3: Package response
            response = {
                'data': data,
                'insights': insights,
                'metadata': {
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'freshness': self._calculate_freshness(data),
                    'llm_model': 'gpt-4' if G4F_AVAILABLE else 'simulated',
                    'data_sources': list(data.keys())
                }
            }
            
            # Step 4: Cache result
            self._save_intelligence_snapshot(response)
            
            self.logger.info("Intelligence snapshot generated successfully")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate intelligence snapshot: {str(e)}", exc_info=True)
            # Return cached version if available
            cached = self._load_cached_intelligence()
            if cached:
                self.logger.info("Returning cached intelligence snapshot")
                return cached
            
            # Fallback to minimal response
            return self._get_fallback_response(str(e))
    
    async def _aggregate_data_sources(self) -> Dict[str, Any]:
        """
        Aggregate data from all sources.
        """
        self.logger.debug("Aggregating data sources...")
        
        data = {}
        
        # Load forecasts
        try:
            forecasts_data = load_forecasts()
            if forecasts_data and forecasts_data.get('data'):
                data['forecasts'] = forecasts_data['data'].get('rows', [])
                data['forecasts_metadata'] = {
                    'last_update': forecasts_data.get('last_update'),
                    'count': len(data['forecasts'])
                }
            else:
                data['forecasts'] = []
                data['forecasts_metadata'] = {'last_update': None, 'count': 0}
        except Exception as e:
            self.logger.warning(f"Failed to load forecasts: {str(e)}")
            data['forecasts'] = []
            data['forecasts_metadata'] = {'error': str(e)}
        
        # Load macro indicators
        try:
            macro_data = load_json('macro_snapshot.json')
            if macro_data and macro_data.get('data'):
                data['macro'] = macro_data['data']
                data['macro_metadata'] = {
                    'last_update': macro_data.get('last_update'),
                    'indicators': list(macro_data['data'].keys()) if isinstance(macro_data['data'], dict) else []
                }
            else:
                data['macro'] = self._get_default_macro()
                data['macro_metadata'] = {'last_update': None, 'source': 'default'}
        except Exception as e:
            self.logger.warning(f"Failed to load macro data: {str(e)}")
            data['macro'] = self._get_default_macro()
            data['macro_metadata'] = {'error': str(e)}
        
        # Load news sentiment
        try:
            news_data = load_json('news_feed.json')
            if news_data and news_data.get('data'):
                news_articles = news_data['data'].get('articles', [])
                data['news'] = news_articles[:10]  # Top 10 most recent
                data['news_metadata'] = {
                    'last_update': news_data.get('last_update'),
                    'count': len(news_articles),
                    'avg_sentiment': self._calculate_avg_sentiment(news_articles)
                }
            else:
                data['news'] = []
                data['news_metadata'] = {'last_update': None, 'count': 0}
        except Exception as e:
            self.logger.warning(f"Failed to load news data: {str(e)}")
            data['news'] = []
            data['news_metadata'] = {'error': str(e)}
        
        # Calculate derived metrics
        data['derived'] = self._calculate_derived_metrics(data)
        
        return data
    
    def _get_default_macro(self) -> Dict[str, Any]:
        """Return default macro values as fallback."""
        return {
            'VIX': 20.0,
            'CPI': 3.0,
            'T10Y2Y': 0.5,
            'UNRATE': 4.0
        }
    
    def _calculate_avg_sentiment(self, articles: List[Dict]) -> float:
        """Calculate average sentiment from news articles."""
        if not articles:
            return 0.0
        
        sentiments = [
            article.get('sentiment_score', 0) 
            for article in articles 
            if 'sentiment_score' in article
        ]
        
        if not sentiments:
            return 0.0
        
        return sum(sentiments) / len(sentiments)
    
    def _calculate_derived_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics from aggregated data."""
        derived = {}
        
        # Forecast metrics
        forecasts = data.get('forecasts', [])
        if forecasts:
            bullish = sum(1 for f in forecasts if f.get('direction') == 'up')
            bearish = sum(1 for f in forecasts if f.get('direction') == 'down')
            neutral = sum(1 for f in forecasts if f.get('direction') == 'flat')
            total = len(forecasts)
            
            derived['forecast_sentiment'] = {
                'bullish_pct': (bullish / total * 100) if total > 0 else 0,
                'bearish_pct': (bearish / total * 100) if total > 0 else 0,
                'neutral_pct': (neutral / total * 100) if total > 0 else 0,
                'bias': 'bullish' if bullish > bearish else 'bearish' if bearish > bullish else 'neutral'
            }
            
            # Average confidence
            confidences = [f.get('confidence', 0) for f in forecasts if 'confidence' in f]
            derived['avg_confidence'] = (sum(confidences) / len(confidences)) if confidences else 0
        
        # Macro regime
        macro = data.get('macro', {})
        vix = macro.get('VIX', 20)
        
        if vix > 30:
            regime = 'HIGH_VOLATILITY'
        elif vix > 20:
            regime = 'ELEVATED_RISK'
        elif vix < 15:
            regime = 'LOW_VOLATILITY'
        else:
            regime = 'NORMAL'
        
        derived['market_regime'] = {
            'regime': regime,
            'vix_level': vix,
            'risk_assessment': self._assess_risk_level(vix)
        }
        
        # News sentiment
        news_meta = data.get('news_metadata', {})
        avg_sentiment = news_meta.get('avg_sentiment', 0)
        
        derived['news_sentiment'] = {
            'score': avg_sentiment,
            'bias': 'positive' if avg_sentiment > 0.1 else 'negative' if avg_sentiment < -0.1 else 'neutral',
            'strength': 'strong' if abs(avg_sentiment) > 0.3 else 'moderate' if abs(avg_sentiment) > 0.15 else 'weak'
        }
        
        return derived
    
    def _assess_risk_level(self, vix: float) -> str:
        """Assess risk level based on VIX."""
        if vix > 30:
            return 'HIGH'
        elif vix > 20:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    async def _generate_llm_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate LLM insights from aggregated data.
        """
        self.logger.debug("Generating LLM insights...")
        
        if not G4F_AVAILABLE or not self.g4f_client:
            self.logger.warning("G4F not available, using simulated insights")
            return self._generate_simulated_insights(data)
        
        try:
            # Build prompt
            prompt = self._build_analysis_prompt(data)
            
            # Call G4F LLM
            response = self.g4f_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse LLM response
            llm_text = response.choices[0].message.content
            insights = self._parse_llm_response(llm_text, data)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {str(e)}", exc_info=True)
            return self._generate_simulated_insights(data)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM."""
        return """You are an expert financial analyst AI assistant for Finance Copilot.

Your role is to analyze market data (forecasts, macro indicators, news, stocks) and provide:
1. Clear market regime assessment
2. Top opportunities identification with reasoning
3. Key risks identification with reasoning
4. Concise actionable summary

Always be:
- Concise (2-3 sentences per insight)
- Specific (mention tickers, levels, percentages)
- Actionable (what should investors consider)
- Balanced (mention both opportunities and risks)

Output format should be JSON-parseable with keys:
- market_regime: {regime: str, explanation: str, confidence: float}
- opportunities: [{ticker: str, reasoning: str, confidence: float}, ...]
- risks: [{type: str, description: str, severity: str}, ...]
- summary: str
"""
    
    def _build_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Build analysis prompt for LLM."""
        derived = data.get('derived', {})
        forecasts = data.get('forecasts', [])[:5]  # Top 5 forecasts
        macro = data.get('macro', {})
        
        prompt = f"""Analyze the current market situation based on this data:

MARKET REGIME:
- VIX: {macro.get('VIX', 'N/A')}
- Regime: {derived.get('market_regime', {}).get('regime', 'UNKNOWN')}

FORECASTS SENTIMENT:
- {derived.get('forecast_sentiment', {}).get('bullish_pct', 0):.1f}% Bullish
- {derived.get('forecast_sentiment', {}).get('bearish_pct', 0):.1f}% Bearish
- Avg Confidence: {derived.get('avg_confidence', 0):.2f}

TOP FORECASTS:
{self._format_forecasts_for_prompt(forecasts)}

NEWS SENTIMENT:
- Score: {derived.get('news_sentiment', {}).get('score', 0):.2f}
- Bias: {derived.get('news_sentiment', {}).get('bias', 'neutral')}

Provide your analysis in JSON format."""
        
        return prompt
    
    def _format_forecasts_for_prompt(self, forecasts: List[Dict]) -> str:
        """Format forecasts for LLM prompt."""
        if not forecasts:
            return "No forecasts available"
        
        lines = []
        for f in forecasts:
            ticker = f.get('ticker', f.get('symbol', 'N/A'))
            direction = f.get('direction', 'flat')
            confidence = f.get('confidence', 0)
            lines.append(f"- {ticker}: {direction.upper()} (conf: {confidence:.2f})")
        
        return "\n".join(lines)
    
    def _parse_llm_response(self, llm_text: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into structured insights."""
        try:
            # Try to parse as JSON
            insights = json.loads(llm_text)
            return insights
        except json.JSONDecodeError:
            # Fallback: extract insights from text
            self.logger.warning("Could not parse LLM response as JSON, using text extraction")
            return self._extract_insights_from_text(llm_text, data)
    
    def _extract_insights_from_text(self, text: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from LLM text response."""
        # Basic extraction (can be improved with more sophisticated parsing)
        return {
            'market_regime': {
                'regime': data.get('derived', {}).get('market_regime', {}).get('regime', 'UNKNOWN'),
                'explanation': text[:200],  # First 200 chars
                'confidence': 0.7
            },
            'opportunities': [],
            'risks': [],
            'summary': text[:300]  # First 300 chars as summary
        }
    
    def _generate_simulated_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate simulated insights when G4F is not available.
        """
        derived = data.get('derived', {})
        regime_info = derived.get('market_regime', {})
        forecast_sentiment = derived.get('forecast_sentiment', {})
        
        # Market regime
        regime = regime_info.get('regime', 'UNKNOWN')
        vix = regime_info.get('vix_level', 20)
        
        regime_explanations = {
            'HIGH_VOLATILITY': f"Market experiencing high volatility (VIX: {vix:.1f}). Risk-off sentiment prevails. Consider defensive positioning.",
            'ELEVATED_RISK': f"Market showing elevated risk (VIX: {vix:.1f}). Caution warranted, monitor closely.",
            'NORMAL': f"Market operating in normal volatility range (VIX: {vix:.1f}). Balanced approach recommended.",
            'LOW_VOLATILITY': f"Market calm with low volatility (VIX: {vix:.1f}). Risk-on environment favorable."
        }
        
        # Opportunities
        forecasts = data.get('forecasts', [])
        bullish_forecasts = [
            f for f in forecasts 
            if f.get('direction') == 'up' and f.get('confidence', 0) > 0.6
        ]
        bullish_forecasts.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        opportunities = []
        for f in bullish_forecasts[:3]:
            ticker = f.get('ticker', f.get('symbol', 'N/A'))
            confidence = f.get('confidence', 0)
            opportunities.append({
                'ticker': ticker,
                'reasoning': f"Strong technical signals with {confidence:.0%} confidence. Positive momentum detected.",
                'confidence': confidence
            })
        
        # Risks
        risks = []
        
        if vix > 25:
            risks.append({
                'type': 'VOLATILITY',
                'description': f"Elevated volatility (VIX: {vix:.1f}) increases market uncertainty",
                'severity': 'HIGH' if vix > 30 else 'MEDIUM'
            })
        
        bearish_pct = forecast_sentiment.get('bearish_pct', 0)
        if bearish_pct > 40:
            risks.append({
                'type': 'SENTIMENT',
                'description': f"Negative forecast bias ({bearish_pct:.0f}% bearish predictions)",
                'severity': 'MEDIUM'
            })
        
        news_sentiment = derived.get('news_sentiment', {})
        if news_sentiment.get('bias') == 'negative' and news_sentiment.get('strength') != 'weak':
            risks.append({
                'type': 'NEWS',
                'description': "Negative news sentiment detected across markets",
                'severity': 'MEDIUM'
            })
        
        # Summary
        bullish_pct = forecast_sentiment.get('bullish_pct', 0)
        bias = forecast_sentiment.get('bias', 'neutral')
        
        summary_parts = [
            regime_explanations.get(regime, "Market regime unclear."),
            f"Forecast sentiment is {bias} ({bullish_pct:.0f}% bullish, {bearish_pct:.0f}% bearish).",
        ]
        
        if opportunities:
            summary_parts.append(f"Top opportunities: {', '.join([o['ticker'] for o in opportunities[:3]])}.")
        
        if risks:
            summary_parts.append(f"Key risks: {', '.join([r['type'] for r in risks])}.")
        
        return {
            'market_regime': {
                'regime': regime,
                'explanation': regime_explanations.get(regime, "Unknown regime"),
                'confidence': 0.75
            },
            'opportunities': opportunities,
            'risks': risks,
            'summary': " ".join(summary_parts)
        }
    
    def _calculate_freshness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate data freshness metrics."""
        freshness = {}
        
        # Forecasts freshness
        forecasts_meta = data.get('forecasts_metadata', {})
        freshness['forecasts'] = {
            'last_update': forecasts_meta.get('last_update'),
            'count': forecasts_meta.get('count', 0),
            'is_stale': self._is_stale(forecasts_meta.get('last_update'), hours=24)
        }
        
        # Macro freshness
        macro_meta = data.get('macro_metadata', {})
        freshness['macro'] = {
            'last_update': macro_meta.get('last_update'),
            'is_stale': self._is_stale(macro_meta.get('last_update'), hours=24)
        }
        
        # News freshness
        news_meta = data.get('news_metadata', {})
        freshness['news'] = {
            'last_update': news_meta.get('last_update'),
            'count': news_meta.get('count', 0),
            'is_stale': self._is_stale(news_meta.get('last_update'), hours=1)
        }
        
        return freshness
    
    def _is_stale(self, last_update: Optional[str], hours: int = 24) -> bool:
        """Check if data is stale."""
        if not last_update:
            return True
        
        try:
            from datetime import timedelta
            update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            now = datetime.utcnow()
            age = now - update_time.replace(tzinfo=None)
            return age > timedelta(hours=hours)
        except:
            return True
    
    def _save_intelligence_snapshot(self, snapshot: Dict[str, Any]):
        """Save intelligence snapshot to cache."""
        try:
            filepath = self.data_dir / "intelligence_snapshot.json"
            with open(filepath, 'w') as f:
                json.dump({
                    'last_update': datetime.utcnow().isoformat() + 'Z',
                    'data': snapshot
                }, f, indent=2)
            self.logger.debug(f"Saved intelligence snapshot to {filepath}")
        except Exception as e:
            self.logger.warning(f"Failed to save intelligence snapshot: {str(e)}")
    
    def _load_cached_intelligence(self) -> Optional[Dict[str, Any]]:
        """Load cached intelligence snapshot."""
        try:
            filepath = self.data_dir / "intelligence_snapshot.json"
            if not filepath.exists():
                return None
            
            with open(filepath, 'r') as f:
                cached = json.load(f)
            
            # Check if not too old (max 1 hour)
            last_update = cached.get('last_update')
            if self._is_stale(last_update, hours=1):
                self.logger.debug("Cached intelligence is stale")
                return None
            
            return cached.get('data')
        except Exception as e:
            self.logger.warning(f"Failed to load cached intelligence: {str(e)}")
            return None
    
    def _get_fallback_response(self, error_message: str) -> Dict[str, Any]:
        """Get fallback response when everything fails."""
        return {
            'data': {
                'forecasts': [],
                'macro': self._get_default_macro(),
                'news': [],
                'derived': {}
            },
            'insights': {
                'market_regime': {
                    'regime': 'UNKNOWN',
                    'explanation': 'Unable to assess market regime due to data unavailability',
                    'confidence': 0.0
                },
                'opportunities': [],
                'risks': [{
                    'type': 'SYSTEM',
                    'description': f'Data generation error: {error_message}',
                    'severity': 'HIGH'
                }],
                'summary': 'Intelligence service temporarily unavailable. Using fallback data.'
            },
            'metadata': {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'freshness': {},
                'llm_model': 'none',
                'status': 'fallback',
                'error': error_message
            }
        }


# Singleton instance
_intelligence_service_instance = None

def get_intelligence_service() -> IntelligenceService:
    """Get singleton instance of IntelligenceService."""
    global _intelligence_service_instance
    if _intelligence_service_instance is None:
        _intelligence_service_instance = IntelligenceService()
    return _intelligence_service_instance
