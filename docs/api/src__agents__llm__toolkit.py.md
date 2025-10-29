# toolkit.py

## Class: `Tool`

### Method: `Tool.call`

Signature: `def call(...)->Any`

Inputs:
- `**kwargs`: Any
Returns: `Any`

## Function: `register`

Signature: `def register(...)->Any`

Inputs:
- `tool`: Tool
Returns: `Any`

## Function: `load_forecasts`

Signature: `def load_forecasts(...)->Dict[str, Any]`

Inputs:
- `horizon`: str | None = None
- `limit`: int = 50
Returns: `Dict[str, Any]`

## Function: `load_macro`

Signature: `def load_macro(...)->Dict[str, Any]`

Inputs:
- `limit`: int = 20
Returns: `Dict[str, Any]`

## Function: `freshness_status`

Signature: `def freshness_status(...)->Dict[str, Any]`

Inputs:
- (none)
Returns: `Dict[str, Any]`
