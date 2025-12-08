"""
G4F Enhanced Forecast Analyzer v2 - Advanced LLM-based Forecasting
File: /models/forecast_g4f_analyzer_v2.py
Purpose: Use G4F models to analyze existing market data and generate enhanced forecasts
Task: FC-ML-ENHANCE-001 - Enhanced ML Model with G4F Integration
"""
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import json
import re
from pathlib import Path

from g4f.client import Client
import g4f

logger = logging.getLogger(__name__)

class ForecastG4FAnalyzerV2:
    """
    Advanced forecasting model that uses G4F LLMs to analyze existing market data
    and generate enhanced forecast predictions
    """
    
    def __init__(self, preferred_model: str = "gpt-3.5-turbo"):
        self.logger = logging.getLogger(__name__)
        self.g4f_client = Client()
        self.preferred_model = preferred_model
        self.data_dir = Path(__file__).parent / ".." / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
    def analyze_existing_data_with_g4f(self, 
                                     ticker: str, 
                                     market_data: pd.DataFrame, 
                                     current_price: float = None) -> Dict[str, Any]:
        """
        Use G4F to analyze existing market data and generate enhanced forecast
        
        Args:
            ticker: Stock ticker symbol to analyze
            market_data: Historical market data DataFrame
            current_price: Current market price (optional, defaults to latest from market_data)
            
        Returns:
            Enhanced forecast with G4F analysis
        """
        try:
            if market_data.empty or len(market_data) < 5:
                return {
                    "ticker": ticker,
                    "direction": "neutral",
                    "confidence": 0.3,
                    "expected_return": 0.0,
                    "probability": 0.5,
                    "explanation": "Insufficient data for G4F analysis",
                    "g4f_analysis": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": ["g4f_analyzer_v2", "fallback"]
                }
            
            # Get current price if not provided
            if current_price is None:
                current_price = float(market_data.iloc[-1]['Close']) if 'Close' in market_data.columns else market_data.iloc[-1].get('close', 0)
            
            # Prepare market context for LLM analysis
            context_prompt = self._prepare_market_context_for_llm(ticker, market_data, current_price)
            
            # Call G4F to analyze market data
            g4f_response = self._call_g4f_for_market_analysis(context_prompt)
            
            # Parse G4F response and create forecast
            enhanced_forecast = self._parse_g4f_response_to_forecast(ticker, g4f_response, current_price)
            
            return enhanced_forecast
            
        except Exception as e:
            self.logger.error(f"Error in G4F analysis for {ticker}: {e}", exc_info=True)
            # Return fallback forecast
            return {
                "ticker": ticker,
                "direction": "neutral", 
                "confidence": 0.2,
                "expected_return": 0.0,
                "probability": 0.5,
                "explanation": f"G4F analysis failed: {str(e)}",
                "g4f_analysis": None,
                "timestamp": datetime.utcnow().isoformat(),
                "source": ["g4f_analyzer_v2", "error_fallback"]
            }
    
    def _prepare_market_context_for_llm(self, 
                                      ticker: str, 
                                      market_data: pd.DataFrame, 
                                      current_price: float) -> str:
        """
        Prepare comprehensive market context for G4F analysis
        """
        # Get recent data points
        recent_data = market_data.tail(10)  # Last 10 days of data
        
        # Calculate key technical indicators if possible
        if 'Close' in market_data.columns:
            sma_20 = market_data['Close'].rolling(20).mean().iloc[-1] if len(market_data) >= 20 else current_price
            sma_50 = market_data['Close'].rolling(50).mean().iloc[-1] if len(market_data) >= 50 else current_price
            rsi = self._calculate_rsi(market_data['Close'])
        else:
            sma_20 = current_price
            sma_50 = current_price
            rsi = 50.0
        
        macd_line, signal_line = self._calculate_macd(market_data['Close'] if 'Close' in market_data.columns else market_data['close']) if ('Close' in market_data.columns or 'close' in market_data.columns) else (0, 0)
        
        # Determine market regime
        price_trend = "bullish" if current_price > sma_20 else "bearish"
        ma_trend = "bullish" if sma_20 > sma_50 else "bearish"
        
        # Calculate momentum based on available columns
        if 'Close' in market_data.columns and len(market_data) > 1:
            prev_close = market_data['Close'].iloc[-2]
            momentum = "positive" if (current_price - prev_close)/prev_close > 0 else "negative"
        elif 'close' in market_data.columns and len(market_data) > 1:
            prev_close = market_data['close'].iloc[-2]
            momentum = "positive" if (current_price - prev_close)/prev_close > 0 else "negative"
        else:
            momentum = "neutral"
        
        context = f"""
        Analyze the financial instrument {ticker} and provide a forecast based on the following market data:

        CURRENT MARKET DATA:
        - Current price: ${current_price:.2f}
        - 20-day moving average: ${sma_20:.2f}
        - 50-day moving average: ${sma_50:.2f}
        - RSI (14-day): {rsi:.2f}
        - MACD: {macd_line:.4f}, Signal: {signal_line:.4f}
        - Price trend vs SMA20: {price_trend}
        - Moving average trend: {ma_trend}
        - Momentum: {momentum}

        RECENT PRICE HISTORY (last 10 days):
        {recent_data.to_json(orient='records', date_format='iso')} 

        ANALYSIS REQUEST:
        1. Determine the most likely price direction (up/down/sideways) in the next 24-48 hours
        2. Estimate confidence level (0-1 scale)
        3. Calculate expected return (as decimal, e.g., 0.02 for 2%)
        4. Identify key support and resistance levels
        5. Highlight any technical patterns or signals
        6. Assess near-term risk factors

        FORMAT RESPONSE AS JSON:
        {{
            "direction": "up|down|sideways",
            "confidence": float (0-1),
            "expected_return": float,
            "short_term_support": float,
            "short_term_resistance": float,
            "technical_signals": ["signal1", "signal2"],
            "risk_factors": ["factor1", "factor2"],
            "explanation": "Brief explanation of technical and market factors considered"
        }}

        Be analytical but concise in your response.
        """
        
        return context
    
    def _call_g4f_for_market_analysis(self, prompt: str) -> str:
        """
        Call G4F client to analyze market context and return response
        """
        try:
            # Prepare models to try in order of preference
            models_to_try = [
                "gpt-3.5-turbo",
                "gpt-4o-mini", 
                "gpt-4o",
                "gemini-pro",
                "claude-3-haiku",
                "llama-3.1-70b",
                "mixtral-8x7b",
            ]
            
            # Try the preferred model first, then fallback
            for model in [self.preferred_model] + models_to_try:
                try:
                    response = self.g4f_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=800
                    )
                    
                    if response and response.choices:
                        result = response.choices[0].message.content
                        self.logger.info(f"G4F analysis successful with model: {model}")
                        return result
                except Exception as e:
                    self.logger.warning(f"Model {model} failed: {e}")
                    continue  # Try next model
            
            # If all models fail, return a default response
            self.logger.error("All G4F models failed, returning default response")
            return json.dumps({
                "direction": "neutral",
                "confidence": 0.3,
                "expected_return": 0.0,
                "short_term_support": 0.0,
                "short_term_resistance": 0.0,
                "technical_signals": ["insufficient_data"],
                "risk_factors": ["model_failure"],
                "explanation": "G4F model analysis temporarily unavailable, using fallback values"
            })
            
        except Exception as e:
            self.logger.error(f"G4F client call failed: {e}")
            # Return fallback response
            return json.dumps({
                "direction": "neutral",
                "confidence": 0.3,
                "expected_return": 0.0,
                "short_term_support": 0.0,
                "short_term_resistance": 0.0,
                "technical_signals": ["fallback_active"],
                "risk_factors": ["g4f_unavailable"],
                "explanation": "G4F analysis unavailable, using system fallback"
            })
    
    def _parse_g4f_response_to_forecast(self, 
                                      ticker: str, 
                                      g4f_response: str, 
                                      current_price: float) -> Dict[str, Any]:
        """
        Parse G4F response and convert to forecast format
        """
        try:
            # Extract JSON from response if it contains other text
            json_match = re.search(r'\{[^}]*\}', g4f_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_data = json.loads(json_str)
            else:
                # If no JSON found, try parsing whole response
                parsed_data = json.loads(g4f_response)
            
            # Map G4F response to forecast structure
            forecast = {
                "ticker": ticker,
                "direction": parsed_data.get("direction", "neutral"),
                "confidence": min(1.0, max(0.0, parsed_data.get("confidence", 0.5))),
                "expected_return": parsed_data.get("expected_return", 0.0),
                "probability": min(1.0, max(0.0, parsed_data.get("confidence", 0.5))),  # Use confidence as probability
                "explanation": parsed_data.get("explanation", "AI-generated forecast based on technical analysis"),
                "g4f_analysis": parsed_data,
                "support_level": parsed_data.get("short_term_support", current_price * 0.98),
                "resistance_level": parsed_data.get("short_term_resistance", current_price * 1.02),
                "technical_signals": parsed_data.get("technical_signals", []),
                "risk_factors": parsed_data.get("risk_factors", []),
                "timestamp": datetime.utcnow().isoformat(),
                "source": ["g4f_analyzer_v2", "g4f_model_analysis", "technical_indicators"],
                "model_version": "g4f_v2",
                "analysis_method": "g4f_technical_analysis"
            }
            
            return forecast
            
        except Exception as e:
            self.logger.error(f"Error parsing G4F response for {ticker}: {e}", exc_info=True)
            # Return fallback forecast
            return {
                "ticker": ticker,
                "direction": "neutral",
                "confidence": 0.25,
                "expected_return": 0.0,
                "probability": 0.25,
                "explanation": f"G4F response parsing failed: {str(e)}",
                "g4f_analysis": {"raw_response": g4f_response},
                "support_level": current_price * 0.98,
                "resistance_level": current_price * 1.02,
                "technical_signals": ["parsing_error"],
                "risk_factors": ["parsing_issue"],
                "timestamp": datetime.utcnow().isoformat(),
                "source": ["g4f_analyzer_v2", "fallback_parse_error"],
                "model_version": "g4f_v2_fallback",
                "analysis_method": "error_recovery"
            }
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = prices.diff().dropna()
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD indicator."""
        if len(prices) < slow + 1:
            return 0.0, 0.0
        
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal).mean()
        
        return float(macd.iloc[-1]), float(signal_line.iloc[-1])
    
    def batch_analyze_with_g4f(self, 
                             tickers_data: Dict[str, pd.DataFrame], 
                             current_prices: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """
        Batch analyze multiple tickers with G4F
        
        Args:
            tickers_data: Dictionary mapping tickers to their market data
            current_prices: Optional dictionary of current prices
            
        Returns:
            List of enhanced forecasts for all tickers
        """
        self.logger.info(f"Starting batch G4F analysis for {len(tickers_data)} tickers")
        
        forecasts = []
        for ticker, data in tickers_data.items():
            current_price = current_prices.get(ticker) if current_prices else None
            forecast = self.analyze_existing_data_with_g4f(ticker, data, current_price)
            forecasts.append(forecast)
        
        self.logger.info(f"Completed batch G4F analysis, generated {len(forecasts)} forecasts")
        return forecasts
    
    def run_enhanced_forecast_job(self, 
                                 tickers: List[str], 
                                 data_loader_func = None) -> Dict[str, Any]:
        """
        Run a complete enhanced forecast job using G4F analysis
        
        Args:
            tickers: List of tickers to analyze
            data_loader_func: Optional function to load market data (defaults to yfinance)
            
        Returns:
            Dictionary with forecast results
        """
        self.logger.info(f"Starting enhanced G4F forecast job for {len(tickers)} tickers")
        
        try:
            # Load market data for each ticker
            tickers_data = {}
            current_prices = {}
            
            for ticker in tickers:
                if data_loader_func:
                    # Use provided data loader
                    data, current_price = data_loader_func(ticker)
                    tickers_data[ticker] = data
                    current_prices[ticker] = current_price
                else:
                    # Use yfinance as default
                    import yfinance as yf
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="6mo")  # 6 months of data
                    if not hist.empty:
                        tickers_data[ticker] = hist
                        current_prices[ticker] = float(hist['Close'].iloc[-1])
                    else:
                        self.logger.warning(f"No data found for {ticker}")
                        # Create minimal data frame with correct column names
                        tickers_data[ticker] = pd.DataFrame({'Close': [100.0]})
                        current_prices[ticker] = 100.0
            
            # Run G4F analysis on all tickers
            forecasts = self.batch_analyze_with_g4f(tickers_data, current_prices)
            
            # Prepare final result
            result = {
                "rows": forecasts,
                "count": len(forecasts),
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["g4f_forecast_v2", "technical_analysis", "market_data"],
                "model_version": "g4f_enhanced_v2",
                "tickers_processed": tickers,
                "g4f_models_used": [self.preferred_model]  # Would include all tried models if needed
            }
            
            self.logger.info(f"Enhanced G4F forecast job completed successfully with {len(forecasts)} forecasts")
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced G4F forecast job failed: {e}", exc_info=True)
            # Return fallback result
            return {
                "rows": [],
                "count": 0,
                "generated_at": datetime.utcnow().isoformat(),
                "source": ["g4f_forecast_v2", "error_fallback"],
                "model_version": "g4f_enhanced_v2_fallback",
                "tickers_processed": tickers,
                "error": str(e),
                "message": "G4F forecast job failed but fallback result returned"
            }