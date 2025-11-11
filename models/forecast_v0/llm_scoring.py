"""
LLM Scoring and Explanation Layer
Uses G4F for financial analysis and explanation generation
Part of the Finance Copilot forecasting engine
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

try:
    from g4f.client import Client
    G4F_AVAILABLE = True
except ImportError:
    G4F_AVAILABLE = False
    # Fallback to a mock implementation
    class Client:
        def __init__(self):
            pass
        
        def chat(self):
            pass
    
    logging.warning("g4f not available, using mock implementation")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMScoringLayer:
    """
    LLM-based scoring and explanation layer for financial forecasts
    Uses G4F to enhance model predictions with qualitative analysis
    """
    
    def __init__(self, model: str = "gpt-3.5-turbo", temperature: float = 0.3):
        self.model = model
        self.temperature = temperature
        self.client = None
        
        if G4F_AVAILABLE:
            self.client = Client()
        
        # Define financial analysis prompt template
        self.analysis_prompt_template = """
        You are an expert financial analyst and trading advisor. Analyze the following financial forecast and market context to provide:

        1. Direction validation (up/down/neutral)
        2. Confidence adjustment based on market conditions
        3. Risk factors and qualitative insights
        4. Clear explanation of your reasoning

        Forecast Data:
        {forecast_data}

        Market Context:
        {market_context}

        Economic Indicators:
        {economic_context}

        Please respond in the following JSON format:
        {{
            "direction_validation": "up|down|neutral",
            "confidence_adjustment": float, // -1.0 to 1.0 adjustment to existing confidence
            "risk_factors": ["factor1", "factor2"],
            "qualitative_insights": "Brief explanation of market conditions",
            "explanation": "Detailed reasoning for your assessment",
            "timestamp": "{timestamp}"
        }}
        """
    
    def validate_and_score(self, 
                         forecast_data: Dict[str, Any], 
                         market_context: Dict[str, Any] = None,
                         economic_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use LLM to validate forecast and provide additional scoring
        
        Args:
            forecast_data: Forecast results from the ML model
            market_context: Current market conditions and technical indicators
            economic_context: Economic indicators and sentiment data
            
        Returns:
            Enhanced forecast with LLM validation and explanation
        """
        if not G4F_AVAILABLE:
            return self._mock_llm_response(forecast_data)
        
        # Prepare the prompt
        prompt = self.analysis_prompt_template.format(
            forecast_data=json.dumps(forecast_data, indent=2),
            market_context=json.dumps(market_context or {}, indent=2),
            economic_context=json.dumps(economic_context or {}, indent=2),
            timestamp=datetime.now().isoformat()
        )
        
        try:
            # Use G4F to get response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            
            # Extract response content
            content = response.choices[0].message.content
            
            # Parse the JSON response
            llm_response = self._parse_json_response(content)
            
            return llm_response
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            # Return mock response if LLM fails
            return self._mock_llm_response(forecast_data)
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM, handling possible formatting issues
        """
        try:
            # Look for JSON in the content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # If no JSON found, return defaults
                return self._default_llm_response()
        except json.JSONDecodeError:
            logger.warning("Could not parse LLM response as JSON, using defaults")
            return self._default_llm_response()
    
    def _default_llm_response(self) -> Dict[str, Any]:
        """
        Return default LLM response when actual LLM is not available or fails
        """
        return {
            "direction_validation": "neutral",
            "confidence_adjustment": 0.0,
            "risk_factors": ["model uncertainty"],
            "qualitative_insights": "LLM analysis not available",
            "explanation": "Default response when LLM is not available",
            "timestamp": datetime.now().isoformat()
        }
    
    def _mock_llm_response(self, forecast_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a mock LLM response based on forecast data
        """
        direction = forecast_data.get('direction', 'neutral')
        expected_return = forecast_data.get('expected_return', 0)
        
        # Generate mock response based on forecast
        confidence = forecast_data.get('confidence', 0.5)
        confidence_adjustment = (confidence - 0.5) * 0.2  # Small adjustment based on initial confidence
        
        risk_factors = []
        if abs(expected_return) > 0.05:
            risk_factors.append("high expected return")
        if confidence < 0.6:
            risk_factors.append("low model confidence")
        
        explanation = (f"Forecast shows {direction} movement with {expected_return:.2%} expected return. "
                      f"Initial confidence was {confidence:.2f}.")
        
        return {
            "direction_validation": direction,
            "confidence_adjustment": confidence_adjustment,
            "risk_factors": risk_factors,
            "qualitative_insights": "Quantitative model prediction",
            "explanation": explanation,
            "timestamp": datetime.now().isoformat()
        }
    
    def enhance_forecast(self, 
                        forecast: Dict[str, Any], 
                        market_context: Dict[str, Any] = None,
                        economic_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhance forecast with LLM analysis
        
        Args:
            forecast: Original forecast from ML model
            market_context: Market conditions
            economic_context: Economic environment
            
        Returns:
            Enhanced forecast with LLM insights
        """
        # Get LLM analysis
        llm_analysis = self.validate_and_score(forecast, market_context, economic_context)
        
        # Adjust the original forecast based on LLM analysis
        enhanced_forecast = forecast.copy()
        
        # Adjust confidence based on LLM feedback
        original_confidence = forecast.get('confidence', 0.5)
        confidence_adjustment = llm_analysis.get('confidence_adjustment', 0.0)
        adjusted_confidence = max(0.0, min(1.0, original_confidence + confidence_adjustment))
        
        # Determine final direction based on LLM validation
        llm_direction = llm_analysis.get('direction_validation', forecast.get('direction', 'neutral'))
        final_direction = llm_direction if llm_direction != 'neutral' else forecast.get('direction', 'neutral')
        
        # Update the forecast
        enhanced_forecast['llm_analysis'] = llm_analysis
        enhanced_forecast['adjusted_confidence'] = adjusted_confidence
        enhanced_forecast['final_direction'] = final_direction
        enhanced_forecast['full_explanation'] = (
            f"ML Model: {forecast.get('explanation', '')}\n"
            f"LLM Analysis: {llm_analysis.get('explanation', '')}"
        )
        
        return enhanced_forecast


def create_llm_scoring_layer(**kwargs) -> LLMScoringLayer:
    """
    Factory function to create an LLM scoring layer
    """
    return LLMScoringLayer(**kwargs)


def example_usage():
    """
    Example of how to use the LLM Scoring Layer
    """
    # Create sample forecast data
    sample_forecast = {
        "ticker": "SPY",
        "horizon": "1d",
        "direction": "up",
        "confidence": 0.65,
        "expected_return": 0.012,
        "explanation": "XGBoost model indicates upward momentum based on technical indicators",
        "metrics": {
            "current_price": 420.50,
            "forecast_price": 425.34,
            "expected_return_pct": 1.14
        },
        "predictions": {
            "xgb": 425.34,
            "arima": 422.10,
            "combined": 425.34
        }
    }
    
    # Create market context
    market_context = {
        "volatility": "moderate",
        "market_regime": "bullish",
        "support_resistance": "resistance at 425",
        "volume_trend": "increasing"
    }
    
    # Create economic context
    economic_context = {
        "fed_policy": "hawkish",
        "inflation_trend": "decreasing",
        "employment": "stable"
    }
    
    # Create LLM scoring layer
    llm_layer = LLMScoringLayer(model="gpt-3.5-turbo")
    
    # Enhance the forecast
    enhanced_forecast = llm_layer.enhance_forecast(
        sample_forecast, 
        market_context, 
        economic_context
    )
    
    print("Original Forecast:")
    print(json.dumps(sample_forecast, indent=2))
    
    print("\nEnhanced Forecast:")
    print(json.dumps(enhanced_forecast, indent=2))
    
    return llm_layer, enhanced_forecast


if __name__ == "__main__":
    print("MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7: Testing LLM Scoring Layer...")
    llm_layer, enhanced_forecast = example_usage()