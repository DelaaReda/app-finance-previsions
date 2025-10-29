# secrets_local.py

## Function: `get_key`

Signature: `def get_key(...)->Optional[str]`

Return an API key by checking environment variables first,
then this module's attributes as a fallback.

Inputs:
- `name`: str
Returns: `Optional[str]`
