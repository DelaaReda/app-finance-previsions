from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_forecast_data():
    """Generate mock forecast data for testing purposes."""
    
    # Create the data directory if it doesn't exist
    forecast_dir = Path("data/forecast/dt=20251103")
    forecast_dir.mkdir(parents=True, exist_ok=True)
    
    # Define some sample tickers
    tickers = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'TSM']
    
    # Define forecast horizons
    horizons = ['1w', '1m', '3m', '6m']
    
    # Generate mock forecast data
    data = []
    for ticker in tickers:
        for horizon in horizons:
            # Generate random forecast values
            final_score = np.random.uniform(30, 90)  # Score between 30-90
            direction = np.random.choice(['UP', 'DOWN'])  # Direction
            confidence = np.random.uniform(0.5, 1.0)  # Confidence between 0.5-1.0
            expected_return = np.random.uniform(-0.1, 0.2)  # Expected return between -10% and +20%
            
            # Add to data list
            data.append({
                'ticker': ticker,
                'horizon': horizon,
                'final_score': final_score,
                'direction': direction,
                'confidence': confidence,
                'expected_return': expected_return,
                'generated_at': datetime.now(),
                'model': 'mock_model',
                'asset_type': 'equity'
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to parquet file
    output_file = forecast_dir / 'final.parquet'
    df.to_parquet(output_file, index=False)
    
    print(f"Generated {len(df)} forecast records and saved to {output_file}")
    print(f"Unique tickers: {df['ticker'].nunique()}")
    print(f"Unique horizons: {df['horizon'].nunique()}")
    
    # Also generate some commodity forecasts
    commodities = ['GC=F', 'CL=F', 'HG=F', 'SI=F']  # Gold, Crude Oil, Copper, Silver
    commodity_data = []
    
    for commodity in commodities:
        for horizon in horizons:
            final_score = np.random.uniform(30, 90)
            direction = np.random.choice(['UP', 'DOWN'])
            confidence = np.random.uniform(0.4, 0.9)
            expected_return = np.random.uniform(-0.15, 0.15)
            
            commodity_data.append({
                'commodity_name': commodity,
                'horizon': horizon,
                'final_score': final_score,
                'direction': direction,
                'confidence': confidence,
                'expected_return': expected_return,
                'generated_at': datetime.now(),
                'model': 'commodity_model',
                'asset_type': 'commodity'
            })
    
    if commodity_data:
        df_commodities = pd.DataFrame(commodity_data)
        commodity_file = forecast_dir / 'commodities.parquet'
        df_commodities.to_parquet(commodity_file, index=False)
        print(f"Generated {len(df_commodities)} commodity forecast records and saved to {commodity_file}")

if __name__ == "__main__":
    generate_forecast_data()