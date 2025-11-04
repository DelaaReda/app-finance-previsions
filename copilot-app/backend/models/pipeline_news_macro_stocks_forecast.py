# News-Macro-Stocks-Forecast Pipeline - Finance Copilot System
# File: /models/pipeline_news_macro_stocks_forecast.py
# Purpose: Define the complete pipeline from news to forecasts
# Mission: ALEX-FINANCE-ANALYST-SUPERMAN-29

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

class NewsMacroStocksForecastPipeline:
    """
    Pipeline to process news, macro data, stock data and generate forecasts
    following the sequence: news→macro→stocks→forecast
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pipeline_config = self._load_pipeline_config()
        
    def _load_pipeline_config(self) -> Dict:
        """
        Load pipeline configuration including required indicators and signal weights
        """
        return {
            "data_refresh_frequency": "daily",
            "news_sentiment_window": "24h",
            "macro_lag": "1d",  # Macro data typically has 1 day lag
            "forecast_horizon": ["1d", "5d", "22d"],  # 1 day, 1 week, 1 month
            "required_news_sources": [
                "earnings_announcements",
                "macro_releases", 
                "geopolitical_events",
                "fed_speeches",
                "economic_reports"
            ],
            "required_macro_indicators": [
                "vix",
                "cpi",
                "gdp_growth",
                "unemployment_rate", 
                "fed_rate",
                "yield_curve"
            ],
            "required_stock_indicators": [
                "price",
                "volume", 
                "rsi",
                "macd",
                "sma_20",
                "sma_50",
                "bb_upper",
                "bb_lower"
            ]
        }

    def ingest_news_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Ingest news and sentiment data for given tickers
        """
        self.logger.info(f"Ingesting news data for tickers: {tickers}")
        
        # Simulate news data structure
        news_data = {}
        for ticker in tickers:
            # This would connect to real news APIs in production
            news_data[ticker] = self._fetch_news_sentiment(ticker)
            
        return news_data

    def _fetch_news_sentiment(self, ticker: str) -> pd.DataFrame:
        """
        Fetch and process sentiment for a given ticker
        """
        # This would connect to news APIs in real implementation
        # For now we simulate the structure
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                              end=datetime.now(), freq='D')
        return pd.DataFrame({
            'date': dates,
            'ticker': ticker,
            'sentiment_score': np.random.uniform(-1, 1, len(dates)),
            'news_volume': np.random.randint(0, 100, len(dates)),
            'relevance_score': np.random.uniform(0, 1, len(dates)),
            'news_category': np.random.choice(['earnings', 'macro', 'geopolitical', 'sector'], len(dates))
        })

    def ingest_macro_data(self) -> Dict[str, pd.DataFrame]:
        """
        Ingest macroeconomic data
        """
        self.logger.info("Ingesting macroeconomic data")
        
        # This would connect to FRED API or other macro sources
        macro_data = {}
        for indicator in self.pipeline_config["required_macro_indicators"]:
            macro_data[indicator] = self._fetch_macro_indicator(indicator)
            
        return macro_data

    def _fetch_macro_indicator(self, indicator: str) -> pd.DataFrame:
        """
        Fetch a specific macro indicator
        """
        dates = pd.date_range(start=datetime.now() - timedelta(days=365), 
                              end=datetime.now(), freq='D')
        return pd.DataFrame({
            'date': dates,
            'indicator': indicator,
            'value': np.random.uniform(0.5, 2.5, len(dates)) if indicator == 'cpi' 
                     else np.random.uniform(10, 40, len(dates)) if indicator == 'vix'
                     else np.random.uniform(0.5, 5, len(dates)),
            'normalized_value': np.random.uniform(-1, 1, len(dates))
        })

    def ingest_stock_data(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Ingest stock price and technical indicator data
        """
        self.logger.info(f"Ingesting stock data for tickers: {tickers}")
        
        stock_data = {}
        for ticker in tickers:
            stock_data[ticker] = self._fetch_stock_with_indicators(ticker)
            
        return stock_data

    def _fetch_stock_with_indicators(self, ticker: str) -> pd.DataFrame:
        """
        Fetch stock data with calculated technical indicators
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
        
        # Create DataFrame
        df = pd.DataFrame({
            'date': dates,
            'ticker': ticker,
            'open': prices * np.random.uniform(0.99, 1.01, len(prices)),
            'high': prices * np.random.uniform(1.00, 1.03, len(prices)),
            'low': prices * np.random.uniform(0.97, 1.00, len(prices)),
            'close': prices,
            'volume': volume
        })
        
        # Add technical indicators
        df = self._calculate_technical_indicators(df)
        return df

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate required technical indicators
        """
        # Moving averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volatility (ATR approximation)
        df['atr'] = df['high'] - df['low']
        df['atr'] = df['atr'].rolling(window=14).mean()
        
        return df

    def calculate_news_impact_score(self, news_data: Dict[str, pd.DataFrame], 
                                  stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Calculate news impact on stock prices
        """
        self.logger.info("Calculating news impact scores")
        
        impact_scores = {}
        for ticker in news_data.keys():
            news_df = news_data[ticker]
            stock_df = stock_data[ticker] if ticker in stock_data else pd.DataFrame()
            
            # Merge news and stock data on date
            # For simplicity, we'll just calculate a composite news sentiment score
            if not news_df.empty:
                # Calculate rolling news sentiment score
                news_df['news_sentiment_rolling'] = news_df['sentiment_score'].rolling(window=5).mean()
                news_df['news_volume_zscore'] = (news_df['news_volume'] - news_df['news_volume'].mean()) / news_df['news_volume'].std()
                
                # Combine sentiment and volume for impact score
                news_df['news_impact_score'] = (
                    news_df['sentiment_score'] * 0.6 + 
                    news_df['relevance_score'] * 0.4
                )
                
                impact_scores[ticker] = news_df[['date', 'news_impact_score', 'sentiment_score', 'relevance_score']]
        
        return impact_scores

    def calculate_macro_regime_score(self, macro_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Calculate macro regime scores based on multiple indicators
        """
        self.logger.info("Calculating macro regime scores")
        
        # Combine all macro indicators into a regime score
        dates = None
        combined_data = {}
        
        for indicator, df in macro_data.items():
            if dates is None:
                dates = df['date'].values
                combined_data['date'] = dates
                combined_data[indicator] = df['normalized_value'].values
            else:
                # Merge on date (simplified version)
                combined_data[indicator] = df.set_index('date').reindex(dates)['normalized_value'].fillna(method='ffill').values
        
        # Create a combined regime score
        df_combined = pd.DataFrame(combined_data)
        
        # Calculate regime score (simplified)
        regime_weights = {
            'vix': 0.3,
            'cpi': 0.2,
            'gdp_growth': 0.2,
            'unemployment_rate': 0.15,
            'fed_rate': 0.15
        }
        
        score_cols = [col for col in df_combined.columns if col in regime_weights]
        regime_score = 0
        total_weight = 0
        
        for col in score_cols:
            if col in regime_weights:
                weight = regime_weights[col]
                regime_score += df_combined[col].fillna(0) * weight
                total_weight += weight
        
        if total_weight > 0:
            df_combined['macro_regime_score'] = regime_score / total_weight
        else:
            df_combined['macro_regime_score'] = 0
            
        return df_combined[['date', 'macro_regime_score']]

    def generate_technical_signals(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Generate technical signals based on stock indicators
        """
        self.logger.info("Generating technical signals")
        
        signals = {}
        for ticker, df in stock_data.items():
            if df.empty:
                signals[ticker] = pd.DataFrame(columns=['date', 'signal_name', 'signal_value', 'confidence'])
                continue
                
            # Calculate various technical signals
            df_signals = df[['date']].copy()
            
            # RSI signals
            df_signals['rsi_oversold'] = (df['rsi'] < 30).astype(int)
            df_signals['rsi_overbought'] = (df['rsi'] > 70).astype(int)
            
            # Moving average signals
            df_signals['ma_bullish_cross'] = ((df['sma_20'] > df['sma_50']) & 
                                            (df['sma_20'].shift(1) <= df['sma_50'].shift(1))).astype(int)
            df_signals['ma_bearish_cross'] = ((df['sma_20'] < df['sma_50']) & 
                                            (df['sma_20'].shift(1) >= df['sma_50'].shift(1))).astype(int)
            
            # Bollinger Band signals
            df_signals['bb_bullish_breakout'] = (df['close'] > df['bb_upper']).astype(int)
            df_signals['bb_bearish_breakout'] = (df['close'] < df['bb_lower']).astype(int)
            
            # MACD signals
            df_signals['macd_bullish_cross'] = ((df['macd'] > df['macd_signal']) & 
                                              (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
            df_signals['macd_bearish_cross'] = ((df['macd'] < df['macd_signal']) & 
                                              (df['macd'].shift(1) >= df['macd_signal'].shift(1))).astype(int)
            
            signals[ticker] = df_signals
        
        return signals

    def combine_signals_for_forecast(self, news_impact: Dict[str, pd.DataFrame],
                                   macro_regime: pd.DataFrame,
                                   technical_signals: Dict[str, pd.DataFrame],
                                   stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Combine news, macro, and technical signals to generate forecasts
        """
        self.logger.info("Combining signals for forecast generation")
        
        forecasts = {}
        
        for ticker in stock_data.keys():
            # Get the latest data for this ticker
            stock_df = stock_data[ticker].copy()
            news_df = news_impact.get(ticker, pd.DataFrame()) if news_impact else pd.DataFrame()
            tech_df = technical_signals.get(ticker, pd.DataFrame()) if technical_signals else pd.DataFrame()
            
            # Merge all data sources (simplified approach)
            if not stock_df.empty:
                # Combine relevant signals
                result_df = stock_df[['date', 'close', 'volume', 'rsi', 'sma_20', 'sma_50']].copy()
                
                # Add macro regime score
                result_df = result_df.merge(macro_regime, on='date', how='left')
                result_df['macro_regime_score'] = result_df['macro_regime_score'].fillna(method='ffill')
                
                # Add news impact if available
                if not news_df.empty:
                    result_df = result_df.merge(news_df, on='date', how='left')
                    result_df['news_impact_score'] = result_df['news_impact_score'].fillna(0)
                    result_df['sentiment_score'] = result_df['sentiment_score'].fillna(0)
                else:
                    result_df['news_impact_score'] = 0
                    result_df['sentiment_score'] = 0
                
                # Add technical signals if available
                if not tech_df.empty:
                    # Only merge the signal columns
                    signal_cols = [col for col in tech_df.columns if col not in ['date']]
                    tech_signal_df = tech_df[['date'] + signal_cols].copy()
                    result_df = result_df.merge(tech_signal_df, on='date', how='left')
                    
                    # Fill missing signal values with 0
                    for col in signal_cols:
                        if col != 'date':
                            result_df[col] = result_df[col].fillna(0)
                else:
                    # Add default signal columns
                    for signal in ['rsi_oversold', 'rsi_overbought', 'ma_bullish_cross', 
                                 'ma_bearish_cross', 'bb_bullish_breakout', 'bb_bearish_breakout',
                                 'macd_bullish_cross', 'macd_bearish_cross']:
                        result_df[signal] = 0
                
                # Calculate composite signal
                result_df['composite_signal'] = (
                    # Technical signals weighted
                    result_df['ma_bullish_cross'] * 0.2 +
                    result_df['ma_bearish_cross'] * -0.2 +
                    (result_df['rsi_oversold'] * 0.15) +
                    (result_df['rsi_overbought'] * -0.15) +
                    (result_df['macd_bullish_cross'] * 0.15) +
                    (result_df['macd_bearish_cross'] * -0.15) +
                    # News impact weighted
                    result_df['news_impact_score'] * 0.2 +
                    # Macro regime weighted
                    result_df['macro_regime_score'] * 0.1
                )
                
                # Calculate forecast direction and confidence
                result_df['forecast_direction'] = np.where(
                    result_df['composite_signal'] > 0.1, 'up',
                    np.where(result_df['composite_signal'] < -0.1, 'down', 'neutral')
                )
                
                # Calculate confidence based on signal strength
                result_df['confidence'] = np.abs(result_df['composite_signal'])
                result_df['confidence'] = np.clip(result_df['confidence'], 0, 1)
                
                # Calculate expected return
                # This is a simplified model - in practice this would be more sophisticated
                result_df['expected_return_1d'] = result_df['composite_signal'] * 0.02  # 2% max daily move
                result_df['expected_return_5d'] = result_df['composite_signal'] * 0.05  # 5% max 5-day move
                result_df['expected_return_22d'] = result_df['composite_signal'] * 0.10  # 10% max monthly move
                
                forecasts[ticker] = result_df
        
        return forecasts

    def run_pipeline(self, tickers: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Run the complete news→macro→stocks→forecast pipeline
        """
        self.logger.info(f"Running complete pipeline for tickers: {tickers}")
        
        # Step 1: Ingest news data
        news_data = self.ingest_news_data(tickers)
        
        # Step 2: Ingest macro data
        macro_data = self.ingest_macro_data()
        
        # Step 3: Ingest stock data
        stock_data = self.ingest_stock_data(tickers)
        
        # Step 4: Calculate news impact scores
        news_impact_scores = self.calculate_news_impact_score(news_data, stock_data)
        
        # Step 5: Calculate macro regime scores
        macro_regime_scores = self.calculate_macro_regime_score(macro_data)
        
        # Step 6: Generate technical signals
        technical_signals = self.generate_technical_signals(stock_data)
        
        # Step 7: Combine all signals for forecast
        forecasts = self.combine_signals_for_forecast(
            news_impact_scores, 
            macro_regime_scores, 
            technical_signals, 
            stock_data
        )
        
        self.logger.info("Pipeline completed successfully")
        return forecasts

    def generate_forecast_for_api(self, tickers: List[str]) -> Dict:
        """
        Generate forecast output in the format expected by the API
        """
        forecasts = self.run_pipeline(tickers)
        
        # Convert to API format
        api_output = {
            "last_update": datetime.now().isoformat(),
            "tickers_analyzed": tickers,
            "forecasts": {}
        }
        
        for ticker, df in forecasts.items():
            if not df.empty:
                # Get the most recent forecast
                latest = df.iloc[-1]
                
                api_output["forecasts"][ticker] = {
                    "date": latest['date'].isoformat() if hasattr(latest['date'], 'isoformat') else str(latest['date']),
                    "direction": latest['forecast_direction'],
                    "confidence": float(latest['confidence']),
                    "expected_return_1d": float(latest['expected_return_1d']),
                    "expected_return_5d": float(latest['expected_return_5d']) if 'expected_return_5d' in df.columns else 0.0,
                    "expected_return_22d": float(latest['expected_return_22d']) if 'expected_return_22d' in df.columns else 0.0,
                    "composite_signal": float(latest['composite_signal']),
                    "technical_signals": {
                        "ma_bullish_cross": bool(latest['ma_bullish_cross']) if 'ma_bullish_cross' in df.columns else False,
                        "ma_bearish_cross": bool(latest['ma_bearish_cross']) if 'ma_bearish_cross' in df.columns else False,
                        "rsi_oversold": bool(latest['rsi_oversold']) if 'rsi_oversold' in df.columns else False,
                        "rsi_overbought": bool(latest['rsi_overbought']) if 'rsi_overbought' in df.columns else False,
                        "bb_bullish_breakout": bool(latest['bb_bullish_breakout']) if 'bb_bullish_breakout' in df.columns else False,
                        "bb_bearish_breakout": bool(latest['bb_bearish_breakout']) if 'bb_bearish_breakout' in df.columns else False,
                        "macd_bullish_cross": bool(latest['macd_bullish_cross']) if 'macd_bullish_cross' in df.columns else False,
                        "macd_bearish_cross": bool(latest['macd_bearish_cross']) if 'macd_bearish_cross' in df.columns else False,
                    },
                    "news_impact": float(latest['news_impact_score']) if 'news_impact_score' in df.columns else 0.0,
                    "macro_regime": float(latest['macro_regime_score']) if 'macro_regime_score' in df.columns else 0.0
                }
        
        return api_output

# Example usage:
# pipeline = NewsMacroStocksForecastPipeline()
# result = pipeline.generate_forecast_for_api(['AAPL', 'MSFT', 'GOOGL'])