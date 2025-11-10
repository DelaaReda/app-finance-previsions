# Forecasts Hybrid v1 - ML + G4F Ranking
# File: /models/forecast_hybrid_v1.py
# Purpose: Combine ML predictions with LLM ranking for forecasts
# Task: FC-P1-013 - ALEX-FINANCE-ANALYST-SUPERMAN-29

import pandas as pd
from typing import Dict, List, Any
import logging
from datetime import datetime
from g4f.client import Client
import json
from pathlib import Path
import re

class ForecastHybridV1:
    """
    Hybrid forecasting system combining ML predictions with G4F LLM ranking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.g4f_client = Client()
        self.data_dir = Path(__file__).parent / ".." / "data"
        self.data_dir.mkdir(exist_ok=True)
        
    def predict_direction_ml(self, ticker: str, features_df: pd.DataFrame) -> Dict:
        """
        ML model to predict direction and probability based on features
        """
        if features_df.empty or len(features_df) < 10:  # Need minimum data
            return {
                "direction": "neutral",
                "probability": 0.5,
                "expected_return": 0.0,
                "confidence": 0.4
            }
        
        # Get the latest row
        latest = features_df.iloc[-1]
        
        # Calculate signals using helper method
        signals = self._calculate_technical_signals(latest)
        
        # Calculate composite direction based on signals
        bullish_signals = self._calculate_bullish_score(signals)
        bearish_signals = self._calculate_bearish_score(signals)
        
        # Determine direction and probability
        direction, probability = self._determine_direction(bullish_signals, bearish_signals)
        
        # Calculate expected return based on signal strength
        signal_strength = abs(bullish_signals - bearish_signals)
        expected_return = signal_strength * (0.02 if direction == "up" else -0.02)  # Max 2% daily
        
        return {
            "direction": direction,
            "probability": probability,
            "expected_return": expected_return,
            "confidence": signal_strength
        }
    
    def _calculate_technical_signals(self, latest: pd.Series) -> Dict[str, float]:
        """Calculate technical signals from the latest data point."""
        signals = {
            'ma_bullish': 1 if latest.get('sma_20', 0) > latest.get('sma_50', 0) else 0,
            'rsi_oversold': 1 if latest.get('rsi', 50) < 30 else 0,
            'rsi_overbought': 1 if latest.get('rsi', 50) > 70 else 0,
            'bb_bullish_breakout': 1 if latest.get('close', 0) > latest.get('bb_upper', 0) else 0,
            'bb_bearish_breakout': 1 if latest.get('close', 0) < latest.get('bb_lower', 0) else 0,
            'macd_bullish': 1 if latest.get('macd', 0) > latest.get('macd_signal', 0) else 0,
            'macd_bearish': 1 if latest.get('macd', 0) < latest.get('macd_signal', 0) else 0,
            'news_positive': 1 if latest.get('news_sentiment_score', 0) > 0.2 else 0,
            'news_negative': 1 if latest.get('news_sentiment_score', 0) < -0.2 else 0,
            'high_volatility': 1 if latest.get('atr', 0) > latest.get('close', 1) * 0.03 else 0  # 3% of price
        }
        return signals
    
    def _calculate_bullish_score(self, signals: Dict[str, float]) -> float:
        """Calculate bullish signal score."""
        score = (signals.get('ma_bullish', 0) * 0.2 +
                signals.get('rsi_oversold', 0) * 0.15 +
                signals.get('bb_bullish_breakout', 0) * 0.15 +
                signals.get('macd_bullish', 0) * 0.15 +
                signals.get('news_positive', 0) * 0.15)
        return score
    
    def _calculate_bearish_score(self, signals: Dict[str, float]) -> float:
        """Calculate bearish signal score."""
        score = (signals.get('rsi_overbought', 0) * 0.15 +
                signals.get('bb_bearish_breakout', 0) * 0.15 +
                signals.get('macd_bearish', 0) * 0.15 +
                signals.get('news_negative', 0) * 0.15 +
                signals.get('high_volatility', 0) * 0.1)
        return score
    
    def _determine_direction(self, bullish_signals: float, bearish_signals: float) -> tuple:
        """Determine forecast direction and probability based on signal strengths."""
        threshold = 0.1  # Minimum difference to avoid neutral
        if bullish_signals > bearish_signals + threshold:  # Bullish threshold
            return "up", min(0.8, bullish_signals)
        elif bearish_signals > bullish_signals + threshold:
            return "down", min(0.8, bearish_signals)
        else:
            return "neutral", 0.5
    
    def get_llm_validation(self, ticker: str, ml_prediction: Dict, market_context: Dict) -> Dict:
        """
        Use G4F LLM to validate, rank, and explain the forecast
        """
        # Prepare market context for the LLM
        context_str = f"""
        Ticker: {ticker}
        ML Prediction: {ml_prediction}
        
        Market Context:
        - Current price: {market_context.get('current_price', 'N/A')}
        - Recent trend: {market_context.get('trend', 'N/A')}
        - Volatility level: {market_context.get('volatility', 'N/A')}
        - News sentiment: {market_context.get('news_sentiment', 'N/A')}
        - Technical signals: {market_context.get('tech_signals', 'N/A')}
        - Macro environment: {market_context.get('macro_regime', 'N/A')}
        
        Please analyze these signals and provide:
        1. Direction filter (up/down/neutral)
        2. Confidence adjustment (how much to modify the ML confidence)
        3. Short explanation of your reasoning
        4. Risk factors to consider
        
        Respond in JSON format:
        {{
            "direction_filter": "up|down|neutral",
            "confidence_adjustment": float,
            "explanation": "short reason",
            "risk_factors": ["factor1", "factor2"]
        }}
        """
        
        try:
            response = self.g4f_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using a widely available model
                messages=[{"role": "user", "content": context_str}]
            )
            
            # Parse the response (need to handle potential format issues)
            response_text = response.choices[0].message.content or ""
            
            # Extract JSON from response if it includes other text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    llm_result = json.loads(json_str)
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    llm_result = {
                        "direction_filter": ml_prediction["direction"],
                        "confidence_adjustment": 0.0,
                        "explanation": "LLM parsing issue, using original prediction",
                        "risk_factors": []
                    }
            else:
                # Fallback if no JSON found
                llm_result = {
                    "direction_filter": ml_prediction["direction"],
                    "confidence_adjustment": 0.0,
                    "explanation": "LLM response format issue, using original prediction",
                    "risk_factors": []
                }
                
            return llm_result
        except Exception as e:
            self.logger.error(f"LLM validation error for {ticker}: {e}")
            # Return fallback values
            return {
                "direction_filter": ml_prediction["direction"],
                "confidence_adjustment": 0.0,
                "explanation": "LLM validation temporarily unavailable",
                "risk_factors": []
            }
    
    def generate_forecast_row(self, ticker: str, ml_result: Dict, llm_result: Dict, 
                            market_context: Dict) -> Dict:
        """
        Generate a final forecast row combining ML and LLM results
        """
        # Combine ML and LLM results
        final_direction = llm_result.get("direction_filter", ml_result["direction"])
        base_confidence = ml_result["confidence"]
        llm_adjustment = llm_result.get("confidence_adjustment", 0.0)
        final_confidence = max(0.0, min(1.0, base_confidence + llm_adjustment))
        
        # Calculate adjusted expected return based on confidence
        confidence_factor = final_confidence / max(ml_result["confidence"], 0.1)  # Avoid division by zero
        adjusted_return = ml_result["expected_return"] * confidence_factor
        
        return {
            "ticker": ticker,
            "direction": final_direction,
            "confidence": round(final_confidence, 3),
            "expected_return": round(adjusted_return, 4),
            "probability": round(ml_result["probability"], 3),
            "explanation": llm_result.get("explanation", "AI-generated forecast combining technical and fundamental analysis"),
            "risk_factors": llm_result.get("risk_factors", []),
            "timestamp": datetime.now().isoformat(),
            "source": ["ml_model", "g4f_llm"],
            "model_version": "hybrid_v1"
        }
    
    def generate_hybrid_forecasts(self, tickers: List[str]) -> Dict:
        """
        Main function to generate hybrid forecasts for given tickers
        This is a simplified version that generates mock data based on ML predictions enhanced with G4F
        """
        self.logger.info(f"Generating hybrid forecasts for tickers: {tickers}")
        
        forecasts = []
        
        # Generate forecasts for each ticker
        for i, ticker in enumerate(tickers):
            # Generate basic ML prediction based on technical indicators
            # In a real system, this would use actual market data
            ml_result = {
                "direction": "up",
                "probability": 0.55 + (i * 0.02),  # Slightly increasing probabilities
                "expected_return": 0.003 + (i * 0.0005),  # Slightly increasing returns
                "confidence": 0.25 + (i * 0.02)  # Starting from 0.25
            }
            
            # Create a mock market context
            market_context = {
                "current_price": 400 + (i * 10),  # Mock prices
                "trend": "bullish" if i % 2 == 0 else "bearish",
                "volatility": 0.015,
                "news_sentiment": 0.1,
                "tech_signals": {
                    "rsi": 50 + (i * 2),
                    "macd_bullish": True,
                    "ma_bullish": i % 2 == 0
                },
                "macro_regime": "growth"
            }
            
            # Apply LLM validation (this would call G4F in a real implementation)
            llm_result = self.get_llm_validation(ticker, ml_result, market_context)
            
            # Generate final forecast row
            forecast_row = self.generate_forecast_row(ticker, ml_result, llm_result, market_context)
            forecasts.append(forecast_row)
        
        # Create final result with metadata
        result = {
            "rows": forecasts,
            "last_update": datetime.now().isoformat(),
            "source": ["ml_model", "g4f_llm", "market_data"],
            "model_version": "hybrid_v1",
            "tickers_processed": tickers,
            "total_forecasts": len(forecasts)
        }
        
        self.logger.info(f"Generated {len(forecasts)} forecasts for {len(tickers)} tickers")
        return result
    
    def save_forecasts(self, forecasts: Dict, filename: str = "forecasts.json"):
        """
        Save forecasts to file with metadata
        """
        # Create the data directory if it doesn't exist
        data_dir = Path(__file__).resolve().parents[2] / "data"
        data_dir.mkdir(exist_ok=True)
        filepath = data_dir / filename
        
        # Add metadata to forecasts
        forecasts_with_meta = {
            "last_update": datetime.now().isoformat(),
            "source": ["ml_model", "g4f_llm", "market_data"],
            "model_version": "hybrid_v1",
            "data": forecasts
        }
        
        with open(filepath, 'w') as f:
            json.dump(forecasts_with_meta, f, indent=2, default=str)
        
        self.logger.info(f"Forecasts saved to {filepath}")
    
    def run_forecast_job(self, tickers: List[str] = None):
        """
        Execute the forecast job and save results
        """
        if tickers is None:
            # Default to major indices/stocks for demo
            tickers = ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "META"]
        
        # Generate forecasts
        forecasts = self.generate_hybrid_forecasts(tickers)
        
        # Save to file
        self.save_forecasts(forecasts)
        
        return forecasts

# Example usage:
# if __name__ == "__main__":
#     hybrid_forecast = ForecastHybridV1()
#     result = hybrid_forecast.run_forecast_job(["AAPL", "GOOGL", "MSFT"])
#     print(result)