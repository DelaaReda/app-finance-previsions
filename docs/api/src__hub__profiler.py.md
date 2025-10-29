# profiler.py

## Function: `log_event`

Signature: `def log_event(...)->None`

Append a JSONL event with utc timestamp.

event_type: 'http' | 'callback' | 'subprocess' | 'info' | 'error'
payload: any JSON-serializable dict

Inputs:
- `event_type`: str
- `payload`: Dict[str, Any]
Returns: `None`

## Function: `read_last`

Signature: `def read_last(...)->list[dict]`

Inputs:
- `n`: int = 200
Returns: `list[dict]`

## Function: `clear`

Signature: `def clear(...)->None`

Inputs:
- (none)
Returns: `None`
