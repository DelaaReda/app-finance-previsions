"""
Feature Integration Module for Forecasting System
Connects the features module with the forecasting pipeline for enhanced technical analysis
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import logging

from backend.features.features import compute_technical_features
from backend.models.pipeline_news_macro_stocks_forecast import NewsMacroStocksForecastPipeline

class FeatureIntegratedPipeline(NewsMacroStocksForecastPipeline):
    """
    Enhanced pipeline that leverages the comprehensive features module
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    def _fetch_stock_with_indicators(self, ticker: str) -> pd.DataFrame:
        """
        Override the parent method to use the enhanced features module
        """
        dates = pd.date_range(start=datetime.now() - timedelta(days=252), 
                              end=datetime.now(), freq='D')
        
        # Generate basic OHLCV data
        base_price = np.random.uniform(50, 200)
        prices = [base_price]
        for i in range(1, len(dates)):
            change = np.random.normal(0, 0.02)  # 2% daily volatility
            prices.append(prices[-1] * (1 + change))
            
        volume = np.random.uniform(100000, 10000000, len(dates))
        
        # Create DataFrame with basic OHLCV data
        df = pd.DataFrame({
            'date': dates,
            'ticker': ticker,
            'open': prices * np.random.uniform(0.99, 1.01, len(prices)),
            'high': prices * np.random.uniform(1.00, 1.03, len(prices)),
            'low': prices * np.random.uniform(0.97, 1.00, len(prices)),
            'close': prices,
            'volume': volume
        })
        
        # Use the enhanced features module instead of manual calculations
        df = compute_technical_features(df)
        return df

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Override to use the features module for more comprehensive indicator calculation
        """
        # Use the enhanced compute_technical_features function from the features module
        df_with_features = compute_technical_features(df)
        return df_with_features

    def generate_technical_signals(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Generate more sophisticated technical signals using the features module (override parent method)
        """
        self.logger.info("Generating enhanced technical signals using features module")
        
        signals = {}
        for ticker, df in stock_data.items():
            if df.empty:
                signals[ticker] = pd.DataFrame(columns=['date', 'signal_name', 'signal_value', 'confidence'])
                continue
                
            # Calculate enhanced signals based on the features module
            df_signals = df[['date']].copy()
            
            # RSI-based signals (using enhanced RSI from features)
            df_signals['rsi_oversold'] = (df.get('rsi_14', pd.Series([50]*len(df))) < 30).astype(int)
            df_signals['rsi_overbought'] = (df.get('rsi_14', pd.Series([50]*len(df))) > 70).astype(int)
            df_signals['rsi_medium_buy'] = ((df.get('rsi_14', pd.Series([50]*len(df))) > 30) & 
                                           (df.get('rsi_14', pd.Series([50]*len(df))) < 40)).astype(int)
            df_signals['rsi_medium_sell'] = ((df.get('rsi_14', pd.Series([50]*len(df))) > 60) & 
                                            (df.get('rsi_14', pd.Series([50]*len(df))) < 70)).astype(int)
            
            # Moving average crossover signals (using enhanced SMA from features)
            df_signals['ma20_50_bullish_cross'] = ((df.get('sma_20', pd.Series([100]*len(df))) > 
                                                   df.get('sma_50', pd.Series([100]*len(df)))) & 
                                                  (df.get('sma_20', pd.Series([100]*len(df))).shift(1) <= 
                                                   df.get('sma_50', pd.Series([100]*len(df))).shift(1))).astype(int)
            df_signals['ma20_50_bearish_cross'] = ((df.get('sma_20', pd.Series([100]*len(df))) < 
                                                   df.get('sma_50', pd.Series([100]*len(df)))) & 
                                                  (df.get('sma_20', pd.Series([100]*len(df))).shift(1) >= 
                                                   df.get('sma_50', pd.Series([100]*len(df))).shift(1))).astype(int)
            
            # MACD signals (using enhanced MACD from features)
            df_signals['macd_bullish_cross'] = ((df.get('macd', pd.Series([0]*len(df))) > 
                                                df.get('macd_signal', pd.Series([0]*len(df)))) & 
                                               (df.get('macd', pd.Series([0]*len(df))).shift(1) <= 
                                                df.get('macd_signal', pd.Series([0]*len(df))).shift(1))).astype(int)
            df_signals['macd_bearish_cross'] = ((df.get('macd', pd.Series([0]*len(df))) < 
                                                df.get('macd_signal', pd.Series([0]*len(df)))) & 
                                               (df.get('macd', pd.Series([0]*len(df))).shift(1) >= 
                                                df.get('macd_signal', pd.Series([0]*len(df))).shift(1))).astype(int)
            
            # Bollinger Band signals (using enhanced BB from features)
            df_signals['bb_breakout_upper'] = (df.get('close', pd.Series([100]*len(df))) > 
                                              df.get('bb_upper', pd.Series([110]*len(df)))).astype(int)
            df_signals['bb_breakout_lower'] = (df.get('close', pd.Series([100]*len(df))) < 
                                              df.get('bb_lower', pd.Series([90]*len(df)))).astype(int)
            df_signals['bb_squeeze'] = (df.get('bb_width', pd.Series([10]*len(df))) < 
                                       df.get('bb_width', pd.Series([10]*len(df))).quantile(0.2)).astype(int)  # Low volatility
            
            # Volatility signals (using enhanced volatility from features)
            df_signals['volatility_expanding'] = (df.get('volatility', pd.Series([0.02]*len(df))) > 
                                                 df.get('volatility', pd.Series([0.02]*len(df))).rolling(20).mean()).astype(int)
            df_signals['volatility_contracting'] = (df.get('volatility', pd.Series([0.02]*len(df))) < 
                                                   df.get('volatility', pd.Series([0.02]*len(df))).rolling(20).mean()).astype(int)
            
            # Momentum signals (using enhanced momentum from features)
            df_signals['momentum_positive'] = (df.get('momentum', pd.Series([0.001]*len(df))) > 0).astype(int)
            df_signals['momentum_negative'] = (df.get('momentum', pd.Series([0.001]*len(df))) < 0).astype(int)
            
            # ATR signals (using enhanced ATR from features)
            df_signals['high_volatility_regime'] = (df.get('atr_14', pd.Series([1.0]*len(df))) > 
                                                   df.get('close', pd.Series([100]*len(df))) * 0.02).astype(int)  # More than 2% of price
            
            signals[ticker] = df_signals
        
        return signals

    def generate_advanced_forecast_data(self, tickers: List[str]) -> Dict:
        """
        Generate advanced forecast data using enhanced features
        """
        self.logger.info(f"Generating advanced forecast data for tickers: {tickers}")
        
        # Ingest all data using the enhanced pipeline
        news_data = self.ingest_news_data(tickers)
        macro_data = self.ingest_macro_data()
        stock_data = {ticker: self._fetch_stock_with_indicators(ticker) for ticker in tickers}
        
        # Use enhanced signal generation (calling overridden parent method)
        technical_signals = self.generate_technical_signals(stock_data)
        news_impact_scores = self.calculate_news_impact_score(news_data, stock_data)
        macro_regime_scores = self.calculate_macro_regime_score(macro_data)
        
        # Combine signals with emphasis on the enhanced features
        forecasts = self.combine_signals_for_forecast(
            news_impact_scores, 
            macro_regime_scores, 
            technical_signals, 
            stock_data
        )
        
        # Format for API with enhanced information
        result = {
            "last_update": datetime.now().isoformat(),
            "tickers_analyzed": tickers,
            "enhanced_features_used": True,
            "forecasts": {}
        }
        
        for ticker, df in forecasts.items():
            if not df.empty:
                latest = df.iloc[-1]
                
                result["forecasts"][ticker] = {
                    "date": latest['date'].isoformat() if hasattr(latest['date'], 'isoformat') else str(latest['date']),
                    "direction": latest.get('forecast_direction', 'neutral'),
                    "confidence": float(latest.get('confidence', 0.5)),
                    "expected_return_1d": float(latest.get('expected_return_1d', 0.0)),
                    "expected_return_5d": float(latest.get('expected_return_5d', 0.0) if 'expected_return_5d' in df.columns else 0.0),
                    "expected_return_22d": float(latest.get('expected_return_22d', 0.0) if 'expected_return_22d' in df.columns else 0.0),
                    "composite_signal": float(latest.get('composite_signal', 0.0) if 'composite_signal' in df.columns else 0.0),
                    "enhanced_technical_signals": {
                        "rsi_oversold": bool(latest.get('rsi_oversold', 0)),
                        "rsi_overbought": bool(latest.get('rsi_overbought', 0)),
                        "rsi_medium_buy": bool(latest.get('rsi_medium_buy', 0)),
                        "rsi_medium_sell": bool(latest.get('rsi_medium_sell', 0)),
                        "ma20_50_bullish_cross": bool(latest.get('ma20_50_bullish_cross', 0)),
                        "ma20_50_bearish_cross": bool(latest.get('ma20_50_bearish_cross', 0)),
                        "macd_bullish_cross": bool(latest.get('macd_bullish_cross', 0)),
                        "macd_bearish_cross": bool(latest.get('macd_bearish_cross', 0)),
                        "bb_breakout_upper": bool(latest.get('bb_breakout_upper', 0)),
                        "bb_breakout_lower": bool(latest.get('bb_breakout_lower', 0)),
                        "bb_squeeze": bool(latest.get('bb_squeeze', 0)),  # Volatility contraction signal
                        "volatility_expanding": bool(latest.get('volatility_expanding', 0)),
                        "volatility_contracting": bool(latest.get('volatility_contracting', 0)),
                        "momentum_positive": bool(latest.get('momentum_positive', 0)),
                        "momentum_negative": bool(latest.get('momentum_negative', 0)),
                        "high_volatility_regime": bool(latest.get('high_volatility_regime', 0)),
                    },
                    "news_impact": float(latest.get('news_impact_score', 0.0)),
                    "macro_regime": float(latest.get('macro_regime_score', 0.0)),
                    "data_quality_score": self._calculate_data_quality_score(latest)
                }
        
        return result

    def _calculate_data_quality_score(self, latest_row) -> float:
        """
        Calculate a data quality score based on available signals and features
        """
        # Count available meaningful values (not NaN/None)
        available_signals = 0
        total_signals = 0
        
        for key, value in latest_row.items():
            if key not in ['date', 'ticker'] and value is not None:
                try:
                    # Try to convert to float to see if it's numeric
                    float_val = float(value)
                    if not (np.isnan(float_val) or np.isinf(float_val)):
                        available_signals += 1
                    total_signals += 1
                except (ValueError, TypeError):
                    # If not numeric, just count as available if it's not None
                    available_signals += 1
                    total_signals += 1
        
        if total_signals == 0:
            return 0.0
        
        return available_signals / total_signals


# Convenience function for direct use with forecasting
def get_enhanced_features_for_tickers(tickers: List[str]) -> Dict:
    """
    Get enhanced forecasts using improved feature integration
    """
    pipeline = FeatureIntegratedPipeline()
    return pipeline.generate_advanced_forecast_data(tickers)


# Example usage:
# enhanced_forecasts = get_enhanced_features_for_tickers(["SPY", "QQQ", "AAPL"])