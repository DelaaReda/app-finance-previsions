"""
Baseline ARIMA/XGB Forecasting Model
Part of the Finance Copilot forecasting engine
Author: MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
import warnings
warnings.filterwarnings('ignore')

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


class HybridForecastModel:
    """
    Hybrid forecasting model combining ARIMA for time series patterns
    and XGBoost for feature-based predictions
    """
    
    def __init__(self, arima_order=(1, 1, 1), xgb_params=None):
        self.arima_order = arima_order
        self.xgb_params = xgb_params or {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': 42
        }
        
        self.arima_model = None
        self.arima_fitted = None
        self.xgb_model = None
        self.is_fitted = False
        
    def _check_stationarity(self, timeseries):
        """Check if the time series is stationary"""
        if not ARIMA_AVAILABLE:
            return True  # Skip stationarity check if statsmodels not available
            
        result = adfuller(timeseries.dropna())
        p_value = result[1]
        return p_value < 0.05  # Stationary if p < 0.05
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare technical features for XGBoost model"""
        features = df.copy()
        
        # Price-based features
        features['returns'] = features['close'].pct_change()
        features['log_returns'] = np.log(features['close'] / features['close'].shift(1))
        
        # Technical indicators
        features['sma_5'] = features['close'].rolling(5).mean()
        features['sma_20'] = features['close'].rolling(20).mean()
        features['sma_ratio'] = features['sma_5'] / features['sma_20']
        
        # Volatility
        features['volatility'] = features['returns'].rolling(20).std()
        
        # RSI
        delta = features['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        features['bb_middle'] = features['close'].rolling(20).mean()
        bb_std = features['close'].rolling(20).std()
        features['bb_upper'] = features['bb_middle'] + (bb_std * 2)
        features['bb_lower'] = features['bb_middle'] - (bb_std * 2)
        features['bb_position'] = (features['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # Volume features
        features['volume_sma'] = features['volume'].rolling(10).mean()
        features['volume_ratio'] = features['volume'] / features['volume_sma']
        
        # Lag features
        for lag in [1, 2, 3, 5]:
            features[f'close_lag_{lag}'] = features['close'].shift(lag)
            features[f'return_lag_{lag}'] = features['returns'].shift(lag)
        
        # Drop rows with NaN values
        features = features.dropna()
        
        return features
    
    def fit(self, data: pd.DataFrame, target_col: str = 'close'):
        """
        Fit the hybrid model
        
        Args:
            data: DataFrame with columns including target_col
            target_col: The target column to forecast
        """
        if data.empty:
            raise ValueError("Input data is empty")
        
        # Prepare features for XGBoost
        features_df = self._prepare_features(data)
        feature_cols = [col for col in features_df.columns 
                       if col not in [target_col, 'returns', 'log_returns']]
        
        if not feature_cols:
            raise ValueError("No features available after processing")
        
        X = features_df[feature_cols]
        y = features_df[target_col]
        
        # Fit XGBoost model
        if XGB_AVAILABLE:
            self.xgb_model = xgb.XGBRegressor(**self.xgb_params)
            self.xgb_model.fit(X, y)
        
        # Fit ARIMA model
        if ARIMA_AVAILABLE:
            # Check if we have enough data for ARIMA
            if len(data[target_col]) >= max(self.arima_order) * 3:
                try:
                    self.arima_model = ARIMA(data[target_col].dropna(), order=self.arima_order)
                    self.arima_fitted = self.arima_model.fit()
                except Exception as e:
                    print(f"Warning: Could not fit ARIMA model: {e}")
        
        self.is_fitted = True
        return self
    
    def predict(self, data: pd.DataFrame, steps: int = 1, target_col: str = 'close') -> Dict[str, Any]:
        """
        Generate forecasts
        
        Args:
            data: Input data for feature calculation
            steps: Number of steps to forecast
            target_col: Target column to forecast
            
        Returns:
            Dictionary with forecast results
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Prepare features
        features_df = self._prepare_features(data)
        feature_cols = [col for col in features_df.columns 
                       if col not in [target_col, 'returns', 'log_returns']]
        X = features_df[feature_cols].tail(1)  # Use the latest row for prediction
        
        results = {
            'predictions': {},
            'confidence': {},
            'direction': {},
            'explanation': '',
            'metrics': {}
        }
        
        # XGBoost prediction
        xgb_pred = None
        if XGB_AVAILABLE and self.xgb_model is not None:
            xgb_pred = float(self.xgb_model.predict(X)[0])
            results['predictions']['xgb'] = xgb_pred
        
        # ARIMA prediction (if available)
        arima_pred = None
        if ARIMA_AVAILABLE and self.arima_fitted is not None:
            try:
                arima_forecast = self.arima_fitted.forecast(steps=steps)
                arima_pred = float(arima_forecast.iloc[0]) if len(arima_forecast) > 0 else xgb_pred
                results['predictions']['arima'] = arima_pred
            except Exception:
                arima_pred = xgb_pred  # Fallback to XGB if ARIMA fails
        
        # Combine predictions (if both available)
        if xgb_pred is not None and arima_pred is not None:
            # Weighted average - give more weight to the more recent prediction method
            combined_pred = 0.6 * xgb_pred + 0.4 * arima_pred
        elif xgb_pred is not None:
            combined_pred = xgb_pred
        elif arima_pred is not None:
            combined_pred = arima_pred
        else:
            # Fallback prediction
            combined_pred = float(data[target_col].iloc[-1])
        
        results['predictions']['combined'] = combined_pred
        
        # Calculate direction and confidence
        current_price = float(data[target_col].iloc[-1])
        expected_return = (combined_pred - current_price) / current_price
        direction = 'up' if expected_return > 0 else 'down' if expected_return < 0 else 'flat'
        
        results['direction'] = direction
        results['expected_return'] = expected_return
        results['confidence'] = min(abs(expected_return) * 10 + 0.5, 1.0)  # Simple confidence calculation
        
        # Simple explanation
        results['explanation'] = f"XGBoost prediction: {xgb_pred:.4f}" if xgb_pred else "XGBoost model not available"
        if arima_pred:
            results['explanation'] += f", ARIMA prediction: {arima_pred:.4f}"
        
        results['metrics'] = {
            'current_price': current_price,
            'forecast_price': combined_pred,
            'expected_return_pct': expected_return * 100
        }
        
        return results


def create_model(**kwargs) -> HybridForecastModel:
    """
    Factory function to create a forecasting model
    """
    return HybridForecastModel(**kwargs)