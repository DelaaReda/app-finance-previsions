"""
Main execution script for the Hybrid Forecast Model
Part of the Finance Copilot forecasting engine
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import pandas as pd
import numpy as np
import sys
import os
from typing import Dict, Any
from model import HybridForecastModel

# Add parent directory to path to import other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_forecast(ticker: str, data: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate forecast for a given ticker using the hybrid model
    
    Args:
        ticker: Stock ticker symbol
        data: Historical price data with columns: date, open, high, low, close, volume
        
    Returns:
        Dictionary with forecast results
    """
    # Initialize the model
    model = HybridForecastModel(arima_order=(2, 1, 2))
    
    # Fit the model
    model.fit(data, target_col='close')
    
    # Generate predictions
    results = model.predict(data, steps=1, target_col='close')
    
    # Format results to match expected API response
    formatted_results = {
        "ticker": ticker,
        "horizon": "1d",
        "direction": results['direction'],
        "confidence": results['confidence'],
        "expected_return": results['expected_return'],
        "explanation": results['explanation'],
        "metrics": results['metrics'],
        "predictions": results['predictions']
    }
    
    return formatted_results


def create_sample_data(ticker: str = "SPY", days: int = 252) -> pd.DataFrame:
    """
    Create sample data for testing (in real implementation, this would come from data sources)
    """
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq='D')
    
    # Generate realistic price data
    returns = np.random.normal(0.0005, 0.02, days)  # Daily return: mean 0.05%, std 2%
    prices = [100]  # Starting price
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Add some technical patterns
    for i in range(20, len(prices)):
        if i % 20 == 0:  # Add some momentum every 20 days
            prices[i] = prices[i-1] * (1 + np.random.normal(0.02, 0.03))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, len(prices))
    })
    
    return df


def main():
    """
    Main function to run the forecasting model
    """
    print("MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7: Initializing Forecast Engine...")
    
    # Create sample data for testing
    sample_data = create_sample_data("SPY", 252)
    
    print(f"Sample data shape: {sample_data.shape}")
    print(f"Date range: {sample_data['date'].min()} to {sample_data['date'].max()}")
    
    # Generate forecast
    try:
        results = generate_forecast("SPY", sample_data)
        
        print("\n" + "="*60)
        print("FORECAST RESULTS")
        print("="*60)
        print(f"Ticker: {results['ticker']}")
        print(f"Horizon: {results['horizon']}")
        print(f"Direction: {results['direction']}")
        print(f"Confidence: {results['confidence']:.3f}")
        print(f"Expected Return: {results['expected_return']:.4f} ({results['expected_return']*100:.2f}%)")
        print(f"Explanation: {results['explanation']}")
        print(f"Current Price: {results['metrics']['current_price']:.2f}")
        print(f"Forecast Price: {results['metrics']['forecast_price']:.2f}")
        print("="*60)
        
        # Save results to a JSON file for API consumption
        import json
        with open('forecast_output.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nForecast saved to forecast_output.json")
        
    except Exception as e:
        print(f"Error generating forecast: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()