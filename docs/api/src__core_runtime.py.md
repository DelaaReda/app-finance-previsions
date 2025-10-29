# core_runtime.py

## Function: `get_trace_id`

Signature: `def get_trace_id(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `set_trace_id`

Signature: `def set_trace_id(...)->Any`

Inputs:
- `val`: Any
Returns: `Any`

## Function: `new_trace_id`

Signature: `def new_trace_id(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `get_span_id`

Signature: `def get_span_id(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `set_span_id`

Signature: `def set_span_id(...)->Any`

Inputs:
- `val`: Any
Returns: `Any`

## Function: `new_span_id`

Signature: `def new_span_id(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Class: `JsonFormatter`

### Method: `JsonFormatter.format`

Signature: `def format(...)->str`

Inputs:
- `record`: logging.LogRecord
Returns: `str`

## Class: `CorrelationIdFilter`

### Method: `CorrelationIdFilter.filter`

Signature: `def filter(...)->bool`

Inputs:
- `record`: logging.LogRecord
Returns: `bool`

## Class: `JsonHandler`

### Method: `JsonHandler.emit`

Signature: `def emit(...)->Any`

Inputs:
- `record`: Any
Returns: `Any`

## Function: `configure_logging`

Signature: `def configure_logging(...)->Any`

Inputs:
- `level`: Any = logging.INFO
Returns: `Any`

## Function: `with_span`

Signature: `def with_span(...)->Any`

Pour les fonctions backend (fetch_xxx, parse_xxx, etc.).

Inputs:
- `name`: str
- `**ctx`: Any
Returns: `Any`

## Function: `ui_event`

Signature: `def ui_event(...)->Any`

À utiliser dans l'UI : encadre chaque clic/chargement.

Inputs:
- `action`: str
- `ui_page`: str = None
- `**ctx`: Any
Returns: `Any`

## Function: `make_session`

Signature: `def make_session(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `df_fingerprint`

Signature: `def df_fingerprint(...)->Any`

Inputs:
- `df`: pd.DataFrame
Returns: `Any`

## Function: `write_entry`

Signature: `def write_entry(...)->Any`

Append a provenance entry to a JSONL log instead of SQLite.

Inputs:
- `dataset`: str
- `source_url`: str
- `status`: str
- `meta`: dict
- `schema_version`: str
Returns: `Any`

## Function: `get_dataset_log_latest`

Signature: `def get_dataset_log_latest(...)->pd.DataFrame`

Return the latest entry per dataset from the JSONL log as a DataFrame.

Inputs:
- (none)
Returns: `pd.DataFrame`
