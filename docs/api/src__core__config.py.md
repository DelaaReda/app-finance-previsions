# config.py

Configuration management for financial analysis tools.
Loads settings from environment variables and config files.

## Class: `Config`

Global configuration singleton

### Method: `Config.get_data_path`

Signature: `def get_data_path(...)->Path`

Get path under data directory

Inputs:
- `*parts`: str
Returns: `Path`

### Method: `Config.get_cache_path`

Signature: `def get_cache_path(...)->Path`

Get path under cache directory

Inputs:
- `*parts`: str
Returns: `Path`

### Method: `Config.get_artifacts_path`

Signature: `def get_artifacts_path(...)->Path`

Get path under artifacts directory

Inputs:
- `*parts`: str
Returns: `Path`

### Method: `Config.has_premium_apis`

Signature: `def has_premium_apis(...)->bool`

Check if premium API keys are configured

Inputs:
- (none)
Returns: `bool`

### Method: `Config.to_dict`

Signature: `def to_dict(...)->Dict[str, Any]`

Convert config to dictionary, optionally excluding sensitive values

Inputs:
- `exclude_secrets`: bool = True
Returns: `Dict[str, Any]`
