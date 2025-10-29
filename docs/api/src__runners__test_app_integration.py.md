# test_app_integration.py

Integration tests for src/apps/app.py
Tests the main Streamlit application functionality.

## Class: `TestAppImports`

Test that app imports work correctly.

### Method: `TestAppImports.test_safe_import_success`

Signature: `def test_safe_import_success(...)->Any`

Test successful safe import.

Inputs:
- (none)
Returns: `Any`

### Method: `TestAppImports.test_safe_import_failure`

Signature: `def test_safe_import_failure(...)->Any`

Test failed safe import.

Inputs:
- (none)
Returns: `Any`

## Class: `TestUtilityFunctions`

Test app utility functions.

### Method: `TestUtilityFunctions.test_json_safe_functionality`

Signature: `def test_json_safe_functionality(...)->Any`

Test _json_s function handles various inputs.

Inputs:
- (none)
Returns: `Any`

### Method: `TestUtilityFunctions.test_trace_call_decorator`

Signature: `def test_trace_call_decorator(...)->Any`

Test the trace_call decorator.

Inputs:
- (none)
Returns: `Any`

## Class: `TestFunctionResolution`

Test function resolution for various modules.

### Method: `TestFunctionResolution.test_resolve_arbitre_with_class`

Signature: `def test_resolve_arbitre_with_class(...)->Any`

Test arbitre resolution when EconomicAnalyst class is available.

Inputs:
- (none)
Returns: `Any`

### Method: `TestFunctionResolution.test_resolve_arbitre_no_modules`

Signature: `def test_resolve_arbitre_no_modules(...)->Any`

Test arbitre resolution when no modules are available.

Inputs:
- (none)
Returns: `Any`

## Class: `TestMockedDependencies`

Test functions that require external dependencies.

### Method: `TestMockedDependencies.test_compute_technical_features_mock`

Signature: `def test_compute_technical_features_mock(...)->Any`

Test compute_technical_features with mocked dependencies.

Inputs:
- (none)
Returns: `Any`

### Method: `TestMockedDependencies.test_load_fundamentals_mock`

Signature: `def test_load_fundamentals_mock(...)->Any`

Test load_fundamentals with mocked function.

Inputs:
- (none)
Returns: `Any`

### Method: `TestMockedDependencies.test_load_news_mock`

Signature: `def test_load_news_mock(...)->Any`

Test load_news with mocked function.

Inputs:
- (none)
Returns: `Any`

## Class: `TestErrorHandling`

Test error handling in the application.

### Method: `TestErrorHandling.test_log_exc_function`

Signature: `def test_log_exc_function(...)->Any`

Test log_exc function logs exceptions properly.

Inputs:
- (none)
Returns: `Any`

## Class: `TestConfigurationConstants`

Test that important constants are defined correctly.

### Method: `TestConfigurationConstants.test_constants_defined`

Signature: `def test_constants_defined(...)->Any`

Test that critical constants exist.

Inputs:
- (none)
Returns: `Any`
