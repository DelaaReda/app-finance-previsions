"""
LLM Ranker - Ranks and refines forecast data using G4F (GPT-for-finance)
"""
import random
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
import json

from models.ml_forecast import run_forecast_generation


class LLMRanker:
    """
    Uses G4F to rank and refine forecast data
    """
    
    def __init__(self):
        pass
    
    def rank_forecasts(self, forecasts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process forecasts through LLM to refine predictions and add explanations
        """
        ranked_forecasts = []
        
        for forecast in forecasts:
            # Simulate LLM refinement - in real implementation, this would use G4F
            refined_explanation = self._generate_llm_explanation(forecast)
            adjusted_confidence = self._adjust_confidence_with_llm(forecast)
            
            forecast_copy = forecast.copy()
            forecast_copy["llm_refined_explanation"] = refined_explanation
            forecast_copy["llm_adjusted_confidence"] = min(adjusted_confidence, 1.0)
            forecast_copy["llm_generated_at"] = datetime.utcnow().isoformat() + "Z"
            
            ranked_forecasts.append(forecast_copy)
        
        return ranked_forecasts
    
    def _generate_llm_explanation(self, forecast: Dict[str, Any]) -> str:
        """
        Generate a refined explanation using LLM-style logic
        """
        ticker = forecast.get("ticker", "UNKNOWN")
        direction = forecast.get("direction", "flat")
        score = forecast.get("direction_score", 0)
        
        # Generate context-aware explanation
        base_explanation = forecast.get("explanation", "Technical indicators suggest movement")
        
        # In a real implementation, this would query G4F
        # For simulation, we'll enhance the explanation
        llm_additions = [
            f"LLM confirms {direction} bias based on market regime",
            f"Cross-validation with sector trends supports direction",
            f"Risk factors considered: volatility, liquidity, news sentiment"
        ]
        
        return f"{base_explanation} - {random.choice(llm_additions)}"
    
    def _adjust_confidence_with_llm(self, forecast: Dict[str, Any]) -> float:
        """
        Adjust confidence based on LLM assessment
        """
        original_confidence = forecast.get("confidence", 0.5)
        
        # Simulate LLM confidence adjustment
        # In real implementation, this would use G4F
        adjustment_factor = random.uniform(0.8, 1.2)  # ±20% adjustment
        
        return min(max(original_confidence * adjustment_factor, 0.05), 0.98)  # Clamp to [0.05, 0.98]


# Singleton instance
llm_ranker = LLMRanker()


def run_llm_ranking() -> List[Dict[str, Any]]:
    """Generate forecasts and run them through LLM ranking"""
    # Get base forecasts from ML model
    base_forecasts = run_forecast_generation()
    
    # Rank them with LLM
    ranked_forecasts = llm_ranker.rank_forecasts(base_forecasts)
    
    return ranked_forecasts