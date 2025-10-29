# test_macro_fix.py

Test script to verify that macro data loading is now working correctly.
Includes tests for deprecated pandas functions and error handling.

## Function: `test_single_fred_series`

Signature: `def test_single_fred_series(...)->Any`

Test that individual FRED series are now loading correctly.

Inputs:
- (none)
Returns: `Any`

## Function: `test_macro_bundle`

Signature: `def test_macro_bundle(...)->Any`

Test that the macro bundle loads correctly.

Inputs:
- (none)
Returns: `Any`

## Function: `test_macro_nowcast`

Signature: `def test_macro_nowcast(...)->Any`

Test that macro nowcast works correctly.

Inputs:
- `bundle`: Any
Returns: `Any`

## Function: `test_pandas_deprecation_warnings`

Signature: `def test_pandas_deprecation_warnings(...)->Any`

Test that deprecated pandas functions don't generate warnings.

Inputs:
- (none)
Returns: `Any`

## Function: `test_get_macro_features`

Signature: `def test_get_macro_features(...)->Any`

Test the get_macro_features function used by the app.

Inputs:
- (none)
Returns: `Any`

## Function: `main`

Signature: `def main(...)->Any`

Run all tests and report results.

Inputs:
- (none)
Returns: `Any`
