# test_phase2_technical.py

Tests for src/analytics/phase2_technical.py
Tests technical analysis functions, indicators, signals, and backtesting.

## Class: `TestDataLoading`

Test data loading functions.

### Method: `TestDataLoading.test_load_prices_success`

Signature: `def test_load_prices_success(...)->Any`

Test successful price loading.

Inputs:
- `mock_yf`: Any
Returns: `Any`

### Method: `TestDataLoading.test_load_prices_empty`

Signature: `def test_load_prices_empty(...)->Any`

Test empty price data handling.

Inputs:
- `mock_yf`: Any
Returns: `Any`

## Class: `TestIndicators`

Test technical indicators computation.

### Method: `TestIndicators.create_sample_data`

Signature: `def create_sample_data(...)->Any`

Create sample OHLCV data for testing.

Inputs:
- (none)
Returns: `Any`

### Method: `TestIndicators.test_compute_indicators`

Signature: `def test_compute_indicators(...)->Any`

Test indicators computation.

Inputs:
- (none)
Returns: `Any`

### Method: `TestIndicators.test_indicator_set_to_dict`

Signature: `def test_indicator_set_to_dict(...)->Any`

Test IndicatorSet to_dict method.

Inputs:
- (none)
Returns: `Any`

## Class: `TestSignals`

Test technical signals calculation.

### Method: `TestSignals.test_technical_signals`

Signature: `def test_technical_signals(...)->Any`

Test technical signals with complete data.

Inputs:
- (none)
Returns: `Any`

### Method: `TestSignals.test_signals_to_dict`

Signature: `def test_signals_to_dict(...)->Any`

Test TechnicalSignals to_dict method.

Inputs:
- (none)
Returns: `Any`

## Class: `TestRegimeDetection`

Test regime detection functions.

### Method: `TestRegimeDetection.test_detect_regime_bull`

Signature: `def test_detect_regime_bull(...)->Any`

Test bull regime detection.

Inputs:
- (none)
Returns: `Any`

### Method: `TestRegimeDetection.test_detect_regime_bear`

Signature: `def test_detect_regime_bear(...)->Any`

Test bear regime detection.

Inputs:
- (none)
Returns: `Any`

### Method: `TestRegimeDetection.test_detect_regime_range`

Signature: `def test_detect_regime_range(...)->Any`

Test range regime detection.

Inputs:
- (none)
Returns: `Any`

### Method: `TestRegimeDetection.test_detect_regime_insufficient_data`

Signature: `def test_detect_regime_insufficient_data(...)->Any`

Test regime detection with insufficient data.

Inputs:
- (none)
Returns: `Any`

## Class: `TestRiskStats`

Test risk statistics calculation.

### Method: `TestRiskStats.test_risk_stats_sufficient_data`

Signature: `def test_risk_stats_sufficient_data(...)->Any`

Test risk stats with sufficient data.

Inputs:
- (none)
Returns: `Any`

### Method: `TestRiskStats.test_risk_stats_insufficient_data`

Signature: `def test_risk_stats_insufficient_data(...)->Any`

Test risk stats with insufficient data.

Inputs:
- (none)
Returns: `Any`

### Method: `TestRiskStats.test_risk_stats_to_dict`

Signature: `def test_risk_stats_to_dict(...)->Any`

Test RiskStats to_dict method.

Inputs:
- (none)
Returns: `Any`

## Class: `TestHighLevelAPI`

Test high-level API functions.

### Method: `TestHighLevelAPI.test_compute_technical_features_success`

Signature: `def test_compute_technical_features_success(...)->Any`

Test successful technical features computation.

Inputs:
- `mock_build`: Any
Returns: `Any`

### Method: `TestHighLevelAPI.test_compute_technical_features_error`

Signature: `def test_compute_technical_features_error(...)->Any`

Test error handling in technical features computation.

Inputs:
- `mock_build`: Any
Returns: `Any`

### Method: `TestHighLevelAPI.test_build_technical_view_success`

Signature: `def test_build_technical_view_success(...)->Any`

Test successful technical view building.

Inputs:
- `mock_risk`: Any
- `mock_regime`: Any
- `mock_signals`: Any
- `mock_indicators`: Any
- `mock_load`: Any
Returns: `Any`

### Method: `TestHighLevelAPI.test_build_technical_view_no_data`

Signature: `def test_build_technical_view_no_data(...)->Any`

Test technical view building with no data.

Inputs:
- `mock_load`: Any
Returns: `Any`
