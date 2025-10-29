# logging_setup.py

## Class: `InterceptHandler`

### Method: `InterceptHandler.emit`

Signature: `def emit(...)->None`

Inputs:
- `record`: LogRecord
Returns: `None`

## Function: `setup_logging`

Signature: `def setup_logging(...)->Any`

Idempotent: configure Loguru + pont stdlib + capture warnings.

Inputs:
- `level`: str | int = 'DEBUG'
Returns: `Any`

## Function: `get_logger`

Signature: `def get_logger(...)->Any`

Inputs:
- `name`: str = 'hub'
Returns: `Any`

## Function: `ensure_trace`

Signature: `def ensure_trace(...)->Any`

Inputs:
- (none)
Returns: `Any`

## Function: `configure_logging`

Signature: `def configure_logging(...)->Any`

Wrapper for backward compatibility with existing code.

Inputs:
- `level`: Any = logging.INFO
- `logfile`: Any = 'logs/hub_app.log'
Returns: `Any`
