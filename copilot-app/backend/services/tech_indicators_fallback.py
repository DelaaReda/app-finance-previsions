"""
Technical Indicators Fallback Service - FC-DATA-005
Author: ALEX-API-ARCHITECT-SUPERMAN-7

Task: FC-DATA-005 - Avoid null values on /api/stocks/:ticker by recalculating via /stocks/prices
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import math
from datetime import datetime

# Import our storage system
from backend.storage.io import load_json, save_json

logger = logging.getLogger(__name__)

def calculate_sma(prices: List[float], window: int) -> List[Optional[float]]:
    """
    Calculate Simple Moving Average for the given price series and window size.
    Returns list with SMA values aligned with original price list (None for first window-1).
    """
    if len(prices) < window:
        return [None] * len(prices)
    
    sma_values = [None] * (window - 1)  # Initialize with None for first window values
    for i in range(window - 1, len(prices)):
        sma = sum(prices[i - window + 1:i + 1]) / window
        sma_values.append(sma)
    
    return sma_values

def calculate_rsi(prices: List[float], window: int = 14) -> List[Optional[float]]:
    """
    Calculate RSI (Relative Strength Index) for the given price series.
    Returns list with RSI values aligned with original price list (None for first window values).
    """
    if len(prices) < window + 1:
        return [None] * len(prices)
    
    rsi_values = [None] * window  # Initialize with None for first window values
    
    # Calculate price changes
    changes = [None] * len(prices)
    for i in range(1, len(prices)):
        changes[i] = prices[i] - prices[i-1] if i > 0 else None
    
    # Calculate RSI for each point past the window
    for i in range(window, len(prices)):
        gains = 0
        losses = 0
        for j in range(i - window + 1, i + 1):
            change = changes[j]
            if change is not None:
                if change > 0:
                    gains += change
                else:
                    losses -= change  # Negative of negative = positive
        
        if losses == 0:
            rsi_values.append(100.0)
        else:
            avg_gain = gains / window
            avg_loss = losses / window
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)
    
    return rsi_values

def calculate_ema(prices: List[float], window: int) -> List[Optional[float]]:
    """
    Calculate Exponential Moving Average for the given price series and window size.
    """
    if len(prices) < window:
        return [None] * len(prices)
    
    ema_values = [None] * (window - 1)  # Initialize with None for first window-1 values
    sma = sum(prices[:window]) / window
    ema_values.append(sma)
    
    multiplier = 2 / (window + 1)
    for i in range(window, len(prices)):
        ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(ema)
    
    return ema_values

def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[Optional[float]]]:
    """
    Calculate MACD (Moving Average Convergence Divergence) indicators.
    Returns dictionary with macd, signal and histogram values.
    """
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    macd_line = []
    for i in range(len(prices)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_val = ema_fast[i] - ema_slow[i]
            macd_line.append(macd_val)
        else:
            macd_line.append(None)
    
    signal_line = calculate_ema(macd_line, signal)
    
    histogram = []
    for i in range(len(prices)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram.append(macd_line[i] - signal_line[i])
        else:
            histogram.append(None)
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }

def enrich_missing_indicators(ticker_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate missing technical indicators (SMA, RSI) for a ticker when they are null,
    using the price history data to recalculate them.
    
    Args:
        ticker_data: Ticker data that may have null/missing technical indicators
        
    Returns:
        Ticker data with calculated indicators where they were missing
    """
    try:
        logger.info(f"Processing technical indicators for {ticker_data.get('ticker', 'N/A')}")
        
        # Extract pricing data to calculate indicators from
        prices_data = ticker_data.get('prices', [])
        
        # Convert to list of prices for calculation
        price_values = []
        if isinstance(prices_data, list):
            # If already a list of values or price objects
            for item in prices_data:
                if isinstance(item, (int, float)):
                    # Direct price values
                    price_values.append(float(item))
                elif isinstance(item, dict) and 'close' in item:
                    # Price objects with close price
                    if item.get('close') is not None:
                        price_values.append(float(item['close']))
                elif isinstance(item, dict) and 'value' in item:
                    # Price objects with value
                    if item.get('value') is not None:
                        price_values.append(float(item['value']))
        elif isinstance(prices_data, dict):
            # If it's a dictionary, might contain a 'points' key
            points = prices_data.get('points', prices_data.get('data', []))
            if isinstance(points, list):
                for point in points:
                    if isinstance(point, dict):
                        if 'close' in point and point['close'] is not None:
                            price_values.append(float(point['close']))
                        elif 'value' in point and point['value'] is not None:
                            price_values.append(float(point['value']))
                        elif 'price' in point and point['price'] is not None:
                            price_values.append(float(point['price']))
                    elif isinstance(point, (int, float)):
                        price_values.append(float(point))
        
        # If no prices data, return original data unchanged
        if not price_values or len(price_values) < 2:
            logger.warning(f"Insufficient price data ({len(price_values)} points) for {ticker_data.get('ticker', 'N/A')}")
            # Still return a structure with indicator values so the frontend doesn't crash
            if 'technical_indicators' not in ticker_data:
                ticker_data['technical_indicators'] = {}
            # Set to N/A values instead of null to prevent crashes
            tech_indicators = ticker_data['technical_indicators']
            if tech_indicators.get('sma_20') is None:
                tech_indicators['sma_20'] = 'N/A'
            if tech_indicators.get('sma_50') is None:
                tech_indicators['sma_50'] = 'N/A'
            if tech_indicators.get('sma_200') is None:
                tech_indicators['sma_200'] = 'N/A'
            if tech_indicators.get('rsi_14') is None:
                tech_indicators['rsi_14'] = 'N/A'
            return ticker_data
        
        # Ensure technical_indicators exists in the data
        if 'technical_indicators' not in ticker_data:
            ticker_data['technical_indicators'] = {}
        
        technical_indicators = ticker_data['technical_indicators']
        
        # Calculate SMA indicators if they are missing/NULL
        if technical_indicators.get('sma_20') is None or technical_indicators.get('sma_20') == 'N/A':
            sma_20_values = calculate_sma(price_values, 20)
            if sma_20_values and len(sma_20_values) > 0:
                # Get the latest non-NaN SMA value
                latest_sma_20 = None
                for val in reversed(sma_20_values):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_sma_20 = val
                        break
                technical_indicators['sma_20'] = latest_sma_20
                logger.info(f"Calculated SMA_20 fallback: {latest_sma_20}")
        
        if technical_indicators.get('sma_50') is None or technical_indicators.get('sma_50') == 'N/A':
            sma_50_values = calculate_sma(price_values, 50)
            if sma_50_values and len(sma_50_values) > 0:
                # Get the latest non-NaN SMA value
                latest_sma_50 = None
                for val in reversed(sma_50_values):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_sma_50 = val
                        break
                technical_indicators['sma_50'] = latest_sma_50
                logger.info(f"Calculated SMA_50 fallback: {latest_sma_50}")
        
        if technical_indicators.get('sma_200') is None or technical_indicators.get('sma_200') == 'N/A':
            sma_200_values = calculate_sma(price_values, 200)
            if sma_200_values and len(sma_200_values) > 0:
                # Get the latest non-NaN SMA value
                latest_sma_200 = None
                for val in reversed(sma_200_values):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_sma_200 = val
                        break
                technical_indicators['sma_200'] = latest_sma_200
                logger.info(f"Calculated SMA_200 fallback: {latest_sma_200}")
        
        if technical_indicators.get('rsi_14') is None or technical_indicators.get('rsi_14') == 'N/A':
            rsi_14_values = calculate_rsi(price_values, 14)
            if rsi_14_values and len(rsi_14_values) > 0:
                # Get the latest non-NaN RSI value
                latest_rsi_14 = None
                for val in reversed(rsi_14_values):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_rsi_14 = val
                        break
                technical_indicators['rsi_14'] = latest_rsi_14
                logger.info(f"Calculated RSI_14 fallback: {latest_rsi_14}")
        
        # Add other common indicators if missing
        if technical_indicators.get('ema_20') is None or technical_indicators.get('ema_20') == 'N/A':
            ema_20_values = calculate_ema(price_values, 20)
            if ema_20_values and len(ema_20_values) > 0:
                latest_ema_20 = None
                for val in reversed(ema_20_values):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_ema_20 = val
                        break
                technical_indicators['ema_20'] = latest_ema_20
        
        if technical_indicators.get('macd') is None or technical_indicators.get('macd') == 'N/A':
            macd_data = calculate_macd(price_values)
            if macd_data.get('macd') and len(macd_data['macd']) > 0:
                latest_macd = None
                latest_signal = None
                latest_histogram = None
                
                for val in reversed(macd_data['macd']):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_macd = val
                        break
                        
                for val in reversed(macd_data['signal']):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_signal = val
                        break
                        
                for val in reversed(macd_data['histogram']):
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        latest_histogram = val
                        break
                
                technical_indicators['macd'] = latest_macd
                technical_indicators['macd_signal'] = latest_signal
                technical_indicators['macd_histogram'] = latest_histogram
        
        # Update the enrichment timestamp to track when indicators were added
        ticker_data['indicators_updated_at'] = datetime.now().isoformat()
        ticker_data['indicators_source'] = 'calculated_fallback'
        
        logger.info(f"Successfully processed technical indicators for {ticker_data.get('ticker', 'N/A')}")
        return ticker_data
        
    except Exception as e:
        logger.error(f"Error calculating missing indicators for {ticker_data.get('ticker', 'N/A')}: {e}", exc_info=True)
        # Return the original data unchanged, but with error information
        if 'technical_indicators' not in ticker_data:
            ticker_data['technical_indicators'] = {}
        tech_indicators = ticker_data['technical_indicators']
        
        # Set default safe values to prevent UI crashes
        if tech_indicators.get('sma_20') is None or tech_indicators.get('sma_20') == 'N/A':
            tech_indicators['sma_20'] = 'N/A'
        if tech_indicators.get('sma_50') is None or tech_indicators.get('sma_50') == 'N/A':
            tech_indicators['sma_50'] = 'N/A'
        if tech_indicators.get('sma_200') is None or tech_indicators.get('sma_200') == 'N/A':
            tech_indicators['sma_200'] = 'N/A'
        if tech_indicators.get('rsi_14') is None or tech_indicators.get('rsi_14') == 'N/A':
            tech_indicators['rsi_14'] = 'N/A'
        
        ticker_data['indicators_error'] = str(e)
        return ticker_data


def calculate_missing_indicators_from_prices(ticker: str, price_data: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """
    Calculate missing technical indicators using price history data directly.
    This is used when technical indicators are missing from the main ticker data but we have price data.
    
    Args:
        ticker: Ticker symbol to calculate for
        price_data: List of price objects with structure like {date, close, high, low, ...}
        
    Returns:
        Dictionary with calculated technical indicators
    """
    try:
        logger.info(f"Calculating technical indicators from price history for {ticker}")
        
        # Extract closing prices
        close_prices = []
        for price_point in price_data:
            if isinstance(price_point, dict):
                close_val = price_point.get('close') or price_point.get('value') or price_point.get('price')
                if close_val is not None:
                    close_prices.append(float(close_val))
            elif isinstance(price_point, (int, float)):
                close_prices.append(float(price_point))
        
        if len(close_prices) < 2:
            logger.warning(f"Not enough price data for {ticker} - need at least 2 data points")
            return {
                'sma_20': 'N/A',
                'sma_50': 'N/A',
                'sma_200': 'N/A',
                'rsi_14': 'N/A',
                'ema_20': 'N/A',
                'macd': 'N/A',
                'calculation_status': 'insufficient_data'
            }
        
        # Calculate all missing indicators
        indicators = {}
        
        # SMA calculations
        sma_20_values = calculate_sma(close_prices, 20)
        latest_sma_20 = next((val for val in reversed(sma_20_values) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        indicators['sma_20'] = latest_sma_20
        
        sma_50_values = calculate_sma(close_prices, 50)
        latest_sma_50 = next((val for val in reversed(sma_50_values) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        indicators['sma_50'] = latest_sma_50
        
        sma_200_values = calculate_sma(close_prices, 200)
        latest_sma_200 = next((val for val in reversed(sma_200_values) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        indicators['sma_200'] = latest_sma_200
        
        # RSI calculation
        rsi_14_values = calculate_rsi(close_prices, 14)
        latest_rsi_14 = next((val for val in reversed(rsi_14_values) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        indicators['rsi_14'] = latest_rsi_14
        
        # EMA calculation
        ema_20_values = calculate_ema(close_prices, 20)
        latest_ema_20 = next((val for val in reversed(ema_20_values) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        indicators['ema_20'] = latest_ema_20
        
        # MACD calculation
        macd_data = calculate_macd(close_prices)
        latest_macd = next((val for val in reversed(macd_data['macd']) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        latest_macd_signal = next((val for val in reversed(macd_data['signal']) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        latest_macd_histogram = next((val for val in reversed(macd_data['histogram']) if val is not None and not (isinstance(val, float) and math.isnan(val))), 'N/A')
        
        indicators['macd'] = latest_macd
        indicators['macd_signal'] = latest_macd_signal
        indicators['macd_histogram'] = latest_macd_histogram
        
        indicators['calculation_status'] = 'success'
        indicators['calculation_time'] = datetime.now().isoformat()
        indicators['data_points_used'] = len(close_prices)
        
        logger.info(f"Successfully calculated indicators for {ticker}: SMA_20={indicators['sma_20']}, SMA_50={indicators['sma_50']}, RSI_14={indicators['rsi_14']}")
        
        return indicators
        
    except Exception as e:
        logger.error(f"Error calculating indicators from price data for {ticker}: {e}", exc_info=True)
        return {
            'sma_20': 'N/A',
            'sma_50': 'N/A',
            'sma_200': 'N/A',
            'rsi_14': 'N/A',
            'ema_20': 'N/A',
            'macd': 'N/A',
            'calculation_status': 'error',
            'error': str(e)
        }