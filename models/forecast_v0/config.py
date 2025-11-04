# Configuration for Forecasting Engine
# MAXIMILIAN-FINANCE-WIZARD-SPIDERMAN-7

# ARIMA Model Configuration
ARIMA_ORDER = (2, 1, 2)
ARIMA_SEASONAL_ORDER = (1, 1, 1, 5)  # (P, D, Q, S) - weekly seasonality

# XGBoost Model Configuration
XGB_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'objective': 'reg:squarederror'
}

# Feature Engineering Configuration
FEATURE_LAGS = [1, 2, 3, 5, 10]
MOVING_AVERAGE_WINDOWS = [5, 10, 20, 50]
RSI_WINDOW = 14
BB_WINDOW = 20

# Forecast Horizon Configuration
DEFAULT_HORIZON = 1  # 1 day forecast
CONFIDENCE_INTERVAL = 0.95

# Data Preprocessing Configuration
MIN_DATAPOINTS = 50  # Minimum data points required to train model
FILL_MISSING_METHOD = 'forward'  # 'forward', 'backward', 'interpolate'
OUTLIER_METHOD = 'iqr'  # 'iqr', 'zscore', 'none'

# Model Validation Configuration
CV_FOLDS = 5
TEST_SIZE = 0.2
RANDOM_STATE = 42

# Performance Metrics Configuration
METRICS = ['mse', 'mae', 'mape', 'rmse']

# Model Persistence Configuration
MODEL_SAVE_PATH = './models/forecast_v0/saved_models/'
MODEL_FILE_EXTENSION = '.pkl'

# Feature Columns (these will be auto-generated based on data)
FEATURE_COLUMNS = [
    'returns',
    'log_returns',
    'sma_5',
    'sma_20',
    'sma_ratio',
    'volatility',
    'rsi',
    'bb_position',
    'volume_ratio'
]

# Target Column Configuration
TARGET_COLUMN = 'close'