# runtime.py

## Class: `LLMClient`

Thin wrapper around g4f (default). Can be swapped without changing callers.

- generate(messages, json_mode=True) returns raw text (ideally JSON when json_mode=True)
- retries and simple backoff included; logs basic timing.

### Method: `LLMClient.generate`

Signature: `def generate(...)->str`

Inputs:
- `messages`: List[Dict[str, str]]
- `json_mode` (kwonly): bool = True
- `temperature` (kwonly): float = 0.2
- `max_tokens` (kwonly): int = 1200
- `retries` (kwonly): int = 2
- `backoff_sec` (kwonly): float = 1.5
Returns: `str`
