"""
Correlation Intelligence Service

Calculates asset correlations and uses LLM to explain WHY they exist
and HOW to act on them (hedging, diversification, arbitrage).

Author: ELENA-39
Task: FC-INT-025
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    from services.g4f_client import call_llm  # type: ignore
except Exception:
    call_llm = None  # type: ignore

# Internal services
try:
    from backend.services.intelligence_service import get_intelligence_service
except ImportError:
    get_intelligence_service = None

try:
    from backend.services.context_service import get_context_service
except ImportError:
    get_context_service = None


class CorrelationIntelligenceService:
    """
    Correlation Intelligence Service
    
    Combines quantitative correlation analysis with LLM explanations
    to provide actionable insights on asset relationships.
    
    Features:
    - Correlation matrix calculation
    - Interesting pairs identification
    - LLM-powered explanations
    - Actionable trading implications
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        if call_llm is None:
            self.logger.warning("Central g4f client unavailable, using simulated explanations")
        
        # Services
        if get_intelligence_service:
            self.intelligence_service = get_intelligence_service()
        else:
            self.intelligence_service = None
        
        if get_context_service:
            self.context_service = get_context_service()
        else:
            self.context_service = None
    
    async def generate_correlation_intelligence(
        self,
        universe: Optional[List[str]] = None,
        window: str = '30d',
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate correlation intelligence
        
        Args:
            universe: List of tickers to analyze
            window: Time window for correlation (e.g., '30d', '90d')
            threshold: Minimum correlation strength to analyze
        
        Returns:
            Dict with correlation matrix, pairs, and insights
        """
        try:
            # Check cache
            cache_key = f"correlation_intelligence_{universe}_{window}_{threshold}" if universe else f"correlation_intelligence_default_{window}_{threshold}"
            cached = self._load_cache(cache_key)
            if cached:
                self.logger.info(f"Returning cached correlation intelligence")
                return cached
            
            # Default universe
            if not universe:
                universe = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN', 'TSLA', 'SPY', 'QQQ']
            
            # Calculate correlation matrix
            matrix, tickers = self._calculate_correlation_matrix(universe, window)
            
            # Identify interesting pairs
            interesting_pairs = self._identify_interesting_pairs(matrix, tickers, threshold)
            
            # Get market context
            context = await self._get_market_context()
            
            # Analyze pairs with LLM
            analyzed_pairs = []
            for pair in interesting_pairs[:5]:  # Top 5 pairs
                analysis = await self._analyze_with_llm(
                    pair['ticker1'],
                    pair['ticker2'],
                    pair['correlation'],
                    context
                )
                analyzed_pairs.append({
                    **pair,
                    **analysis
                })
            
            # Generate summary
            summary = self._generate_summary(analyzed_pairs, context)
            
            # Format result
            result = {
                'matrix': matrix,
                'tickers': tickers,
                'interesting_pairs': analyzed_pairs,
                'summary': summary,
                'market_context': context,
                'generated_at': datetime.utcnow().isoformat(),
                'valid_until': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
            
            # Save to cache
            self._save_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate correlation intelligence: {e}", exc_info=True)
            return self._fallback_intelligence()
    
    def _calculate_correlation_matrix(
        self,
        universe: List[str],
        window: str
    ) -> Tuple[List[List[float]], List[str]]:
        """
        Calculate correlation matrix
        
        In production, this would use real price data.
        For now, we use simulated correlations based on asset classes.
        """
        try:
            # Asset classes for realistic correlations
            TECH_STOCKS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN']
            INDICES = ['SPY', 'QQQ']
            
            n = len(universe)
            matrix = [[0.0 for _ in range(n)] for _ in range(n)]
            
            for i, ticker1 in enumerate(universe):
                for j, ticker2 in enumerate(universe):
                    if i == j:
                        matrix[i][j] = 1.0  # Perfect self-correlation
                    elif i < j:
                        # Calculate based on asset class
                        if ticker1 in TECH_STOCKS and ticker2 in TECH_STOCKS:
                            corr = 0.75 + (hash(ticker1 + ticker2) % 20) / 100  # 0.75-0.95
                        elif ticker1 in INDICES or ticker2 in INDICES:
                            corr = 0.60 + (hash(ticker1 + ticker2) % 30) / 100  # 0.60-0.90
                        else:
                            corr = 0.30 + (hash(ticker1 + ticker2) % 40) / 100  # 0.30-0.70
                        
                        matrix[i][j] = round(corr, 2)
                        matrix[j][i] = round(corr, 2)  # Symmetric
            
            return matrix, universe
            
        except Exception as e:
            self.logger.warning(f"Correlation calculation failed: {e}")
            # Return identity matrix as fallback
            n = len(universe)
            return [[1.0 if i == j else 0.5 for j in range(n)] for i in range(n)], universe
    
    def _identify_interesting_pairs(
        self,
        matrix: List[List[float]],
        tickers: List[str],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Identify pairs with strong correlations"""
        pairs = []
        n = len(tickers)
        
        for i in range(n):
            for j in range(i + 1, n):
                corr = matrix[i][j]
                
                # Strong positive or negative correlation
                if abs(corr) >= threshold:
                    pairs.append({
                        'ticker1': tickers[i],
                        'ticker2': tickers[j],
                        'correlation': corr,
                        'strength': 'strong' if abs(corr) > 0.8 else 'moderate',
                        'direction': 'positive' if corr > 0 else 'negative'
                    })
        
        # Sort by absolute correlation (strongest first)
        pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        return pairs
    
    async def _get_market_context(self) -> Dict[str, Any]:
        """Get current market context"""
        try:
            if self.context_service:
                context = await self.context_service.get_current_market_context()
                return {
                    'regime': context.get('regime', 'NORMAL'),
                    'characteristics': context.get('characteristics', {})
                }
        except Exception as e:
            self.logger.warning(f"Failed to get market context: {e}")
        
        return {'regime': 'NORMAL', 'characteristics': {}}
    
    async def _analyze_with_llm(
        self,
        ticker1: str,
        ticker2: str,
        correlation: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze correlation with LLM"""
        
        if call_llm is None:
            return self._simulated_explanation(ticker1, ticker2, correlation, context)
        
        try:
            prompt = self._build_analysis_prompt(ticker1, ticker2, correlation, context)

            response = call_llm(
                messages=[{"role": "user", "content": prompt}],
                mode=os.getenv("LLM_CORRELATION_MODE") or os.getenv("LLM_MODEL_MODE"),
                timeout=60,
                category_preference="forecast",
            )
            if not response.get("ok"):
                raise RuntimeError(str(response.get("error") or "g4f_analysis_failed"))
            content = str(response.get("answer") or "")
            if not content.strip():
                raise RuntimeError("empty_response_content")
            
            # Parse JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Extract from markdown if present
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    raise
            
        except Exception as e:
            self.logger.warning(f"LLM analysis failed for {ticker1}-{ticker2}: {e}")
            return self._simulated_explanation(ticker1, ticker2, correlation, context)
    
    def _build_analysis_prompt(
        self,
        ticker1: str,
        ticker2: str,
        correlation: float,
        context: Dict[str, Any]
    ) -> str:
        """Build LLM analysis prompt"""
        
        regime = context.get('regime', 'NORMAL')
        strength = "strong" if abs(correlation) > 0.8 else "moderate"
        direction = "positive" if correlation > 0 else "negative"
        
        prompt = f"""You are analyzing asset correlations.

Pair: {ticker1} & {ticker2}
Correlation: {correlation:.2f} ({strength} {direction})
Market Regime: {regime}

Analyze this correlation and provide insights:

1. WHY does this correlation exist? (2-3 sentences explaining the fundamental drivers)
2. What are the KEY DRIVERS? (sector, macro factors, business overlap, etc.)
3. TRADING IMPLICATIONS: What should an investor do with this information?
   - Consider: hedging, diversification, arbitrage opportunities, or just monitoring

Output ONLY valid JSON with this structure:
{{
  "explanation": "Why this correlation exists (2-3 sentences)",
  "drivers": ["driver1", "driver2", "driver3"],
  "implications": ["implication1", "implication2"],
  "action_type": "HEDGE" or "DIVERSIFY" or "ARBITRAGE" or "MONITOR",
  "action_description": "Specific action to take"
}}"""
        
        return prompt
    
    def _simulated_explanation(
        self,
        ticker1: str,
        ticker2: str,
        correlation: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulated explanation when LLM unavailable"""
        
        # Determine asset classes
        TECH_STOCKS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN']
        
        ticker1_is_tech = ticker1 in TECH_STOCKS
        ticker2_is_tech = ticker2 in TECH_STOCKS
        
        if ticker1_is_tech and ticker2_is_tech:
            explanation = f"{ticker1} and {ticker2} both operate in the technology sector with significant overlap in cloud computing, AI, and enterprise software markets."
            drivers = ["Sector correlation (Big Tech)", "Similar macro exposure", "Cloud & AI tailwinds"]
            action_type = "DIVERSIFY"
            action_desc = "Consider adding non-tech exposure to reduce sector concentration risk."
        else:
            explanation = f"{ticker1} and {ticker2} show correlation driven by broader market movements and macro factors."
            drivers = ["Market beta", "Macro factors", "Investor sentiment"]
            action_type = "MONITOR"
            action_desc = "Monitor this relationship for changes that might signal shifts in market regime."
        
        return {
            'explanation': explanation,
            'drivers': drivers,
            'implications': [
                f"Both assets move together with {abs(correlation):.0%} correlation",
                "Portfolio diversification benefit may be limited",
                f"Consider {action_type.lower()}ing to manage risk"
            ],
            'action_type': action_type,
            'action_description': action_desc
        }
    
    def _generate_summary(
        self,
        pairs: List[Dict],
        context: Dict[str, Any]
    ) -> str:
        """Generate overall summary"""
        
        if not pairs:
            return "No strong correlations detected in current universe."
        
        strong_count = sum(1 for p in pairs if abs(p.get('correlation', 0)) > 0.8)
        positive_count = sum(1 for p in pairs if p.get('correlation', 0) > 0)
        
        regime = context.get('regime', 'NORMAL')
        
        summary = f"Detected {len(pairs)} significant correlations ({strong_count} strong). "
        summary += f"{positive_count} positive, {len(pairs) - positive_count} negative. "
        summary += f"Market regime: {regime}. "
        
        # Add regime-specific insight
        if regime in ['BULL_MARKET', 'RISK_ON']:
            summary += "In bullish conditions, tech correlations typically strengthen."
        elif regime in ['BEAR_MARKET', 'HIGH_VOLATILITY', 'RISK_OFF']:
            summary += "In risk-off conditions, correlations tend to spike as flight-to-safety dominates."
        else:
            summary += "In normal conditions, sector-specific factors drive correlations."
        
        return summary
    
    def _fallback_intelligence(self) -> Dict[str, Any]:
        """Fallback if all fails"""
        return {
            'matrix': [[1.0]],
            'tickers': [],
            'interesting_pairs': [],
            'summary': "Correlation analysis temporarily unavailable",
            'market_context': {'regime': 'UNKNOWN'},
            'generated_at': datetime.utcnow().isoformat(),
            'valid_until': (datetime.utcnow() + timedelta(minutes=10)).isoformat(),
            'error': 'Failed to generate correlation intelligence'
        }
    
    def _load_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Load from cache if valid"""
        try:
            cache_file = self.data_dir / f"{key}.json"
            if not cache_file.exists():
                return None
            
            data = json.loads(cache_file.read_text())
            
            # Check validity (1h)
            generated_at = datetime.fromisoformat(data.get('generated_at', '2000-01-01'))
            if datetime.utcnow() - generated_at > timedelta(hours=1):
                return None
            
            return data
            
        except Exception as e:
            self.logger.warning(f"Cache load failed: {e}")
            return None
    
    def _save_cache(self, key: str, data: Dict[str, Any]):
        """Save to cache"""
        try:
            cache_file = self.data_dir / f"{key}.json"
            cache_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            self.logger.warning(f"Cache save failed: {e}")


# Singleton
_correlation_intelligence_service_instance = None

def get_correlation_intelligence_service() -> CorrelationIntelligenceService:
    """Get singleton instance"""
    global _correlation_intelligence_service_instance
    if _correlation_intelligence_service_instance is None:
        _correlation_intelligence_service_instance = CorrelationIntelligenceService()
    return _correlation_intelligence_service_instance
