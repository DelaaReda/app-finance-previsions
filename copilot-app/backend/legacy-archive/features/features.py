"""
Market Feature Set - FC-P1-012
Technical indicators for ML model input
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path


def sma(prices: pd.Series, window: int) -> pd.Series:
    """
    Simple Moving Average
    """
    return prices.rolling(window=window).mean()


def ema(prices: pd.Series, window: int) -> pd.Series:
    """
    Exponential Moving Average
    """
    return prices.ewm(span=window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    Relative Strength Index
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def bb(close: pd.Series, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands
    Returns: (upper, middle, lower)
    """
    middle = sma(close, window)
    rolling_std = close.rolling(window).std()
    upper = middle + (rolling_std * num_std)
    lower = middle - (rolling_std * num_std)
    
    return upper, middle, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Average True Range (volatility indicator)
    """
    # True Range calculation
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return tr.rolling(window).mean()


def returns(close: pd.Series) -> pd.Series:
    """
    Calculate simple returns
    """
    return (close / close.shift(1)) - 1


def log_returns(close: pd.Series) -> pd.Series:
    """
    Calculate log returns
    """
    return np.log(close / close.shift(1))


def volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    """
    Rolling volatility (standard deviation of returns)
    """
    return returns.rolling(window=window).std()


def momentum(close: pd.Series, period: int = 10) -> pd.Series:
    """
    Price momentum indicator
    """
    return close - close.shift(period)


def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all technical features for a given dataframe with OHLCV data
    Expected columns: ['date', 'open', 'high', 'low', 'close', 'volume']
    """
    # Create a copy to avoid modifying original
    features_df = df.copy()
    
    # Basic price features
    features_df['returns'] = returns(features_df['close'])
    features_df['log_returns'] = log_returns(features_df['close'])
    features_df['volatility'] = volatility(features_df['returns'])
    features_df['momentum'] = momentum(features_df['close'])
    
    # Moving averages
    features_df['sma_20'] = sma(features_df['close'], 20)
    features_df['sma_50'] = sma(features_df['close'], 50)
    features_df['ema_12'] = ema(features_df['close'], 12)
    features_df['ema_26'] = ema(features_df['close'], 26)
    
    # RSI
    features_df['rsi_14'] = rsi(features_df['close'], 14)
    
    # MACD
    macd_line, signal_line, histogram = macd(features_df['close'])
    features_df['macd'] = macd_line
    features_df['macd_signal'] = signal_line
    features_df['macd_histogram'] = histogram
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = bb(features_df['close'])
    features_df['bb_upper'] = bb_upper
    features_df['bb_middle'] = bb_middle
    features_df['bb_lower'] = bb_lower
    features_df['bb_width'] = bb_upper - bb_lower  # Band width
    features_df['bb_position'] = (features_df['close'] - bb_lower) / (bb_upper - bb_lower)  # Position within bands
    
    # ATR and volatility
    features_df['atr_14'] = atr(features_df['high'], features_df['low'], features_df['close'], 14)
    features_df['atr_ratio'] = features_df['atr_14'] / features_df['close']  # Normalized ATR
    
    # Volume indicators (if available)
    if 'volume' in features_df.columns:
        features_df['volume_sma'] = sma(features_df['volume'], 20)
        features_df['volume_ratio'] = features_df['volume'] / features_df['volume_sma']  # Volume relative to average
    
    # Price-based features
    features_df['high_low_ratio'] = features_df['high'] / features_df['low']
    features_df['close_position'] = (features_df['close'] - features_df['low']) / (features_df['high'] - features_df['low'])  # Position within day's range
    
    # Add some derived features
    features_df['price_change_pct'] = (features_df['close'] - features_df['open']) / features_df['open']
    features_df['high_close_ratio'] = features_df['high'] / features_df['close']
    features_df['low_close_ratio'] = features_df['low'] / features_df['close']
    
    return features_df


def load_market_data(ticker: str, days_back: int = 365) -> Optional[pd.DataFrame]:
    """
    Load market data for a given ticker
    In a real implementation, this would connect to yfinance or another data provider
    For this implementation, we'll generate synthetic data based on the ticker pattern
    """
    try:
        # Create date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Filter out weekends (in real implementation, use business days)
        dates = dates[dates.weekday < 5]  # Only weekdays
        
        # Generate synthetic price data with realistic patterns
        np.random.seed(abs(hash(ticker + str(dates[0])) % (2**32)))  # For reproducible results per ticker
        n_days = len(dates)
        
        # Start with a base price based on ticker (just for variety)
        base_price = 50 + (hash(ticker) % 200)  # Base price between 50-250
        
        # Generate realistic price movements
        returns = np.random.normal(0.0005, 0.02, n_days)  # Daily returns (0.05% mean, 2% std)
        prices = [base_price]
        
        for r in returns[1:]:
            prices.append(prices[-1] * (1 + r))
        
        # Ensure no negative prices
        prices = [max(p, 1.0) for p in prices]
        
        # Generate OHLCV data
        high = []
        low = []
        open_prices = []
        close_prices = []
        volume = []
        
        for i in range(len(prices)):
            # Add some intraday volatility
            daily_change = np.random.uniform(0.01, 0.04)  # 1-4% daily range
            open_price = prices[i-1] if i > 0 else prices[i]
            close_price = prices[i]
            
            # Calculate high and low based on open/close and daily volatility
            range_size = abs(close_price - open_price) + close_price * daily_change
            high_val = max(open_price, close_price) + range_size * np.random.uniform(0, 0.5)
            low_val = min(open_price, close_price) - range_size * np.random.uniform(0, 0.5)
            
            # Ensure low is not below 0
            low_val = max(low_val, close_price * 0.95)  # Never below 5% of close
            
            high.append(high_val)
            low.append(low_val)
            open_prices.append(open_price)
            close_prices.append(close_price)
            # Realistic volume
            volume.append(np.random.randint(1000000, 100000000))
        
        # Create the dataframe
        df = pd.DataFrame({
            'date': dates[:len(prices)],
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close_prices,
            'volume': volume[:len(prices)]
        })
        
        return df
    
    except Exception as e:
        print(f"Error loading market data for {ticker}: {e}")
        return None


def compute_features_for_ticker(ticker: str, days_back: int = 365) -> Optional[Dict]:
    """
    Compute features for a specific ticker
    """
    print(f"Computing features for {ticker}...")
    
    # Load market data
    market_data = load_market_data(ticker, days_back)
    if market_data is None or market_data.empty:
        print(f"Could not load market data for {ticker}")
        return None
    
    # Compute technical features
    features_df = compute_technical_features(market_data)
    
    # Prepare result
    result = {
        'ticker': ticker,
        'computed_at': datetime.now().isoformat(),
        'feature_count': len(features_df.columns),
        'data_points': len(features_df),
        'date_range': {
            'start': features_df['date'].min().isoformat() if not features_df.empty else None,
            'end': features_df['date'].max().isoformat() if not features_df.empty else None
        },
        'features': features_df.to_dict('records'),  # Convert to list of dictionaries
        'feature_names': list(features_df.columns)
    }
    
    return result


def save_features_to_json(features_data: Dict, output_dir: str = "data/features") -> bool:
    """
    Save features to JSON file
    """
    try:
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create filename
        ticker = features_data['ticker']
        filename = f"{output_dir}/{ticker}_features.json"
        
        # Write to file
        with open(filename, 'w') as f:
            json.dump(features_data, f, default=str, indent=2)  # default=str handles datetime serialization
        
        print(f"Features saved for {ticker} to {filename}")
        return True
    
    except Exception as e:
        print(f"Error saving features for {ticker}: {e}")
        return False


def compute_features_for_multiple_tickers(tickers: List[str], days_back: int = 365) -> Dict[str, Dict]:
    """
    Compute features for multiple tickers
    """
    all_features = {}
    
    for ticker in tickers:
        features = compute_features_for_ticker(ticker, days_back)
        if features:
            all_features[ticker] = features
            save_features_to_json(features)
        else:
            print(f"Failed to compute features for {ticker}")
    
    return all_features


# Example usage and test function
def main():
    """
    Main function to demonstrate the feature computation
    """
    print("Starting market feature computation...")
    
    # List of example tickers
    tickers = ["SPY", "QQQ"]  # Using 2 tickers as required by DoD
    
    print(f"Computing features for {len(tickers)} tickers: {tickers}")
    
    # Compute features for all tickers
    all_features = compute_features_for_multiple_tickers(tickers)
    
    print(f"Completed feature computation for {len(all_features)} tickers")
    
    # Show summary
    for ticker, features in all_features.items():
        print(f"{ticker}: {features['data_points']} data points, {features['feature_count']} features")
        
        # Show a sample of recent features
        if features['features']:
            recent = features['features'][-1]  # Latest data point
            print(f"  Latest close: {recent.get('close', 'N/A')}")
            print(f"  Latest RSI: {recent.get('rsi_14', 'N/A')}")
            print(f"  Latest MACD: {recent.get('macd', 'N/A')}")
            print(f"  Latest volatility: {recent.get('volatility', 'N/A')}")
    
    return all_features


if __name__ == "__main__":
    main()