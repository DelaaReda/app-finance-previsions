# test_econ_llm_agent.py

Tests for src/analytics/econ_llm_agent.py
Tests the EconomicAnalyst class and related functions.

## Class: `TestEconomicAnalyst`

Test the EconomicAnalyst class.

### Method: `TestEconomicAnalyst.sample_input`

Signature: `def sample_input(...)->Any`

Sample EconomicInput for testing.

Inputs:
- (none)
Returns: `Any`

### Method: `TestEconomicAnalyst.test_initialization_default`

Signature: `def test_initialization_default(...)->Any`

Test default initialization.

Inputs:
- (none)
Returns: `Any`

### Method: `TestEconomicAnalyst.test_initialization_custom`

Signature: `def test_initialization_custom(...)->Any`

Test custom initialization.

Inputs:
- (none)
Returns: `Any`

### Method: `TestEconomicAnalyst.test_call_model_success`

Signature: `def test_call_model_success(...)->Any`

Test successful model call.

Inputs:
- `mock_client`: Any
- `sample_input`: Any
Returns: `Any`

### Method: `TestEconomicAnalyst.test_call_model_failure`

Signature: `def test_call_model_failure(...)->Any`

Test model call failure.

Inputs:
- `mock_client`: Any
- `sample_input`: Any
Returns: `Any`

### Method: `TestEconomicAnalyst.test_build_messages`

Signature: `def test_build_messages(...)->Any`

Test message building.

Inputs:
- `sample_input`: Any
Returns: `Any`

## Class: `TestUtilityFunctions`

Test utility functions.

### Method: `TestUtilityFunctions.test_truncate_normal_text`

Signature: `def test_truncate_normal_text(...)->Any`

Test text truncation when under limit.

Inputs:
- (none)
Returns: `Any`

### Method: `TestUtilityFunctions.test_truncate_long_text`

Signature: `def test_truncate_long_text(...)->Any`

Test text truncation when over limit.

Inputs:
- (none)
Returns: `Any`

### Method: `TestUtilityFunctions.test_format_features`

Signature: `def test_format_features(...)->Any`

Test feature formatting.

Inputs:
- (none)
Returns: `Any`

### Method: `TestUtilityFunctions.test_format_news`

Signature: `def test_format_news(...)->Any`

Test news formatting.

Inputs:
- (none)
Returns: `Any`

### Method: `TestUtilityFunctions.test_build_context`

Signature: `def test_build_context(...)->Any`

Test context building.

Inputs:
- (none)
Returns: `Any`

## Class: `TestJsonProcessing`

Test JSON processing functions.

### Method: `TestJsonProcessing.test_to_json_serializable_basic_types`

Signature: `def test_to_json_serializable_basic_types(...)->Any`

Test serialization of basic Python types.

Inputs:
- (none)
Returns: `Any`

### Method: `TestJsonProcessing.test_to_json_serializable_dict`

Signature: `def test_to_json_serializable_dict(...)->Any`

Test serialization of dictionaries.

Inputs:
- (none)
Returns: `Any`

### Method: `TestJsonProcessing.test_to_json_serializable_list`

Signature: `def test_to_json_serializable_list(...)->Any`

Test serialization of lists.

Inputs:
- (none)
Returns: `Any`

### Method: `TestJsonProcessing.test_to_json_serializable_custom_object`

Signature: `def test_to_json_serializable_custom_object(...)->Any`

Test serialization of custom objects.

Inputs:
- (none)
Returns: `Any`

### Method: `TestJsonProcessing.test_extract_tail_json_line_valid`

Signature: `def test_extract_tail_json_line_valid(...)->Any`

Test extraction of valid JSON from text.

Inputs:
- (none)
Returns: `Any`

### Method: `TestJsonProcessing.test_extract_tail_json_line_invalid`

Signature: `def test_extract_tail_json_line_invalid(...)->Any`

Test extraction with invalid JSON.

Inputs:
- (none)
Returns: `Any`

### Method: `TestJsonProcessing.test_extract_tail_json_line_missing_keys`

Signature: `def test_extract_tail_json_line_missing_keys(...)->Any`

Test extraction with JSON missing required keys.

Inputs:
- (none)
Returns: `Any`

## Class: `TestAgreementScoring`

Test agreement scoring functions.

### Method: `TestAgreementScoring.test_agreement_score_identical`

Signature: `def test_agreement_score_identical(...)->Any`

Test agreement score for identical texts.

Inputs:
- (none)
Returns: `Any`

### Method: `TestAgreementScoring.test_agreement_score_different`

Signature: `def test_agreement_score_different(...)->Any`

Test agreement score for completely different texts.

Inputs:
- (none)
Returns: `Any`

### Method: `TestAgreementScoring.test_agreement_score_partial`

Signature: `def test_agreement_score_partial(...)->Any`

Test agreement score for partially similar texts.

Inputs:
- (none)
Returns: `Any`

## Class: `TestEconomicInput`

Test EconomicInput dataclass.

### Method: `TestEconomicInput.test_initialization_minimal`

Signature: `def test_initialization_minimal(...)->Any`

Test minimal initialization.

Inputs:
- (none)
Returns: `Any`

### Method: `TestEconomicInput.test_initialization_full`

Signature: `def test_initialization_full(...)->Any`

Test full initialization.

Inputs:
- (none)
Returns: `Any`
