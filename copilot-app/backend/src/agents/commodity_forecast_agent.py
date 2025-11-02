"""
Commodity Forecast Agent

Generates forecasts for commodities (gold, oil, agricultural) using technical indicators,
macro factors (supply/demand, USD strength), and historical patterns.

Outputs: data/forecast/dt=YYYYMMDD/commodities.parquet
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import json

import pandas as pd
import numpy as np

# Lazy imports to keep CLI simple
try:
    from core.market_data import get_price_history
except Exception:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from core.market_data import get_price_history

DT_FMT = "%Y%m%d"

# Commodity configurations
COMMODITIES = {
    "GC=F": {
        "name": "Gold",
        "category": "precious_metals",
        "unit": "USD/oz",
        "macro_factors": ["USD_strength", "inflation", "geopolitical_risk"]
    },
    "CL=F": {
        "name": "Crude Oil WTI",
        "category": "energy",
        "unit": "USD/barrel",
        "macro_factors": ["global_demand", "supply_disruptions", "USD_strength"]
    },
    "SI=F": {
        "name": "Silver",
        "category": "precious_metals",
        "unit": "USD/oz",
        "macro_factors": ["USD_strength", "industrial_demand", "gold_correlation"]
    },
    "HG=F": {
        "name": "Copper",
        "category": "industrial_metals",
        "unit": "USD/lb",
        "macro_factors": ["china_demand", "global_growth", "supply_constraints"]
    },
    "ZC=F": {
        "name": "Corn",
        "category": "agricultural",
        "unit": "USD/bushel",
        "macro_factors": ["weather_patterns", "global_demand", "ethanol_demand"]
    }
}

HORIZONS = ["1w", "1m", "3m"]
HORIZON_DAYS = {"1w": 5, "1m": 21, "3m": 63}

def _today_dt() -> str:
    return datetime.utcnow().strftime(DT_FMT)

def _load_macro_factors() -> Dict[str, float]:
    """Load latest macro indicators for commodity forecasting"""
    try:
        # Try to load from macro forecast data
        macro_parts = sorted(Path('data/macro/forecast').glob('dt=*'))
        if macro_parts:
            latest = macro_parts[-1]
            macro_file = latest / 'macro_forecast.parquet'
            if macro_file.exists():
                df = pd.read_parquet(macro_file)
                if not df.empty:
                    # Extract latest values
                    factors = {}
                    for col in df.columns:
                        if col in ['cpi_yoy', 'yield_10y', 'yield_2y', 'unemployment', 'gdp_growth']:
                            factors[col] = float(df[col].dropna().iloc[-1])
                    return factors
    except Exception as e:
        print(f"Warning: Could not load macro factors: {e}")

    # Fallback to default values
    return {
        'cpi_yoy': 2.5,
        'yield_10y': 4.5,
        'yield_2y': 4.2,
        'unemployment': 3.8,
        'gdp_growth': 2.1
    }

def _compute_technical_indicators(prices: pd.DataFrame, ticker: str) -> Dict[str, float]:
    """Compute technical indicators for commodity forecasting"""
    if prices is None or prices.empty or 'Close' not in prices.columns:
        return {}

    close = pd.to_numeric(prices['Close'], errors='coerce').dropna()

    if len(close) < 50:  # Need minimum data for indicators
        return {}

    indicators = {}

    try:
        # Moving averages
        indicators['sma_20'] = float(close.tail(20).mean())
        indicators['sma_50'] = float(close.tail(50).mean())
        indicators['sma_200'] = float(close.tail(200).mean())

        # Momentum indicators
        indicators['rsi_14'] = _compute_rsi(close, 14)
        indicators['macd'] = _compute_macd(close)

        # Volatility
        indicators['volatility_20'] = float(close.tail(20).pct_change().std() * np.sqrt(252))

        # Trend strength
        indicators['trend_strength'] = _compute_trend_strength(close)

    except Exception as e:
        print(f"Warning: Error computing indicators for {ticker}: {e}")

    return indicators

def _compute_rsi(prices: pd.Series, period: int = 14) -> float:
    """Compute RSI indicator"""
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        return float(rsi)
    except Exception:
        return 50.0

def _compute_macd(prices: pd.Series) -> float:
    """Compute MACD indicator"""
    try:
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        return float(macd.iloc[-1])
    except:
        return 0.0

def _compute_trend_strength(prices: pd.Series) -> float:
    """Compute trend strength based on price momentum"""
    try:
        # Compare short-term vs long-term momentum
        short_ma = prices.tail(20).mean()
        long_ma = prices.tail(200).mean()
        current_price = prices.iloc[-1]

        if long_ma > 0:
            trend_ratio = (current_price - long_ma) / long_ma
            return float(min(max(trend_ratio, -1.0), 1.0))
        return 0.0
    except:
        return 0.0

def _forecast_commodity(ticker: str, commodity_config: Dict, macro_factors: Dict) -> List[Dict[str, Any]]:
    """Generate forecasts for a single commodity"""
    print(f"Forecasting {commodity_config['name']} ({ticker})...")

    # Get historical price data (minimum 5 years)
    start_date = (datetime.utcnow() - timedelta(days=5*365)).strftime('%Y-%m-%d')
    prices = get_price_history(ticker, start=start_date)

    if prices is None or prices.empty:
        print(f"Warning: No price data for {ticker}")
        return _get_empty_forecasts(ticker, commodity_config)

    # Compute technical indicators
    indicators = _compute_technical_indicators(prices, ticker)

    # Get current price
    current_price = float(prices['Close'].iloc[-1])

    # Generate forecasts for each horizon
    forecasts = []
    for horizon in HORIZONS:
        forecast = _generate_single_forecast(
            ticker, commodity_config, current_price, indicators,
            macro_factors, horizon, prices
        )
        forecasts.append(forecast)

    return forecasts

def _generate_single_forecast(ticker: str, config: Dict, current_price: float,
                            indicators: Dict, macro_factors: Dict,
                            horizon: str, prices: pd.DataFrame) -> Dict[str, Any]:
    """Generate forecast for a single horizon"""

    # Base forecast using technical indicators
    base_return = _compute_base_return(indicators, horizon)

    # Adjust for macro factors
    macro_adjustment = _compute_macro_adjustment(config, macro_factors, horizon)

    # Adjust for commodity-specific factors
    commodity_adjustment = _compute_commodity_adjustment(config, indicators, horizon)

    # Combine adjustments
    total_adjustment = base_return + macro_adjustment + commodity_adjustment

    # Calculate expected price and return
    horizon_days = HORIZON_DAYS[horizon]
    expected_return = total_adjustment
    expected_price = current_price * (1 + expected_return)

    # Determine direction and confidence
    direction = "up" if expected_return > 0.02 else ("down" if expected_return < -0.02 else "flat")
    confidence = _compute_confidence(indicators, macro_factors, horizon)

    return {
        "ticker": ticker,
        "commodity_name": config["name"],
        "category": config["category"],
        "horizon": horizon,
        "current_price": round(current_price, 2),
        "expected_price": round(expected_price, 2),
        "expected_return": round(expected_return, 4),
        "direction": direction,
        "confidence": round(confidence, 3),
        "unit": config["unit"],
        "technical_indicators": indicators,
        "macro_factors": macro_factors
    }

def _compute_base_return(indicators: Dict, horizon: str) -> float:
    """Compute base return using technical indicators"""
    if not indicators:
        return 0.0

    # Trend-based return
    trend_strength = indicators.get('trend_strength', 0.0)
    volatility = indicators.get('volatility_20', 0.15)

    # Scale return by horizon
    horizon_multiplier = {"1w": 0.5, "1m": 1.0, "3m": 1.5}[horizon]

    # Base return from trend
    base_return = trend_strength * 0.1 * horizon_multiplier

    # Adjust for volatility (higher volatility = lower confidence, smaller moves)
    volatility_adjustment = -0.05 * (volatility - 0.15) * horizon_multiplier

    return base_return + volatility_adjustment

def _compute_macro_adjustment(config: Dict, macro_factors: Dict, horizon: str) -> float:
    """Compute macro factor adjustments"""
    adjustment = 0.0
    horizon_multiplier = {"1w": 0.3, "1m": 0.7, "3m": 1.0}[horizon]

    # USD strength impact (inverse relationship for most commodities)
    usd_strength = macro_factors.get('yield_10y', 4.5) - macro_factors.get('yield_2y', 4.2)
    if 'USD_strength' in config['macro_factors']:
        adjustment -= usd_strength * 0.02 * horizon_multiplier

    # Inflation impact (positive for commodities as inflation hedge)
    cpi = macro_factors.get('cpi_yoy', 2.5)
    if 'inflation' in config['macro_factors']:
        adjustment += (cpi - 2.0) * 0.03 * horizon_multiplier

    # Growth impact
    gdp_growth = macro_factors.get('gdp_growth', 2.1)
    if 'global_demand' in config['macro_factors'] or 'china_demand' in config['macro_factors']:
        adjustment += (gdp_growth - 2.0) * 0.02 * horizon_multiplier

    return adjustment

def _compute_commodity_adjustment(config: Dict, indicators: Dict, horizon: str) -> float:
    """Compute commodity-specific adjustments"""
    adjustment = 0.0

    # Precious metals adjustments
    if config['category'] == 'precious_metals':
        # Gold/silver benefit from uncertainty
        if indicators.get('volatility_20', 0) > 0.2:
            adjustment += 0.02

        # RSI-based mean reversion
        rsi = indicators.get('rsi_14', 50)
        if rsi > 70:
            adjustment -= 0.03  # Overbought
        elif rsi < 30:
            adjustment += 0.03  # Oversold

    # Energy adjustments
    elif config['category'] == 'energy':
        # MACD trend following
        macd = indicators.get('macd', 0)
        if macd > 0:
            adjustment += 0.02
        else:
            adjustment -= 0.02

    # Industrial metals adjustments
    elif config['category'] == 'industrial_metals':
        # Strong trend following
        trend_strength = indicators.get('trend_strength', 0)
        adjustment += trend_strength * 0.05

    return adjustment

def _compute_confidence(indicators: Dict, macro_factors: Dict, horizon: str) -> float:
    """Compute confidence level for the forecast"""
    confidence = 0.5  # Base confidence

    # Technical indicators confidence
    if indicators:
        # RSI confidence (extreme values = higher confidence)
        rsi = indicators.get('rsi_14', 50)
        rsi_confidence = 1.0 - abs(rsi - 50) / 50
        confidence += rsi_confidence * 0.2

        # Trend strength confidence
        trend_strength = abs(indicators.get('trend_strength', 0))
        confidence += trend_strength * 0.2

        # Volatility confidence (lower volatility = higher confidence)
        volatility = indicators.get('volatility_20', 0.15)
        vol_confidence = max(0, 1.0 - (volatility - 0.1) / 0.2)
        confidence += vol_confidence * 0.1

    # Horizon confidence (shorter horizon = higher confidence)
    horizon_confidence = {"1w": 0.8, "1m": 0.6, "3m": 0.4}[horizon]
    confidence += (horizon_confidence - 0.5) * 0.3

    return min(max(confidence, 0.3), 0.9)

def _get_empty_forecasts(ticker: str, config: Dict) -> List[Dict[str, Any]]:
    """Return empty forecasts when no data is available"""
    return [{
        "ticker": ticker,
        "commodity_name": config["name"],
        "category": config["category"],
        "horizon": horizon,
        "current_price": 0.0,
        "expected_price": 0.0,
        "expected_return": 0.0,
        "direction": "flat",
        "confidence": 0.5,
        "unit": config["unit"],
        "technical_indicators": {},
        "macro_factors": {}
    } for horizon in HORIZONS]

def run_once() -> Path:
    """Generate commodity forecasts and save to parquet"""
    print("Starting commodity forecast generation...")

    # Load macro factors
    macro_factors = _load_macro_factors()
    print(f"Loaded macro factors: {macro_factors}")

    # Generate forecasts for all commodities
    all_forecasts = []
    for ticker, config in COMMODITIES.items():
        forecasts = _forecast_commodity(ticker, config, macro_factors)
        all_forecasts.extend(forecasts)

    # Create output dataframe
    df = pd.DataFrame(all_forecasts)
    df.insert(0, "dt", pd.to_datetime(_today_dt()))

    # Save to parquet
    outdir = Path("data/forecast") / f"dt={_today_dt()}"
    outdir.mkdir(parents=True, exist_ok=True)

    output_file = outdir / "commodities.parquet"
    df.to_parquet(output_file, index=False)

    print(f"Saved {len(df)} commodity forecasts to {output_file}")
    return output_file

def main():
    """CLI entry point"""
    output_file = run_once()
    print(f"Commodity forecasts completed: {output_file}")

if __name__ == "__main__":
    main()
