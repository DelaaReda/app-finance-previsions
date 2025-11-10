"""
Test script to verify G4F model enhancements on existing data
Task: FC-ML-ENHANCE-001 - Enhanced ML Model with G4F Integration
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'copilot-app', 'backend'))

from models.forecast_g4f_analyzer_v2 import ForecastG4FAnalyzerV2

def create_test_data(ticker: str, days: int = 60):
    """Create realistic test market data for a ticker"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Start with a base price
    base_price = 400.0 if 'SPY' in ticker else 300.0
    
    # Generate price movements with some trend
    prices = [base_price]
    for i in range(1, len(dates)):
        # Base return
        base_return = 0.0005 if ticker in ['SPY', 'QQQ'] else 0.001  # Small daily drift
        # Add some volatility
        volatility = 0.02  # 2% daily volatility
        daily_return = base_return + np.random.normal(0, volatility)
        prices.append(prices[-1] * (1 + daily_return))
    
    # Create technical indicators
    df = pd.DataFrame({
        'Date': dates,
        'Open': [p * (1 + np.random.uniform(-0.005, 0.005)) for p in prices],
        'High': [p * (1 + np.random.uniform(0.005, 0.015)) for p in prices],
        'Low': [p * (1 - np.random.uniform(0.005, 0.015)) for p in prices],
        'Close': prices,
        'Volume': np.random.uniform(1000000, 50000000, len(prices)).astype(int)
    })
    df.set_index('Date', inplace=True)
    
    return df

def test_g4f_on_existing_data():
    """Test G4F model enhancements on existing market data"""
    print("🧪 Testing G4F Forecast Model Enhancements on Existing Data...")
    
    # Initialize the G4F analyzer
    analyzer = ForecastG4FAnalyzerV2(preferred_model="gpt-3.5-turbo")
    
    # Create test data for multiple tickers
    test_tickers = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'META']
    test_data = {}
    
    for ticker in test_tickers:
        print(f"📈 Creating test data for {ticker}...")
        test_data[ticker] = create_test_data(ticker)
        print(f"   Data shape: {test_data[ticker].shape}")
        print(f"   Price range: ${test_data[ticker]['Close'].iloc[-5:].min():.2f} - ${test_data[ticker]['Close'].iloc[-5:].max():.2f}")
    
    # Test single forecast analysis
    print(f"\n🤖 Testing G4F analysis for {test_tickers[0]}...")
    result = analyzer.analyze_existing_data_with_g4f(test_tickers[0], test_data[test_tickers[0]])
    
    print(f"✅ Single forecast result: {result['ticker']} - {result['direction']} (confidence: {result['confidence']:.3f})")
    
    # Test batch analysis
    print(f"\n🔄 Testing batch G4F analysis for {len(test_tickers)} tickers...")
    batch_results = analyzer.batch_analyze_with_g4f(test_data)
    
    print(f"✅ Batch forecast completed: {len(batch_results)} forecasts generated")
    
    # Display results
    print("\n📊 Forecast Results:")
    for forecast in batch_results:
        print(f"   {forecast['ticker']}: {forecast['direction']} | "
              f"Conf: {forecast['confidence']:.3f} | "
              f"ER: {forecast['expected_return']:.4f} | "
              f"Expl: {forecast['explanation'][:50]}...")
    
    # Verify data integrity
    print(f"\n✅ Verification:")
    print(f"   - All forecasts have ticker: {all('ticker' in f for f in batch_results)}")
    print(f"   - All forecasts have direction: {all('direction' in f for f in batch_results)}")
    print(f"   - All forecasts have confidence: {all('confidence' in f for f in batch_results)}")
    print(f"   - Confidence values in valid range: {all(0 <= f['confidence'] <= 1 for f in batch_results)}")
    
    return result, batch_results

if __name__ == "__main__":
    test_g4f_on_existing_data()