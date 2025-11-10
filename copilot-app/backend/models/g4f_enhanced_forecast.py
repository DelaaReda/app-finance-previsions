"""
G4F Forecast Enhancement Model - Enhance existing forecasts with LLM insights
Part of Finance Copilot Architecture Enhancement Initiative

Implements advanced forecasting model that uses G4F models to enhance existing ML forecasts 
with deeper market analysis and insights based on technical, fundamental, and macro factors
"""
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional
import json
import re
import pandas as pd
from pathlib import Path

try:
    from g4f.client import Client
    HAS_G4F = True
except ImportError:
    HAS_G4F = False
    print("Warning: g4f not installed. Install with 'pip install g4f' for LLM enhancement features.")

logger = logging.getLogger(__name__)

class G4FEnhancedForecast:
    """
    Enhanced forecasting model using G4F integrations to provide deeper analysis
    on top of existing ML forecasts with market context awareness
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if HAS_G4F:
            self.g4f_client = Client()
        else:
            self.g4f_client = None
        self.data_dir = Path(__file__).parent / ".." / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
    def enhance_forecast_with_llm(self, 
                                 ticker: str, 
                                 ml_forecast: Dict[str, Any], 
                                 market_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an existing ML forecast with G4F LLM analysis of market conditions
        
        Args:
            ticker: Stock ticker symbol
            ml_forecast: Original ML forecast data
            market_context: Current market conditions including news, macro, technicals
            
        Returns:
            Enhanced forecast with LLM insights
        """
        try:
            if not HAS_G4F or self.g4f_client is None:
                # If G4F is not available, return original forecast with note
                ml_forecast["enhancement_note"] = "G4F LLM enhancement unavailable - using original forecast"
                ml_forecast["enhanced_at"] = datetime.utcnow().isoformat()
                ml_forecast["enhancement_source"] = "ml_model_only"
                return ml_forecast
            
            # Prepare comprehensive market context for LLM analysis
            context_prompt = self._prepare_market_context(ticker, ml_forecast, market_context)
            
            # Generate LLM analysis to enhance forecast
            llm_response = self._call_g4f_for_analysis(context_prompt)
            
            # Parse and incorporate LLM insights
            enhanced_forecast = self._parse_llm_response_and_enhance(
                ml_forecast, 
                llm_response, 
                market_context
            )
            
            return enhanced_forecast
            
        except Exception as e:
            logger.error(f"Error enhancing forecast for {ticker}: {e}", exc_info=True)
            # Fall back to original forecast with error note
            ml_forecast["enhancement_note"] = f"LLM enhancement failed: {str(e)}"
            ml_forecast["enhanced_at"] = datetime.utcnow().isoformat()
            return ml_forecast
    
    def _prepare_market_context(self, 
                               ticker: str, 
                               ml_forecast: Dict[str, Any], 
                               market_context: Dict[str, Any]) -> str:
        """
        Prepare comprehensive market context for LLM analysis
        """
        return f"""
        Analyze and enhance the financial forecast for ticker: {ticker}
        
        ORIGINAL ML FORECAST:
        {json.dumps(ml_forecast, indent=2)}
        
        MARKET CONTEXT:
        - Current price: {market_context.get('current_price', 'N/A')}
        - Recent trend: {market_context.get('trend', 'N/A')} 
        - Volatility level: {market_context.get('volatility', 'N/A')}
        - News sentiment: {market_context.get('news_sentiment', 'N/A')}
        - Technical indicators: {market_context.get('tech_indicators', 'N/A')}
        - Macro environment: {market_context.get('macro_env', 'N/A')}
        - Sector performance: {market_context.get('sector_performance', 'N/A')}
        
        FORECAST ENHANCEMENT REQUEST:
        1. Validate and adjust the ML forecast direction based on the market context
        2. Adjust the confidence level considering all factors
        3. Provide risk assessment based on current conditions
        4. Add specific catalysts (positive/negative) that could affect the forecast
        5. Adjust expected return based on market conditions
        6. Suggest position sizing based on risk-reward
        
        FORMAT RESPONSE AS JSON:
        {{
            "direction_validated": "up/down/sideways",
            "confidence_adjusted": float (0-1),
            "expected_return_adjusted": float,
            "risk_factors": ["factor1", "factor2", ...],
            "catalysts_positive": ["catalyst1", ...],
            "catalysts_negative": ["catalyst1", ...],
            "position_sizing_suggestion": "conservative/moderate/aggressive",
            "timeframe_validated": "short/mid/long",
            "explanation": "Detailed reasoning for adjustments"
        }}
        """
    
    def _call_g4f_for_analysis(self, prompt: str) -> str:
        """
        Call G4F client to analyze market context and enhance forecast
        """
        try:
            if not HAS_G4F or self.g4f_client is None:
                return json.dumps({
                    "direction_validated": "neutral",
                    "confidence_adjusted": 0.5,
                    "expected_return_adjusted": 0.0,
                    "risk_factors": [],
                    "catalysts_positive": [],
                    "catalysts_negative": [],
                    "position_sizing_suggestion": "conservative",
                    "timeframe_validated": "short",
                    "explanation": "G4F client not available - using ML forecast as-is"
                })
            
            response = self.g4f_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"G4F call failed: {e}")
            return json.dumps({
                "direction_validated": "neutral",
                "confidence_adjusted": 0.5,
                "expected_return_adjusted": 0.0,
                "risk_factors": [],
                "catalysts_positive": [],
                "catalysts_negative": [],
                "position_sizing_suggestion": "conservative",
                "timeframe_validated": "short",
                "explanation": f"LLM analysis unavailable due to API error: {str(e)}"
            })
    
    def _parse_llm_response_and_enhance(self, 
                                      ml_forecast: Dict[str, Any], 
                                      llm_response: str, 
                                      market_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse LLM response and enhance forecast with insights
        """
        try:
            # Extract JSON from LLM response if wrapped in code blocks
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                llm_analysis = json.loads(json_str)
            else:
                # Try to parse whole response if it's JSON
                llm_analysis = json.loads(llm_response)
            
            # Merge LLM analysis with original forecast
            enhanced = dict(ml_forecast)
            enhanced.update({
                "direction": llm_analysis.get("direction_validated", ml_forecast.get("direction")),
                "confidence": llm_analysis.get("confidence_adjusted", ml_forecast.get("confidence")),
                "expected_return": llm_analysis.get("expected_return_adjusted", 
                                                   ml_forecast.get("expected_return", 0.0)),
                "risk_factors": list(set(llm_analysis.get("risk_factors", []) + 
                                        ml_forecast.get("risk_factors", []))),
                "catalysts_positive": llm_analysis.get("catalysts_positive", []),
                "catalysts_negative": llm_analysis.get("catalysts_negative", []),
                "position_sizing": llm_analysis.get("position_sizing_suggestion", "moderate"),
                "validated_horizon": llm_analysis.get("timeframe_validated", "medium"),
                "enhanced_explanation": llm_analysis.get("explanation", ""),
                "enhanced_at": datetime.utcnow().isoformat(),
                "enhancement_source": "g4f_analysis",
                "market_context_used": True,
                "llm_model_used": "gpt-3.5-turbo-g4f"
            })
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            # Return original forecast with error note
            ml_forecast["enhancement_error"] = str(e)
            ml_forecast["enhanced_at"] = datetime.utcnow().isoformat()
            return ml_forecast
    
    def run_batch_enhancement(self, 
                             forecasts: List[Dict[str, Any]], 
                             market_contexts: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance a batch of forecasts with G4F analysis
        
        Args:
            forecasts: List of forecast dictionaries to enhance
            market_contexts: Dictionary mapping tickers to market context
            
        Returns:
            List of enhanced forecasts
        """
        logger.info(f"Starting G4F enhancement for {len(forecasts)} forecasts...")
        
        enhanced_forecasts = []
        
        for forecast in forecasts:
            ticker = forecast.get("ticker", forecast.get("symbol", "UNKNOWN"))
            market_context = market_contexts.get(ticker, {})
            
            enhanced = self.enhance_forecast_with_llm(ticker, forecast, market_context)
            enhanced_forecasts.append(enhanced)
        
        logger.info(f"✅ Completed G4F enhancement for {len(enhanced_forecasts)} forecasts")
        return enhanced_forecasts
    
    def generate_enhanced_macro_forecast(self, 
                                       macro_indicators: Dict[str, float], 
                                       asset_class: str = "equity") -> Dict[str, Any]:
        """
        Generate enhanced forecast for an asset class based on macro indicators using G4F
        """
        try:
            if not HAS_G4F or self.g4f_client is None:
                # If G4F is not available, return fallback forecast
                return {
                    "asset_class": asset_class,
                    "direction": "neutral",
                    "confidence": 0.3,
                    "expected_return": 0.0,
                    "horizon": "medium",
                    "risk_factors": ["g4f_unavailable"],
                    "explanation": "G4F model not available - using fallback forecast",
                    "generated_at": datetime.utcnow().isoformat(),
                    "model_source": "fallback_macro_model"
                }
            
            # Prepare macro context for LLM analysis
            macro_context = self._prepare_macro_context(macro_indicators, asset_class)
            
            # Get LLM analysis of macro conditions
            llm_response = self._call_g4f_macro_analysis(macro_context)
            
            # Parse response and create forecast
            macro_forecast = self._parse_macro_llm_response(llm_response, asset_class)
            
            return macro_forecast
            
        except Exception as e:
            logger.error(f"Error generating enhanced macro forecast: {e}", exc_info=True)
            return {
                "asset_class": asset_class,
                "direction": "neutral",
                "confidence": 0.3,
                "expected_return": 0.0,
                "horizon": "medium",
                "risk_factors": ["macro_conditions_uncertain"],
                "explanation": f"Macro forecast unavailable due to error: {str(e)}",
                "generated_at": datetime.utcnow().isoformat(),
                "model_source": "fallback_macro_model"
            }
    
    def _prepare_macro_context(self, macro_indicators: Dict[str, float], asset_class: str) -> str:
        """
        Prepare macroeconomic context for LLM analysis
        """
        return f"""
        Analyze the macroeconomic environment and its impact on the {asset_class} asset class.
        
        MACRO INDICATORS:
        {json.dumps(macro_indicators, indent=2)}
        
        ANALYSIS REQUIREMENTS:
        1. Assess the overall market regime (bull/bear/sideways)
        2. Identify the primary drivers affecting the {asset_class} asset class
        3. Evaluate risk factors in the current environment
        4. Provide directional forecast based on macro conditions
        5. Estimate confidence level based on indicator alignment
        6. Suggest tactical adjustments based on regime
        
        FORMAT RESPONSE AS JSON:
        {{
            "regime": "bull/bear/lateral/high_stress/stable_growth",
            "primary_drivers": ["driver1", "driver2", ...],
            "risk_factors": ["risk1", "risk2", ...],
            "direction": "up/down/sideways",
            "confidence": float (0-1),
            "expected_return": float,
            "tactical_suggestions": ["suggestion1", ...],
            "horizon": "short/mid/long",
            "detailed_analysis": "Comprehensive analysis of conditions"
        }}
        """
    
    def _call_g4f_macro_analysis(self, prompt: str) -> str:
        """
        Call G4F for macro analysis
        """
        try:
            response = self.g4f_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1200
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"G4F macro analysis call failed: {e}")
            return json.dumps({
                "regime": "uncertain", 
                "primary_drivers": ["data_insufficient"],
                "risk_factors": ["model_error"],
                "direction": "neutral",
                "confidence": 0.2,
                "expected_return": 0.0,
                "tactical_suggestions": [],
                "horizon": "short",
                "detailed_analysis": f"Macro analysis unavailable due to API error: {str(e)}"
            })
    
    def _parse_macro_llm_response(self, llm_response: str, asset_class: str) -> Dict[str, Any]:
        """
        Parse LLM response and create macro forecast
        """
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
            else:
                parsed = json.loads(llm_response)
            
            return {
                "asset_class": asset_class,
                "regime": parsed.get("regime", "stable"),
                "direction": parsed.get("direction", "neutral"),
                "confidence": parsed.get("confidence", 0.5),
                "expected_return": parsed.get("expected_return", 0.0),
                "horizon": parsed.get("horizon", "medium"),
                "primary_drivers": parsed.get("primary_drivers", []),
                "risk_factors": parsed.get("risk_factors", []),
                "tactical_suggestions": parsed.get("tactical_suggestions", []),
                "analysis": parsed.get("detailed_analysis", ""),
                "generated_at": datetime.utcnow().isoformat(),
                "model_source": "g4f_macro_analysis"
            }
            
        except Exception as e:
            logger.error(f"Error parsing macro LLM response: {e}")
            return {
                "asset_class": asset_class,
                "regime": "uncertain",
                "direction": "neutral", 
                "confidence": 0.3,
                "expected_return": 0.0,
                "horizon": "short",
                "primary_drivers": ["parsing_error"],
                "risk_factors": ["llm_response_invalid"],
                "tactical_suggestions": [],
                "analysis": f"Macro analysis failed to parse: {str(e)}",
                "generated_at": datetime.utcnow().isoformat(),
                "model_source": "fallback_macro_model"
            }

# API for external use
def create_enhanced_forecasts(forecasts: List[Dict[str, Any]], 
                           market_contexts: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create enhanced forecasts using G4F analysis on a batch of existing forecasts
    """
    enhancer = G4FEnhancedForecast()
    return enhancer.run_batch_enhancement(forecasts, market_contexts)

def create_macro_enhanced_forecast(macro_indicators: Dict[str, float], 
                                 asset_class: str = "equity") -> Dict[str, Any]:
    """
    Create enhanced macro forecast using G4F analysis
    """
    enhancer = G4FEnhancedForecast()
    return enhancer.generate_enhanced_macro_forecast(macro_indicators, asset_class)

if __name__ == "__main__":
    # Example usage
    print("G4F Enhanced Forecast Model - Ready for Use")
    enhancer = G4FEnhancedForecast()
    
    # Example: Enhance a simple forecast
    sample_forecast = {
        "ticker": "SPY",
        "direction": "up", 
        "confidence": 0.65,
        "expected_return": 0.008,
        "probability": 0.65,
        "explanation": "ML model prediction based on technicals",
        "risk_factors": ["volatility_risk"],
        "timestamp": "2025-01-01T00:00:00Z"
    }
    
    sample_context = {
        "current_price": 500.00,
        "trend": "bullish",
        "volatility": 0.18,
        "news_sentiment": 0.2,
        "tech_indicators": {"rsi": 55, "macd": "bullish", "sma": "bullish"},
        "macro_env": {"vix": 16, "fed_rate": 0.0525, "cpi": 0.032},
        "sector_performance": {"technology": 0.02, "finance": 0.01}
    }
    
    if HAS_G4F:
        print("Enhanced forecast example:")
        enhanced = enhancer.enhance_forecast_with_llm("SPY", sample_forecast, sample_context)
        print(json.dumps(enhanced, indent=2))
    else:
        print("G4F not available - model initialized without LLM enhancement capability")